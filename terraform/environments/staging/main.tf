# Google requires unique names for databases. This creates a random suffix for the DB name
resource "random_id" "db_name_suffix" {
  byte_length = 4
}

# 2PostgreSQL Database instance
resource "google_sql_database_instance" "staging_db_instance" {
  name             = "stockpot-staging-db-${random_id.db_name_suffix.hex}"
  database_version = "POSTGRES_16"
  region           = "us-central1"

  settings {
    tier = "db-f1-micro"

    ip_configuration {
      ipv4_enabled = true
    }
  }

  # Avoids accidentally deleting the database
  deletion_protection = false
}

# Creates the DB inside the instance
resource "google_sql_database" "staging_db" {
  name     = "stockpot"
  instance = google_sql_database_instance.staging_db_instance.name
}

# DB User
resource "google_sql_user" "staging_user" {
  name     = "stockpot_user"
  instance = google_sql_database_instance.staging_db_instance.name
  password = "staging-secure-password-123!"
}

# Cloud Run application
resource "google_cloud_run_v2_service" "staging_app" {
  name     = "stockpot-staging"
  location = "us-central1"
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      # GitHub Actions will overwrite this dummy image with the real app
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      # Connection string for dj-database-url
      env {
        name  = "DATABASE_URL"
        value = "postgres://${google_sql_user.staging_user.name}:${google_sql_user.staging_user.password}@/${google_sql_database.staging_db.name}?host=/cloudsql/${google_sql_database_instance.staging_db_instance.connection_name}"
      }
    }

    # Connects the app container to the database
    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.staging_db_instance.connection_name]
      }
    }
  }
}

# Set the application as public
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.staging_app.location
  service  = google_cloud_run_v2_service.staging_app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# URL to see the app
output "app_url" {
  value = google_cloud_run_v2_service.staging_app.uri
}