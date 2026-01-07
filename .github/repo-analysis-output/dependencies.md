# Dependency Graph

Multi-language intra-repository dependency analysis.

Supports Python, JavaScript/TypeScript, C/C++, Rust, Go, Java, C#, Swift, HTML/CSS, and SQL.

Includes classification of external dependencies as stdlib vs third-party.

## Statistics

- **Total files**: 13
- **Intra-repo dependencies**: 7
- **External stdlib dependencies**: 6
- **External third-party dependencies**: 9

## External Dependencies

### Standard Library / Core Modules

Total: 6 unique modules

- `collections.abc.AsyncGenerator`
- `contextlib.asynccontextmanager`
- `enum.Enum`
- `functools.lru_cache`
- `logging`
- `sys`

### Third-Party Packages

Total: 9 unique packages

- `fastapi.Depends`
- `fastapi.FastAPI`
- `fastapi.testclient.TestClient`
- `pydantic.Field`
- `pydantic.ValidationError`
- `pydantic.field_validator`
- `pydantic_settings.BaseSettings`
- `pydantic_settings.SettingsConfigDict`
- `pytest`

## Most Depended Upon Files (Intra-Repo)

- `src/consensus_engine/config/__init__.py` (3 dependents)
- `src/consensus_engine/config/settings.py` (2 dependents)
- `src/consensus_engine/config/logging.py` (1 dependents)
- `src/consensus_engine/app.py` (1 dependents)

## Files with Most Dependencies (Intra-Repo)

- `src/consensus_engine/app.py` (2 dependencies)
- `tests/integration/test_app.py` (2 dependencies)
- `src/consensus_engine/config/__init__.py` (1 dependencies)
- `src/consensus_engine/config/logging.py` (1 dependencies)
- `tests/unit/test_config.py` (1 dependencies)
