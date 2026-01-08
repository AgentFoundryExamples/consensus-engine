# Example Terraform configuration for Consensus Engine
# This is a starting point - customize for your needs
#
# NOTE: This configuration deploys both frontend and backend services.
# The backend CORS_ORIGINS uses the frontend service URL dynamically,
# which resolves the circular dependency by referencing the frontend
# resource directly rather than constructing the URL manually.

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  
  # Uncomment to use remote state (recommended for production)
  # backend "gcs" {
  #   bucket = "your-terraform-state-bucket"
  #   prefix = "consensus-engine/prod"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Local values for resource references (support both created and existing resources)
locals {
  db_instance_name        = var.create_cloud_sql ? google_sql_database_instance.main[0].name : var.db_instance_name
  db_connection_name      = var.create_cloud_sql ? google_sql_database_instance.main[0].connection_name : "${var.project_id}:${var.region}:${var.db_instance_name}"
  pubsub_topic_name       = var.create_pubsub ? google_pubsub_topic.jobs[0].name : var.pubsub_topic_name
  pubsub_subscription_name = var.create_pubsub ? google_pubsub_subscription.jobs[0].name : var.pubsub_subscription_name
  artifact_registry_path  = var.create_artifact_registry ? "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repository}" : "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repository}"
}

# Artifact Registry Repository
resource "google_artifact_registry_repository" "consensus_engine" {
  count = var.create_artifact_registry ? 1 : 0

  location      = var.region
  repository_id = var.artifact_registry_repository
  description   = "Consensus Engine container images"
  format        = "DOCKER"
}

# Service Accounts
resource "google_service_account" "backend" {
  account_id   = "consensus-api-sa"
  display_name = "Consensus Engine API Backend"
  description  = "Service account for Consensus Engine API backend"
}

resource "google_service_account" "frontend" {
  account_id   = "consensus-web-sa"
  display_name = "Consensus Engine Web Frontend"
  description  = "Service account for Consensus Engine web frontend"
}

resource "google_service_account" "worker" {
  account_id   = "consensus-worker-sa"
  display_name = "Consensus Engine Pipeline Worker"
  description  = "Service account for Consensus Engine pipeline worker"
}

# Cloud SQL Instance
resource "google_sql_database_instance" "main" {
  count = var.create_cloud_sql ? 1 : 0

  name             = var.db_instance_name
  database_version = "POSTGRES_16"
  region           = var.region
  
  settings {
    tier      = var.db_tier
    disk_size = var.db_disk_size
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = var.db_private_network  # Set if using VPC
    }
    
    backup_configuration {
      enabled    = true
      start_time = "03:00"
    }
  }
  
  deletion_protection = var.db_deletion_protection
}

# Database
resource "google_sql_database" "consensus_engine" {
  count = var.create_cloud_sql ? 1 : 0

  name     = var.db_name
  instance = local.db_instance_name
}

# IAM Database User for backend service account
resource "google_sql_user" "backend" {
  count = var.create_cloud_sql && var.db_iam_auth ? 1 : 0

  name     = trimsuffix(google_service_account.backend.email, ".gserviceaccount.com")
  instance = local.db_instance_name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
}

# IAM Database User for worker service account
resource "google_sql_user" "worker" {
  count = var.create_cloud_sql && var.db_iam_auth ? 1 : 0

  name     = trimsuffix(google_service_account.worker.email, ".gserviceaccount.com")
  instance = local.db_instance_name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
}

# Pub/Sub Topic
resource "google_pubsub_topic" "jobs" {
  count = var.create_pubsub ? 1 : 0

  name = var.pubsub_topic_name
}

# Pub/Sub Subscription
resource "google_pubsub_subscription" "jobs" {
  count = var.create_pubsub ? 1 : 0

  name  = var.pubsub_subscription_name
  topic = local.pubsub_topic_name
  
  ack_deadline_seconds = var.pubsub_ack_deadline_seconds
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
  
  dynamic "dead_letter_policy" {
    for_each = var.create_pubsub ? [1] : []
    content {
      dead_letter_topic     = google_pubsub_topic.dead_letter[0].id
      max_delivery_attempts = var.pubsub_max_delivery_attempts
    }
  }
}

# Dead Letter Topic
resource "google_pubsub_topic" "dead_letter" {
  count = var.create_pubsub ? 1 : 0

  name = "${var.pubsub_topic_name}-dead-letter"
}

# Secret for OpenAI API Key
resource "google_secret_manager_secret" "openai_key" {
  count = var.create_secrets ? 1 : 0

  secret_id = var.openai_secret_name
  
  replication {
    automatic = true
  }
}

# Optional: Secret for Anthropic API Key
resource "google_secret_manager_secret" "anthropic_key" {
  count = var.create_secrets && var.create_anthropic_secret ? 1 : 0

  secret_id = var.anthropic_secret_name
  
  replication {
    automatic = true
  }
}

# Secret version (you'll need to add the actual secret value separately)
# gcloud secrets versions add openai-api-key --data-file=-
# (paste your API key and press Ctrl+D)

# IAM Bindings
resource "google_project_iam_member" "backend_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_project_iam_member" "worker_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_pubsub_topic_iam_member" "backend_publisher" {
  project = var.project_id
  topic   = local.pubsub_topic_name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_pubsub_subscription_iam_member" "worker_subscriber" {
  project      = var.project_id
  subscription = local.pubsub_subscription_name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_secret_manager_secret_iam_member" "backend_secret_accessor" {
  count = var.create_secrets ? 1 : 0

  project   = var.project_id
  secret_id = google_secret_manager_secret.openai_key[0].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_secret_manager_secret_iam_member" "worker_secret_accessor" {
  count = var.create_secrets ? 1 : 0

  project   = var.project_id
  secret_id = google_secret_manager_secret.openai_key[0].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_secret_manager_secret_iam_member" "backend_anthropic_secret_accessor" {
  count = var.create_secrets && var.create_anthropic_secret ? 1 : 0

  project   = var.project_id
  secret_id = google_secret_manager_secret.anthropic_key[0].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_secret_manager_secret_iam_member" "worker_anthropic_secret_accessor" {
  count = var.create_secrets && var.create_anthropic_secret ? 1 : 0

  project   = var.project_id
  secret_id = google_secret_manager_secret.anthropic_key[0].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.worker.email}"
}

# Cloud Run Service - Backend
resource "google_cloud_run_service" "backend" {
  name     = var.backend_service_name
  location = var.region
  
  template {
    spec {
      service_account_name = google_service_account.backend.email
      container_concurrency = var.backend_concurrency
      timeout_seconds       = var.backend_timeout_seconds
      
      containers {
        image = var.backend_image
        
        ports {
          container_port = 8000
        }
        
        resources {
          limits = {
            cpu    = var.backend_cpu
            memory = var.backend_memory
          }
        }
        
        env {
          name  = "ENV"
          value = var.environment
        }
        
        env {
          name  = "OPENAI_MODEL"
          value = var.openai_model
        }
        
        env {
          name  = "TEMPERATURE"
          value = var.temperature
        }
        
        env {
          name  = "EXPAND_MODEL"
          value = var.expand_model
        }
        
        env {
          name  = "EXPAND_TEMPERATURE"
          value = var.expand_temperature
        }
        
        env {
          name  = "REVIEW_MODEL"
          value = var.review_model
        }
        
        env {
          name  = "REVIEW_TEMPERATURE"
          value = var.review_temperature
        }
        
        env {
          name  = "CORS_ORIGINS"
          value = google_cloud_run_service.frontend.status[0].url
        }
        
        env {
          name  = "CORS_ALLOW_HEADERS"
          value = var.cors_allow_headers
        }
        
        env {
          name  = "USE_CLOUD_SQL_CONNECTOR"
          value = "true"
        }
        
        env {
          name  = "DB_INSTANCE_CONNECTION_NAME"
          value = local.db_connection_name
        }
        
        env {
          name  = "DB_NAME"
          value = var.db_name
        }
        
        env {
          name  = "DB_USER"
          value = var.db_iam_auth ? trimsuffix(google_service_account.backend.email, ".gserviceaccount.com") : var.db_user
        }
        
        env {
          name  = "DB_IAM_AUTH"
          value = var.db_iam_auth ? "true" : "false"
        }
        
        env {
          name  = "PUBSUB_PROJECT_ID"
          value = var.project_id
        }
        
        env {
          name  = "PUBSUB_TOPIC"
          value = local.pubsub_topic_name
        }
        
        dynamic "env" {
          for_each = var.create_secrets ? [1] : []
          content {
            name = "OPENAI_API_KEY"
            value_from {
              secret_key_ref {
                name = google_secret_manager_secret.openai_key[0].secret_id
                key  = "latest"
              }
            }
          }
        }
        
        dynamic "env" {
          for_each = var.create_secrets && var.create_anthropic_secret ? [1] : []
          content {
            name = "ANTHROPIC_API_KEY"
            value_from {
              secret_key_ref {
                name = google_secret_manager_secret.anthropic_key[0].secret_id
                key  = "latest"
              }
            }
          }
        }
      }
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"        = var.backend_min_instances
        "autoscaling.knative.dev/maxScale"        = var.backend_max_instances
        "run.googleapis.com/cloudsql-instances"   = local.db_connection_name
        "run.googleapis.com/cpu-throttling"       = var.backend_cpu_throttling ? "true" : "false"
        "run.googleapis.com/execution-environment" = "gen2"
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
  
  depends_on = [
    google_project_iam_member.backend_cloudsql,
    google_pubsub_topic_iam_member.backend_publisher,
  ]
}

# IAM policy for backend - no unauthenticated access
data "google_iam_policy" "backend_noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "serviceAccount:${google_service_account.frontend.email}",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "backend" {
  location    = google_cloud_run_service.backend.location
  project     = google_cloud_run_service.backend.project
  service     = google_cloud_run_service.backend.name
  policy_data = data.google_iam_policy.backend_noauth.policy_data
}

# Cloud Run Service - Frontend
resource "google_cloud_run_service" "frontend" {
  name     = var.frontend_service_name
  location = var.region
  
  template {
    spec {
      service_account_name  = google_service_account.frontend.email
      container_concurrency = var.frontend_concurrency
      timeout_seconds       = var.frontend_timeout_seconds
      
      containers {
        image = var.frontend_image
        
        ports {
          container_port = 8080
        }
        
        env {
          name  = "VITE_API_BASE_URL"
          value = google_cloud_run_service.backend.status[0].url
        }
        
        env {
          name  = "VITE_ENVIRONMENT"
          value = var.environment
        }
        
        env {
          name  = "VITE_POLLING_INTERVAL_MS"
          value = var.vite_polling_interval_ms
        }
        
        resources {
          limits = {
            cpu    = var.frontend_cpu
            memory = var.frontend_memory
          }
        }
      }
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"        = var.frontend_min_instances
        "autoscaling.knative.dev/maxScale"        = var.frontend_max_instances
        "run.googleapis.com/cpu-throttling"       = var.frontend_cpu_throttling ? "true" : "false"
        "run.googleapis.com/execution-environment" = "gen2"
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Cloud Run Service - Worker
resource "google_cloud_run_service" "worker" {
  name     = var.worker_service_name
  location = var.region
  
  template {
    spec {
      service_account_name  = google_service_account.worker.email
      container_concurrency = var.worker_concurrency
      timeout_seconds       = var.worker_timeout_seconds
      
      containers {
        image = var.worker_image
        
        ports {
          container_port = 8080
        }
        
        resources {
          limits = {
            cpu    = var.worker_cpu
            memory = var.worker_memory
          }
        }
        
        env {
          name  = "ENV"
          value = var.environment
        }
        
        env {
          name  = "OPENAI_MODEL"
          value = var.openai_model
        }
        
        env {
          name  = "TEMPERATURE"
          value = var.temperature
        }
        
        env {
          name  = "EXPAND_MODEL"
          value = var.expand_model
        }
        
        env {
          name  = "EXPAND_TEMPERATURE"
          value = var.expand_temperature
        }
        
        env {
          name  = "REVIEW_MODEL"
          value = var.review_model
        }
        
        env {
          name  = "REVIEW_TEMPERATURE"
          value = var.review_temperature
        }
        
        env {
          name  = "USE_CLOUD_SQL_CONNECTOR"
          value = "true"
        }
        
        env {
          name  = "DB_INSTANCE_CONNECTION_NAME"
          value = local.db_connection_name
        }
        
        env {
          name  = "DB_NAME"
          value = var.db_name
        }
        
        env {
          name  = "DB_USER"
          value = var.db_iam_auth ? trimsuffix(google_service_account.worker.email, ".gserviceaccount.com") : var.db_user
        }
        
        env {
          name  = "DB_IAM_AUTH"
          value = var.db_iam_auth ? "true" : "false"
        }
        
        env {
          name  = "PUBSUB_PROJECT_ID"
          value = var.project_id
        }
        
        env {
          name  = "PUBSUB_SUBSCRIPTION"
          value = local.pubsub_subscription_name
        }
        
        env {
          name  = "WORKER_MAX_CONCURRENCY"
          value = var.worker_max_concurrency
        }
        
        env {
          name  = "WORKER_ACK_DEADLINE_SECONDS"
          value = var.worker_ack_deadline_seconds
        }
        
        env {
          name  = "WORKER_STEP_TIMEOUT_SECONDS"
          value = var.worker_step_timeout_seconds
        }
        
        env {
          name  = "WORKER_JOB_TIMEOUT_SECONDS"
          value = var.worker_job_timeout_seconds
        }
        
        dynamic "env" {
          for_each = var.create_secrets ? [1] : []
          content {
            name = "OPENAI_API_KEY"
            value_from {
              secret_key_ref {
                name = google_secret_manager_secret.openai_key[0].secret_id
                key  = "latest"
              }
            }
          }
        }
        
        dynamic "env" {
          for_each = var.create_secrets && var.create_anthropic_secret ? [1] : []
          content {
            name = "ANTHROPIC_API_KEY"
            value_from {
              secret_key_ref {
                name = google_secret_manager_secret.anthropic_key[0].secret_id
                key  = "latest"
              }
            }
          }
        }
      }
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"        = var.worker_min_instances
        "autoscaling.knative.dev/maxScale"        = var.worker_max_instances
        "run.googleapis.com/cloudsql-instances"   = local.db_connection_name
        "run.googleapis.com/cpu-throttling"       = var.worker_cpu_throttling ? "true" : "false"
        "run.googleapis.com/execution-environment" = "gen2"
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
  
  depends_on = [
    google_project_iam_member.worker_cloudsql,
    google_pubsub_subscription_iam_member.worker_subscriber,
  ]
}

# IAM policy for frontend - allow unauthenticated (IAP will handle auth)
data "google_iam_policy" "frontend_allauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "frontend" {
  location    = google_cloud_run_service.frontend.location
  project     = google_cloud_run_service.frontend.project
  service     = google_cloud_run_service.frontend.name
  policy_data = data.google_iam_policy.frontend_allauth.policy_data
}

# IAM policy for worker - no unauthenticated access
data "google_iam_policy" "worker_noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "serviceAccount:${google_service_account.worker.email}",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "worker" {
  location    = google_cloud_run_service.worker.location
  project     = google_cloud_run_service.worker.project
  service     = google_cloud_run_service.worker.name
  policy_data = data.google_iam_policy.worker_noauth.policy_data
}

# Data source for project info
data "google_project" "project" {
  project_id = var.project_id
}
