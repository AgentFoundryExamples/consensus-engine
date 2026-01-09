# ==============================================================================
# Core Project Variables
# ==============================================================================

variable "project_id" {
  description = "GCP Project ID where resources will be created"
  type        = string
}

variable "region" {
  description = "GCP region for resources (e.g., us-central1, us-east1)"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "production"
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be one of: development, staging, production."
  }
}

# ==============================================================================
# Resource Creation Flags
# ==============================================================================

variable "create_artifact_registry" {
  description = "Whether to create Artifact Registry repository (set to false if using existing repository)"
  type        = bool
  default     = true
}

variable "create_cloud_sql" {
  description = "Whether to create Cloud SQL instance (set to false if using existing instance)"
  type        = bool
  default     = true
}

variable "create_pubsub" {
  description = "Whether to create Pub/Sub topic and subscription (set to false if using existing resources)"
  type        = bool
  default     = true
}

variable "create_secrets" {
  description = "Whether to create Secret Manager secrets (set to false if using existing secrets)"
  type        = bool
  default     = true
}

# ==============================================================================
# Artifact Registry Configuration
# ==============================================================================

variable "artifact_registry_repository" {
  description = "Name of the Artifact Registry repository for Docker images"
  type        = string
  default     = "consensus-engine"
}

# ==============================================================================
# Service Names
# ==============================================================================

variable "backend_service_name" {
  description = "Name for the backend Cloud Run service"
  type        = string
  default     = "consensus-api"
}

variable "frontend_service_name" {
  description = "Name for the frontend Cloud Run service"
  type        = string
  default     = "consensus-web"
}

variable "worker_service_name" {
  description = "Name for the worker Cloud Run service"
  type        = string
  default     = "consensus-worker"
}

# ==============================================================================
# Container Images
# ==============================================================================

variable "backend_image" {
  description = "Container image for backend API service. Example: us-central1-docker.pkg.dev/PROJECT_ID/consensus-engine/consensus-api:latest"
  type        = string
}

variable "frontend_image" {
  description = "Container image for frontend web service. Example: us-central1-docker.pkg.dev/PROJECT_ID/consensus-engine/consensus-web:latest"
  type        = string
}

variable "worker_image" {
  description = "Container image for pipeline worker service. Example: us-central1-docker.pkg.dev/PROJECT_ID/consensus-engine/consensus-worker:latest"
  type        = string
}

# ==============================================================================
# Cloud SQL Configuration
# ==============================================================================

variable "db_instance_name" {
  description = "Name for Cloud SQL instance (used for both creating new instance and referencing existing one)"
  type        = string
  default     = "consensus-db"
}

variable "db_name" {
  description = "Database name within the Cloud SQL instance"
  type        = string
  default     = "consensus_engine"
}

variable "db_tier" {
  description = "Cloud SQL instance tier (e.g., db-f1-micro, db-g1-small, db-n1-standard-1)"
  type        = string
  default     = "db-f1-micro"
}

variable "db_disk_size" {
  description = "Cloud SQL disk size in GB"
  type        = number
  default     = 10
}

variable "db_private_network" {
  description = "VPC network for private IP (leave null for public IP with authorized networks). Example: projects/PROJECT_ID/global/networks/default"
  type        = string
  default     = null
}

variable "db_deletion_protection" {
  description = "Enable deletion protection for Cloud SQL instance to prevent accidental deletion"
  type        = bool
  default     = true
}

variable "db_iam_auth" {
  description = "Use IAM authentication for Cloud SQL (recommended for production, no passwords needed)"
  type        = bool
  default     = true
}

variable "db_user" {
  description = "Database user (only used when db_iam_auth=false for password-based authentication)"
  type        = string
  default     = "postgres"
}

# ==============================================================================
# Pub/Sub Configuration
# ==============================================================================

variable "pubsub_topic_name" {
  description = "Pub/Sub topic name for job queue (used for both creating new topic and referencing existing one)"
  type        = string
  default     = "consensus-engine-jobs"
}

variable "pubsub_subscription_name" {
  description = "Pub/Sub subscription name for worker (used for both creating new subscription and referencing existing one)"
  type        = string
  default     = "consensus-engine-jobs-sub"
}

variable "pubsub_ack_deadline_seconds" {
  description = "Pub/Sub acknowledgment deadline in seconds (10-600)"
  type        = number
  default     = 600
  validation {
    condition     = var.pubsub_ack_deadline_seconds >= 10 && var.pubsub_ack_deadline_seconds <= 600
    error_message = "Pub/Sub ack deadline must be between 10 and 600 seconds."
  }
}

variable "pubsub_max_delivery_attempts" {
  description = "Maximum delivery attempts before moving message to dead letter queue (5-100)"
  type        = number
  default     = 5
  validation {
    condition     = var.pubsub_max_delivery_attempts >= 5 && var.pubsub_max_delivery_attempts <= 100
    error_message = "Max delivery attempts must be between 5 and 100."
  }
}

# ==============================================================================
# Secret Manager Configuration
# ==============================================================================

variable "openai_secret_name" {
  description = "Secret Manager secret name for OpenAI API key"
  type        = string
  default     = "openai-api-key"
}

variable "create_anthropic_secret" {
  description = "Whether to create Anthropic API key secret (optional, for future multi-LLM support)"
  type        = bool
  default     = false
}

variable "anthropic_secret_name" {
  description = "Secret Manager secret name for Anthropic API key (only used if create_anthropic_secret=true)"
  type        = string
  default     = "anthropic-api-key"
}

# ==============================================================================
# LLM Configuration
# ==============================================================================

variable "openai_model" {
  description = "Default OpenAI model to use (e.g., gpt-4, gpt-4-turbo, gpt-4o). Note: gpt-5.1 is a target model for future use; gpt-4 is used as the default."
  type        = string
  default     = "gpt-4"
}

variable "temperature" {
  description = "Default temperature for LLM responses (0.0-1.0, lower is more deterministic)"
  type        = string
  default     = "0.7"
}

variable "expand_model" {
  description = "Model for expansion step (defaults to openai_model if not specified)"
  type        = string
  default     = "gpt-4"
}

variable "expand_temperature" {
  description = "Temperature for expansion step (0.0-1.0)"
  type        = string
  default     = "0.7"
}

variable "review_model" {
  description = "Model for review step (defaults to openai_model if not specified)"
  type        = string
  default     = "gpt-4"
}

variable "review_temperature" {
  description = "Temperature for review step (0.0-1.0, recommended 0.2 for consistent reviews)"
  type        = string
  default     = "0.2"
}

# ==============================================================================
# CORS Configuration
# ==============================================================================

variable "cors_allow_headers" {
  description = "Comma-separated list of allowed CORS headers. For production, specify explicit headers. Use '*' only for development."
  type        = string
  default     = "Content-Type,Authorization,X-Request-ID,X-Schema-Version,X-Prompt-Set-Version"
}

# ==============================================================================
# Frontend Configuration
# ==============================================================================

variable "vite_polling_interval_ms" {
  description = "Frontend polling interval in milliseconds for checking job status"
  type        = string
  default     = "5000"
}

# ==============================================================================
# Backend Service Configuration
# ==============================================================================

variable "backend_min_instances" {
  description = "Minimum number of backend instances (0 for scale-to-zero, 1+ for always-on)"
  type        = string
  default     = "1"
}

variable "backend_max_instances" {
  description = "Maximum number of backend instances (controls cost and concurrency)"
  type        = string
  default     = "20"
}

variable "backend_cpu" {
  description = "CPU allocation for backend service (e.g., 1000m, 2000m, 4000m)"
  type        = string
  default     = "2000m"
}

variable "backend_memory" {
  description = "Memory allocation for backend service (e.g., 512Mi, 1Gi, 2Gi, 4Gi)"
  type        = string
  default     = "2Gi"
}

variable "backend_concurrency" {
  description = "Maximum concurrent requests per backend instance (1-1000)"
  type        = number
  default     = 100
  validation {
    condition     = var.backend_concurrency >= 1 && var.backend_concurrency <= 1000
    error_message = "Backend concurrency must be between 1 and 1000."
  }
}

variable "backend_timeout_seconds" {
  description = "Request timeout for backend service in seconds (1-3600)"
  type        = number
  default     = 300
  validation {
    condition     = var.backend_timeout_seconds >= 1 && var.backend_timeout_seconds <= 3600
    error_message = "Backend timeout must be between 1 and 3600 seconds."
  }
}

variable "backend_cpu_throttling" {
  description = "Enable CPU throttling for backend (true for cost savings, false for consistent performance)"
  type        = bool
  default     = false
}

# ==============================================================================
# Frontend Service Configuration
# ==============================================================================

variable "frontend_min_instances" {
  description = "Minimum number of frontend instances (0 for scale-to-zero, 1+ for always-on)"
  type        = string
  default     = "0"
}

variable "frontend_max_instances" {
  description = "Maximum number of frontend instances"
  type        = string
  default     = "10"
}

variable "frontend_cpu" {
  description = "CPU allocation for frontend service (e.g., 1000m, 2000m)"
  type        = string
  default     = "1000m"
}

variable "frontend_memory" {
  description = "Memory allocation for frontend service (e.g., 512Mi, 1Gi)"
  type        = string
  default     = "512Mi"
}

variable "frontend_concurrency" {
  description = "Maximum concurrent requests per frontend instance (1-1000)"
  type        = number
  default     = 80
  validation {
    condition     = var.frontend_concurrency >= 1 && var.frontend_concurrency <= 1000
    error_message = "Frontend concurrency must be between 1 and 1000."
  }
}

variable "frontend_timeout_seconds" {
  description = "Request timeout for frontend service in seconds (1-3600)"
  type        = number
  default     = 300
  validation {
    condition     = var.frontend_timeout_seconds >= 1 && var.frontend_timeout_seconds <= 3600
    error_message = "Frontend timeout must be between 1 and 3600 seconds."
  }
}

variable "frontend_cpu_throttling" {
  description = "Enable CPU throttling for frontend (true for cost savings with nginx, false for consistent performance)"
  type        = bool
  default     = true
}

# ==============================================================================
# Worker Service Configuration
# ==============================================================================

variable "worker_min_instances" {
  description = "Minimum number of worker instances (1+ recommended to avoid cold starts for job processing)"
  type        = string
  default     = "1"
}

variable "worker_max_instances" {
  description = "Maximum number of worker instances (controls concurrent job processing)"
  type        = string
  default     = "3"
}

variable "worker_cpu" {
  description = "CPU allocation for worker service (e.g., 2000m, 4000m)"
  type        = string
  default     = "2000m"
}

variable "worker_memory" {
  description = "Memory allocation for worker service (e.g., 2Gi, 4Gi)"
  type        = string
  default     = "4Gi"
}

variable "worker_concurrency" {
  description = "Maximum concurrent requests per worker instance (typically 1 for long-running jobs)"
  type        = number
  default     = 1
  validation {
    condition     = var.worker_concurrency >= 1 && var.worker_concurrency <= 1000
    error_message = "Worker concurrency must be between 1 and 1000."
  }
}

variable "worker_timeout_seconds" {
  description = "Request timeout for worker service in seconds (1-3600, recommended 3600 for long jobs)"
  type        = number
  default     = 3600
  validation {
    condition     = var.worker_timeout_seconds >= 1 && var.worker_timeout_seconds <= 3600
    error_message = "Worker timeout must be between 1 and 3600 seconds."
  }
}

variable "worker_cpu_throttling" {
  description = "Enable CPU throttling for worker (false recommended for consistent job processing performance)"
  type        = bool
  default     = false
}

variable "worker_max_concurrency" {
  description = "Maximum concurrent message handlers in worker (1-1000)"
  type        = string
  default     = "10"
}

variable "worker_ack_deadline_seconds" {
  description = "Pub/Sub ack deadline for worker messages in seconds (60-3600, should be >= job timeout)"
  type        = string
  default     = "600"
}

variable "worker_step_timeout_seconds" {
  description = "Timeout for individual pipeline steps in seconds (10-1800)"
  type        = string
  default     = "300"
}

variable "worker_job_timeout_seconds" {
  description = "Overall timeout for job processing in seconds (60-7200)"
  type        = string
  default     = "1800"
}
