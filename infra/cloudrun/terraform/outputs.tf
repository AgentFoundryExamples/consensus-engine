# ==============================================================================
# Service Outputs
# ==============================================================================

output "backend_url" {
  description = "URL of the backend Cloud Run service"
  value       = google_cloud_run_service.backend.status[0].url
}

output "frontend_url" {
  description = "URL of the frontend Cloud Run service"
  value       = google_cloud_run_service.frontend.status[0].url
}

output "worker_url" {
  description = "URL of the worker Cloud Run service (internal use only)"
  value       = google_cloud_run_service.worker.status[0].url
}

# ==============================================================================
# Service Account Outputs
# ==============================================================================

output "backend_service_account" {
  description = "Email of the backend service account"
  value       = google_service_account.backend.email
}

output "frontend_service_account" {
  description = "Email of the frontend service account"
  value       = google_service_account.frontend.email
}

output "worker_service_account" {
  description = "Email of the worker service account"
  value       = google_service_account.worker.email
}

# ==============================================================================
# Database Outputs
# ==============================================================================

output "db_instance_name" {
  description = "Cloud SQL instance name"
  value       = local.db_instance_name
}

output "db_instance_connection_name" {
  description = "Cloud SQL instance connection name (format: project:region:instance)"
  value       = local.db_connection_name
}

output "db_name" {
  description = "Database name within the Cloud SQL instance"
  value       = var.db_name
}

# ==============================================================================
# Pub/Sub Outputs
# ==============================================================================

output "pubsub_topic" {
  description = "Pub/Sub topic name for job queue"
  value       = local.pubsub_topic_name
}

output "pubsub_subscription" {
  description = "Pub/Sub subscription name for worker"
  value       = local.pubsub_subscription_name
}

# ==============================================================================
# Artifact Registry Outputs
# ==============================================================================

output "artifact_registry_repository" {
  description = "Artifact Registry repository name"
  value       = var.artifact_registry_repository
}

output "artifact_registry_path" {
  description = "Full path to Artifact Registry repository for pushing images"
  value       = local.artifact_registry_path
}

# ==============================================================================
# Deployment Information
# ==============================================================================

output "project_id" {
  description = "GCP Project ID where resources were deployed"
  value       = var.project_id
}

output "region" {
  description = "GCP region where resources were deployed"
  value       = var.region
}

output "environment" {
  description = "Environment name (development, staging, production)"
  value       = var.environment
}

# ==============================================================================
# Next Steps Output
# ==============================================================================

output "next_steps" {
  description = "Next steps after Terraform apply"
  value       = <<-EOT
  
  ============================================================================
  Deployment complete! Follow these steps to finalize your setup:
  ============================================================================
  
  1. ADD OPENAI API KEY TO SECRET MANAGER:
     ${var.create_secrets ? "echo -n \"your-api-key\" | gcloud secrets versions add ${var.openai_secret_name} --data-file=-" : "Secret already exists. Update if needed with: gcloud secrets versions add ${var.openai_secret_name} --data-file=-"}
  
  ${var.create_anthropic_secret ? "2. ADD ANTHROPIC API KEY (if using Anthropic models):\n     echo -n \"your-anthropic-key\" | gcloud secrets versions add ${var.anthropic_secret_name} --data-file=-\n  " : ""}
  
  2. RUN DATABASE MIGRATIONS:
     # Download Cloud SQL proxy
     curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.linux.amd64
     chmod +x cloud-sql-proxy
     
     # Start proxy with IAM authentication
     ./cloud-sql-proxy ${local.db_connection_name} --port 5432 --impersonate-service-account="${google_service_account.backend.email}" &
     
     # Run migrations
     export DATABASE_URL="postgresql://${var.db_iam_auth ? "${trimsuffix(google_service_account.backend.email, ".gserviceaccount.com")}" : var.db_user}:@localhost:5432/${var.db_name}"
     alembic upgrade head
     
     # Stop proxy
     pkill cloud-sql-proxy
  
  3. CONFIGURE CORS FOR BACKEND:
     Backend CORS is already configured with frontend URL: ${google_cloud_run_service.frontend.status[0].url}
     ${var.cors_allow_headers != "*" ? "CORS headers restricted to: ${var.cors_allow_headers}" : "WARNING: CORS headers set to '*' - restrict in production!"}
  
  4. ENABLE IAP FOR FRONTEND (via Console):
     - Navigate to: https://console.cloud.google.com/security/iap?project=${var.project_id}
     - Enable IAP API if not already enabled
     - Configure OAuth consent screen (Internal for org-only access)
     - Find Cloud Run service: ${var.frontend_service_name}
     - Toggle IAP to "On"
     - Add authorized users with role: IAP-secured Web App User
  
  5. TEST BACKEND HEALTH:
     curl -H "Authorization: Bearer $(gcloud auth print-identity-token --impersonate-service-account=${google_service_account.frontend.email} --audiences=${google_cloud_run_service.backend.status[0].url})" \
       ${google_cloud_run_service.backend.status[0].url}/health
  
  6. TEST FRONTEND ACCESS:
     ${google_cloud_run_service.frontend.status[0].url}
  
  7. TEST FULL PIPELINE (submit a job):
     curl -X POST ${google_cloud_run_service.backend.status[0].url}/v1/full-review \
       -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
       -H "Content-Type: application/json" \
       -d '{"idea":"Build a REST API for user management with authentication."}'
     
     # Poll for results with returned run_id:
     curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
       ${google_cloud_run_service.backend.status[0].url}/v1/runs/{run_id}
  
  ============================================================================
  Service URLs:
  ============================================================================
  Backend:  ${google_cloud_run_service.backend.status[0].url}
  Frontend: ${google_cloud_run_service.frontend.status[0].url}
  Worker:   ${google_cloud_run_service.worker.status[0].url} (internal)
  
  ============================================================================
  Important Notes:
  ============================================================================
  - Backend and worker use IAM authentication (no public access)
  - Frontend allows unauthenticated access (protect with IAP)
  - Worker processes jobs from Pub/Sub subscription: ${local.pubsub_subscription_name}
  - Database connection: ${local.db_connection_name}
  - All secrets must be added to Secret Manager manually
  ${var.db_deletion_protection ? "- Database deletion protection is ENABLED - disable before destroying" : "- WARNING: Database deletion protection is DISABLED"}
  
  For more details, see:
  - infra/cloudrun/terraform/README.md (Terraform usage and state management)
  - infra/cloudrun/README.md (Manual deployment and troubleshooting)
  - docs/GCP_DEPLOYMENT_ARCHITECTURE.md (Complete architecture guide)
  ============================================================================
  EOT
}

# ==============================================================================
# Warning Outputs
# ==============================================================================

output "warnings" {
  description = "Important warnings about configuration"
  value = concat(
    var.db_deletion_protection ? [] : ["WARNING: Database deletion protection is DISABLED - data will be lost on 'terraform destroy'"],
    var.cors_allow_headers == "*" ? ["WARNING: CORS headers set to '*' - restrict to specific headers in production for security"] : [],
    var.frontend_min_instances == "0" ? ["INFO: Frontend min instances is 0 (scale-to-zero) - may have cold start latency"] : [],
    var.backend_min_instances == "0" ? ["WARNING: Backend min instances is 0 - may have cold start latency and job enqueue delays"] : [],
    var.worker_min_instances == "0" ? ["WARNING: Worker min instances is 0 - jobs may experience delays due to cold starts"] : [],
    !var.db_iam_auth ? ["WARNING: Database using password authentication instead of IAM - IAM is recommended for production"] : [],
  )
}
