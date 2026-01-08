# Example Terraform configuration for Consensus Engine
# This is a starting point - customize for your needs

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

# Cloud SQL Instance
resource "google_sql_database_instance" "main" {
  name             = var.db_instance_name
  database_version = "POSTGRES_16"
  region           = var.region
  
  settings {
    tier      = var.db_tier
    disk_size = 10
    
    ip_configuration {
      ipv4_enabled    = false
      private_network = null  # Set if using VPC
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
  name     = "consensus_engine"
  instance = google_sql_database_instance.main.name
}

# IAM Database User for backend service account
resource "google_sql_user" "backend" {
  name     = trimsuffix(google_service_account.backend.email, ".gserviceaccount.com")
  instance = google_sql_database_instance.main.name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"
}

# Pub/Sub Topic
resource "google_pubsub_topic" "jobs" {
  name = "consensus-engine-jobs"
}

# Pub/Sub Subscription
resource "google_pubsub_subscription" "jobs" {
  name  = "consensus-engine-jobs-sub"
  topic = google_pubsub_topic.jobs.name
  
  ack_deadline_seconds = 600
  
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
  
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5
  }
}

# Dead Letter Topic
resource "google_pubsub_topic" "dead_letter" {
  name = "consensus-engine-jobs-dead-letter"
}

# Secret for OpenAI API Key
resource "google_secret_manager_secret" "openai_key" {
  secret_id = "openai-api-key"
  
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

resource "google_pubsub_topic_iam_member" "backend_publisher" {
  project = var.project_id
  topic   = google_pubsub_topic.jobs.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_secret_manager_secret_iam_member" "backend_secret_accessor" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.openai_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}

# Cloud Run Service - Backend
resource "google_cloud_run_service" "backend" {
  name     = var.backend_service_name
  location = var.region
  
  template {
    spec {
      service_account_name = google_service_account.backend.email
      
      containers {
        image = var.backend_image
        
        ports {
          container_port = 8000
        }
        
        env {
          name  = "ENV"
          value = var.environment
        }
        
        env {
          name  = "OPENAI_MODEL"
          value = "gpt-5.1"
        }
        
        env {
          name  = "CORS_ORIGINS"
          value = "https://${var.frontend_service_name}-${data.google_project.project.number}.${var.region}.run.app"
        }
        
        env {
          name  = "USE_CLOUD_SQL_CONNECTOR"
          value = "true"
        }
        
        env {
          name  = "DB_INSTANCE_CONNECTION_NAME"
          value = "${var.project_id}:${var.region}:${var.db_instance_name}"
        }
        
        env {
          name  = "DB_NAME"
          value = "consensus_engine"
        }
        
        env {
          name  = "DB_USER"
          value = trimsuffix(google_service_account.backend.email, ".gserviceaccount.com")
        }
        
        env {
          name  = "DB_IAM_AUTH"
          value = "true"
        }
        
        env {
          name  = "PUBSUB_PROJECT_ID"
          value = var.project_id
        }
        
        env {
          name  = "PUBSUB_TOPIC"
          value = google_pubsub_topic.jobs.name
        }
        
        env {
          name = "OPENAI_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.openai_key.secret_id
              key  = "latest"
            }
          }
        }
        
        resources {
          limits = {
            cpu    = "2000m"
            memory = "2Gi"
          }
        }
      }
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"        = var.backend_min_instances
        "autoscaling.knative.dev/maxScale"        = var.backend_max_instances
        "run.googleapis.com/cloudsql-instances"   = "${var.project_id}:${var.region}:${var.db_instance_name}"
        "run.googleapis.com/cpu-throttling"       = "false"
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
    google_secret_manager_secret_iam_member.backend_secret_accessor,
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
      service_account_name = google_service_account.frontend.email
      
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
          value = "5000"
        }
        
        resources {
          limits = {
            cpu    = "1000m"
            memory = "512Mi"
          }
        }
      }
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"        = var.frontend_min_instances
        "autoscaling.knative.dev/maxScale"        = var.frontend_max_instances
        "run.googleapis.com/cpu-throttling"       = "true"
        "run.googleapis.com/execution-environment" = "gen2"
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
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

# Data source for project info
data "google_project" "project" {
  project_id = var.project_id
}
