# Pipeline Worker Deployment Guide

## Overview

The pipeline worker is a background process that consumes job messages from Google Cloud Pub/Sub and executes the consensus pipeline asynchronously. It processes jobs through the full pipeline: expand → persona reviews → aggregation, updating database records with progress and results.

**For comprehensive deployment architecture and requirements, see [GCP Deployment Architecture](./GCP_DEPLOYMENT_ARCHITECTURE.md).**

This guide focuses on worker-specific deployment details. For complete system architecture, components, environment variables, IAM requirements, and deployment prerequisites, refer to the comprehensive architecture document.

## Architecture

```
┌──────────────┐     ┌─────────────┐     ┌──────────────────┐
│   API        │────▶│  Pub/Sub    │────▶│  Pipeline Worker │
│  Endpoints   │     │   Queue     │     │   (Cloud Run)    │
└──────────────┘     └─────────────┘     └──────────────────┘
                                                    │
                                                    ▼
                                          ┌─────────────────┐
                                          │   PostgreSQL    │
                                          │    Database     │
                                          └─────────────────┘
```

### Key Features

- **Idempotent Processing**: Safely handles duplicate message deliveries
- **Status Tracking**: Updates Run and StepProgress records at each pipeline stage
- **Error Handling**: Marks failed steps and runs with error context
- **Retry Logic**: Leverages Pub/Sub automatic retries and OpenAI client retries
- **Structured Logging**: Emits lifecycle events for monitoring and debugging
- **Graceful Shutdown**: Handles SIGTERM/SIGINT signals for clean termination

## Configuration

The worker is configured via environment variables:

### Required Settings

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-xxx...           # OpenAI API key

# Database Configuration
DB_INSTANCE_CONNECTION_NAME=...    # Cloud SQL instance (project:region:instance)
DB_NAME=consensus_engine
DB_USER=...
DB_IAM_AUTH=true                   # Use IAM authentication
USE_CLOUD_SQL_CONNECTOR=true

# Pub/Sub Configuration
PUBSUB_PROJECT_ID=your-project-id
PUBSUB_SUBSCRIPTION=consensus-engine-jobs-sub
```

### Optional Settings

```bash
# Worker Configuration
WORKER_MAX_CONCURRENCY=10          # Max concurrent message handlers (default: 10)
WORKER_ACK_DEADLINE_SECONDS=600    # Pub/Sub ack deadline (default: 600)
WORKER_STEP_TIMEOUT_SECONDS=300    # Per-step timeout (default: 300)
WORKER_JOB_TIMEOUT_SECONDS=1800    # Overall job timeout (default: 1800)

# OpenAI Retry Configuration
MAX_RETRIES_PER_PERSONA=3          # Max retries per persona (default: 3)
RETRY_INITIAL_BACKOFF_SECONDS=1.0  # Initial backoff delay (default: 1.0)
RETRY_BACKOFF_MULTIPLIER=2.0       # Backoff multiplier (default: 2.0)

# Logging
ENV=production                     # Environment (development, production, testing)
```

## Architecture Assumptions

### Database Configuration

**Supported**:
- ✅ Cloud SQL for PostgreSQL with IAM authentication (recommended)
- ✅ Cloud SQL with password authentication (less secure)
- ✅ Cloud SQL Connector for connection management

**Unsupported for Cloud Deployments**:
- ❌ Self-hosted PostgreSQL on Compute Engine
- ❌ Local PostgreSQL instances
- ❌ PostgreSQL on other cloud providers (AWS RDS, Azure Database)

**Connection Method**:
- Workers use Cloud SQL Python Connector (set `USE_CLOUD_SQL_CONNECTOR=true`)
- IAM authentication strongly recommended (set `DB_IAM_AUTH=true`)
- Service account must have `roles/cloudsql.client` role

### Pub/Sub Configuration

**Subscription Type**:
- Workers use **pull subscription** (streaming pull for efficiency)
- Cloud Run workers automatically handle message acknowledgement
- Kubernetes/GCE workers use long-lived connections with streaming pull

**Message Flow**:
1. API publishes job messages to topic
2. Worker subscribes to subscription and receives messages
3. Worker processes job and updates database
4. Worker acknowledges message on success or nacks on failure
5. Pub/Sub redelivers nacked messages based on retry policy

**Idempotency**:
- Workers check run status before processing to handle duplicate deliveries
- Completed runs are skipped (idempotency guard)
- Database updates use upsert semantics to avoid conflicts

### Container Registry

**Supported**:
- ✅ Google Container Registry (gcr.io) - legacy
- ✅ Artifact Registry (recommended) - REGION-docker.pkg.dev

**Image Requirements**:
- Python 3.11+ base image
- All dependencies from pyproject.toml installed
- Application code copied to container
- Worker entrypoint configured

### Networking

**Worker Network Access**:
- Outbound to Pub/Sub (Google-managed, no configuration needed)
- Outbound to Cloud SQL (via Cloud SQL Connector or private IP)
- Outbound to OpenAI API (public internet)
- No inbound connections required

**VPC Requirements**:
- Not required for basic Cloud Run deployment
- Optional VPC connector for private Cloud SQL access
- Required for GKE deployments with private networking

## Deployment

### Prerequisites

**For complete prerequisites including API enablement, quotas, and IAM permissions, see [GCP Deployment Architecture](./GCP_DEPLOYMENT_ARCHITECTURE.md#deployment-prerequisites).**

Worker-specific prerequisites:

1. **Pub/Sub Setup**:
   ```bash
   # Create topic
   gcloud pubsub topics create consensus-engine-jobs \
     --project=$PROJECT_ID
   
   # Create subscription with dead-letter topic (recommended)
   gcloud pubsub topics create consensus-engine-jobs-dlq \
     --project=$PROJECT_ID
   
   gcloud pubsub subscriptions create consensus-engine-jobs-sub \
     --topic=consensus-engine-jobs \
     --ack-deadline=600 \
     --message-retention-duration=7d \
     --dead-letter-topic=consensus-engine-jobs-dlq \
     --max-delivery-attempts=5 \
     --project=$PROJECT_ID
   ```

2. **Database Setup**:
   - PostgreSQL database with migrations applied (see [README.md - Database Setup](../README.md#database-setup))
   - Cloud SQL instance with IAM authentication enabled

3. **Service Account**:
   ```bash
   # Create worker service account
   gcloud iam service-accounts create consensus-worker-sa \
     --display-name="Consensus Engine Pipeline Worker" \
     --project=$PROJECT_ID
   
   # Grant required IAM roles
   # Cloud SQL Client (for database access)
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member="serviceAccount:consensus-worker-sa@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/cloudsql.client"
   
   # Pub/Sub Subscriber (for consuming job messages)
   gcloud pubsub subscriptions add-iam-policy-binding consensus-engine-jobs-sub \
     --member="serviceAccount:consensus-worker-sa@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/pubsub.subscriber" \
     --project=$PROJECT_ID
   
   # Secret Manager Secret Accessor (for OpenAI API key)
   gcloud secrets add-iam-policy-binding openai-api-key \
     --member="serviceAccount:consensus-worker-sa@$PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor" \
     --project=$PROJECT_ID
   ```

### Cloud Run Deployment Options

The pipeline worker can be deployed in two modes:

1. **Cloud Run Service** (Recommended): Long-running service that continuously pulls messages from Pub/Sub
2. **Cloud Run Job**: Batch processing job that runs on a schedule or on-demand

#### Option A: Cloud Run Service (Continuous Processing)

Best for: Production workloads with continuous job processing.

**Build and Push Image:**

```bash
cd /path/to/consensus-engine

# Set region
export REGION="us-central1"

# Build and push worker image
gcloud builds submit \
  --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/consensus-engine/consensus-worker:latest \
  --file Dockerfile.worker \
  --project=$PROJECT_ID \
  --timeout=20m

# Or build locally
docker build \
  -f Dockerfile.worker \
  -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/consensus-engine/consensus-worker:latest .

docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/consensus-engine/consensus-worker:latest
```

**Deploy as Service:**

```bash
# Set image reference
export WORKER_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/consensus-engine/consensus-worker:latest"

# Deploy worker service
gcloud run deploy consensus-worker \
  --image=${WORKER_IMAGE} \
  --platform=managed \
  --region=$REGION \
  --service-account=consensus-worker-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --no-allow-unauthenticated \
  --min-instances=1 \
  --max-instances=3 \
  --cpu=2 \
  --memory=4Gi \
  --timeout=3600s \
  --concurrency=1 \
  --no-cpu-throttling \
  --execution-environment=gen2 \
  --add-cloudsql-instances=${PROJECT_ID}:${REGION}:consensus-db \
  --set-env-vars="^@^ENV=production@OPENAI_MODEL=gpt-5.1@EXPAND_MODEL=gpt-5.1@EXPAND_TEMPERATURE=0.7@REVIEW_MODEL=gpt-5.1@REVIEW_TEMPERATURE=0.2@USE_CLOUD_SQL_CONNECTOR=true@DB_INSTANCE_CONNECTION_NAME=${PROJECT_ID}:${REGION}:consensus-db@DB_NAME=consensus_engine@DB_USER=consensus-worker-sa@${PROJECT_ID}.iam@DB_IAM_AUTH=true@PUBSUB_PROJECT_ID=${PROJECT_ID}@PUBSUB_SUBSCRIPTION=consensus-engine-jobs-sub@WORKER_MAX_CONCURRENCY=10@WORKER_ACK_DEADLINE_SECONDS=600@WORKER_STEP_TIMEOUT_SECONDS=300@WORKER_JOB_TIMEOUT_SECONDS=1800" \
  --set-secrets=OPENAI_API_KEY=openai-api-key:latest \
  --project=$PROJECT_ID

# Verify deployment
gcloud run services describe consensus-worker \
  --region=$REGION \
  --format='value(status.url)' \
  --project=$PROJECT_ID
```

**Using YAML Configuration (Alternative):**

```bash
# Update worker-service.yaml with your values
gcloud run services replace infra/cloudrun/worker-service.yaml \
  --region=$REGION \
  --project=$PROJECT_ID
```

**Worker Service Configuration Notes:**
- `min-instances=1`: Keeps at least one instance warm to avoid cold starts
- `max-instances=3`: Limits horizontal scaling to control costs
- `concurrency=1`: Process one job at a time per instance (for resource-intensive jobs)
- `no-cpu-throttling`: Ensure CPU is always available (critical for LLM processing)
- `timeout=3600s`: Allow up to 1 hour for job processing

#### Option B: Cloud Run Job (Scheduled or On-Demand)

Best for: Batch processing or scheduled job execution.

**Deploy as Job:**

```bash
# Create Cloud Run Job
gcloud run jobs create consensus-worker-job \
  --image=${WORKER_IMAGE} \
  --region=$REGION \
  --service-account=consensus-worker-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --max-retries=3 \
  --task-timeout=3600s \
  --parallelism=1 \
  --tasks=1 \
  --add-cloudsql-instances=${PROJECT_ID}:${REGION}:consensus-db \
  --set-env-vars="ENV=production,OPENAI_MODEL=gpt-5.1,EXPAND_MODEL=gpt-5.1,EXPAND_TEMPERATURE=0.7,REVIEW_MODEL=gpt-5.1,REVIEW_TEMPERATURE=0.2,USE_CLOUD_SQL_CONNECTOR=true,DB_INSTANCE_CONNECTION_NAME=${PROJECT_ID}:${REGION}:consensus-db,DB_NAME=consensus_engine,DB_USER=consensus-worker-sa@${PROJECT_ID}.iam,DB_IAM_AUTH=true,PUBSUB_PROJECT_ID=${PROJECT_ID},PUBSUB_SUBSCRIPTION=consensus-engine-jobs-sub" \
  --set-secrets=OPENAI_API_KEY=openai-api-key:latest \
  --project=$PROJECT_ID

# Execute job manually
gcloud run jobs execute consensus-worker-job \
  --region=$REGION \
  --project=$PROJECT_ID \
  --wait

# Check job execution logs
gcloud run jobs executions logs read \
  --region=$REGION \
  --job=consensus-worker-job \
  --project=$PROJECT_ID
```

**Schedule Job with Cloud Scheduler:**

```bash
# Create scheduler job (run every 5 minutes)
gcloud scheduler jobs create http consensus-worker-scheduler \
  --location=$REGION \
  --schedule="*/5 * * * *" \
  --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/consensus-worker-job:run" \
  --http-method=POST \
  --oauth-service-account-email=consensus-worker-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --project=$PROJECT_ID

# Test scheduler
gcloud scheduler jobs run consensus-worker-scheduler \
  --location=$REGION \
  --project=$PROJECT_ID
```

#### Comparison: Service vs Job

| Feature | Cloud Run Service | Cloud Run Job |
|---------|-------------------|---------------|
| **Use Case** | Continuous processing | Batch/scheduled processing |
| **Cost** | Billed for instance uptime (even idle with min-instances) | Billed only during execution |
| **Scaling** | Auto-scales based on incoming messages | Fixed task parallelism |
| **Cold Start** | Can be mitigated with min-instances | Always has cold start |
| **Message Processing** | Streaming pull (real-time) | Pull-and-process (batch) |
| **Best For** | Production with continuous load | Development, testing, scheduled jobs |

**Recommendation:** Use **Cloud Run Service** for production workloads to ensure real-time job processing with minimal latency.

### Verification

After deployment, verify the worker is functioning correctly:

**1. Check Worker Service Status:**

```bash
# Check service is running
gcloud run services describe consensus-worker \
  --region=$REGION \
  --format='value(status.conditions)' \
  --project=$PROJECT_ID

# Expected: Ready condition with status=True
```

**2. Check Worker Logs:**

```bash
# View recent worker logs
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-worker" \
  --limit=50 \
  --format=json \
  --project=$PROJECT_ID

# Look for "worker.started" lifecycle event
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-worker AND jsonPayload.lifecycle_event=\"worker.started\"" \
  --limit=5 \
  --project=$PROJECT_ID
```

**3. Test Job Submission:**

Submit a test job via the API and verify the worker processes it:

```bash
# Get backend URL
export BACKEND_URL=$(gcloud run services describe consensus-api \
  --region=$REGION \
  --format='value(status.url)' \
  --project=$PROJECT_ID)

# Submit test job
curl -X POST ${BACKEND_URL}/v1/full-review \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "idea": "Build a REST API for user management with authentication",
    "extra_context": {"language": "Python", "framework": "FastAPI"}
  }'

# Capture run_id from response
export RUN_ID="<run-id-from-response>"

# Watch worker process the job
gcloud logging tail \
  "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-worker AND jsonPayload.run_id=\"${RUN_ID}\"" \
  --format=json \
  --project=$PROJECT_ID

# Poll for completion (run status should change: queued -> running -> completed)
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  ${BACKEND_URL}/v1/runs/${RUN_ID}
```

**4. Check Pub/Sub Metrics:**

```bash
# Check subscription metrics
gcloud pubsub subscriptions describe consensus-engine-jobs-sub \
  --format="table(name,numUndeliveredMessages,oldestUnackedMessageAge)" \
  --project=$PROJECT_ID

# Healthy worker should have:
# - numUndeliveredMessages: 0 (all messages processed)
# - oldestUnackedMessageAge: small value or null
```

### Scaling and Resource Configuration

#### Vertical Scaling (Instance Resources)

Adjust CPU and memory based on job complexity:

```bash
# For larger/more complex jobs, increase resources
gcloud run services update consensus-worker \
  --cpu=4 \
  --memory=8Gi \
  --region=$REGION \
  --project=$PROJECT_ID

# For cost optimization with simpler jobs
gcloud run services update consensus-worker \
  --cpu=1 \
  --memory=2Gi \
  --region=$REGION \
  --project=$PROJECT_ID
```

**Resource Recommendations:**
- **Light jobs** (1-2 personas): 1 CPU, 2Gi memory
- **Standard jobs** (5 personas): 2 CPU, 4Gi memory
- **Complex jobs** (10+ personas, large context): 4 CPU, 8Gi memory

#### Horizontal Scaling (Instance Count)

Control the number of worker instances:

```bash
# Increase max instances for higher throughput
gcloud run services update consensus-worker \
  --max-instances=10 \
  --region=$REGION \
  --project=$PROJECT_ID

# Decrease for cost control
gcloud run services update consensus-worker \
  --max-instances=1 \
  --region=$REGION \
  --project=$PROJECT_ID

# Always keep at least one instance warm (recommended for production)
gcloud run services update consensus-worker \
  --min-instances=1 \
  --region=$REGION \
  --project=$PROJECT_ID
```

**Scaling Guidelines:**
- `min-instances=0`: Cold starts on first job (not recommended for production)
- `min-instances=1`: One instance always warm, minimal cold starts (recommended)
- `min-instances=2-3`: Multiple instances for high availability
- `max-instances`: Set based on expected peak load and budget

#### Concurrency Configuration

Control how many jobs each instance processes simultaneously:

```bash
# Process one job at a time (default, recommended for LLM-heavy workloads)
gcloud run services update consensus-worker \
  --concurrency=1 \
  --region=$REGION \
  --project=$PROJECT_ID

# Process multiple jobs (only for very light jobs)
# Note: LLM API calls are I/O bound, but memory usage may be high
gcloud run services update consensus-worker \
  --concurrency=5 \
  --region=$REGION \
  --project=$PROJECT_ID
```

**Concurrency Recommendations:**
- `concurrency=1`: Best for CPU/memory-intensive jobs (default)
- `concurrency=2-5`: Only if jobs are I/O bound with low memory footprint
- Match `WORKER_MAX_CONCURRENCY` env var to concurrency setting

### Monitoring Worker Performance

**Key Metrics to Track:**

1. **Job Processing Rate:**
   ```bash
   # Query for completed jobs in last hour
   gcloud logging read \
     "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-worker AND jsonPayload.lifecycle_event=\"job.completed\"" \
     --limit=100 \
     --format=json \
     --project=$PROJECT_ID | jq length
   ```

2. **Job Latency:**
   ```bash
   # Average job processing time
   gcloud logging read \
     "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-worker AND jsonPayload.lifecycle_event=\"job.completed\"" \
     --limit=50 \
     --format=json \
     --project=$PROJECT_ID | jq '[.[].jsonPayload.elapsed_time] | add / length'
   ```

3. **Error Rate:**
   ```bash
   # Failed jobs in last hour
   gcloud logging read \
     "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-worker AND jsonPayload.lifecycle_event=\"job.failed\"" \
     --limit=100 \
     --format=json \
     --project=$PROJECT_ID | jq length
   ```

4. **Queue Depth:**
   ```bash
   # Unprocessed messages
   gcloud pubsub subscriptions describe consensus-engine-jobs-sub \
     --format='value(numUndeliveredMessages)' \
     --project=$PROJECT_ID
   ```

**Set Up Monitoring Dashboards:**

Create custom dashboards in Cloud Monitoring to track these metrics over time. Navigate to: Cloud Console > Monitoring > Dashboards > Create Dashboard

**Configure Alerts:**

```bash
# Example: Alert on high queue depth
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High Worker Queue Depth" \
  --condition-display-name="Queue depth > 50" \
  --condition-threshold-value=50 \
  --condition-threshold-duration=600s \
  --condition-threshold-comparison=COMPARISON_GT \
  --condition-threshold-filter='resource.type="pubsub_subscription" AND resource.labels.subscription_id="consensus-engine-jobs-sub" AND metric.type="pubsub.googleapis.com/subscription/num_undelivered_messages"' \
  --project=$PROJECT_ID
```

### Alternative: Pull-based Worker (Kubernetes/GCE)

For pull-based deployments (Kubernetes, GCE, local), the worker automatically uses pull mode:

```bash
# The worker internally uses streaming pull
python -m consensus_engine.workers.pipeline_worker
```

Deploy to Kubernetes:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pipeline-worker
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pipeline-worker
  template:
    metadata:
      labels:
        app: pipeline-worker
    spec:
      serviceAccountName: pipeline-worker
      containers:
      - name: worker
        image: gcr.io/YOUR_PROJECT/pipeline-worker:latest
        env:
        - name: PUBSUB_PROJECT_ID
          value: "YOUR_PROJECT"
        - name: PUBSUB_SUBSCRIPTION
          value: "consensus-engine-jobs-sub"
        - name: WORKER_MAX_CONCURRENCY
          value: "10"
        - name: DB_INSTANCE_CONNECTION_NAME
          value: "YOUR_PROJECT:us-central1:consensus-db"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: openai-api-key
              key: key
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
```

## Local Development

### Using Pub/Sub Emulator

1. **Start Emulator**:

```bash
docker run -d --name pubsub-emulator -p 8085:8085 \
  gcr.io/google.com/cloudsdktool/cloud-sdk:emulators \
  gcloud beta emulators pubsub start --host-port=0.0.0.0:8085
```

2. **Create Topic and Subscription**:

```bash
export PUBSUB_EMULATOR_HOST=localhost:8085

python << 'EOF'
from google.cloud import pubsub_v1

project_id = "emulator-project"
topic_id = "consensus-engine-jobs"
subscription_id = "consensus-engine-jobs-sub"

publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()

topic_path = publisher.topic_path(project_id, topic_id)
subscription_path = subscriber.subscription_path(project_id, subscription_id)

# Create topic
publisher.create_topic(request={"name": topic_path})

# Create subscription
subscriber.create_subscription(
    request={"name": subscription_path, "topic": topic_path}
)

print(f"Created topic: {topic_path}")
print(f"Created subscription: {subscription_path}")
EOF
```

3. **Configure Environment**:

```bash
cat > .env << 'EOF'
OPENAI_API_KEY=sk-test-key
PUBSUB_PROJECT_ID=emulator-project
PUBSUB_SUBSCRIPTION=consensus-engine-jobs-sub
PUBSUB_EMULATOR_HOST=localhost:8085
DB_HOST=localhost
DB_PORT=5432
DB_NAME=consensus_engine
DB_USER=postgres
DB_PASSWORD=postgres
ENV=development
EOF
```

4. **Run Worker**:

```bash
python -m consensus_engine.workers.pipeline_worker
```

### Using Mock Mode (No Pub/Sub)

For testing without Pub/Sub:

```bash
PUBSUB_USE_MOCK=true python -m consensus_engine.workers.pipeline_worker
```

Note: Mock mode only logs messages; use emulator or real Pub/Sub for actual processing.

## Monitoring

### Key Metrics

Monitor these metrics in Cloud Monitoring:

- **Message Processing Rate**: Messages/second
- **Job Latency**: Time from enqueue to completion (p50, p95, p99)
- **Step Latency**: Per-step processing time
- **Error Rate**: Failed jobs / total jobs
- **Queue Depth**: Unprocessed messages in subscription

### Log Events

The worker emits structured JSON logs with these lifecycle events:

- `enqueued`: Job published to queue
- `job_started`: Worker picked up job
- `step_started`: Pipeline step started
- `step_completed`: Pipeline step completed
- `job_completed`: Job finished successfully
- `job_failed`: Job failed after retries
- `idempotent_skip`: Job already processed (duplicate delivery)

Example log query (Cloud Logging):

```
resource.type="cloud_run_revision"
resource.labels.service_name="pipeline-worker"
jsonPayload.lifecycle_event=("job_completed" OR "job_failed")
```

### Alerting

Set up alerts for:

1. **High Error Rate**: Error rate > 5% over 5 minutes
2. **Queue Backlog**: Unprocessed messages > 100 for 10 minutes
3. **High Latency**: p95 job latency > 5 minutes
4. **Worker Crashes**: Container restarts > 3 in 10 minutes

## Troubleshooting

### Common Issues

**1. Messages Not Being Processed**

**Symptoms:**
- Jobs remain in "queued" status
- Subscription shows undelivered messages
- Worker logs show no activity

**Check:**
```bash
# Verify worker is running
gcloud run services describe consensus-worker \
  --region=$REGION \
  --format='value(status.conditions.status)' \
  --project=$PROJECT_ID

# Check worker logs for startup errors
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-worker" \
  --limit=20 \
  --format=json \
  --project=$PROJECT_ID | grep -A5 "error"

# Check subscription configuration
gcloud pubsub subscriptions describe consensus-engine-jobs-sub \
  --format="table(name,ackDeadlineSeconds,pushConfig.pushEndpoint)" \
  --project=$PROJECT_ID

# Verify IAM permissions
gcloud pubsub subscriptions get-iam-policy consensus-engine-jobs-sub \
  --project=$PROJECT_ID
```

**Solutions:**
- **Worker not started:** Check if min-instances=0 and cold start is slow. Set min-instances=1
- **Subscription misconfigured:** Verify ackDeadline (should be 600s) and subscription exists
- **IAM permissions:** Grant `roles/pubsub.subscriber` to worker service account
- **Worker crashed:** Check logs for startup errors (database connection, missing env vars)

**2. High Error Rate**

**Symptoms:**
- Many jobs fail with errors
- High rate of "job.failed" log events
- Dead-letter queue accumulating messages

**Check:**
```bash
# View failed job logs
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-worker AND jsonPayload.lifecycle_event=\"job.failed\"" \
  --limit=20 \
  --format=json \
  --project=$PROJECT_ID

# Check error patterns
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-worker AND severity>=ERROR" \
  --limit=50 \
  --format=json \
  --project=$PROJECT_ID | jq '[.[].jsonPayload.error_message] | group_by(.) | map({error: .[0], count: length}) | sort_by(.count) | reverse'

# Check OpenAI API errors
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-worker AND textPayload:\"OpenAI\"" \
  --limit=20 \
  --project=$PROJECT_ID

# Check database errors
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-worker AND textPayload:\"database\"" \
  --limit=20 \
  --project=$PROJECT_ID
```

**Solutions:**
- **OpenAI rate limits:** Increase `RETRY_INITIAL_BACKOFF_SECONDS`, reduce concurrent jobs, or request higher rate limits
- **Database connection errors:** Check Cloud SQL instance status, verify IAM authentication works
- **Timeout errors:** Increase `WORKER_STEP_TIMEOUT_SECONDS` and `WORKER_JOB_TIMEOUT_SECONDS`
- **Memory errors (OOM):** Increase worker memory allocation

**3. High Latency (Slow Processing)**

**Symptoms:**
- Jobs taking longer than expected
- High p95/p99 latencies
- Queue backlog growing

**Check:**
```bash
# Analyze job latencies
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-worker AND jsonPayload.lifecycle_event=\"job.completed\"" \
  --limit=100 \
  --format=json \
  --project=$PROJECT_ID | jq '[.[].jsonPayload.elapsed_time] | {min: min, max: max, avg: (add / length), p95: (sort | .[95])}'

# Check per-step latencies
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-worker AND jsonPayload.lifecycle_event=\"step.completed\"" \
  --limit=50 \
  --format=json \
  --project=$PROJECT_ID | jq 'group_by(.jsonPayload.step_name) | map({step: .[0].jsonPayload.step_name, avg_latency: ([.[].jsonPayload.elapsed_time] | add / length)})'

# Check worker resource usage
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/container/cpu/utilizations" AND resource.labels.service_name="consensus-worker"' \
  --project=$PROJECT_ID
```

**Solutions:**
- **OpenAI API slowness:** Check OpenAI status page, consider using faster models
- **Under-provisioned:** Increase CPU/memory allocation
- **Too many concurrent jobs:** Reduce `WORKER_MAX_CONCURRENCY` or increase instances
- **Database query slowness:** Optimize database queries, check connection pool settings
- **Scale horizontally:** Increase `max-instances` to process more jobs in parallel

**4. Duplicate Processing (Same Job Processed Twice)**

**Symptoms:**
- Same run_id appears in logs multiple times
- Run status updates conflict
- Duplicate results in database

**Expected Behavior:**
Worker should skip already-completed runs via idempotency checks.

**Check:**
```bash
# Look for idempotent skips
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-worker AND jsonPayload.lifecycle_event=\"idempotency_check.skipped\"" \
  --limit=20 \
  --project=$PROJECT_ID

# Check for duplicate processing
export RUN_ID="<your-run-id>"
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-worker AND jsonPayload.run_id=\"${RUN_ID}\"" \
  --limit=50 \
  --format=json \
  --project=$PROJECT_ID | jq 'group_by(.jsonPayload.lifecycle_event) | map({event: .[0].jsonPayload.lifecycle_event, count: length})'
```

**Solutions:**
- **Verify idempotency logic:** Check worker code for proper status checks
- **Pub/Sub redelivery:** Expected due to ack deadline, should be handled by idempotency
- **Database race conditions:** Ensure unique constraints on run tables
- **Long-running jobs:** Extend ack deadline if jobs take > 600s

**5. Worker Crashes or Restarts Frequently**

**Symptoms:**
- Worker container restarts
- Jobs fail mid-processing
- Liveness probe failures

**Check:**
```bash
# Check revision history for restarts
gcloud run revisions list \
  --service=consensus-worker \
  --region=$REGION \
  --limit=10 \
  --format='table(metadata.name,status.conditions.status,metadata.creationTimestamp)' \
  --project=$PROJECT_ID

# Check for OOM kills
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-worker AND textPayload:\"memory\"" \
  --limit=20 \
  --project=$PROJECT_ID

# Check liveness probe failures
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-worker AND textPayload:\"liveness\"" \
  --limit=10 \
  --project=$PROJECT_ID

# Check for crashes/exceptions
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-worker AND severity>=ERROR" \
  --limit=30 \
  --project=$PROJECT_ID | grep -A5 "exception\|traceback\|fatal"
```

**Solutions:**
- **OOM (Out of Memory):** Increase memory allocation, optimize memory usage in code
- **Unhandled exceptions:** Fix bugs in worker code, add better error handling
- **Liveness probe too aggressive:** Adjust probe settings in YAML
- **Database connection leaks:** Verify proper connection pool management
- **Graceful shutdown issues:** Ensure worker handles SIGTERM properly

**6. Pub/Sub Subscription Issues**

**Symptoms:**
- Messages stuck in subscription
- High oldest-unacked-message age
- Messages going to dead-letter queue

**Check:**
```bash
# Check subscription health
gcloud pubsub subscriptions describe consensus-engine-jobs-sub \
  --format="table(name,numUndeliveredMessages,oldestUnackedMessageAge,deadLetterPolicy.deadLetterTopic)" \
  --project=$PROJECT_ID

# Check dead-letter queue
gcloud pubsub topics describe consensus-engine-jobs-dlq \
  --project=$PROJECT_ID

# Pull dead-letter messages
gcloud pubsub subscriptions pull consensus-engine-jobs-dlq \
  --limit=10 \
  --auto-ack \
  --project=$PROJECT_ID

# Check ack/nack patterns
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=consensus-worker AND textPayload:\"nack\"" \
  --limit=20 \
  --project=$PROJECT_ID
```

**Solutions:**
- **Stuck messages:** Manually purge if invalid, or fix worker to process them
- **Dead-letter accumulation:** Investigate why jobs are repeatedly failing, fix root cause
- **Ack deadline too short:** Increase to 600s if jobs take longer
- **Max delivery attempts too low:** Increase if transient failures are common
- **Subscription deleted/recreated:** Recreate with proper configuration

### Debugging Workflow

1. **Identify the Issue:**
   - Check service status
   - Review recent logs
   - Check metrics (queue depth, error rate, latency)

2. **Isolate the Cause:**
   - Is it affecting all jobs or specific ones?
   - When did the issue start?
   - What changed recently (deployment, configuration)?

3. **Gather Evidence:**
   - Collect relevant logs
   - Note error patterns
   - Check resource utilization

4. **Test Hypothesis:**
   - Try a fix in staging first
   - Deploy with gradual rollout
   - Monitor impact

5. **Document Resolution:**
   - Update runbook with findings
   - Add alerting if needed
   - Consider adding automated remediation

### Emergency Procedures

**Pause Job Processing:**
```bash
# Scale to 0 instances (stops processing immediately)
gcloud run services update consensus-worker \
  --min-instances=0 \
  --max-instances=0 \
  --region=$REGION \
  --project=$PROJECT_ID

# Messages will queue in Pub/Sub until worker is restarted
```

**Drain Queue:**
```bash
# Purge subscription (USE WITH CAUTION - deletes all messages)
gcloud pubsub subscriptions seek consensus-engine-jobs-sub \
  --time=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --project=$PROJECT_ID

# Or manually pull and discard messages
gcloud pubsub subscriptions pull consensus-engine-jobs-sub \
  --limit=1000 \
  --auto-ack \
  --project=$PROJECT_ID
```

**Force Restart Worker:**
```bash
# Deploy no-op change to force revision update
gcloud run services update consensus-worker \
  --update-labels="restart=$(date +%s)" \
  --region=$REGION \
  --project=$PROJECT_ID

# Or redeploy with same image
gcloud run services update consensus-worker \
  --image=${WORKER_IMAGE} \
  --region=$REGION \
  --project=$PROJECT_ID
```

### Debug Mode

Enable debug logging:

```bash
ENV=development python -m consensus_engine.workers.pipeline_worker
```

This outputs detailed logs including:
- Message payloads (sanitized)
- Step-by-step progress
- Database queries
- OpenAI request/response metadata

## Production Best Practices

1. **Resource Sizing**:
   - Memory: 2-4 GB per worker instance
   - CPU: 1-2 cores per instance
   - Adjust based on concurrent message processing

2. **Scaling**:
   - Set min instances to 1 (avoid cold starts)
   - Set max instances based on expected load
   - Use Cloud Run autoscaling or Kubernetes HPA

3. **Retries**:
   - Configure dead-letter topic for failed jobs
   - Set max delivery attempts to 5
   - Monitor dead-letter queue

4. **Database**:
   - Use connection pooling (pool_size=5, max_overflow=10)
   - Enable Cloud SQL connection pooler
   - Set appropriate timeouts

5. **Security**:
   - Use IAM authentication for Cloud SQL
   - Store API keys in Secret Manager
   - Use least-privilege service accounts
   - Enable VPC-SC for additional isolation

6. **Monitoring**:
   - Set up comprehensive logging
   - Create dashboards for key metrics
   - Configure alerts for anomalies
   - Enable error reporting

## Cost Optimization

- **Pub/Sub**: Use pull subscription to reduce costs
- **Cloud Run**: Set appropriate min/max instances
- **Database**: Use connection pooling to reduce connections
- **OpenAI**: Implement rate limiting to control API costs

## FAQ

**Q: Can I run multiple worker instances?**
A: Yes, the worker is designed for horizontal scaling. Each instance processes messages independently.

**Q: What happens if a worker crashes mid-job?**
A: Pub/Sub will redeliver the message. The worker's idempotency guards ensure safe reprocessing.

**Q: How do I handle high-priority jobs?**
A: Create a separate subscription with higher concurrency for high-priority messages.

**Q: Can I customize step timeouts?**
A: Yes, use `WORKER_STEP_TIMEOUT_SECONDS` and `WORKER_JOB_TIMEOUT_SECONDS` environment variables.

**Q: How do I monitor job progress?**
A: Query the `runs` and `step_progress` tables, or use the `/v1/runs/{run_id}` API endpoint.
