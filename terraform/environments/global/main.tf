# Artifact registry to hold the Docker images
resource "google_artifact_registry_repository" "stockpot_registry" {
  location      = "us-central1"
  repository_id = "stockpot-repo"
  description   = "Docker repository for StockPot images"
  format        = "DOCKER"
}