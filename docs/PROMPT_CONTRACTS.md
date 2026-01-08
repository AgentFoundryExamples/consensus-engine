# Prompt Contracts and Schema Versioning Strategy

## Overview

This document provides comprehensive guidance for developers working with the Consensus Engine's schema registry, prompt contracts, and versioning system. Understanding these concepts is essential for evolving prompts and schemas safely while maintaining API compatibility and reproducibility.

## Table of Contents

- [Core Concepts](#core-concepts)
- [Schema Registry](#schema-registry)
- [Prompt Set Versioning](#prompt-set-versioning)
- [Version Bump Rules](#version-bump-rules)
- [Configuration and Overrides](#configuration-and-overrides)
- [API Versioning Strategy](#api-versioning-strategy)
- [Evolving Contracts Safely](#evolving-contracts-safely)
- [Testing Strategy](#testing-strategy)
- [Deployment and Migration](#deployment-and-migration)
- [Troubleshooting](#troubleshooting)

## Core Concepts

### What are Prompt Contracts?

A **prompt contract** is the combination of:
1. **Prompt Template**: The instruction text sent to the LLM
2. **Schema Definition**: The Pydantic model defining expected output structure
3. **Version Metadata**: Schema version and prompt set version identifiers

Together, these form a contract that defines what the LLM receives as input and what structured output is expected in return.

### Why Version Prompts and Schemas?

**Reproducibility**: Track exact prompt and schema versions used in each run for audit and debugging.

**Safe Evolution**: Change prompts or schemas without breaking existing clients or invalidating historical data.

**Compatibility Tracking**: Understand which prompt versions work with which schema versions.

**Rollback Capability**: Revert to previous versions if new versions cause issues.

**A/B Testing**: Compare performance across different prompt/schema combinations.

## Schema Registry

### Purpose

The Schema Registry (`src/consensus_engine/schemas/registry.py`) is the single source of truth for all schema definitions in the Consensus Engine. It provides:

- Centralized version management
- Schema-to-prompt version mapping
- Deprecation tracking
- Migration guidance

### Registered Schemas

Currently, four core schemas are registered at version `1.0.0`:

#### 1. ExpandedProposal
Output from the expansion step that transforms brief ideas into detailed proposals.

**Schema Version**: `1.0.0`  
**Prompt Set Version**: `1.0.0`

**Key Fields**:
- `problem_statement`: Clear problem articulation
- `proposed_solution`: Detailed solution approach
- `assumptions`: List of assumptions
- `scope_non_goals`: What's explicitly out of scope

#### 2. PersonaReview
Review from a specific persona (Architect, Critic, Optimist, SecurityGuardian, UserAdvocate).

**Schema Version**: `1.0.0`  
**Prompt Set Version**: `1.0.0`

**Key Fields**:
- `persona_name`: Name of reviewing persona
- `persona_id`: Stable identifier (e.g., 'architect')
- `confidence_score`: Confidence level [0.0, 1.0]
- `strengths`: Identified strengths
- `concerns`: Concerns with blocking flags
- `blocking_issues`: Critical issues that block approval

#### 3. DecisionAggregation
Aggregated decision from multiple persona reviews.

**Schema Version**: `1.0.0`  
**Prompt Set Version**: `1.0.0`

**Key Fields**:
- `overall_weighted_confidence`: Weighted confidence score
- `decision`: Final decision (approve/revise/reject)
- `detailed_score_breakdown`: Complete scoring details
- `minority_reports`: Dissenting opinions

#### 4. RunStatus
Enum representing run lifecycle state (queued, running, completed, failed).

**Schema Version**: `1.0.0`  
**Prompt Set Version**: `1.0.0`

### Using the Registry

```python
from consensus_engine.schemas import get_current_schema, get_schema_version

# Get current version (recommended for production)
schema_version = get_current_schema("ExpandedProposal")
print(f"Version: {schema_version.version}")
print(f"Prompt set: {schema_version.prompt_set_version}")

# Get specific version (for backward compatibility)
legacy_schema = get_schema_version("ExpandedProposal", "1.0.0")

# Serialize with version metadata
proposal_data = schema_version.to_dict(proposal)
# Result includes: {"_schema_version": "1.0.0", ...}

# Get JSON schema with version metadata
json_schema = schema_version.get_json_schema()
```

## Prompt Set Versioning

### What is a Prompt Set Version?

A **prompt set version** (e.g., `1.0.0`) identifies a specific collection of prompt templates used across all pipeline steps. It's defined in `src/consensus_engine/config/llm_steps.py`:

```python
# Current prompt set version
PROMPT_SET_VERSION = "1.0.0"
```

### How Prompt Versions are Used

**At Request Time**:
1. System retrieves current `PROMPT_SET_VERSION` from configuration
2. Prompt templates are built using instructions from `InstructionBuilder`
3. LLM receives prompts with metadata including prompt set version
4. Response includes `prompt_set_version` in metadata

**In Run Persistence**:
- Run record stores `prompt_set_version` in database
- Each step's metadata includes prompt version used
- API responses include version information for clients

**Example Metadata**:
```json
{
  "request_id": "550e8400-...",
  "step_name": "expand",
  "model": "gpt-5.1",
  "temperature": 0.7,
  "schema_version": "1.0.0",
  "prompt_set_version": "1.0.0",
  "elapsed_time": 2.3
}
```

### Deployment-Wide Versioning Model

**Important**: The Consensus Engine uses a **single deployment-wide versioning model**. This means:

- All API endpoints under `/v1` use the same schema and prompt versions
- A single `PROMPT_SET_VERSION` applies to all requests in a deployment
- All workers in a deployment use the same version
- Version changes roll out globally when deploying new code

**Implications**:
- ✅ Consistent behavior across all endpoints
- ✅ Simplified version tracking and debugging
- ✅ No version conflicts within a deployment
- ❌ Cannot run multiple prompt versions simultaneously
- ❌ Breaking changes require new API version (e.g., `/v2`)

## Version Bump Rules

### Semantic Versioning

Both schema versions and prompt set versions follow [Semantic Versioning](https://semver.org/):

**Format**: `MAJOR.MINOR.PATCH` (e.g., `1.2.3`)

**MAJOR** version (e.g., `1.0.0` → `2.0.0`):
- Breaking changes to schema structure
- Incompatible prompt changes
- Removal of required fields
- Changed field types or validation rules
- **Action Required**: New API version path (e.g., `/v2`)

**MINOR** version (e.g., `1.0.0` → `1.1.0`):
- Backward-compatible additions
- New optional fields
- Enhanced prompts that don't change output structure
- New features that don't break existing clients
- **Action Required**: Update version constant, test compatibility

**PATCH** version (e.g., `1.0.0` → `1.0.1`):
- Bug fixes in prompts
- Clarifications that don't change behavior
- Documentation improvements
- Minor validation adjustments
- **Action Required**: Update version constant, run tests

### When to Bump Schema Version

**Bump MAJOR (breaking change)**:
- Adding required fields to schema
- Removing fields from schema
- Changing field types (e.g., string → dict)
- Renaming fields
- Changing validation constraints that reject previously valid data

**Bump MINOR (compatible addition)**:
- Adding optional fields
- Making required fields optional
- Relaxing validation constraints
- Adding new enum values (if clients handle unknown values)

**Bump PATCH (non-functional change)**:
- Fixing typos in field descriptions
- Updating field documentation
- Clarifying validation error messages

### When to Bump Prompt Set Version

**Bump MAJOR (breaking change)**:
- Fundamentally changing output structure expected by prompt
- Removing or renaming personas
- Changing decision thresholds significantly
- Altering aggregation algorithm

**Bump MINOR (enhancement)**:
- Improving prompt clarity without changing output
- Adding context to prompts
- Enhancing instructions for better quality
- Tweaking temperature or model settings

**Bump PATCH (bug fix)**:
- Fixing typos in prompts
- Correcting minor instruction errors
- Clarifying ambiguous language

### Coordinating Schema and Prompt Versions

**Rule**: Schema version and prompt set version should increment together when:
- Prompt changes require schema changes
- Schema changes necessitate prompt updates
- Breaking changes affect both layers

**Example Scenario**:
```python
# Before: Version 1.0.0
class PersonaReview(BaseModel):
    persona_name: str
    confidence_score: float
    strengths: list[str]
    concerns: list[str]

# After: Version 2.0.0 (breaking change)
class PersonaReview(BaseModel):
    persona_name: str
    persona_id: str  # NEW REQUIRED FIELD
    confidence_score: float
    strengths: list[str]
    concerns: list[Concern]  # CHANGED TYPE

# Action: Bump both PROMPT_SET_VERSION and SCHEMA_VERSION to 2.0.0
# Update prompts to instruct LLM about new structure
# Create /v2 API endpoints
# Document migration path
```

## Configuration and Overrides

### Per-Step Model and Temperature Configuration

The Consensus Engine supports per-step configuration via environment variables:

**Expand Step**:
```bash
EXPAND_MODEL=gpt-5.1          # Model for expansion
EXPAND_TEMPERATURE=0.7         # Temperature for expansion (0.0-1.0)
```

**Review Step**:
```bash
REVIEW_MODEL=gpt-5.1          # Model for persona reviews
REVIEW_TEMPERATURE=0.2         # Temperature for reviews (0.0-1.0, lower = more deterministic)
```

**Aggregate Step**:
```bash
AGGREGATE_MODEL=gpt-5.1       # Model for aggregation (currently not used by LLM)
AGGREGATE_TEMPERATURE=0.0      # Temperature for aggregation
```

**Temperature Guidelines**:
- **0.0-0.3**: Deterministic, focused (recommended for reviews)
- **0.4-0.7**: Balanced creativity (recommended for expansion)
- **0.8-1.0**: High creativity (use with caution)

### Validation Limits Configuration

Configure input validation limits to prevent abuse and ensure quality:

```bash
# Maximum character length for idea text (default: 10000)
MAX_IDEA_LENGTH=10000

# Maximum character length for extra_context (default: 50000)
MAX_EXTRA_CONTEXT_LENGTH=50000

# Maximum character length for edited_proposal (default: 100000)
MAX_EDITED_PROPOSAL_LENGTH=100000

# Maximum character length for edit_notes (default: 10000)
MAX_EDIT_NOTES_LENGTH=10000
```

**Important**: These limits are enforced at the API boundary before LLM calls. Exceeding limits results in `422 Unprocessable Entity` errors.

### Where Versions Appear

**In Run Outputs** (GET `/v1/runs/{run_id}`):
```json
{
  "run_id": "...",
  "status": "completed",
  "schema_version": "1.0.0",
  "prompt_set_version": "1.0.0",
  "model": "gpt-5.1",
  "temperature": 0.7,
  ...
}
```

**In API Responses**:
```json
{
  "expanded_proposal": {
    "problem_statement": "...",
    "schema_version": "1.0.0",
    "prompt_set_version": "1.0.0"
  },
  "metadata": {
    "request_id": "...",
    "schema_version": "1.0.0",
    "prompt_set_version": "1.0.0"
  }
}
```

**In Logs**:
```json
{
  "level": "INFO",
  "message": "Job version metadata",
  "run_id": "...",
  "schema_version": "1.0.0",
  "prompt_set_version": "1.0.0",
  "lifecycle_event": "version_audit"
}
```

## API Versioning Strategy

### Current API Version: `/v1`

All API endpoints currently use the `/v1` prefix:
- `POST /v1/expand-idea`
- `POST /v1/review-idea`
- `POST /v1/full-review`
- `GET /v1/runs`
- `GET /v1/runs/{run_id}`

**What `/v1` Means**:
- Single global schema version for all endpoints
- Deployment-wide consistency in behavior
- All endpoints share the same `SCHEMA_VERSION` and `PROMPT_SET_VERSION`
- Breaking changes require incrementing to `/v2`

### When to Create a New API Version

**Create `/v2` when**:
- Breaking changes to request/response schemas
- Incompatible changes to core data structures
- Major changes to business logic that affect contracts
- Removal of deprecated endpoints or fields

**DO NOT create a new API version for**:
- Minor bug fixes
- Backward-compatible additions
- Performance improvements
- Internal refactoring
- Non-breaking field additions

### Process for Releasing Breaking Changes

**Step 1: Plan the Breaking Change**
- Document what's changing and why
- Identify affected endpoints and clients
- Define migration path for existing users
- Set deprecation timeline

**Step 2: Increment Versions**
```python
# In src/consensus_engine/config/llm_steps.py
PROMPT_SET_VERSION = "2.0.0"  # Increment MAJOR version
SCHEMA_VERSION = "2.0.0"      # Increment MAJOR version
```

**Step 3: Create New API Version**
```python
# Create new router with /v2 prefix
router = APIRouter(prefix="/v2", tags=["v2"])

# Register new schemas in registry
_registry.register(
    schema_name="ExpandedProposal",
    version="2.0.0",
    schema_class=ExpandedProposalV2,
    is_current=True,
    prompt_set_version="2.0.0",
)

# Mark old version as deprecated
_registry.register(
    schema_name="ExpandedProposal",
    version="1.0.0",
    schema_class=ExpandedProposal,
    is_current=False,
    deprecated=True,
    migration_notes="Use version 2.0.0. See MIGRATION.md for details.",
)
```

**Step 4: Document Migration**
- Add migration guide to documentation
- Update API documentation with deprecation notices
- Provide code examples for migration
- Set end-of-life date for old version

**Step 5: Deprecation Period**
- Continue supporting `/v1` endpoints (read-only if needed)
- Return deprecation headers in `/v1` responses:
  ```
  X-API-Deprecation: true
  X-API-Sunset: 2026-12-31
  X-API-Migration-Guide: https://<your-docs-domain>/migration-v2
  ```
- Log usage of deprecated endpoints for monitoring

**Step 6: Removal**
- After deprecation period, remove `/v1` endpoints
- Return `410 Gone` for removed endpoints
- Redirect users to migration documentation

## Evolving Contracts Safely

### Pre-Deployment Checklist

Before deploying new schema or prompt versions:

- [ ] **Version Bump**: Updated `SCHEMA_VERSION` and/or `PROMPT_SET_VERSION` appropriately
- [ ] **Registry Update**: New schema version registered in registry
- [ ] **Tests**: All tests pass with new version
- [ ] **Snapshot Tests**: Updated snapshot tests for new outputs (see below)
- [ ] **Migration Notes**: Documented breaking changes and migration path
- [ ] **Backward Compatibility**: Verified if claiming compatible change
- [ ] **Documentation**: Updated relevant documentation

### Snapshot Testing Strategy

Use snapshot tests to detect unintended changes to LLM outputs:

**1. Capture Baseline Snapshots**
```bash
# Generate snapshots for current version
pytest tests/integration/test_snapshots.py --snapshot-update
```

**2. Make Prompt Changes**
```python
# Update prompt in instruction builder
# Increment PROMPT_SET_VERSION if needed
```

**3. Compare Against Snapshots**
```bash
# Run tests without --snapshot-update
pytest tests/integration/test_snapshots.py

# Review diffs if tests fail
# Ensure changes are intentional
```

**4. Update Snapshots if Intended**
```bash
# After verifying changes are correct
pytest tests/integration/test_snapshots.py --snapshot-update
```

**What to Snapshot**:
- Full API response structures
- Schema validation results
- Aggregated decision outputs
- Persona review structures

**Snapshot Test Example**:
```python
def test_expand_output_snapshot(client, snapshot):
    """Ensure expand output structure remains stable."""
    response = client.post("/v1/expand-idea", json={
        "idea": "Build a REST API for user management"
    })
    
    # Remove non-deterministic fields
    data = response.json()
    data["metadata"].pop("request_id")
    data["metadata"].pop("elapsed_time")
    
    # Compare against snapshot
    snapshot.assert_match(data, "expand_output.json")
```

### Testing Version Changes Locally

**1. Set Up Test Environment**
```bash
# Use .env.test for isolated testing
cp .env.example .env.test
```

**2. Override Versions Locally**
```bash
# In .env.test
PROMPT_SET_VERSION=2.0.0-rc1  # Release candidate
SCHEMA_VERSION=2.0.0-rc1
```

**3. Run Local Tests**
```bash
# Run with test environment
ENV=testing pytest tests/

# Test specific scenarios
pytest tests/integration/test_full_review_endpoint.py -v
```

**4. Test with Emulator**
```bash
# Start Pub/Sub emulator
docker run -d -p 8085:8085 \
  gcr.io/google.com/cloudsdktool/cloud-sdk:emulators \
  gcloud beta emulators pubsub start --host-port=0.0.0.0:8085

# Configure environment
export PUBSUB_EMULATOR_HOST=localhost:8085

# Test full pipeline
python -m consensus_engine.workers.pipeline_worker &
curl -X POST http://localhost:8000/v1/full-review -d '{"idea": "Test"}'
```

## Deployment and Migration

### Deployment Best Practices

**Single Version Per Deployment**:
- All instances in a deployment use the same schema/prompt versions
- Configuration is set via environment variables at deploy time
- Rolling updates ensure gradual version transitions

**Blue-Green Deployments** (Recommended for Breaking Changes):
```
1. Deploy v2 to green environment
2. Test v2 thoroughly
3. Switch traffic from blue (v1) to green (v2)
4. Keep blue online for rollback
5. Retire blue after confidence period
```

**Canary Deployments** (For Non-Breaking Changes):
```
1. Deploy new version to 5% of instances
2. Monitor error rates, latency, quality metrics
3. Gradually increase to 25%, 50%, 100%
4. Rollback if issues detected
```

### Fallback Behavior for Historical Runs

**Scenario**: Querying runs created before version tracking was implemented.

**Behavior**:
- Runs with `schema_version = NULL` in database
- API returns `"unknown"` for version fields
- No errors or failures
- Clients should handle `"unknown"` gracefully

**Example Response**:
```json
{
  "run_id": "...",
  "status": "completed",
  "schema_version": "unknown",
  "prompt_set_version": "unknown",
  ...
}
```

**Client Handling**:
```python
schema_version = run_data.get("schema_version", "unknown")
if schema_version == "unknown":
    # Handle legacy data
    logger.warning(f"Run {run_id} has no version metadata")
    # Continue with degraded functionality or skip version checks
```

**Optional: Backfill Historical Data**
```sql
-- Only if version is certain
UPDATE runs
SET 
    schema_version = '1.0.0',
    prompt_set_version = '1.0.0'
WHERE 
    schema_version IS NULL
    AND created_at < '2026-01-08'  -- Before version tracking
    AND status = 'completed';
```

### Migration Checklist

**Before Migration**:
- [ ] Review all breaking changes
- [ ] Update documentation and migration guide
- [ ] Test new version thoroughly
- [ ] Prepare rollback plan
- [ ] Notify clients of upcoming changes

**During Migration**:
- [ ] Deploy new version to staging
- [ ] Run smoke tests
- [ ] Deploy to production (blue-green or canary)
- [ ] Monitor error rates, latency, logs
- [ ] Verify version metadata in new runs

**After Migration**:
- [ ] Confirm all systems using new version
- [ ] Monitor for version-related issues
- [ ] Update deprecation notices
- [ ] Plan for old version retirement

## Troubleshooting

### Issue: Schema Validation Errors After Deployment

**Symptoms**: 
- `SCHEMA_VALIDATION_ERROR` in API responses
- LLM responses not matching expected schema
- Field validation failures

**Possible Causes**:
- Prompt instructions unclear for new schema
- Schema validation too strict
- LLM model change affecting output
- Version mismatch between services

**Resolution**:
1. Check error details for specific field issues
   ```json
   {
     "code": "SCHEMA_VALIDATION_ERROR",
     "field_errors": [
       {"field": "confidence_score", "message": "value must be >= 0.0"}
     ]
   }
   ```
2. Review prompt changes - are instructions clear?
3. Test with previous version to isolate issue
4. Consider if schema validation is too restrictive
5. Rollback if critical issue

### Issue: Mixed Version Warnings in Logs

**Symptoms**:
```
Schema version consistency check failed
inconsistent_schemas: {"PersonaReview": ["1.0.0", "2.0.0"]}
```

**Possible Causes**:
- Rolling deployment in progress
- Different instances running different versions
- Cached old version in some services

**Resolution**:
1. Check all instances are running same version:
   ```bash
   # Cloud Run
   gcloud run services describe consensus-engine \
     --region us-central1 --format json | jq '.spec.template.metadata.labels'
   ```
2. Wait for rolling deployment to complete
3. Restart all services to clear caches
4. Verify environment variables consistent

### Issue: Historical Runs Returning "unknown" Versions

**Symptoms**: API returns `schema_version: "unknown"` for old runs

**Cause**: Run created before version tracking implemented

**Resolution**: This is expected behavior. Options:
1. **Accept "unknown"**: Handle gracefully in client code
2. **Backfill data**: Run SQL update (see Fallback Behavior section)
3. **Ignore old runs**: Filter by `created_at` in queries

### Issue: Breaking Change Deployed Without API Version Bump

**Symptoms**:
- Client errors after deployment
- Unexpected validation failures
- Incompatible data structures

**Immediate Actions**:
1. **Rollback deployment** to previous version
2. Notify affected clients
3. Investigate scope of impact

**Long-Term Fix**:
1. Increment to new API version (e.g., `/v2`)
2. Keep `/v1` compatible or deprecated
3. Provide migration path
4. Add tests to prevent future incidents

## Best Practices Summary

### DO

✅ Use `get_current_schema()` to get active schema version  
✅ Increment versions following semantic versioning rules  
✅ Document breaking changes in migration notes  
✅ Test schema changes with snapshot tests  
✅ Use per-step configuration for model/temperature tuning  
✅ Monitor version metadata in logs and metrics  
✅ Provide fallback behavior for historical data  
✅ Create new API versions for breaking changes  
✅ Use blue-green deployments for major version changes  

### DON'T

❌ Create schemas outside the registry  
❌ Modify schemas without version bumps  
❌ Deploy breaking changes without API version increment  
❌ Remove old schema versions until data migrated  
❌ Forget to update `prompt_set_version` with prompt changes  
❌ Use hardcoded version strings in application code  
❌ Skip snapshot tests before deploying  
❌ Deploy mixed versions across instances  

## Additional Resources

- [Schema Registry Documentation](SCHEMA_REGISTRY.md)
- [Schema Versioning and Validation](SCHEMA_VERSIONING.md)
- [Version Tracking and Audit](VERSION_TRACKING.md)
- [Worker Deployment Guide](WORKER_DEPLOYMENT.md)
- [Semantic Versioning Specification](https://semver.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

## Questions and Support

For questions about schema or prompt versioning:
1. Review this documentation and linked resources
2. Check existing issues in repository
3. Review recent version changes in git history
4. Consult with team lead for complex migrations

---

**Last Updated**: 2026-01-08  
**Current Schema Version**: 1.0.0  
**Current Prompt Set Version**: 1.0.0  
**Current API Version**: /v1
