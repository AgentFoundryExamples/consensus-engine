# Dependency Graph

Multi-language intra-repository dependency analysis.

Supports Python, JavaScript/TypeScript, C/C++, Rust, Go, Java, C#, Swift, HTML/CSS, and SQL.

Includes classification of external dependencies as stdlib vs third-party.

## Statistics

- **Total files**: 78
- **Intra-repo dependencies**: 224
- **External stdlib dependencies**: 37
- **External third-party dependencies**: 71

## External Dependencies

### Standard Library / Core Modules

Total: 37 unique modules

- `collections.abc.AsyncGenerator`
- `collections.abc.Awaitable`
- `collections.abc.Callable`
- `collections.abc.Generator`
- `collections.abc.Sequence`
- `collections.deque`
- `contextlib.asynccontextmanager`
- `dataclasses.dataclass`
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
- ... and 17 more (see JSON for full list)

### Third-Party Packages

Total: 71 unique packages

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
- `google.api_core.exceptions.GoogleAPIError`
- `google.api_core.retry`
- `google.cloud.pubsub_v1`
- `google.cloud.sql.connector.Connector`
- `httpx`
- ... and 51 more (see JSON for full list)

## Most Depended Upon Files (Intra-Repo)

- `src/consensus_engine/schemas/proposal.py` (26 dependents)
- `src/consensus_engine/schemas/review.py` (23 dependents)
- `src/consensus_engine/config/settings.py` (20 dependents)
- `src/consensus_engine/exceptions.py` (16 dependents)
- `src/consensus_engine/db/models.py` (16 dependents)
- `src/consensus_engine/config/__init__.py` (15 dependents)
- `src/consensus_engine/config/logging.py` (15 dependents)
- `src/consensus_engine/app.py` (10 dependents)
- `src/consensus_engine/db/__init__.py` (9 dependents)
- `src/consensus_engine/db/dependencies.py` (8 dependents)

## Files with Most Dependencies (Intra-Repo)

- `src/consensus_engine/workers/pipeline_worker.py` (12 dependencies)
- `src/consensus_engine/app.py` (10 dependencies)
- `src/consensus_engine/api/routes/runs.py` (8 dependencies)
- `src/consensus_engine/api/routes/full_review.py` (7 dependencies)
- `src/consensus_engine/api/routes/review.py` (7 dependencies)
- `tests/integration/test_pipeline_worker.py` (7 dependencies)
- `tests/integration/test_revision_endpoint.py` (7 dependencies)
- `src/consensus_engine/services/orchestrator.py` (6 dependencies)
- `tests/integration/test_acceptance_criteria.py` (6 dependencies)
- `tests/integration/test_full_review_endpoint.py` (6 dependencies)
