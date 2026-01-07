"""Full review endpoint router.

This module implements the POST /v1/full-review endpoint that orchestrates
expand → multi-persona review → aggregate decision flow synchronously.
"""

import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from consensus_engine.config import Settings, get_settings
from consensus_engine.config.logging import get_logger
from consensus_engine.exceptions import (
    ConsensusEngineError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from consensus_engine.schemas.proposal import ExpandedProposal, IdeaInput
from consensus_engine.schemas.requests import (
    ExpandIdeaResponse,
    FullReviewErrorResponse,
    FullReviewRequest,
    FullReviewResponse,
)
from consensus_engine.services import expand_idea
from consensus_engine.services.aggregator import aggregate_persona_reviews
from consensus_engine.services.orchestrator import review_with_all_personas

logger = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["full-review"])


def _map_exception_to_status_code(exc: ConsensusEngineError) -> int:
    """Map domain exception to HTTP status code.

    Args:
        exc: ConsensusEngineError instance

    Returns:
        HTTP status code
    """
    if isinstance(exc, LLMAuthenticationError):
        return status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, LLMRateLimitError | LLMTimeoutError):
        return status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        return status.HTTP_500_INTERNAL_SERVER_ERROR


def _build_expand_response(
    proposal: ExpandedProposal, metadata: dict[str, Any]
) -> ExpandIdeaResponse:
    """Build ExpandIdeaResponse from ExpandedProposal and metadata.

    Args:
        proposal: ExpandedProposal instance
        metadata: Metadata dictionary from expand service

    Returns:
        ExpandIdeaResponse instance
    """
    return ExpandIdeaResponse(
        problem_statement=proposal.problem_statement,
        proposed_solution=proposal.proposed_solution,
        assumptions=proposal.assumptions,
        scope_non_goals=proposal.scope_non_goals,
        title=proposal.title,
        summary=proposal.summary,
        raw_idea=proposal.raw_idea,
        raw_expanded_proposal=proposal.raw_expanded_proposal,
        metadata=metadata,
    )


@router.post(
    "/full-review",
    response_model=FullReviewResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully expanded and reviewed idea with all personas",
            "content": {
                "application/json": {
                    "example": {
                        "expanded_proposal": {
                            "problem_statement": "Clear problem statement",
                            "proposed_solution": "Detailed solution approach",
                            "assumptions": ["Assumption 1", "Assumption 2"],
                            "scope_non_goals": ["Out of scope 1"],
                            "metadata": {
                                "request_id": "expand-123",
                                "model": "gpt-5.1",
                                "temperature": 0.7,
                                "elapsed_time": 2.5,
                            },
                        },
                        "persona_reviews": [
                            {
                                "persona_id": "architect",
                                "persona_name": "Architect",
                                "confidence_score": 0.85,
                                "strengths": ["Good architecture"],
                                "concerns": [
                                    {"text": "Missing error handling", "is_blocking": False}
                                ],
                                "recommendations": ["Add error handling"],
                                "blocking_issues": [],
                                "estimated_effort": "2-3 weeks",
                                "dependency_risks": [],
                            }
                        ],
                        "decision": {
                            "overall_weighted_confidence": 0.82,
                            "weighted_confidence": 0.82,
                            "decision": "approve",
                            "detailed_score_breakdown": {
                                "weights": {"architect": 0.25, "critic": 0.25},
                                "individual_scores": {"architect": 0.85, "critic": 0.80},
                                "weighted_contributions": {"architect": 0.2125, "critic": 0.20},
                                "formula": "weighted_confidence = sum(weight_i * score_i)",
                            },
                            "minority_reports": None,
                        },
                        "run_id": "run-123",
                        "elapsed_time": 15.2,
                    }
                }
            },
        },
        422: {
            "description": "Validation error - invalid request format or sentence count",
            "content": {
                "application/json": {
                    "example": {
                        "code": "VALIDATION_ERROR",
                        "message": "Request validation failed",
                        "failed_step": "validation",
                        "run_id": "run-123",
                        "details": [
                            {
                                "type": "value_error",
                                "loc": ["body", "idea"],
                                "msg": "Idea must contain at most 10 sentences (found 15)",
                            }
                        ],
                    }
                }
            },
        },
        500: {
            "description": "Internal server error - expansion, review, or aggregation failure",
            "content": {
                "application/json": {
                    "example": {
                        "code": "LLM_SERVICE_ERROR",
                        "message": "Failed to process request",
                        "failed_step": "review",
                        "run_id": "run-123",
                        "partial_results": {
                            "expanded_proposal": {
                                "problem_statement": "...",
                                "proposed_solution": "...",
                            }
                        },
                        "details": {"retryable": False},
                    }
                }
            },
        },
    },
    summary="Expand and review an idea with all five personas",
    description=(
        "Accepts a brief idea (1-10 sentences) with optional extra context, "
        "expands it into a comprehensive proposal, reviews it with all five personas "
        "(Architect, Critic, Optimist, SecurityGuardian, UserAdvocate), and aggregates "
        "a final decision. Returns the expanded proposal, all persona reviews, and "
        "aggregated decision with telemetry. Errors include failed_step and any partial "
        "results. All personas must succeed for the endpoint to return success."
    ),
)
async def full_review_endpoint(
    request_obj: Request,
    review_request: FullReviewRequest,
    settings: Settings = Depends(get_settings),
) -> FullReviewResponse:
    """Expand and review an idea with all five personas.

    This endpoint orchestrates the following steps synchronously:
    1. Expand the idea into a detailed proposal
    2. Review the proposal with all five personas (Architect, Critic, Optimist,
       SecurityGuardian, UserAdvocate) in sequence
    3. Aggregate all persona reviews into a final decision

    Args:
        request_obj: FastAPI request object for accessing state
        review_request: Validated request containing idea and optional extra_context
        settings: Application settings injected via dependency

    Returns:
        FullReviewResponse with expanded proposal, all persona reviews, and final decision

    Raises:
        JSONResponse: For validation errors (422) or service errors (500/503)
    """
    # Generate unique run_id for this orchestration
    run_id = str(uuid.uuid4())
    start_time = time.time()

    # Get request_id from middleware if available
    request_id = getattr(request_obj.state, "request_id", "unknown")

    logger.info(
        "Starting full-review orchestration",
        extra={
            "run_id": run_id,
            "request_id": request_id,
            "has_extra_context": review_request.extra_context is not None,
        },
    )

    # Convert extra_context to string if it's a dict
    extra_context_str: str | None = None
    if review_request.extra_context is not None:
        if isinstance(review_request.extra_context, dict):
            extra_context_str = json.dumps(review_request.extra_context, indent=2)
        else:
            extra_context_str = review_request.extra_context

    # Create IdeaInput for service
    idea_input = IdeaInput(idea=review_request.idea, extra_context=extra_context_str)

    # Track partial results and step statuses
    expanded_proposal: ExpandedProposal | None = None
    expand_metadata: dict[str, Any] | None = None
    persona_reviews: list | None = None
    orchestration_metadata: dict[str, Any] | None = None

    # Step 1: Expand the idea
    try:
        logger.info(
            "Step 1: Expanding idea",
            extra={"run_id": run_id, "step": "expand"},
        )

        expanded_proposal, expand_metadata = expand_idea(idea_input, settings)

        logger.info(
            "Step 1 completed: Idea expanded successfully",
            extra={
                "run_id": run_id,
                "step": "expand",
                "expand_request_id": expand_metadata.get("request_id"),
                "expand_elapsed_time": expand_metadata.get("elapsed_time"),
            },
        )

    except ConsensusEngineError as e:
        elapsed_time = time.time() - start_time
        logger.error(
            "Step 1 failed: Expansion error",
            extra={
                "run_id": run_id,
                "step": "expand",
                "error_code": e.code,
                "elapsed_time": elapsed_time,
            },
        )

        # Return structured error with failed_step and no partial results
        error_response = FullReviewErrorResponse(
            code=e.code,
            message=e.message,
            failed_step="expand",
            run_id=run_id,
            partial_results=None,
            details=e.details,
        )

        status_code = _map_exception_to_status_code(e)

        return JSONResponse(
            status_code=status_code,
            content=error_response.model_dump(),
        )

    except Exception:
        elapsed_time = time.time() - start_time
        logger.error(
            "Step 1 failed: Unexpected error",
            extra={"run_id": run_id, "step": "expand", "elapsed_time": elapsed_time},
            exc_info=True,
        )

        error_response = FullReviewErrorResponse(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred during expansion",
            failed_step="expand",
            run_id=run_id,
            partial_results=None,
            details={},
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.model_dump(),
        )

    # Step 2: Review with all personas
    try:
        logger.info(
            "Step 2: Reviewing proposal with all personas",
            extra={"run_id": run_id, "step": "review"},
        )

        persona_reviews, orchestration_metadata = review_with_all_personas(
            expanded_proposal,
            settings,
        )

        logger.info(
            "Step 2 completed: All persona reviews completed successfully",
            extra={
                "run_id": run_id,
                "step": "review",
                "persona_count": len(persona_reviews),
                "orchestration_elapsed_time": orchestration_metadata.get("elapsed_time"),
            },
        )

    except ConsensusEngineError as e:
        elapsed_time = time.time() - start_time
        logger.error(
            "Step 2 failed: Review orchestration error",
            extra={
                "run_id": run_id,
                "step": "review",
                "error_code": e.code,
                "elapsed_time": elapsed_time,
            },
        )

        # Return structured error with failed_step and partial results (expanded proposal)
        partial_results_data = None
        if expanded_proposal:
            expand_response = _build_expand_response(expanded_proposal, expand_metadata or {})
            partial_results_data = {"expanded_proposal": expand_response.model_dump()}

        error_response = FullReviewErrorResponse(
            code=e.code,
            message=e.message,
            failed_step="review",
            run_id=run_id,
            partial_results=partial_results_data,
            details=e.details,
        )

        status_code = _map_exception_to_status_code(e)

        return JSONResponse(
            status_code=status_code,
            content=error_response.model_dump(),
        )

    except Exception:
        elapsed_time = time.time() - start_time
        logger.error(
            "Step 2 failed: Unexpected error",
            extra={"run_id": run_id, "step": "review", "elapsed_time": elapsed_time},
            exc_info=True,
        )

        # Include partial results (expanded proposal)
        partial_results_data = None
        if expanded_proposal:
            expand_response = _build_expand_response(expanded_proposal, expand_metadata or {})
            partial_results_data = {"expanded_proposal": expand_response.model_dump()}

        error_response = FullReviewErrorResponse(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred during multi-persona review",
            failed_step="review",
            run_id=run_id,
            partial_results=partial_results_data,
            details={},
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.model_dump(),
        )

    # Step 3: Aggregate decision
    try:
        logger.info(
            "Step 3: Aggregating decision from all persona reviews",
            extra={"run_id": run_id, "step": "aggregate"},
        )

        decision = aggregate_persona_reviews(persona_reviews)

        logger.info(
            "Step 3 completed: Decision aggregated successfully",
            extra={
                "run_id": run_id,
                "step": "aggregate",
                "decision": decision.decision.value,
                "weighted_confidence": decision.weighted_confidence,
            },
        )

    except ConsensusEngineError as e:
        elapsed_time = time.time() - start_time
        logger.error(
            "Step 3 failed: Aggregation error",
            extra={
                "run_id": run_id,
                "step": "aggregate",
                "error_code": e.code,
                "elapsed_time": elapsed_time,
            },
        )

        # Include partial results (expanded proposal and reviews)
        partial_results_data: dict[str, Any] | None = None
        if expanded_proposal and persona_reviews:
            expand_response = _build_expand_response(expanded_proposal, expand_metadata or {})
            partial_results_data = {
                "expanded_proposal": expand_response.model_dump(),
                "persona_reviews": [review.model_dump() for review in persona_reviews],
            }

        error_response = FullReviewErrorResponse(
            code=e.code,
            message=e.message,
            failed_step="aggregate",
            run_id=run_id,
            partial_results=partial_results_data,
            details=e.details,
        )

        status_code = _map_exception_to_status_code(e)

        return JSONResponse(
            status_code=status_code,
            content=error_response.model_dump(),
        )

    except Exception:
        elapsed_time = time.time() - start_time
        logger.error(
            "Step 3 failed: Unexpected error during aggregation",
            extra={"run_id": run_id, "step": "aggregate", "elapsed_time": elapsed_time},
            exc_info=True,
        )

        # Include partial results (expanded proposal and reviews)
        partial_results_data: dict[str, Any] | None = None
        if expanded_proposal and persona_reviews:
            expand_response = _build_expand_response(expanded_proposal, expand_metadata or {})
            partial_results_data = {
                "expanded_proposal": expand_response.model_dump(),
                "persona_reviews": [review.model_dump() for review in persona_reviews],
            }

        error_response = FullReviewErrorResponse(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred during decision aggregation",
            failed_step="aggregate",
            run_id=run_id,
            partial_results=partial_results_data,
            details={},
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.model_dump(),
        )

    # Build successful response
    elapsed_time = time.time() - start_time

    # Build ExpandIdeaResponse from expanded_proposal
    expand_response = _build_expand_response(expanded_proposal, expand_metadata or {})

    response = FullReviewResponse(
        expanded_proposal=expand_response,
        persona_reviews=persona_reviews,
        decision=decision,
        run_id=run_id,
        elapsed_time=elapsed_time,
    )

    logger.info(
        "Full-review orchestration completed successfully",
        extra={
            "run_id": run_id,
            "request_id": request_id,
            "elapsed_time": elapsed_time,
            "expand_elapsed_time": expand_metadata.get("elapsed_time") if expand_metadata else None,
            "review_elapsed_time": orchestration_metadata.get("elapsed_time")
            if orchestration_metadata
            else None,
            "decision": decision.decision.value,
            "weighted_confidence": decision.weighted_confidence,
            "persona_count": len(persona_reviews),
        },
    )

    return response
