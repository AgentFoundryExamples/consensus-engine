# Async-Ready Run and Step Persistence

This document describes the async-ready persistence layer for runs and step progress tracking introduced to support queue-based and worker-based execution patterns.

## Overview

The async persistence layer extends the `Run` model with queue-friendly fields and introduces a new `StepProgress` model for tracking individual pipeline steps. These changes enable:

- Queueing runs for asynchronous processing
- Priority-based execution ordering
- Fine-grained step-level progress tracking
- Retry management
- Detailed execution timelines

## Run Model Extensions

### New Status Values

The `RunStatus` enum now includes:
- `QUEUED` - Run has been created and is waiting for processing
- `RUNNING` - Run is currently being executed (existing status)
- `COMPLETED` - Run finished successfully (existing status)
- `FAILED` - Run encountered an error and terminated (existing status)

### New Fields

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `queued_at` | DateTime(TZ) | Yes | Timestamp when run was placed in queue |
| `started_at` | DateTime(TZ) | Yes | Timestamp when run execution began |
| `completed_at` | DateTime(TZ) | Yes | Timestamp when run finished (success or failure) |
| `retry_count` | Integer | No (default: 0) | Number of retry attempts for this run |
| `priority` | RunPriority | No (default: NORMAL) | Execution priority level |

### Priority Levels

The `RunPriority` enum defines:
- `NORMAL` - Standard priority (default)
- `HIGH` - Elevated priority for urgent runs

### Status Transition Rules

Valid status transitions:

```
QUEUED → RUNNING → COMPLETED
  ↓         ↓          
  ↓       FAILED
  ↓         ↓
  └─────────┘ (retry: increment retry_count, reset to QUEUED)
```

**Invariants:**
1. A run must start in `QUEUED` status
2. Only `QUEUED` runs can transition to `RUNNING`
3. Only `RUNNING` runs can transition to `COMPLETED` or `FAILED`
4. Retrying a `FAILED` run resets it to `QUEUED` and increments `retry_count`
5. Timestamps must be set atomically with status transitions:
   - Set `queued_at` when status becomes `QUEUED`
   - Set `started_at` when status becomes `RUNNING`
   - Set `completed_at` when status becomes `COMPLETED` or `FAILED`

### Backward Compatibility

For backward compatibility with synchronous execution:
- The `create_run()` method accepts a `status` parameter (default: `QUEUED`)
- Legacy code can pass `status=RunStatus.RUNNING` to bypass queueing
- All timestamp fields are nullable to support existing runs without these fields

## StepProgress Model

The `StepProgress` model tracks execution progress for individual pipeline steps.

### Schema

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | UUID | No | Primary key |
| `run_id` | UUID | No | Foreign key to runs.id (CASCADE DELETE) |
| `step_name` | String(100) | No | Canonical step name |
| `step_order` | Integer | No | Ordering index for deterministic sequencing |
| `status` | StepStatus | No | Current step status |
| `started_at` | DateTime(TZ) | Yes | When step processing began |
| `completed_at` | DateTime(TZ) | Yes | When step finished |
| `error_message` | Text | Yes | Error message if step failed |

**Unique Constraint:** `(run_id, step_name)`

### Step Names

Canonical step names in execution order:

| Order | Step Name | Description |
|-------|-----------|-------------|
| 0 | `expand` | Proposal expansion phase |
| 1 | `review_architect` | Architect persona review |
| 2 | `review_critic` | Critic persona review |
| 3 | `review_optimist` | Optimist persona review |
| 4 | `review_security` | SecurityGuardian persona review |
| 5 | `review_user_advocate` | UserAdvocate persona review |
| 6 | `aggregate_decision` | Decision aggregation phase |

**Validation:** Only these canonical names are accepted. Invalid names raise `ValueError`.

### Step Status Values

The `StepStatus` enum defines:
- `PENDING` - Step is queued but not started
- `RUNNING` - Step is currently executing
- `COMPLETED` - Step finished successfully
- `FAILED` - Step encountered an error

### Idempotent Updates

The `StepProgressRepository.upsert_step_progress()` method provides idempotent insert-or-update semantics:

1. If no record exists for `(run_id, step_name)`, creates a new one
2. If a record exists, updates it in-place
3. Calling multiple times with the same `run_id` and `step_name` never creates duplicates

**Example Usage:**

```python
# First call creates the record
StepProgressRepository.upsert_step_progress(
    session=session,
    run_id=run_id,
    step_name="expand",
    status=StepStatus.RUNNING,
    started_at=datetime.now(UTC)
)

# Second call updates the same record (idempotent)
StepProgressRepository.upsert_step_progress(
    session=session,
    run_id=run_id,
    step_name="expand",
    status=StepStatus.COMPLETED,
    completed_at=datetime.now(UTC)
)
```

### Edge Cases

#### Reprocessing Completed Runs

When reprocessing a run that already has step progress:
- Existing step records are updated, not duplicated
- Timestamps are only updated if new values are provided
- Workers must handle potential concurrent updates with row-level locking

#### Invalid Step Names

Invalid step names are rejected early:
```python
# Raises ValueError
StepProgressRepository.upsert_step_progress(
    session=session,
    run_id=run_id,
    step_name="invalid_step",  # Not in VALID_STEP_NAMES
    status=StepStatus.PENDING
)
```

#### Cascade Deletion

When a `Run` is deleted:
- All related `StepProgress` records are automatically deleted (CASCADE)
- No orphaned step records remain in the database

## Database Migration

### Migration: `77563d1e925b_add_async_run_and_step_progress`

**Upgrade Operations:**
1. Add columns to `runs` table:
   - `queued_at` (nullable DateTime)
   - `started_at` (nullable DateTime)
   - `completed_at` (nullable DateTime)
   - `retry_count` (Integer, default 0)
   - `priority` (String, default 'normal')
2. Create indexes:
   - `ix_runs_queued_at`
   - `ix_runs_started_at`
   - `ix_runs_completed_at`
   - `ix_runs_priority`
3. Add check constraint for `retry_count >= 0`
4. Create `step_progress` table with columns and constraints
5. Create indexes:
   - `ix_step_progress_run_id`
   - `ix_step_progress_status`

**Downgrade Operations:**
Reverses all upgrade operations in the correct order.

### Rollback Strategy

If async rollout needs to be postponed:

1. **Stop workers** - Ensure no active processing
2. **Apply downgrade migration**:
   ```bash
   alembic downgrade -1
   ```
3. **Verify data integrity** - Check that existing runs still function
4. **Revert application code** to previous version

**Data Loss:**
- `step_progress` table and all records are deleted
- New `runs` columns are dropped
- Existing runs retain `status`, `created_at`, `updated_at`

### Large-Scale Deployment Considerations

For databases with millions of rows:

1. **Indexes are created with `CONCURRENTLY` where supported**
   - PostgreSQL allows concurrent index creation
   - Reduces table lock duration

2. **Add columns with nullable defaults**
   - New columns are nullable to avoid full table rewrites
   - Defaults are applied at the application layer

3. **Monitor migration duration**
   - Test on staging with production-scale data
   - Plan maintenance window if necessary

4. **Phased rollout**
   - Deploy migration first
   - Update application code second
   - Enable async workers last

## API Response Schema Updates

### RunListItemResponse

New fields exposed:
- `queued_at` (nullable ISO timestamp)
- `started_at` (nullable ISO timestamp)
- `completed_at` (nullable ISO timestamp)
- `retry_count` (integer, default 0)
- `priority` (string: "normal" | "high")
- `status` now includes "queued"

### RunDetailResponse

All `RunListItemResponse` fields plus:
- `step_progress` (array of `StepProgressSummary`)

### StepProgressSummary

New schema for step progress in responses:
```json
{
  "step_name": "expand",
  "step_order": 0,
  "status": "completed",
  "started_at": "2026-01-08T10:00:00Z",
  "completed_at": "2026-01-08T10:00:15Z",
  "error_message": null
}
```

## Repository API

### RunRepository

**Updated Method:**
```python
@staticmethod
def create_run(
    session: Session,
    run_id: uuid.UUID,
    input_idea: str,
    extra_context: dict[str, Any] | None,
    run_type: RunType,
    model: str,
    temperature: float,
    parameters_json: dict[str, Any],
    parent_run_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    priority: RunPriority = RunPriority.NORMAL,  # NEW
    status: RunStatus = RunStatus.QUEUED,  # CHANGED default
) -> Run
```

### StepProgressRepository

**New Methods:**

```python
@staticmethod
def upsert_step_progress(
    session: Session,
    run_id: uuid.UUID,
    step_name: str,
    status: StepStatus,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    error_message: str | None = None,
) -> StepProgress
```

```python
@staticmethod
def get_run_steps(
    session: Session,
    run_id: uuid.UUID
) -> list[StepProgress]
```

```python
@staticmethod
def get_step_order(step_name: str) -> int
```

## Future Work

### Worker Implementation

The persistence layer is ready for:
- Celery/RQ task queues
- Cloud Tasks / Cloud Scheduler
- Custom worker pools

Workers should:
1. Poll for `QUEUED` runs ordered by `priority DESC, queued_at ASC`
2. Atomically update status to `RUNNING` with `started_at`
3. Upsert step progress as pipeline executes
4. Set final status and `completed_at` on completion

### Monitoring & Observability

Recommended queries:

**Queue depth:**
```sql
SELECT priority, COUNT(*) 
FROM runs 
WHERE status = 'queued' 
GROUP BY priority;
```

**Average processing time:**
```sql
SELECT AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds
FROM runs
WHERE status = 'completed' AND started_at IS NOT NULL AND completed_at IS NOT NULL;
```

**Failed step analysis:**
```sql
SELECT step_name, COUNT(*) as failure_count
FROM step_progress
WHERE status = 'failed'
GROUP BY step_name
ORDER BY failure_count DESC;
```

### Retry Logic

Implement exponential backoff:
1. Check `retry_count` before retrying
2. Apply delay based on retry count (e.g., `2^retry_count` minutes)
3. Cap max retries (e.g., 5 attempts)
4. Increment `retry_count` and reset to `QUEUED`

### Concurrency Control

For multi-worker scenarios:
- Use PostgreSQL row-level locks (`SELECT FOR UPDATE`)
- Implement optimistic locking with version columns if needed
- Ensure idempotent step updates handle concurrent workers

## Testing

### Unit Tests

Located in `tests/unit/test_models.py`:
- `TestRunModel.test_run_with_async_fields`
- `TestRunModel.test_run_priority_enum`
- `TestStepProgressModel.*`

### Integration Tests

Located in `tests/integration/test_db.py`:
- `TestStepProgressRepository.test_upsert_step_progress_create`
- `TestStepProgressRepository.test_upsert_step_progress_update`
- `TestStepProgressRepository.test_get_run_steps`
- `TestStepProgressRepository.test_step_progress_cascade_delete`

Run tests:
```bash
pytest tests/unit/test_models.py -v
pytest tests/integration/test_db.py::TestStepProgressRepository -v
```
