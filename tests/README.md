# Test Suite Documentation

This directory contains the comprehensive test suite for the Consensus Engine.

## Directory Structure

```
tests/
├── fixtures/          # Test data and fixtures
│   ├── schemas/      # Schema version fixtures (JSON)
│   └── README.md     # Fixture documentation
├── integration/       # Integration tests
│   └── ...           # End-to-end and service integration tests
├── unit/             # Unit tests
│   ├── test_schema_registry.py      # Schema contract tests
│   ├── test_instruction_builder.py  # Instruction builder tests
│   └── ...           # Other unit tests
└── conftest.py       # Shared fixtures and configuration
```

## Test Categories

### Unit Tests (`tests/unit/`)

Unit tests validate individual components in isolation:

- **Schema Tests**: Validate schema structure, versioning, and serialization
- **Instruction Builder Tests**: Verify instruction hierarchy and metadata
- **Service Tests**: Test individual service logic with mocked dependencies
- **Validation Tests**: Ensure input validation and error handling
- **Model Tests**: Verify database model behavior

**Key test files:**

- `test_schema_registry.py`: Schema contract and backward compatibility tests
- `test_instruction_builder.py`: Instruction composition and versioning tests
- `test_request_schemas.py`: Request schema validation tests
- `test_review_schemas.py`: Review schema validation tests
- `test_proposal_schemas.py`: Proposal schema validation tests

### Integration Tests (`tests/integration/`)

Integration tests validate multiple components working together:

- **Endpoint Tests**: Test API endpoints with database integration
- **Service Integration**: Test services with real dependencies
- **Workflow Tests**: Validate end-to-end workflows
- **Database Tests**: Test database operations and migrations

**Key test files:**

- `test_runs_endpoint.py`: Run retrieval and persistence tests
- `test_full_review_endpoint.py`: Full review workflow tests
- `test_expand_endpoint.py`: Expand service endpoint tests
- `test_review_endpoint.py`: Review service endpoint tests

## Schema and Prompt Contract Testing

### Why Schema Contract Tests Matter

Schema contract tests prevent silent regressions by:

1. **Locking in Schema Structure**: Tests fail if fields are removed/renamed without explicit version bumps
2. **Ensuring Backward Compatibility**: Old payloads must validate with newer minor versions
3. **Documenting Breaking Changes**: Major version changes require explicit migration notes
4. **Preventing API Drift**: Schema changes are intentional and documented

### Schema Test Organization

**Snapshot Tests** (`TestSchemaStructureSnapshots`):
- Validate JSON schema structure for each version
- Ensure all required and optional fields exist
- Verify field types and constraints
- Check version metadata presence

**Backward Compatibility Tests** (`TestBackwardCompatibility`):
- Load fixture payloads from prior versions
- Validate minor version changes remain compatible
- Document major version breaking change behavior
- Test forward compatibility with unknown fields

**Example:**
```python
def test_expanded_proposal_schema_structure_v1_0_0(self) -> None:
    """Test ExpandedProposal v1.0.0 schema has expected fields."""
    schema_version = get_schema_version("ExpandedProposal", "1.0.0")
    json_schema = schema_version.get_json_schema()
    
    # Verify required fields
    assert "problem_statement" in json_schema["required"]
    assert "proposed_solution" in json_schema["required"]
    # ... more assertions
```

## Instruction Builder Testing

### Why Instruction Hierarchy Tests Matter

Instruction builder tests ensure:

1. **Correct Ordering**: System → Developer → User instruction ordering is maintained
2. **Persona Injection**: Persona content is correctly injected into developer instructions
3. **Version Tagging**: prompt_set_version is included in all payloads
4. **Metadata Completeness**: All expected metadata is present

### Instruction Builder Test Organization

**Hierarchy Tests** (`TestInstructionHierarchyOrdering`):
- Verify instruction ordering (system, developer, user)
- Test instruction separation and combining
- Ensure persona injection preserves ordering

**Persona Injection Tests** (`TestPersonaContentInjection`):
- Validate persona name appears in developer instructions
- Verify persona-specific instructions are included
- Test persona injection with/without existing developer instructions

**Versioning Tests** (`TestPromptSetVersionTagging`):
- Ensure prompt_set_version is present in all payloads
- Validate version consistency across different payload types
- Test version metadata for expand, review, and aggregate steps

**Metadata Tests** (`TestInstructionPayloadMetadata`):
- Verify all expected metadata fields
- Test custom metadata preservation
- Validate step-specific metadata

## Running Tests

### All Tests

```bash
# Run entire test suite with coverage
pytest

# Run tests with verbose output
pytest -v

# Run tests with coverage report
pytest --cov=consensus_engine --cov-report=term-missing
```

### Specific Test Categories

```bash
# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v

# Run specific test file
pytest tests/unit/test_schema_registry.py -v

# Run specific test class
pytest tests/unit/test_schema_registry.py::TestBackwardCompatibility -v

# Run specific test
pytest tests/unit/test_schema_registry.py::TestBackwardCompatibility::test_load_expanded_proposal_v1_0_0_fixture -v
```

### Schema Contract Tests

```bash
# Run all schema contract tests
pytest tests/unit/test_schema_registry.py -v

# Run only snapshot tests
pytest tests/unit/test_schema_registry.py::TestSchemaStructureSnapshots -v

# Run only backward compatibility tests
pytest tests/unit/test_schema_registry.py::TestBackwardCompatibility -v
```

### Instruction Builder Tests

```bash
# Run all instruction builder tests
pytest tests/unit/test_instruction_builder.py -v

# Run only hierarchy tests
pytest tests/unit/test_instruction_builder.py::TestInstructionHierarchyOrdering -v

# Run only persona injection tests
pytest tests/unit/test_instruction_builder.py::TestPersonaContentInjection -v

# Run only versioning tests
pytest tests/unit/test_instruction_builder.py::TestPromptSetVersionTagging -v
```

## Writing New Tests

### Test Naming Conventions

- **Test files**: `test_<module_name>.py`
- **Test classes**: `Test<ComponentName>` (e.g., `TestSchemaRegistry`)
- **Test methods**: `test_<behavior_being_tested>` (e.g., `test_schema_field_removal_detection`)

### Test Structure

```python
def test_specific_behavior(self) -> None:
    """Test description explaining what is being validated."""
    # Arrange: Set up test data and dependencies
    builder = InstructionBuilder()
    
    # Act: Perform the action being tested
    payload = builder.with_system_instruction("System").build()
    
    # Assert: Verify expected outcomes
    assert payload.system_instruction == "System"
    assert "prompt_set_version" in payload.metadata
```

### Test Best Practices

**DO:**

✅ Write descriptive test names that explain behavior
✅ Use docstrings to document what's being tested and why
✅ Test both happy paths and error cases
✅ Use fixtures for reusable test data
✅ Mock external dependencies (LLM API, database in unit tests)
✅ Keep tests focused and atomic
✅ Use deterministic test data (no random values)

**DON'T:**

❌ Write tests that depend on external services
❌ Use time.sleep() or arbitrary waits
❌ Test implementation details (test behavior, not internals)
❌ Create tests that depend on execution order
❌ Modify existing tests to make them pass (unless they're incorrect)
❌ Use mutable shared state between tests

## Test Fixtures

### Using Fixtures

Fixtures provide reusable test data and setup:

```python
@pytest.fixture
def sample_proposal():
    """Provide a sample ExpandedProposal for testing."""
    return ExpandedProposal(
        problem_statement="Problem",
        proposed_solution="Solution",
        assumptions=["Assumption"],
        scope_non_goals=["Non-goal"],
    )

def test_with_fixture(sample_proposal):
    """Test using the fixture."""
    assert sample_proposal.problem_statement == "Problem"
```

### Fixture Locations

- **Shared fixtures**: `tests/conftest.py`
- **Module-specific fixtures**: In the test file itself
- **Data fixtures**: `tests/fixtures/`

## Deterministic Testing

To ensure tests are deterministic and reproducible:

### Time Freezing

```python
from unittest.mock import patch
from datetime import datetime

@patch('consensus_engine.module.datetime')
def test_with_frozen_time(mock_datetime):
    """Test with a fixed timestamp."""
    mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0, 0)
    # Test code that uses datetime.now()
```

### UUID Freezing

```python
from unittest.mock import patch
import uuid

@patch('consensus_engine.module.uuid.uuid4')
def test_with_frozen_uuid(mock_uuid):
    """Test with a fixed UUID."""
    mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
    # Test code that generates UUIDs
```

### Random Seed

```python
import random

def test_with_random_seed():
    """Test with a fixed random seed."""
    random.seed(42)
    # Test code that uses random values
```

## Test Coverage

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=consensus_engine --cov-report=html

# View report
open htmlcov/index.html
```

### Coverage Goals

- **Unit tests**: Aim for >90% coverage of business logic
- **Integration tests**: Focus on critical workflows and error paths
- **Avoid**: Chasing 100% coverage; focus on meaningful tests

### What to Test

**High Priority:**
- Business logic and algorithms
- Validation and error handling
- Schema contracts and versioning
- Instruction building and prompt composition
- API request/response handling

**Lower Priority:**
- Simple getters/setters
- Configuration loading (unless complex logic)
- Framework code (FastAPI, SQLAlchemy internals)

## Debugging Tests

### Running with Debugger

```bash
# Run with pdb on failure
pytest --pdb

# Run specific test with pdb
pytest tests/unit/test_schema_registry.py::TestBackwardCompatibility::test_load_expanded_proposal_v1_0_0_fixture --pdb
```

### Verbose Output

```bash
# Show print statements and detailed assertions
pytest -v -s

# Show local variables on failure
pytest -v -l
```

### Selective Testing

```bash
# Run tests matching pattern
pytest -k "schema" -v

# Run tests NOT matching pattern
pytest -k "not integration" -v
```

## Continuous Integration

Tests run automatically on:
- Pull request creation
- Push to main branch
- Manual workflow trigger

CI fails if:
- Any test fails
- Coverage drops below threshold
- Linting errors exist

## Related Documentation

- **Fixture Documentation**: `tests/fixtures/README.md`
- **Schema Registry**: `src/consensus_engine/schemas/registry.py`
- **Instruction Builder**: `src/consensus_engine/config/instruction_builder.py`
- **Contributing Guide**: `CONTRIBUTING.md` (if exists)

## Getting Help

- **Test failures**: Check test output and logs carefully
- **Coverage questions**: Run `pytest --cov-report=html` for detailed report
- **Schema changes**: See `tests/fixtures/README.md` for versioning guide
- **New tests**: Follow existing patterns in similar test files
