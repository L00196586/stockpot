variable "env" {}
variable "project_id" {}
variable "db_tier" { default = "db-f1-micro" }
# Google requires unique names for databases. This creates a random suffix for the DB name
resource "random_id" "db_name_suffix" {
  byte_length = 4
}

resource "google_sql_database_instance" "db_instance" {
  project          = var.project_id
  name             = "stockpot-${var.env}-db-${random_id.db_name_suffix.hex}"
  database_version = "POSTGRES_16"
  region           = "us-central1"
  settings {
    tier = var.db_tier
    edition = "ENTERPRISE"

    ip_configuration {
      ipv4_enabled = true
    }
  }
  deletion_protection = var.env == "production" ? true : false
}

# Creates the DB inside the instance
resource "google_sql_database" "db" {
  name     = "stockpot"
  instance = google_sql_database_instance.db_instance.name
}

# DB User
resource "google_sql_user" "user" {
  name     = "stockpot_user"
  instance = google_sql_database_instance.db_instance.name
  password = var.env == "production" ? "PROD-REALLY-SECURE-PW-CHANGE-ME" : "staging-pw-123"
}

# Cloud Run application
resource "google_cloud_run_v2_service" "app" {
  project  = var.project_id
  name     = "stockpot-${var.env}"
  location = "us-central1"
  template {
    # Django app
    containers {
      # GitHub Actions will overwrite this dummy image with the real app
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      # Connection string for dj-database-url
      env {
        name  = "DATABASE_URL"
        value = "postgres://${google_sql_user.user.name}:${google_sql_user.user.password}@/${google_sql_database.db.name}?host=/cloudsql/${google_sql_database_instance.db_instance.connection_name}"
      }
    }

    # Prometheus sidecar for monitoring
    containers {
      # GitHub Actions will overwrite this dummy image with the real app
      image = "us-docker.pkg.dev/cloud-ops-agents-artifacts/cloud-run-gmp-sidecar/cloud-run-gmp-sidecar:1.2.0"
      name  = "collector"

      args = [
        "--stackdriver.project-id=${var.project_id}",
        "--prometheus.target-url=http://localhost:8080/metrics",
        "--prometheus.scrape-interval=60s"
      ]
    }

    # Connects the app container to the database
    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.db_instance.connection_name]
      }
    }
  }
}

# Set the application as public
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  project  = google_cloud_run_v2_service.app.project
  location = google_cloud_run_v2_service.app.location
  name     = google_cloud_run_v2_service.app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# URL to see the app
output "app_url" {
    value = google_cloud_run_v2_service.app.uri
}
