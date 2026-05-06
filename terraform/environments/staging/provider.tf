terraform {
  # Using a bucket to maintain the state
  backend "gcs" {
    bucket  = "stockpot-terraform-state-16101989"
    prefix  = "terraform/staging"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = "stockpot-infrastructure"
  region  = "us-central1"
}
