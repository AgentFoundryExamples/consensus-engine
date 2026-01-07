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

This module implements GET /v1/runs and GET /v1/runs/{run_id} endpoints
for querying run history and retrieving individual run details.
"""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy.orm import Session

from consensus_engine.config.logging import get_logger
from consensus_engine.db.dependencies import get_db_session
from consensus_engine.db.models import RunStatus, RunType
from consensus_engine.db.repositories import RunRepository
from consensus_engine.schemas.requests import (
    PersonaReviewSummary,
    RunDetailResponse,
    RunListItemResponse,
    RunListResponse,
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
