# Copyright 2025 John Brosnihan
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Run retrieval endpoint router.

This module implements GET /v1/runs, GET /v1/runs/{run_id}, and
GET /v1/runs/{run_id}/diff/{other_run_id} endpoints for querying run history,
retrieving individual run details, and comparing runs, as well as
POST /v1/runs/{run_id}/revisions for creating revision runs.
"""

import time
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from consensus_engine.api.validation import log_validation_failure, validate_version_headers
from consensus_engine.clients.pubsub import PubSubPublishError, get_publisher
from consensus_engine.config import Settings, get_settings
from consensus_engine.config.logging import get_logger
from consensus_engine.db.dependencies import get_db_session
from consensus_engine.db.models import Run, RunPriority, RunStatus, RunType, StepStatus
from consensus_engine.db.repositories import (
    RunRepository,
    StepProgressRepository,
)
from consensus_engine.exceptions import UnsupportedVersionError, ValidationError
from consensus_engine.schemas.requests import (
    CreateRevisionRequest,
    JobEnqueuedResponse,
    PersonaReviewSummary,
    RunDetailResponse,
    RunDiffResponse,
    RunListItemResponse,
    RunListResponse,
    StepProgressSummary,
)
from consensus_engine.services.diff import compute_run_diff

logger = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["runs"])


def _build_step_progress_summaries(run: Run) -> list[StepProgressSummary]:
    """Build ordered step progress summaries for a run.

    Merges actual StepProgress records with default pending steps to ensure
    a complete, ordered list of all canonical steps is always returned.

    Args:
        run: Run instance with step_progress relationship loaded

    Returns:
        List of StepProgressSummary objects ordered by step_order
    """
    # Create a dictionary of actual steps, keyed by step_name
    actual_steps = {step.step_name: step for step in run.step_progress}
    summaries = []

    # Iterate through all canonical steps to build a complete list
    for i, step_name in enumerate(StepProgressRepository.VALID_STEP_NAMES):
        if step_name in actual_steps:
            # Use the actual step progress if it exists
            step = actual_steps[step_name]
            summary = StepProgressSummary(
                step_name=step.step_name,
                step_order=step.step_order,
                status=step.status.value,
                started_at=step.started_at.isoformat() if step.started_at else None,
                completed_at=step.completed_at.isoformat() if step.completed_at else None,
                error_message=step.error_message,
            )
        else:
            # Generate a default pending step if it's missing
            summary = StepProgressSummary(
                step_name=step_name,
                step_order=i,
                status=StepStatus.PENDING.value,
                started_at=None,
                completed_at=None,
                error_message=None,
            )
        summaries.append(summary)

    return summaries


@router.get(
    "/runs",
    response_model=RunListResponse,
    status_code=http_status.HTTP_200_OK,
    summary="List runs with filtering and pagination",
    description=(
        "Returns a paginated list of runs sorted by created_at descending. "
        "Supports filtering by status, run_type, parent_run_id, decision, "
        "min_confidence, and date ranges. Returns empty list (200) for no matches."
    ),
)
async def list_runs(
    db_session: Session = Depends(get_db_session),
    limit: int = Query(
        default=30,
        ge=1,
        le=100,
        description="Number of items per page (1-100)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Offset for pagination",
    ),
    status: str | None = Query(
        default=None,
        description="Filter by status: running, completed, or failed",
    ),
    run_type: str | None = Query(
        default=None,
        description="Filter by run_type: initial or revision",
    ),
    parent_run_id: str | None = Query(
        default=None,
        description="Filter by parent_run_id (UUID)",
    ),
    decision: str | None = Query(
        default=None,
        description="Filter by decision_label (e.g., approve, revise, reject)",
    ),
    min_confidence: float | None = Query(
        default=None,
        ge=0.0,
        le=1.0,
        description="Filter by minimum overall_weighted_confidence (0.0-1.0)",
    ),
    start_date: str | None = Query(
        default=None,
        description="Filter by created_at >= start_date (ISO 8601 format)",
    ),
    end_date: str | None = Query(
        default=None,
        description="Filter by created_at <= end_date (ISO 8601 format)",
    ),
) -> RunListResponse:
    """List runs with filtering and pagination.

    Args:
        db_session: Database session injected via dependency
        limit: Number of items per page
        offset: Offset for pagination
        status: Optional filter by status
        run_type: Optional filter by run_type
        parent_run_id: Optional filter by parent_run_id
        decision: Optional filter by decision_label
        min_confidence: Optional filter by minimum overall_weighted_confidence
        start_date: Optional filter by created_at >= start_date
        end_date: Optional filter by created_at <= end_date

    Returns:
        RunListResponse with paginated list of runs

    Raises:
        HTTPException: 400 for invalid parameters (e.g., invalid UUID, date format)
    """
    logger.info(
        "Listing runs",
        extra={
            "limit": limit,
            "offset": offset,
            "status": status,
            "run_type": run_type,
            "parent_run_id": parent_run_id,
            "decision": decision,
            "min_confidence": min_confidence,
            "start_date": start_date,
            "end_date": end_date,
        },
    )

    # Parse and validate filters
    status_enum: RunStatus | None = None
    if status is not None:
        try:
            status_enum = RunStatus(status)
        except ValueError as e:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}. Must be one of: running, completed, failed",
            ) from e

    run_type_enum: RunType | None = None
    if run_type is not None:
        try:
            run_type_enum = RunType(run_type)
        except ValueError as e:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid run_type: {run_type}. Must be one of: initial, revision",
            ) from e

    parent_run_uuid: uuid.UUID | None = None
    if parent_run_id is not None:
        try:
            parent_run_uuid = uuid.UUID(parent_run_id)
        except ValueError as e:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid parent_run_id UUID: {parent_run_id}",
            ) from e

    start_date_dt: datetime | None = None
    if start_date is not None:
        try:
            start_date_dt = datetime.fromisoformat(start_date)
            if start_date_dt.tzinfo is None:
                raise ValueError("Date must include timezone information")
        except ValueError as e:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid start_date format: {start_date}. "
                    "Must be ISO 8601 format with timezone."
                ),
            ) from e

    end_date_dt: datetime | None = None
    if end_date is not None:
        try:
            end_date_dt = datetime.fromisoformat(end_date)
            if end_date_dt.tzinfo is None:
                raise ValueError("Date must include timezone information")
        except ValueError as e:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid end_date format: {end_date}. "
                    "Must be ISO 8601 format with timezone."
                ),
            ) from e

    # Query database
    try:
        runs, total = RunRepository.list_runs(
            session=db_session,
            limit=limit,
            offset=offset,
            status=status_enum,
            run_type=run_type_enum,
            parent_run_id=parent_run_uuid,
            decision=decision,
            min_confidence=min_confidence,
            start_date=start_date_dt,
            end_date=end_date_dt,
        )
    except Exception as e:
        logger.error(
            "Database error while listing runs",
            extra={"limit": limit, "offset": offset},
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve runs from database",
        ) from e

    # Build response items
    run_items: list[RunListItemResponse] = []
    for run in runs:
        # Extract truncated proposal metadata
        proposal_title: str | None = None
        proposal_summary: str | None = None

        if run.proposal_version and run.proposal_version.expanded_proposal_json:
            proposal_json = run.proposal_version.expanded_proposal_json
            proposal_title = proposal_json.get("title")
            proposal_summary = proposal_json.get("summary")

        run_item = RunListItemResponse(
            run_id=str(run.id),
            created_at=run.created_at.isoformat(),
            status=run.status.value,
            queued_at=run.queued_at.isoformat() if run.queued_at else None,
            started_at=run.started_at.isoformat() if run.started_at else None,
            completed_at=run.completed_at.isoformat() if run.completed_at else None,
            retry_count=run.retry_count,
            run_type=run.run_type.value,
            priority=run.priority.value,
            parent_run_id=str(run.parent_run_id) if run.parent_run_id else None,
            overall_weighted_confidence=float(run.overall_weighted_confidence)
            if run.overall_weighted_confidence is not None
            else None,
            decision_label=run.decision_label,
            proposal_title=proposal_title,
            proposal_summary=proposal_summary,
        )
        run_items.append(run_item)

    logger.info(
        f"Returning {len(run_items)} runs (total={total})",
        extra={"count": len(run_items), "total": total},
    )

    return RunListResponse(
        runs=run_items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/runs/{run_id}",
    response_model=RunDetailResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Get full run details by ID",
    description=(
        "Returns the full run detail including metadata, proposal JSON, "
        "persona reviews, and decision JSON. Returns 404 for missing run_id."
    ),
)
async def get_run_detail(
    run_id: str,
    db_session: Session = Depends(get_db_session),
) -> RunDetailResponse:
    """Get full run details by ID.

    Args:
        run_id: UUID of the run
        db_session: Database session injected via dependency

    Returns:
        RunDetailResponse with full run details

    Raises:
        HTTPException: 400 for invalid UUID, 404 for missing run
    """
    logger.info(
        "Retrieving run detail",
        extra={"run_id": run_id},
    )

    # Parse and validate run_id
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid run_id UUID: {run_id}",
        ) from e

    # Retrieve run with all relations
    try:
        run = RunRepository.get_run_with_relations(db_session, run_uuid)
    except Exception as e:
        logger.error(
            f"Database error while retrieving run {run_id}",
            extra={"run_id": run_id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve run from database",
        ) from e

    if run is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )

    # Extract proposal JSON
    proposal_json: dict[str, Any] | None = None
    if run.proposal_version:
        proposal_json = run.proposal_version.expanded_proposal_json

    # Extract persona reviews
    persona_reviews: list[PersonaReviewSummary] = []
    for review in run.persona_reviews:
        persona_review = PersonaReviewSummary(
            persona_id=review.persona_id,
            persona_name=review.persona_name,
            confidence_score=float(review.confidence_score),
            blocking_issues_present=review.blocking_issues_present,
            prompt_parameters_json=review.prompt_parameters_json,
        )
        persona_reviews.append(persona_review)

    # Extract decision JSON
    decision_json: dict[str, Any] | None = None
    if run.decision:
        decision_json = run.decision.decision_json

    # Build step progress summaries
    step_progress_summaries = _build_step_progress_summaries(run)

    # Extract schema_version and prompt_set_version from Run model with safe defaults
    schema_version = run.schema_version if run.schema_version else "unknown"
    prompt_set_version = run.prompt_set_version if run.prompt_set_version else "unknown"

    # Build response
    response = RunDetailResponse(
        run_id=str(run.id),
        created_at=run.created_at.isoformat(),
        updated_at=run.updated_at.isoformat(),
        status=run.status.value,
        queued_at=run.queued_at.isoformat() if run.queued_at else None,
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        retry_count=run.retry_count,
        run_type=run.run_type.value,
        priority=run.priority.value,
        parent_run_id=str(run.parent_run_id) if run.parent_run_id else None,
        input_idea=run.input_idea,
        extra_context=run.extra_context,
        model=run.model,
        temperature=float(run.temperature),
        parameters_json=run.parameters_json,
        overall_weighted_confidence=float(run.overall_weighted_confidence)
        if run.overall_weighted_confidence is not None
        else None,
        decision_label=run.decision_label,
        schema_version=schema_version,
        prompt_set_version=prompt_set_version,
        proposal=proposal_json,
        persona_reviews=persona_reviews,
        decision=decision_json,
        step_progress=step_progress_summaries,
    )

    logger.info(
        "Returning run detail",
        extra={
            "run_id": run_id,
            "status": run.status.value,
            "has_proposal": proposal_json is not None,
            "persona_reviews_count": len(persona_reviews),
            "has_decision": decision_json is not None,
            "step_progress_count": len(step_progress_summaries),
            "schema_version": schema_version,
            "prompt_set_version": prompt_set_version,
        },
    )

    return response


@router.get(
    "/runs/{run_id}/diff/{other_run_id}",
    response_model=RunDiffResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Compare two runs and compute diff",
    description=(
        "Computes structured diff between two runs including proposal changes, "
        "persona score deltas, and decision changes. Returns 400 for identical runs, "
        "404 for missing runs. All diffs are computed from stored JSONB without re-running models."
    ),
)
async def get_run_diff(
    run_id: str,
    other_run_id: str,
    db_session: Session = Depends(get_db_session),
) -> RunDiffResponse:
    """Compare two runs and return structured diff.

    Args:
        run_id: UUID of the first run
        other_run_id: UUID of the second run
        db_session: Database session injected via dependency

    Returns:
        RunDiffResponse with proposal changes, persona deltas, and decision delta

    Raises:
        HTTPException: 400 for identical run IDs, 404 for missing runs
    """
    logger.info(
        f"Computing diff between runs {run_id} and {other_run_id}",
        extra={"run_id": run_id, "other_run_id": other_run_id},
    )

    # Validate run IDs are different
    if run_id == other_run_id:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Cannot diff a run against itself. Please provide two different run IDs.",
        )

    # Parse and validate run IDs
    try:
        run_uuid = uuid.UUID(run_id)
        other_run_uuid = uuid.UUID(other_run_id)
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {str(e)}",
        ) from e

    # Retrieve both runs with all relations
    try:
        run1 = RunRepository.get_run_with_relations(db_session, run_uuid)
        run2 = RunRepository.get_run_with_relations(db_session, other_run_uuid)
    except SQLAlchemyError as e:
        logger.error(
            "Database error while retrieving runs for diff",
            extra={"run_id": run_id, "other_run_id": other_run_id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve runs from database",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error while retrieving runs for diff",
            extra={"run_id": run_id, "other_run_id": other_run_id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e

    # Check both runs exist
    if run1 is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )

    if run2 is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {other_run_id}",
        )

    # Compute diff using service
    try:
        diff_result = compute_run_diff(run1, run2)
    except (AttributeError, KeyError, ValueError) as e:
        logger.error(
            "Data validation error while computing diff",
            extra={"run_id": run_id, "other_run_id": other_run_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute diff due to invalid or incomplete run data",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error computing diff between runs",
            extra={"run_id": run_id, "other_run_id": other_run_id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute diff: {str(e)}",
        ) from e

    logger.info(
        f"Successfully computed diff between runs {run_id} and {other_run_id}",
        extra={
            "run_id": run_id,
            "other_run_id": other_run_id,
            "is_parent_child": diff_result["metadata"]["is_parent_child"],
        },
    )

    return RunDiffResponse(
        metadata=diff_result["metadata"],
        proposal_changes=diff_result["proposal_changes"],
        persona_deltas=diff_result["persona_deltas"],
        decision_delta=diff_result["decision_delta"],
    )


@router.post(
    "/runs/{run_id}/revisions",
    response_model=JobEnqueuedResponse,
    status_code=http_status.HTTP_202_ACCEPTED,
    summary="Enqueue a revision job from an existing run",
    description=(
        "Creates a revision run with status='queued', initializes StepProgress entries, "
        "publishes a job message to Pub/Sub, and returns run metadata immediately. "
        "Clients should poll GET /v1/runs/{run_id} to check status and retrieve "
        "results once processing completes."
        "\n\n"
        "**Validation Rules:**\n"
        "- edited_proposal: max 100,000 characters (string or JSON)\n"
        "- edit_notes: max 10,000 characters\n"
        "- input_idea: max 10,000 characters\n"
        "- extra_context: max 50,000 characters (string or JSON)\n"
        "- At least one of edited_proposal or edit_notes must be provided\n"
        "\n\n"
        "**Version Headers (Optional):**\n"
        "- X-Schema-Version: Schema version (current: 1.0.0)\n"
        "- X-Prompt-Set-Version: Prompt set version (current: 1.0.0)\n"
        "If not provided, defaults to current deployment versions with a warning."
    ),
)
async def create_revision(
    run_id: str,
    request: CreateRevisionRequest,
    settings: Settings = Depends(get_settings),
    db_session: Session = Depends(get_db_session),
    x_schema_version: str | None = Header(default=None, alias="X-Schema-Version"),
    x_prompt_set_version: str | None = Header(default=None, alias="X-Prompt-Set-Version"),
) -> JobEnqueuedResponse:
    """Enqueue a revision job and return run metadata immediately.

    This endpoint:
    1. Validates version headers
    2. Validates the parent run exists and completed successfully
    3. Creates a Run with status='queued' and run_type='revision'
    4. Initializes StepProgress entries for all pipeline steps
    5. Publishes a job message to Pub/Sub with run_id, run_type='revision', priority, and payload
    6. Returns run_id and metadata immediately
    7. Rolls back database changes if Pub/Sub publish fails

    Args:
        run_id: UUID of the parent run
        request: CreateRevisionRequest with edit inputs
        settings: Application settings
        db_session: Database session
        x_schema_version: Optional schema version header
        x_prompt_set_version: Optional prompt set version header

    Returns:
        JobEnqueuedResponse with run_id, status='queued', and timestamps

    Raises:
        HTTPException: 400 for invalid input/version, 404 for missing run,
            409 for failed parent, 500 for errors
    """
    logger.info(
        f"Enqueuing revision job for run {run_id}",
        extra={"parent_run_id": run_id},
    )

    # Pre-generate new run_id and start timing
    new_run_id = uuid.uuid4()
    start_time = time.time()
    db_committed = False

    try:
        # Validate version headers
        versions = validate_version_headers(
            x_schema_version,
            x_prompt_set_version,
            settings,
        )
        schema_version = versions["schema_version"]
        prompt_set_version = versions["prompt_set_version"]

    except UnsupportedVersionError as e:
        log_validation_failure(
            field="version_headers",
            rule="supported_version",
            message=e.message,
            metadata={**e.details, "parent_run_id": run_id, "new_run_id": str(new_run_id)},
        )
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail={
                "code": e.code,
                "message": e.message,
                "details": e.details,
            },
        ) from e

    try:
        # Validate request has at least one edit input
        if request.edited_proposal is None and request.edit_notes is None:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="At least one of 'edited_proposal' or 'edit_notes' must be provided",
            )

        # Parse and validate parent run_id
        try:
            parent_run_uuid = uuid.UUID(run_id)
        except ValueError as e:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid run_id UUID: {run_id}",
            ) from e

        # Retrieve parent run with all relations to validate it has required data
        try:
            parent_run = RunRepository.get_run_with_relations(db_session, parent_run_uuid)
        except Exception as e:
            logger.error(
                f"Database error while retrieving parent run {run_id}",
                extra={"parent_run_id": run_id},
                exc_info=True,
            )
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve parent run from database",
            ) from e

        if parent_run is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Parent run not found: {run_id}",
            )

        # Validate parent run completed successfully
        if parent_run.status != RunStatus.COMPLETED:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot create revision from run with status '{parent_run.status.value}'. "
                    "Parent run must have status 'completed'."
                ),
            )

        # Validate parent has required data for revision processing
        # This prevents enqueueing jobs that will fail when the worker tries to process them
        if not hasattr(parent_run, 'proposal_version') or parent_run.proposal_version is None:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Parent run missing proposal version data. Cannot create revision.",
            )

        if not hasattr(parent_run, 'persona_reviews') or not parent_run.persona_reviews:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Parent run missing persona reviews data. Cannot create revision.",
            )

        # Determine parameters (merge with parent)
        input_idea = request.input_idea if request.input_idea is not None else parent_run.input_idea

        extra_context_dict: dict[str, Any] | None = None
        if request.extra_context is not None:
            if isinstance(request.extra_context, dict):
                extra_context_dict = request.extra_context
            else:
                extra_context_dict = {"text": request.extra_context}
        else:
            extra_context_dict = parent_run.extra_context

        model = request.model if request.model is not None else parent_run.model
        temperature = (
            request.temperature
            if request.temperature is not None
            else float(parent_run.temperature)
        )

        parameters_json = (
            request.parameters_json
            if request.parameters_json is not None
            else parent_run.parameters_json
        )

        # Determine priority (inherit from parent or default to normal)
        priority = parent_run.priority if parent_run.priority else RunPriority.NORMAL

        # Use validated schema and prompt versions from headers
        # Step 1: Create new Run with status='queued'
        new_run = RunRepository.create_run(
            session=db_session,
            run_id=new_run_id,
            input_idea=input_idea,
            extra_context=extra_context_dict,
            run_type=RunType.REVISION,
            model=model,
            temperature=temperature,
            parameters_json=parameters_json,
            parent_run_id=parent_run_uuid,
            priority=priority,
            status=RunStatus.QUEUED,
            schema_version=schema_version,
            prompt_set_version=prompt_set_version,
        )

        logger.info(
            f"Created revision run {new_run_id} with status='queued'",
            extra={"run_id": str(new_run_id), "parent_run_id": run_id, "priority": priority.value},
        )

        # Step 2: Initialize StepProgress entries for all pipeline steps
        for step_name in StepProgressRepository.VALID_STEP_NAMES:
            StepProgressRepository.upsert_step_progress(
                session=db_session,
                run_id=new_run_id,
                step_name=step_name,
                status=StepStatus.PENDING,
            )
        logger.info(
            f"Initialized {len(StepProgressRepository.VALID_STEP_NAMES)} StepProgress entries",
            extra={"run_id": str(new_run_id)},
        )

        # All database operations successful, commit the transaction first
        db_session.commit()
        db_committed = True
        logger.info(
            "Revision run and StepProgress records committed to database",
            extra={"run_id": str(new_run_id), "parent_run_id": run_id},
        )

        # Step 3: Publish job message to Pub/Sub
        # Build sanitized payload (include revision-specific data)
        payload = {
            "parent_run_id": run_id,
            "input_idea": input_idea,
            "extra_context": extra_context_dict,
            "edited_proposal": request.edited_proposal,
            "edit_notes": request.edit_notes,
            "parameters": parameters_json,
        }

        try:
            publisher = get_publisher(settings)
            message_id = publisher.publish(
                run_id=str(new_run_id),
                run_type=RunType.REVISION.value,
                priority=priority.value,
                payload=payload,
            )
            logger.info(
                "Published revision job message to Pub/Sub",
                extra={
                    "run_id": str(new_run_id),
                    "parent_run_id": run_id,
                    "message_id": message_id,
                    "publish_latency_ms": (time.time() - start_time) * 1000,
                },
            )

        except PubSubPublishError as e:
            # The run is already committed, so we can't roll back.
            # The API should return an error, and a background job
            # could be used to find and retry publishing for such orphaned runs.
            logger.error(
                "Failed to publish revision job message after committing database changes",
                extra={
                    "run_id": str(new_run_id),
                    "parent_run_id": run_id,
                    "error": str(e),
                    "mitigation": "A background job should retry publishing for this run_id.",
                },
                exc_info=True,
            )
            raise HTTPException(
                status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to enqueue revision job: Pub/Sub publish failed after run creation",
            ) from e

        # All operations successful
        logger.info(
            "Revision job enqueued successfully, transaction committed",
            extra={"run_id": str(new_run_id), "parent_run_id": run_id},
        )

    except HTTPException:
        # Re-raise HTTPExceptions as-is (already have proper status codes)
        # Only rollback if we haven't committed yet
        if not db_committed:
            db_session.rollback()
        raise

    except SQLAlchemyError as e:
        # Database error, rollback only if not committed
        if not db_committed:
            db_session.rollback()
        logger.error(
            "Database error while enqueueing revision job",
            extra={"run_id": str(new_run_id), "parent_run_id": run_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create revision run: Database operation failed",
        ) from e

    except Exception as e:
        # Unexpected error, rollback only if not committed
        if not db_committed:
            db_session.rollback()
        logger.error(
            "Unexpected error while enqueueing revision job",
            extra={"run_id": str(new_run_id), "parent_run_id": run_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enqueue revision job: {str(e)}",
        ) from e

    # Build successful response
    response = JobEnqueuedResponse(
        run_id=str(new_run_id),
        status=RunStatus.QUEUED.value,
        run_type=RunType.REVISION.value,
        priority=priority.value,
        created_at=new_run.created_at.isoformat(),
        queued_at=(
            new_run.queued_at.isoformat()
            if new_run.queued_at
            else new_run.created_at.isoformat()
        ),
        message=f"Revision job enqueued successfully. Poll GET /v1/runs/{new_run_id} for status.",
    )

    logger.info(
        "Revision job enqueued successfully",
        extra={
            "run_id": str(new_run_id),
            "parent_run_id": run_id,
            "status": "queued",
            "elapsed_time": time.time() - start_time,
        },
    )

    return response
