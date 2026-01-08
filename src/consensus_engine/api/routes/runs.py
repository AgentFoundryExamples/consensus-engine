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

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from consensus_engine.config import Settings, get_settings
from consensus_engine.config.logging import get_logger
from consensus_engine.db.dependencies import get_db_session
from consensus_engine.db.models import RunStatus, RunType
from consensus_engine.db.repositories import (
    DecisionRepository,
    PersonaReviewRepository,
    ProposalVersionRepository,
    RunRepository,
)
from consensus_engine.exceptions import ConsensusEngineError
from consensus_engine.schemas.proposal import ExpandedProposal
from consensus_engine.schemas.requests import (
    CreateRevisionRequest,
    CreateRevisionResponse,
    PersonaReviewSummary,
    RunDetailResponse,
    RunDiffResponse,
    RunListItemResponse,
    RunListResponse,
)
from consensus_engine.services.aggregator import aggregate_persona_reviews
from consensus_engine.services.diff import compute_run_diff
from consensus_engine.services.expand import expand_with_edits
from consensus_engine.services.orchestrator import (
    determine_personas_to_rerun,
    review_with_selective_personas,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["runs"])


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
            run_type=run.run_type.value,
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

    # Build response
    response = RunDetailResponse(
        run_id=str(run.id),
        created_at=run.created_at.isoformat(),
        updated_at=run.updated_at.isoformat(),
        status=run.status.value,
        run_type=run.run_type.value,
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
        proposal=proposal_json,
        persona_reviews=persona_reviews,
        decision=decision_json,
    )

    logger.info(
        "Returning run detail",
        extra={
            "run_id": run_id,
            "status": run.status.value,
            "has_proposal": proposal_json is not None,
            "persona_reviews_count": len(persona_reviews),
            "has_decision": decision_json is not None,
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
    response_model=CreateRevisionResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Create a revision run from an existing run",
    description=(
        "Creates a revision run that re-expands the proposal with edits and selectively "
        "re-runs personas based on confidence scores and blocking issues. Returns metadata "
        "about which personas were rerun vs reused."
    ),
)
async def create_revision(
    run_id: str,
    request: CreateRevisionRequest,
    settings: Settings = Depends(get_settings),
    db_session: Session = Depends(get_db_session),
) -> CreateRevisionResponse:
    """Create a revision run from an existing run.

    This endpoint:
    1. Validates the parent run exists and completed successfully
    2. Re-expands the proposal with edits
    3. Determines which personas to re-run based on criteria
    4. Re-runs selected personas, reuses others
    5. Aggregates decision across mixed reviews
    6. Persists new Run with all data

    Args:
        run_id: UUID of the parent run
        request: CreateRevisionRequest with edit inputs
        settings: Application settings
        db_session: Database session

    Returns:
        CreateRevisionResponse with new run metadata

    Raises:
        HTTPException: 400 for invalid input, 404 for missing run, 409 for failed parent
    """
    logger.info(
        f"Creating revision for run {run_id}",
        extra={"parent_run_id": run_id},
    )

    # Pre-generate new run_id and start timing
    new_run_id = uuid.uuid4()
    start_time = time.time()

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

        # Retrieve parent run with all relations
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

        # Validate parent has required data
        if not parent_run.proposal_version:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Parent run missing proposal version data",
            )

        if not parent_run.persona_reviews:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Parent run missing persona reviews data",
            )

        # Extract parent data
        parent_proposal_json = parent_run.proposal_version.expanded_proposal_json
        parent_proposal = ExpandedProposal(**parent_proposal_json)

        # Extract parent reviews with security_concerns_present from DB
        parent_reviews_data: list[tuple[str, dict[str, Any], bool]] = [
            (review.persona_id, review.review_json, review.security_concerns_present)
            for review in parent_run.persona_reviews
        ]

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
        # Step 1: Create new Run record
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
        )

        logger.info(
            f"Created new revision run {new_run_id}",
            extra={"run_id": str(new_run_id), "parent_run_id": run_id},
        )

        # Flush to ensure run is persisted before potential failures
        db_session.flush()

        # Step 2: Expand with edits
        try:
            new_proposal, expand_metadata, diff_json = expand_with_edits(
                parent_proposal=parent_proposal,
                edited_proposal=request.edited_proposal,
                edit_notes=request.edit_notes,
                settings=settings,
            )
        except ConsensusEngineError as e:
            # Mark run as failed and let outer exception handler rollback
            RunRepository.update_run_status(db_session, new_run_id, RunStatus.FAILED)
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to expand proposal with edits: {str(e)}",
            ) from e

        # Step 3: Persist new proposal version
        persona_template_version = "v1"  # TODO: Make configurable
        proposal_version = ProposalVersionRepository.create_proposal_version(
            session=db_session,
            run_id=new_run_id,
            expanded_proposal=new_proposal,
            persona_template_version=persona_template_version,
            proposal_diff_json=diff_json,
            edit_notes=request.edit_notes,
        )

        logger.info(
            f"Created proposal version for revision run {new_run_id}",
            extra={
                "run_id": str(new_run_id),
                "proposal_version_id": str(proposal_version.id),
            },
        )

        # Step 4: Determine personas to rerun
        personas_to_rerun = determine_personas_to_rerun(parent_reviews_data)

        # Step 5: Review with selective personas
        try:
            persona_reviews, orchestration_metadata = review_with_selective_personas(
                expanded_proposal=new_proposal,
                parent_persona_reviews=parent_reviews_data,
                personas_to_rerun=personas_to_rerun,
                settings=settings,
            )
        except (ConsensusEngineError, ValueError) as e:
            # Mark run as failed and let outer exception handler rollback
            RunRepository.update_run_status(db_session, new_run_id, RunStatus.FAILED)
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to review proposal with personas: {str(e)}",
            ) from e

        # Step 6: Persist persona reviews
        for review in persona_reviews:
            prompt_params = {
                "model": settings.review_model,
                "temperature": settings.review_temperature,
                "persona_template_version": persona_template_version,
                "reused": review.internal_metadata.get("reused", False)
                if review.internal_metadata
                else False,
            }

            PersonaReviewRepository.create_persona_review(
                session=db_session,
                run_id=new_run_id,
                persona_review=review,
                prompt_parameters_json=prompt_params,
            )

        logger.info(
            f"Created {len(persona_reviews)} persona reviews for revision run {new_run_id}",
            extra={"run_id": str(new_run_id), "review_count": len(persona_reviews)},
        )

        # Step 7: Aggregate decision
        decision_aggregation = aggregate_persona_reviews(persona_reviews)

        # Step 8: Persist decision
        decision = DecisionRepository.create_decision(
            session=db_session,
            run_id=new_run_id,
            decision_aggregation=decision_aggregation,
        )

        logger.info(
            f"Created decision for revision run {new_run_id}",
            extra={
                "run_id": str(new_run_id),
                "decision_id": str(decision.id),
                "decision": decision_aggregation.decision.value,
                "confidence": decision_aggregation.overall_weighted_confidence,
            },
        )

        # Step 9: Update run status to completed
        RunRepository.update_run_status(
            session=db_session,
            run_id=new_run_id,
            status=RunStatus.COMPLETED,
            overall_weighted_confidence=decision_aggregation.overall_weighted_confidence,
            decision_label=decision_aggregation.decision.value,
        )

        # Commit transaction
        db_session.commit()

        elapsed_time = time.time() - start_time

        # Build list of personas reused
        personas_reused = [
            pid for pid, _ in parent_reviews_data if pid not in personas_to_rerun
        ]

        logger.info(
            f"Successfully created revision run {new_run_id} in {elapsed_time:.2f}s",
            extra={
                "run_id": str(new_run_id),
                "parent_run_id": run_id,
                "elapsed_time": elapsed_time,
                "personas_rerun": personas_to_rerun,
                "personas_reused": personas_reused,
            },
        )

        return CreateRevisionResponse(
            run_id=str(new_run_id),
            parent_run_id=run_id,
            status=RunStatus.COMPLETED.value,
            created_at=new_run.created_at.isoformat(),
            personas_rerun=personas_to_rerun,
            personas_reused=personas_reused,
            message=(
                f"Revision created successfully. "
                f"Re-ran {len(personas_to_rerun)} persona(s), "
                f"reused {len(personas_reused)} review(s)."
            ),
        )

    except Exception as e:
        # Catch all errors (including HTTPExceptions from validation)
        db_session.rollback()
        logger.error(
            f"Error creating revision for run {run_id}, rolling back transaction",
            extra={"parent_run_id": run_id},
            exc_info=True,
        )
        # Re-raise HTTPException as-is, wrap others
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create revision: {str(e)}",
        ) from e
