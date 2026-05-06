terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  # Replace this with your exact Google Cloud Project ID
  project = "stockpot-infrastructure"
  region  = "us-central1"
}
