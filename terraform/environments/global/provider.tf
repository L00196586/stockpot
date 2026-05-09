terraform {
  backend "gcs" {
    bucket  = "stockpot-terraform-state-16101989"
    prefix  = "terraform/global"
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
