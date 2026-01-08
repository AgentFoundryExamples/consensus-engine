output "backend_url" {
  description = "URL of the backend Cloud Run service"
  value       = google_cloud_run_service.backend.status[0].url
}

output "frontend_url" {
  description = "URL of the frontend Cloud Run service"
  value       = google_cloud_run_service.frontend.status[0].url
}

output "backend_service_account" {
  description = "Email of the backend service account"
  value       = google_service_account.backend.email
}

output "frontend_service_account" {
  description = "Email of the frontend service account"
  value       = google_service_account.frontend.email
}

output "db_instance_connection_name" {
  description = "Cloud SQL instance connection name"
  value       = google_sql_database_instance.main.connection_name
}

output "pubsub_topic" {
  description = "Pub/Sub topic name"
  value       = google_pubsub_topic.jobs.name
}

output "pubsub_subscription" {
  description = "Pub/Sub subscription name"
  value       = google_pubsub_subscription.jobs.name
}

output "next_steps" {
  description = "Next steps after Terraform apply"
  value       = <<-EOT
  
  Deployment complete! Next steps:
  
  1. Add OpenAI API key to Secret Manager:
     echo -n "your-api-key" | gcloud secrets versions add openai-api-key --data-file=-
  
  2. Run database migrations:
     cloud_sql_proxy -instances=${google_sql_database_instance.main.connection_name}=tcp:5432 &
     alembic upgrade head
     pkill cloud_sql_proxy
  
  3. Enable IAP for frontend (via Console):
     - Navigate to Security > Identity-Aware Proxy
     - Select service: ${google_cloud_run_service.frontend.name}
     - Toggle IAP to "On"
     - Add authorized users
  
  4. Test backend health:
     curl -H "Authorization: Bearer $(gcloud auth print-identity-token --impersonate-service-account=${google_service_account.frontend.email} --audiences=${google_cloud_run_service.backend.status[0].url})" \
       ${google_cloud_run_service.backend.status[0].url}/health
  
  5. Access frontend:
     ${google_cloud_run_service.frontend.status[0].url}
  
  For more details, see: infra/cloudrun/README.md
  EOT
}
