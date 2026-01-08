"""Pub/Sub worker for executing async consensus pipelines.

This module provides a Cloud Run-friendly worker process that:
- Consumes Pub/Sub messages from a subscription
- Validates message schema and checks for idempotent processing
- Executes the full pipeline: expand -> persona reviews -> aggregation
- Updates Run and StepProgress records with proper status transitions
- Implements retries, timeouts, and structured logging
- Handles duplicate deliveries safely through idempotency guards
"""

import json
import os
import signal
import sys
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from google.api_core import retry
from google.cloud import pubsub_v1
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from consensus_engine.clients.openai_client import OpenAIClientWrapper
from consensus_engine.config.logging import get_logger
from consensus_engine.config.personas import get_all_personas
from consensus_engine.config.settings import Settings, get_settings
from consensus_engine.db.dependencies import get_engine
from consensus_engine.db.models import (
    Decision,
    PersonaReview as PersonaReviewModel,
    ProposalVersion,
    Run,
    RunStatus,
    RunType,
    StepProgress,
    StepStatus,
)
from consensus_engine.db.repositories import (
    DecisionRepository,
    PersonaReviewRepository,
    ProposalVersionRepository,
    RunRepository,
    StepProgressRepository,
)
from consensus_engine.exceptions import (
    LLMRateLimitError,
    LLMServiceError,
    LLMTimeoutError,
    SchemaValidationError,
)
from consensus_engine.schemas.proposal import ExpandedProposal, IdeaInput
from consensus_engine.services.aggregator import aggregate_persona_reviews
from consensus_engine.services.expand import expand_idea
from consensus_engine.services.orchestrator import (
    determine_personas_to_rerun,
    review_with_all_personas,
    review_with_selective_personas,
)

logger = get_logger(__name__)

# Step names in canonical order
STEP_EXPAND = "expand"
STEP_REVIEW_ARCHITECT = "review_architect"
STEP_REVIEW_CRITIC = "review_critic"
STEP_REVIEW_OPTIMIST = "review_optimist"
STEP_REVIEW_SECURITY = "review_security"
STEP_REVIEW_USER_ADVOCATE = "review_user_advocate"
STEP_AGGREGATE = "aggregate_decision"

ALL_STEPS = [
    STEP_EXPAND,
    STEP_REVIEW_ARCHITECT,
    STEP_REVIEW_CRITIC,
    STEP_REVIEW_OPTIMIST,
    STEP_REVIEW_SECURITY,
    STEP_REVIEW_USER_ADVOCATE,
    STEP_AGGREGATE,
]


class JobMessage(BaseModel):
    """Schema for job messages from Pub/Sub.
    
    Attributes:
        run_id: UUID of the run to process
        run_type: Type of run ('initial' or 'revision')
        priority: Priority level ('normal' or 'high')
        payload: Request payload with idea/context or edit details
    """
    
    run_id: str = Field(..., description="UUID of the run")
    run_type: str = Field(..., description="Type of run (initial or revision)")
    priority: str = Field(..., description="Priority level (normal or high)")
    payload: dict[str, Any] = Field(..., description="Request payload")


class PipelineWorker:
    """Worker that processes pipeline jobs from Pub/Sub.
    
    This worker:
    - Subscribes to a Pub/Sub subscription
    - Validates and processes job messages
    - Executes the full consensus pipeline
    - Updates database with progress and results
    - Handles errors, retries, and timeouts
    - Implements idempotency for duplicate deliveries
    """
    
    def __init__(self, settings: Settings):
        """Initialize the pipeline worker.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.should_stop = False
        
        # Track retry attempts per run
        self.retry_counts: dict[str, int] = {}
        
        # Set up database engine
        self.engine = get_engine(settings)
        
        # Set up Pub/Sub subscriber
        if settings.pubsub_emulator_host:
            os.environ["PUBSUB_EMULATOR_HOST"] = settings.pubsub_emulator_host
            logger.info(
                f"Using Pub/Sub emulator at {settings.pubsub_emulator_host}",
                extra={"emulator_host": settings.pubsub_emulator_host},
            )
            self.project_id = settings.pubsub_project_id or "emulator-project"
        else:
            if not settings.pubsub_project_id:
                raise ValueError("PUBSUB_PROJECT_ID is required when not using emulator")
            self.project_id = settings.pubsub_project_id
        
        # Set up credentials if provided (avoid modifying global env if possible)
        if settings.pubsub_credentials_file and not settings.pubsub_emulator_host:
            # Only set if not already set to avoid overwriting
            if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.pubsub_credentials_file
        
        self.subscriber = pubsub_v1.SubscriberClient()
        self.subscription_path = self.subscriber.subscription_path(
            self.project_id, settings.pubsub_subscription
        )
        
        logger.info(
            "Initialized PipelineWorker",
            extra={
                "project_id": self.project_id,
                "subscription": settings.pubsub_subscription,
                "max_concurrency": settings.worker_max_concurrency,
                "step_timeout_seconds": settings.worker_step_timeout_seconds,
                "job_timeout_seconds": settings.worker_job_timeout_seconds,
            },
        )
    
    def _sanitize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Sanitize payload for safe logging by removing/masking sensitive data.
        
        Args:
            payload: Raw payload data
            
        Returns:
            Sanitized payload safe for logging
        """
        sanitized = {}
        for key, value in payload.items():
            # Mask or truncate potentially sensitive fields
            if key in ("api_key", "password", "token", "secret"):
                sanitized[key] = "***MASKED***"
            elif isinstance(value, str) and len(value) > 200:
                # Truncate long strings
                sanitized[key] = value[:200] + "...[truncated]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_payload(value)
            else:
                sanitized[key] = value
        return sanitized
    
    def _validate_message(self, message_data: dict[str, Any]) -> JobMessage:
        """Validate Pub/Sub message schema.
        
        Args:
            message_data: Decoded message data
            
        Returns:
            Validated JobMessage
            
        Raises:
            ValidationError: If message doesn't match schema
        """
        try:
            return JobMessage(**message_data)
        except ValidationError as e:
            # Log without sensitive payload data
            sanitized_data = {
                "run_id": message_data.get("run_id", "unknown"),
                "run_type": message_data.get("run_type", "unknown"),
                "priority": message_data.get("priority", "unknown"),
            }
            logger.error(
                "Invalid message schema",
                extra={"error": str(e), "message_data": sanitized_data},
                exc_info=True,
            )
            raise
    
    def _check_idempotency(self, session: Session, run_id: uuid.UUID) -> tuple[bool, Run | None]:
        """Check if run has already been processed (idempotency guard).
        
        Uses SELECT FOR UPDATE to prevent race conditions on concurrent message deliveries.
        
        Args:
            session: Database session
            run_id: Run ID to check
            
        Returns:
            Tuple of (should_skip, run_instance)
            - should_skip: True if run is already completed/failed, False otherwise
            - run_instance: The Run object if found, None otherwise
        """
        # Use SELECT FOR UPDATE to lock the row and prevent race conditions
        query = select(Run).where(Run.id == run_id).with_for_update()
        run = session.execute(query).scalar_one_or_none()
        
        if not run:
            logger.warning(
                "Run not found in database",
                extra={"run_id": str(run_id)},
            )
            return False, None
        
        # If run is already completed or failed, skip processing
        if run.status in (RunStatus.COMPLETED, RunStatus.FAILED):
            logger.info(
                f"Run already {run.status.value}, skipping (idempotent)",
                extra={
                    "run_id": str(run_id),
                    "status": run.status.value,
                    "lifecycle_event": "idempotent_skip",
                },
            )
            return True, run
        
        return False, run
    
    def _transition_to_running(self, session: Session, run: Run) -> None:
        """Transition run status to RUNNING.
        
        Args:
            session: Database session
            run: Run instance to update
        """
        if run.status != RunStatus.QUEUED:
            logger.warning(
                f"Run status is {run.status.value}, expected QUEUED",
                extra={"run_id": str(run.id), "status": run.status.value},
            )
        
        run.status = RunStatus.RUNNING
        run.started_at = datetime.now(UTC)
        run.updated_at = datetime.now(UTC)
        session.flush()
        
        logger.info(
            "Run transitioned to RUNNING",
            extra={
                "run_id": str(run.id),
                "status": "running",
                "lifecycle_event": "job_started",
            },
        )
    
    def _mark_step_started(
        self, session: Session, run_id: uuid.UUID, step_name: str
    ) -> None:
        """Mark a step as started.
        
        Args:
            session: Database session
            run_id: Run ID
            step_name: Step name
        """
        StepProgressRepository.upsert_step_progress(
            session=session,
            run_id=run_id,
            step_name=step_name,
            status=StepStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        session.commit()
        
        logger.info(
            f"Step {step_name} started",
            extra={
                "run_id": str(run_id),
                "step_name": step_name,
                "lifecycle_event": "step_started",
            },
        )
    
    def _mark_step_completed(
        self, session: Session, run_id: uuid.UUID, step_name: str, latency_ms: float
    ) -> None:
        """Mark a step as completed.
        
        Args:
            session: Database session
            run_id: Run ID
            step_name: Step name
            latency_ms: Step latency in milliseconds
        """
        StepProgressRepository.upsert_step_progress(
            session=session,
            run_id=run_id,
            step_name=step_name,
            status=StepStatus.COMPLETED,
            completed_at=datetime.now(UTC),
        )
        session.commit()
        
        logger.info(
            f"Step {step_name} completed",
            extra={
                "run_id": str(run_id),
                "step_name": step_name,
                "latency_ms": latency_ms,
                "lifecycle_event": "step_completed",
            },
        )
    
    def _mark_step_failed(
        self,
        session: Session,
        run_id: uuid.UUID,
        step_name: str,
        error_message: str,
        latency_ms: float,
    ) -> None:
        """Mark a step as failed.
        
        Args:
            session: Database session
            run_id: Run ID
            step_name: Step name
            error_message: Error message
            latency_ms: Step latency in milliseconds
        """
        StepProgressRepository.upsert_step_progress(
            session=session,
            run_id=run_id,
            step_name=step_name,
            status=StepStatus.FAILED,
            completed_at=datetime.now(UTC),
            error_message=error_message,
        )
        session.commit()
        
        logger.error(
            f"Step {step_name} failed",
            extra={
                "run_id": str(run_id),
                "step_name": step_name,
                "error_message": error_message,
                "latency_ms": latency_ms,
                "lifecycle_event": "step_failed",
            },
        )
    
    def _execute_expand_step(
        self, session: Session, run: Run
    ) -> ExpandedProposal:
        """Execute the expand step with timeout enforcement.
        
        Args:
            session: Database session
            run: Run instance
            
        Returns:
            ExpandedProposal instance
            
        Raises:
            LLMServiceError: If expand fails
            TimeoutError: If step exceeds timeout
        """
        step_start = time.time()
        self._mark_step_started(session, run.id, STEP_EXPAND)
        
        try:
            # Build IdeaInput from run
            idea_input = IdeaInput(
                idea=run.input_idea,
                extra_context=run.extra_context,
            )
            
            # Call expand service
            expanded_proposal, expand_metadata = expand_idea(idea_input, self.settings)
            
            # Check step timeout
            step_elapsed = time.time() - step_start
            if step_elapsed > self.settings.worker_step_timeout_seconds:
                raise TimeoutError(
                    f"Expand step exceeded timeout of {self.settings.worker_step_timeout_seconds}s "
                    f"(took {step_elapsed:.2f}s)"
                )
            
            # Save proposal version to database
            ProposalVersionRepository.create_proposal_version(
                session=session,
                run_id=run.id,
                expanded_proposal=expanded_proposal,
                persona_template_version=self.settings.persona_template_version,
            )
            session.commit()
            
            latency_ms = (time.time() - step_start) * 1000
            self._mark_step_completed(session, run.id, STEP_EXPAND, latency_ms)
            
            return expanded_proposal
            
        except Exception as e:
            latency_ms = (time.time() - step_start) * 1000
            error_msg = f"Expand failed: {str(e)}"
            self._mark_step_failed(session, run.id, STEP_EXPAND, error_msg, latency_ms)
            raise
    
    def _execute_review_steps(
        self, session: Session, run: Run, expanded_proposal: ExpandedProposal
    ) -> list[Any]:
        """Execute persona review steps with timeout enforcement.
        
        Args:
            session: Database session
            run: Run instance
            expanded_proposal: Expanded proposal to review
            
        Returns:
            List of PersonaReview instances
            
        Raises:
            LLMServiceError: If review fails
            TimeoutError: If step exceeds timeout
        """
        step_start = time.time()
        
        # Mark all review steps as started
        for step_name in [
            STEP_REVIEW_ARCHITECT,
            STEP_REVIEW_CRITIC,
            STEP_REVIEW_OPTIMIST,
            STEP_REVIEW_SECURITY,
            STEP_REVIEW_USER_ADVOCATE,
        ]:
            StepProgressRepository.upsert_step_progress(
                session=session,
                run_id=run.id,
                step_name=step_name,
                status=StepStatus.RUNNING,
                started_at=datetime.now(UTC),
            )
        session.commit()
        
        logger.info(
            "Starting persona reviews",
            extra={
                "run_id": str(run.id),
                "run_type": run.run_type.value,
                "lifecycle_event": "reviews_started",
            },
        )
        
        try:
            # Check timeout before starting reviews
            step_elapsed = time.time() - step_start
            if step_elapsed > self.settings.worker_step_timeout_seconds:
                raise TimeoutError(
                    f"Review steps exceeded timeout of {self.settings.worker_step_timeout_seconds}s"
                )
            
            # Determine if this is initial or revision
            if run.run_type == RunType.INITIAL:
                # Run all personas
                persona_reviews, orchestration_metadata = review_with_all_personas(
                    expanded_proposal, self.settings
                )
            else:
                # Revision - determine which personas to rerun
                # Load parent persona reviews
                parent_run = session.get(Run, run.parent_run_id)
                if not parent_run:
                    raise ValueError(f"Parent run {run.parent_run_id} not found")
                
                # Get parent persona reviews
                query = select(PersonaReviewModel).where(
                    PersonaReviewModel.run_id == parent_run.id
                )
                parent_reviews = list(session.execute(query).scalars().all())
                
                # Convert to format expected by determine_personas_to_rerun
                parent_persona_reviews = [
                    (
                        review.persona_id,
                        review.review_json,
                        review.security_concerns_present,
                    )
                    for review in parent_reviews
                ]
                
                # Determine personas to rerun
                personas_to_rerun = determine_personas_to_rerun(parent_persona_reviews)
                
                # Run selective personas
                persona_reviews, orchestration_metadata = review_with_selective_personas(
                    expanded_proposal,
                    parent_persona_reviews,
                    personas_to_rerun,
                    self.settings,
                )
            
            # Check timeout after reviews
            step_elapsed = time.time() - step_start
            if step_elapsed > self.settings.worker_step_timeout_seconds:
                raise TimeoutError(
                    f"Review steps exceeded timeout of {self.settings.worker_step_timeout_seconds}s "
                    f"(took {step_elapsed:.2f}s)"
                )
            
            # Save persona reviews to database
            for persona_review in persona_reviews:
                # Check if this persona review already exists (idempotency)
                existing_query = select(PersonaReviewModel).where(
                    PersonaReviewModel.run_id == run.id,
                    PersonaReviewModel.persona_id == persona_review.persona_id,
                )
                existing_review = session.execute(existing_query).scalar_one_or_none()
                
                if existing_review:
                    logger.info(
                        f"Persona review for {persona_review.persona_id} already exists, skipping",
                        extra={
                            "run_id": str(run.id),
                            "persona_id": persona_review.persona_id,
                        },
                    )
                    continue
                
                # Build prompt parameters
                prompt_parameters = {
                    "model": self.settings.review_model,
                    "temperature": self.settings.review_temperature,
                    "persona_template_version": self.settings.persona_template_version,
                }
                
                PersonaReviewRepository.create_persona_review(
                    session=session,
                    run_id=run.id,
                    persona_review=persona_review,
                    prompt_parameters_json=prompt_parameters,
                )
            
            session.commit()
            
            # Mark all review steps as completed
            latency_ms = (time.time() - step_start) * 1000
            for step_name in [
                STEP_REVIEW_ARCHITECT,
                STEP_REVIEW_CRITIC,
                STEP_REVIEW_OPTIMIST,
                STEP_REVIEW_SECURITY,
                STEP_REVIEW_USER_ADVOCATE,
            ]:
                StepProgressRepository.upsert_step_progress(
                    session=session,
                    run_id=run.id,
                    step_name=step_name,
                    status=StepStatus.COMPLETED,
                    completed_at=datetime.now(UTC),
                )
            session.commit()
            
            logger.info(
                "Persona reviews completed",
                extra={
                    "run_id": str(run.id),
                    "review_count": len(persona_reviews),
                    "latency_ms": latency_ms,
                    "lifecycle_event": "reviews_completed",
                },
            )
            
            return persona_reviews
            
        except Exception as e:
            latency_ms = (time.time() - step_start) * 1000
            error_msg = f"Reviews failed: {str(e)}"
            
            # Mark all review steps as failed
            for step_name in [
                STEP_REVIEW_ARCHITECT,
                STEP_REVIEW_CRITIC,
                STEP_REVIEW_OPTIMIST,
                STEP_REVIEW_SECURITY,
                STEP_REVIEW_USER_ADVOCATE,
            ]:
                StepProgressRepository.upsert_step_progress(
                    session=session,
                    run_id=run.id,
                    step_name=step_name,
                    status=StepStatus.FAILED,
                    completed_at=datetime.now(UTC),
                    error_message=error_msg,
                )
            session.commit()
            
            raise
    
    def _execute_aggregate_step(
        self, session: Session, run: Run, persona_reviews: list[Any]
    ) -> None:
        """Execute the aggregate decision step.
        
        Args:
            session: Database session
            run: Run instance
            persona_reviews: List of PersonaReview instances
            
        Raises:
            Exception: If aggregation fails
        """
        step_start = time.time()
        self._mark_step_started(session, run.id, STEP_AGGREGATE)
        
        try:
            # Aggregate reviews
            decision_aggregation = aggregate_persona_reviews(persona_reviews)
            
            # Check if decision already exists (idempotency)
            existing_decision = session.execute(
                select(Decision).where(Decision.run_id == run.id)
            ).scalar_one_or_none()
            
            if existing_decision:
                logger.info(
                    "Decision already exists, skipping",
                    extra={"run_id": str(run.id)},
                )
            else:
                # Save decision to database
                DecisionRepository.create_decision(
                    session=session,
                    run_id=run.id,
                    decision_aggregation=decision_aggregation,
                )
            
            # Update run with decision summary
            run.overall_weighted_confidence = decision_aggregation.overall_weighted_confidence
            run.decision_label = decision_aggregation.decision.value
            session.commit()
            
            latency_ms = (time.time() - step_start) * 1000
            self._mark_step_completed(session, run.id, STEP_AGGREGATE, latency_ms)
            
        except Exception as e:
            latency_ms = (time.time() - step_start) * 1000
            error_msg = f"Aggregation failed: {str(e)}"
            self._mark_step_failed(session, run.id, STEP_AGGREGATE, error_msg, latency_ms)
            raise
    
    def _process_job(self, session: Session, job_msg: JobMessage) -> None:
        """Process a single job message with timeout and retry tracking.
        
        Args:
            session: Database session
            job_msg: Validated job message
            
        Raises:
            Exception: If processing fails
            TimeoutError: If job exceeds timeout
        """
        run_id = uuid.UUID(job_msg.run_id)
        job_start_time = time.time()
        
        # Track retry count
        run_id_str = str(run_id)
        retry_count = self.retry_counts.get(run_id_str, 0)
        self.retry_counts[run_id_str] = retry_count + 1
        
        logger.info(
            "Starting job processing",
            extra={
                "run_id": run_id_str,
                "run_type": job_msg.run_type,
                "priority": job_msg.priority,
                "retry_count": retry_count,
                "lifecycle_event": "job_started",
            },
        )
        
        # Check idempotency (with row locking)
        should_skip, run = self._check_idempotency(session, run_id)
        if should_skip:
            # Job already completed, acknowledge and return
            # Clear retry count on successful completion
            self.retry_counts.pop(run_id_str, None)
            return
        
        if not run:
            raise ValueError(f"Run {run_id} not found in database")
        
        # Transition to RUNNING
        self._transition_to_running(session, run)
        session.commit()
        
        try:
            # Execute pipeline steps
            # Step 1: Expand
            self._check_job_timeout(job_start_time, run_id_str)
            expanded_proposal = self._execute_expand_step(session, run)
            
            # Step 2-6: Persona reviews
            self._check_job_timeout(job_start_time, run_id_str)
            persona_reviews = self._execute_review_steps(session, run, expanded_proposal)
            
            # Step 7: Aggregate
            self._check_job_timeout(job_start_time, run_id_str)
            self._execute_aggregate_step(session, run, persona_reviews)
            
            # Mark run as completed
            run.status = RunStatus.COMPLETED
            run.completed_at = datetime.now(UTC)
            run.updated_at = datetime.now(UTC)
            session.commit()
            
            job_latency_ms = (time.time() - job_start_time) * 1000
            
            logger.info(
                "Job completed successfully",
                extra={
                    "run_id": run_id_str,
                    "job_latency_ms": job_latency_ms,
                    "decision": run.decision_label,
                    "confidence": run.overall_weighted_confidence,
                    "retry_count": retry_count,
                    "lifecycle_event": "job_completed",
                },
            )
            
            # Clear retry count on successful completion
            self.retry_counts.pop(run_id_str, None)
            
        except Exception as e:
            # Mark run as failed
            run.status = RunStatus.FAILED
            run.completed_at = datetime.now(UTC)
            run.updated_at = datetime.now(UTC)
            session.commit()
            
            job_latency_ms = (time.time() - job_start_time) * 1000
            
            logger.error(
                "Job failed",
                extra={
                    "run_id": run_id_str,
                    "job_latency_ms": job_latency_ms,
                    "error": str(e),
                    "retry_count": retry_count,
                    "lifecycle_event": "job_failed",
                },
                exc_info=True,
            )
            
            # Re-raise to nack message (will be retried by Pub/Sub)
            raise
    
    def _check_job_timeout(self, job_start_time: float, run_id: str) -> None:
        """Check if job has exceeded overall timeout.
        
        Args:
            job_start_time: Time when job started
            run_id: Run ID for logging
            
        Raises:
            TimeoutError: If job exceeds timeout
        """
        job_elapsed = time.time() - job_start_time
        if job_elapsed > self.settings.worker_job_timeout_seconds:
            error_msg = (
                f"Job exceeded overall timeout of {self.settings.worker_job_timeout_seconds}s "
                f"(took {job_elapsed:.2f}s)"
            )
            logger.error(
                "Job timeout exceeded",
                extra={
                    "run_id": run_id,
                    "job_elapsed_seconds": job_elapsed,
                    "timeout_seconds": self.settings.worker_job_timeout_seconds,
                    "lifecycle_event": "job_timeout",
                },
            )
            raise TimeoutError(error_msg)
    
    def _message_callback(self, message: pubsub_v1.subscriber.message.Message) -> None:
        """Callback for processing Pub/Sub messages.
        
        Args:
            message: Pub/Sub message
        """
        message_start_time = time.time()
        
        try:
            # Decode message
            message_data = json.loads(message.data.decode("utf-8"))
            
            # Validate message schema
            job_msg = self._validate_message(message_data)
            
            # Create database session
            with Session(self.engine) as session:
                # Process job
                self._process_job(session, job_msg)
            
            # Acknowledge message (commit transaction)
            message.ack()
            
            message_latency_ms = (time.time() - message_start_time) * 1000
            logger.info(
                "Message processed and acknowledged",
                extra={
                    "run_id": job_msg.run_id,
                    "message_id": message.message_id,
                    "message_latency_ms": message_latency_ms,
                },
            )
            
        except ValidationError as e:
            # Invalid message schema - ack to remove from queue
            logger.error(
                "Invalid message schema, acknowledging to remove from queue",
                extra={
                    "message_id": message.message_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            message.ack()
            
        except Exception as e:
            # Processing error - nack to retry
            message_latency_ms = (time.time() - message_start_time) * 1000
            logger.error(
                "Message processing failed, nacking for retry",
                extra={
                    "message_id": message.message_id,
                    "message_latency_ms": message_latency_ms,
                    "error": str(e),
                },
                exc_info=True,
            )
            message.nack()
    
    def start(self) -> None:
        """Start the worker to consume messages.
        
        This method blocks until the worker is stopped via signal or error.
        """
        logger.info(
            "Starting pipeline worker",
            extra={
                "subscription_path": self.subscription_path,
                "max_concurrency": self.settings.worker_max_concurrency,
            },
        )
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(signum: int, frame: Any) -> None:
            logger.info(
                f"Received signal {signum}, stopping worker",
                extra={"signal": signum},
            )
            self.should_stop = True
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Configure flow control
        flow_control = pubsub_v1.types.FlowControl(
            max_messages=self.settings.worker_max_concurrency,
        )
        
        # Start streaming pull
        streaming_pull_future = self.subscriber.subscribe(
            self.subscription_path,
            callback=self._message_callback,
            flow_control=flow_control,
        )
        
        logger.info(
            "Worker started, listening for messages",
            extra={"subscription_path": self.subscription_path},
        )
        
        try:
            # Block until stopped
            while not self.should_stop:
                time.sleep(1)
            
            # Cancel subscription
            streaming_pull_future.cancel()
            streaming_pull_future.result(timeout=30)
            
        except Exception as e:
            logger.error(
                "Worker error",
                extra={"error": str(e)},
                exc_info=True,
            )
            streaming_pull_future.cancel()
            raise
        finally:
            self.subscriber.close()
            logger.info("Worker stopped")


def main() -> None:
    """Main entry point for the pipeline worker."""
    try:
        settings = get_settings()
        worker = PipelineWorker(settings)
        worker.start()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(
            "Worker failed to start",
            extra={"error": str(e)},
            exc_info=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
