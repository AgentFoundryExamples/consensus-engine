# Dependency Graph

Multi-language intra-repository dependency analysis.

Supports Python, JavaScript/TypeScript, C/C++, Rust, Go, Java, C#, Swift, HTML/CSS, and SQL.

Includes classification of external dependencies as stdlib vs third-party.

## Statistics

- **Total files**: 34
- **Intra-repo dependencies**: 55
- **External stdlib dependencies**: 21
- **External third-party dependencies**: 23

## External Dependencies

### Standard Library / Core Modules

Total: 21 unique modules

- `collections.abc.AsyncGenerator`
- `collections.abc.Awaitable`
- `collections.abc.Callable`
- `collections.abc.Generator`
- `contextlib.asynccontextmanager`
- `enum.Enum`
- `functools.lru_cache`
- `json`
- `logging`
- `re`
- `sys`
- `time`
- `typing.Any`
- `typing.TypeVar`
- `typing.cast`
- `unittest.mock.MagicMock`
- `unittest.mock.Mock`
- `unittest.mock.patch`
- `uuid`
- `uuid.UUID`
- ... and 1 more (see JSON for full list)

### Third-Party Packages

Total: 23 unique packages

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
- `openai.`
- `openai.APIConnectionError`
- `openai.APITimeoutError`
- `openai.AuthenticationError`
- `openai.OpenAI`
- `openai.RateLimitError`
- `pydantic.BaseModel`
- `pydantic.Field`
- `pydantic.ValidationError`
- `pydantic.field_validator`
- ... and 3 more (see JSON for full list)

## Most Depended Upon Files (Intra-Repo)

- `src/consensus_engine/schemas/proposal.py` (10 dependents)
- `src/consensus_engine/exceptions.py` (8 dependents)
- `src/consensus_engine/config/settings.py` (7 dependents)
- `src/consensus_engine/config/__init__.py` (6 dependents)
- `src/consensus_engine/config/logging.py` (5 dependents)
- `src/consensus_engine/services/expand.py` (4 dependents)
- `src/consensus_engine/schemas/requests.py` (4 dependents)
- `src/consensus_engine/schemas/review.py` (3 dependents)
- `src/consensus_engine/app.py` (3 dependents)
- `src/consensus_engine/clients/openai_client.py` (2 dependents)

## Files with Most Dependencies (Intra-Repo)

- `src/consensus_engine/api/routes/expand.py` (5 dependencies)
- `src/consensus_engine/app.py` (5 dependencies)
- `src/consensus_engine/services/expand.py` (4 dependencies)
- `tests/integration/test_expand_endpoint.py` (4 dependencies)
- `tests/unit/test_expand_service.py` (4 dependencies)
- `src/consensus_engine/api/dependencies.py` (3 dependencies)
- `src/consensus_engine/api/routes/health.py` (3 dependencies)
- `src/consensus_engine/clients/openai_client.py` (3 dependencies)
- `tests/conftest.py` (3 dependencies)
- `tests/integration/test_expand_service.py` (3 dependencies)
