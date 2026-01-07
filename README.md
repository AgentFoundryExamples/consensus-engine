# Consensus Engine

A FastAPI-based backend service with LLM integration for consensus building. This project provides a production-ready Python API with OpenAI integration, configuration management, and comprehensive testing.

## Features

- **FastAPI Backend**: Modern async Python web framework
- **LLM Integration**: OpenAI GPT-5.1 support with configurable parameters
- **Multi-Persona Consensus**: Five specialized personas for comprehensive proposal review
- **Configuration Management**: Pydantic-based settings with validation
- **Structured Logging**: Environment-aware logging configuration
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
│       ├── config/       # Configuration and settings
│       ├── schemas/      # Pydantic models for validation
│       ├── services/     # Business logic services
│       └── app.py        # FastAPI application factory
├── tests/
│   ├── unit/            # Unit tests
│   └── integration/     # Integration tests
├── pyproject.toml       # Project metadata and dependencies
├── .env.example         # Example environment configuration
└── README.md
```

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

### Running the Server

Start the development server:
```bash
uvicorn consensus_engine.app:app --reload
```

The API will be available at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

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

**Issue**: `ModuleNotFoundError: No module named 'consensus_engine'`
**Solution**: Install the package with `pip install -e .`

**Issue**: `ValidationError` on startup
**Solution**: Ensure all required environment variables are set in `.env`

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
