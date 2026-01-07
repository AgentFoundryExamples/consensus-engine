# Dependency Graph

Multi-language intra-repository dependency analysis.

Supports Python, JavaScript/TypeScript, C/C++, Rust, Go, Java, C#, Swift, HTML/CSS, and SQL.

Includes classification of external dependencies as stdlib vs third-party.

## Statistics

- **Total files**: 22
- **Intra-repo dependencies**: 25
- **External stdlib dependencies**: 14
- **External third-party dependencies**: 16

## External Dependencies

### Standard Library / Core Modules

Total: 14 unique modules

- `collections.abc.AsyncGenerator`
- `contextlib.asynccontextmanager`
- `enum.Enum`
- `functools.lru_cache`
- `logging`
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

Total: 16 unique packages

- `fastapi.Depends`
- `fastapi.FastAPI`
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
- `pydantic_settings.BaseSettings`
- `pydantic_settings.SettingsConfigDict`
- `pytest`

## Most Depended Upon Files (Intra-Repo)

- `src/consensus_engine/config/settings.py` (6 dependents)
- `src/consensus_engine/exceptions.py` (4 dependents)
- `src/consensus_engine/schemas/proposal.py` (4 dependents)
- `src/consensus_engine/config/__init__.py` (3 dependents)
- `src/consensus_engine/config/logging.py` (3 dependents)
- `src/consensus_engine/services/expand.py` (2 dependents)
- `src/consensus_engine/clients/openai_client.py` (2 dependents)
- `src/consensus_engine/app.py` (1 dependents)

## Files with Most Dependencies (Intra-Repo)

- `src/consensus_engine/services/expand.py` (4 dependencies)
- `tests/unit/test_expand_service.py` (4 dependencies)
- `src/consensus_engine/clients/openai_client.py` (3 dependencies)
- `tests/unit/test_openai_client.py` (3 dependencies)
- `src/consensus_engine/app.py` (2 dependencies)
- `tests/integration/test_app.py` (2 dependencies)
- `src/consensus_engine/config/__init__.py` (1 dependencies)
- `src/consensus_engine/config/logging.py` (1 dependencies)
- `src/consensus_engine/schemas/__init__.py` (1 dependencies)
- `src/consensus_engine/services/__init__.py` (1 dependencies)
