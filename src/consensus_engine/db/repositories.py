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
"""Repository layer for database operations.

This module provides repository classes for CRUD operations on Run, ProposalVersion,
PersonaReview, and Decision models with proper error handling and logging.
"""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from consensus_engine.config.logging import get_logger
from consensus_engine.db.models import (
    Decision,
    PersonaReview,
    ProposalVersion,
    Run,
    RunPriority,
    RunStatus,
    RunType,
    StepProgress,
    StepStatus,
)
from consensus_engine.schemas.proposal import ExpandedProposal
from consensus_engine.schemas.review import DecisionAggregation
from consensus_engine.schemas.review import PersonaReview as PersonaReviewSchema

logger = get_logger(__name__)


class RunRepository:
    """Repository for Run model operations."""

    @staticmethod
    def create_run(
        session: Session,
        run_id: uuid.UUID,
        input_idea: str,
        extra_context: dict[str, Any] | None,
        run_type: RunType,
        model: str,
        temperature: float,
        parameters_json: dict[str, Any],
        parent_run_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        priority: RunPriority = RunPriority.NORMAL,
        status: RunStatus = RunStatus.QUEUED,
    ) -> Run:
        """Create a new Run record with status='queued' by default.

        Args:
            session: Database session
            run_id: Pre-generated UUID for the run
            input_idea: The original idea text
            extra_context: Optional additional context as dict
            run_type: Whether this is an initial or revision run
            model: LLM model identifier
            temperature: Temperature parameter
            parameters_json: Additional LLM parameters
            parent_run_id: Optional parent run ID for revisions
            user_id: Optional user ID
            priority: Priority level for run execution (default: NORMAL)
            status: Initial status (default: QUEUED)

        Returns:
            Created Run instance

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            now = datetime.now(UTC)
            run = Run(
                id=run_id,
                status=status,
                queued_at=now if status == RunStatus.QUEUED else None,
                started_at=now if status == RunStatus.RUNNING else None,
                input_idea=input_idea,
                extra_context=extra_context,
                run_type=run_type,
                priority=priority,
                model=model,
                temperature=temperature,
                parameters_json=parameters_json,
                parent_run_id=parent_run_id,
                user_id=user_id,
            )

            session.add(run)

            logger.info(
                f"Created Run object with id={run.id}, status={run.status.value}, priority={run.priority.value}",
                extra={"run_id": str(run.id), "status": run.status.value, "priority": run.priority.value},
            )

            return run

        except SQLAlchemyError as e:
            logger.error(f"Failed to create Run: {e}", exc_info=True)
            raise

    @staticmethod
    def update_run_status(
        session: Session,
        run_id: uuid.UUID,
        status: RunStatus,
        overall_weighted_confidence: float | None = None,
        decision_label: str | None = None,
    ) -> Run:
        """Update Run status and optional decision fields.

        Args:
            session: Database session
            run_id: Run ID to update
            status: New status
            overall_weighted_confidence: Optional weighted confidence
            decision_label: Optional decision label

        Returns:
            Updated Run instance

        Raises:
            ValueError: If run not found
            SQLAlchemyError: If database operation fails
        """
        try:
            run = session.get(Run, run_id)
            if not run:
                raise ValueError(f"Run with id={run_id} not found")

            run.status = status
            run.updated_at = datetime.now(UTC)

            if overall_weighted_confidence is not None:
                run.overall_weighted_confidence = overall_weighted_confidence

            if decision_label is not None:
                run.decision_label = decision_label

            session.flush()

            logger.info(
                f"Updated Run id={run_id}, status={status.value}",
                extra={"run_id": str(run_id), "status": status.value},
            )

            return run

        except SQLAlchemyError as e:
            logger.error(f"Failed to update Run id={run_id}: {e}", exc_info=True)
            raise

    @staticmethod
    def get_run(session: Session, run_id: uuid.UUID) -> Run | None:
        """Retrieve a Run by ID.

        Args:
            session: Database session
            run_id: Run ID

        Returns:
            Run instance or None if not found
        """
        return session.get(Run, run_id)

    @staticmethod
    def list_runs(
        session: Session,
        limit: int = 30,
        offset: int = 0,
        status: RunStatus | None = None,
        run_type: RunType | None = None,
        parent_run_id: uuid.UUID | None = None,
        decision: str | None = None,
        min_confidence: float | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[list[Run], int]:
        """List runs with filtering, pagination, and ordering.

        Args:
            session: Database session
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
            Tuple of (list of Run instances, total count)

        Raises:
            SQLAlchemyError: If database query fails
        """
        from sqlalchemy import func, select
        from sqlalchemy.exc import SQLAlchemyError
        from sqlalchemy.orm import joinedload

        try:
            query = select(Run).options(
                joinedload(Run.proposal_version)
            )
            count_query = select(func.count()).select_from(Run)

            # Apply filters
            if status is not None:
                query = query.where(Run.status == status)
                count_query = count_query.where(Run.status == status)

            if run_type is not None:
                query = query.where(Run.run_type == run_type)
                count_query = count_query.where(Run.run_type == run_type)

            if parent_run_id is not None:
                query = query.where(Run.parent_run_id == parent_run_id)
                count_query = count_query.where(Run.parent_run_id == parent_run_id)

            if decision is not None:
                query = query.where(Run.decision_label == decision)
                count_query = count_query.where(Run.decision_label == decision)

            if min_confidence is not None:
                query = query.where(Run.overall_weighted_confidence >= min_confidence)
                count_query = count_query.where(Run.overall_weighted_confidence >= min_confidence)

            if start_date is not None:
                query = query.where(Run.created_at >= start_date)
                count_query = count_query.where(Run.created_at >= start_date)

            if end_date is not None:
                query = query.where(Run.created_at <= end_date)
                count_query = count_query.where(Run.created_at <= end_date)

            # Order by created_at descending (newest first)
            query = query.order_by(Run.created_at.desc())

            # Apply pagination
            query = query.limit(limit).offset(offset)

            # Execute queries
            runs = list(session.execute(query).scalars().all())
            total = session.execute(count_query).scalar_one()

            logger.info(
                f"Listed {len(runs)} runs (total={total}, limit={limit}, offset={offset})",
                extra={"count": len(runs), "total": total, "limit": limit, "offset": offset}
            )

            return runs, total

        except SQLAlchemyError as e:
            logger.error(
                f"Database error while listing runs: {e}",
                extra={"limit": limit, "offset": offset},
                exc_info=True
            )
            raise

    @staticmethod
    def get_run_with_relations(session: Session, run_id: uuid.UUID) -> Run | None:
        """Retrieve a Run by ID with all related data eagerly loaded.

        Args:
            session: Database session
            run_id: Run ID

        Returns:
            Run instance with relations loaded, or None if not found

        Raises:
            SQLAlchemyError: If database query fails
        """
        from sqlalchemy import select
        from sqlalchemy.exc import SQLAlchemyError
        from sqlalchemy.orm import joinedload, selectinload

        try:
            query = (
                select(Run)
                .where(Run.id == run_id)
                .options(
                    joinedload(Run.proposal_version),
                    selectinload(Run.persona_reviews),
                    joinedload(Run.decision),
                )
            )

            result = session.execute(query).scalar_one_or_none()

            if result:
                logger.info(
                    f"Retrieved run {run_id} with relations",
                    extra={"run_id": str(run_id)}
                )
            else:
                logger.warning(
                    f"Run {run_id} not found",
                    extra={"run_id": str(run_id)}
                )

            return result

        except SQLAlchemyError as e:
            logger.error(
                f"Database error while retrieving run {run_id}: {e}",
                extra={"run_id": str(run_id)},
                exc_info=True
            )
            raise


class ProposalVersionRepository:
    """Repository for ProposalVersion model operations."""

    @staticmethod
    def create_proposal_version(
        session: Session,
        run_id: uuid.UUID,
        expanded_proposal: ExpandedProposal,
        persona_template_version: str,
        proposal_diff_json: dict[str, Any] | None = None,
        edit_notes: str | None = None,
    ) -> ProposalVersion:
        """Create a new ProposalVersion record.

        Args:
            session: Database session
            run_id: Parent run ID
            expanded_proposal: ExpandedProposal instance
            persona_template_version: Version of persona templates
            proposal_diff_json: Optional diff from parent proposal
            edit_notes: Optional edit notes

        Returns:
            Created ProposalVersion instance

        Raises:
            IntegrityError: If run_id already has a proposal (unique constraint)
            SQLAlchemyError: If database operation fails
        """
        try:
            # Convert ExpandedProposal to JSON dict
            expanded_proposal_json = json.loads(expanded_proposal.model_dump_json())

            proposal_version = ProposalVersion(
                run_id=run_id,
                expanded_proposal_json=expanded_proposal_json,
                proposal_diff_json=proposal_diff_json,
                persona_template_version=persona_template_version,
                edit_notes=edit_notes,
            )

            session.add(proposal_version)
            session.flush()

            logger.info(
                f"Created ProposalVersion id={proposal_version.id} for run_id={run_id}",
                extra={"proposal_version_id": str(proposal_version.id), "run_id": str(run_id)},
            )

            return proposal_version

        except IntegrityError as e:
            logger.error(
                f"Integrity error creating ProposalVersion for run_id={run_id}: {e}",
                exc_info=True,
            )
            raise
        except SQLAlchemyError as e:
            logger.error(
                f"Failed to create ProposalVersion for run_id={run_id}: {e}", exc_info=True
            )
            raise


class PersonaReviewRepository:
    """Repository for PersonaReview model operations."""

    @staticmethod
    def create_persona_review(
        session: Session,
        run_id: uuid.UUID,
        persona_review: PersonaReviewSchema,
        prompt_parameters_json: dict[str, Any],
    ) -> PersonaReview:
        """Create a new PersonaReview record.

        Args:
            session: Database session
            run_id: Parent run ID
            persona_review: PersonaReviewSchema instance
            prompt_parameters_json: Prompt parameters (model, temp, attempt_count, etc.)

        Returns:
            Created PersonaReview instance

        Raises:
            IntegrityError: If (run_id, persona_id) already exists (unique constraint)
            SQLAlchemyError: If database operation fails
        """
        try:
            # Convert PersonaReviewSchema to JSON dict
            review_json = json.loads(persona_review.model_dump_json())

            # Extract derived fields for indexing
            blocking_issues_present = len(persona_review.blocking_issues) > 0
            security_concerns_present = any(
                issue.security_critical is True for issue in persona_review.blocking_issues
            )

            persona_review_record = PersonaReview(
                run_id=run_id,
                persona_id=persona_review.persona_id,
                persona_name=persona_review.persona_name,
                review_json=review_json,
                confidence_score=persona_review.confidence_score,
                blocking_issues_present=blocking_issues_present,
                security_concerns_present=security_concerns_present,
                prompt_parameters_json=prompt_parameters_json,
            )

            session.add(persona_review_record)
            session.flush()

            logger.info(
                f"Created PersonaReview id={persona_review_record.id} "
                f"for run_id={run_id}, persona_id={persona_review.persona_id}",
                extra={
                    "persona_review_id": str(persona_review_record.id),
                    "run_id": str(run_id),
                    "persona_id": persona_review.persona_id,
                    "confidence_score": persona_review.confidence_score,
                },
            )

            return persona_review_record

        except IntegrityError as e:
            logger.error(
                f"Integrity error creating PersonaReview for run_id={run_id}, "
                f"persona_id={persona_review.persona_id}: {e}",
                exc_info=True,
            )
            raise
        except SQLAlchemyError as e:
            logger.error(
                f"Failed to create PersonaReview for run_id={run_id}, "
                f"persona_id={persona_review.persona_id}: {e}",
                exc_info=True,
            )
            raise


class DecisionRepository:
    """Repository for Decision model operations."""

    @staticmethod
    def create_decision(
        session: Session,
        run_id: uuid.UUID,
        decision_aggregation: DecisionAggregation,
        decision_notes: str | None = None,
    ) -> Decision:
        """Create a new Decision record.

        Args:
            session: Database session
            run_id: Parent run ID
            decision_aggregation: DecisionAggregation instance
            decision_notes: Optional notes

        Returns:
            Created Decision instance

        Raises:
            IntegrityError: If run_id already has a decision (unique constraint)
            SQLAlchemyError: If database operation fails
        """
        try:
            # Convert DecisionAggregation to JSON dict
            decision_json = json.loads(decision_aggregation.model_dump_json())

            decision = Decision(
                run_id=run_id,
                decision_json=decision_json,
                overall_weighted_confidence=decision_aggregation.overall_weighted_confidence,
                decision_notes=decision_notes,
            )

            session.add(decision)
            session.flush()

            logger.info(
                f"Created Decision id={decision.id} for run_id={run_id}",
                extra={
                    "decision_id": str(decision.id),
                    "run_id": str(run_id),
                    "decision": decision_aggregation.decision.value,
                    "confidence": decision_aggregation.overall_weighted_confidence,
                },
            )

            return decision

        except IntegrityError as e:
            logger.error(
                f"Integrity error creating Decision for run_id={run_id}: {e}", exc_info=True
            )
            raise
        except SQLAlchemyError as e:
            logger.error(f"Failed to create Decision for run_id={run_id}: {e}", exc_info=True)
            raise


class StepProgressRepository:
    """Repository for StepProgress model operations."""

    # Canonical step names in order
    VALID_STEP_NAMES = [
        "expand",
        "review_architect",
        "review_critic",
        "review_optimist",
        "review_security",
        "review_user_advocate",
        "aggregate_decision",
    ]

    @staticmethod
    def get_step_order(step_name: str) -> int:
        """Get the order index for a step name.

        Args:
            step_name: The step name to look up

        Returns:
            Integer order index (0-based)

        Raises:
            ValueError: If step_name is not recognized
        """
        try:
            return StepProgressRepository.VALID_STEP_NAMES.index(step_name)
        except ValueError:
            raise ValueError(
                f"Invalid step_name '{step_name}'. Must be one of: {', '.join(StepProgressRepository.VALID_STEP_NAMES)}"
            )

    @staticmethod
    def upsert_step_progress(
        session: Session,
        run_id: uuid.UUID,
        step_name: str,
        status: StepStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error_message: str | None = None,
    ) -> StepProgress:
        """Create or update a step progress record (idempotent).

        This method ensures idempotent updates - calling it multiple times
        with the same run_id and step_name will update the existing record
        rather than creating duplicates.

        Args:
            session: Database session
            run_id: Parent run ID
            step_name: Canonical step name (must be in VALID_STEP_NAMES)
            status: Current status of the step
            started_at: Optional timestamp when step started
            completed_at: Optional timestamp when step completed/failed
            error_message: Optional error message if step failed

        Returns:
            StepProgress instance (created or updated)

        Raises:
            ValueError: If step_name is not recognized
            SQLAlchemyError: If database operation fails
        """
        from sqlalchemy import select

        try:
            # Validate step_name and get order
            step_order = StepProgressRepository.get_step_order(step_name)

            # Try to find existing record
            query = select(StepProgress).where(
                StepProgress.run_id == run_id,
                StepProgress.step_name == step_name
            )
            existing = session.execute(query).scalar_one_or_none()

            if existing:
                # Update existing record
                existing.status = status
                existing.step_order = step_order
                if started_at is not None:
                    existing.started_at = started_at
                if completed_at is not None:
                    existing.completed_at = completed_at
                if error_message is not None:
                    existing.error_message = error_message
                
                session.flush()
                
                logger.info(
                    f"Updated StepProgress id={existing.id} for run_id={run_id}, step={step_name}, status={status.value}",
                    extra={
                        "step_progress_id": str(existing.id),
                        "run_id": str(run_id),
                        "step_name": step_name,
                        "status": status.value,
                    },
                )
                
                return existing
            else:
                # Create new record
                step_progress = StepProgress(
                    run_id=run_id,
                    step_name=step_name,
                    step_order=step_order,
                    status=status,
                    started_at=started_at,
                    completed_at=completed_at,
                    error_message=error_message,
                )

                session.add(step_progress)
                session.flush()

                logger.info(
                    f"Created StepProgress id={step_progress.id} for run_id={run_id}, step={step_name}",
                    extra={
                        "step_progress_id": str(step_progress.id),
                        "run_id": str(run_id),
                        "step_name": step_name,
                        "status": status.value,
                    },
                )

                return step_progress

        except SQLAlchemyError as e:
            logger.error(
                f"Failed to upsert StepProgress for run_id={run_id}, step={step_name}: {e}",
                exc_info=True,
            )
            raise

    @staticmethod
    def get_run_steps(session: Session, run_id: uuid.UUID) -> list[StepProgress]:
        """Get all step progress records for a run, ordered by step_order.

        Args:
            session: Database session
            run_id: Run ID

        Returns:
            List of StepProgress instances ordered by step_order

        Raises:
            SQLAlchemyError: If database query fails
        """
        from sqlalchemy import select

        try:
            query = (
                select(StepProgress)
                .where(StepProgress.run_id == run_id)
                .order_by(StepProgress.step_order)
            )

            steps = list(session.execute(query).scalars().all())

            logger.info(
                f"Retrieved {len(steps)} step progress records for run_id={run_id}",
                extra={"run_id": str(run_id), "step_count": len(steps)},
            )

            return steps

        except SQLAlchemyError as e:
            logger.error(
                f"Failed to get step progress for run_id={run_id}: {e}",
                exc_info=True,
            )
            raise


