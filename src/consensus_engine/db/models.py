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
"""SQLAlchemy models for versioned run lifecycle tracking.

This module defines database models for tracking runs, proposal versions,
persona reviews, and decisions. Each model captures structured data as JSONB
plus derived scalar columns for query performance.
"""

import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from consensus_engine.db import Base


class RunStatus(str, enum.Enum):
    """Enumeration of run lifecycle states."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RunType(str, enum.Enum):
    """Enumeration of run types."""

    INITIAL = "initial"
    REVISION = "revision"


class Run(Base):
    """Model for tracking proposal evaluation runs.

    A run represents a single pass through the expansion-review-decision pipeline.
    Runs can be initial (from scratch) or revision (based on a parent run).

    Attributes:
        id: UUID primary key
        created_at: Timestamp when run was created
        updated_at: Timestamp when run was last updated
        user_id: Optional UUID of the user who initiated the run
        status: Current status of the run (running, completed, failed)
        input_idea: The original idea text provided by the user
        extra_context: Optional additional context as JSONB
        run_type: Whether this is an initial run or revision
        parent_run_id: Optional FK to parent run for revisions
        model: LLM model identifier used for this run
        temperature: Temperature parameter used for LLM calls
        parameters_json: Additional LLM parameters as JSONB
        overall_weighted_confidence: Final weighted confidence score (nullable until decision)
        decision_label: Final decision label (nullable until decision)
    """

    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, native_enum=False, length=20), nullable=False, default=RunStatus.RUNNING
    )
    input_idea: Mapped[str] = mapped_column(Text, nullable=False)
    extra_context: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    run_type: Mapped[RunType] = mapped_column(
        Enum(RunType, native_enum=False, length=20), nullable=False
    )
    parent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=True
    )
    model: Mapped[str] = mapped_column(Text, nullable=False)
    temperature: Mapped[float] = mapped_column(Numeric(precision=3, scale=2), nullable=False)
    parameters_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    overall_weighted_confidence: Mapped[float | None] = mapped_column(
        Numeric(precision=5, scale=4), nullable=True
    )
    decision_label: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    parent_run: Mapped["Run | None"] = relationship(
        "Run", remote_side=[id], back_populates="child_runs"
    )
    child_runs: Mapped[list["Run"]] = relationship(
        "Run", back_populates="parent_run", cascade="all, delete-orphan"
    )
    proposal_version: Mapped["ProposalVersion | None"] = relationship(
        "ProposalVersion", back_populates="run", cascade="all, delete-orphan", uselist=False
    )
    persona_reviews: Mapped[list["PersonaReview"]] = relationship(
        "PersonaReview", back_populates="run", cascade="all, delete-orphan"
    )
    decision: Mapped["Decision | None"] = relationship(
        "Decision", back_populates="run", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (
        Index("ix_runs_status", "status"),
        Index("ix_runs_parent_run_id", "parent_run_id"),
        Index("ix_runs_created_at", "created_at"),
        CheckConstraint(
            "temperature >= 0.0 AND temperature <= 2.0", name="ck_runs_temperature_range"
        ),
        CheckConstraint(
            "overall_weighted_confidence >= 0.0 AND overall_weighted_confidence <= 1.0",
            name="ck_runs_confidence_range",
        ),
    )

    def __repr__(self) -> str:
        """String representation of Run."""
        return (
            f"<Run(id={self.id}, status={self.status.value}, "
            f"run_type={self.run_type.value}, created_at={self.created_at})>"
        )


class ProposalVersion(Base):
    """Model for tracking proposal versions within a run.

    Each run generates a single proposal version from the expansion step.
    The proposal is stored as structured JSONB following the ExpandedProposal schema.

    Attributes:
        id: UUID primary key
        run_id: UUID foreign key to parent run (unique - one proposal per run)
        expanded_proposal_json: JSONB containing the structured proposal schema
        proposal_diff_json: Optional JSONB containing diff from parent proposal
        persona_template_version: Version identifier for persona templates used
        edit_notes: Optional notes about manual edits or adjustments
    """

    __tablename__ = "proposal_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    expanded_proposal_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    proposal_diff_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    persona_template_version: Mapped[str] = mapped_column(Text, nullable=False)
    edit_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    run: Mapped["Run"] = relationship("Run", back_populates="proposal_version")

    def __repr__(self) -> str:
        """String representation of ProposalVersion."""
        return (
            f"<ProposalVersion(id={self.id}, run_id={self.run_id}, "
            f"template_version={self.persona_template_version})>"
        )


class PersonaReview(Base):
    """Model for tracking individual persona reviews within a run.

    Each persona generates one review per run. Reviews capture the full
    PersonaReview schema as JSONB plus derived metrics for efficient queries.

    Attributes:
        id: UUID primary key
        run_id: UUID foreign key to parent run
        persona_id: Stable identifier for the persona (e.g., 'architect')
        persona_name: Display name for the persona
        review_json: JSONB containing the complete PersonaReview schema
        confidence_score: Numeric confidence score [0.0, 1.0] extracted for indexing
        blocking_issues_present: Boolean flag indicating presence of blocking issues
        security_concerns_present: Boolean flag indicating presence of security concerns
        prompt_parameters_json: JSONB containing model, temperature, persona version, retries
        created_at: Timestamp when review was created
    """

    __tablename__ = "persona_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False
    )
    persona_id: Mapped[str] = mapped_column(String(100), nullable=False)
    persona_name: Mapped[str] = mapped_column(Text, nullable=False)
    review_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[float] = mapped_column(
        Numeric(precision=5, scale=4), nullable=False
    )
    blocking_issues_present: Mapped[bool] = mapped_column(Boolean, nullable=False)
    security_concerns_present: Mapped[bool] = mapped_column(Boolean, nullable=False)
    prompt_parameters_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    run: Mapped["Run"] = relationship("Run", back_populates="persona_reviews")

    __table_args__ = (
        UniqueConstraint("run_id", "persona_id", name="uq_persona_reviews_run_persona"),
        CheckConstraint(
            "confidence_score >= 0.0 AND confidence_score <= 1.0",
            name="ck_persona_reviews_confidence_range",
        ),
    )

    def __repr__(self) -> str:
        """String representation of PersonaReview."""
        return (
            f"<PersonaReview(id={self.id}, run_id={self.run_id}, "
            f"persona_id={self.persona_id}, confidence={self.confidence_score})>"
        )


class Decision(Base):
    """Model for tracking final decisions for runs.

    Each run generates a single decision from the aggregation step.
    The decision is stored as structured JSONB following the DecisionAggregation schema.

    Attributes:
        id: UUID primary key
        run_id: UUID foreign key to parent run (unique - one decision per run)
        decision_json: JSONB containing the complete DecisionAggregation schema
        overall_weighted_confidence: Numeric weighted confidence extracted for indexing
        decision_notes: Optional notes about the decision or manual overrides
        created_at: Timestamp when decision was created
    """

    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    decision_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    overall_weighted_confidence: Mapped[float] = mapped_column(
        Numeric(precision=5, scale=4), nullable=False
    )
    decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    run: Mapped["Run"] = relationship("Run", back_populates="decision")

    __table_args__ = (
        Index("ix_decisions_overall_weighted_confidence", "overall_weighted_confidence"),
        CheckConstraint(
            "overall_weighted_confidence >= 0.0 AND overall_weighted_confidence <= 1.0",
            name="ck_decisions_confidence_range",
        ),
    )

    def __repr__(self) -> str:
        """String representation of Decision."""
        return (
            f"<Decision(id={self.id}, run_id={self.run_id}, "
            f"confidence={self.overall_weighted_confidence})>"
        )
