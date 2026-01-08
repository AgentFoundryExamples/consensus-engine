# ==============================================================================
# Consensus Engine API - Production Dockerfile
# ==============================================================================
# Multi-stage build for FastAPI backend with dependency caching
# Supports both amd64 and arm64 architectures
# Cloud Run compatible with configurable gunicorn/uvicorn entrypoint
# ==============================================================================

# Stage 1: Base image with system dependencies
FROM python:3.11-slim-bookworm AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Builder stage for installing Python dependencies
FROM base AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy dependency files
COPY pyproject.toml /app/

# Install Python dependencies
# Separate layer for dependencies to maximize cache reuse
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -e .

# Stage 3: Runtime image
FROM base AS runtime

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY src/ /app/src/
COPY alembic.ini /app/
COPY migrations/ /app/migrations/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Set Python environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# Expose port (Cloud Run uses PORT env variable)
ENV PORT=8000
EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health').read()" || exit 1

# Entrypoint with configurable workers
# Can be overridden via Cloud Run command or docker-compose
CMD ["uvicorn", "consensus_engine.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
