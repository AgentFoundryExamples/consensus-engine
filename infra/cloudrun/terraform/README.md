# Terraform Configuration Examples

This directory contains example Terraform configurations for provisioning Consensus Engine infrastructure on Google Cloud Platform.

## Overview

These are **example configurations** to help you get started. They are not production-ready and should be customized for your specific requirements.

## Files

- `main.tf` - Main Terraform configuration with core resources
- `variables.tf` - Input variables for customization
- `outputs.tf` - Outputs for service URLs and connection info
- `terraform.tfvars.example` - Example variable values

## Prerequisites

1. **Terraform**: Install Terraform >= 1.5.0
2. **GCP Account**: Active GCP account with billing enabled
3. **gcloud CLI**: Authenticated with `gcloud auth application-default login`
4. **APIs Enabled**: See infra/cloudrun/README.md for required APIs

## Quick Start

```bash
cd infra/cloudrun/terraform

# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your values
vim terraform.tfvars

# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Apply configuration
terraform apply
```

## What Gets Created

- Service accounts for frontend and backend
- Cloud SQL PostgreSQL instance
- Pub/Sub topic and subscription
- Secret Manager secret for OpenAI API key
- Cloud Run services for frontend and backend
- IAM bindings for service-to-service auth

## Customization

Edit `terraform.tfvars` to customize:
- Project ID and region
- Service names
- Resource sizes (CPU, memory, instance types)
- Scaling parameters (min/max instances)
- Environment variables

## State Management

**Important**: For production, use a remote backend to store Terraform state:

```hcl
terraform {
  backend "gcs" {
    bucket = "your-terraform-state-bucket"
    prefix = "consensus-engine/prod"
  }
}
```

## Security Considerations

- Never commit `terraform.tfvars` or `*.tfstate` files to version control
- Use least-privilege IAM roles
- Enable audit logging
- Store sensitive values in Secret Manager
- Use Terraform Cloud/Enterprise for team collaboration

## Maintenance

```bash
# Show current state
terraform show

# List resources
terraform state list

# Refresh state
terraform refresh

# Destroy all resources (be careful!)
terraform destroy
```

## Cost Estimation

Use `terraform plan` output to estimate costs, or use:

```bash
terraform plan -out=plan.tfplan
terraform show -json plan.tfplan | jq . > plan.json
# Upload plan.json to Google Cloud Pricing Calculator
```

## Troubleshooting

### "Error creating Instance: googleapi: Error 409"

Resource already exists. Either:
- Import existing resource: `terraform import google_sql_database_instance.main project/instance`
- Remove from state and manage manually: `terraform state rm google_sql_database_instance.main`

### "quota exceeded" errors

Check quotas in GCP Console and request increases if needed.

### "insufficient_scope" errors

Re-authenticate with broader scopes:
```bash
gcloud auth application-default login --scopes=https://www.googleapis.com/auth/cloud-platform
```

## Additional Resources

- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Cloud Run Terraform Example](https://github.com/terraform-google-modules/terraform-google-cloud-run)
- [GCP Best Practices](https://cloud.google.com/docs/terraform/best-practices-for-terraform)
