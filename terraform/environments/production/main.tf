module "stockpot_app" {
  source     = "../../modules/application"
  env        = "production"
  project_id = "stockpot-infrastructure"
  # Production should have a more powerful DB tier, but this is the most affordable option and enough for this demo
  db_tier    = "db-f1-micro"
}

# URL to see the app
output "production_url" {
  value = module.stockpot_app.app_url
}
