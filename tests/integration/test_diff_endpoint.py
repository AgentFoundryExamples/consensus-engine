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
"""Integration tests for diff endpoint.

These tests validate GET /v1/runs/{run_id}/diff/{other_run_id} endpoint
with database operations but without invoking any LLM services.
"""

import json
import os
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from consensus_engine.app import create_app
from consensus_engine.db import Base
from consensus_engine.db.dependencies import get_db_session
from consensus_engine.db.models import Decision, PersonaReview, ProposalVersion, Run, RunStatus, RunType


def is_database_available():
    """Check if a test database is available."""
    try:
        from sqlalchemy import text
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
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def test_session_factory(test_engine):
    """Create a session factory for tests."""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def test_client(test_session_factory, clean_database, monkeypatch):
    """Create a test client with database override."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-diff-endpoint")
    
    app = create_app()
    
    def override_get_db_session():
        session = test_session_factory()
        try:
            yield session
        finally:
            session.close()
    
    app.dependency_overrides[get_db_session] = override_get_db_session
    
    with TestClient(app) as client:
        yield client


def create_test_run(
    session,
    run_id: uuid.UUID,
    status: RunStatus = RunStatus.COMPLETED,
    run_type: RunType = RunType.INITIAL,
    parent_run_id: uuid.UUID | None = None,
    confidence: float | None = 0.80,
    decision: str | None = "approve",
    proposal_data: dict | None = None,
    persona_reviews_data: list[dict] | None = None,
) -> Run:
    """Helper to create a test run with full data."""
    # Create run
    run = Run(
        id=run_id,
        status=status,
        input_idea="Test idea",
        extra_context={"test": True},
        run_type=run_type,
        parent_run_id=parent_run_id,
        model="gpt-5.1",
        temperature=0.7,
        parameters_json={},
        overall_weighted_confidence=confidence,
        decision_label=decision,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(run)
    session.flush()
    
    # Create proposal if provided
    if proposal_data:
        proposal = ProposalVersion(
            run_id=run_id,
            expanded_proposal_json=proposal_data,
            persona_template_version="v1",
        )
        session.add(proposal)
        session.flush()
    
    # Create persona reviews if provided
    if persona_reviews_data:
        for review_data in persona_reviews_data:
            review = PersonaReview(
                run_id=run_id,
                persona_id=review_data["persona_id"],
                persona_name=review_data["persona_name"],
                review_json=review_data.get("review_json", {}),
                confidence_score=review_data["confidence_score"],
                blocking_issues_present=review_data.get("blocking_issues_present", False),
                security_concerns_present=review_data.get("security_concerns_present", False),
                prompt_parameters_json={},
            )
            session.add(review)
        session.flush()
    
    # Create decision if run is completed
    if status == RunStatus.COMPLETED and confidence is not None:
        decision_obj = Decision(
            run_id=run_id,
            decision_json={"decision": decision, "confidence": confidence},
            overall_weighted_confidence=confidence,
        )
        session.add(decision_obj)
        session.flush()
    
    session.commit()
    return run


class TestDiffEndpoint:
    """Test suite for GET /v1/runs/{run_id}/diff/{other_run_id} endpoint."""

    def test_diff_identical_runs_returns_400(self, test_client, test_session_factory):
        """Test that diffing a run against itself returns 400."""
        session = test_session_factory()
        
        run_id = uuid.uuid4()
        create_test_run(session, run_id)
        
        session.close()
        
        response = test_client.get(f"/v1/runs/{run_id}/diff/{run_id}")
        
        assert response.status_code == 400
        data = response.json()
        assert "cannot diff a run against itself" in data["detail"].lower()

    def test_diff_missing_first_run_returns_404(self, test_client, test_session_factory):
        """Test that missing first run returns 404."""
        session = test_session_factory()
        
        run2_id = uuid.uuid4()
        create_test_run(session, run2_id)
        
        session.close()
        
        missing_id = uuid.uuid4()
        response = test_client.get(f"/v1/runs/{missing_id}/diff/{run2_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_diff_missing_second_run_returns_404(self, test_client, test_session_factory):
        """Test that missing second run returns 404."""
        session = test_session_factory()
        
        run1_id = uuid.uuid4()
        create_test_run(session, run1_id)
        
        session.close()
        
        missing_id = uuid.uuid4()
        response = test_client.get(f"/v1/runs/{run1_id}/diff/{missing_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_diff_invalid_uuid_returns_400(self, test_client):
        """Test that invalid UUID returns 400."""
        response = test_client.get("/v1/runs/invalid-uuid/diff/another-invalid")
        
        assert response.status_code == 400
        data = response.json()
        assert "uuid" in data["detail"].lower()

    def test_diff_parent_child_runs(self, test_client, test_session_factory):
        """Test diff between parent and child runs."""
        session = test_session_factory()
        
        parent_id = uuid.uuid4()
        child_id = uuid.uuid4()
        
        # Create parent run
        parent_proposal = {
            "title": "Original Title",
            "problem_statement": "Original problem",
            "proposed_solution": "Original solution",
            "assumptions": ["Assumption 1"],
            "scope_non_goals": ["Non-goal 1"],
        }
        
        parent_reviews = [
            {
                "persona_id": "architect",
                "persona_name": "Architect",
                "confidence_score": 0.70,
                "blocking_issues_present": True,
            },
            {
                "persona_id": "critic",
                "persona_name": "Critic",
                "confidence_score": 0.65,
            },
        ]
        
        create_test_run(
            session,
            parent_id,
            confidence=0.68,
            decision="revise",
            proposal_data=parent_proposal,
            persona_reviews_data=parent_reviews,
        )
        
        # Create child run (revision)
        child_proposal = {
            "title": "Updated Title",
            "problem_statement": "Updated problem",
            "proposed_solution": "Original solution",
            "assumptions": ["Assumption 1", "Assumption 2"],
            "scope_non_goals": ["Non-goal 1"],
        }
        
        child_reviews = [
            {
                "persona_id": "architect",
                "persona_name": "Architect",
                "confidence_score": 0.90,
                "blocking_issues_present": False,
            },
            {
                "persona_id": "critic",
                "persona_name": "Critic",
                "confidence_score": 0.80,
            },
        ]
        
        create_test_run(
            session,
            child_id,
            run_type=RunType.REVISION,
            parent_run_id=parent_id,
            confidence=0.85,
            decision="approve",
            proposal_data=child_proposal,
            persona_reviews_data=child_reviews,
        )
        
        session.close()
        
        # Request diff
        response = test_client.get(f"/v1/runs/{parent_id}/diff/{child_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check metadata
        assert data["metadata"]["is_parent_child"] is True
        assert data["metadata"]["relationship"] == "run1_is_parent_of_run2"
        
        # Check proposal changes
        assert data["proposal_changes"]["title"]["status"] == "modified"
        assert data["proposal_changes"]["problem_statement"]["status"] == "modified"
        assert data["proposal_changes"]["proposed_solution"]["status"] == "unchanged"
        assert data["proposal_changes"]["assumptions"]["status"] == "modified"
        
        # Check persona deltas
        assert len(data["persona_deltas"]) == 2
        
        architect_delta = next(d for d in data["persona_deltas"] if d["persona_id"] == "architect")
        assert architect_delta["old_confidence"] == 0.70
        assert architect_delta["new_confidence"] == 0.90
        assert architect_delta["confidence_delta"] == 0.20
        assert architect_delta["blocking_changed"] is True
        
        # Check decision delta
        assert data["decision_delta"]["old_overall_weighted_confidence"] == 0.68
        assert data["decision_delta"]["new_overall_weighted_confidence"] == 0.85
        assert data["decision_delta"]["confidence_delta"] == 0.17
        assert data["decision_delta"]["old_decision_label"] == "revise"
        assert data["decision_delta"]["new_decision_label"] == "approve"
        assert data["decision_delta"]["decision_changed"] is True

    def test_diff_unrelated_runs(self, test_client, test_session_factory):
        """Test diff between unrelated runs."""
        session = test_session_factory()
        
        run1_id = uuid.uuid4()
        run2_id = uuid.uuid4()
        
        # Create two unrelated runs
        proposal1 = {
            "problem_statement": "Problem A",
            "proposed_solution": "Solution A",
            "assumptions": [],
            "scope_non_goals": [],
        }
        
        proposal2 = {
            "problem_statement": "Problem B",
            "proposed_solution": "Solution B",
            "assumptions": [],
            "scope_non_goals": [],
        }
        
        create_test_run(session, run1_id, proposal_data=proposal1, confidence=0.75)
        create_test_run(session, run2_id, proposal_data=proposal2, confidence=0.85)
        
        session.close()
        
        # Request diff
        response = test_client.get(f"/v1/runs/{run1_id}/diff/{run2_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check metadata
        assert data["metadata"]["is_parent_child"] is False
        assert data["metadata"]["relationship"] == "unrelated"

    def test_diff_with_missing_proposals(self, test_client, test_session_factory):
        """Test diff when one or both runs have no proposal."""
        session = test_session_factory()
        
        run1_id = uuid.uuid4()
        run2_id = uuid.uuid4()
        
        # Create runs without proposals
        create_test_run(session, run1_id, proposal_data=None)
        create_test_run(session, run2_id, proposal_data=None)
        
        session.close()
        
        # Request diff
        response = test_client.get(f"/v1/runs/{run1_id}/diff/{run2_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Proposal changes should indicate both missing
        assert data["proposal_changes"]["status"] == "both_missing"

    def test_diff_with_persona_changes(self, test_client, test_session_factory):
        """Test diff with personas added/removed between runs."""
        session = test_session_factory()
        
        run1_id = uuid.uuid4()
        run2_id = uuid.uuid4()
        
        # First run has only architect
        reviews1 = [
            {
                "persona_id": "architect",
                "persona_name": "Architect",
                "confidence_score": 0.80,
            }
        ]
        
        # Second run has architect and critic
        reviews2 = [
            {
                "persona_id": "architect",
                "persona_name": "Architect",
                "confidence_score": 0.85,
            },
            {
                "persona_id": "critic",
                "persona_name": "Critic",
                "confidence_score": 0.70,
            },
        ]
        
        create_test_run(session, run1_id, persona_reviews_data=reviews1)
        create_test_run(session, run2_id, persona_reviews_data=reviews2)
        
        session.close()
        
        # Request diff
        response = test_client.get(f"/v1/runs/{run1_id}/diff/{run2_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have deltas for both personas
        assert len(data["persona_deltas"]) == 2
        
        # Architect should have confidence change
        architect = next(d for d in data["persona_deltas"] if d["persona_id"] == "architect")
        assert architect["confidence_delta"] == 0.05
        
        # Critic should be marked as added
        critic = next(d for d in data["persona_deltas"] if d["persona_id"] == "critic")
        assert critic["status"] == "added_in_run2"
        assert critic["old_confidence"] is None
        assert critic["new_confidence"] == 0.70

    def test_diff_security_concerns_change(self, test_client, test_session_factory):
        """Test diff tracking security concerns changes."""
        session = test_session_factory()
        
        run1_id = uuid.uuid4()
        run2_id = uuid.uuid4()
        
        # First run has security concerns
        reviews1 = [
            {
                "persona_id": "security_guardian",
                "persona_name": "SecurityGuardian",
                "confidence_score": 0.60,
                "security_concerns_present": True,
                "blocking_issues_present": True,
            }
        ]
        
        # Second run has no security concerns
        reviews2 = [
            {
                "persona_id": "security_guardian",
                "persona_name": "SecurityGuardian",
                "confidence_score": 0.90,
                "security_concerns_present": False,
                "blocking_issues_present": False,
            }
        ]
        
        create_test_run(session, run1_id, persona_reviews_data=reviews1, confidence=0.60, decision="reject")
        create_test_run(session, run2_id, persona_reviews_data=reviews2, confidence=0.90, decision="approve")
        
        session.close()
        
        # Request diff
        response = test_client.get(f"/v1/runs/{run1_id}/diff/{run2_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check security concerns changed
        security_delta = data["persona_deltas"][0]
        assert security_delta["security_concerns_changed"] is True
        assert security_delta["old_security_concerns"] is True
        assert security_delta["new_security_concerns"] is False
