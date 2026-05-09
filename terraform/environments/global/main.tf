# Artifact registry to hold the Docker images
resource "google_artifact_registry_repository" "stockpot_registry" {
  location      = "us-central1"
  repository_id = "stockpot-repo"
  description   = "Docker repository for StockPot images"
  format        = "DOCKER"
}

# DORA Metric Collector Cloud Function
# Bucket to store the function code
resource "google_storage_bucket" "function_bucket" {
  name     = "${var.project_id}-function-source"
  location = "US"
  uniform_bucket_level_access = true
}

# Zipping the code
data "archive_file" "dora_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../functions/dora-collector"
  output_path = "${path.module}/dora-collector.zip"
}

# Upload the zip to the bucket
resource "google_storage_bucket_object" "dora_zip_upload" {
  name   = "dora-collector-${data.archive_file.dora_zip.output_md5}.zip"
  bucket = google_storage_bucket.function_bucket.name
  source = data.archive_file.dora_zip.output_path
}

# Deploy the Cloud Function
resource "google_cloudfunctions2_function" "dora_collector" {
  name        = "dora-metric-collector"
  location    = "us-central1"
  description = "Collects DORA metrics from GitHub Actions"

  build_config {
    runtime     = "python311"
    entry_point = "collect_dora"
    source {
      storage_source {
        bucket = google_storage_bucket.function_bucket.name
        object = google_storage_bucket_object.dora_zip_upload.name
      }
    }
  }

  service_config {
    max_instance_count = 1
    available_memory   = "256M"
    timeout_seconds    = 60
    environment_variables = {
      GCP_PROJECT = var.project_id
    }
  }
}

# GitHub Actions needs to invoke the function without authentication, so we make it public
resource "google_cloud_run_service_iam_member" "public_invoker" {
  location = google_cloudfunctions2_function.dora_collector.location
  service  = google_cloudfunctions2_function.dora_collector.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Output the URL to use it in GitHub Actions
output "dora_webhook_url" {
  value = google_cloudfunctions2_function.dora_collector.service_config[0].uri
}
