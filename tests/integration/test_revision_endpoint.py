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
"""Integration tests for revision endpoint."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from consensus_engine.app import create_app
from consensus_engine.db.dependencies import get_db_session
from consensus_engine.db.models import Run, RunStatus, RunType
from consensus_engine.db.repositories import (
    DecisionRepository,
    PersonaReviewRepository,
    ProposalVersionRepository,
    RunRepository,
)
from consensus_engine.schemas.proposal import ExpandedProposal
from consensus_engine.schemas.review import (
    BlockingIssue,
    Concern,
    DecisionAggregation,
    DecisionEnum,
    DetailedScoreBreakdown,
    PersonaReview,
)


@pytest.fixture
def valid_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up valid test environment."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-revision-endpoint")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.1")
    monkeypatch.setenv("TEMPERATURE", "0.7")
    monkeypatch.setenv("ENV", "testing")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture
def client(valid_test_env: None) -> Generator[TestClient, None, None]:
    """Create test client with valid environment."""
    from consensus_engine.config import get_settings

    get_settings.cache_clear()

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session(client: TestClient) -> Session:
    """Get database session from client."""
    return next(get_db_session())


def create_sample_completed_run(db_session: Session) -> str:
    """Create a sample completed run for testing revisions.

    Returns:
        run_id as string
    """
    import uuid

    # Create parent run
    run_id = uuid.uuid4()
    run = RunRepository.create_run(
        session=db_session,
        run_id=run_id,
        input_idea="Build a REST API",
        extra_context={"language": "Python"},
        run_type=RunType.INITIAL,
        model="gpt-5.1",
        temperature=0.7,
        parameters_json={"expand_model": "gpt-5.1"},
    )

    # Create proposal
    proposal = ExpandedProposal(
        problem_statement="Need a REST API",
        proposed_solution="Use FastAPI",
        assumptions=["Python 3.11+"],
        scope_non_goals=["No mobile app"],
    )

    ProposalVersionRepository.create_proposal_version(
        session=db_session,
        run_id=run_id,
        expanded_proposal=proposal,
        persona_template_version="v1",
    )

    # Create persona reviews
    personas = [
        ("architect", "Architect", 0.65),  # Low confidence - should re-run
        ("critic", "Critic", 0.85),
        ("optimist", "Optimist", 0.90),
        ("security_guardian", "SecurityGuardian", 0.80),
        ("user_advocate", "UserAdvocate", 0.88),
    ]

    for persona_id, persona_name, confidence in personas:
        review = PersonaReview(
            persona_name=persona_name,
            persona_id=persona_id,
            confidence_score=confidence,
            strengths=["Good"],
            concerns=[],
            recommendations=["Improve"],
            blocking_issues=[],
            estimated_effort="2 weeks",
            dependency_risks=[],
        )

        PersonaReviewRepository.create_persona_review(
            session=db_session,
            run_id=run_id,
            persona_review=review,
            prompt_parameters_json={
                "model": "gpt-5.1",
                "temperature": 0.2,
                "persona_template_version": "v1",
            },
        )

    # Create decision
    decision = DecisionAggregation(
        overall_weighted_confidence=0.82,
        weighted_confidence=0.82,
        decision=DecisionEnum.APPROVE,
        detailed_score_breakdown=DetailedScoreBreakdown(
            weights={"architect": 0.25, "critic": 0.25},
            individual_scores={"architect": 0.65, "critic": 0.85},
            weighted_contributions={"architect": 0.1625, "critic": 0.2125},
            formula="test",
        ),
    )

    DecisionRepository.create_decision(
        session=db_session,
        run_id=run_id,
        decision_aggregation=decision,
    )

    # Update run status
    RunRepository.update_run_status(
        session=db_session,
        run_id=run_id,
        status=RunStatus.COMPLETED,
        overall_weighted_confidence=0.82,
        decision_label="approve",
    )

    db_session.commit()

    return str(run_id)


class TestRevisionEndpoint:
    """Test suite for POST /v1/runs/{run_id}/revisions endpoint."""

    @patch("consensus_engine.services.orchestrator.OpenAIClientWrapper")
    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_create_revision_success(
        self,
        mock_expand_client_class: MagicMock,
        mock_orchestrator_client_class: MagicMock,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Test successful revision creation with selective persona re-run."""
        # Create parent run
        parent_run_id = create_sample_completed_run(db_session)

        # Mock expand service
        revised_proposal = ExpandedProposal(
            problem_statement="Need a secure REST API",
            proposed_solution="Use FastAPI with OAuth2",
            assumptions=["Python 3.11+", "OAuth2 provider"],
            scope_non_goals=["No mobile app"],
        )
        mock_expand_client = MagicMock()
        mock_expand_client.create_structured_response.return_value = (
            revised_proposal,
            {"request_id": "expand-req-123"},
        )
        mock_expand_client_class.return_value = mock_expand_client

        # Mock orchestrator service (only architect should be re-run)
        mock_review = PersonaReview(
            persona_name="Architect",
            persona_id="architect",
            confidence_score=0.90,
            strengths=["Improved design"],
            concerns=[],
            recommendations=["Good"],
            blocking_issues=[],
            estimated_effort="2 weeks",
            dependency_risks=[],
        )
        mock_orchestrator_client = MagicMock()
        mock_orchestrator_client.create_structured_response.return_value = (
            mock_review,
            {"request_id": "review-req-123"},
        )
        mock_orchestrator_client_class.return_value = mock_orchestrator_client

        # Make request
        response = client.post(
            f"/v1/runs/{parent_run_id}/revisions",
            json={
                "edited_proposal": "Add OAuth2 authentication",
                "edit_notes": "Addressing security concerns",
            },
        )

        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert "run_id" in data
        assert data["parent_run_id"] == parent_run_id
        assert data["status"] == "completed"
        assert "architect" in data["personas_rerun"]
        assert len(data["personas_reused"]) == 4

    def test_create_revision_parent_not_found(
        self,
        client: TestClient,
    ) -> None:
        """Test revision creation fails when parent run not found."""
        response = client.post(
            "/v1/runs/00000000-0000-0000-0000-000000000000/revisions",
            json={
                "edited_proposal": "Add feature",
                "edit_notes": "Improve proposal",
            },
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_revision_parent_failed(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Test revision creation fails when parent run failed."""
        import uuid

        # Create failed run
        run_id = uuid.uuid4()
        RunRepository.create_run(
            session=db_session,
            run_id=run_id,
            input_idea="Build API",
            extra_context=None,
            run_type=RunType.INITIAL,
            model="gpt-5.1",
            temperature=0.7,
            parameters_json={},
        )
        RunRepository.update_run_status(
            session=db_session,
            run_id=run_id,
            status=RunStatus.FAILED,
        )
        db_session.commit()

        response = client.post(
            f"/v1/runs/{run_id}/revisions",
            json={
                "edited_proposal": "Add feature",
                "edit_notes": "Improve proposal",
            },
        )

        assert response.status_code == 409
        assert "completed" in response.json()["detail"].lower()

    def test_create_revision_missing_edit_inputs(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Test revision creation fails when no edit inputs provided."""
        parent_run_id = create_sample_completed_run(db_session)

        response = client.post(
            f"/v1/runs/{parent_run_id}/revisions",
            json={},
        )

        assert response.status_code == 400
        assert "edited_proposal" in response.json()["detail"].lower()

    def test_create_revision_invalid_run_id(
        self,
        client: TestClient,
    ) -> None:
        """Test revision creation fails with invalid UUID."""
        response = client.post(
            "/v1/runs/not-a-uuid/revisions",
            json={
                "edited_proposal": "Add feature",
            },
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()
