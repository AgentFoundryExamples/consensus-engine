# ==============================================================================
# Consensus Engine Web Frontend - Production Dockerfile
# ==============================================================================
# Multi-stage build for React + Vite application with nginx serving
# Supports both amd64 and arm64 architectures
# Cloud Run compatible with environment variable injection at runtime
# ==============================================================================

# Stage 1: Build the React application
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
# Use clean install for reproducible builds
RUN npm ci --prefer-offline --no-audit

# Copy source code
COPY . .

# Build the application
# Vite will use environment variables from .env files or build-time ENV vars
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:1.27-alpine AS runtime

# Install wget for healthcheck
RUN apk add --no-cache wget

# Copy nginx configuration
# Create a custom nginx config that supports runtime env var injection
RUN rm /etc/nginx/conf.d/default.conf

COPY <<'EOF' /etc/nginx/conf.d/default.conf
server {
    listen 8080;
    server_name _;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Root directory
    root /usr/share/nginx/html;
    index index.html;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1000;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    
    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # SPA routing - serve index.html for all routes
    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache";
    }
    
    # Health check endpoint for Cloud Run
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Create runtime environment variable injection script
# This allows VITE_ env vars to be injected at container startup
COPY <<'EOF' /docker-entrypoint.d/40-inject-env.sh
#!/bin/sh
set -e

# Create runtime config file with environment variables
cat <<ENVEOF > /usr/share/nginx/html/runtime-env.js
window._env_ = {
  VITE_API_BASE_URL: "${VITE_API_BASE_URL:-http://localhost:8000}",
  VITE_ENVIRONMENT: "${VITE_ENVIRONMENT:-production}",
  VITE_POLLING_INTERVAL_MS: "${VITE_POLLING_INTERVAL_MS:-3000}",
  VITE_IAM_TOKEN: "${VITE_IAM_TOKEN:-}"
};
ENVEOF

echo "Runtime environment variables injected"
EOF

RUN chmod +x /docker-entrypoint.d/40-inject-env.sh

# Expose port (Cloud Run default)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# Note: nginx:alpine uses the official nginx entrypoint which will run scripts in /docker-entrypoint.d/
# No need to override CMD
