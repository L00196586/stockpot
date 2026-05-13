import functions_framework
from google.cloud import monitoring_v3
import time
import os

client = monitoring_v3.MetricServiceClient()
# Extract project ID from the environment
project_id = os.environ.get('GCP_PROJECT', 'stockpot-infrastructure')
project_name = f"projects/{project_id}"


@functions_framework.http
def collect_dora(request):
    data = request.get_json()
    if not data:
        return "No data provided", 400

    print(f"Full Payload Received: {data}")
    env = data.get('env', 'production')
    # Status value => 1: Success. Status 0: Error
    status_str = str(data.get('status', '')).lower()
    is_success = (status_str == 'success')

    commit_sha = data.get('commit', 'unknown')
    commit_time = data.get('commit_time')

    now = time.time()
    seconds = int(now)
    nanos = int((now - seconds) * 10 ** 9)

    time_interval = {"end_time": {"seconds": seconds, "nanos": nanos}}
    series_list = []

    # Deployment status metric
    status_series = monitoring_v3.TimeSeries()
    status_series.metric.type = "custom.googleapis.com/dora/deployment_status"
    status_series.metric.labels["environment"] = env
    status_series.resource.type = "global"
    status_series.resource.labels["project_id"] = project_id

    status_series.points = [monitoring_v3.Point({
        "interval": time_interval,
        "value": {"int64_value": 1 if is_success else 0}
    })]
    series_list.append(status_series)

    # Calculate lead time if the deploy succeeded
    lead_time_result = "Not attempted"
    if is_success and commit_time:
        try:
            # Cleaning the input from whitespace and quotes
            clean_time = str(commit_time).strip().replace('"', '')
            # Calculating lead time (current time - commit time)
            lead_time_seconds = int(now - float(clean_time))

            lead_series = monitoring_v3.TimeSeries()
            lead_series.metric.type = "custom.googleapis.com/dora/lead_time"
            lead_series.metric.labels["environment"] = env
            lead_series.metric.labels["commit"] = commit_sha
            lead_series.resource.type = "global"
            lead_series.resource.labels["project_id"] = project_id

            lead_series.points = [monitoring_v3.Point({
                "interval": time_interval,
                "value": {"int64_value": lead_time_seconds}
            })]
            series_list.append(lead_series)
            lead_time_result = f"Lead time calculated: {lead_time_seconds} seconds"
        except Exception as e:
            lead_time_result = f"Lead time ValueError: {str(e)}"
            print("Invalid commit_time format received.")
    else:
        lead_time_result = "Lead time not calculated"

    try:
        client.create_time_series(name=project_name, time_series=series_list)
        return f"Metric recorded. {lead_time_result}", 200
    except Exception as e:
        print(f"Error writing metric: {e}")
        return str(e), 500
