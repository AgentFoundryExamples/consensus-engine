# Dependency Graph

Multi-language intra-repository dependency analysis.

Supports Python, JavaScript/TypeScript, C/C++, Rust, Go, Java, C#, Swift, HTML/CSS, and SQL.

Includes classification of external dependencies as stdlib vs third-party.

## Statistics

- **Total files**: 58
- **Intra-repo dependencies**: 150
- **External stdlib dependencies**: 30
- **External third-party dependencies**: 62

## External Dependencies

### Standard Library / Core Modules

Total: 30 unique modules

- `collections.abc.AsyncGenerator`
- `collections.abc.Awaitable`
- `collections.abc.Callable`
- `collections.abc.Generator`
- `collections.abc.Sequence`
- `contextlib.asynccontextmanager`
- `datetime.UTC`
- `datetime.datetime`
- `enum`
- `enum.Enum`
- `functools.lru_cache`
- `json`
- `logging`
- `logging.config.fileConfig`
- `os`
- `pathlib.Path`
- `re`
- `sys`
- `threading`
- `time`
- ... and 10 more (see JSON for full list)

### Third-Party Packages

Total: 62 unique packages

- `alembic.command`
- `alembic.config.Config`
- `alembic.context`
- `alembic.op`
- `fastapi.APIRouter`
- `fastapi.Depends`
- `fastapi.FastAPI`
- `fastapi.HTTPException`
- `fastapi.Request`
- `fastapi.Response`
- `fastapi.exceptions.RequestValidationError`
- `fastapi.responses.JSONResponse`
- `fastapi.status`
- `fastapi.testclient.TestClient`
- `google.cloud.sql.connector.Connector`
- `httpx`
- `openai.`
- `openai.APIConnectionError`
- `openai.APITimeoutError`
- `openai.AuthenticationError`
- ... and 42 more (see JSON for full list)

## Most Depended Upon Files (Intra-Repo)

- `src/consensus_engine/schemas/proposal.py` (21 dependents)
- `src/consensus_engine/schemas/review.py` (18 dependents)
- `src/consensus_engine/exceptions.py` (16 dependents)
- `src/consensus_engine/config/settings.py` (15 dependents)
- `src/consensus_engine/config/__init__.py` (13 dependents)
- `src/consensus_engine/config/logging.py` (10 dependents)
- `src/consensus_engine/schemas/requests.py` (6 dependents)
- `src/consensus_engine/config/personas.py` (6 dependents)
- `src/consensus_engine/services/review.py` (5 dependents)
- `src/consensus_engine/clients/openai_client.py` (5 dependents)

## Files with Most Dependencies (Intra-Repo)

- `src/consensus_engine/api/routes/full_review.py` (8 dependencies)
- `src/consensus_engine/api/routes/review.py` (7 dependencies)
- `src/consensus_engine/app.py` (7 dependencies)
- `src/consensus_engine/services/orchestrator.py` (6 dependencies)
- `tests/integration/test_acceptance_criteria.py` (6 dependencies)
- `tests/integration/test_full_review_endpoint.py` (6 dependencies)
- `src/consensus_engine/api/dependencies.py` (5 dependencies)
- `src/consensus_engine/api/routes/expand.py` (5 dependencies)
- `src/consensus_engine/services/review.py` (5 dependencies)
- `tests/integration/test_multi_persona.py` (5 dependencies)
