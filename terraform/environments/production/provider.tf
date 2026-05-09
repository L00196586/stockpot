terraform {
  # Using a bucket to maintain the state
  backend "gcs" {
    bucket  = "stockpot-terraform-state-16101989"
    prefix  = "terraform/production"
  }
}
provider "google" {
  project = "stockpot-infrastructure"
  region  = "us-central1"
}
