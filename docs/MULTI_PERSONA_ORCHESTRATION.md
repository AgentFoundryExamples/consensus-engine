# Multi-Persona Orchestration

This document describes the multi-persona consensus building system in the Consensus Engine.

## Overview

The Consensus Engine uses a multi-persona approach to evaluate proposals from diverse perspectives, ensuring comprehensive analysis and balanced decision-making. The system orchestrates reviews from five specialized personas, aggregates their feedback using weighted confidence scores, and produces a final decision with transparency into the decision-making process.

## Usage Example

```python
from consensus_engine.services import review_with_all_personas, aggregate_persona_reviews
from consensus_engine.schemas.proposal import ExpandedProposal
from consensus_engine.config import get_settings

# Create proposal
proposal = ExpandedProposal(
    problem_statement="Build a scalable API",
    proposed_solution="Use FastAPI with async handlers",
    assumptions=["Python 3.11+"],
    scope_non_goals=["No mobile app"]
)

# Orchestrate reviews from all 5 personas
settings = get_settings()
reviews, metadata = review_with_all_personas(proposal, settings)

# Aggregate into final decision
decision = aggregate_persona_reviews(reviews)

print(f"Decision: {decision.decision.value}")
print(f"Confidence: {decision.weighted_confidence:.2f}")
if decision.minority_reports:
    print(f"Minority Reports: {len(decision.minority_reports)}")
```

## Architecture

The multi-persona system consists of two main components:

1. **Orchestrator** (`orchestrator.py`): Manages sequential review process
2. **Aggregator** (`aggregator.py`): Computes final decision with weighted confidence

## Personas

### 1. Architect (Weight: 0.25)
- Focus: System design, scalability, architecture
- Temperature: 0.2 (deterministic)

### 2. Critic (Weight: 0.25)
- Focus: Risks, edge cases, failures
- Temperature: 0.2 (deterministic)

### 3. Optimist (Weight: 0.15)
- Focus: Strengths, opportunities
- Temperature: 0.2 (deterministic)

### 4. SecurityGuardian (Weight: 0.20)
- Focus: Security, vulnerabilities, auth
- Temperature: 0.2 (deterministic)
- **Veto Power**: Can force REVISE with security_critical flags

### 5. UserAdvocate (Weight: 0.15)
- Focus: Usability, UX, accessibility
- Temperature: 0.2 (deterministic)

## Aggregation

Weighted confidence formula:
```
weighted_confidence = Σ(weight_i × confidence_i) for all personas
```

Decision thresholds:
- **APPROVE**: ≥ 0.80
- **REVISE**: 0.60 to < 0.80
- **REJECT**: < 0.60

## SecurityGuardian Veto

SecurityGuardian can force decision to at least REVISE when:
- A blocking issue has `security_critical: true`
- Weighted confidence would otherwise be APPROVE

## Minority Reports

Generated when:
1. Decision is APPROVE but persona confidence < 0.60
2. Decision is APPROVE/REVISE but persona has blocking issues

## Testing

Run tests:
```bash
pytest tests/unit/test_orchestrator.py
pytest tests/unit/test_aggregator.py
pytest tests/integration/test_multi_persona.py
```

## Persistence

The Consensus Engine uses PostgreSQL to persist run lifecycle data with SQLAlchemy and Alembic migrations.

### Database Infrastructure

- **Engine**: SQLAlchemy 2.0+ with connection pooling
- **Migrations**: Alembic for schema version control
- **Local Development**: Docker Compose with PostgreSQL 16
- **Production**: Cloud SQL for PostgreSQL with IAM authentication

### Connection Modes

**Local Development:**
```python
from consensus_engine.config import get_settings
from consensus_engine.db import create_engine_from_settings

settings = get_settings()
engine = create_engine_from_settings(settings)
```

**Cloud SQL with IAM Authentication:**
```bash
USE_CLOUD_SQL_CONNECTOR=true
DB_INSTANCE_CONNECTION_NAME=project:region:instance
DB_IAM_AUTH=true
```

**Cloud SQL with Password Authentication:**
```bash
USE_CLOUD_SQL_CONNECTOR=true
DB_INSTANCE_CONNECTION_NAME=project:region:instance
DB_IAM_AUTH=false
DB_PASSWORD=your-password
```

### Health Checks

Database connectivity is verified through health checks:

```python
from consensus_engine.db import check_database_health

if not check_database_health(engine):
    logger.error("Database is unreachable")
    # Fail fast with actionable error
```

Health checks:
- Never fall back to IP allowlists
- Emit clear errors when DB is unreachable
- Surface actionable error messages for IAM principal issues

### Connection Pool Management

- **Pool Size**: Configurable via `DB_POOL_SIZE` (default: 5)
- **Max Overflow**: Configurable via `DB_MAX_OVERFLOW` (default: 10)
- **Pool Timeout**: Configurable via `DB_POOL_TIMEOUT` (default: 30s)
- **Pool Recycle**: Configurable via `DB_POOL_RECYCLE` (default: 3600s)
- **Pre-Ping**: Enabled to verify connections before use
- **Retries**: Connection pool exhaustion triggers backoff

### Security Considerations

- **No Passwords in Code**: All credentials from environment variables
- **IAM Authentication**: Recommended for Cloud SQL (no passwords)
- **Masked Logging**: Database passwords masked in logs via `get_safe_dict()`
- **No Ad-Hoc Connections**: All persistence via SQLAlchemy/Alembic

### Migration Workflow

```bash
# Create a new migration after model changes
alembic revision --autogenerate -m "add_new_table"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Migrations are idempotent and safe to run multiple times
```

See full documentation in the repository for complete details.
