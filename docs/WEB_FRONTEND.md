# Web Frontend Documentation

This document provides a comprehensive guide to the Consensus Engine web frontend, including setup, development, deployment, and maintenance.

## Overview

The Consensus Engine web frontend is a modern React application built with:

- **Vite**: Fast build tool and dev server
- **React 19**: Latest React features with TypeScript support
- **TypeScript**: Type-safe development with strict mode enabled
- **Tailwind CSS**: Utility-first CSS framework for consistent styling
- **OpenAPI Client**: Auto-generated TypeScript client from backend API

## Project Structure

```
webapp/
├── src/
│   ├── api/
│   │   ├── generated/        # Auto-generated OpenAPI client (DO NOT EDIT)
│   │   └── client.ts         # API client wrapper with auth configuration
│   ├── components/
│   │   ├── layout/           # Layout components (Header, Container)
│   │   └── ui/               # UI primitives (Button, StatusBadge)
│   ├── config/
│   │   └── index.ts          # Environment configuration
│   ├── App.tsx               # Main application component
│   ├── main.tsx              # Application entry point
│   └── index.css             # Global styles with Tailwind directives
├── public/                   # Static assets
├── .env.example              # Example environment variables
├── package.json              # Dependencies and scripts
├── tsconfig.json             # TypeScript configuration
├── tailwind.config.js        # Tailwind CSS configuration
├── vite.config.ts            # Vite configuration
└── openapi.json              # OpenAPI specification (regenerated from backend)
```

## Quick Start

### Prerequisites

- Node.js 20.x or later
- npm 10.x or later
- Backend API running (see main README.md)

### Installation

1. Navigate to the webapp directory:

```bash
cd webapp
```

2. Install dependencies:

```bash
npm install
```

3. Copy the example environment file:

```bash
cp .env.example .env
```

4. Update `.env` with your configuration:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_POLLING_INTERVAL_MS=3000
VITE_ENVIRONMENT=development
```

### Development

Start the development server:

```bash
npm run dev
```

The application will be available at `http://localhost:5173` by default.

#### Hot Module Replacement

Vite provides instant HMR (Hot Module Replacement) for a fast development experience:
- Changes to React components are reflected immediately
- TypeScript type checking runs in watch mode
- CSS changes apply without full page refresh

### Building for Production

Build the optimized production bundle:

```bash
npm run build
```

The build output will be in the `dist/` directory.

Preview the production build locally:

```bash
npm run preview
```

### Code Quality

#### Linting

Run ESLint to check for code issues:

```bash
npm run lint
```

Auto-fix linting issues:

```bash
npm run lint:fix
```

#### Formatting

Format all code with Prettier:

```bash
npm run format
```

Check formatting without making changes:

```bash
npx prettier --check .
```

#### Type Checking

Run TypeScript type checking:

```bash
npm run typecheck
```

## Environment Configuration

### Environment Variables

The frontend uses environment variables prefixed with `VITE_` (Vite convention). These are loaded from `.env` files and available at build time.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_BASE_URL` | Yes | `http://localhost:8000` | Base URL for the Consensus Engine API |
| `VITE_IAM_TOKEN` | No | - | IAM token for Cloud IAP/IAM authentication (leave empty for local dev) |
| `VITE_POLLING_INTERVAL_MS` | No | `3000` | Interval in milliseconds for polling run status (1000-60000) |
| `VITE_ENVIRONMENT` | No | `development` | Environment name (development, staging, production) |

### Multiple Environments

You can create environment-specific files:

- `.env` - Default environment variables (local development)
- `.env.local` - Local overrides (not committed to git)
- `.env.production` - Production environment variables
- `.env.staging` - Staging environment variables

Vite automatically loads the appropriate file based on the `--mode` flag:

```bash
npm run build -- --mode production
npm run build -- --mode staging
```

### Configuration Validation

The application validates configuration on startup (see `src/config/index.ts`):

- Ensures `VITE_API_BASE_URL` is set
- Warns if polling interval is outside recommended range (1000-60000ms)
- Logs configuration details (without exposing secrets) to console

## OpenAPI Client Generation

The TypeScript client is auto-generated from the backend's OpenAPI specification. This ensures type safety and keeps the frontend in sync with the API.

### Regenerating the Client

When the backend API changes, regenerate the TypeScript client:

```bash
npm run generate:api
```

This script:
1. Exports the OpenAPI spec from the backend (`webapp/openapi.json`)
2. Generates TypeScript types and services (`src/api/generated/`)
3. Preserves the API wrapper configuration (`src/api/client.ts`)

**Important:** Never edit files in `src/api/generated/` manually. They will be overwritten on the next generation.

### Client Usage

The generated client is wrapped in `src/api/client.ts` for centralized configuration:

```typescript
import { configureApiClient, DefaultService } from './api/client';

// Configure on app startup
configureApiClient();

// Use the services
const health = await DefaultService.healthHealthGet();
const runs = await RunsService.getRunsV1RunsGet();
```

### Available Services

The generated client includes services for all API endpoints:

- `ExpandService` - Expand idea endpoint
- `ReviewService` - Review idea endpoint
- `FullReviewService` - Full review with all personas
- `RunsService` - Get runs and run details
- `HealthService` - Health check endpoint
- `RootService` - Root endpoint

Each service includes TypeScript types for request/response payloads.

## Authentication

### Local Development

For local development, authentication is typically not required. The backend runs without IAM/IAP protection.

### Cloud IAP/IAM (Production)

In production, the application is deployed behind Cloud Identity-Aware Proxy (IAP) or uses IAM authentication.

#### IAM Token Flow

1. User authenticates with Google Identity Platform
2. IAP/IAM proxy validates authentication and injects token
3. Frontend extracts token and adds to API requests via `Authorization: Bearer <token>` header

#### Configuration

Set the IAM token in `.env`:

```env
VITE_IAM_TOKEN=<your-iam-token>
```

The API client wrapper (`src/api/client.ts`) automatically adds the token to all requests.

#### Token Management

For production deployments:
- Tokens are typically managed by the IAP proxy
- Frontend doesn't need to handle token refresh
- For service-to-service auth, use service account tokens

## CORS Configuration

The backend must be configured to allow requests from the frontend origin.

### Backend CORS Setup

In the backend `.env`:

```env
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

For production, use your actual frontend domain:

```env
CORS_ORIGINS=https://app.example.com,https://staging.example.com
```

**Security:** Never use wildcard (`*`) CORS origins in production.

### Verifying CORS

Check CORS headers in browser DevTools Network tab:

```
Access-Control-Allow-Origin: http://localhost:5173
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: *
Access-Control-Allow-Headers: *
```

## Component Library

### Layout Components

#### Header

```tsx
import { Header } from './components/layout';

<Header title="My Custom Title" />
```

Props:
- `title` (optional, string): Header title text (default: "Consensus Engine")

#### Container

```tsx
import { Container } from './components/layout';

<Container className="py-8">
  {/* Your content */}
</Container>
```

Props:
- `children` (ReactNode): Content to render inside the container
- `className` (optional, string): Additional Tailwind classes

### UI Primitives

#### Button

```tsx
import { Button } from './components/ui';

<Button
  variant="primary"
  size="md"
  onClick={handleClick}
  disabled={isLoading}
>
  Click Me
</Button>
```

Props:
- `variant` (optional): `"primary"` | `"secondary"` | `"danger"` (default: "primary")
- `size` (optional): `"sm"` | `"md"` | `"lg"` (default: "md")
- `disabled` (optional, boolean): Disable button
- All standard button HTML attributes

#### StatusBadge

```tsx
import { StatusBadge } from './components/ui';

<StatusBadge status="completed" />
<StatusBadge status="running" />
<StatusBadge status="failed" />
```

Props:
- `status` (string): Status to display - `"queued"`, `"running"`, `"completed"`, `"failed"`, or custom
- `className` (optional, string): Additional Tailwind classes

Automatically applies color-coding:
- **Queued**: Gray
- **Running**: Blue
- **Completed**: Green
- **Failed**: Red

### Accessibility

All components follow accessibility best practices:

- **Semantic HTML**: Uses appropriate HTML elements (`<header>`, `<button>`, `<main>`)
- **ARIA Labels**: Includes `role` and `aria-label` attributes where appropriate
- **Focus States**: Visible focus indicators with `focus:ring` styles
- **Color Contrast**: Meets WCAG AA standards with high-contrast defaults
- **Keyboard Navigation**: All interactive elements are keyboard accessible

## Styling with Tailwind CSS

### Utility Classes

Tailwind provides utility classes for common styles:

```tsx
<div className="flex items-center gap-4 rounded-lg bg-white p-6 shadow">
  <span className="text-sm font-medium text-gray-900">Label</span>
</div>
```

### Responsive Design

Use responsive prefixes for breakpoint-specific styles:

```tsx
<div className="px-4 sm:px-6 lg:px-8">
  {/* 4px padding on mobile, 6px on sm+, 8px on lg+ */}
</div>
```

Breakpoints:
- `sm`: 640px
- `md`: 768px
- `lg`: 1024px
- `xl`: 1280px
- `2xl`: 1536px

### Customization

Extend Tailwind in `tailwind.config.js`:

```js
export default {
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0f9ff',
          // ... more shades
        }
      },
    },
  },
}
```

## Deployment

### Cloud Run Deployment

1. **Build the Docker image:**

Create `webapp/Dockerfile`:

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
```

2. **Create nginx configuration (`webapp/nginx.conf`):**

```nginx
events {
  worker_connections 1024;
}

http {
  include /etc/nginx/mime.types;
  default_type application/octet-stream;
  
  server {
    listen 8080;
    root /usr/share/nginx/html;
    index index.html;
    
    location / {
      try_files $uri $uri/ /index.html;
    }
  }
}
```

3. **Build and deploy to Cloud Run:**

```bash
# Build the container
gcloud builds submit --tag gcr.io/PROJECT_ID/consensus-web

# Deploy to Cloud Run
gcloud run deploy consensus-web \
  --image gcr.io/PROJECT_ID/consensus-web \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "VITE_API_BASE_URL=https://api.example.com"
```

### Environment Variables in Cloud Run

Set environment variables at deploy time:

```bash
gcloud run deploy consensus-web \
  --set-env-vars "VITE_API_BASE_URL=https://api.example.com,VITE_ENVIRONMENT=production"
```

Or use a `.env.yaml` file:

```yaml
VITE_API_BASE_URL: "https://api.example.com"
VITE_ENVIRONMENT: "production"
VITE_POLLING_INTERVAL_MS: "5000"
```

Deploy with env file:

```bash
gcloud run deploy consensus-web --env-vars-file .env.yaml
```

### Static Hosting (Alternative)

For simple deployments, use static hosting:

1. **Build the app:**

```bash
npm run build
```

2. **Deploy to Cloud Storage + CDN:**

```bash
gsutil -m rsync -r dist/ gs://my-bucket/
gsutil iam ch allUsers:objectViewer gs://my-bucket
gsutil web set -m index.html -e index.html gs://my-bucket
```

3. **Configure Cloud CDN:**

```bash
gcloud compute backend-buckets create consensus-web-backend \
  --gcs-bucket-name=my-bucket

gcloud compute url-maps create consensus-web-map \
  --default-backend-bucket=consensus-web-backend
```

## Troubleshooting

### CORS Errors

**Symptom:** Browser console shows CORS policy errors

**Solutions:**
1. Verify backend `CORS_ORIGINS` includes your frontend URL
2. Restart the backend after changing CORS configuration
3. Check browser DevTools Network tab for CORS headers
4. Ensure credentials are included in requests (set by default in `src/api/client.ts`)

### API Connection Failed

**Symptom:** Health check shows "unhealthy" status

**Solutions:**
1. Verify `VITE_API_BASE_URL` is correct
2. Check backend is running: `curl http://localhost:8000/health`
3. Verify CORS configuration allows frontend origin
4. Check browser DevTools Console for error messages
5. Try accessing API directly in browser to rule out network issues

### Build Errors

**Symptom:** `npm run build` fails with TypeScript errors

**Solutions:**
1. Run `npm run typecheck` to see detailed type errors
2. Regenerate API client if backend types changed: `npm run generate:api`
3. Clear node_modules and reinstall: `rm -rf node_modules && npm install`
4. Check for incompatible dependency versions: `npm audit`

### OpenAPI Client Generation Failed

**Symptom:** `npm run generate:api` fails

**Solutions:**
1. Ensure backend dependencies are installed: `pip install -e .` (in repo root)
2. Verify backend can start: `python -m consensus_engine.app`
3. Check `openapi.json` was created in `webapp/` directory
4. Try generating manually:
   ```bash
   cd webapp
   npx openapi-typescript-codegen --input openapi.json --output src/api/generated --client axios
   ```

### Environment Variables Not Loading

**Symptom:** `config.apiBaseUrl` shows default value

**Solutions:**
1. Ensure `.env` file exists in `webapp/` directory
2. Restart dev server after changing `.env` (HMR doesn't reload env vars)
3. Verify variable names start with `VITE_` prefix
4. Check for syntax errors in `.env` file
5. Use `console.log(import.meta.env)` to debug available variables

## Development Best Practices

### Code Organization

- **Components**: One component per file, co-located styles if needed
- **API Calls**: Use generated services, don't call `fetch()` directly
- **State Management**: Start with React `useState`, add context/library as needed
- **Types**: Prefer imported API types over manual type definitions

### Performance

- **Code Splitting**: Use dynamic imports for large components
  ```tsx
  const HeavyComponent = lazy(() => import('./HeavyComponent'));
  ```
- **Memoization**: Use `React.memo()` and `useMemo()` for expensive renders
- **Image Optimization**: Use WebP format and lazy loading

### Security

- **No Secrets in Code**: Never commit API keys or tokens
- **Environment Variables**: Use `.env.local` for local secrets (gitignored)
- **Input Validation**: Validate user input before API calls
- **XSS Prevention**: React escapes by default, be careful with `dangerouslySetInnerHTML`

## Maintenance

### Updating Dependencies

Check for outdated packages:

```bash
npm outdated
```

Update dependencies:

```bash
npm update
```

Update to latest major versions:

```bash
npm install react@latest react-dom@latest
npm install -D vite@latest typescript@latest
```

### Regenerating API Client

When backend API changes, always regenerate the client:

```bash
npm run generate:api
```

Commit the generated files to version control:

```bash
git add src/api/generated/
git commit -m "Update API client from backend changes"
```

### Monitoring

In production, monitor:
- **Error Rates**: Use error boundaries and logging
- **Performance**: Core Web Vitals (LCP, FID, CLS)
- **API Latency**: Track API call durations
- **User Sessions**: Analytics for usage patterns

## Additional Resources

- [Vite Documentation](https://vitejs.dev/)
- [React Documentation](https://react.dev/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [TypeScript Documentation](https://www.typescriptlang.org/docs/)
- [OpenAPI TypeScript Codegen](https://github.com/ferdikoomen/openapi-typescript-codegen)
