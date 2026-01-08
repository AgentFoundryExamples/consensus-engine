# Dependency Graph

Multi-language intra-repository dependency analysis.

Supports Python, JavaScript/TypeScript, C/C++, Rust, Go, Java, C#, Swift, HTML/CSS, and SQL.

Includes classification of external dependencies as stdlib vs third-party.

## Statistics

- **Total files**: 68
- **Intra-repo dependencies**: 194
- **External stdlib dependencies**: 32
- **External third-party dependencies**: 68

## External Dependencies

### Standard Library / Core Modules

Total: 32 unique modules

- `collections.abc.AsyncGenerator`
- `collections.abc.Awaitable`
- `collections.abc.Callable`
- `collections.abc.Generator`
- `collections.abc.Sequence`
- `contextlib.asynccontextmanager`
- `datetime.UTC`
- `datetime.datetime`
- `datetime.timedelta`
- `difflib`
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
- ... and 12 more (see JSON for full list)

### Third-Party Packages

Total: 68 unique packages

- `alembic.command`
- `alembic.config.Config`
- `alembic.context`
- `alembic.op`
- `fastapi.APIRouter`
- `fastapi.Depends`
- `fastapi.FastAPI`
- `fastapi.HTTPException`
- `fastapi.Query`
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
- ... and 48 more (see JSON for full list)

## Most Depended Upon Files (Intra-Repo)

- `src/consensus_engine/schemas/proposal.py` (24 dependents)
- `src/consensus_engine/schemas/review.py` (20 dependents)
- `src/consensus_engine/exceptions.py` (17 dependents)
- `src/consensus_engine/config/settings.py` (15 dependents)
- `src/consensus_engine/config/__init__.py` (14 dependents)
- `src/consensus_engine/config/logging.py` (13 dependents)
- `src/consensus_engine/db/models.py` (11 dependents)
- `src/consensus_engine/app.py` (9 dependents)
- `src/consensus_engine/db/__init__.py` (8 dependents)
- `src/consensus_engine/schemas/requests.py` (7 dependents)

## Files with Most Dependencies (Intra-Repo)

- `src/consensus_engine/api/routes/runs.py` (12 dependencies)
- `src/consensus_engine/api/routes/full_review.py` (11 dependencies)
- `src/consensus_engine/app.py` (10 dependencies)
- `src/consensus_engine/api/routes/review.py` (7 dependencies)
- `tests/integration/test_revision_endpoint.py` (7 dependencies)
- `src/consensus_engine/services/orchestrator.py` (6 dependencies)
- `tests/integration/test_acceptance_criteria.py` (6 dependencies)
- `tests/integration/test_full_review_endpoint.py` (6 dependencies)
- `src/consensus_engine/api/dependencies.py` (5 dependencies)
- `src/consensus_engine/api/routes/__init__.py` (5 dependencies)
