module "stockpot_app" {
  source     = "../../modules/application"
  env        = "staging"
  project_id = "stockpot-infrastructure"
  db_tier    = "db-f1-micro"
}

output "staging_url" {
  value = module.stockpot_app.app_url
}
