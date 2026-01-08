# Dependency Graph

Multi-language intra-repository dependency analysis.

Supports Python, JavaScript/TypeScript, C/C++, Rust, Go, Java, C#, Swift, HTML/CSS, and SQL.

Includes classification of external dependencies as stdlib vs third-party.

## Statistics

- **Total files**: 138
- **Intra-repo dependencies**: 323
- **External stdlib dependencies**: 39
- **External third-party dependencies**: 86

## External Dependencies

### Standard Library / Core Modules

Total: 39 unique modules

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
- ... and 19 more (see JSON for full list)

### Third-Party Packages

Total: 86 unique packages

- `@eslint/js`
- `@vitejs/plugin-react`
- `alembic.command`
- `alembic.config.Config`
- `alembic.context`
- `alembic.op`
- `axios`
- `eslint-plugin-prettier/recommended`
- `eslint-plugin-react-hooks`
- `eslint-plugin-react-refresh`
- `fastapi.APIRouter`
- `fastapi.Depends`
- `fastapi.FastAPI`
- `fastapi.HTTPException`
- `fastapi.Header`
- `fastapi.Query`
- `fastapi.Request`
- `fastapi.Response`
- `fastapi.exceptions.RequestValidationError`
- `fastapi.middleware.cors.CORSMiddleware`
- ... and 66 more (see JSON for full list)

## Most Depended Upon Files (Intra-Repo)

- `src/consensus_engine/schemas/proposal.py` (27 dependents)
- `src/consensus_engine/schemas/review.py` (24 dependents)
- `src/consensus_engine/exceptions.py` (22 dependents)
- `src/consensus_engine/config/settings.py` (20 dependents)
- `src/consensus_engine/config/__init__.py` (18 dependents)
- `src/consensus_engine/db/models.py` (18 dependents)
- `src/consensus_engine/config/logging.py` (15 dependents)
- `src/consensus_engine/app.py` (11 dependents)
- `src/consensus_engine/db/__init__.py` (10 dependents)
- `src/consensus_engine/db/dependencies.py` (9 dependents)

## Files with Most Dependencies (Intra-Repo)

- `src/consensus_engine/workers/pipeline_worker.py` (11 dependencies)
- `src/consensus_engine/api/routes/runs.py` (10 dependencies)
- `src/consensus_engine/app.py` (10 dependencies)
- `src/consensus_engine/api/routes/full_review.py` (9 dependencies)
- `src/consensus_engine/api/routes/review.py` (8 dependencies)
- `src/consensus_engine/services/orchestrator.py` (8 dependencies)
- `webapp/src/api/generated/services/RunsService.ts` (8 dependencies)
- `src/consensus_engine/api/routes/expand.py` (7 dependencies)
- `src/consensus_engine/services/review.py` (7 dependencies)
- `tests/integration/test_pipeline_worker.py` (7 dependencies)
