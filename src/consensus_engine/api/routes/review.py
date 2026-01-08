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
"""Review idea endpoint router.

This module implements the POST /v1/review-idea endpoint that orchestrates
expand → review → aggregate decision flow synchronously.
"""

import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import JSONResponse

from consensus_engine.config import Settings, get_settings
from consensus_engine.config.logging import get_logger
from consensus_engine.exceptions import (
    ConsensusEngineError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    UnsupportedVersionError,
    ValidationError,
)
from consensus_engine.api.validation import log_validation_failure, validate_version_headers
from consensus_engine.schemas.proposal import ExpandedProposal, IdeaInput
from consensus_engine.schemas.requests import (
    ExpandIdeaResponse,
    ReviewIdeaErrorResponse,
    ReviewIdeaRequest,
    ReviewIdeaResponse,
)
from consensus_engine.schemas.review import (
    DecisionAggregation,
    DecisionEnum,
    PersonaReview,
    PersonaScoreBreakdown,
)
from consensus_engine.services import expand_idea, review_proposal

logger = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["review"])


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
    proposal: ExpandedProposal, metadata: dict[str, Any], schema_version: str, prompt_set_version: str
) -> ExpandIdeaResponse:
    """Build ExpandIdeaResponse from ExpandedProposal and metadata.

    Args:
        proposal: ExpandedProposal instance
        metadata: Metadata dictionary from expand service
        schema_version: Validated schema version
        prompt_set_version: Validated prompt set version

    Returns:
        ExpandIdeaResponse instance
    """
    # Override metadata with validated versions
    metadata["schema_version"] = schema_version
    metadata["prompt_set_version"] = prompt_set_version

    return ExpandIdeaResponse(
        problem_statement=proposal.problem_statement,
        proposed_solution=proposal.proposed_solution,
        assumptions=proposal.assumptions,
        scope_non_goals=proposal.scope_non_goals,
        title=proposal.title,
        summary=proposal.summary,
        raw_idea=proposal.raw_idea,
        raw_expanded_proposal=proposal.raw_expanded_proposal,
        schema_version=schema_version,
        prompt_set_version=prompt_set_version,
        metadata=metadata,
    )


def _create_single_persona_decision(
    persona_review: PersonaReview, persona_name: str
) -> DecisionAggregation:
    """Create a DecisionAggregation for a single persona review.

    For a single persona, the overall_weighted_confidence equals the reviewer's
    confidence score, and the decision is derived from that confidence and
    blocking issues.

    Args:
        persona_review: PersonaReview instance
        persona_name: Name of the persona

    Returns:
        DecisionAggregation instance
    """
    # For single persona, weighted confidence equals the persona's confidence
    overall_confidence = persona_review.confidence_score

    # Determine decision based on confidence and blocking issues
    if persona_review.blocking_issues:
        decision = DecisionEnum.REJECT
    elif overall_confidence >= 0.7:
        decision = DecisionEnum.APPROVE
    else:
        decision = DecisionEnum.REVISE

    # Create score breakdown with weight=1.0 for single persona
    score_breakdown = {
        persona_name: PersonaScoreBreakdown(
            weight=1.0, notes=f"Single persona review with confidence {overall_confidence}"
        )
    }

    return DecisionAggregation(
        overall_weighted_confidence=overall_confidence,
        decision=decision,
        score_breakdown=score_breakdown,
        minority_report=None,  # No minority report for single persona
    )


@router.post(
    "/review-idea",
    response_model=ReviewIdeaResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully expanded and reviewed idea",
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
                        "reviews": [
                            {
                                "persona_name": "GenericReviewer",
                                "confidence_score": 0.85,
                                "strengths": ["Good architecture", "Clear scope"],
                                "concerns": [
                                    {"text": "Missing error handling", "is_blocking": False}
                                ],
                                "recommendations": ["Add error handling"],
                                "blocking_issues": [],
                                "estimated_effort": "2-3 weeks",
                                "dependency_risks": [],
                            }
                        ],
                        "draft_decision": {
                            "overall_weighted_confidence": 0.85,
                            "decision": "approve",
                            "score_breakdown": {
                                "GenericReviewer": {"weight": 1.0, "notes": "Single persona review"}
                            },
                        },
                        "run_id": "run-123",
                        "elapsed_time": 5.2,
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
            "description": "Internal server error - expansion or review failure",
            "content": {
                "application/json": {
                    "example": {
                        "code": "LLM_SERVICE_ERROR",
                        "message": "Failed to process request",
                        "failed_step": "expand",
                        "run_id": "run-123",
                        "partial_results": None,
                        "details": {"retryable": False},
                    }
                }
            },
        },
    },
    summary="Review an idea through expand, review, and decision aggregation",
    description=(
        "Accepts a brief idea (1-10 sentences) with optional extra context, "
        "expands it into a comprehensive proposal, reviews it with a single persona "
        "(GenericReviewer), and aggregates a draft decision. Returns the expanded "
        "proposal, review, and decision with telemetry. Errors include failed_step "
        "and any partial results."
        "\n\n"
        "**Validation Rules:**\n"
        "- Idea: 1-10 sentences, max 10,000 characters\n"
        "- Extra context: max 50,000 characters (string or JSON)\n"
        "\n\n"
        "**Version Headers (Optional):**\n"
        "- X-Schema-Version: Schema version (current: 1.0.0)\n"
        "- X-Prompt-Set-Version: Prompt set version (current: 1.0.0)\n"
        "If not provided, defaults to current deployment versions with a warning."
    ),
)
async def review_idea_endpoint(
    request_obj: Request,
    review_request: ReviewIdeaRequest,
    settings: Settings = Depends(get_settings),
    x_schema_version: str | None = Header(default=None, alias="X-Schema-Version"),
    x_prompt_set_version: str | None = Header(default=None, alias="X-Prompt-Set-Version"),
) -> ReviewIdeaResponse:
    """Review an idea through expand, review, and decision aggregation.

    This endpoint orchestrates the following steps synchronously:
    1. Validate version headers
    2. Expand the idea into a detailed proposal
    3. Review the proposal with a single persona (GenericReviewer)
    4. Aggregate a draft decision from the review

    Args:
        request_obj: FastAPI request object for accessing state
        review_request: Validated request containing idea and optional extra_context
        settings: Application settings injected via dependency
        x_schema_version: Optional schema version header
        x_prompt_set_version: Optional prompt set version header

    Returns:
        ReviewIdeaResponse with expanded proposal, reviews, and draft decision

    Raises:
        JSONResponse: For validation errors (400, 422) or service errors (500/503)
    """
    # Generate unique run_id for this orchestration
    run_id = str(uuid.uuid4())
    start_time = time.time()

    # Get request_id from middleware if available
    request_id = getattr(request_obj.state, "request_id", "unknown")

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
            metadata={**e.details, "run_id": run_id},
        )
        error_response = ReviewIdeaErrorResponse(
            code=e.code,
            message=e.message,
            failed_step="validation",
            run_id=run_id,
            partial_results=None,
            details=e.details,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response.model_dump(),
        )

    logger.info(
        "Starting review-idea orchestration",
        extra={
            "run_id": run_id,
            "request_id": request_id,
            "has_extra_context": review_request.extra_context is not None,
            "schema_version": schema_version,
            "prompt_set_version": prompt_set_version,
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
        error_response = ReviewIdeaErrorResponse(
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

        error_response = ReviewIdeaErrorResponse(
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

    # Step 2: Review the expanded proposal
    try:
        logger.info(
            "Step 2: Reviewing proposal",
            extra={"run_id": run_id, "step": "review"},
        )

        persona_review, review_metadata = review_proposal(
            expanded_proposal,
            settings,
            # Uses default persona from settings (GenericReviewer)
        )

        logger.info(
            "Step 2 completed: Proposal reviewed successfully",
            extra={
                "run_id": run_id,
                "step": "review",
                "review_request_id": review_metadata.get("request_id"),
                "review_elapsed_time": review_metadata.get("elapsed_time"),
                "persona_name": persona_review.persona_name,
                "confidence_score": persona_review.confidence_score,
            },
        )

    except ConsensusEngineError as e:
        elapsed_time = time.time() - start_time
        logger.error(
            "Step 2 failed: Review error",
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
            # Build ExpandIdeaResponse from expanded_proposal for partial results
            expand_response = _build_expand_response(
                expanded_proposal, expand_metadata or {}, schema_version, prompt_set_version
            )
            partial_results_data = {"expanded_proposal": expand_response.model_dump()}

        error_response = ReviewIdeaErrorResponse(
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
            expand_response = _build_expand_response(
                expanded_proposal, expand_metadata or {}, schema_version, prompt_set_version
            )
            partial_results_data = {"expanded_proposal": expand_response.model_dump()}

        error_response = ReviewIdeaErrorResponse(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred during review",
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
            "Step 3: Aggregating decision",
            extra={"run_id": run_id, "step": "aggregate"},
        )

        draft_decision = _create_single_persona_decision(
            persona_review, persona_review.persona_name
        )

        logger.info(
            "Step 3 completed: Decision aggregated successfully",
            extra={
                "run_id": run_id,
                "step": "aggregate",
                "decision": draft_decision.decision.value,
                "overall_confidence": draft_decision.overall_weighted_confidence,
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

        # Include partial results (expanded proposal and review)
        partial_results_data = {}
        if expanded_proposal:
            expand_response = _build_expand_response(
                expanded_proposal, expand_metadata or {}, schema_version, prompt_set_version
            )
            partial_results_data["expanded_proposal"] = expand_response.model_dump()
        if persona_review:
            partial_results_data["reviews"] = [persona_review.model_dump()]

        error_response = ReviewIdeaErrorResponse(
            code=e.code,
            message=e.message,
            failed_step="aggregate",
            run_id=run_id,
            partial_results=partial_results_data if partial_results_data else None,
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

        # Include partial results (expanded proposal and review)
        partial_results_data = {}
        if expanded_proposal:
            expand_response = _build_expand_response(
                expanded_proposal, expand_metadata or {}, schema_version, prompt_set_version
            )
            partial_results_data["expanded_proposal"] = expand_response.model_dump()
        if persona_review:
            partial_results_data["reviews"] = [persona_review.model_dump()]

        error_response = ReviewIdeaErrorResponse(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred during decision aggregation",
            failed_step="aggregate",
            run_id=run_id,
            partial_results=partial_results_data if partial_results_data else None,
            details={},
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.model_dump(),
        )

    # Build successful response
    elapsed_time = time.time() - start_time

    # Build ExpandIdeaResponse from expanded_proposal
    expand_response = _build_expand_response(
        expanded_proposal, expand_metadata or {}, schema_version, prompt_set_version
    )

    response = ReviewIdeaResponse(
        expanded_proposal=expand_response,
        reviews=[persona_review],
        draft_decision=draft_decision,
        run_id=run_id,
        elapsed_time=elapsed_time,
    )

    logger.info(
        "Review-idea orchestration completed successfully",
        extra={
            "run_id": run_id,
            "request_id": request_id,
            "elapsed_time": elapsed_time,
            "expand_elapsed_time": expand_metadata.get("elapsed_time") if expand_metadata else None,
            "review_elapsed_time": review_metadata.get("elapsed_time"),
            "decision": draft_decision.decision.value,
            "overall_confidence": draft_decision.overall_weighted_confidence,
        },
    )

    return response
