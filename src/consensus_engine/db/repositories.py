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
    RunStatus,
    RunType,
)
from consensus_engine.schemas.proposal import ExpandedProposal
from consensus_engine.schemas.review import DecisionAggregation, PersonaReview as PersonaReviewSchema

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
    ) -> Run:
        """Create a new Run record with status='running'.

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

        Returns:
            Created Run instance

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            run = Run(
                id=run_id,
                status=RunStatus.RUNNING,
                input_idea=input_idea,
                extra_context=extra_context,
                run_type=run_type,
                model=model,
                temperature=temperature,
                parameters_json=parameters_json,
                parent_run_id=parent_run_id,
                user_id=user_id,
            )

            session.add(run)

            logger.info(
                f"Created Run object with id={run.id}, status={run.status.value}",
                extra={"run_id": str(run.id), "status": run.status.value},
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
            logger.error(f"Integrity error creating Decision for run_id={run_id}: {e}", exc_info=True)
            raise
        except SQLAlchemyError as e:
            logger.error(f"Failed to create Decision for run_id={run_id}: {e}", exc_info=True)
            raise

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
        """
        from sqlalchemy import select, func
        
        query = select(Run)
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

    @staticmethod
    def get_run_with_relations(session: Session, run_id: uuid.UUID) -> Run | None:
        """Retrieve a Run by ID with all related data eagerly loaded.
        
        Args:
            session: Database session
            run_id: Run ID
            
        Returns:
            Run instance with relations loaded, or None if not found
        """
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload
        
        query = (
            select(Run)
            .where(Run.id == run_id)
            .options(
                joinedload(Run.proposal_version),
                joinedload(Run.persona_reviews),
                joinedload(Run.decision),
            )
        )
        
        result = session.execute(query).unique().scalar_one_or_none()
        
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
