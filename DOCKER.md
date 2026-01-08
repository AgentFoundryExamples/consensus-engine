# Docker Deployment Guide

This guide covers building and deploying the Consensus Engine services using Docker.

## Quick Start

### Prerequisites

- Docker 20.10+ installed
- Docker Compose 2.0+ (optional, for local development)
- Google Cloud SDK (for Cloud Run deployment)
- Access to Google Container Registry (GCR) or Artifact Registry

### Build Images

Build all three services:

```bash
# Backend API
docker build -t consensus-api:latest -f Dockerfile .

# Pipeline Worker
docker build -t consensus-worker:latest -f Dockerfile.worker .

# Web Frontend
docker build -t consensus-web:latest -f webapp/Dockerfile webapp/
```

### Multi-Architecture Support

All Dockerfiles support both amd64 and arm64 architectures. To build for multiple architectures:

```bash
# Create a new builder instance
docker buildx create --name multiarch --use

# Build and push multi-arch images
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t gcr.io/PROJECT_ID/consensus-api:latest \
  -f Dockerfile \
  --push \
  .
```

## Local Development with Docker Compose

```bash
# Copy environment file
cp .env.example .env

# Edit .env with your configuration (at minimum, set OPENAI_API_KEY)
vim .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

Services will be available at:
- API: http://localhost:8000
- Frontend: http://localhost:8080
- PostgreSQL: localhost:5432
- pgAdmin: http://localhost:5050

## Cloud Run Deployment

### 1. Push Images to GCR

```bash
# Set your project ID
export PROJECT_ID=your-project-id

# Tag and push images
docker tag consensus-api:latest gcr.io/$PROJECT_ID/consensus-api:latest
docker tag consensus-worker:latest gcr.io/$PROJECT_ID/consensus-worker:latest
docker tag consensus-web:latest gcr.io/$PROJECT_ID/consensus-web:latest

docker push gcr.io/$PROJECT_ID/consensus-api:latest
docker push gcr.io/$PROJECT_ID/consensus-worker:latest
docker push gcr.io/$PROJECT_ID/consensus-web:latest
```

### 2. Create Secrets in Secret Manager

```bash
# Create OpenAI API key secret
echo -n "your-openai-api-key" | gcloud secrets create openai-api-key \
  --data-file=- \
  --replication-policy=automatic
```

### 3. Deploy Services

```bash
# Update the YAML files with your project details
# Then deploy each service

# Backend API
gcloud run services replace infra/cloudrun/backend-service.yaml

# Worker
gcloud run services replace infra/cloudrun/worker-service.yaml

# Frontend
gcloud run services replace infra/cloudrun/frontend-service.yaml
```

## Docker Image Details

### Backend API (Dockerfile)

- **Base**: python:3.11-slim-bookworm
- **Multi-stage**: Yes (base → builder → runtime)
- **Port**: 8000
- **Entry point**: uvicorn
- **Health check**: /health endpoint
- **Size**: ~500MB (optimized with multi-stage build)

#### Build stages:
1. **base**: System dependencies (libpq5)
2. **builder**: Python dependencies installed in virtual environment
3. **runtime**: Application code + virtual environment (minimal)

#### Configuration:
- All configuration via environment variables (see `.env.example`)
- No build-time secrets required
- Runs as non-root user (appuser, UID 1000)

### Pipeline Worker (Dockerfile.worker)

- **Base**: python:3.11-slim-bookworm
- **Multi-stage**: Yes (base → builder → runtime)
- **Port**: 8080 (for health checks)
- **Entry point**: python -m consensus_engine.workers.pipeline_worker
- **Health check**: Process-based
- **Size**: ~500MB (same base as API)

#### Key features:
- Shares dependency layer with API for efficient caching
- Configured for long-running Pub/Sub message processing
- Suitable for Cloud Run Services or Cloud Run Jobs

### Web Frontend (webapp/Dockerfile)

- **Builder base**: node:20-alpine
- **Runtime base**: nginx:1.27-alpine
- **Multi-stage**: Yes (builder → runtime)
- **Port**: 8080
- **Entry point**: nginx
- **Health check**: /health endpoint
- **Size**: ~50MB (static files only)

#### Build stages:
1. **builder**: npm ci + npm run build → creates dist/
2. **runtime**: nginx + static files + runtime env injection

#### Runtime environment injection:
The frontend Dockerfile includes a script that creates `runtime-env.js` at container startup, allowing environment variables to be injected without rebuilding:

```javascript
// Injected at runtime
window._env_ = {
  VITE_API_BASE_URL: "https://api.example.com",
  VITE_ENVIRONMENT: "production",
  // ...
};
```

To use in your React app:
```typescript
const apiUrl = window._env_?.VITE_API_BASE_URL || import.meta.env.VITE_API_BASE_URL;
```

## Environment Variables

### Build-Time vs Runtime

All configuration is **runtime** - no build-time secrets or configuration required.

Benefits:
- Same image can be used across environments (dev, staging, prod)
- No secrets embedded in images
- Easy promotion and rollback
- Reduced build times (no per-environment rebuilds)

### Required Environment Variables

#### API Service
- `OPENAI_API_KEY` (secret)
- `DB_INSTANCE_CONNECTION_NAME` (for Cloud SQL)
- `DB_NAME`, `DB_USER`
- `PUBSUB_PROJECT_ID`

See `.env.example` for complete list.

#### Worker Service
- Same as API service
- Additional worker-specific settings (WORKER_MAX_CONCURRENCY, etc.)

#### Frontend Service
- `VITE_API_BASE_URL`
- `VITE_ENVIRONMENT`

See `webapp/.env.example` for complete list.

## Optimization Tips

### Build Cache

Docker uses layer caching to speed up builds. The Dockerfiles are optimized:

1. System dependencies installed first (rarely change)
2. Python/Node dependencies installed next (change occasionally)
3. Application code copied last (changes frequently)

To maximize cache hits:
- Don't modify `pyproject.toml` or `package.json` unless adding dependencies
- Use `.dockerignore` to exclude unnecessary files
- Use `docker build --cache-from` for CI/CD pipelines

### Image Size

Current optimizations:
- Multi-stage builds (dependencies separate from runtime)
- Slim/alpine base images where possible
- No build tools in final images
- `--no-cache-dir` for pip to avoid caching packages

Further optimization:
- Use Distroless images (requires more testing)
- Implement layer squashing for final images
- Remove unnecessary Python packages

### Security

Current security features:
- Non-root user in all containers
- Pinned base image versions
- Minimal system dependencies
- No secrets in images
- Security headers in nginx
- Health checks for all services

## Troubleshooting

### Build Failures

**SSL Certificate Issues (Sandbox Only)**
If you see SSL certificate errors during build, this is a sandbox environment limitation. In production:
- Ensure proper CA certificates are installed
- Check network/proxy configuration

**Dependency Installation Fails**
- Clear Docker cache: `docker builder prune`
- Check `pyproject.toml` or `package.json` for syntax errors
- Verify all dependencies are available in PyPI/npm

### Runtime Issues

**Container Won't Start**
- Check logs: `docker logs <container-id>`
- Verify all required environment variables are set
- Check database connectivity
- Ensure ports aren't already in use

**Health Checks Failing**
- Verify the application is listening on the correct port
- Check that health endpoints return 200 status
- Review application startup logs

**Worker Not Processing Messages**
- Verify Pub/Sub subscription exists
- Check service account has `roles/pubsub.subscriber`
- Review worker logs for connection issues
- Ensure `PUBSUB_PROJECT_ID` is set correctly

## Architecture Constraints

### Supported Platforms

All images support:
- linux/amd64 (x86_64)
- linux/arm64 (aarch64)

### Cloud Run Compatibility

All Dockerfiles are optimized for Cloud Run:
- Listen on port from `PORT` environment variable
- Respond to SIGTERM for graceful shutdown
- Include health check endpoints
- Run as non-root user
- Container size under Cloud Run limits

### Resource Requirements

Recommended minimum resources:

| Service  | CPU   | Memory | Notes                    |
|----------|-------|--------|--------------------------|
| API      | 1 CPU | 1GB    | Can scale to 2 CPU/2GB   |
| Worker   | 2 CPU | 2GB    | Needs memory for LLM     |
| Frontend | 0.5   | 512MB  | Static file serving only |

## Further Reading

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [GCP Deployment Architecture](docs/GCP_DEPLOYMENT_ARCHITECTURE.md)
- [Worker Deployment Guide](docs/WORKER_DEPLOYMENT.md)
