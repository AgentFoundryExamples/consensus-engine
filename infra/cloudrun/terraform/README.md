# Terraform Configuration for Consensus Engine on Google Cloud Run

This directory contains Terraform configuration for deploying the Consensus Engine to Google Cloud Platform (GCP) using Cloud Run, Cloud SQL, and Pub/Sub.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [State Management](#state-management)
- [Deployment Workflow](#deployment-workflow)
- [Using Existing Resources](#using-existing-resources)
- [Zero-Downtime Deployments](#zero-downtime-deployments)
- [Teardown and Cleanup](#teardown-and-cleanup)
- [Troubleshooting](#troubleshooting)
- [Cost Estimation](#cost-estimation)
- [Security Considerations](#security-considerations)

## Overview

This Terraform configuration provisions the following resources:

- **Artifact Registry repository** for Docker images
- **Cloud Run services** for API backend, web frontend, and pipeline worker
- **Cloud SQL PostgreSQL instance** with IAM authentication
- **Pub/Sub topic and subscription** for async job processing
- **Secret Manager secrets** for API keys
- **Service accounts** with least-privilege IAM roles
- **IAM bindings** for service-to-service authentication

### What Gets Created

```
┌─────────────────────┐     ┌──────────────────────┐
│ Artifact Registry   │────▶│ Cloud Run Services   │
│ (Docker Images)     │     │ - API Backend        │
└─────────────────────┘     │ - Frontend           │
                            │ - Worker             │
                            └──────────────────────┘
                                     │
                                     ▼
                            ┌──────────────────────┐
                            │ Cloud SQL PostgreSQL │
                            │ (IAM Authentication) │
                            └──────────────────────┘
                                     │
                                     ▼
                            ┌──────────────────────┐
                            │ Pub/Sub Topic + Sub  │
                            │ (Job Queue)          │
                            └──────────────────────┘
                                     │
                                     ▼
                            ┌──────────────────────┐
                            │ Secret Manager       │
                            │ (API Keys)           │
                            └──────────────────────┘
```

## Prerequisites

### Required Tools

1. **Terraform** >= 1.5.0
   ```bash
   # Install Terraform
   curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
   sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
   sudo apt-get update && sudo apt-get install terraform
   
   # Verify installation
   terraform version
   ```

2. **gcloud CLI** (latest version)
   ```bash
   # Install gcloud
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   
   # Initialize and authenticate
   gcloud init
   gcloud auth login
   gcloud auth application-default login
   ```

3. **Docker** (for building images)
   ```bash
   docker --version
   ```

### GCP Project Setup

1. **Create or select a GCP project:**
   ```bash
   export PROJECT_ID="your-project-id"
   gcloud config set project $PROJECT_ID
   ```

2. **Enable required APIs:**
   ```bash
   gcloud services enable \
     run.googleapis.com \
     cloudbuild.googleapis.com \
     artifactregistry.googleapis.com \
     sql-component.googleapis.com \
     sqladmin.googleapis.com \
     pubsub.googleapis.com \
     secretmanager.googleapis.com \
     iap.googleapis.com \
     compute.googleapis.com \
     cloudresourcemanager.googleapis.com
   ```

3. **Grant yourself required permissions:**
   ```bash
   export USER_EMAIL="your-email@example.com"
   
   for role in \
     "roles/run.admin" \
     "roles/iam.serviceAccountAdmin" \
     "roles/iam.serviceAccountUser" \
     "roles/cloudsql.admin" \
     "roles/pubsub.admin" \
     "roles/secretmanager.admin" \
     "roles/artifactregistry.admin"; do
     gcloud projects add-iam-policy-binding $PROJECT_ID \
       --member="user:$USER_EMAIL" \
       --role="$role"
   done
   ```

### External Services

- **OpenAI API Key**: Obtain from https://platform.openai.com/api-keys
- **Anthropic API Key** (optional): For future multi-LLM support

## Quick Start

### 1. Build and Push Docker Images

Before running Terraform, build and push your Docker images to Artifact Registry:

```bash
cd /path/to/consensus-engine
export PROJECT_ID="your-project-id"
export REGION="us-central1"

# Configure Docker authentication
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build and push backend
gcloud builds submit \
  --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/consensus-engine/consensus-api:latest \
  --project=$PROJECT_ID

# Build and push worker
gcloud builds submit \
  --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/consensus-engine/consensus-worker:latest \
  --file Dockerfile.worker \
  --project=$PROJECT_ID

# Build and push frontend
cd webapp
gcloud builds submit \
  --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/consensus-engine/consensus-web:latest \
  --project=$PROJECT_ID
cd ..
```

### 2. Configure Terraform Variables

```bash
cd infra/cloudrun/terraform

# Copy example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
vim terraform.tfvars
```

**Minimum required variables:**
```hcl
project_id     = "your-project-id"
backend_image  = "us-central1-docker.pkg.dev/your-project-id/consensus-engine/consensus-api:latest"
frontend_image = "us-central1-docker.pkg.dev/your-project-id/consensus-engine/consensus-web:latest"
worker_image   = "us-central1-docker.pkg.dev/your-project-id/consensus-engine/consensus-worker:latest"
```

### 3. Initialize Terraform

```bash
terraform init
```

This downloads the Google Cloud provider and initializes the working directory.

### 4. Review the Plan

```bash
terraform plan
```

**Carefully review the output** to ensure:
- Correct resource names and quantities
- No unexpected deletions or replacements
- Image tags are correct
- Database deletion protection is enabled

### 5. Apply Configuration

```bash
terraform apply
```

Type `yes` when prompted to confirm resource creation.

**Expected duration**: 5-10 minutes (Cloud SQL creation is the longest step)

### 6. Post-Deployment Steps

After `terraform apply` completes successfully:

1. **Add OpenAI API key to Secret Manager:**
   ```bash
   echo -n "your-openai-api-key" | gcloud secrets versions add openai-api-key --data-file=-
   ```

2. **Run database migrations:**
   ```bash
   # Download Cloud SQL proxy
   curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.linux.amd64
   chmod +x cloud-sql-proxy
   
   # Start proxy with IAM authentication
   ./cloud-sql-proxy PROJECT_ID:REGION:consensus-db --port 5432 --impersonate-service-account="consensus-api-sa@PROJECT_ID.iam.gserviceaccount.com" &
   
   # Run migrations
   cd /path/to/consensus-engine
   export DATABASE_URL="postgresql://consensus-api-sa@PROJECT_ID.iam:@localhost:5432/consensus_engine"
   alembic upgrade head
   
   # Stop proxy
   pkill cloud-sql-proxy
   ```

3. **Enable IAP for frontend** (via GCP Console):
   - Navigate to Security > Identity-Aware Proxy
   - Find service: `consensus-web`
   - Toggle IAP to "On"
   - Add authorized users

4. **Test the deployment:**
   ```bash
   # Get URLs from Terraform outputs
   export BACKEND_URL=$(terraform output -raw backend_url)
   export FRONTEND_URL=$(terraform output -raw frontend_url)
   
   # Test backend health
   curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" ${BACKEND_URL}/health
   
   # Test frontend
   open $FRONTEND_URL
   ```

## Configuration

### Variable Reference

See `variables.tf` for complete variable documentation. Key categories:

**Resource Creation Flags** (control what gets created vs. referenced):
- `create_artifact_registry` - Create new Artifact Registry repository
- `create_cloud_sql` - Create new Cloud SQL instance
- `create_pubsub` - Create new Pub/Sub topic and subscription
- `create_secrets` - Create new Secret Manager secrets

**Service Configuration**:
- `backend_min_instances`, `backend_max_instances` - API autoscaling
- `worker_min_instances`, `worker_max_instances` - Worker autoscaling
- `backend_cpu`, `backend_memory` - API resource limits
- `worker_cpu`, `worker_memory` - Worker resource limits

**Database Configuration**:
- `db_tier` - Cloud SQL instance size (db-f1-micro to db-n1-standard-N)
- `db_iam_auth` - Enable IAM authentication (recommended)
- `db_deletion_protection` - Prevent accidental deletion

**LLM Configuration**:
- `openai_model` - Default model (e.g., gpt-4, gpt-4-turbo)
- `expand_model`, `review_model` - Step-specific models
- `expand_temperature`, `review_temperature` - Step-specific temperatures

### Customization Examples

**Development environment with scale-to-zero:**
```hcl
environment            = "development"
frontend_min_instances = "0"
backend_min_instances  = "0"
worker_min_instances   = "0"
db_tier                = "db-f1-micro"
db_deletion_protection = false
```

**Production with high availability:**
```hcl
environment            = "production"
backend_min_instances  = "2"
worker_min_instances   = "2"
backend_max_instances  = "50"
worker_max_instances   = "10"
db_tier                = "db-n1-standard-2"
db_deletion_protection = true
```

**Cost-optimized staging:**
```hcl
environment            = "staging"
backend_min_instances  = "1"
worker_min_instances   = "1"
backend_max_instances  = "10"
worker_max_instances   = "3"
db_tier                = "db-g1-small"
```

## State Management

### Local State (Default)

By default, Terraform stores state locally in `terraform.tfstate`. This is suitable for:
- Individual developers
- Quick prototypes
- Testing

**⚠️ Important**: Never commit `terraform.tfstate` to version control.

Add to `.gitignore`:
```
*.tfstate
*.tfstate.*
.terraform/
```

### Remote State (Recommended for Teams)

For team environments, use Google Cloud Storage for remote state with locking:

#### 1. Create a GCS bucket for state:

```bash
export STATE_BUCKET="your-project-id-terraform-state"
export PROJECT_ID="your-project-id"

gsutil mb -p $PROJECT_ID -l us-central1 gs://$STATE_BUCKET/

# Enable versioning for state history
gsutil versioning set on gs://$STATE_BUCKET/

# Restrict access
gsutil iam ch user:your-email@example.com:roles/storage.objectAdmin gs://$STATE_BUCKET/
```

#### 2. Configure backend in `main.tf`:

Uncomment the backend block in `main.tf`:
```hcl
terraform {
  backend "gcs" {
    bucket = "your-project-id-terraform-state"
    prefix = "consensus-engine/prod"
  }
}
```

#### 3. Migrate existing state:

```bash
terraform init -migrate-state
```

### State Locking

State locking is **automatically enabled** when using GCS backend. This prevents:
- Concurrent `terraform apply` operations
- State corruption from simultaneous writes
- Race conditions in team environments

**No additional configuration needed** - locking happens automatically via GCS object versioning.

### Best Practices for State Management

1. **Use separate state files per environment:**
   ```hcl
   # Production
   backend "gcs" {
     bucket = "your-project-terraform-state"
     prefix = "consensus-engine/prod"
   }
   
   # Staging
   backend "gcs" {
     bucket = "your-project-terraform-state"
     prefix = "consensus-engine/staging"
   }
   ```

2. **Enable versioning on state bucket:**
   ```bash
   gsutil versioning set on gs://your-state-bucket/
   ```

3. **Restrict access to state bucket:**
   - Only grant access to CI/CD service accounts and operators
   - Use IAM conditions for fine-grained control

4. **Regular state backups:**
   ```bash
   terraform state pull > backup-$(date +%Y%m%d).tfstate
   ```

5. **Never manually edit state files:**
   - Use `terraform state` commands for modifications
   - Example: `terraform state rm google_cloud_run_service.backend`

## Deployment Workflow

### Standard Deployment

```bash
# 1. Update configuration
vim terraform.tfvars

# 2. Format code
terraform fmt

# 3. Validate configuration
terraform validate

# 4. Review changes
terraform plan -out=tfplan

# 5. Apply changes
terraform apply tfplan

# 6. Verify deployment
export BACKEND_URL=$(terraform output -raw backend_url)
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" ${BACKEND_URL}/health
```

### Updating Service Images

When updating to new Docker image tags:

```bash
# 1. Build and push new images
gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT/repo/consensus-api:v1.2.0

# 2. Update terraform.tfvars
backend_image = "...consensus-api:v1.2.0"

# 3. Review plan (should show Cloud Run service will be updated)
terraform plan

# 4. Apply (Cloud Run creates new revision automatically)
terraform apply

# 5. Verify new revision
gcloud run revisions list --service=consensus-api --region=REGION

# 6. Monitor for issues
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-api" --limit=50
```

### Updating Environment Variables

```bash
# 1. Update variables.tf or terraform.tfvars
expand_temperature = "0.8"

# 2. Plan shows env var change
terraform plan
# Look for: ~ update in-place
#   ~ env {
#       ~ value = "0.7" -> "0.8"

# 3. Apply (triggers new revision)
terraform apply
```

**⚠️ Note**: Environment variable changes trigger new Cloud Run revisions. Old revisions remain for rollback.

### Workspace-Based Multi-Environment

Use Terraform workspaces for managing multiple environments:

```bash
# Create workspace for staging
terraform workspace new staging
terraform apply -var-file=staging.tfvars

# Switch to production
terraform workspace select production
terraform apply -var-file=production.tfvars

# List workspaces
terraform workspace list
```

## Using Existing Resources

If you already have Cloud SQL, Pub/Sub, or other resources, you can reference them instead of creating new ones.

### Example: Use Existing Cloud SQL Instance

```hcl
# In terraform.tfvars
create_cloud_sql    = false
db_instance_name    = "my-existing-postgres-instance"
db_name             = "my_existing_database"
```

Terraform will:
- ✅ Skip creating new Cloud SQL instance
- ✅ Reference existing instance by name
- ✅ Create IAM database users on existing instance
- ✅ Grant service accounts access to existing instance

### Example: Use Existing Pub/Sub Resources

```hcl
# In terraform.tfvars
create_pubsub             = false
pubsub_topic_name         = "my-existing-topic"
pubsub_subscription_name  = "my-existing-subscription"
```

### Example: Use Existing Secrets

```hcl
# In terraform.tfvars
create_secrets     = false
openai_secret_name = "my-existing-openai-secret"
```

**Important**: When using existing resources, ensure:
1. Resources exist in the same project and region
2. Terraform has permissions to read/modify resources
3. Resource names match exactly (case-sensitive)

## Zero-Downtime Deployments

Cloud Run provides built-in support for zero-downtime deployments through revisions and traffic splitting.

### Standard Rolling Update (Default)

When you update an image or environment variable:

```bash
terraform apply
```

Cloud Run automatically:
1. Creates a new revision with updated configuration
2. Waits for health checks to pass
3. Gradually shifts traffic to new revision
4. Keeps old revisions for quick rollback

**No downtime** occurs during this process.

### Canary Deployment (Manual)

For high-risk changes, use manual traffic splitting:

```bash
# 1. Apply changes with Terraform
terraform apply

# 2. Get new revision name
export NEW_REVISION=$(gcloud run revisions list \
  --service=consensus-api \
  --region=us-central1 \
  --limit=1 \
  --format='value(name)')

# 3. Route 10% traffic to new revision
gcloud run services update-traffic consensus-api \
  --to-revisions=${NEW_REVISION}=10 \
  --region=us-central1

# 4. Monitor metrics for 10-15 minutes
# Check error rates, latency, logs

# 5. Gradually increase traffic
gcloud run services update-traffic consensus-api \
  --to-revisions=${NEW_REVISION}=50 \
  --region=us-central1

# 6. Monitor again

# 7. Route 100% traffic
gcloud run services update-traffic consensus-api \
  --to-latest \
  --region=us-central1
```

### Rollback

If issues are detected after deployment:

```bash
# 1. List recent revisions
gcloud run revisions list \
  --service=consensus-api \
  --region=us-central1 \
  --limit=5

# 2. Identify stable revision
export STABLE_REVISION="consensus-api-00042-abc"

# 3. Rollback by routing 100% traffic to stable revision
gcloud run services update-traffic consensus-api \
  --to-revisions=${STABLE_REVISION}=100 \
  --region=us-central1

# 4. Verify rollback
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://consensus-api-xxx.run.app/health
```

**Note**: Terraform state is not automatically rolled back. To sync state:

```bash
# Import current traffic split into state
terraform import google_cloud_run_service.backend projects/PROJECT/locations/REGION/services/consensus-api

# Or refresh state
terraform refresh
```

### Blue-Green Deployment (Advanced)

For complete isolation during deployment:

1. Create separate Cloud Run services for blue/green
2. Use Cloud Load Balancer to route traffic
3. Switch load balancer backend after verification

This approach is beyond the scope of this Terraform configuration but can be implemented using additional resources.

## Teardown and Cleanup

### Partial Teardown (Preserve Data)

To remove services but keep database and secrets:

```bash
# 1. Remove Cloud Run services
terraform destroy \
  -target=google_cloud_run_service.backend \
  -target=google_cloud_run_service.frontend \
  -target=google_cloud_run_service.worker

# 2. Confirm selective destruction
```

Database and secrets remain intact for future deployments.

### Complete Teardown

```bash
# 1. Disable deletion protection (if enabled)
vim terraform.tfvars
# Set: db_deletion_protection = false

terraform apply  # Update deletion protection first

# 2. Destroy all resources
terraform destroy

# 3. Confirm destruction
# Type: yes

# 4. Verify cleanup
gcloud run services list --region=REGION
gcloud sql instances list
gcloud pubsub topics list
```

### Troubleshooting Destroy Failures

**Error**: "Cannot delete Cloud SQL instance with deletion protection"

**Solution**:
```bash
# Update terraform.tfvars
db_deletion_protection = false

# Apply change first
terraform apply

# Then destroy
terraform destroy
```

**Error**: "Cloud SQL instance still has active connections"

**Solution**:
```bash
# Force delete connections
gcloud sql instances patch consensus-db --activation-policy=NEVER
sleep 30
terraform destroy
```

**Error**: "Secret Manager secret still has versions"

**Solution**:
```bash
# Secrets must be in DISABLED or DESTROYED state
gcloud secrets versions destroy latest --secret=openai-api-key
terraform destroy
```

### Cleanup Checklist

After `terraform destroy`, manually verify and clean up:

- [ ] Cloud Run services deleted
- [ ] Cloud SQL instance deleted
- [ ] Pub/Sub topic and subscription deleted
- [ ] Secret Manager secrets deleted or disabled
- [ ] Service accounts deleted
- [ ] Artifact Registry repository (optional - may want to keep images)
- [ ] IAM bindings removed
- [ ] Terraform state file backed up and secured

## Troubleshooting

### Common Issues

#### Issue: "Error creating service: Invalid image"

**Cause**: Image doesn't exist in Artifact Registry or wrong path.

**Solution**:
```bash
# Verify image exists
gcloud artifacts docker images list REGION-docker.pkg.dev/PROJECT/consensus-engine

# Check image path in terraform.tfvars matches exactly
backend_image = "us-central1-docker.pkg.dev/PROJECT/consensus-engine/consensus-api:latest"

# Push image if missing
gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT/consensus-engine/consensus-api:latest
```

#### Issue: "Error creating Cloud SQL instance: name already exists"

**Cause**: Instance name in use or recently deleted (7-day retention).

**Solution**:
```bash
# Option 1: Use existing instance
create_cloud_sql = false
db_instance_name = "existing-instance-name"

# Option 2: Choose different name
db_instance_name = "consensus-db-v2"

# Option 3: Permanently delete old instance (cannot undo!)
gcloud sql instances delete consensus-db --project=PROJECT
```

#### Issue: "Secret not found: openai-api-key"

**Cause**: Secret created by Terraform but no versions added.

**Solution**:
```bash
# Add secret version
echo -n "your-api-key" | gcloud secrets versions add openai-api-key --data-file=-

# Verify
gcloud secrets versions list openai-api-key
```

#### Issue: "Insufficient permissions to create resource"

**Cause**: Missing IAM roles for deploying user.

**Solution**:
```bash
# Grant required roles
export USER_EMAIL="your-email@example.com"

gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="user:$USER_EMAIL" \
  --role="roles/run.admin"

# See Prerequisites section for complete role list
```

#### Issue: "Backend configuration changed"

**Cause**: Switched between local and remote state, or changed bucket.

**Solution**:
```bash
# Reconfigure backend
terraform init -reconfigure

# Or migrate state
terraform init -migrate-state
```

#### Issue: "Resource already managed by another Terraform"

**Cause**: Resource created manually or by another Terraform state.

**Solution**:
```bash
# Option 1: Import into current state
terraform import google_cloud_run_service.backend projects/PROJECT/locations/REGION/services/consensus-api

# Option 2: Remove from state (if truly external)
terraform state rm google_cloud_run_service.backend

# Option 3: Rename resource in config
resource "google_cloud_run_service" "backend_v2" {
  name = "consensus-api-v2"
  # ...
}
```

### Terraform Output Not Showing

```bash
# Refresh outputs
terraform refresh

# Show specific output
terraform output backend_url

# Show all outputs
terraform output
```

### Plan Shows Unexpected Changes

```bash
# Show detailed diff
terraform plan -out=tfplan
terraform show tfplan

# Check for drift (manual changes outside Terraform)
terraform plan -refresh-only

# Sync state with actual resources
terraform apply -refresh-only
```

### Debugging Terraform

Enable debug logging:

```bash
export TF_LOG=DEBUG
export TF_LOG_PATH=./terraform-debug.log
terraform apply
```

## Cost Estimation

### Using Terraform Cloud Cost Estimation

Terraform Cloud provides built-in cost estimation. For free tier users, use Google Cloud Pricing Calculator:

```bash
# 1. Export plan
terraform plan -out=plan.tfplan

# 2. Convert to JSON
terraform show -json plan.tfplan > plan.json

# 3. Upload to Pricing Calculator
# https://cloud.google.com/products/calculator
```

### Manual Cost Estimation

**Typical monthly costs** (varies by usage):

| Component | Configuration | Est. Cost/Month |
|-----------|--------------|-----------------|
| Cloud Run API | 1-20 instances, 2 vCPU, 2GB | $50-500 |
| Cloud Run Worker | 1-3 instances, 2 vCPU, 4GB | $30-200 |
| Cloud Run Frontend | 0-10 instances, 1 vCPU, 512MB | $10-100 |
| Cloud SQL (db-f1-micro) | 0.6GB RAM, shared CPU | $7 |
| Cloud SQL (db-n1-standard-1) | 3.75GB RAM, 1 vCPU | $75 |
| Pub/Sub | <1M messages/month | $1-5 |
| Secret Manager | <10 secrets | $0.50 |
| Artifact Registry | <10GB storage | $1-2 |
| **Total (Development)** | Small workload | **$50-100** |
| **Total (Production)** | Medium workload | **$200-500** |

**Cost optimization tips:**

1. Use scale-to-zero (`min_instances = 0`) for non-critical services
2. Enable CPU throttling for services with bursty traffic
3. Use smaller Cloud SQL tiers for development/testing
4. Set appropriate `max_instances` to prevent runaway costs
5. Enable autoscaling based on CPU/memory metrics
6. Use committed use discounts for predictable workloads
7. Clean up unused Cloud Run revisions (keep last 5)
8. Monitor costs with budget alerts

### Setting Budget Alerts

```bash
# Create budget alert
gcloud billing budgets create \
  --billing-account=YOUR_BILLING_ACCOUNT_ID \
  --display-name="Consensus Engine Budget" \
  --budget-amount=500 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

## Security Considerations

### Terraform Security Best Practices

1. **Never commit sensitive files:**
   ```bash
   # Add to .gitignore
   echo "terraform.tfvars" >> .gitignore
   echo "*.tfstate*" >> .gitignore
   echo ".terraform/" >> .gitignore
   ```

2. **Use Secret Manager for API keys:**
   - ✅ Store API keys in Secret Manager
   - ❌ Never pass API keys as Terraform variables
   - ❌ Never hardcode API keys in .tf files

3. **Enable audit logging:**
   ```hcl
   # Add to main.tf
   resource "google_project_iam_audit_config" "audit" {
     project = var.project_id
     service = "allServices"
     audit_log_config {
       log_type = "ADMIN_READ"
     }
     audit_log_config {
       log_type = "DATA_WRITE"
     }
   }
   ```

4. **Use least-privilege IAM roles:**
   - Service accounts have minimal required permissions
   - Review IAM bindings regularly
   - Remove unused service accounts

5. **Enable deletion protection:**
   ```hcl
   db_deletion_protection = true
   ```

6. **Restrict CORS origins:**
   ```hcl
   # Production
   cors_allow_headers = "Content-Type,Authorization"
   
   # Not this
   cors_allow_headers = "*"  # Insecure!
   ```

7. **Use IAM authentication for Cloud SQL:**
   ```hcl
   db_iam_auth = true  # No passwords needed
   ```

8. **Enable private Google Access:**
   ```hcl
   db_private_network = "projects/PROJECT/global/networks/default"
   ```

9. **Encrypt secrets at rest:**
   - Secret Manager encrypts by default
   - Cloud SQL encrypts by default
   - No additional configuration needed

10. **Regular security audits:**
    ```bash
    # Review IAM policies
    gcloud projects get-iam-policy PROJECT_ID
    
    # Check for overly permissive bindings
    gcloud asset search-all-iam-policies \
      --scope=projects/PROJECT_ID \
      --query="policy:allUsers OR policy:allAuthenticatedUsers"
    ```

### Compliance and Governance

- **Terraform Cloud**: Use Sentinel policies for policy-as-code
- **Cloud Asset Inventory**: Monitor resource compliance
- **Security Command Center**: Detect vulnerabilities
- **VPC Service Controls**: Additional network isolation
- **Organization Policies**: Enforce constraints across projects

## Additional Resources

### Terraform Documentation
- [Terraform Google Cloud Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Cloud Run Terraform Examples](https://github.com/terraform-google-modules/terraform-google-cloud-run)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)

### GCP Documentation
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Best Practices](https://cloud.google.com/sql/docs/postgres/best-practices)
- [Terraform on GCP Best Practices](https://cloud.google.com/docs/terraform/best-practices-for-terraform)

### Consensus Engine Documentation
- [GCP Deployment Architecture](../../../docs/GCP_DEPLOYMENT_ARCHITECTURE.md)
- [Manual Deployment Guide](../README.md)
- [Worker Deployment](../../../docs/WORKER_DEPLOYMENT.md)
- [Web Frontend](../../../docs/WEB_FRONTEND.md)

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review [Manual Deployment Guide](../README.md) for detailed command examples
3. See [GCP Deployment Architecture](../../../docs/GCP_DEPLOYMENT_ARCHITECTURE.md) for architecture details
4. Open an issue in the repository
