# Test Fixtures Documentation

This directory contains test fixtures used to validate schema contracts and ensure backward compatibility.

## Directory Structure

```
tests/fixtures/
└── schemas/
    ├── expanded_proposal_v1.0.0.json
    ├── persona_review_v1.0.0.json
    ├── decision_aggregation_v1.0.0.json
    └── run_status_v1.0.0.json
```

## Purpose

These fixtures serve multiple purposes:

1. **Schema Contract Validation**: Ensure that schemas maintain their documented structure across code changes
2. **Backward Compatibility Testing**: Verify that old payloads still validate with current schema versions
3. **Regression Prevention**: Detect when fields are accidentally removed or renamed without a version bump
4. **Documentation**: Provide concrete examples of valid payloads for each schema version

## Schema Versioning Strategy

### Semantic Versioning

All schemas follow semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes (removed fields, renamed fields, changed types)
- **MINOR**: Backward-compatible additions (new optional fields)
- **PATCH**: Bug fixes and documentation updates (no schema changes)

### Version Bump Guidelines

#### When to Bump MAJOR Version (e.g., 1.0.0 → 2.0.0)

A MAJOR version bump is required when making breaking changes:

- Removing a required field
- Removing an optional field that's widely used
- Renaming any field
- Changing field type (e.g., string → object)
- Changing validation constraints that would reject previously valid data

**Process for MAJOR version bump:**

1. Create new schema class (or modify existing with breaking changes)
2. Register new version in `src/consensus_engine/schemas/registry.py`:
   ```python
   _registry.register(
       schema_name="SchemaName",
       version="2.0.0",
       schema_class=NewSchemaClass,
       description="Description of breaking changes",
       is_current=True,
       prompt_set_version="2.0.0",
       migration_notes="Migration guide: field X renamed to Y, field Z removed. "
                       "See docs/migrations/v2.0.0.md for details.",
   )
   ```
3. Mark old version as deprecated:
   ```python
   # Update v1.0.0 registration
   deprecated=True,
   migration_notes="Use version 2.0.0 instead"
   ```
4. Create new fixture file: `tests/fixtures/schemas/schema_name_v2.0.0.json`
5. Add backward compatibility test that expects old payloads to fail (or require migration)
6. Update integration tests to handle both versions if needed
7. Document migration path in `docs/migrations/v2.0.0.md`

#### When to Bump MINOR Version (e.g., 1.0.0 → 1.1.0)

A MINOR version bump is appropriate for backward-compatible additions:

- Adding new optional fields
- Adding new enum values (if existing code can handle unknown values)
- Relaxing validation constraints (making fields optional)

**Process for MINOR version bump:**

1. Modify schema class with new optional fields
2. Register new version:
   ```python
   _registry.register(
       schema_name="SchemaName",
       version="1.1.0",
       schema_class=SchemaClass,  # Same class, enhanced
       description="Added optional fields X, Y, Z",
       is_current=True,
       prompt_set_version="1.1.0",
   )
   ```
3. Create fixture with new fields: `tests/fixtures/schemas/schema_name_v1.1.0.json`
4. Add backward compatibility test verifying v1.0.0 payloads still validate
5. Ensure tests demonstrate new fields work correctly

#### When to Bump PATCH Version (e.g., 1.0.0 → 1.0.1)

PATCH versions are for bug fixes and documentation:

- Fixing typos in field descriptions
- Updating docstrings
- Fixing validation that was too strict or too lenient
- Documentation improvements

**Note**: For schemas, PATCH bumps are rare because most "fixes" are actually MINOR or MAJOR changes.

## Updating Fixtures

### When Schema Changes Are Made

1. **If you're making a MAJOR version change:**
   - Keep the old fixture (e.g., `schema_name_v1.0.0.json`)
   - Create a new fixture (e.g., `schema_name_v2.0.0.json`)
   - Update tests to verify old fixtures fail with new schema (expected behavior)

2. **If you're making a MINOR version change:**
   - Keep the old fixture
   - Create a new fixture with additional fields
   - Ensure backward compatibility tests still pass

3. **If you're NOT changing the schema:**
   - Don't touch the fixtures
   - Don't bump version numbers

### Fixture Content Guidelines

Each fixture should:

- **Be complete**: Include all required fields
- **Be realistic**: Use representative data, not minimal placeholders
- **Be diverse**: Show different value types (nested objects, arrays, etc.)
- **Be documented**: Include comments in JSON explaining complex fields (use a pre-processor if needed)

Example of a good fixture:

```json
{
  "problem_statement": "Realistic problem statement that shows typical length and content",
  "proposed_solution": "Detailed solution showing how this field is typically used",
  "assumptions": [
    "Real-world assumption 1",
    "Real-world assumption 2",
    "Shows that arrays have multiple items"
  ],
  "scope_non_goals": [
    "Clearly defined non-goal"
  ],
  "title": "Descriptive title",
  "summary": "Concise summary",
  "raw_idea": "Original idea text",
  "raw_expanded_proposal": "Full expanded text",
  "metadata": {
    "model": "gpt-5.1",
    "temperature": 0.7,
    "request_id": "test-request-123"
  }
}
```

## Test Coverage

### Schema Structure Tests

Located in `tests/unit/test_schema_registry.py`, class `TestSchemaStructureSnapshots`:

- `test_<schema_name>_schema_structure_v<version>`: Validates JSON schema structure
- `test_schema_field_removal_detection`: Ensures field removals are caught
- `test_schema_rename_detection`: Ensures field renames cause validation errors

### Backward Compatibility Tests

Located in `tests/unit/test_schema_registry.py`, class `TestBackwardCompatibility`:

- `test_load_<schema_name>_v<version>_fixture`: Loads and validates each versioned fixture
- `test_minor_version_compatibility_simulation`: Validates minor version changes
- `test_major_version_breaking_change_detection`: Documents major version behavior

### Running Schema Tests

```bash
# Run all schema registry tests
pytest tests/unit/test_schema_registry.py -v

# Run only snapshot tests
pytest tests/unit/test_schema_registry.py::TestSchemaStructureSnapshots -v

# Run only backward compatibility tests
pytest tests/unit/test_schema_registry.py::TestBackwardCompatibility -v
```

## Prompt Set Versioning

Prompt sets are versioned independently from schemas but follow the same principles:

- `PROMPT_SET_VERSION` in `src/consensus_engine/config/llm_steps.py`
- Incremented when prompt content changes significantly
- Tagged in metadata of all instruction payloads

### When to Bump Prompt Set Version

1. **MAJOR**: Complete rewrite of prompt structure
2. **MINOR**: Adding new prompts or significantly expanding existing ones
3. **PATCH**: Minor wording changes, typo fixes

Prompt set version is automatically included in all instruction payloads via `InstructionBuilder`.

## Testing Best Practices

### DO:

✅ Create fixtures for each schema version
✅ Test that old payloads validate with current schema (for MINOR changes)
✅ Test that old payloads fail with new schema (for MAJOR changes)
✅ Use realistic, representative data in fixtures
✅ Document breaking changes in migration_notes
✅ Keep fixtures in version control

### DON'T:

❌ Modify existing fixtures when schema changes
❌ Use minimal/empty fixtures that don't represent real usage
❌ Skip version bumps for breaking changes
❌ Delete old fixture files
❌ Manually edit version numbers in multiple places (use constants)

## Troubleshooting

### Test fails after schema change

1. **Did you bump the schema version?**
   - If yes, create new fixture and update tests
   - If no, you need to bump the version

2. **Is this a breaking change?**
   - If yes, bump MAJOR version
   - If no, bump MINOR version

3. **Are old fixtures failing?**
   - For MINOR changes: Fix the schema (backward compatibility is required)
   - For MAJOR changes: Expected behavior (update tests to verify this)

### Adding a new schema

1. Define schema in `src/consensus_engine/schemas/`
2. Register in `src/consensus_engine/schemas/registry.py`
3. Create fixture in `tests/fixtures/schemas/`
4. Add structure test in `tests/unit/test_schema_registry.py`
5. Add backward compatibility test

## Related Documentation

- **Schema Registry**: `src/consensus_engine/schemas/registry.py`
- **Schema Definitions**: `src/consensus_engine/schemas/`
- **Test Suite**: `tests/unit/test_schema_registry.py`
- **Instruction Builder**: `src/consensus_engine/config/instruction_builder.py`

## Questions?

For questions about schema versioning or test fixtures, see:

- Issue tracking: Check GitHub issues tagged `schema-versioning` or `testing`
- Code review: Schema changes require careful review and explicit version bumps
