# Dependency Graph

Multi-language intra-repository dependency analysis.

Supports Python, JavaScript/TypeScript, C/C++, Rust, Go, Java, C#, Swift, HTML/CSS, and SQL.

Includes classification of external dependencies as stdlib vs third-party.

## Statistics

- **Total files**: 50
- **Intra-repo dependencies**: 136
- **External stdlib dependencies**: 19
- **External third-party dependencies**: 24

## External Dependencies

### Standard Library / Core Modules

Total: 19 unique modules

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

### Third-Party Packages

Total: 24 unique packages

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
- `httpx`
- `openai.`
- `openai.APIConnectionError`
- `openai.APITimeoutError`
- `openai.AuthenticationError`
- `openai.OpenAI`
- `openai.RateLimitError`
- `pydantic.BaseModel`
- `pydantic.Field`
- `pydantic.ValidationError`
- ... and 4 more (see JSON for full list)

## Most Depended Upon Files (Intra-Repo)

- `src/consensus_engine/schemas/proposal.py` (21 dependents)
- `src/consensus_engine/schemas/review.py` (17 dependents)
- `src/consensus_engine/exceptions.py` (16 dependents)
- `src/consensus_engine/config/settings.py` (14 dependents)
- `src/consensus_engine/config/__init__.py` (10 dependents)
- `src/consensus_engine/config/logging.py` (10 dependents)
- `src/consensus_engine/schemas/requests.py` (6 dependents)
- `src/consensus_engine/services/review.py` (5 dependents)
- `src/consensus_engine/clients/openai_client.py` (5 dependents)
- `src/consensus_engine/app.py` (5 dependents)

## Files with Most Dependencies (Intra-Repo)

- `src/consensus_engine/api/routes/full_review.py` (8 dependencies)
- `src/consensus_engine/api/routes/review.py` (7 dependencies)
- `src/consensus_engine/app.py` (7 dependencies)
- `src/consensus_engine/services/orchestrator.py` (6 dependencies)
- `tests/integration/test_acceptance_criteria.py` (6 dependencies)
- `src/consensus_engine/api/dependencies.py` (5 dependencies)
- `src/consensus_engine/api/routes/expand.py` (5 dependencies)
- `src/consensus_engine/services/review.py` (5 dependencies)
- `tests/integration/test_full_review_endpoint.py` (5 dependencies)
- `tests/integration/test_multi_persona.py` (5 dependencies)
