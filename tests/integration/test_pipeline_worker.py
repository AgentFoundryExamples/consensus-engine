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
"""Integration tests for pipeline worker.

These tests require a PostgreSQL database to run.
If no database is available, tests will be skipped.
"""

import json
import os
import uuid
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from consensus_engine.config.settings import Settings
from consensus_engine.db import Base
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
from consensus_engine.db.repositories import (
    RunRepository,
    StepProgressRepository,
)
from consensus_engine.workers.pipeline_worker import JobMessage, PipelineWorker


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


@pytest.fixture
def test_db_engine():
    """Create test database engine."""
    test_url = os.getenv(
        "TEST_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
    )
    engine = create_engine(test_url, pool_pre_ping=True, echo=False)
    # Clean database before each test
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    # Clean up after test
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def test_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Create test settings."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-integration")
    monkeypatch.setenv("PUBSUB_USE_MOCK", "true")
    monkeypatch.setenv("PUBSUB_EMULATOR_HOST", "localhost:8085")
    monkeypatch.setenv("PUBSUB_PROJECT_ID", "test-project")
    monkeypatch.setenv("PUBSUB_SUBSCRIPTION", "test-sub")
    return Settings()


class TestPipelineWorkerIntegration:
    """Integration tests for PipelineWorker."""

    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    @patch("consensus_engine.workers.pipeline_worker.expand_idea")
    @patch("consensus_engine.workers.pipeline_worker.review_with_all_personas")
    @patch("consensus_engine.workers.pipeline_worker.aggregate_persona_reviews")
    def test_full_pipeline_execution_initial(
        self,
        mock_aggregate: Mock,
        mock_review: Mock,
        mock_expand: Mock,
        mock_get_engine: Mock,
        mock_subscriber_cls: Mock,
        test_db_engine,
        test_settings: Settings,
    ):
        """Test full pipeline execution for initial run."""
        # Set up database
        mock_get_engine.return_value = test_db_engine

        # Set up worker
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        worker = PipelineWorker(test_settings)
        worker.engine = test_db_engine

        # Create test run in database
        with Session(test_db_engine) as session:
            run_id = uuid.uuid4()
            run = RunRepository.create_run(
                session=session,
                run_id=run_id,
                input_idea="Test idea for integration",
                extra_context={"test": "context"},
                run_type=RunType.INITIAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
                priority=RunPriority.NORMAL,
                status=RunStatus.QUEUED,
            )
            
            # Initialize step progress
            for step_name in [
                "expand",
                "review_architect",
                "review_critic",
                "review_optimist",
                "review_security",
                "review_user_advocate",
                "aggregate_decision",
            ]:
                StepProgressRepository.upsert_step_progress(
                    session=session,
                    run_id=run_id,
                    step_name=step_name,
                    status=StepStatus.PENDING,
                )
            
            session.commit()

        # Mock expand service
        from consensus_engine.schemas.proposal import ExpandedProposal

        mock_expanded_proposal = ExpandedProposal(
            title="Test Proposal",
            summary="Test summary",
            problem_statement="Test problem",
            proposed_solution="Test solution",
            assumptions=["Assumption 1"],
            scope_non_goals=["Non-goal 1"],
        )
        mock_expand.return_value = (mock_expanded_proposal, {"request_id": "test-req"})

        # Mock review service
        from consensus_engine.schemas.review import PersonaReview as PersonaReviewSchema

        mock_persona_reviews = [
            PersonaReviewSchema(
                persona_name="Architect",
                persona_id="architect",
                confidence_score=0.85,
                strengths=["Good design"],
                concerns=[],
                recommendations=["Add more details"],
                blocking_issues=[],
                estimated_effort="Medium",
                dependency_risks=[],
            ),
            PersonaReviewSchema(
                persona_name="Critic",
                persona_id="critic",
                confidence_score=0.75,
                strengths=["Feasible"],
                concerns=[],
                recommendations=["Consider edge cases"],
                blocking_issues=[],
                estimated_effort="Medium",
                dependency_risks=[],
            ),
            PersonaReviewSchema(
                persona_name="Optimist",
                persona_id="optimist",
                confidence_score=0.90,
                strengths=["Great potential"],
                concerns=[],
                recommendations=["Go for it"],
                blocking_issues=[],
                estimated_effort="Low",
                dependency_risks=[],
            ),
            PersonaReviewSchema(
                persona_name="SecurityGuardian",
                persona_id="security_guardian",
                confidence_score=0.80,
                strengths=["Secure approach"],
                concerns=[],
                recommendations=["Add authentication"],
                blocking_issues=[],
                estimated_effort="Medium",
                dependency_risks=[],
            ),
            PersonaReviewSchema(
                persona_name="UserAdvocate",
                persona_id="user_advocate",
                confidence_score=0.85,
                strengths=["User-friendly"],
                concerns=[],
                recommendations=["Improve UX"],
                blocking_issues=[],
                estimated_effort="Low",
                dependency_risks=[],
            ),
        ]
        mock_review.return_value = (mock_persona_reviews, {"status": "success"})

        # Mock aggregate service
        from consensus_engine.schemas.review import DecisionAggregation, DecisionEnum

        mock_decision = DecisionAggregation(
            decision=DecisionEnum.APPROVE,
            overall_weighted_confidence=0.82,
            detailed_breakdown={},
            minority_report=None,
            veto_applied=False,
        )
        mock_aggregate.return_value = mock_decision

        # Create job message
        job_msg = JobMessage(
            run_id=str(run_id),
            run_type="initial",
            priority="normal",
            payload={"idea": "Test idea for integration"},
        )

        # Process job
        with Session(test_db_engine) as session:
            worker._process_job(session, job_msg)

        # Verify run status
        with Session(test_db_engine) as session:
            run = session.get(Run, run_id)
            assert run is not None
            assert run.status == RunStatus.COMPLETED
            assert run.started_at is not None
            assert run.completed_at is not None
            assert run.overall_weighted_confidence == 0.82
            assert run.decision_label == "approve"

            # Verify step progress
            steps = StepProgressRepository.get_run_steps(session, run_id)
            assert len(steps) == 7
            for step in steps:
                assert step.status == StepStatus.COMPLETED
                assert step.started_at is not None
                assert step.completed_at is not None

            # Verify proposal version
            proposal_version = session.execute(
                select(ProposalVersion).where(ProposalVersion.run_id == run_id)
            ).scalar_one_or_none()
            assert proposal_version is not None

            # Verify persona reviews
            persona_reviews = session.execute(
                select(PersonaReview).where(PersonaReview.run_id == run_id)
            ).scalars().all()
            assert len(persona_reviews) == 5

            # Verify decision
            decision = session.execute(
                select(Decision).where(Decision.run_id == run_id)
            ).scalar_one_or_none()
            assert decision is not None
            assert decision.overall_weighted_confidence == 0.82

    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    def test_idempotent_processing(
        self,
        mock_get_engine: Mock,
        mock_subscriber_cls: Mock,
        test_db_engine,
        test_settings: Settings,
    ):
        """Test that processing is idempotent for completed runs."""
        # Set up database
        mock_get_engine.return_value = test_db_engine

        # Set up worker
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        worker = PipelineWorker(test_settings)
        worker.engine = test_db_engine

        # Create completed run in database
        with Session(test_db_engine) as session:
            run_id = uuid.uuid4()
            run = RunRepository.create_run(
                session=session,
                run_id=run_id,
                input_idea="Test idea",
                extra_context=None,
                run_type=RunType.INITIAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
                priority=RunPriority.NORMAL,
                status=RunStatus.COMPLETED,
            )
            run.started_at = datetime.now(UTC)
            run.completed_at = datetime.now(UTC)
            session.commit()

        # Create job message
        job_msg = JobMessage(
            run_id=str(run_id),
            run_type="initial",
            priority="normal",
            payload={"idea": "Test idea"},
        )

        # Process job - should be skipped
        with Session(test_db_engine) as session:
            worker._process_job(session, job_msg)

        # Verify run is still completed (no changes)
        with Session(test_db_engine) as session:
            run = session.get(Run, run_id)
            assert run is not None
            assert run.status == RunStatus.COMPLETED

    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    @patch("consensus_engine.workers.pipeline_worker.expand_idea")
    def test_pipeline_failure_handling(
        self,
        mock_expand: Mock,
        mock_get_engine: Mock,
        mock_subscriber_cls: Mock,
        test_db_engine,
        test_settings: Settings,
    ):
        """Test that pipeline failures are handled correctly."""
        # Set up database
        mock_get_engine.return_value = test_db_engine

        # Set up worker
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        worker = PipelineWorker(test_settings)
        worker.engine = test_db_engine

        # Create test run in database
        with Session(test_db_engine) as session:
            run_id = uuid.uuid4()
            run = RunRepository.create_run(
                session=session,
                run_id=run_id,
                input_idea="Test idea",
                extra_context=None,
                run_type=RunType.INITIAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
                priority=RunPriority.NORMAL,
                status=RunStatus.QUEUED,
            )
            
            # Initialize step progress
            StepProgressRepository.upsert_step_progress(
                session=session,
                run_id=run_id,
                step_name="expand",
                status=StepStatus.PENDING,
            )
            
            session.commit()

        # Mock expand to raise error
        mock_expand.side_effect = Exception("Test error")

        # Create job message
        job_msg = JobMessage(
            run_id=str(run_id),
            run_type="initial",
            priority="normal",
            payload={"idea": "Test idea"},
        )

        # Process job - should fail
        with pytest.raises(Exception, match="Test error"):
            with Session(test_db_engine) as session:
                worker._process_job(session, job_msg)

        # Verify run status is FAILED
        with Session(test_db_engine) as session:
            run = session.get(Run, run_id)
            assert run is not None
            assert run.status == RunStatus.FAILED
            assert run.completed_at is not None

            # Verify expand step is FAILED
            step = session.execute(
                select(StepProgress).where(
                    StepProgress.run_id == run_id,
                    StepProgress.step_name == "expand",
                )
            ).scalar_one()
            assert step.status == StepStatus.FAILED
            assert step.error_message is not None
            assert "Expand failed" in step.error_message
