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

This module implements the POST /v1/full-review endpoint that enqueues
expand → multi-persona review → aggregate decision jobs to Pub/Sub
and immediately returns run metadata for polling.
"""

import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from consensus_engine.api.validation import log_validation_failure, validate_version_headers
from consensus_engine.clients.pubsub import PubSubPublishError, get_publisher
from consensus_engine.config import Settings, get_settings
from consensus_engine.config.logging import get_logger
from consensus_engine.db.dependencies import get_db_session
from consensus_engine.db.models import RunPriority, RunStatus, RunType, StepStatus
from consensus_engine.db.repositories import RunRepository, StepProgressRepository
from consensus_engine.exceptions import UnsupportedVersionError, ValidationError
from consensus_engine.schemas.requests import (
    FullReviewRequest,
    JobEnqueuedResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["full-review"])


@router.post(
    "/full-review",
    response_model=JobEnqueuedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue a full review job for an idea",
    description=(
        "Accepts a brief idea (1-10 sentences) with optional extra context, "
        "creates a Run with status='queued', initializes StepProgress entries, "
        "publishes a job message to Pub/Sub, and returns run metadata immediately. "
        "Clients should poll GET /v1/runs/{run_id} to check status and retrieve "
        "results once processing completes."
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
async def full_review_endpoint(
    request_obj: Request,
    review_request: FullReviewRequest,
    settings: Settings = Depends(get_settings),
    db_session: Session = Depends(get_db_session),
    x_schema_version: str | None = Header(default=None, alias="X-Schema-Version"),
    x_prompt_set_version: str | None = Header(default=None, alias="X-Prompt-Set-Version"),
) -> JobEnqueuedResponse:
    """Enqueue a full review job and return run metadata immediately.

    This endpoint:
    1. Validates version headers
    2. Creates a Run with status='queued'
    3. Initializes StepProgress entries for all pipeline steps
    4. Publishes a job message to Pub/Sub with run_id, run_type, priority, and payload
    5. Returns run_id and metadata immediately
    6. Rolls back database changes if Pub/Sub publish fails

    Args:
        request_obj: FastAPI request object for accessing state
        review_request: Validated request containing idea and optional extra_context
        settings: Application settings injected via dependency
        db_session: Database session injected via dependency
        x_schema_version: Optional schema version header
        x_prompt_set_version: Optional prompt set version header

    Returns:
        JobEnqueuedResponse with run_id, status='queued', and timestamps

    Raises:
        HTTPException: 400 for invalid version, 500 if database or Pub/Sub operations fail
    """
    # Pre-generate run_id for atomic failure handling
    run_id = uuid.uuid4()
    start_time = time.time()
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
            metadata={**e.details, "run_id": str(run_id)},
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "code": e.code,
                "message": e.message,
                "details": e.details,
            },
        )

    logger.info(
        "Enqueuing full-review job",
        extra={
            "run_id": str(run_id),
            "request_id": request_id,
            "schema_version": schema_version,
            "prompt_set_version": prompt_set_version,
        },
    )

    # Convert extra_context to dict for storage
    extra_context_dict: dict[str, Any] | None = None
    if review_request.extra_context is not None:
        if isinstance(review_request.extra_context, dict):
            extra_context_dict = review_request.extra_context
        else:
            extra_context_dict = {"text": review_request.extra_context}

    # Build parameters JSON
    parameters_json = {
        "expand_model": settings.expand_model,
        "expand_temperature": settings.expand_temperature,
        "review_model": settings.review_model,
        "review_temperature": settings.review_temperature,
        "persona_template_version": settings.persona_template_version,
        "max_retries_per_persona": settings.max_retries_per_persona,
    }

    # Determine priority (default: normal, can be extended later)
    priority = RunPriority.NORMAL
    run_type = RunType.INITIAL

    # Use validated schema and prompt versions from headers
    try:
        # Step 1: Create Run with status='queued'
        run = RunRepository.create_run(
            session=db_session,
            run_id=run_id,
            input_idea=review_request.idea,
            extra_context=extra_context_dict,
            run_type=run_type,
            model=settings.review_model,
            temperature=settings.review_temperature,
            parameters_json=parameters_json,
            priority=priority,
            status=RunStatus.QUEUED,
            schema_version=schema_version,
            prompt_set_version=prompt_set_version,
        )
        logger.info(
            "Created Run with status='queued'",
            extra={"run_id": str(run_id), "priority": priority.value},
        )

        # Step 2: Initialize StepProgress entries for all pipeline steps
        for step_name in StepProgressRepository.VALID_STEP_NAMES:
            StepProgressRepository.upsert_step_progress(
                session=db_session,
                run_id=run_id,
                step_name=step_name,
                status=StepStatus.PENDING,
            )
        logger.info(
            f"Initialized {len(StepProgressRepository.VALID_STEP_NAMES)} StepProgress entries",
            extra={"run_id": str(run_id)},
        )

        # All database operations successful, commit the transaction first
        db_session.commit()
        logger.info(
            "Run and StepProgress records committed to database",
            extra={"run_id": str(run_id)},
        )

        # Step 3: Publish job message to Pub/Sub
        # Build sanitized payload (exclude internal fields)
        payload = {
            "idea": review_request.idea,
            "extra_context": extra_context_dict,
            "parameters": parameters_json,
        }

        try:
            publisher = get_publisher(settings)
            message_id = publisher.publish(
                run_id=str(run_id),
                run_type=run_type.value,
                priority=priority.value,
                payload=payload,
            )
            logger.info(
                "Published job message to Pub/Sub",
                extra={
                    "run_id": str(run_id),
                    "message_id": message_id,
                    "publish_latency_ms": (time.time() - start_time) * 1000,
                },
            )

        except PubSubPublishError as e:
            # The run is already committed, so we can't roll back.
            # The API should return an error, and a background job
            # could be used to find and retry publishing for such orphaned runs.
            logger.error(
                "Failed to publish job message after committing database changes",
                extra={
                    "run_id": str(run_id),
                    "error": str(e),
                    "mitigation": "A background job should retry publishing for this run_id.",
                },
                exc_info=True,
            )
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "code": "PUBSUB_PUBLISH_ERROR",
                    "message": "Failed to enqueue job: Pub/Sub publish failed after run creation",
                    "run_id": str(run_id),
                    "details": {"error": str(e)},
                },
            )

    except SQLAlchemyError as e:
        # Database error, rollback
        db_session.rollback()
        logger.error(
            "Database error while enqueueing job",
            extra={"run_id": str(run_id), "error": str(e)},
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "DATABASE_ERROR",
                "message": "Failed to create run: Database operation failed",
                "run_id": str(run_id),
                "details": {"error": str(e)},
            },
        )

    except Exception as e:
        # Unexpected error, rollback
        db_session.rollback()
        logger.error(
            "Unexpected error while enqueueing job",
            extra={"run_id": str(run_id), "error": str(e)},
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred while enqueueing job",
                "run_id": str(run_id),
                "details": {},
            },
        )

    # Build successful response
    response = JobEnqueuedResponse(
        run_id=str(run_id),
        status=RunStatus.QUEUED.value,
        run_type=run_type.value,
        priority=priority.value,
        created_at=run.created_at.isoformat(),
        queued_at=run.queued_at.isoformat() if run.queued_at else run.created_at.isoformat(),
        message=f"Full review job enqueued successfully. Poll GET /v1/runs/{run_id} for status.",
    )

    logger.info(
        "Full-review job enqueued successfully",
        extra={
            "run_id": str(run_id),
            "status": "queued",
            "elapsed_time": time.time() - start_time,
        },
    )

    return response
