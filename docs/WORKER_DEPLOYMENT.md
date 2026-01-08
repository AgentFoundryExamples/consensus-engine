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
   - Create topic: `consensus-engine-jobs`
   - Create subscription: `consensus-engine-jobs-sub`
   - Configure dead-letter topic (recommended)

2. **Database Setup**:
   - PostgreSQL database with migrations applied
   - Cloud SQL instance with IAM authentication enabled

3. **Service Account**:
   - IAM roles: `roles/pubsub.subscriber`, `roles/cloudsql.client`, `roles/secretmanager.secretAccessor`

### Cloud Run Deployment

1. **Build Container**:

```bash
# Create Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy source
COPY src/ src/

# Run worker
CMD ["python", "-m", "consensus_engine.workers.pipeline_worker"]
EOF

# Build and push
docker build -t gcr.io/YOUR_PROJECT/pipeline-worker:latest .
docker push gcr.io/YOUR_PROJECT/pipeline-worker:latest
```

2. **Deploy to Cloud Run**:

```bash
gcloud run deploy pipeline-worker \
  --image gcr.io/YOUR_PROJECT/pipeline-worker:latest \
  --platform managed \
  --region us-central1 \
  --no-allow-unauthenticated \
  --service-account pipeline-worker@YOUR_PROJECT.iam.gserviceaccount.com \
  --set-env-vars "PUBSUB_PROJECT_ID=YOUR_PROJECT" \
  --set-env-vars "PUBSUB_SUBSCRIPTION=consensus-engine-jobs-sub" \
  --set-env-vars "DB_INSTANCE_CONNECTION_NAME=YOUR_PROJECT:us-central1:consensus-db" \
  --set-env-vars "DB_NAME=consensus_engine" \
  --set-env-vars "DB_IAM_AUTH=true" \
  --set-env-vars "USE_CLOUD_SQL_CONNECTOR=true" \
  --set-env-vars "ENV=production" \
  --set-secrets "OPENAI_API_KEY=openai-api-key:latest" \
  --add-cloudsql-instances YOUR_PROJECT:us-central1:consensus-db \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 10 \
  --min-instances 1 \
  --concurrency 10
```

3. **Configure Pub/Sub Push Subscription**:

```bash
gcloud pubsub subscriptions create consensus-engine-jobs-sub \
  --topic consensus-engine-jobs \
  --push-endpoint https://pipeline-worker-xxx-uc.a.run.app \
  --push-auth-service-account pipeline-worker@YOUR_PROJECT.iam.gserviceaccount.com \
  --ack-deadline 600 \
  --message-retention-duration 7d \
  --dead-letter-topic consensus-engine-jobs-dlq \
  --max-delivery-attempts 5
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

- Check worker logs for errors
- Verify subscription configuration
- Check IAM permissions
- Ensure database connectivity

**2. High Error Rate**

- Review `job_failed` logs for error patterns
- Check OpenAI API rate limits
- Verify database connection pool settings
- Check for schema validation errors

**3. High Latency**

- Review per-step latencies in logs
- Check OpenAI API response times
- Verify database query performance
- Consider increasing worker concurrency

**4. Duplicate Processing**

- Verify idempotency guards are working
- Check logs for `idempotent_skip` events
- Ensure unique constraints on database tables

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
