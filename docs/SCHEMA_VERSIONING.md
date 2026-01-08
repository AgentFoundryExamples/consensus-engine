# Schema Versioning and Validation

## Overview

The Consensus Engine uses a comprehensive schema versioning system to ensure compatibility, traceability, and deterministic behavior across all LLM-based operations. This document explains the versioning conventions, validation mechanisms, and best practices.

## Key Concepts

### Schema Registry

All schemas used for structured LLM outputs are registered in a central registry (`src/consensus_engine/schemas/registry.py`) with explicit version metadata:

- **Schema Version**: Semantic version (e.g., `1.0.0`) identifying the schema structure
- **Prompt Set Version**: Version of the prompts used to generate responses
- **Description**: Human-readable description of the schema
- **Deprecation Status**: Whether the version is deprecated
- **Migration Notes**: Guidance for version upgrades

### Registered Schemas

The system currently maintains four core schemas:

1. **ExpandedProposal** - Structured proposal output from expansion step
2. **PersonaReview** - Review from a specific persona
3. **DecisionAggregation** - Aggregated multi-persona decision
4. **RunStatus** - Run lifecycle state wrapper

All schemas are currently at version `1.0.0` with prompt set version `1.0.0`.

## Version Tracking Flow

### 1. LLM Request

When the OpenAI client makes a request with structured outputs:

```python
client.create_structured_response_with_payload(
    instruction_payload=payload,
    response_model=ExpandedProposal,
    schema_name="ExpandedProposal",  # Links to registry
    step_name="expand",
)
```

The client:
- Retrieves current schema version from registry
- Validates the response against the registered schema
- Includes schema_version and prompt_set_version in metadata

### 2. Service Layer

Services receive validated responses with version metadata:

```python
proposal, metadata = expand_idea(idea_input, settings)

# metadata includes:
# - schema_version: "1.0.0"
# - prompt_set_version: "1.0.0"
# - schema_name: "ExpandedProposal"
```

### 3. API Response

All API endpoints include version information in their responses:

```json
{
  "problem_statement": "...",
  "proposed_solution": "...",
  "assumptions": [...],
  "scope_non_goals": [...],
  "schema_version": "1.0.0",
  "prompt_set_version": "1.0.0",
  "metadata": {
    "request_id": "...",
    "model": "gpt-5.1",
    ...
  }
}
```

### 4. Database Persistence

The pipeline worker stores version information in the database:

- Run parameters include schema_version and prompt_set_version
- Proposal, reviews, and decisions store version metadata in JSON
- Version consistency is validated before marking runs complete

## Validation Mechanisms

### Response Validation

Every LLM response is validated against its registered schema:

```python
from consensus_engine.schemas.validation import validate_against_schema

validate_against_schema(
    instance=proposal,
    schema_name="ExpandedProposal",
    context={"request_id": "...", "step_name": "expand"}
)
```

**On Validation Failure:**
- `SchemaValidationError` is raised with detailed field-level errors
- Error includes schema_version, field paths, and context
- Client receives 500 error with actionable debugging information

Example error response:
```json
{
  "code": "SCHEMA_VALIDATION_ERROR",
  "message": "Schema validation failed for ExpandedProposal v1.0.0",
  "schema_version": "1.0.0",
  "field_errors": [
    {
      "field": "problem_statement",
      "message": "Field required",
      "type": "missing"
    }
  ],
  "details": {...}
}
```

### Version Consistency Checks

The pipeline worker validates that all schemas within a run use consistent versions:

```python
from consensus_engine.schemas.validation import check_version_consistency

check_version_consistency(
    schema_versions=[
        {"schema_name": "ExpandedProposal", "schema_version": "1.0.0"},
        {"schema_name": "PersonaReview", "schema_version": "1.0.0"},
        {"schema_name": "DecisionAggregation", "schema_version": "1.0.0"},
    ],
    context={"run_id": "..."}
)
```

**On Inconsistency Detection:**
- Warning is logged but run is not failed (for backwards compatibility)
- Error details include all inconsistent schemas and their versions
- Helps operators detect deployment issues

## API Versioning

### Base Path Convention

All API routes use the `/v1` prefix to support global version rollouts:

```python
router = APIRouter(prefix="/v1", tags=["expand"])

@router.post("/expand-idea", ...)
# Results in: POST /v1/expand-idea
```

### Version Migration Strategy

**For Breaking Changes:**
1. Increment schema version in registry (e.g., `1.0.0` → `2.0.0`)
2. Create new API version path (`/v2/...`)
3. Update documentation for migration path
4. Deprecate old version with timeline

**For Compatible Changes (minor/patch):**
1. Increment minor/patch version (e.g., `1.0.0` → `1.1.0`)
2. Maintain existing API paths
3. Ensure backward compatibility validation
4. Update documentation

## Error Handling

### Schema Validation Errors

When LLM responses fail validation:

**HTTP Status:** 500 Internal Server Error

**Response Body:**
```json
{
  "code": "SCHEMA_VALIDATION_ERROR",
  "message": "Schema validation failed for PersonaReview v1.0.0",
  "schema_version": "1.0.0",
  "field_errors": [
    {"field": "confidence_score", "message": "value must be ≥ 0.0", "type": "greater_than_equal"}
  ],
  "details": {
    "schema_name": "PersonaReview",
    "request_id": "...",
    "step_name": "review"
  }
}
```

**Client Action:** Log error with schema_version and field details for debugging

### Version Consistency Errors

When mixed versions are detected:

**Effect:** Warning logged, run continues (non-fatal)

**Log Message:**
```
Schema version consistency check failed
inconsistent_schemas: {"PersonaReview": ["1.0.0", "2.0.0"]}
run_id: "..."
```

**Operator Action:** Review deployment configuration, ensure single schema version per deployment

## Best Practices

### For Development

1. **Always specify schema_name** when calling OpenAI client:
   ```python
   client.create_structured_response_with_payload(
       ...,
       schema_name="ExpandedProposal"  # Required!
   )
   ```

2. **Include version info in API responses**:
   ```python
   return ExpandIdeaResponse(
       ...,
       schema_version=metadata.get("schema_version"),
       prompt_set_version=metadata.get("prompt_set_version")
   )
   ```

3. **Validate before persistence**:
   ```python
   # Service layer should validate before returning
   validate_against_schema(instance, schema_name, context={...})
   ```

### For Operations

1. **Monitor validation errors** - Track schema validation failures in logs
2. **Enforce single version** - Use consistent schema versions across deployment
3. **Plan migrations** - Breaking changes require API version increments
4. **Test thoroughly** - Validate schema changes with comprehensive tests

### For Clients

1. **Check schema_version** - Use version metadata for compatibility checks
2. **Handle validation errors** - Parse field_errors for specific issues
3. **Monitor version changes** - Subscribe to schema deprecation notices
4. **Cache version info** - Reduce redundant version lookups

## Configuration

### Registry Configuration

Register new schema versions in `src/consensus_engine/schemas/registry.py`:

```python
_registry.register(
    schema_name="NewSchema",
    version="1.0.0",
    schema_class=NewSchemaModel,
    description="Description of the schema",
    is_current=True,
    prompt_set_version="1.0.0",
)
```

### Validation Configuration

Validation is automatically enabled for all registered schemas. To customize:

```python
# Optional: Provide specific schema version
schema_version = get_schema_version("ExpandedProposal", "1.0.0")

validate_against_schema(
    instance=proposal,
    schema_name="ExpandedProposal",
    schema_version=schema_version,  # Use specific version
    context={...}
)
```

## Testing

### Unit Tests

Test validation functionality:

```python
def test_validate_valid_proposal():
    proposal = ExpandedProposal(...)
    validate_against_schema(
        instance=proposal,
        schema_name="ExpandedProposal"
    )
    # Should not raise
```

### Integration Tests

Test version tracking in API flows:

```python
def test_expand_includes_version_metadata():
    response = client.post("/v1/expand-idea", json={...})
    assert "schema_version" in response.json()
    assert "prompt_set_version" in response.json()
```

## Troubleshooting

### "Schema validation failed" errors

**Cause:** LLM response doesn't match expected schema

**Solution:**
1. Check field_errors in error response for specific issues
2. Review prompt instructions for clarity
3. Verify schema_version matches expectation
4. Consider if schema needs updating

### "Mixed schema versions detected" warnings

**Cause:** Different parts of system using different schema versions

**Solution:**
1. Review deployment configuration
2. Ensure all services use same schema version
3. Complete pending migrations
4. Restart services to clear cache

### Version mismatch between runs

**Cause:** Schema version changed during long-running operations

**Solution:**
1. Complete in-flight runs before deploying new versions
2. Implement graceful version transitions
3. Use feature flags for gradual rollout

## References

- **Schema Registry:** `src/consensus_engine/schemas/registry.py`
- **Validation Utils:** `src/consensus_engine/schemas/validation.py`
- **OpenAI Client:** `src/consensus_engine/clients/openai_client.py`
- **Tests:** `tests/unit/test_schema_validation.py`
