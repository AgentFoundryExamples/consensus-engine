# Consensus Engine

A FastAPI-based backend service with LLM integration for consensus building. This project provides a production-ready Python API with OpenAI integration, asynchronous job processing, configuration management, and comprehensive testing.

## Features

- **FastAPI Backend**: Modern async Python web framework
- **LLM Integration**: OpenAI GPT-5.1 support with configurable parameters
- **Multi-Persona Consensus**: Five specialized personas for comprehensive proposal review
- **Asynchronous Processing**: Pub/Sub-based worker for background job execution
- **Configuration Management**: Pydantic-based settings with validation
- **Structured Logging**: Environment-aware logging configuration with lifecycle events
- **Database Persistence**: PostgreSQL with versioned run tracking and step progress
- **Dependency Injection**: Clean separation of concerns
- **Comprehensive Testing**: Unit and integration tests with pytest

## Multi-Persona Consensus System

The Consensus Engine employs a multi-persona approach to evaluate proposals from diverse perspectives, ensuring comprehensive analysis and balanced decision-making.

### Personas

The system includes five specialized personas, each with distinct expertise and focus areas:

#### 1. Architect (Weight: 0.25)
- **Focus**: System design, scalability, maintainability, and technical architecture
- **Role**: Evaluates proposals for architectural soundness, design patterns, and long-term viability
- **Evaluates**: Design quality, scalability concerns, architectural patterns, technical debt

#### 2. Critic (Weight: 0.25)
- **Focus**: Risks, edge cases, potential failures, and implementation challenges
- **Role**: Provides skeptical analysis to ensure thorough consideration of downsides
- **Evaluates**: Risk factors, edge cases, failure modes, implementation complexity

#### 3. Optimist (Weight: 0.15)
- **Focus**: Strengths, opportunities, and positive aspects
- **Role**: Balances critical feedback with recognition of good ideas and feasible approaches
- **Evaluates**: Proposal strengths, feasibility, practical opportunities, potential for success

#### 4. SecurityGuardian (Weight: 0.20)
- **Focus**: Security vulnerabilities, data protection, authentication, authorization
- **Role**: Security expert with **veto power** through `security_critical` blocking issues
- **Evaluates**: Security risks, vulnerabilities, compliance, data protection, authentication

**Veto Power**: The SecurityGuardian can mark blocking issues with `security_critical: true`, giving these issues special weight in decision aggregation. This ensures critical security concerns cannot be overlooked.

#### 5. UserAdvocate (Weight: 0.15)
- **Focus**: Usability, user experience, accessibility, and value delivery
- **Role**: Advocates for user needs and practical utility
- **Evaluates**: UX quality, accessibility, user value, ease of use

### Consensus Thresholds

Decision outcomes are determined by weighted confidence scores:

- **Approve**: `weighted_confidence >= 0.80` (and no blocking issues)
- **Revise**: `0.60 <= weighted_confidence < 0.80` (and no blocking issues)
- **Reject**: `weighted_confidence < 0.60` or has blocking issues

### Consensus Configuration

All personas share a common configuration:
- **Temperature**: 0.2 (low temperature for deterministic, consistent reviews)
- **Weights**: Sum to exactly 1.0 for proper aggregation
- **Model**: Uses configured `REVIEW_MODEL` (default: gpt-5.1)

The persona weights and thresholds are defined in `src/consensus_engine/config/personas.py` and validated at startup to ensure correctness.

## Project Structure

```
consensus-engine/
├── src/
│   └── consensus_engine/
│       ├── api/          # API route handlers
│       ├── clients/      # External service clients (OpenAI, Pub/Sub)
│       ├── config/       # Configuration and settings
│       ├── db/           # Database models and repositories
│       ├── schemas/      # Pydantic models and versioned schema registry
│       ├── services/     # Business logic services
│       ├── workers/      # Background workers (pipeline processor)
│       └── app.py        # FastAPI application factory
├── tests/
│   ├── unit/            # Unit tests
│   └── integration/     # Integration tests
├── docs/                # Documentation
├── migrations/          # Alembic database migrations
├── pyproject.toml       # Project metadata and dependencies
├── .env.example         # Example environment configuration
└── README.md
```

## Architecture

The Consensus Engine uses an asynchronous architecture with separate API and worker components:

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│   Client    │────▶│  API Server │────▶│    Pub/Sub       │
│             │◀────│  (FastAPI)  │     │     Queue        │
└─────────────┘     └─────────────┘     └──────────────────┘
                           │                      │
                           ▼                      ▼
                    ┌─────────────┐     ┌──────────────────┐
                    │  PostgreSQL │◀────│ Pipeline Worker  │
                    │   Database  │     │   (Background)   │
                    └─────────────┘     └──────────────────┘
```

### API Server
- Handles HTTP requests (expand, review, full-review, runs)
- Validates inputs and enqueues jobs to Pub/Sub
- Returns job status and run details
- Serves health checks and metrics

### Pipeline Worker
- Consumes messages from Pub/Sub subscription
- Executes full consensus pipeline (expand → reviews → aggregation)
- Updates database with progress and results
- Handles retries, failures, and idempotency

See [Worker Deployment Guide](docs/WORKER_DEPLOYMENT.md) for deployment details.

## Documentation

- [Schema Registry](docs/SCHEMA_REGISTRY.md) - Versioned schema management and JSON contract versioning
- [Worker Deployment Guide](docs/WORKER_DEPLOYMENT.md) - Production deployment and monitoring
- [Multi-Persona Orchestration](docs/MULTI_PERSONA_ORCHESTRATION.md) - Consensus building architecture
- [Async Run Persistence](docs/async_run_persistence.md) - Database persistence patterns

## Quick Start

### Prerequisites

- Python 3.11 or higher
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd consensus-engine
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e .
```

For development with testing and linting tools:
```bash
pip install -e ".[dev]"
```

### Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your OpenAI API key:
```bash
OPENAI_API_KEY=your_actual_api_key_here
OPENAI_MODEL=gpt-5.1
TEMPERATURE=0.7
ENV=development
```

#### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | Your OpenAI API key for authentication |
| `OPENAI_MODEL` | No | `gpt-5.1` | Default OpenAI model to use |
| `TEMPERATURE` | No | `0.7` | Default temperature for model responses (0.0-1.0) |
| `EXPAND_MODEL` | No | `gpt-5.1` | Model for expansion step |
| `EXPAND_TEMPERATURE` | No | `0.7` | Temperature for expansion (0.0-1.0) |
| `REVIEW_MODEL` | No | `gpt-5.1` | Model for review step |
| `REVIEW_TEMPERATURE` | No | `0.2` | Temperature for review (0.0-1.0, lower for deterministic reviews) |
| `DEFAULT_PERSONA_NAME` | No | `GenericReviewer` | Default persona name for reviews |
| `DEFAULT_PERSONA_INSTRUCTIONS` | No | See settings.py | Default persona instructions for reviews |
| `ENV` | No | `development` | Environment mode: development, production, testing |

**Database Configuration:**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USE_CLOUD_SQL_CONNECTOR` | No | `false` | Use Cloud SQL Python Connector for IAM authentication |
| `DB_INSTANCE_CONNECTION_NAME` | Cloud SQL | - | Cloud SQL instance (format: project:region:instance) |
| `DB_NAME` | No | `consensus_engine` | Database name |
| `DB_USER` | No | `postgres` | Database user |
| `DB_PASSWORD` | Local | - | Database password (not used with IAM auth) |
| `DB_HOST` | No | `localhost` | Database host for local connections |
| `DB_PORT` | No | `5432` | Database port for local connections |
| `DB_IAM_AUTH` | No | `false` | Use IAM authentication with Cloud SQL |
| `DB_POOL_SIZE` | No | `5` | Database connection pool size (1-100) |
| `DB_MAX_OVERFLOW` | No | `10` | Maximum overflow connections (0-100) |
| `DB_POOL_TIMEOUT` | No | `30` | Connection pool timeout in seconds (1-300) |
| `DB_POOL_RECYCLE` | No | `3600` | Connection pool recycle time in seconds (60-7200) |

**Google Cloud Pub/Sub Configuration:**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PUBSUB_PROJECT_ID` | Production | - | Google Cloud project ID for Pub/Sub (required for production) |
| `PUBSUB_TOPIC` | No | `consensus-engine-jobs` | Pub/Sub topic name for job queue |
| `PUBSUB_SUBSCRIPTION` | No | `consensus-engine-jobs-sub` | Pub/Sub subscription name for worker |
| `PUBSUB_CREDENTIALS_FILE` | Local Dev | - | Path to service account JSON credentials file |
| `PUBSUB_EMULATOR_HOST` | No | - | Pub/Sub emulator host (e.g., localhost:8085) for local testing |
| `PUBSUB_USE_MOCK` | No | `false` | Use mock publisher for testing (no-op that logs messages) |

**Worker Configuration:**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WORKER_MAX_CONCURRENCY` | No | `10` | Maximum concurrent message handlers (1-1000) |
| `WORKER_ACK_DEADLINE_SECONDS` | No | `600` | Pub/Sub ack deadline in seconds (60-3600) |
| `WORKER_STEP_TIMEOUT_SECONDS` | No | `300` | Per-step timeout in seconds (10-1800) |
| `WORKER_JOB_TIMEOUT_SECONDS` | No | `1800` | Overall job timeout in seconds (60-7200) |

**Pub/Sub Deployment Modes:**

The API supports multiple modes for Pub/Sub integration:

- **Production Mode**: Uses Application Default Credentials (ADC) or service account credentials
  - Set `PUBSUB_PROJECT_ID` to your Google Cloud project ID
  - On Cloud Run/GCE, ADC is automatically available
  - For local deployment with real Pub/Sub, set `PUBSUB_CREDENTIALS_FILE` to your service account JSON file

- **Emulator Mode**: Uses Pub/Sub emulator for local testing
  - Set `PUBSUB_EMULATOR_HOST` to your emulator address (e.g., `localhost:8085`)
  - Project ID can be any non-empty string when using emulator

- **Mock Mode**: Uses no-op publisher for testing without Pub/Sub
  - Set `PUBSUB_USE_MOCK=true`
  - Messages are logged but not sent to Pub/Sub
  - Useful for local development without emulator or credentials

**Temperature Guidelines:**
- Range: 0.0 to 1.0
- **Expansion (0.7)**: Balanced creativity for generating comprehensive proposals
- **Review (0.2)**: Deterministic and focused for consistent, reliable reviews
- Lower values (0.0-0.3): More deterministic, focused
- Higher values (0.8-1.0): More creative, varied

**Step-Specific Configuration:**
The Consensus Engine supports separate model and temperature settings for different steps:
- **Expansion**: Generates detailed proposals from brief ideas
- **Review**: Evaluates proposals with persona-based analysis

This allows you to use different models or settings optimized for each task.

### Database Setup

The Consensus Engine uses PostgreSQL for durable storage with support for both local development and Cloud SQL deployments.

#### Local Development with Docker Compose

The easiest way to run PostgreSQL locally is using Docker Compose:

1. Start the database and admin tools:
```bash
docker-compose up -d
```

This starts:
- PostgreSQL 16 on port 5432
- pgAdmin 4 on port 5050 (http://localhost:5050)
  - Default email: `admin@consensus-engine.local`
  - Default password: `admin`

2. Run database migrations:
```bash
alembic upgrade head
```

3. Verify the database connection:
```bash
# Connect with psql
docker-compose exec postgres psql -U postgres -d consensus_engine

# Or use pgAdmin at http://localhost:5050
```

To stop the services:
```bash
docker-compose down
```

To reset the database:
```bash
docker-compose down -v  # Remove volumes
docker-compose up -d
alembic upgrade head
```

#### Manual PostgreSQL Installation

If you prefer to install PostgreSQL manually:

1. Install PostgreSQL 16+ on your system
2. Create the database:
```bash
createdb consensus_engine
```
3. Update `.env` with your database credentials:
```bash
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=consensus_engine
```
4. Run migrations:
```bash
alembic upgrade head
```

#### Cloud SQL (Production)

For Cloud Run deployments with Cloud SQL:

1. Create a Cloud SQL PostgreSQL instance
2. Create a database named `consensus_engine`
3. Configure service account with `cloudsql.client` role
4. Set environment variables in Cloud Run:

```bash
USE_CLOUD_SQL_CONNECTOR=true
DB_INSTANCE_CONNECTION_NAME=project:region:instance
DB_NAME=consensus_engine
DB_USER=your-db-user
DB_IAM_AUTH=true  # Recommended for IAM authentication
# Or use password authentication:
# DB_IAM_AUTH=false
# DB_PASSWORD=your-password
```

5. Run migrations using Cloud SQL proxy or from a connection with access:
```bash
# With Cloud SQL proxy
cloud_sql_proxy -instances=project:region:instance=tcp:5432 &
alembic upgrade head
```

**IAM Authentication:**
- Requires service account with `cloudsql.client` role
- No password needed
- More secure than password authentication
- Recommended for production

**Connection Pooling:**
- Configured via `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE`
- Cloud SQL Connector manages its own connection pool
- Local connections use SQLAlchemy's QueuePool

#### Database Migrations

The project uses Alembic for database migrations:

```bash
# Run all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current migration version
alembic current

# Show migration history
alembic history

# Create a new migration (after modifying models)
alembic revision --autogenerate -m "description"
```

All migrations are idempotent and can be run multiple times safely.

### Asynchronous Job Execution

The Consensus Engine uses Google Cloud Pub/Sub for asynchronous job processing. When you submit a review request, the API:

1. **Creates a Run** with `status='queued'` in the database
2. **Initializes StepProgress** entries for all pipeline steps (expand, review_*, aggregate_decision)
3. **Publishes a job message** to Pub/Sub containing run_id, run_type, priority, and request payload
4. **Returns immediately** with run_id and status='queued'

Clients should poll `GET /v1/runs/{run_id}` to check job status and retrieve results once processing completes.

**Job Message Structure:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "run_type": "initial",  // or "revision"
  "priority": "normal",   // or "high"
  "payload": {
    "idea": "Build a REST API...",
    "extra_context": {...},
    "parameters": {...}
  }
}
```

**Run Lifecycle:**
1. `queued` → Job enqueued, waiting for worker pickup
2. `running` → Worker processing job (not yet implemented)
3. `completed` → Job finished successfully with results
4. `failed` → Job failed with error details

**Benefits:**
- **Fast response times**: API returns immediately without waiting for LLM calls
- **Scalability**: Workers can process jobs independently
- **Fault tolerance**: Failed jobs can be retried without affecting API availability
- **Queue management**: Priority-based job ordering

**Note**: Worker implementation is not yet complete. This release focuses on job enqueueing; worker processing will be added in a future release.

### Running the Application

The Consensus Engine consists of two components:

#### 1. API Server

Start the development server:
```bash
uvicorn consensus_engine.app:app --reload
```

The API will be available at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

#### 2. Pipeline Worker

Start the background worker to process jobs:
```bash
python -m consensus_engine.workers.pipeline_worker
```

The worker will consume messages from the configured Pub/Sub subscription and process them asynchronously.

**Worker Modes:**

- **Local Development** (with emulator):
  ```bash
  # Start Pub/Sub emulator first
  docker run -d -p 8085:8085 \
    gcr.io/google.com/cloudsdktool/cloud-sdk:emulators \
    gcloud beta emulators pubsub start --host-port=0.0.0.0:8085
  
  # Set environment
  export PUBSUB_EMULATOR_HOST=localhost:8085
  
  # Run worker
  python -m consensus_engine.workers.pipeline_worker
  ```

- **Production** (with real Pub/Sub):
  ```bash
  # Worker automatically uses Application Default Credentials
  python -m consensus_engine.workers.pipeline_worker
  ```

See [Worker Deployment Guide](docs/WORKER_DEPLOYMENT.md) for detailed deployment instructions.

### Running Tests

Run all tests:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=consensus_engine --cov-report=html
```

Run specific test categories:
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific test file
pytest tests/unit/test_config.py
```

### Code Quality

Format and lint code:
```bash
# Format with ruff
ruff format src/ tests/

# Lint with ruff
ruff check src/ tests/

# Type checking with mypy
mypy src/
```

## API Endpoints

### Review Idea (POST /v1/review-idea)

Orchestrates idea expansion, review, and decision aggregation in a single synchronous request. This endpoint expands a brief idea into a detailed proposal, reviews it with a GenericReviewer persona, and aggregates a draft decision.

**Request:**
```bash
POST /v1/review-idea
Content-Type: application/json
```

**Request Body:**
```json
{
  "idea": "Build a REST API for user management with authentication.",
  "extra_context": {
    "language": "Python",
    "version": "3.11+",
    "features": ["auth", "CRUD"]
  }
}
```

**Parameters:**
- `idea` (required, string): The core idea to expand and review (1-10 sentences)
- `extra_context` (optional, dict or string): Additional context or constraints

**Success Response (200):**
```json
{
  "expanded_proposal": {
    "problem_statement": "Clear articulation of the problem to be solved",
    "proposed_solution": "Detailed description of the solution approach",
    "assumptions": ["Assumption 1", "Assumption 2"],
    "scope_non_goals": ["Out of scope item 1"],
    "raw_expanded_proposal": "Complete proposal text...",
    "metadata": {
      "request_id": "expand-550e8400-e29b-41d4-a716-446655440000",
      "model": "gpt-5.1",
      "temperature": 0.7,
      "elapsed_time": 2.5
    }
  },
  "reviews": [
    {
      "persona_name": "GenericReviewer",
      "confidence_score": 0.85,
      "strengths": ["Good architecture", "Clear scope"],
      "concerns": [
        {
          "text": "Missing error handling",
          "is_blocking": false
        }
      ],
      "recommendations": ["Add error handling", "Include monitoring"],
      "blocking_issues": [],
      "estimated_effort": "2-3 weeks",
      "dependency_risks": ["Database setup"]
    }
  ],
  "draft_decision": {
    "overall_weighted_confidence": 0.85,
    "decision": "approve",
    "score_breakdown": {
      "GenericReviewer": {
        "weight": 1.0,
        "notes": "Single persona review with confidence 0.85"
      }
    },
    "minority_report": null
  },
  "run_id": "run-550e8400-e29b-41d4-a716-446655440000",
  "elapsed_time": 5.2
}
```

**Response Fields:**
- `expanded_proposal`: The expanded proposal with problem statement, solution, assumptions, scope, and metadata
- `reviews`: Array containing exactly one PersonaReview from GenericReviewer
- `draft_decision`: Aggregated decision with weighted confidence and score breakdown
  - For a single persona, `overall_weighted_confidence` equals the reviewer's confidence score
  - `decision` is "approve" (confidence ≥ 0.7, no blocking issues), "revise" (confidence < 0.7, no blocking issues), or "reject" (has blocking issues)
  - `score_breakdown` shows the persona's weight (1.0 for single persona) and notes
  - `minority_report` is always null for single-persona reviews
- `run_id`: Unique identifier for this orchestration run (different from individual request_ids)
- `elapsed_time`: Total wall time for the entire orchestration (expand + review + aggregate) in seconds

**Error Responses:**

All error responses include structured information about which step failed and any partial results:

```json
{
  "code": "LLM_SERVICE_ERROR",
  "message": "Failed to process request",
  "failed_step": "expand",
  "run_id": "run-550e8400-e29b-41d4-a716-446655440000",
  "partial_results": null,
  "details": {}
}
```

**Error Fields:**
- `code`: Machine-readable error code (see Error Handling section)
- `message`: Human-readable error message
- `failed_step`: Which step failed: "validation", "expand", "review", or "aggregate"
- `run_id`: Unique identifier for this orchestration run
- `partial_results`: Partial results if available (e.g., `{"expanded_proposal": {...}}` if review failed)
- `details`: Additional error details (e.g., `{"retryable": true}`)

**Status Codes:**
- **200 OK**: Successfully completed all steps (expand, review, aggregate)
- **422 Unprocessable Entity**: Validation error (empty idea, too many sentences, etc.)
- **401 Unauthorized**: Invalid API key
- **503 Service Unavailable**: Rate limit exceeded or timeout
- **500 Internal Server Error**: Service error during expansion, review, or aggregation

**Error Scenarios:**
- **Expansion failure**: `failed_step="expand"`, `partial_results=null`
- **Review failure**: `failed_step="review"`, `partial_results` includes the expanded proposal
- **Aggregation failure**: `failed_step="aggregate"`, `partial_results` includes expanded proposal and reviews

**Example with curl:**
```bash
curl -X POST http://localhost:8000/v1/review-idea \
  -H "Content-Type: application/json" \
  -d '{"idea": "Build a REST API for user management with authentication."}'
```

**Orchestration Flow:**
1. **Expand**: Transforms the brief idea into a comprehensive proposal (uses `EXPAND_MODEL` and `EXPAND_TEMPERATURE`)
2. **Review**: Evaluates the proposal with GenericReviewer persona (uses `REVIEW_MODEL` and `REVIEW_TEMPERATURE`)
3. **Aggregate**: Computes draft decision from the single review

**Important Notes:**
- Model and temperature settings are controlled server-side and cannot be overridden by clients
- Each request generates a unique `run_id` for tracking the orchestration
- Logging emits per-request records with `run_id`, elapsed time, and step statuses
- Sequential orchestration means total `elapsed_time` is the sum of expand + review + aggregate times
- No background jobs or persistent storage—all operations are synchronous

### Full Review (POST /v1/full-review)

Enqueues a job to expand an idea and review it with all five personas (Architect, Critic, Optimist, SecurityGuardian, UserAdvocate). The API creates a Run with `status='queued'`, publishes a job message to Pub/Sub, and returns immediately with run_id for status polling.

**Request:**
```bash
POST /v1/full-review
Content-Type: application/json
```

**Request Body:**
```json
{
  "idea": "Build a REST API for user management with authentication.",
  "extra_context": {
    "language": "Python",
    "version": "3.11+",
    "features": ["auth", "CRUD"]
  }
}
```

**Parameters:**
- `idea` (required, string): The core idea to expand and review with all personas (1-10 sentences)
- `extra_context` (optional, dict or string): Additional context or constraints

**Success Response (202 Accepted):**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "run_type": "initial",
  "priority": "normal",
  "created_at": "2026-01-08T04:00:00.000000Z",
  "queued_at": "2026-01-08T04:00:00.000000Z",
  "message": "Full review job enqueued successfully. Poll GET /v1/runs/550e8400-e29b-41d4-a716-446655440000 for status."
}
```

**Response Fields:**
- `run_id`: Unique identifier for this run (use this to poll for status and results)
- `status`: Current status of the run (`queued`)
- `run_type`: Type of run (`initial` for new reviews, `revision` for re-reviews)
- `priority`: Priority level (`normal` or `high`)
- `created_at`: ISO 8601 timestamp when run was created
- `queued_at`: ISO 8601 timestamp when job was enqueued
- `message`: Human-readable message with polling instructions

**Polling for Results:**

After receiving the 202 response, poll `GET /v1/runs/{run_id}` to check status:

```bash
GET /v1/runs/550e8400-e29b-41d4-a716-446655440000
```

The response will include:
- Current `status` (`queued`, `running`, `completed`, or `failed`)
- When `status='completed'`: Full results including expanded_proposal, persona_reviews, and decision
- When `status='failed'`: Error details

**Job Processing:**
1. Worker picks up the job from Pub/Sub (when worker is implemented)
2. Expands the idea into a detailed proposal
3. Reviews with all five personas
4. Aggregates final decision
5. Updates run status to `completed` with results

**Status Codes:**
- **202 Accepted**: Job enqueued successfully
- **422 Unprocessable Entity**: Validation error (empty idea, too many sentences, etc.)
- **503 Service Unavailable**: Pub/Sub publish failed (database changes rolled back)
- **500 Internal Server Error**: Database error or unexpected failure

**Error Responses:**

Pub/Sub publish failure (503):
```json
{
  "code": "PUBSUB_PUBLISH_ERROR",
  "message": "Failed to enqueue job: Pub/Sub publish failed",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "details": {"error": "..."}
}
```

Database failure (500):
```json
{
  "code": "DATABASE_ERROR",
  "message": "Failed to create run: Database operation failed",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "details": {"error": "..."}
}
```

**Orchestration Flow (Worker - Not Yet Implemented):**
1. **Expand**: Transforms the brief idea into a comprehensive proposal (uses `EXPAND_MODEL` and `EXPAND_TEMPERATURE`)
2. **Review**: Evaluates the proposal with all five personas (Architect, Critic, Optimist, SecurityGuardian, UserAdvocate) using `REVIEW_MODEL` and `REVIEW_TEMPERATURE`
3. **Aggregate**: Computes final decision from weighted consensus of all persona reviews

Once the worker completes processing, the run will include full results with:
- `expanded_proposal`: Detailed proposal with problem statement, solution, assumptions, and scope
- `persona_reviews`: Array of five PersonaReview objects (one per persona)
- `decision`: Aggregated decision with weighted confidence, score breakdown, and minority report

See the **Multi-Persona Consensus System** section for details on personas, weights, and decision thresholds.

**Important Notes:**
    }
  ],
  "decision": {
    "overall_weighted_confidence": 0.808,
    "weighted_confidence": 0.808,
    "decision": "approve",
    "detailed_score_breakdown": {
      "weights": {
        "architect": 0.25,
        "critic": 0.25,
        "optimist": 0.15,
        "security_guardian": 0.20,
        "user_advocate": 0.15
      },
      "individual_scores": {
        "architect": 0.85,
        "critic": 0.75,
        "optimist": 0.90,
        "security_guardian": 0.70,
        "user_advocate": 0.82
      },
      "weighted_contributions": {
        "architect": 0.2125,
        "critic": 0.1875,
        "optimist": 0.135,
        "security_guardian": 0.14,
        "user_advocate": 0.123
      },
      "formula": "weighted_confidence = sum(weight_i * score_i for each persona i) = 0.808"
    },
    "minority_reports": null
  },
  "run_id": "run-550e8400-e29b-41d4-a716-446655440000",
  "elapsed_time": 15.2
}
```

**Response Fields:**
- `expanded_proposal`: The expanded proposal with problem statement, solution, assumptions, scope, and metadata
- `persona_reviews`: Array containing exactly five PersonaReview objects from all personas in configuration order:
  - `architect`: System design and architecture (weight: 0.25)
  - `critic`: Risks and edge cases (weight: 0.25)
  - `optimist`: Strengths and opportunities (weight: 0.15)
  - `security_guardian`: Security concerns with veto power (weight: 0.20)
  - `user_advocate`: User experience and value (weight: 0.15)
- `decision`: Aggregated decision with weighted confidence and detailed breakdown
  - `overall_weighted_confidence`: Weighted average of persona confidence scores
  - `decision`: "approve" (confidence ≥ 0.80, no critical issues), "revise" (0.60 ≤ confidence < 0.80), or "reject" (confidence < 0.60 or has blocking issues)
  - `detailed_score_breakdown`: Complete breakdown showing weights, individual scores, weighted contributions, and formula
  - `minority_reports`: Array of dissenting personas when decision is approve/revise but some personas have concerns (see Multi-Persona Consensus section)
- `run_id`: Unique identifier for this orchestration run (different from individual request_ids)
- `elapsed_time`: Total wall time for the entire orchestration (expand + all reviews + aggregate) in seconds

**Decision Thresholds:**
- **Approve**: `weighted_confidence >= 0.80` and no blocking issues
- **Revise**: `0.60 <= weighted_confidence < 0.80` and no blocking issues
- **Reject**: `weighted_confidence < 0.60` or has blocking issues

**SecurityGuardian Veto Power:**
- If SecurityGuardian marks a blocking issue with `security_critical: true`, the decision is downgraded from "approve" to at least "revise"
- This ensures critical security concerns cannot be overlooked even with high overall confidence

**Minority Reports:**
Minority reports are generated for dissenting personas when:
- Final decision is "approve" but a persona has confidence < 0.60
- Final decision is "approve" or "revise" but a persona has blocking issues

Each minority report includes:
- Persona name and ID
- Confidence score
- Summary of blocking issues or concerns
- Mitigation recommendations

**Error Responses:**

All error responses include structured information about which step failed and any partial results:

```json
{
  "code": "LLM_SERVICE_ERROR",
  "message": "Failed to process request",
  "failed_step": "review",
  "run_id": "run-550e8400-e29b-41d4-a716-446655440000",
  "partial_results": {
    "expanded_proposal": {
      "problem_statement": "...",
      "proposed_solution": "..."
    }
  },
  "details": {}
}
```

**Error Fields:**
- `code`: Machine-readable error code (see Error Handling section)
- `message`: Human-readable error message
- `failed_step`: Which step failed: "validation", "expand", "review", or "aggregate"
- `run_id`: Unique identifier for this orchestration run
- `partial_results`: Partial results if available:
  - `{"expanded_proposal": {...}}` if review or aggregate failed
  - `{"expanded_proposal": {...}, "persona_reviews": [...]}` if only aggregate failed
- `details`: Additional error details (e.g., `{"retryable": true}`)

**Status Codes:**
- **200 OK**: Successfully completed all steps (expand, all persona reviews, aggregate)
- **422 Unprocessable Entity**: Validation error (empty idea, too many sentences, etc.)
- **401 Unauthorized**: Invalid API key
- **503 Service Unavailable**: Rate limit exceeded or timeout
- **500 Internal Server Error**: Service error during expansion, review, or aggregation

**Error Scenarios:**
- **Expansion failure**: `failed_step="expand"`, `partial_results=null`
- **Review failure**: `failed_step="review"`, `partial_results` includes the expanded proposal
  - Note: If any single persona review fails, the entire review step fails (deterministic failure)
- **Aggregation failure**: `failed_step="aggregate"`, `partial_results` includes expanded proposal and all persona reviews

**Example with curl:**
```bash
curl -X POST http://localhost:8000/v1/full-review \
  -H "Content-Type: application/json" \
  -d '{"idea": "Build a REST API for user management with authentication."}'
```

**Orchestration Flow:**
1. **Expand**: Transforms the brief idea into a comprehensive proposal (uses `EXPAND_MODEL` and `EXPAND_TEMPERATURE`)
2. **Review**: Evaluates the proposal with all five personas sequentially (uses `REVIEW_MODEL` and `PERSONA_TEMPERATURE=0.2`)
3. **Aggregate**: Computes final decision using weighted consensus algorithm with thresholds and veto rules

**Important Notes:**
- **Deterministic Failure**: All five persona reviews must succeed. If any single persona fails, the entire review step fails and returns an error with partial results.
- **Persona Ordering**: Reviews are executed and returned in configuration order (architect, critic, optimist, security_guardian, user_advocate) for consistent behavior.
- **No Partial Results**: The endpoint only returns success (200) when all personas complete successfully. No partial persona lists are exposed.
- Model and temperature settings are controlled server-side and cannot be overridden by clients.
- Each request generates a unique `run_id` for tracking the orchestration.
- Logging emits per-request records with `run_id`, elapsed time, and step statuses.
- Sequential orchestration means total `elapsed_time` includes expand time + all persona review times + aggregation time.
- No background jobs or persistent storage—all operations are synchronous.

**Performance Considerations:**
- Full review takes longer than single-persona review since it runs 5 persona reviews sequentially
- Typical elapsed time: 10-20 seconds depending on proposal complexity and API latency
- Consider using single-persona `/v1/review-idea` for faster feedback during iterative development
- Use `/v1/full-review` when comprehensive multi-perspective analysis is needed

### Expand Idea (POST /v1/expand-idea)

Expands a brief idea (1-10 sentences) into a comprehensive, structured proposal using LLM.

**Request:**
```bash
POST /v1/expand-idea
Content-Type: application/json
```

**Request Body:**
```json
{
  "idea": "Build a REST API for user management with authentication.",
  "extra_context": {
    "language": "Python",
    "version": "3.11+",
    "features": ["auth", "CRUD"]
  }
}
```

**Parameters:**
- `idea` (required, string): The core idea to expand (1-10 sentences)
- `extra_context` (optional, dict or string): Additional context or constraints

**Success Response (200):**
```json
{
  "problem_statement": "Clear articulation of the problem to be solved",
  "proposed_solution": "Detailed description of the solution approach",
  "assumptions": ["Assumption 1", "Assumption 2"],
  "scope_non_goals": ["Out of scope item 1"],
  "title": "Optional proposal title",
  "summary": "Optional brief summary",
  "raw_idea": "Original user idea",
  "raw_expanded_proposal": "Complete proposal text...",
  "metadata": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "model": "gpt-5.1",
    "temperature": 0.7,
    "elapsed_time": 2.5
  }
}
```

**Error Responses:**
- **422 Unprocessable Entity**: Validation error (empty idea, too many sentences, etc.)
- **401 Unauthorized**: Invalid API key
- **503 Service Unavailable**: Rate limit exceeded or timeout
- **500 Internal Server Error**: Service error

**Example with curl:**
```bash
curl -X POST http://localhost:8000/v1/expand-idea \
  -H "Content-Type: application/json" \
  -d '{"idea": "Build a REST API for user management."}'
```

### Health Check (GET /health)

Returns service health status, configuration metadata, and uptime.

**Request:**
```bash
GET /health
```

**Response (200):**
```json
{
  "status": "healthy",
  "environment": "production",
  "debug": false,
  "model": "gpt-5.1",
  "temperature": 0.7,
  "uptime_seconds": 3600.5,
  "config_status": "ok"
}
```

**Status Values:**
- `healthy`: Service is fully operational
- `degraded`: Service is operational but configuration has warnings
- `unhealthy`: Service has critical issues

**Config Status Values:**
- `ok`: Configuration is valid
- `warning`: Configuration has non-critical issues
- `error`: Configuration has critical issues

### Root (GET /)

Returns API information and links to documentation.

**Request:**
```bash
GET /
```

**Response (200):**
```json
{
  "message": "Consensus Engine API",
  "version": "0.1.0",
  "docs": "/docs"
}
```

### OpenAPI Documentation

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Services

### Expand Idea Service

The `expand_idea` service transforms brief ideas into comprehensive, structured proposals using OpenAI's GPT-5.1 with structured outputs.

**Key Features:**
- Accepts 1-10 sentence ideas with optional context
- Uses expansion-specific model and temperature settings
- Returns validated `ExpandedProposal` with problem statement, solution, assumptions, and scope
- Includes detailed telemetry (request_id, step_name='expand', model, temperature, latency)
- Structured error handling with proper exception types

**Usage:**
```python
from consensus_engine.services import expand_idea
from consensus_engine.schemas.proposal import IdeaInput
from consensus_engine.config import get_settings

settings = get_settings()
idea_input = IdeaInput(idea="Build a scalable API")
proposal, metadata = expand_idea(idea_input, settings)

print(f"Request ID: {metadata['request_id']}")
print(f"Step: {metadata['step_name']}")  # 'expand'
print(f"Latency: {metadata['latency']}s")
print(f"Problem: {proposal.problem_statement}")
```

### Review Proposal Service

The `review_proposal` service evaluates expanded proposals using persona-based analysis with OpenAI's structured outputs.

**Key Features:**
- Accepts `ExpandedProposal` objects with optional persona customization
- Uses review-specific model and temperature (default: 0.2 for deterministic reviews)
- Returns validated `PersonaReview` with confidence score, strengths, concerns, and recommendations
- Supports custom personas with specific instructions and perspectives
- Includes detailed telemetry (request_id, step_name='review', persona_name, model, temperature, latency)
- Automatically truncates long proposal fields to avoid token limits

**Usage:**
```python
from consensus_engine.services import review_proposal
from consensus_engine.config import get_settings

settings = get_settings()

# Use default persona (GenericReviewer)
review, metadata = review_proposal(proposal, settings)

print(f"Persona: {review.persona_name}")
print(f"Confidence: {review.confidence_score}")
print(f"Strengths: {review.strengths}")
print(f"Concerns: {review.concerns}")
print(f"Blocking Issues: {review.blocking_issues}")
print(f"Latency: {metadata['latency']}s")

# Use custom persona
review, metadata = review_proposal(
    proposal,
    settings,
    persona_name="SecurityExpert",
    persona_instructions="Focus on security vulnerabilities and data protection"
)
```

**PersonaReview Schema:**
```python
{
    "persona_name": "GenericReviewer",
    "confidence_score": 0.75,  # 0.0 to 1.0
    "strengths": ["Clear problem statement", "Good architecture"],
    "concerns": [
        {"text": "Missing error handling", "is_blocking": False},
        {"text": "No security design", "is_blocking": True}
    ],
    "recommendations": ["Add authentication", "Implement rate limiting"],
    "blocking_issues": ["Missing security audit plan"],
    "estimated_effort": "3-4 weeks for MVP",
    "dependency_risks": ["PostgreSQL cluster setup"]
}
```

#### Usage

```python
from consensus_engine.config import get_settings
from consensus_engine.schemas import IdeaInput
from consensus_engine.services import expand_idea

# Create input
idea_input = IdeaInput(
    idea="Build a REST API for user management",
    extra_context="Must support Python 3.11+ and include authentication"
)

# Get settings
settings = get_settings()

# Expand the idea
proposal, metadata = expand_idea(idea_input, settings)

# Access the structured proposal
print(proposal.problem_statement)
print(proposal.proposed_solution)
print(proposal.assumptions)
print(proposal.scope_non_goals)
```

#### Input Schema

- **idea** (required): The core idea or problem to expand
- **extra_context** (optional): Additional context or constraints

#### Output Schema

The service returns a tuple of `(ExpandedProposal, metadata)`:

**ExpandedProposal fields:**
- `problem_statement`: Clear articulation of the problem (required, trimmed)
- `proposed_solution`: Detailed description of the solution approach (required, trimmed)
- `assumptions`: List of underlying assumptions (required, can be empty)
- `scope_non_goals`: List of what is explicitly out of scope (required, can be empty)
- `title`: Optional short title for the proposal
- `summary`: Optional brief summary of the proposal
- `raw_idea`: Optional original idea text before expansion
- `metadata`: Optional metadata dictionary for tracking
- `raw_expanded_proposal`: Optional complete proposal text or notes

**Metadata fields:**
- `request_id`: Unique identifier for the request
- `step_name`: Name of the step ('expand' or 'review')
- `model`: Model used (e.g., "gpt-5.1")
- `temperature`: Temperature setting used
- `elapsed_time`: Time taken in seconds
- `latency`: Same as elapsed_time (for consistency)
- `finish_reason`: Completion reason from OpenAI
- `usage`: Token usage information
- `status`: Request status ('success', 'error', etc.)
- `persona_name`: (review only) Name of the reviewing persona

#### Telemetry and Logging

The Consensus Engine provides comprehensive telemetry for all OpenAI API calls:

**Logged Fields:**
- `run_id` / `request_id`: Unique identifier for tracking
- `step_name`: Operation type ('expand', 'review', 'llm_call')
- `model`: Model used for the request
- `temperature`: Temperature setting used
- `latency`: Request duration in seconds
- `status`: Request outcome ('success', 'error', 'timeout', 'rate_limited', etc.)
- `persona_name`: (review only) Persona used for review

**Example Log Output:**
```
2024-01-07 10:15:23 - consensus_engine.clients.openai_client - INFO - Starting OpenAI request for step=expand
  extra={'request_id': '123abc', 'step_name': 'expand', 'model': 'gpt-5.1', 'temperature': 0.7}

2024-01-07 10:15:25 - consensus_engine.clients.openai_client - INFO - OpenAI request completed successfully for step=expand
  extra={'request_id': '123abc', 'step_name': 'expand', 'latency': '2.1s', 'status': 'success'}
```

**Privacy:**
- Logs do NOT include user-provided content (ideas, proposals)
- Only metadata and performance metrics are logged
- Request IDs allow correlation without exposing sensitive data

#### Error Handling

The service uses domain exceptions with machine-readable error codes:

- `LLMAuthenticationError` (code: `LLM_AUTH_ERROR`): Invalid API key
- `LLMRateLimitError` (code: `LLM_RATE_LIMIT`): Rate limit exceeded (retryable)
- `LLMTimeoutError` (code: `LLM_TIMEOUT`): Request timed out (retryable)
- `LLMServiceError` (code: `LLM_SERVICE_ERROR` or `LLM_CONNECTION_ERROR`): Other API errors
- `SchemaValidationError` (code: `SCHEMA_VALIDATION_ERROR`): Response doesn't match expected schema

All exceptions include a `details` dict with additional context like `request_id` and `retryable` flags.

#### Logging

### Get Runs (GET /v1/runs)

Retrieves a paginated list of runs with filtering and sorting capabilities. This endpoint allows you to query run history for audits and tooling without re-triggering the pipeline.

**Request:**
```bash
GET /v1/runs?limit=30&offset=0&status=completed&min_confidence=0.8
```

**Query Parameters:**
- `limit` (optional, integer, 1-100, default: 30): Number of items per page
- `offset` (optional, integer, ≥0, default: 0): Offset for pagination
- `status` (optional, string): Filter by status - `running`, `completed`, or `failed`
- `run_type` (optional, string): Filter by run type - `initial` or `revision`
- `parent_run_id` (optional, UUID): Filter by parent run ID (for revisions)
- `decision` (optional, string): Filter by decision label (e.g., `approve`, `revise`, `reject`)
- `min_confidence` (optional, float, 0.0-1.0): Filter by minimum overall_weighted_confidence
- `start_date` (optional, ISO 8601): Filter by created_at >= start_date
- `end_date` (optional, ISO 8601): Filter by created_at <= end_date

**Success Response (200):**
```json
{
  "runs": [
    {
      "run_id": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2025-01-07T10:30:00Z",
      "status": "completed",
      "run_type": "initial",
      "parent_run_id": null,
      "overall_weighted_confidence": 0.85,
      "decision_label": "approve",
      "proposal_title": "User Management API",
      "proposal_summary": "A comprehensive REST API for managing users"
    },
    {
      "run_id": "660f9511-f3ac-52e5-b827-557766551111",
      "created_at": "2025-01-06T14:20:00Z",
      "status": "completed",
      "run_type": "revision",
      "parent_run_id": "550e8400-e29b-41d4-a716-446655440000",
      "overall_weighted_confidence": 0.90,
      "decision_label": "approve",
      "proposal_title": "User Management API v2",
      "proposal_summary": "Enhanced API with OAuth support"
    }
  ],
  "total": 42,
  "limit": 30,
  "offset": 0
}
```

**Response Fields:**
- `runs`: Array of run items with metadata and truncated proposal info
- `total`: Total number of runs matching the filters
- `limit`: Number of items per page (as requested)
- `offset`: Current offset (as requested)

**Notes:**
- Results are sorted by `created_at` descending (newest first)
- Returns empty list (200) for no matches or nonexistent filters
- No LLM calls are made during GET requests

**Error Responses:**
- `400 Bad Request`: Invalid parameters (e.g., invalid UUID, date format, status/run_type values)

### Get Run Detail (GET /v1/runs/{run_id})

Retrieves the full details of a single run including metadata, proposal JSON, persona reviews, and decision JSON.

**Request:**
```bash
GET /v1/runs/550e8400-e29b-41d4-a716-446655440000
```

**Path Parameters:**
- `run_id` (required, UUID): The unique identifier of the run

**Success Response (200):**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-01-07T10:30:00Z",
  "updated_at": "2025-01-07T10:35:00Z",
  "status": "completed",
  "run_type": "initial",
  "parent_run_id": null,
  "input_idea": "Build a REST API for user management with authentication",
  "extra_context": {
    "language": "Python",
    "version": "3.11+"
  },
  "model": "gpt-5.1",
  "temperature": 0.7,
  "parameters_json": {
    "expand_model": "gpt-5.1",
    "expand_temperature": 0.7,
    "review_model": "gpt-5.1",
    "review_temperature": 0.2
  },
  "overall_weighted_confidence": 0.85,
  "decision_label": "approve",
  "proposal": {
    "title": "User Management API",
    "summary": "A comprehensive REST API for managing users",
    "problem_statement": "Need user management capabilities",
    "proposed_solution": "Build a REST API with CRUD operations",
    "assumptions": ["Python 3.11+"],
    "scope_non_goals": ["No mobile app"]
  },
  "persona_reviews": [
    {
      "persona_id": "architect",
      "persona_name": "Architect",
      "confidence_score": 0.85,
      "blocking_issues_present": false,
      "prompt_parameters_json": {
        "model": "gpt-5.1",
        "temperature": 0.2,
        "persona_version": "1.0"
      }
    }
  ],
  "decision": {
    "decision": "approve",
    "overall_weighted_confidence": 0.85,
    "score_breakdown": {
      "Architect": {
        "weight": 0.25,
        "notes": "Strong architectural design"
      }
    }
  }
}
```

**Response Fields:**
- All run metadata fields (id, timestamps, status, type, etc.)
- `proposal`: Full proposal JSON (null if run failed before proposal creation)
- `persona_reviews`: Array of persona review summaries with confidence scores
- `decision`: Full decision JSON (null if run failed or is incomplete)

**Notes:**
- Returns partial data for failed runs (null fields for incomplete steps)
- No LLM calls are made during GET requests
- Useful for auditing, debugging, and building on previous proposals

**Error Responses:**
- `400 Bad Request`: Invalid UUID format
- `404 Not Found`: Run ID does not exist


The service logs the following without exposing sensitive data:
- Request start with request_id, model, and temperature
- Request completion with elapsed time and status
- All errors with request_id and error details (no sensitive payloads)

## Error Handling

The API uses a consistent error response format across all endpoints:

```json
{
  "code": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {},
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Error Codes

**Validation Errors (422):**
- `VALIDATION_ERROR`: Request validation failed (e.g., empty idea, too many sentences)

**Authentication Errors (401):**
- `LLM_AUTH_ERROR`: OpenAI API authentication failed

**Service Errors (503):**
- `LLM_RATE_LIMIT`: OpenAI rate limit exceeded (retryable)
- `LLM_TIMEOUT`: Request timed out (retryable)

**Server Errors (500):**
- `LLM_SERVICE_ERROR`: OpenAI API error
- `LLM_CONNECTION_ERROR`: Connection to OpenAI failed
- `SCHEMA_VALIDATION_ERROR`: Response schema validation failed
- `INTERNAL_ERROR`: Unexpected server error

### Request Tracking

All requests include a unique `X-Request-ID` header in the response for tracing and debugging:

```bash
curl -v http://localhost:8000/health
# Response headers include:
# X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

Request IDs are also included in error responses and logged for all operations.

### Middleware

The application includes the following middleware:

**Logging Middleware:**
- Generates unique request IDs for each request
- Logs request/response information without storing full payloads
- Adds `X-Request-ID` header to all responses
- Tracks request duration

**Exception Handlers:**
- Global validation error handler for 422 responses
- Domain exception handler for application errors
- Generic exception handler for unexpected errors
- All handlers return structured JSON with error codes

## Development

### Adding New Endpoints

1. Create route handlers in `src/consensus_engine/api/`
2. Define request/response schemas in `src/consensus_engine/schemas/`
3. Implement business logic in `src/consensus_engine/services/`
4. Add tests in `tests/unit/` and `tests/integration/`

### Configuration Access

Use dependency injection to access settings in your endpoints:

```python
from fastapi import Depends
from consensus_engine.config import Settings, get_settings

@app.get("/example")
async def example(settings: Settings = Depends(get_settings)):
    # Access configuration
    model = settings.openai_model
    temperature = settings.temperature
    return {"model": model}
```

### Logging

Use the logging utility to add logs:

```python
from consensus_engine.config.logging import get_logger

logger = get_logger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

## Schemas

The application uses Pydantic models for data validation and serialization. All schemas include automatic whitespace trimming and validation for required fields.

### Core Schemas

#### ExpandedProposal

Represents a detailed proposal expanded from a brief idea. All strings are automatically trimmed and validated.

**Required Fields:**
- `problem_statement` (str): Clear articulation of the problem to be solved
- `proposed_solution` (str): Detailed description of the solution approach
- `assumptions` (list[str]): List of underlying assumptions (can be empty)
- `scope_non_goals` (list[str]): List of what is explicitly out of scope (can be empty)

**Optional Fields:**
- `title` (str | None): Short title for the proposal
- `summary` (str | None): Brief summary of the proposal
- `raw_idea` (str | None): Original idea text before expansion
- `metadata` (dict[str, Any] | None): Metadata for tracking and processing
- `raw_expanded_proposal` (str | None): Complete proposal text or additional notes

**Validation:**
- Required string fields reject empty or whitespace-only values
- List items must be non-empty strings after trimming
- Optional fields that are empty/whitespace become `None`

#### PersonaReview

Represents a review from a specific persona evaluating a proposal.

**Required Fields:**
- `persona_name` (str): Name of the reviewing persona (e.g., "Architect", "SecurityGuardian")
- `persona_id` (str): Stable identifier for the persona (e.g., "architect", "security_guardian")
- `confidence_score` (float): Confidence in the proposal, range [0.0, 1.0]
- `strengths` (list[str]): Identified strengths in the proposal
- `concerns` (list[Concern]): Concerns with blocking flags
- `recommendations` (list[str]): Actionable recommendations
- `blocking_issues` (list[BlockingIssue]): Critical blocking issues with optional security flags (can be empty)
- `estimated_effort` (str | dict[str, Any]): Effort estimation
- `dependency_risks` (list[str | dict[str, Any]]): Identified dependency risks (can be empty)

**Optional Fields:**
- `internal_metadata` (dict[str, Any] | None): Internal metadata for tracking (e.g., model, duration, timestamps)

**BlockingIssue Schema:**
- `text` (str): The blocking issue description
- `security_critical` (bool | None): Whether this is a security-critical issue (SecurityGuardian veto power)

**Concern Schema:**
- `text` (str): The concern description
- `is_blocking` (bool): Whether this concern blocks approval

**Validation:**
- `confidence_score` must be between 0.0 and 1.0
- String list items must be non-empty after trimming
- `dependency_risks` accepts both strings and structured dicts
- Empty strings in `dependency_risks` are filtered out
- `security_critical` flag on BlockingIssue enables SecurityGuardian veto power

#### DecisionAggregation

Represents aggregated decision from multiple persona reviews with comprehensive score breakdown.

**Required Fields:**
- `overall_weighted_confidence` (float): Weighted confidence across all personas [0.0, 1.0] (legacy field)
- `decision` (DecisionEnum): Final decision outcome (approve/revise/reject)

**Optional Fields (New Schema):**
- `weighted_confidence` (float | None): Weighted confidence (mirrors overall_weighted_confidence)
- `detailed_score_breakdown` (DetailedScoreBreakdown | None): Comprehensive scoring details
- `minority_reports` (list[MinorityReport] | None): Multiple dissenting opinions

**Optional Fields (Legacy Schema):**
- `score_breakdown` (dict[str, PersonaScoreBreakdown] | None): Per-persona scoring (legacy format)
- `minority_report` (MinorityReport | None): Single dissenting opinion (legacy field)

**DecisionEnum Values:**
- `APPROVE`: "approve" - Proposal approved (weighted_confidence >= 0.80, no blocking issues)
- `REVISE`: "revise" - Proposal needs revision (0.60 <= weighted_confidence < 0.80, no blocking issues)
- `REJECT`: "reject" - Proposal rejected (weighted_confidence < 0.60 or has blocking issues)

**DetailedScoreBreakdown:**
- `weights` (dict[str, float]): Persona IDs mapped to their weights
- `individual_scores` (dict[str, float]): Persona IDs mapped to their confidence scores
- `weighted_contributions` (dict[str, float]): Persona IDs mapped to their weighted contribution (weight * score)
- `formula` (str): Description of the aggregation formula (e.g., "weighted_confidence = sum(weight_i * score_i)")

**PersonaScoreBreakdown (Legacy):**
- `weight` (float): Weight assigned to persona's review (>= 0.0)
- `notes` (str | None): Optional notes about persona's contribution

**MinorityReport (Extended):**
- `persona_id` (str): Stable identifier of dissenting persona
- `persona_name` (str): Name of dissenting persona
- `confidence_score` (float): Confidence score of dissenting persona [0.0, 1.0]
- `blocking_summary` (str): Summary of blocking issues from dissenting persona
- `mitigation_recommendation` (str): Recommended mitigation for blocking issues
- `strengths` (list[str] | None): Optional strengths (backward compatibility)
- `concerns` (list[str] | None): Optional concerns (backward compatibility)

**Validation:**
- `overall_weighted_confidence` and `weighted_confidence` must be between 0.0 and 1.0
- Weights in `detailed_score_breakdown` should sum to 1.0
- When only one persona exists, confidence matches that reviewer's score
- Multiple minority reports support simultaneous dissenters

**Score Breakdown Contract:**

The `detailed_score_breakdown` provides full transparency into how the final decision was computed:

1. **weights**: Shows each persona's influence (must sum to 1.0)
2. **individual_scores**: Shows each persona's confidence score
3. **weighted_contributions**: Shows each persona's contribution to final score (weight × score)
4. **formula**: Documents the exact aggregation method used

Example:
```python
detailed_score_breakdown = DetailedScoreBreakdown(
    weights={
        "architect": 0.25,
        "critic": 0.25,
        "optimist": 0.15,
        "security_guardian": 0.20,
        "user_advocate": 0.15
    },
    individual_scores={
        "architect": 0.80,
        "critic": 0.70,
        "optimist": 0.90,
        "security_guardian": 0.75,
        "user_advocate": 0.85
    },
    weighted_contributions={
        "architect": 0.200,
        "critic": 0.175,
        "optimist": 0.135,
        "security_guardian": 0.150,
        "user_advocate": 0.1275
    },
    formula="weighted_confidence = sum(weight_i * score_i for each persona i) = 0.7875"
)
```

**Minority Report Triggers:**

Minority reports are generated when:
1. A persona's confidence significantly differs from the majority
2. A persona has blocking issues that were overruled
3. A persona strongly dissents from the final decision

Multiple minority reports can be present when several personas dissent.

**SecurityGuardian Veto Behavior:**

The SecurityGuardian can exercise veto power by marking blocking issues with `security_critical: true`:
- Security-critical blocking issues trigger automatic REJECT decision
- This ensures critical security vulnerabilities are never overlooked
- Non-security blocking issues from SecurityGuardian follow normal aggregation rules
- Only SecurityGuardian blocking issues can have the `security_critical` flag

### Usage Examples

```python
from consensus_engine.schemas import (
    BlockingIssue,
    Concern,
    DecisionAggregation,
    DecisionEnum,
    DetailedScoreBreakdown,
    ExpandedProposal,
    MinorityReport,
    PersonaReview,
    PersonaScoreBreakdown,
)

# Create an expanded proposal
proposal = ExpandedProposal(
    problem_statement="Need to improve API performance",
    proposed_solution="Implement caching layer with Redis",
    assumptions=["Redis available", "Load < 10k req/sec"],
    scope_non_goals=["Mobile app changes"],
    title="API Performance Improvement",
)

# Create a persona review with new schema
review = PersonaReview(
    persona_name="SecurityGuardian",
    persona_id="security_guardian",
    confidence_score=0.40,
    strengths=["Good caching strategy", "Realistic assumptions"],
    concerns=[
        Concern(text="No authentication on cache", is_blocking=True),
        Concern(text="Redis cluster sizing unclear", is_blocking=False),
    ],
    recommendations=["Add Redis authentication", "Size Redis cluster"],
    blocking_issues=[
        BlockingIssue(text="No authentication on cache", security_critical=True),
        BlockingIssue(text="Missing cache invalidation strategy", security_critical=False),
    ],
    estimated_effort="2 weeks",
    dependency_risks=["Redis cluster setup", "Cache key design"],
    internal_metadata={"model": "gpt-5.1", "duration": 2.5},
)

# Create a decision aggregation with detailed score breakdown
decision = DecisionAggregation(
    overall_weighted_confidence=0.7875,
    weighted_confidence=0.7875,
    decision=DecisionEnum.APPROVE,
    detailed_score_breakdown=DetailedScoreBreakdown(
        weights={
            "architect": 0.25,
            "critic": 0.25,
            "optimist": 0.15,
            "security_guardian": 0.20,
            "user_advocate": 0.15,
        },
        individual_scores={
            "architect": 0.80,
            "critic": 0.70,
            "optimist": 0.90,
            "security_guardian": 0.75,
            "user_advocate": 0.85,
        },
        weighted_contributions={
            "architect": 0.200,
            "critic": 0.175,
            "optimist": 0.135,
            "security_guardian": 0.150,
            "user_advocate": 0.1275,
        },
        formula="weighted_confidence = sum(weight_i * score_i for each persona i)",
    ),
    minority_reports=[
        MinorityReport(
            persona_id="critic",
            persona_name="Critic",
            confidence_score=0.50,
            blocking_summary="Too many edge cases not addressed",
            mitigation_recommendation="Add comprehensive error handling and edge case tests",
        )
    ],
)
```

## Architecture

### Components

The application follows a clean architecture with clear separation of concerns:

```
src/consensus_engine/
├── api/              # FastAPI route handlers and HTTP layer
├── clients/          # External service wrappers (OpenAI, etc.)
├── config/           # Configuration and settings management
├── schemas/          # Pydantic models for validation
├── services/         # Business logic layer
└── exceptions.py     # Domain exception definitions
```

### OpenAI Integration

The OpenAI client wrapper (`clients/openai_client.py`) provides:

- **Structured Outputs**: Uses OpenAI's Responses API with schema validation
- **Error Handling**: Maps OpenAI errors to domain exceptions
- **Logging**: Structured logging without sensitive data exposure
- **Type Safety**: Generic type support for response models

### Exception Hierarchy

```
ConsensusEngineError (base)
├── LLMServiceError
│   ├── LLMAuthenticationError
│   ├── LLMRateLimitError
│   └── LLMTimeoutError
└── SchemaValidationError
```

All exceptions include:
- Machine-readable error codes for HTTP translation
- Human-readable messages
- Optional details dictionary with context

## Error Handling

### Missing API Key

If `OPENAI_API_KEY` is not set or is invalid, the application will fail to start with a clear error message:

```
ValidationError: OPENAI_API_KEY cannot be empty
```

The API key is never logged or exposed in error messages for security.

### Temperature Validation

- Values outside [0.0, 1.0] are rejected at startup
- Values outside recommended range [0.5, 0.7] trigger a warning but are allowed

### Environment Modes

- **development**: DEBUG logging, debug mode enabled
- **testing**: INFO logging, debug mode disabled
- **production**: WARNING logging, debug mode disabled, verbose third-party logs suppressed

## Security Considerations

- API keys are validated at startup but never logged
- The `get_safe_dict()` method masks sensitive values for logging
- Production mode suppresses verbose logging from third-party libraries
- Use environment variables, never hardcode credentials

## Future Development

This scaffolding provides the foundation for:
- LLM-powered consensus building services
- Additional API endpoints for consensus operations
- Database integration for persistence
- Background task processing
- CI/CD pipeline integration

## Troubleshooting

### Common Setup Issues

**Issue**: `ModuleNotFoundError: No module named 'consensus_engine'`  
**Solution**: Install the package with `pip install -e .`

**Issue**: `ValidationError` on startup  
**Solution**: Ensure all required environment variables are set in `.env`

**Issue**: Missing API Key  
**Symptom**: Application fails to start with `ValidationError: OPENAI_API_KEY cannot be empty`  
**Solution**: Set `OPENAI_API_KEY` in `.env` file or environment

### API Server Issues

**Issue**: API returns 503 "Pub/Sub publish error"  
**Cause**: Cannot publish to Pub/Sub topic  
**Check**:
- Verify `PUBSUB_PROJECT_ID` and `PUBSUB_TOPIC` are set correctly
- Check Pub/Sub credentials (`PUBSUB_CREDENTIALS_FILE` or ADC)
- If using emulator, ensure `PUBSUB_EMULATOR_HOST` is set and emulator is running
- Check IAM permissions: `roles/pubsub.publisher` on the topic

**Solution**:
- Restart API with correct environment variables
- Use `PUBSUB_USE_MOCK=true` for testing without Pub/Sub

**Issue**: Database connection errors  
**Cause**: Cannot connect to PostgreSQL  
**Check**:
- Verify `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- For Cloud SQL: Check `DB_INSTANCE_CONNECTION_NAME` and IAM permissions
- Check database is running: `pg_isready -h localhost -p 5432`
- Check connection pool settings (`DB_POOL_SIZE`, `DB_POOL_TIMEOUT`)

**Solution**:
- For local dev: Start PostgreSQL with Docker Compose
- For Cloud SQL: Ensure service account has `roles/cloudsql.client`
- Check network connectivity and firewall rules

### Worker Issues

**Issue**: Worker not processing jobs (runs stuck in "queued")  
**Cause**: Worker not running or not subscribed  
**Check**:
- Worker process is running: `ps aux | grep pipeline_worker`
- Worker logs show `worker.started` event
- Worker configured with correct `PUBSUB_SUBSCRIPTION`
- Subscription exists and has messages: `gcloud pubsub subscriptions describe <subscription>`

**Solution**:
- Start worker: `python -m consensus_engine.workers.pipeline_worker`
- Verify subscription is attached to correct topic
- Check worker logs for connection or authentication errors

**Issue**: Worker keeps nacking messages (jobs retry forever)  
**Cause**: Worker encounters repeated errors during processing  
**Check**:
- Worker logs for `job.failed` or `step.failed` events with error details
- LLM API errors (rate limits, timeouts, auth failures)
- Database errors during status updates
- Pub/Sub ack deadline too short (job takes longer than `WORKER_ACK_DEADLINE_SECONDS`)

**Solution**:
- Review error logs and fix underlying issue (e.g., increase OpenAI rate limits)
- Increase `WORKER_ACK_DEADLINE_SECONDS` for long-running jobs
- Configure dead-letter topic to prevent infinite retries
- Manually mark problematic runs as failed in database

**Issue**: Duplicate results (same job processed twice)  
**Expected Behavior**: Worker idempotency checks should prevent duplicate work  
**Verify**:
- Worker logs show `idempotency_check.skipped` for completed runs
- Completed runs are acked without reprocessing
- Check run status is properly checked before processing

**Issue**: High latency (jobs taking too long)  
**Cause**: LLM API slowness, worker overload, or resource constraints  
**Check**:
- Worker concurrency: `WORKER_MAX_CONCURRENCY` (default: 10)
- Per-step latency in logs: Look for slow steps (e.g., `expand` taking > 10s)
- OpenAI API latency: Check OpenAI status page
- Database query latency: Slow updates to StepProgress
- Queue depth: Check `num_undelivered_messages` in subscription metrics

**Solution**:
- Increase `WORKER_MAX_CONCURRENCY` (balance with resource limits)
- Optimize OpenAI requests (check temperature, max_tokens settings)
- Scale worker horizontally (run multiple worker instances)
- Review database indexes and connection pool size

### Job Failure Recovery

**Inspect failed run:**
```bash
curl http://localhost:8000/v1/runs/{run_id}
```

**Monitor stuck runs:**
```sql
-- Runs stuck in "running" for > 30 minutes
SELECT id, started_at, EXTRACT(EPOCH FROM NOW() - started_at) AS seconds_running
FROM runs
WHERE status = 'running'
AND started_at < NOW() - INTERVAL '30 minutes'
ORDER BY started_at;
```

**Monitor failed steps:**
```sql
-- Recent failed steps with errors
SELECT r.id AS run_id, sp.step_name, sp.error_message, sp.completed_at
FROM runs r
JOIN step_progress sp ON r.id = sp.run_id
WHERE sp.status = 'failed'
AND sp.completed_at > NOW() - INTERVAL '1 hour'
ORDER BY sp.completed_at DESC;
```

**Manual intervention (advanced):**
```sql
-- Mark run as failed manually (if worker stuck)
UPDATE runs SET status = 'failed', completed_at = NOW()
WHERE id = '550e8400-e29b-41d4-a716-446655440000';

-- Reset run for retry (use with caution)
UPDATE runs SET status = 'queued', started_at = NULL, completed_at = NULL
WHERE id = '550e8400-e29b-41d4-a716-446655440000';

UPDATE step_progress SET status = 'pending', started_at = NULL, completed_at = NULL, error_message = NULL
WHERE run_id = '550e8400-e29b-41d4-a716-446655440000';
```

### Logging and Observability

**Key log events to monitor:**
- `worker.started` - Worker initialized successfully
- `job.processing.started` - Job processing began
- `step.started`, `step.completed` - Individual pipeline steps
- `step.failed` - Step failures with error details
- `job.completed` - Job succeeded
- `job.failed` - Job failed after all retries
- `idempotency_check.skipped` - Duplicate message ignored

**Enable debug logging:**
```bash
export LOG_LEVEL=DEBUG
```

**Cloud Logging queries (GCP):**
```
# Failed jobs in last hour
resource.type="cloud_run_revision"
jsonPayload.event="job.failed"
timestamp>="2026-01-08T04:00:00Z"

# High latency jobs (>60s)
resource.type="cloud_run_revision"
jsonPayload.event="job.completed"
jsonPayload.elapsed_time>60
```

See [Worker Deployment Guide](docs/WORKER_DEPLOYMENT.md) for production deployment details and monitoring setup.

**Issue**: Tests failing with import errors
**Solution**: Ensure dev dependencies are installed with `pip install -e ".[dev]"`

---

# Permanents (License, Contributing, Author)

Do not change any of the below sections

## License

This Agent Foundry Project is licensed under the Apache 2.0 License - see the LICENSE file for details.

## Contributing

Feel free to submit issues and enhancement requests!

## Author

Created by Agent Foundry and John Brosnihan
