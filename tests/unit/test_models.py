"""Unit tests for database models."""

import uuid

from consensus_engine.db.models import (
    Decision,
    PersonaReview,
    ProposalVersion,
    Run,
    RunStatus,
    RunType,
)


class TestRunModel:
    """Test Run model."""

    def test_run_model_creation(self):
        """Test creating a Run instance."""
        run_id = uuid.uuid4()
        run = Run(
            id=run_id,
            status=RunStatus.RUNNING,
            input_idea="Build a scalable API",
            run_type=RunType.INITIAL,
            model="gpt-5.1",
            temperature=0.7,
            parameters_json={"max_tokens": 1000},
        )

        assert run.id == run_id
        assert run.status == RunStatus.RUNNING
        assert run.input_idea == "Build a scalable API"
        assert run.run_type == RunType.INITIAL
        assert run.model == "gpt-5.1"
        assert run.temperature == 0.7
        assert run.parameters_json == {"max_tokens": 1000}
        assert run.parent_run_id is None
        assert run.user_id is None
        assert run.extra_context is None

    def test_run_model_with_optional_fields(self):
        """Test creating a Run with optional fields."""
        run_id = uuid.uuid4()
        user_id = uuid.uuid4()
        parent_run_id = uuid.uuid4()

        run = Run(
            id=run_id,
            user_id=user_id,
            status=RunStatus.COMPLETED,
            input_idea="Improve the API",
            extra_context={"priority": "high"},
            run_type=RunType.REVISION,
            parent_run_id=parent_run_id,
            model="gpt-5.1",
            temperature=0.5,
            parameters_json={"max_tokens": 2000},
            overall_weighted_confidence=0.85,
            decision_label="approve",
        )

        assert run.user_id == user_id
        assert run.extra_context == {"priority": "high"}
        assert run.parent_run_id == parent_run_id
        assert run.overall_weighted_confidence == 0.85
        assert run.decision_label == "approve"

    def test_run_model_repr(self):
        """Test Run string representation."""
        run = Run(
            status=RunStatus.RUNNING,
            input_idea="Test",
            run_type=RunType.INITIAL,
            model="gpt-5.1",
            temperature=0.7,
            parameters_json={},
        )

        repr_str = repr(run)
        assert "Run" in repr_str
        assert "running" in repr_str
        assert "initial" in repr_str

    def test_run_status_enum(self):
        """Test RunStatus enum values."""
        assert RunStatus.RUNNING.value == "running"
        assert RunStatus.COMPLETED.value == "completed"
        assert RunStatus.FAILED.value == "failed"

    def test_run_type_enum(self):
        """Test RunType enum values."""
        assert RunType.INITIAL.value == "initial"
        assert RunType.REVISION.value == "revision"


class TestProposalVersionModel:
    """Test ProposalVersion model."""

    def test_proposal_version_creation(self):
        """Test creating a ProposalVersion instance."""
        proposal_id = uuid.uuid4()
        run_id = uuid.uuid4()

        proposal = ProposalVersion(
            id=proposal_id,
            run_id=run_id,
            expanded_proposal_json={
                "problem_statement": "Build API",
                "proposed_solution": "Use FastAPI",
                "assumptions": ["Python 3.11+"],
                "scope_non_goals": ["Mobile app"],
            },
            persona_template_version="v1.0",
        )

        assert proposal.id == proposal_id
        assert proposal.run_id == run_id
        assert proposal.expanded_proposal_json["problem_statement"] == "Build API"
        assert proposal.persona_template_version == "v1.0"
        assert proposal.proposal_diff_json is None
        assert proposal.edit_notes is None

    def test_proposal_version_with_optional_fields(self):
        """Test creating ProposalVersion with optional fields."""
        proposal = ProposalVersion(
            run_id=uuid.uuid4(),
            expanded_proposal_json={"problem_statement": "Test"},
            proposal_diff_json={"added": ["new field"]},
            persona_template_version="v1.0",
            edit_notes="Manual adjustment to scope",
        )

        assert proposal.proposal_diff_json == {"added": ["new field"]}
        assert proposal.edit_notes == "Manual adjustment to scope"

    def test_proposal_version_repr(self):
        """Test ProposalVersion string representation."""
        run_id = uuid.uuid4()
        proposal = ProposalVersion(
            run_id=run_id,
            expanded_proposal_json={},
            persona_template_version="v2.0",
        )

        repr_str = repr(proposal)
        assert "ProposalVersion" in repr_str
        assert str(run_id) in repr_str
        assert "v2.0" in repr_str


class TestPersonaReviewModel:
    """Test PersonaReview model."""

    def test_persona_review_creation(self):
        """Test creating a PersonaReview instance."""
        review_id = uuid.uuid4()
        run_id = uuid.uuid4()

        review = PersonaReview(
            id=review_id,
            run_id=run_id,
            persona_id="architect",
            persona_name="Architect",
            review_json={
                "confidence_score": 0.8,
                "strengths": ["Good design"],
                "concerns": [],
            },
            confidence_score=0.8,
            blocking_issues_present=False,
            security_concerns_present=False,
            prompt_parameters_json={
                "model": "gpt-5.1",
                "temperature": 0.2,
                "version": "v1.0",
            },
        )

        assert review.id == review_id
        assert review.run_id == run_id
        assert review.persona_id == "architect"
        assert review.persona_name == "Architect"
        assert review.confidence_score == 0.8
        assert review.blocking_issues_present is False
        assert review.security_concerns_present is False
        assert review.prompt_parameters_json["model"] == "gpt-5.1"

    def test_persona_review_with_blocking_issues(self):
        """Test PersonaReview with blocking issues."""
        review = PersonaReview(
            run_id=uuid.uuid4(),
            persona_id="security_guardian",
            persona_name="Security Guardian",
            review_json={
                "blocking_issues": [{"text": "SQL injection risk"}]
            },
            confidence_score=0.4,
            blocking_issues_present=True,
            security_concerns_present=True,
            prompt_parameters_json={},
        )

        assert review.blocking_issues_present is True
        assert review.security_concerns_present is True

    def test_persona_review_repr(self):
        """Test PersonaReview string representation."""
        run_id = uuid.uuid4()
        review = PersonaReview(
            run_id=run_id,
            persona_id="critic",
            persona_name="Critic",
            review_json={},
            confidence_score=0.65,
            blocking_issues_present=False,
            security_concerns_present=False,
            prompt_parameters_json={},
        )

        repr_str = repr(review)
        assert "PersonaReview" in repr_str
        assert str(run_id) in repr_str
        assert "critic" in repr_str
        assert "0.65" in repr_str


class TestDecisionModel:
    """Test Decision model."""

    def test_decision_creation(self):
        """Test creating a Decision instance."""
        decision_id = uuid.uuid4()
        run_id = uuid.uuid4()

        decision = Decision(
            id=decision_id,
            run_id=run_id,
            decision_json={
                "decision": "approve",
                "overall_weighted_confidence": 0.85,
                "score_breakdown": {},
            },
            overall_weighted_confidence=0.85,
        )

        assert decision.id == decision_id
        assert decision.run_id == run_id
        assert decision.overall_weighted_confidence == 0.85
        assert decision.decision_json["decision"] == "approve"
        assert decision.decision_notes is None

    def test_decision_with_notes(self):
        """Test Decision with notes."""
        decision = Decision(
            run_id=uuid.uuid4(),
            decision_json={"decision": "revise"},
            overall_weighted_confidence=0.72,
            decision_notes="Security concerns need addressing",
        )

        assert decision.decision_notes == "Security concerns need addressing"

    def test_decision_repr(self):
        """Test Decision string representation."""
        run_id = uuid.uuid4()
        decision = Decision(
            run_id=run_id,
            decision_json={},
            overall_weighted_confidence=0.90,
        )

        repr_str = repr(decision)
        assert "Decision" in repr_str
        assert str(run_id) in repr_str
        assert "0.9" in repr_str


class TestModelRelationships:
    """Test relationships between models."""

    def test_run_to_proposal_version_relationship(self):
        """Test Run to ProposalVersion relationship setup."""
        run = Run(
            status=RunStatus.RUNNING,
            input_idea="Test",
            run_type=RunType.INITIAL,
            model="gpt-5.1",
            temperature=0.7,
            parameters_json={},
        )

        # Test that relationship attributes exist
        assert hasattr(run, "proposal_version")
        assert hasattr(run, "persona_reviews")
        assert hasattr(run, "decision")
        assert hasattr(run, "parent_run")
        assert hasattr(run, "child_runs")

    def test_proposal_version_to_run_relationship(self):
        """Test ProposalVersion to Run relationship setup."""
        proposal = ProposalVersion(
            run_id=uuid.uuid4(),
            expanded_proposal_json={},
            persona_template_version="v1.0",
        )

        # Test that relationship attribute exists
        assert hasattr(proposal, "run")

    def test_persona_review_to_run_relationship(self):
        """Test PersonaReview to Run relationship setup."""
        review = PersonaReview(
            run_id=uuid.uuid4(),
            persona_id="architect",
            persona_name="Architect",
            review_json={},
            confidence_score=0.8,
            blocking_issues_present=False,
            security_concerns_present=False,
            prompt_parameters_json={},
        )

        # Test that relationship attribute exists
        assert hasattr(review, "run")

    def test_decision_to_run_relationship(self):
        """Test Decision to Run relationship setup."""
        decision = Decision(
            run_id=uuid.uuid4(),
            decision_json={},
            overall_weighted_confidence=0.85,
        )

        # Test that relationship attribute exists
        assert hasattr(decision, "run")


class TestModelValidation:
    """Test model validation and constraints."""

    def test_run_model_has_table_constraints(self):
        """Test that Run model has expected constraints."""
        # Check that __table_args__ is defined
        assert hasattr(Run, "__table_args__")
        table_args = Run.__table_args__

        # Verify indexes exist
        index_names = [idx.name for idx in table_args if hasattr(idx, "name")]
        assert "ix_runs_status" in index_names
        assert "ix_runs_parent_run_id" in index_names
        assert "ix_runs_created_at" in index_names

        # Verify check constraints exist
        constraint_names = [
            constraint.name
            for constraint in table_args
            if hasattr(constraint, "name") and "ck_" in str(constraint.name)
        ]
        assert "ck_runs_temperature_range" in constraint_names
        assert "ck_runs_confidence_range" in constraint_names

    def test_persona_review_has_unique_constraint(self):
        """Test that PersonaReview has unique constraint."""
        assert hasattr(PersonaReview, "__table_args__")
        table_args = PersonaReview.__table_args__

        constraint_names = [
            constraint.name
            for constraint in table_args
            if hasattr(constraint, "name")
        ]
        assert "uq_persona_reviews_run_persona" in constraint_names

    def test_decision_has_index(self):
        """Test that Decision model has expected index."""
        assert hasattr(Decision, "__table_args__")
        table_args = Decision.__table_args__

        index_names = [idx.name for idx in table_args if hasattr(idx, "name")]
        assert "ix_decisions_overall_weighted_confidence" in index_names


class TestModelDefaultValues:
    """Test model default values."""

    def test_run_default_id_column_has_default(self):
        """Test that Run id column has default configured."""
        # UUID defaults are set at insert time by the database or ORM
        # Verify that the column has a default callable configured
        id_column = Run.__table__.columns["id"]
        assert id_column.default is not None
        # When an explicit ID is provided, it should be used
        explicit_id = uuid.uuid4()
        run = Run(
            id=explicit_id,
            status=RunStatus.RUNNING,
            input_idea="Test",
            run_type=RunType.INITIAL,
            model="gpt-5.1",
            temperature=0.7,
            parameters_json={},
        )
        assert run.id == explicit_id

    def test_proposal_version_default_id_column_has_default(self):
        """Test that ProposalVersion id column has default configured."""
        id_column = ProposalVersion.__table__.columns["id"]
        assert id_column.default is not None
        # When an explicit ID is provided, it should be used
        explicit_id = uuid.uuid4()
        proposal = ProposalVersion(
            id=explicit_id,
            run_id=uuid.uuid4(),
            expanded_proposal_json={},
            persona_template_version="v1.0",
        )
        assert proposal.id == explicit_id

    def test_persona_review_default_id_column_has_default(self):
        """Test that PersonaReview id column has default configured."""
        id_column = PersonaReview.__table__.columns["id"]
        assert id_column.default is not None
        # When an explicit ID is provided, it should be used
        explicit_id = uuid.uuid4()
        review = PersonaReview(
            id=explicit_id,
            run_id=uuid.uuid4(),
            persona_id="architect",
            persona_name="Architect",
            review_json={},
            confidence_score=0.8,
            blocking_issues_present=False,
            security_concerns_present=False,
            prompt_parameters_json={},
        )
        assert review.id == explicit_id

    def test_decision_default_id_column_has_default(self):
        """Test that Decision id column has default configured."""
        id_column = Decision.__table__.columns["id"]
        assert id_column.default is not None
        # When an explicit ID is provided, it should be used
        explicit_id = uuid.uuid4()
        decision = Decision(
            id=explicit_id,
            run_id=uuid.uuid4(),
            decision_json={},
            overall_weighted_confidence=0.85,
        )
        assert decision.id == explicit_id


class TestTableNames:
    """Test that table names are correctly defined."""

    def test_run_table_name(self):
        """Test Run table name."""
        assert Run.__tablename__ == "runs"

    def test_proposal_version_table_name(self):
        """Test ProposalVersion table name."""
        assert ProposalVersion.__tablename__ == "proposal_versions"

    def test_persona_review_table_name(self):
        """Test PersonaReview table name."""
        assert PersonaReview.__tablename__ == "persona_reviews"

    def test_decision_table_name(self):
        """Test Decision table name."""
        assert Decision.__tablename__ == "decisions"
