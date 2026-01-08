# Schema Registry

## Overview

The Schema Registry provides a centralized, versioned system for managing JSON schemas in the consensus engine. It ensures deterministic contracts and enables safe prompt evolution by explicitly tracking schema versions and their associated prompt sets.

## Purpose

The schema registry solves several key problems:

1. **Version Management**: Each schema has an explicit semantic version, making it clear which contract version is being used
2. **Single Source of Truth**: All schema definitions are centralized in the registry, preventing ad-hoc duplicates
3. **Prompt Evolution**: By linking schema versions to prompt set versions, we can safely evolve prompts while maintaining compatibility
4. **Serialization Metadata**: All serialized data includes version metadata for audit and compatibility tracking
5. **Backward Compatibility**: The registry supports multiple versions of the same schema, enabling gradual migrations

## Architecture

### Core Components

#### SchemaVersion

A dataclass that encapsulates a specific version of a schema:

```python
@dataclass
class SchemaVersion:
    version: str                    # Semantic version (e.g., "1.0.0")
    schema_class: type[BaseModel]   # Pydantic model class
    description: str                # Human-readable description
    prompt_set_version: str | None  # Associated prompt version
    deprecated: bool                # Deprecation flag
    migration_notes: str | None     # Migration guidance
```

Key methods:
- `to_dict(instance)`: Serialize with version metadata
- `to_json(instance)`: Serialize to JSON with version metadata
- `get_json_schema()`: Get JSON schema with version metadata

#### SchemaRegistry

The central registry that manages all schema versions:

```python
class SchemaRegistry:
    def register(schema_name, version, schema_class, ...)
    def get_current(schema_name) -> SchemaVersion
    def get_version(schema_name, version) -> SchemaVersion
    def list_schemas() -> list[str]
    def list_versions(schema_name) -> list[str]
```

## Registered Schemas

The following schemas are registered in version 1.0.0:

### ExpandedProposal

Structured output from the LLM expansion service containing:
- `problem_statement`: Clear problem articulation
- `proposed_solution`: Detailed solution approach
- `assumptions`: List of underlying assumptions
- `scope_non_goals`: List of what's out of scope
- Optional fields: `title`, `summary`, `raw_idea`, `metadata`, `raw_expanded_proposal`

**Prompt Set Version**: 1.0.0

### PersonaReview

Review from a specific persona evaluating a proposal:
- `persona_name`: Name of the reviewing persona
- `persona_id`: Stable identifier (e.g., 'architect', 'security_guardian')
- `confidence_score`: Confidence in the proposal [0.0, 1.0]
- `strengths`: List of identified strengths
- `concerns`: List of concerns with blocking flags
- `recommendations`: List of actionable recommendations
- `blocking_issues`: List of critical blocking issues
- `estimated_effort`: Effort estimation
- `dependency_risks`: List of identified dependency risks

**Prompt Set Version**: 1.0.0

### DecisionAggregation

Aggregated decision from multiple persona reviews:
- `overall_weighted_confidence`: Weighted confidence score [0.0, 1.0]
- `decision`: Final decision (approve/revise/reject)
- `score_breakdown`: Per-persona scoring details (legacy)
- `detailed_score_breakdown`: Detailed scoring with formula (new)
- `minority_report`: Optional dissenting opinion (legacy)
- `minority_reports`: List of dissenting opinions (new)

**Prompt Set Version**: 1.0.0

### RunStatus

Run lifecycle state enum (queued, running, completed, failed)

**Prompt Set Version**: 1.0.0

## Usage

### Getting the Current Schema Version

```python
from consensus_engine.schemas import get_current_schema

# Get current ExpandedProposal schema
schema_version = get_current_schema("ExpandedProposal")
print(f"Current version: {schema_version.version}")
print(f"Prompt set version: {schema_version.prompt_set_version}")
```

### Getting a Specific Schema Version

```python
from consensus_engine.schemas import get_schema_version

# Get a specific version (useful for backward compatibility)
schema_version = get_schema_version("PersonaReview", "1.0.0")
```

### Serializing with Version Metadata

```python
from consensus_engine.schemas import ExpandedProposal, get_current_schema

# Create a proposal
proposal = ExpandedProposal(
    problem_statement="Build a REST API",
    proposed_solution="Use FastAPI framework",
    assumptions=["Python 3.11+"],
    scope_non_goals=["Mobile app"],
)

# Get schema version
schema_version = get_current_schema("ExpandedProposal")

# Serialize to dict with metadata
data = schema_version.to_dict(proposal)
# Result includes: {"problem_statement": "...", "_schema_version": "1.0.0", ...}

# Serialize to JSON with metadata
json_str = schema_version.to_json(proposal)
```

### Getting JSON Schema

```python
from consensus_engine.schemas import get_current_schema

schema_version = get_current_schema("PersonaReview")
json_schema = schema_version.get_json_schema()
# Result includes: {"$version": "1.0.0", "$prompt_set_version": "1.0.0", ...}
```

### Listing Available Schemas

```python
from consensus_engine.schemas import list_all_schemas, list_schema_versions

# List all registered schemas
schemas = list_all_schemas()
# Result: ["ExpandedProposal", "PersonaReview", "DecisionAggregation", "RunStatus"]

# List all versions of a specific schema
versions = list_schema_versions("ExpandedProposal")
# Result: ["1.0.0"]
```

## Error Handling

### Unknown Schema

```python
from consensus_engine.schemas import get_current_schema, SchemaNotFoundError

try:
    schema_version = get_current_schema("NonExistentSchema")
except SchemaNotFoundError as e:
    print(f"Schema not found: {e}")
    # Error includes list of available schemas
```

### Unknown Version

```python
from consensus_engine.schemas import get_schema_version, SchemaVersionNotFoundError

try:
    schema_version = get_schema_version("ExpandedProposal", "99.0.0")
except SchemaVersionNotFoundError as e:
    print(f"Version not found: {e}")
    # Error includes list of available versions
```

## Adding New Schema Versions

To add a new version of an existing schema:

1. Create the new Pydantic model class (or modify the existing one)
2. Register the new version in the registry:

```python
# In src/consensus_engine/schemas/registry.py

_registry.register(
    schema_name="ExpandedProposal",
    version="2.0.0",
    schema_class=ExpandedProposalV2,
    description="Enhanced proposal schema with additional fields",
    is_current=True,  # Make this the new current version
    prompt_set_version="2.0.0",
    deprecated=False,
)

# Optionally mark the old version as deprecated
_registry.register(
    schema_name="ExpandedProposal",
    version="1.0.0",
    schema_class=ExpandedProposal,
    description="Original proposal schema",
    is_current=False,
    prompt_set_version="1.0.0",
    deprecated=True,
    migration_notes="Use version 2.0.0 for new proposals. See MIGRATION.md for details.",
)
```

3. Add migration tests to ensure backward compatibility
4. Update documentation with migration guidance

## Best Practices

### DO

- ✅ Always use `get_current_schema()` in production code to get the active version
- ✅ Include version metadata in all serialized data
- ✅ Use semantic versioning (MAJOR.MINOR.PATCH)
- ✅ Document breaking changes in migration notes
- ✅ Test backward compatibility when adding new versions
- ✅ Mark old versions as deprecated when superseded

### DON'T

- ❌ Don't create duplicate schema definitions outside the registry
- ❌ Don't modify a schema without bumping its version
- ❌ Don't remove old versions until all data is migrated
- ❌ Don't forget to update prompt_set_version when prompts change
- ❌ Don't use hardcoded version strings in application code

## Testing

The schema registry includes comprehensive unit tests covering:

- Registry initialization and registration
- Getting current and specific versions
- Error handling for unknown schemas/versions
- Serialization with metadata
- Backward compatibility
- Deprecated version warnings
- Multiple version management

Run tests with:

```bash
pytest tests/unit/test_schema_registry.py -v
```

## Integration with Database Models

The schema registry works alongside database models:

- **Schema Classes** (Pydantic): For validation, serialization, and API contracts
- **Database Models** (SQLAlchemy): For persistence and queries

Example:

```python
from consensus_engine.schemas import ExpandedProposal, get_current_schema
from consensus_engine.db.models import Proposal

# Deserialize from database
proposal_data = db_proposal.proposal_json
proposal = ExpandedProposal(**proposal_data)

# Serialize with version metadata
schema_version = get_current_schema("ExpandedProposal")
versioned_data = schema_version.to_dict(proposal)

# Store back to database
db_proposal.proposal_json = versioned_data
```

## Future Enhancements

Potential improvements to the schema registry:

1. **Automatic Migration**: Helper functions to migrate data between versions
2. **Schema Validation**: Validate persisted data against its declared version
3. **Version Inference**: Detect schema version from data structure
4. **Compatibility Matrix**: Track which versions are compatible with each other
5. **Schema Evolution Rules**: Automated checks for backward-compatible changes
6. **Audit Logging**: Track when specific versions are requested and by whom

## References

- [Semantic Versioning](https://semver.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [JSON Schema Specification](https://json-schema.org/)
