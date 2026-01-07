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
"""Full review endpoint router.

This module implements the POST /v1/full-review endpoint that orchestrates
expand → multi-persona review → aggregate decision flow synchronously with
database persistence at each step.
"""

import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
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
    summary="Expand and review an idea with all five personas",
    description=(
        "Accepts a brief idea (1-10 sentences) with optional extra context, "
        "expands it into a comprehensive proposal, reviews it with all five personas "
        "(Architect, Critic, Optimist, SecurityGuardian, UserAdvocate), and aggregates "
        "a final decision. All steps are persisted to the database for audit trails. "
        "Returns run_id for tracing."
    ),
)
async def full_review_endpoint(
    request_obj: Request,
    review_request: FullReviewRequest,
    settings: Settings = Depends(get_settings),
    db_session: Session = Depends(get_db_session),
) -> FullReviewResponse:
    """Expand and review an idea with all five personas with database persistence."""
    # Generate unique run_id
    run_id = uuid.uuid4()
    start_time = time.time()
    request_id = getattr(request_obj.state, "request_id", "unknown")

    logger.info(
        "Starting full-review with DB persistence",
        extra={"run_id": str(run_id), "request_id": request_id},
    )

    # Convert extra_context
    extra_context_dict: dict[str, Any] | None = None
    if review_request.extra_context is not None:
        if isinstance(review_request.extra_context, dict):
            extra_context_dict = review_request.extra_context
        else:
            extra_context_dict = {"text": review_request.extra_context}

    # Build parameters
    parameters_json = {
        "expand_model": settings.expand_model,
        "expand_temperature": settings.expand_temperature,
        "review_model": settings.review_model,
        "review_temperature": settings.review_temperature,
        "persona_template_version": settings.persona_template_version,
        "max_retries_per_persona": settings.max_retries_per_persona,
    }

    # Create Run
    try:
        run = RunRepository.create_run(
            session=db_session,
            input_idea=review_request.idea,
            extra_context=extra_context_dict,
            run_type=RunType.INITIAL,
            model=settings.review_model,
            temperature=settings.review_temperature,
            parameters_json=parameters_json,
        )
        run_id = run.id
        db_session.commit()
        logger.info("Created Run", extra={"run_id": str(run_id)})
    except SQLAlchemyError as e:
        logger.error(f"Failed to create Run: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=FullReviewErrorResponse(
                code="DATABASE_ERROR",
                message="Failed to create run",
                failed_step="initialization",
                run_id=str(run_id),
                partial_results=None,
                details={"error": str(e)},
            ).model_dump(),
        )

    expanded_proposal: ExpandedProposal | None = None
    expand_metadata: dict[str, Any] | None = None
    persona_reviews: list | None = None
    orchestration_metadata: dict[str, Any] | None = None

    # Prepare IdeaInput
    extra_context_str: str | None = None
    if review_request.extra_context is not None:
        if isinstance(review_request.extra_context, dict):
            extra_context_str = json.dumps(review_request.extra_context, indent=2)
        else:
            extra_context_str = review_request.extra_context

    idea_input = IdeaInput(idea=review_request.idea, extra_context=extra_context_str)

    # Step 1: Expand
    try:
        logger.info("Step 1: Expanding", extra={"run_id": str(run_id)})
        expanded_proposal, expand_metadata = expand_idea(idea_input, settings)
        logger.info("Step 1 complete", extra={"run_id": str(run_id)})

        # Persist ProposalVersion
        try:
            proposal_version = ProposalVersionRepository.create_proposal_version(
                session=db_session,
                run_id=run_id,
                expanded_proposal=expanded_proposal,
                persona_template_version=settings.persona_template_version,
            )
            db_session.commit()
            logger.info("Persisted ProposalVersion", extra={"run_id": str(run_id)})
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"Failed to persist ProposalVersion: {e}", exc_info=True)
            try:
                RunRepository.update_run_status(db_session, run_id, RunStatus.FAILED)
                db_session.commit()
            except Exception:
                pass
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=FullReviewErrorResponse(
                    code="DATABASE_ERROR",
                    message="Failed to persist proposal",
                    failed_step="expand",
                    run_id=str(run_id),
                    partial_results=None,
                    details={"error": str(e)},
                ).model_dump(),
            )

    except ConsensusEngineError as e:
        db_session.rollback()
        try:
            RunRepository.update_run_status(db_session, run_id, RunStatus.FAILED)
            db_session.commit()
        except Exception:
            pass
        return JSONResponse(
            status_code=_map_exception_to_status_code(e),
            content=FullReviewErrorResponse(
                code=e.code,
                message=e.message,
                failed_step="expand",
                run_id=str(run_id),
                partial_results=None,
                details=e.details,
            ).model_dump(),
        )
    except Exception:
        db_session.rollback()
        try:
            RunRepository.update_run_status(db_session, run_id, RunStatus.FAILED)
            db_session.commit()
        except Exception:
            pass
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=FullReviewErrorResponse(
                code="INTERNAL_ERROR",
                message="Unexpected error during expansion",
                failed_step="expand",
                run_id=str(run_id),
                partial_results=None,
                details={},
            ).model_dump(),
        )

    # Step 2: Review
    try:
        logger.info("Step 2: Reviewing", extra={"run_id": str(run_id)})
        persona_reviews, orchestration_metadata = review_with_all_personas(
            expanded_proposal, settings
        )
        logger.info("Step 2 complete", extra={"run_id": str(run_id)})

        # Persist PersonaReviews
        try:
            for review in persona_reviews:
                prompt_parameters_json = {
                    "model": settings.review_model,
                    "temperature": settings.review_temperature,
                    "persona_template_version": settings.persona_template_version,
                    "attempt_count": review.internal_metadata.get("attempt_count", 1)
                    if review.internal_metadata
                    else 1,
                    "request_id": review.internal_metadata.get("request_id")
                    if review.internal_metadata
                    else None,
                }
                PersonaReviewRepository.create_persona_review(
                    session=db_session,
                    run_id=run_id,
                    persona_review=review,
                    prompt_parameters_json=prompt_parameters_json,
                )
            db_session.commit()
            logger.info(f"Persisted {len(persona_reviews)} reviews", extra={"run_id": str(run_id)})
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"Failed to persist reviews: {e}", exc_info=True)
            try:
                RunRepository.update_run_status(db_session, run_id, RunStatus.FAILED)
                db_session.commit()
            except Exception:
                pass
            partial_results_data = None
            if expanded_proposal:
                expand_response = _build_expand_response(expanded_proposal, expand_metadata or {})
                partial_results_data = {"expanded_proposal": expand_response.model_dump()}
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=FullReviewErrorResponse(
                    code="DATABASE_ERROR",
                    message="Failed to persist reviews",
                    failed_step="review",
                    run_id=str(run_id),
                    partial_results=partial_results_data,
                    details={"error": str(e)},
                ).model_dump(),
            )

    except ConsensusEngineError as e:
        db_session.rollback()
        try:
            RunRepository.update_run_status(db_session, run_id, RunStatus.FAILED)
            db_session.commit()
        except Exception:
            pass
        partial_results_data = None
        if expanded_proposal:
            expand_response = _build_expand_response(expanded_proposal, expand_metadata or {})
            partial_results_data = {"expanded_proposal": expand_response.model_dump()}
        return JSONResponse(
            status_code=_map_exception_to_status_code(e),
            content=FullReviewErrorResponse(
                code=e.code,
                message=e.message,
                failed_step="review",
                run_id=str(run_id),
                partial_results=partial_results_data,
                details=e.details,
            ).model_dump(),
        )
    except Exception:
        db_session.rollback()
        try:
            RunRepository.update_run_status(db_session, run_id, RunStatus.FAILED)
            db_session.commit()
        except Exception:
            pass
        partial_results_data = None
        if expanded_proposal:
            expand_response = _build_expand_response(expanded_proposal, expand_metadata or {})
            partial_results_data = {"expanded_proposal": expand_response.model_dump()}
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=FullReviewErrorResponse(
                code="INTERNAL_ERROR",
                message="Unexpected error during review",
                failed_step="review",
                run_id=str(run_id),
                partial_results=partial_results_data,
                details={},
            ).model_dump(),
        )

    # Step 3: Aggregate
    try:
        logger.info("Step 3: Aggregating", extra={"run_id": str(run_id)})
        decision = aggregate_persona_reviews(persona_reviews)
        logger.info("Step 3 complete", extra={"run_id": str(run_id)})

        # Persist Decision and update Run
        try:
            DecisionRepository.create_decision(
                session=db_session,
                run_id=run_id,
                decision_aggregation=decision,
            )
            RunRepository.update_run_status(
                session=db_session,
                run_id=run_id,
                status=RunStatus.COMPLETED,
                overall_weighted_confidence=decision.overall_weighted_confidence,
                decision_label=decision.decision.value,
            )
            db_session.commit()
            logger.info("Persisted Decision, Run completed", extra={"run_id": str(run_id)})
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"Failed to persist Decision: {e}", exc_info=True)
            try:
                RunRepository.update_run_status(db_session, run_id, RunStatus.FAILED)
                db_session.commit()
            except Exception:
                pass
            partial_results_data: dict[str, Any] | None = None
            if expanded_proposal and persona_reviews:
                expand_response = _build_expand_response(expanded_proposal, expand_metadata or {})
                partial_results_data = {
                    "expanded_proposal": expand_response.model_dump(),
                    "persona_reviews": [review.model_dump() for review in persona_reviews],
                }
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=FullReviewErrorResponse(
                    code="DATABASE_ERROR",
                    message="Failed to persist decision",
                    failed_step="aggregate",
                    run_id=str(run_id),
                    partial_results=partial_results_data,
                    details={"error": str(e)},
                ).model_dump(),
            )

    except ConsensusEngineError as e:
        db_session.rollback()
        try:
            RunRepository.update_run_status(db_session, run_id, RunStatus.FAILED)
            db_session.commit()
        except Exception:
            pass
        partial_results_data: dict[str, Any] | None = None
        if expanded_proposal and persona_reviews:
            expand_response = _build_expand_response(expanded_proposal, expand_metadata or {})
            partial_results_data = {
                "expanded_proposal": expand_response.model_dump(),
                "persona_reviews": [review.model_dump() for review in persona_reviews],
            }
        return JSONResponse(
            status_code=_map_exception_to_status_code(e),
            content=FullReviewErrorResponse(
                code=e.code,
                message=e.message,
                failed_step="aggregate",
                run_id=str(run_id),
                partial_results=partial_results_data,
                details=e.details,
            ).model_dump(),
        )
    except Exception:
        db_session.rollback()
        try:
            RunRepository.update_run_status(db_session, run_id, RunStatus.FAILED)
            db_session.commit()
        except Exception:
            pass
        partial_results_data: dict[str, Any] | None = None
        if expanded_proposal and persona_reviews:
            expand_response = _build_expand_response(expanded_proposal, expand_metadata or {})
            partial_results_data = {
                "expanded_proposal": expand_response.model_dump(),
                "persona_reviews": [review.model_dump() for review in persona_reviews],
            }
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=FullReviewErrorResponse(
                code="INTERNAL_ERROR",
                message="Unexpected error during aggregation",
                failed_step="aggregate",
                run_id=str(run_id),
                partial_results=partial_results_data,
                details={},
            ).model_dump(),
        )

    # Success
    elapsed_time = time.time() - start_time
    expand_response = _build_expand_response(expanded_proposal, expand_metadata or {})

    response = FullReviewResponse(
        expanded_proposal=expand_response,
        persona_reviews=persona_reviews,
        decision=decision,
        run_id=str(run_id),
        elapsed_time=elapsed_time,
    )

    logger.info(
        "Full-review completed with DB persistence",
        extra={
            "run_id": str(run_id),
            "elapsed_time": elapsed_time,
            "decision": decision.decision.value,
            "status": "completed",
        },
    )

    return response
