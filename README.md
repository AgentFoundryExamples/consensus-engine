# Consensus Engine

A FastAPI-based backend service with LLM integration for consensus building. This project provides a production-ready Python API with OpenAI integration, configuration management, and comprehensive testing.

## Features

- **FastAPI Backend**: Modern async Python web framework
- **LLM Integration**: OpenAI GPT-5.1 support with configurable parameters
- **Configuration Management**: Pydantic-based settings with validation
- **Structured Logging**: Environment-aware logging configuration
- **Dependency Injection**: Clean separation of concerns
- **Comprehensive Testing**: Unit and integration tests with pytest

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
| `OPENAI_MODEL` | No | `gpt-5.1` | OpenAI model to use |
| `TEMPERATURE` | No | `0.7` | Temperature for model responses (0.0-1.0) |
| `ENV` | No | `development` | Environment mode: development, production, testing |

**Temperature Guidelines:**
- Range: 0.0 to 1.0
- Recommended: 0.5 to 0.7 for balanced responses
- Lower values (0.0-0.3): More deterministic, focused
- Higher values (0.8-1.0): More creative, varied

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

### Health Check
```bash
GET /health
```
Returns the health status and configuration information.

**Response:**
```json
{
  "status": "healthy",
  "environment": "development",
  "debug": true,
  "model": "gpt-5.1"
}
```

### Root
```bash
GET /
```
Returns API information and links to documentation.

## Services

### Expand Idea Service

The `expand_idea` service transforms brief ideas into comprehensive, structured proposals using OpenAI's GPT-5.1 with structured outputs.

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
- `problem_statement`: Clear articulation of the problem
- `proposed_solution`: Detailed description of the solution approach
- `assumptions`: List of underlying assumptions
- `scope_non_goals`: List of what is explicitly out of scope
- `raw_expanded_proposal`: Complete expanded proposal text or notes

**Metadata fields:**
- `request_id`: Unique identifier for the request
- `model`: Model used (e.g., "gpt-5.1")
- `temperature`: Temperature setting used
- `elapsed_time`: Time taken in seconds
- `finish_reason`: Completion reason from OpenAI
- `usage`: Token usage information

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
