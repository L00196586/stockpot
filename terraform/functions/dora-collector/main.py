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

    resource = {
        "type": "global",
        "labels": {"project_id": project_id}  # Add this explicit label
    }

    env = data.get('env', 'production')
    # Status value => 1: Success. Status 0: Error
    status_value = 1 if data.get('status') == 'success' else 0
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
    status_series.resource.copy_from(resource)

    status_series.points = [monitoring_v3.Point({
        "interval": time_interval,
        "value": {"int64_value": status_value}
    })]
    series_list.append(status_series)

    # Calculate lead time if the deploy actually succeeded
    if status_value == 1 and commit_time:
        try:
            # Calculating lead time (current time - commit time)
            lead_time_seconds = int(now - float(commit_time))

            lead_series = monitoring_v3.TimeSeries()
            lead_series.metric.type = "custom.googleapis.com/dora/lead_time"
            lead_series.metric.labels["environment"] = env
            lead_series.metric.labels["commit"] = commit_sha
            lead_series.resource.copy_from(resource)

            lead_series.points = [monitoring_v3.Point({
                "interval": time_interval,
                "value": {"int64_value": lead_time_seconds}
            })]
            series_list.append(lead_series)
            lead_time_result = f"Lead time calculated: {lead_time_seconds} seconds"
        except ValueError:
            lead_time_result = f"Lead time ValueError: Invalid commit_time format"
            print("Invalid commit_time format received.")
    else:
        lead_time_result = f"Lead time not calculated"

    try:
        client.create_time_series(name=project_name, time_series=series_list)
        return f"Metric recorded. {lead_time_result}", 200
    except Exception as e:
        print(f"Error writing metric: {e}")
        return str(e), 500
