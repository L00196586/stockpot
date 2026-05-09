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

    env = data.get('env', 'production')
    # Status 1: Success. Status 0: Error
    status = 1 if data.get('status') == 'success' else 0

    series = monitoring_v3.TimeSeries()
    series.metric.type = "custom.googleapis.com/dora/deployment_status"
    series.metric.labels["environment"] = env
    series.resource.type = "global"

    now = time.time()
    seconds = int(now)
    nanos = int((now - seconds) * 10 ** 9)

    point = monitoring_v3.Point({
        "interval": {"end_time": {"seconds": seconds, "nanos": nanos}},
        "value": {"int64_value": status}
    })
    series.points = [point]

    try:
        client.create_time_series(name=project_name, time_series=[series])
        return "Metric recorded", 200
    except Exception as e:
        print(f"Error writing metric: {e}")
        return str(e), 500