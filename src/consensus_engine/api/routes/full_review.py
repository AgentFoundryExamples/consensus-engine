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
database persistence in a single transaction.
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
from consensus_engine.db.dependencies import get_db_session, get_session_factory
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
        "a final decision. All steps are persisted to the database in a single transaction. "
        "Returns run_id for tracing."
    ),
)
async def full_review_endpoint(
    request_obj: Request,
    review_request: FullReviewRequest,
    settings: Settings = Depends(get_settings),
    db_session: Session = Depends(get_db_session),
) -> FullReviewResponse:
    """Expand and review an idea with all five personas with atomic database persistence.
    
    All database operations are performed in a single transaction that is committed
    only after all steps complete successfully. If any step fails, the entire
    transaction is rolled back.
    """
    # Pre-generate run_id for atomic failure handling
    run_id = uuid.uuid4()
    start_time = time.time()
    request_id = getattr(request_obj.state, "request_id", "unknown")

    logger.info(
        "Starting full-review with single-transaction DB persistence",
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

    # Prepare IdeaInput
    extra_context_str: str | None = None
    if review_request.extra_context is not None:
        if isinstance(review_request.extra_context, dict):
            extra_context_str = json.dumps(review_request.extra_context, indent=2)
        else:
            extra_context_str = review_request.extra_context

    idea_input = IdeaInput(idea=review_request.idea, extra_context=extra_context_str)

    # Track partial results for error responses
    expanded_proposal: ExpandedProposal | None = None
    expand_metadata: dict[str, Any] | None = None
    persona_reviews: list | None = None
    orchestration_metadata: dict[str, Any] | None = None

    try:
        # Step 0: Create Run object (not committed yet)
        run = RunRepository.create_run(
            session=db_session,
            run_id=run_id,
            input_idea=review_request.idea,
            extra_context=extra_context_dict,
            run_type=RunType.INITIAL,
            model=settings.review_model,
            temperature=settings.review_temperature,
            parameters_json=parameters_json,
        )
        logger.info("Created Run object in session", extra={"run_id": str(run_id)})

        # Step 1: Expand idea
        logger.info("Step 1: Expanding idea", extra={"run_id": str(run_id)})
        expanded_proposal, expand_metadata = expand_idea(idea_input, settings)
        logger.info("Step 1 complete", extra={"run_id": str(run_id)})

        # Step 1a: Persist ProposalVersion (not committed yet)
        ProposalVersionRepository.create_proposal_version(
            session=db_session,
            run_id=run_id,
            expanded_proposal=expanded_proposal,
            persona_template_version=settings.persona_template_version,
        )
        logger.info("Created ProposalVersion object in session", extra={"run_id": str(run_id)})

        # Step 2: Review with all personas
        logger.info("Step 2: Reviewing with all personas", extra={"run_id": str(run_id)})
        persona_reviews, orchestration_metadata = review_with_all_personas(
            expanded_proposal, settings
        )
        logger.info("Step 2 complete", extra={"run_id": str(run_id)})

        # Step 2a: Persist PersonaReviews (not committed yet)
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
        logger.info(
            f"Created {len(persona_reviews)} PersonaReview objects in session",
            extra={"run_id": str(run_id)},
        )

        # Step 3: Aggregate decision
        logger.info("Step 3: Aggregating decision", extra={"run_id": str(run_id)})
        decision = aggregate_persona_reviews(persona_reviews)
        logger.info("Step 3 complete", extra={"run_id": str(run_id)})

        # Step 3a: Persist Decision and update Run (not committed yet)
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
        logger.info(
            "Created Decision and updated Run to COMPLETED in session",
            extra={"run_id": str(run_id)},
        )

        # All steps successful, commit the single transaction
        db_session.commit()
        logger.info("All steps successful, transaction committed", extra={"run_id": str(run_id)})

    except (ConsensusEngineError, SQLAlchemyError, Exception) as e:
        # Any error occurs, rollback the entire transaction
        db_session.rollback()

        # Determine error details
        if isinstance(e, ConsensusEngineError):
            error_code = e.code
            error_message = e.message
            error_details = e.details
            status_code = _map_exception_to_status_code(e)
            failed_step = "expand" if isinstance(e, (LLMAuthenticationError, LLMRateLimitError, LLMTimeoutError)) else "unknown"
        elif isinstance(e, SQLAlchemyError):
            error_code = "DATABASE_ERROR"
            error_message = "Database operation failed"
            error_details = {"error": str(e)}
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            failed_step = "database"
        else:
            error_code = "INTERNAL_ERROR"
            error_message = "An unexpected error occurred"
            error_details = {}
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            failed_step = "unknown"

        # Log the primary error
        logger.error(
            f"Full review failed, transaction rolled back: {e}",
            extra={"run_id": str(run_id), "error_code": error_code},
            exc_info=True,
        )

        # Try to create a FAILED run record in a new transaction for auditing
        try:
            # Get a new session for the audit record
            session_factory = get_session_factory()
            if session_factory:
                audit_session = session_factory()
                try:
                    # Create a failed run for audit trail
                    RunRepository.create_run(
                        session=audit_session,
                        run_id=run_id,
                        input_idea=review_request.idea,
                        extra_context=extra_context_dict,
                        run_type=RunType.INITIAL,
                        model=settings.review_model,
                        temperature=settings.review_temperature,
                        parameters_json=parameters_json,
                    )
                    RunRepository.update_run_status(
                        session=audit_session,
                        run_id=run_id,
                        status=RunStatus.FAILED,
                    )
                    audit_session.commit()
                    logger.info("Created FAILED run record for auditing", extra={"run_id": str(run_id)})
                except Exception:
                    audit_session.rollback()
                    raise
                finally:
                    audit_session.close()
        except Exception as audit_e:
            logger.error(
                f"Failed to create audit record for failed run: {audit_e}",
                extra={"run_id": str(run_id)},
                exc_info=True,
            )

        # Build partial results if available
        partial_results_data: dict[str, Any] | None = None
        if expanded_proposal:
            expand_response = _build_expand_response(expanded_proposal, expand_metadata or {})
            partial_results_data = {"expanded_proposal": expand_response.model_dump()}
            if persona_reviews:
                partial_results_data["persona_reviews"] = [
                    review.model_dump() for review in persona_reviews
                ]

        # Return error response
        return JSONResponse(
            status_code=status_code,
            content=FullReviewErrorResponse(
                code=error_code,
                message=error_message,
                failed_step=failed_step,
                run_id=str(run_id),
                partial_results=partial_results_data,
                details=error_details,
            ).model_dump(),
        )

    # Build successful response
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
        "Full-review completed successfully with single-transaction DB persistence",
        extra={
            "run_id": str(run_id),
            "elapsed_time": elapsed_time,
            "decision": decision.decision.value,
            "status": "completed",
        },
    )

    return response
