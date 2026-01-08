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
"""Integration tests for database functionality.

These tests require a running PostgreSQL instance.
They can be run against the Docker Compose database or a test database.
"""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Column, Integer, String, create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from consensus_engine.config import get_settings
from consensus_engine.db import (
    Base,
    check_database_health,
    create_engine_from_settings,
    create_session_factory,
    get_session,
)


# Skip integration tests if database is not available
def is_database_available():
    """Check if a test database is available."""
    try:
        test_url = os.getenv(
            "TEST_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
        )
        engine = create_engine(test_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


# Mark all tests in this module to be skipped if database is not available
pytestmark = pytest.mark.skipif(
    not is_database_available(), reason="Database not available for integration tests"
)


@pytest.fixture(scope="module")
def test_engine():
    """Create a test database engine."""
    test_url = os.getenv(
        "TEST_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
    )
    engine = create_engine(test_url, pool_pre_ping=True, echo=False)
    yield engine
    engine.dispose()


@pytest.fixture
def clean_database(test_engine):
    """Clean database before each test."""
    # Drop all tables
    Base.metadata.drop_all(test_engine)
    # Create all tables
    Base.metadata.create_all(test_engine)
    yield
    # Clean up after test
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def test_session_factory(test_engine):
    """Create a session factory for tests."""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def test_settings(monkeypatch):
    """Set up test settings with local database."""
    get_settings.cache_clear()

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")
    monkeypatch.setenv("USE_CLOUD_SQL_CONNECTOR", "false")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "postgres")
    monkeypatch.setenv("DB_USER", "postgres")
    monkeypatch.setenv("DB_PASSWORD", "postgres")

    return get_settings()


class TestDatabaseConnection:
    """Test database connection establishment."""

    def test_create_engine_from_settings(self, test_settings):
        """Test creating an engine from settings."""
        engine = create_engine_from_settings(test_settings)

        assert engine is not None
        assert check_database_health(engine)

        engine.dispose()

    def test_database_health_check_success(self, test_engine):
        """Test successful database health check."""
        result = check_database_health(test_engine)

        assert result is True

    def test_database_health_check_failure(self):
        """Test health check with invalid connection."""
        # Create engine with invalid connection
        bad_engine = create_engine(
            "postgresql+psycopg://invalid:invalid@localhost:9999/invalid", pool_pre_ping=False
        )

        result = check_database_health(bad_engine)

        assert result is False

        bad_engine.dispose()

    def test_connection_pooling(self, test_settings):
        """Test that connection pooling works correctly."""
        engine = create_engine_from_settings(test_settings)

        # Create multiple connections
        connections = []
        for _ in range(3):
            conn = engine.connect()
            connections.append(conn)

        # Verify all connections work
        for conn in connections:
            result = conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1

        # Close all connections
        for conn in connections:
            conn.close()

        engine.dispose()


class TestSessionManagement:
    """Test session management and operations."""

    def test_create_session_factory_from_engine(self, test_engine):
        """Test creating a session factory."""
        factory = create_session_factory(test_engine)

        assert factory is not None

        # Create a session
        session = factory()
        assert session is not None

        # Verify session can execute queries
        result = session.execute(text("SELECT 1"))
        assert result.fetchone()[0] == 1

        session.close()

    def test_get_session_context_manager(self, test_session_factory):
        """Test session context manager."""
        session_used = None

        for session in get_session(test_session_factory):
            session_used = session
            result = session.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1

        # Session should be closed after context
        assert session_used is not None
        # Note: We can't easily test if session is closed without internal access

    def test_session_transaction_commit(self, clean_database, test_session_factory):
        """Test session transaction commit."""

        # Define a test model
        class TestModel(Base):
            __tablename__ = "test_model"
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        # Create table
        Base.metadata.create_all(bind=test_session_factory.kw["bind"])

        # Insert data
        for session in get_session(test_session_factory):
            test_obj = TestModel(name="test")
            session.add(test_obj)
            session.commit()

        # Verify data persists
        for session in get_session(test_session_factory):
            result = session.query(TestModel).filter_by(name="test").first()
            assert result is not None
            assert result.name == "test"

    def test_session_transaction_rollback(self, clean_database, test_session_factory):
        """Test session transaction rollback."""

        # Define a test model
        class TestModel(Base):
            __tablename__ = "test_model_rollback"
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        # Create table
        Base.metadata.create_all(bind=test_session_factory.kw["bind"])

        # Insert data but rollback
        for session in get_session(test_session_factory):
            test_obj = TestModel(name="test")
            session.add(test_obj)
            session.rollback()

        # Verify data was not persisted
        for session in get_session(test_session_factory):
            result = session.query(TestModel).filter_by(name="test").first()
            assert result is None


class TestAlembicMigrations:
    """Test Alembic migration functionality."""

    def test_alembic_config_exists(self):
        """Test that Alembic configuration exists."""
        alembic_ini_path = Path(__file__).parent.parent.parent / "alembic.ini"
        assert alembic_ini_path.exists()

    def test_migrations_directory_exists(self):
        """Test that migrations directory exists."""
        migrations_dir = Path(__file__).parent.parent.parent / "migrations"
        assert migrations_dir.exists()
        assert (migrations_dir / "env.py").exists()

    def test_initial_migration_exists(self):
        """Test that initial migration exists."""
        migrations_dir = Path(__file__).parent.parent.parent / "migrations" / "versions"
        assert migrations_dir.exists()

        # Check that at least one migration file exists
        migration_files = list(migrations_dir.glob("*.py"))
        assert len(migration_files) > 0

    def test_run_migrations_up_and_down(self, test_engine, test_settings, monkeypatch):
        """Test running migrations up and down."""
        # Set up test database URL
        monkeypatch.setenv(
            "TEST_DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/postgres",
        )

        # Get alembic config
        alembic_ini_path = Path(__file__).parent.parent.parent / "alembic.ini"
        alembic_cfg = Config(str(alembic_ini_path))

        # Set the database URL in the config
        alembic_cfg.set_main_option("sqlalchemy.url", test_settings.database_url)

        try:
            # Run migrations to head (upgrade)
            command.upgrade(alembic_cfg, "head")

            # Check alembic version table exists
            with test_engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT EXISTS (SELECT FROM information_schema.tables "
                        "WHERE table_name = 'alembic_version')"
                    )
                )
                assert result.fetchone()[0] is True

            # Downgrade one revision
            command.downgrade(alembic_cfg, "-1")

            # Verify alembic version table still exists (we only went back one migration)
            with test_engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT EXISTS (SELECT FROM information_schema.tables "
                        "WHERE table_name = 'alembic_version')"
                    )
                )
                # Table should still exist after downgrade of empty migration
                assert result.fetchone()[0] is True

        except (OperationalError, OSError) as e:
            # OperationalError: Database connection/query issues
            # OSError: File system or network issues
            pytest.skip(f"Migration test requires database connection: {e}")
        except Exception as e:
            # Re-raise unexpected errors to surface them properly
            pytest.fail(f"Unexpected error in migration test: {e}")


class TestDatabaseModels:
    """Test database model functionality."""

    def test_base_metadata(self, clean_database, test_engine):
        """Test Base metadata operations."""

        # Create a test model
        class TestModel(Base):
            __tablename__ = "test_metadata_model"
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        # Create tables
        Base.metadata.create_all(test_engine)

        # Verify table was created
        with test_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_name = 'test_metadata_model')"
                )
            )
            assert result.fetchone()[0] is True

        # Drop tables
        Base.metadata.drop_all(test_engine)

        # Verify table was dropped
        with test_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_name = 'test_metadata_model')"
                )
            )
            assert result.fetchone()[0] is False


class TestVersionedRunModels:
    """Test versioned run models with database operations."""

    def test_create_run_with_all_fields(self, clean_database, test_session_factory):
        """Test creating a run with all fields."""
        import uuid

        from consensus_engine.db.models import Run, RunStatus, RunType

        for session in get_session(test_session_factory):
            run = Run(
                user_id=uuid.uuid4(),
                status=RunStatus.RUNNING,
                input_idea="Build a scalable API",
                extra_context={"priority": "high", "deadline": "2024-12-31"},
                run_type=RunType.INITIAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={"max_tokens": 1000, "top_p": 0.9},
            )
            session.add(run)
            session.commit()
            run_id = run.id

        # Verify run was created
        for session in get_session(test_session_factory):
            result = session.query(Run).filter_by(id=run_id).first()
            assert result is not None
            assert result.input_idea == "Build a scalable API"
            assert result.status == RunStatus.RUNNING
            assert result.run_type == RunType.INITIAL
            assert result.model == "gpt-5.1"
            assert float(result.temperature) == 0.7
            assert result.parameters_json["max_tokens"] == 1000
            assert result.extra_context["priority"] == "high"

    def test_create_run_with_parent(self, clean_database, test_session_factory):
        """Test creating a revision run with parent."""
        from consensus_engine.db.models import Run, RunStatus, RunType

        parent_run_id = None
        child_run_id = None

        for session in get_session(test_session_factory):
            # Create parent run
            parent = Run(
                status=RunStatus.COMPLETED,
                input_idea="Original idea",
                run_type=RunType.INITIAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
            )
            session.add(parent)
            session.commit()
            parent_run_id = parent.id

            # Create child run
            child = Run(
                status=RunStatus.RUNNING,
                input_idea="Revised idea",
                run_type=RunType.REVISION,
                parent_run_id=parent_run_id,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
            )
            session.add(child)
            session.commit()
            child_run_id = child.id

        # Verify parent-child relationship
        for session in get_session(test_session_factory):
            child = session.query(Run).filter_by(id=child_run_id).first()
            assert child.parent_run_id == parent_run_id
            assert child.run_type == RunType.REVISION

    def test_create_proposal_version(self, clean_database, test_session_factory):
        """Test creating a proposal version."""
        from consensus_engine.db.models import ProposalVersion, Run, RunStatus, RunType

        run_id = None

        for session in get_session(test_session_factory):
            # Create run
            run = Run(
                status=RunStatus.RUNNING,
                input_idea="Test",
                run_type=RunType.INITIAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
            )
            session.add(run)
            session.commit()
            run_id = run.id

            # Create proposal
            proposal = ProposalVersion(
                run_id=run_id,
                expanded_proposal_json={
                    "problem_statement": "Build a scalable API",
                    "proposed_solution": "Use FastAPI with async handlers",
                    "assumptions": ["Python 3.11+"],
                    "scope_non_goals": ["Mobile app"],
                },
                persona_template_version="v1.0",
                edit_notes="Initial expansion",
            )
            session.add(proposal)
            session.commit()

        # Verify proposal was created
        for session in get_session(test_session_factory):
            result = session.query(ProposalVersion).filter_by(run_id=run_id).first()
            assert result is not None
            assert result.expanded_proposal_json["problem_statement"] == "Build a scalable API"
            assert result.persona_template_version == "v1.0"
            assert result.edit_notes == "Initial expansion"

    def test_create_persona_reviews(self, clean_database, test_session_factory):
        """Test creating multiple persona reviews for a run."""
        from consensus_engine.db.models import PersonaReview, Run, RunStatus, RunType

        run_id = None

        for session in get_session(test_session_factory):
            # Create run
            run = Run(
                status=RunStatus.RUNNING,
                input_idea="Test",
                run_type=RunType.INITIAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
            )
            session.add(run)
            session.commit()
            run_id = run.id

            # Create multiple reviews
            reviews_data = [
                ("architect", "Architect", 0.85, False, False),
                ("critic", "Critic", 0.65, True, False),
                ("security_guardian", "Security Guardian", 0.70, False, True),
            ]

            for persona_id, persona_name, confidence, blocking, security in reviews_data:
                review = PersonaReview(
                    run_id=run_id,
                    persona_id=persona_id,
                    persona_name=persona_name,
                    review_json={
                        "confidence_score": confidence,
                        "strengths": ["Good design"],
                        "concerns": [],
                    },
                    confidence_score=confidence,
                    blocking_issues_present=blocking,
                    security_concerns_present=security,
                    prompt_parameters_json={
                        "model": "gpt-5.1",
                        "temperature": 0.2,
                        "version": "v1.0",
                    },
                )
                session.add(review)
            session.commit()

        # Verify reviews were created
        for session in get_session(test_session_factory):
            results = session.query(PersonaReview).filter_by(run_id=run_id).all()
            assert len(results) == 3
            persona_ids = [r.persona_id for r in results]
            assert "architect" in persona_ids
            assert "critic" in persona_ids
            assert "security_guardian" in persona_ids

    def test_persona_review_unique_constraint(self, clean_database, test_session_factory):
        """Test that unique constraint prevents duplicate persona reviews."""
        from sqlalchemy.exc import IntegrityError

        from consensus_engine.db.models import PersonaReview, Run, RunStatus, RunType

        for session in get_session(test_session_factory):
            # Create run
            run = Run(
                status=RunStatus.RUNNING,
                input_idea="Test",
                run_type=RunType.INITIAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
            )
            session.add(run)
            session.commit()
            run_id = run.id

            # Create first review
            review1 = PersonaReview(
                run_id=run_id,
                persona_id="architect",
                persona_name="Architect",
                review_json={},
                confidence_score=0.8,
                blocking_issues_present=False,
                security_concerns_present=False,
                prompt_parameters_json={},
            )
            session.add(review1)
            session.commit()

            # Try to create duplicate review - should fail
            review2 = PersonaReview(
                run_id=run_id,
                persona_id="architect",  # Same persona_id
                persona_name="Architect",
                review_json={},
                confidence_score=0.9,
                blocking_issues_present=False,
                security_concerns_present=False,
                prompt_parameters_json={},
            )
            session.add(review2)

            with pytest.raises(IntegrityError):
                session.commit()

    def test_create_decision(self, clean_database, test_session_factory):
        """Test creating a decision."""
        from consensus_engine.db.models import Decision, Run, RunStatus, RunType

        run_id = None

        for session in get_session(test_session_factory):
            # Create run
            run = Run(
                status=RunStatus.RUNNING,
                input_idea="Test",
                run_type=RunType.INITIAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
            )
            session.add(run)
            session.commit()
            run_id = run.id

            # Create decision
            decision = Decision(
                run_id=run_id,
                decision_json={
                    "decision": "approve",
                    "overall_weighted_confidence": 0.85,
                    "score_breakdown": {},
                },
                overall_weighted_confidence=0.85,
                decision_notes="All personas agreed",
            )
            session.add(decision)
            session.commit()

        # Verify decision was created
        for session in get_session(test_session_factory):
            result = session.query(Decision).filter_by(run_id=run_id).first()
            assert result is not None
            assert float(result.overall_weighted_confidence) == 0.85
            assert result.decision_json["decision"] == "approve"
            assert result.decision_notes == "All personas agreed"

    def test_cascade_delete_run(self, clean_database, test_session_factory):
        """Test that deleting a run cascades to related records."""
        from consensus_engine.db.models import (
            Decision,
            PersonaReview,
            ProposalVersion,
            Run,
            RunStatus,
            RunType,
        )

        run_id = None

        for session in get_session(test_session_factory):
            # Create run with all related records
            run = Run(
                status=RunStatus.COMPLETED,
                input_idea="Test",
                run_type=RunType.INITIAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
            )
            session.add(run)
            session.commit()
            run_id = run.id

            # Add proposal
            proposal = ProposalVersion(
                run_id=run_id,
                expanded_proposal_json={},
                persona_template_version="v1.0",
            )
            session.add(proposal)

            # Add review
            review = PersonaReview(
                run_id=run_id,
                persona_id="architect",
                persona_name="Architect",
                review_json={},
                confidence_score=0.8,
                blocking_issues_present=False,
                security_concerns_present=False,
                prompt_parameters_json={},
            )
            session.add(review)

            # Add decision
            decision = Decision(
                run_id=run_id,
                decision_json={},
                overall_weighted_confidence=0.85,
            )
            session.add(decision)
            session.commit()

        # Verify all records exist
        for session in get_session(test_session_factory):
            assert session.query(Run).filter_by(id=run_id).first() is not None
            assert session.query(ProposalVersion).filter_by(run_id=run_id).first() is not None
            assert session.query(PersonaReview).filter_by(run_id=run_id).first() is not None
            assert session.query(Decision).filter_by(run_id=run_id).first() is not None

        # Delete run
        for session in get_session(test_session_factory):
            run = session.query(Run).filter_by(id=run_id).first()
            session.delete(run)
            session.commit()

        # Verify all related records were deleted
        for session in get_session(test_session_factory):
            assert session.query(Run).filter_by(id=run_id).first() is None
            assert session.query(ProposalVersion).filter_by(run_id=run_id).first() is None
            assert session.query(PersonaReview).filter_by(run_id=run_id).first() is None
            assert session.query(Decision).filter_by(run_id=run_id).first() is None

    def test_query_by_indexes(self, clean_database, test_session_factory):
        """Test querying by indexed columns."""
        from consensus_engine.db.models import Decision, Run, RunStatus, RunType

        for session in get_session(test_session_factory):
            # Create multiple runs with different statuses
            run1 = Run(
                status=RunStatus.RUNNING,
                input_idea="Test 1",
                run_type=RunType.INITIAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
            )
            run2 = Run(
                status=RunStatus.COMPLETED,
                input_idea="Test 2",
                run_type=RunType.INITIAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
            )
            session.add_all([run1, run2])
            session.commit()

            # Query by status (indexed)
            running_runs = session.query(Run).filter(Run.status == RunStatus.RUNNING).all()
            assert len(running_runs) == 1
            assert running_runs[0].input_idea == "Test 1"

            completed_runs = session.query(Run).filter(Run.status == RunStatus.COMPLETED).all()
            assert len(completed_runs) == 1
            assert completed_runs[0].input_idea == "Test 2"

            # Create decisions and query by confidence (indexed)
            decision1 = Decision(
                run_id=run1.id,
                decision_json={},
                overall_weighted_confidence=0.75,
            )
            decision2 = Decision(
                run_id=run2.id,
                decision_json={},
                overall_weighted_confidence=0.95,
            )
            session.add_all([decision1, decision2])
            session.commit()

            # Query decisions with high confidence
            high_confidence = (
                session.query(Decision)
                .filter(Decision.overall_weighted_confidence >= 0.90)
                .all()
            )
            assert len(high_confidence) == 1
            assert float(high_confidence[0].overall_weighted_confidence) == 0.95


class TestStepProgressRepository:
    """Test StepProgressRepository functionality with database."""

    def test_upsert_step_progress_create(self, clean_database, test_session_factory):
        """Test creating a new step progress record."""
        from datetime import UTC, datetime
        from consensus_engine.db.models import Run, RunPriority, RunStatus, RunType, StepStatus
        from consensus_engine.db.repositories import StepProgressRepository

        for session in get_session(test_session_factory):
            # Create a run first
            run = Run(
                status=RunStatus.QUEUED,
                input_idea="Test idea",
                run_type=RunType.INITIAL,
                priority=RunPriority.NORMAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
            )
            session.add(run)
            session.commit()
            run_id = run.id

            # Create step progress
            started = datetime.now(UTC)
            step = StepProgressRepository.upsert_step_progress(
                session=session,
                run_id=run_id,
                step_name="expand",
                status=StepStatus.RUNNING,
                started_at=started,
            )

            session.commit()

            assert step.run_id == run_id
            assert step.step_name == "expand"
            assert step.step_order == 0
            assert step.status == StepStatus.RUNNING
            assert step.started_at == started
            assert step.completed_at is None
            assert step.error_message is None

    def test_upsert_step_progress_update(self, clean_database, test_session_factory):
        """Test updating an existing step progress record (idempotent)."""
        from datetime import UTC, datetime
        from consensus_engine.db.models import Run, RunPriority, RunStatus, RunType, StepStatus
        from consensus_engine.db.repositories import StepProgressRepository

        for session in get_session(test_session_factory):
            # Create a run
            run = Run(
                status=RunStatus.RUNNING,
                input_idea="Test idea",
                run_type=RunType.INITIAL,
                priority=RunPriority.NORMAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
            )
            session.add(run)
            session.commit()
            run_id = run.id

            # Create initial step progress
            started = datetime.now(UTC)
            step1 = StepProgressRepository.upsert_step_progress(
                session=session,
                run_id=run_id,
                step_name="expand",
                status=StepStatus.RUNNING,
                started_at=started,
            )
            session.commit()
            step_id = step1.id

            # Update the same step (idempotent)
            completed = datetime.now(UTC)
            step2 = StepProgressRepository.upsert_step_progress(
                session=session,
                run_id=run_id,
                step_name="expand",
                status=StepStatus.COMPLETED,
                completed_at=completed,
            )
            session.commit()

            # Should be the same record, not a duplicate
            assert step2.id == step_id
            assert step2.status == StepStatus.COMPLETED
            assert step2.completed_at == completed
            assert step2.started_at == started

    def test_upsert_step_progress_clears_error_on_success(self, clean_database, test_session_factory):
        """Test that error messages are cleared when step succeeds after failure."""
        from datetime import UTC, datetime
        from consensus_engine.db.models import Run, RunPriority, RunStatus, RunType, StepStatus
        from consensus_engine.db.repositories import StepProgressRepository

        for session in get_session(test_session_factory):
            # Create a run
            run = Run(
                status=RunStatus.RUNNING,
                input_idea="Test idea",
                run_type=RunType.INITIAL,
                priority=RunPriority.NORMAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
            )
            session.add(run)
            session.commit()
            run_id = run.id

            # Create step progress that fails
            started = datetime.now(UTC)
            step1 = StepProgressRepository.upsert_step_progress(
                session=session,
                run_id=run_id,
                step_name="expand",
                status=StepStatus.FAILED,
                started_at=started,
                error_message="API timeout",
            )
            session.commit()
            step_id = step1.id

            # Verify error message is set
            assert step1.error_message == "API timeout"

            # Retry and succeed - error message should be cleared
            completed = datetime.now(UTC)
            step2 = StepProgressRepository.upsert_step_progress(
                session=session,
                run_id=run_id,
                step_name="expand",
                status=StepStatus.COMPLETED,
                completed_at=completed,
            )
            session.commit()

            # Should be the same record with error cleared
            assert step2.id == step_id
            assert step2.status == StepStatus.COMPLETED
            assert step2.error_message is None

            # Test that error message is preserved when status is FAILED
            step3 = StepProgressRepository.upsert_step_progress(
                session=session,
                run_id=run_id,
                step_name="expand",
                status=StepStatus.FAILED,
                error_message="New error",
            )
            session.commit()

            assert step3.id == step_id
            assert step3.error_message == "New error"

    def test_upsert_step_progress_invalid_step_name(self, clean_database, test_session_factory):
        """Test that invalid step names are rejected."""
        from consensus_engine.db.models import Run, RunPriority, RunStatus, RunType, StepStatus
        from consensus_engine.db.repositories import StepProgressRepository

        for session in get_session(test_session_factory):
            # Create a run
            run = Run(
                status=RunStatus.RUNNING,
                input_idea="Test idea",
                run_type=RunType.INITIAL,
                priority=RunPriority.NORMAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
            )
            session.add(run)
            session.commit()

            # Try to create step with invalid name
            with pytest.raises(ValueError, match="Invalid step_name"):
                StepProgressRepository.upsert_step_progress(
                    session=session,
                    run_id=run.id,
                    step_name="invalid_step",
                    status=StepStatus.PENDING,
                )

    def test_get_run_steps(self, clean_database, test_session_factory):
        """Test retrieving all steps for a run in order."""
        from consensus_engine.db.models import Run, RunPriority, RunStatus, RunType, StepStatus
        from consensus_engine.db.repositories import StepProgressRepository

        for session in get_session(test_session_factory):
            # Create a run
            run = Run(
                status=RunStatus.RUNNING,
                input_idea="Test idea",
                run_type=RunType.INITIAL,
                priority=RunPriority.NORMAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
            )
            session.add(run)
            session.commit()
            run_id = run.id

            # Create multiple steps out of order
            StepProgressRepository.upsert_step_progress(
                session, run_id, "aggregate_decision", StepStatus.PENDING
            )
            StepProgressRepository.upsert_step_progress(
                session, run_id, "expand", StepStatus.COMPLETED
            )
            StepProgressRepository.upsert_step_progress(
                session, run_id, "review_architect", StepStatus.RUNNING
            )
            session.commit()

            # Retrieve steps - should be ordered by step_order
            steps = StepProgressRepository.get_run_steps(session, run_id)

            assert len(steps) == 3
            assert steps[0].step_name == "expand"
            assert steps[0].step_order == 0
            assert steps[1].step_name == "review_architect"
            assert steps[1].step_order == 1
            assert steps[2].step_name == "aggregate_decision"
            assert steps[2].step_order == 6

    def test_step_progress_cascade_delete(self, clean_database, test_session_factory):
        """Test that step progress records are deleted when run is deleted."""
        from consensus_engine.db.models import Run, RunPriority, RunStatus, RunType, StepProgress, StepStatus
        from consensus_engine.db.repositories import StepProgressRepository

        for session in get_session(test_session_factory):
            # Create a run with steps
            run = Run(
                status=RunStatus.RUNNING,
                input_idea="Test idea",
                run_type=RunType.INITIAL,
                priority=RunPriority.NORMAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
            )
            session.add(run)
            session.commit()
            run_id = run.id

            # Create step progress
            StepProgressRepository.upsert_step_progress(
                session, run_id, "expand", StepStatus.COMPLETED
            )
            session.commit()

            # Verify step exists
            steps_before = session.query(StepProgress).filter_by(run_id=run_id).all()
            assert len(steps_before) == 1

            # Delete run
            session.delete(run)
            session.commit()

            # Verify steps were cascade deleted
            steps_after = session.query(StepProgress).filter_by(run_id=run_id).all()
            assert len(steps_after) == 0

    def test_valid_step_names(self):
        """Test that all expected step names are in the valid list."""
        from consensus_engine.db.repositories import StepProgressRepository

        valid_steps = StepProgressRepository.VALID_STEP_NAMES
        assert "expand" in valid_steps
        assert "review_architect" in valid_steps
        assert "review_critic" in valid_steps
        assert "review_optimist" in valid_steps
        assert "review_security" in valid_steps
        assert "review_user_advocate" in valid_steps
        assert "aggregate_decision" in valid_steps

    def test_get_step_order(self):
        """Test getting step order for valid step names."""
        from consensus_engine.db.repositories import StepProgressRepository

        assert StepProgressRepository.get_step_order("expand") == 0
        assert StepProgressRepository.get_step_order("review_architect") == 1
        assert StepProgressRepository.get_step_order("aggregate_decision") == 6

        with pytest.raises(ValueError):
            StepProgressRepository.get_step_order("invalid_step")

