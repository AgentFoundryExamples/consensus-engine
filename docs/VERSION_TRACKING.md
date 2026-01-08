# Version Tracking and Audit

## Overview

The Consensus Engine implements comprehensive version tracking for schema and prompt versions across all runs and pipeline steps. This enables full audit trails for reproducibility, cross-version comparisons, and debugging.

## Key Features

### Run-Level Version Tracking

Every run records:
- **`schema_version`**: The schema version used for data structures (ExpandedProposal, PersonaReview, DecisionAggregation)
- **`prompt_set_version`**: The prompt template version used for LLM interactions

These fields are:
- Nullable for backward compatibility with historical data
- Automatically populated when runs are created
- Exposed through API responses for external audit systems
- Logged in structured format for observability

### Step-Level Metadata

Each pipeline step (expand, review_*, aggregate_decision) records metadata including:
- Schema version
- Prompt set version
- Model identifier (e.g., "gpt-5.1")
- Temperature setting
- Max retries configuration

This metadata is stored in the `step_metadata` JSONB column of the `step_progress` table.

## Database Schema

### Run Model Additions

```python
class Run(Base):
    # ... existing fields ...
    schema_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_set_version: Mapped[str | None] = mapped_column(Text, nullable=True)
```

### StepProgress Model Additions

```python
class StepProgress(Base):
    # ... existing fields ...
    step_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
```

## API Exposure

### GET /v1/runs/{run_id}

Returns run details including version information:

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "schema_version": "1.0.0",
  "prompt_set_version": "1.0.0",
  "model": "gpt-5.1",
  "temperature": 0.7,
  ...
}
```

For historical runs without version data, the API returns `"unknown"` as a safe default.

## Version Consistency Checking

The pipeline worker validates version consistency across all outputs in a run:

1. Collects schema versions from:
   - Proposal (ExpandedProposal)
   - Persona reviews (PersonaReview)
   - Decision (DecisionAggregation)

2. Verifies:
   - All schemas use the same version within a run
   - All prompt_set_versions are consistent

3. Emits warnings for mixed versions:
   - Logged with `schema_validation_error` level
   - Does not fail the run (graceful degradation)
   - Includes full context for debugging

## Structured Logging

All run-related log entries include version tags:

```json
{
  "timestamp": "2026-01-08T08:06:28.236Z",
  "level": "INFO",
  "message": "Job version metadata",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "schema_version": "1.0.0",
  "prompt_set_version": "1.0.0",
  "lifecycle_event": "version_audit"
}
```

## Migration

A database migration adds the new columns with nullable constraints:

```bash
# Apply migration
alembic upgrade head
```

Migration file: `migrations/versions/add_version_tracking_to_runs.py`

## Backward Compatibility

### Historical Data

Runs created before version tracking:
- Have `schema_version` and `prompt_set_version` set to `NULL` in database
- Return `"unknown"` through API (converted at response layer)
- Do not break clients or queries
- Can be backfilled if needed

### No Breaking Changes

- All version fields are nullable
- Existing code continues to work without modifications
- API responses include default values for missing data
- No required database backfills

## Usage Examples

### Creating a Run with Versions

```python
from consensus_engine.db.repositories import RunRepository
from consensus_engine.config.settings import get_settings

settings = get_settings()
llm_config = settings.get_llm_steps_config()

run = RunRepository.create_run(
    session=session,
    run_id=run_id,
    input_idea="Test idea",
    extra_context=None,
    run_type=RunType.INITIAL,
    model="gpt-5.1",
    temperature=0.7,
    parameters_json={},
    schema_version="1.0.0",  # Default schema version
    prompt_set_version=llm_config.prompt_set_version,  # From config
)
```

### Querying Run Versions

```python
# Via repository
run = RunRepository.get_run_with_relations(session, run_id)
print(f"Schema: {run.schema_version}, Prompts: {run.prompt_set_version}")

# Via API
response = requests.get(f"https://api.example.com/v1/runs/{run_id}")
data = response.json()
print(f"Schema: {data['schema_version']}, Prompts: {data['prompt_set_version']}")
```

### Adding Step Metadata

```python
from consensus_engine.db.repositories import StepProgressRepository

step_metadata = {
    "schema_version": "1.0.0",
    "prompt_set_version": "1.0.0",
    "model": "gpt-5.1",
    "temperature": 0.7,
    "max_retries": 3,
}

StepProgressRepository.upsert_step_progress(
    session=session,
    run_id=run_id,
    step_name="expand",
    status=StepStatus.RUNNING,
    step_metadata=step_metadata,
)
```

## Audit Use Cases

### 1. Reproducibility

Track exact versions used in a successful run to reproduce results:

```sql
SELECT 
    r.id,
    r.schema_version,
    r.prompt_set_version,
    r.model,
    r.temperature,
    r.decision_label,
    r.overall_weighted_confidence
FROM runs r
WHERE r.status = 'completed'
  AND r.decision_label = 'approve'
ORDER BY r.created_at DESC
LIMIT 10;
```

### 2. Cross-Version Comparison

Compare results across different schema or prompt versions:

```sql
SELECT 
    schema_version,
    prompt_set_version,
    COUNT(*) as run_count,
    AVG(overall_weighted_confidence) as avg_confidence,
    COUNT(CASE WHEN decision_label = 'approve' THEN 1 END) as approvals
FROM runs
WHERE status = 'completed'
GROUP BY schema_version, prompt_set_version
ORDER BY schema_version DESC, prompt_set_version DESC;
```

### 3. Debugging Version Mismatches

Identify runs with mixed versions:

```sql
-- This requires custom logic as version consistency is checked at runtime
-- Check pipeline worker logs for "mixed_prompt_versions" warnings
```

## Best Practices

1. **Always Set Versions on Run Creation**
   - Extract from `llm_config.prompt_set_version`
   - Use consistent schema version (default: "1.0.0")

2. **Include Versions in Logs**
   - Add `schema_version` and `prompt_set_version` to log context
   - Use structured logging for easy querying

3. **Monitor Version Distribution**
   - Track version usage in production
   - Alert on unexpected version changes
   - Correlate version changes with outcome quality

4. **Version Increment Process**
   - Update `PROMPT_SET_VERSION` in `llm_steps.py`
   - Update schema version constants as needed
   - Run version consistency checks in CI/CD

## Configuration

Version settings are managed in:

- **`src/consensus_engine/config/llm_steps.py`**: Defines `PROMPT_SET_VERSION`
- **`src/consensus_engine/config/settings.py`**: Exposes `persona_template_version`
- **Environment Variables**: Override via `PERSONA_TEMPLATE_VERSION` if needed

## Testing

Version tracking is covered by:

- **Unit Tests**: `tests/unit/test_version_tracking.py`
- **Integration Tests**: `tests/integration/test_version_tracking_api.py`
- **Model Tests**: Verify nullable constraints work correctly

Run tests:

```bash
pytest tests/unit/test_version_tracking.py -v
pytest tests/integration/test_version_tracking_api.py -v
```

## Troubleshooting

### Version Shows as "unknown"

**Cause**: Historical run created before version tracking was implemented.

**Solution**: This is expected behavior. The run predates version tracking. If needed, you can backfill versions:

```sql
UPDATE runs 
SET 
    schema_version = '1.0.0',
    prompt_set_version = '1.0.0'
WHERE schema_version IS NULL;
```

### Mixed Version Warnings

**Cause**: Different pipeline steps used different versions (rare, indicates deployment issue).

**Solution**: Check deployment rollout logs. Ensure all workers are running the same version.

### Migration Fails

**Cause**: Database permissions or constraint violations.

**Solution**: Ensure user has ALTER TABLE permissions. Verify no custom constraints conflict with nullable columns.

## Future Enhancements

Potential improvements for version tracking:

1. **Schema Evolution Tracking**: Record schema migrations and transformations
2. **Prompt Diff Visualization**: Show changes between prompt versions
3. **Version Rollback**: Quickly revert to previous version for new runs
4. **A/B Testing Support**: Run experiments with different versions in parallel
5. **Version Lifecycle Management**: Mark versions as deprecated, stable, experimental
