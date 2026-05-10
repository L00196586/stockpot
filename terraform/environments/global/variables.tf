variable "project_id" {
  type        = string
  description = "The GCP Project ID"
}

# You'll likely also need this for the Cloud Function region
variable "region" {
  type        = string
  description = "The GCP Region"
  default     = "us-central1"
}
