variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "production"
}

# Service Names
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

# Container Images
variable "backend_image" {
  description = "Container image for backend (e.g., gcr.io/PROJECT_ID/consensus-api:latest)"
  type        = string
}

variable "frontend_image" {
  description = "Container image for frontend (e.g., gcr.io/PROJECT_ID/consensus-web:latest)"
  type        = string
}

# Database Configuration
variable "db_instance_name" {
  description = "Name for Cloud SQL instance"
  type        = string
  default     = "consensus-db"
}

variable "db_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-f1-micro"
}

variable "db_deletion_protection" {
  description = "Enable deletion protection for Cloud SQL instance"
  type        = bool
  default     = true
}

# Scaling Configuration
variable "backend_min_instances" {
  description = "Minimum number of backend instances"
  type        = string
  default     = "1"
}

variable "backend_max_instances" {
  description = "Maximum number of backend instances"
  type        = string
  default     = "20"
}

variable "frontend_min_instances" {
  description = "Minimum number of frontend instances"
  type        = string
  default     = "0"
}

variable "frontend_max_instances" {
  description = "Maximum number of frontend instances"
  type        = string
  default     = "10"
}
