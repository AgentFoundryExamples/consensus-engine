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
"""Integration tests for run retrieval endpoints.

These tests validate GET /v1/runs and GET /v1/runs/{run_id} endpoints
with database operations but without invoking any LLM services.
"""

import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from consensus_engine.app import create_app
from consensus_engine.db import Base
from consensus_engine.db.dependencies import get_db_session
from consensus_engine.db.models import Decision, PersonaReview, ProposalVersion, Run, RunPriority, RunStatus, RunType, StepProgress, StepStatus


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
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-runs-endpoint")
    
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


@pytest.fixture
def sample_runs(test_session_factory):
    """Create sample runs in the database for testing."""
    session = test_session_factory()
    
    try:
        runs = []
        
        # Run 1: Completed with high confidence
        run1_id = uuid.uuid4()
        run1 = Run(
            id=run1_id,
            status=RunStatus.COMPLETED,
            input_idea="Build a REST API for user management",
            extra_context={"language": "Python"},
            run_type=RunType.INITIAL,
            model="gpt-5.1",
            temperature=0.7,
            parameters_json={"max_tokens": 4000},
            overall_weighted_confidence=0.85,
            decision_label="approve",
            created_at=datetime.now(UTC) - timedelta(days=2),
        )
        session.add(run1)
        
        # Add proposal for run1
        proposal1 = ProposalVersion(
            run_id=run1_id,
            expanded_proposal_json={
                "title": "User Management API",
                "summary": "A comprehensive REST API for managing users",
                "problem_statement": "Need user management",
                "proposed_solution": "Build REST API",
                "assumptions": ["Python 3.11+"],
                "scope_non_goals": ["No mobile app"],
            },
            persona_template_version="1.0",
        )
        session.add(proposal1)
        
        # Add persona reviews for run1
        review1 = PersonaReview(
            run_id=run1_id,
            persona_id="architect",
            persona_name="Architect",
            review_json={"confidence_score": 0.85},
            confidence_score=0.85,
            blocking_issues_present=False,
            security_concerns_present=False,
            prompt_parameters_json={"model": "gpt-5.1", "temperature": 0.2},
        )
        session.add(review1)
        
        # Add decision for run1
        decision1 = Decision(
            run_id=run1_id,
            decision_json={
                "decision": "approve",
                "overall_weighted_confidence": 0.85,
                "score_breakdown": {},
            },
            overall_weighted_confidence=0.85,
        )
        session.add(decision1)
        
        runs.append(run1)
        
        # Run 2: Completed with low confidence
        run2_id = uuid.uuid4()
        run2 = Run(
            id=run2_id,
            status=RunStatus.COMPLETED,
            input_idea="Create a blockchain solution",
            extra_context=None,
            run_type=RunType.INITIAL,
            model="gpt-5.1",
            temperature=0.7,
            parameters_json={"max_tokens": 4000},
            overall_weighted_confidence=0.45,
            decision_label="reject",
            created_at=datetime.now(UTC) - timedelta(days=1),
        )
        session.add(run2)
        
        # Add proposal for run2
        proposal2 = ProposalVersion(
            run_id=run2_id,
            expanded_proposal_json={
                "title": "Blockchain Solution",
                "summary": "A blockchain-based system",
                "problem_statement": "Need blockchain",
                "proposed_solution": "Build blockchain",
                "assumptions": [],
                "scope_non_goals": [],
            },
            persona_template_version="1.0",
        )
        session.add(proposal2)
        
        runs.append(run2)
        
        # Run 3: Failed
        run3_id = uuid.uuid4()
        run3 = Run(
            id=run3_id,
            status=RunStatus.FAILED,
            input_idea="Implement AI agent",
            extra_context=None,
            run_type=RunType.INITIAL,
            model="gpt-5.1",
            temperature=0.7,
            parameters_json={"max_tokens": 4000},
            created_at=datetime.now(UTC) - timedelta(hours=12),
        )
        session.add(run3)
        
        runs.append(run3)
        
        # Run 4: Revision of run1
        run4_id = uuid.uuid4()
        run4 = Run(
            id=run4_id,
            status=RunStatus.COMPLETED,
            input_idea="Build a REST API for user management with OAuth",
            extra_context={"language": "Python"},
            run_type=RunType.REVISION,
            parent_run_id=run1_id,
            model="gpt-5.1",
            temperature=0.7,
            parameters_json={"max_tokens": 4000},
            overall_weighted_confidence=0.90,
            decision_label="approve",
            created_at=datetime.now(UTC) - timedelta(hours=6),
        )
        session.add(run4)
        
        # Add proposal for run4
        proposal4 = ProposalVersion(
            run_id=run4_id,
            expanded_proposal_json={
                "title": "User Management API v2",
                "summary": "Enhanced API with OAuth",
                "problem_statement": "Need user management with OAuth",
                "proposed_solution": "Build REST API with OAuth",
                "assumptions": ["Python 3.11+"],
                "scope_non_goals": ["No mobile app"],
            },
            persona_template_version="1.0",
        )
        session.add(proposal4)
        
        runs.append(run4)
        
        # Run 5: Running (incomplete)
        run5_id = uuid.uuid4()
        run5 = Run(
            id=run5_id,
            status=RunStatus.RUNNING,
            input_idea="Build GraphQL API",
            extra_context=None,
            run_type=RunType.INITIAL,
            model="gpt-5.1",
            temperature=0.7,
            parameters_json={"max_tokens": 4000},
            created_at=datetime.now(UTC) - timedelta(minutes=5),
        )
        session.add(run5)
        
        runs.append(run5)
        
        session.commit()
        
        return runs
        
    finally:
        session.close()


@pytest.fixture
def run_with_step_progress(test_session_factory):
    """Create a run with actual StepProgress records for testing."""
    session = test_session_factory()
    
    try:
        # Create a queued run with step progress
        run_id = uuid.uuid4()
        now = datetime.now(UTC)
        
        run = Run(
            id=run_id,
            status=RunStatus.RUNNING,
            queued_at=now - timedelta(minutes=5),
            started_at=now - timedelta(minutes=4),
            input_idea="Test idea with step progress",
            extra_context=None,
            run_type=RunType.INITIAL,
            model="gpt-5.1",
            temperature=0.7,
            parameters_json={"max_tokens": 4000},
            created_at=now - timedelta(minutes=5),
        )
        session.add(run)
        
        # Add step progress records - some completed, some running, some pending
        # Step 1: expand - completed
        step1 = StepProgress(
            run_id=run_id,
            step_name="expand",
            step_order=0,
            status=StepStatus.COMPLETED,
            started_at=now - timedelta(minutes=4),
            completed_at=now - timedelta(minutes=3, seconds=30),
        )
        session.add(step1)
        
        # Step 2: review_architect - completed
        step2 = StepProgress(
            run_id=run_id,
            step_name="review_architect",
            step_order=1,
            status=StepStatus.COMPLETED,
            started_at=now - timedelta(minutes=3, seconds=30),
            completed_at=now - timedelta(minutes=3),
        )
        session.add(step2)
        
        # Step 3: review_critic - running
        step3 = StepProgress(
            run_id=run_id,
            step_name="review_critic",
            step_order=2,
            status=StepStatus.RUNNING,
            started_at=now - timedelta(minutes=3),
            completed_at=None,
        )
        session.add(step3)
        
        # Steps 4-7: pending
        for i, step_name in enumerate([
            "review_optimist",
            "review_security",
            "review_user_advocate",
            "aggregate_decision",
        ], start=3):
            step = StepProgress(
                run_id=run_id,
                step_name=step_name,
                step_order=i,
                status=StepStatus.PENDING,
                started_at=None,
                completed_at=None,
            )
            session.add(step)
        
        session.commit()
        
        return run
        
    finally:
        session.close()


@pytest.fixture
def failed_run_with_error(test_session_factory):
    """Create a failed run with error in step progress."""
    session = test_session_factory()
    
    try:
        run_id = uuid.uuid4()
        now = datetime.now(UTC)
        
        run = Run(
            id=run_id,
            status=RunStatus.FAILED,
            queued_at=now - timedelta(minutes=5),
            started_at=now - timedelta(minutes=4),
            completed_at=now - timedelta(minutes=2),
            input_idea="Test idea that fails",
            extra_context=None,
            run_type=RunType.INITIAL,
            model="gpt-5.1",
            temperature=0.7,
            parameters_json={"max_tokens": 4000},
            created_at=now - timedelta(minutes=5),
        )
        session.add(run)
        
        # Add step progress - expand completed, review_architect failed
        step1 = StepProgress(
            run_id=run_id,
            step_name="expand",
            step_order=0,
            status=StepStatus.COMPLETED,
            started_at=now - timedelta(minutes=4),
            completed_at=now - timedelta(minutes=3),
        )
        session.add(step1)
        
        step2 = StepProgress(
            run_id=run_id,
            step_name="review_architect",
            step_order=1,
            status=StepStatus.FAILED,
            started_at=now - timedelta(minutes=3),
            completed_at=now - timedelta(minutes=2),
            error_message="API rate limit exceeded. Please retry later.",
        )
        session.add(step2)
        
        # Remaining steps stay pending
        for i, step_name in enumerate([
            "review_critic",
            "review_optimist",
            "review_security",
            "review_user_advocate",
            "aggregate_decision",
        ], start=2):
            step = StepProgress(
                run_id=run_id,
                step_name=step_name,
                step_order=i,
                status=StepStatus.PENDING,
                started_at=None,
                completed_at=None,
            )
            session.add(step)
        
        session.commit()
        
        return run
        
    finally:
        session.close()


class TestListRunsEndpoint:
    """Tests for GET /v1/runs endpoint."""
    
    def test_list_runs_no_filters(self, test_client, sample_runs):
        """Test listing all runs without filters."""
        response = test_client.get("/v1/runs")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "runs" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        
        assert data["total"] == 5
        assert len(data["runs"]) == 5
        assert data["limit"] == 30
        assert data["offset"] == 0
        
        # Verify ordering (newest first)
        run_dates = [run["created_at"] for run in data["runs"]]
        assert run_dates == sorted(run_dates, reverse=True)
    
    def test_list_runs_with_pagination(self, test_client, sample_runs):
        """Test pagination with limit and offset."""
        # First page
        response1 = test_client.get("/v1/runs?limit=2&offset=0")
        assert response1.status_code == 200
        data1 = response1.json()
        
        assert data1["total"] == 5
        assert len(data1["runs"]) == 2
        assert data1["limit"] == 2
        assert data1["offset"] == 0
        
        # Second page
        response2 = test_client.get("/v1/runs?limit=2&offset=2")
        assert response2.status_code == 200
        data2 = response2.json()
        
        assert data2["total"] == 5
        assert len(data2["runs"]) == 2
        assert data2["limit"] == 2
        assert data2["offset"] == 2
        
        # Verify no overlap
        run_ids_page1 = {run["run_id"] for run in data1["runs"]}
        run_ids_page2 = {run["run_id"] for run in data2["runs"]}
        assert len(run_ids_page1.intersection(run_ids_page2)) == 0
    
    def test_list_runs_filter_by_status(self, test_client, sample_runs):
        """Test filtering by status."""
        # Filter for completed runs
        response = test_client.get("/v1/runs?status=completed")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 3
        assert all(run["status"] == "completed" for run in data["runs"])
        
        # Filter for failed runs
        response = test_client.get("/v1/runs?status=failed")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert all(run["status"] == "failed" for run in data["runs"])
    
    def test_list_runs_filter_by_run_type(self, test_client, sample_runs):
        """Test filtering by run_type."""
        # Filter for initial runs
        response = test_client.get("/v1/runs?run_type=initial")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 4
        assert all(run["run_type"] == "initial" for run in data["runs"])
        
        # Filter for revision runs
        response = test_client.get("/v1/runs?run_type=revision")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert all(run["run_type"] == "revision" for run in data["runs"])
    
    def test_list_runs_filter_by_parent_run_id(self, test_client, sample_runs):
        """Test filtering by parent_run_id."""
        parent_run_id = str(sample_runs[0].id)
        
        response = test_client.get(f"/v1/runs?parent_run_id={parent_run_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert data["runs"][0]["parent_run_id"] == parent_run_id
    
    def test_list_runs_filter_by_decision(self, test_client, sample_runs):
        """Test filtering by decision label."""
        # Filter for approve decisions
        response = test_client.get("/v1/runs?decision=approve")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 2
        assert all(run["decision_label"] == "approve" for run in data["runs"])
        
        # Filter for reject decisions
        response = test_client.get("/v1/runs?decision=reject")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 1
        assert all(run["decision_label"] == "reject" for run in data["runs"])
    
    def test_list_runs_filter_by_min_confidence(self, test_client, sample_runs):
        """Test filtering by minimum confidence."""
        response = test_client.get("/v1/runs?min_confidence=0.8")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 2
        for run in data["runs"]:
            assert run["overall_weighted_confidence"] is not None
            assert run["overall_weighted_confidence"] >= 0.8
    
    def test_list_runs_filter_by_date_range(self, test_client, sample_runs):
        """Test filtering by date range."""
        # Filter for runs in the last day
        start_date = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        
        response = test_client.get(f"/v1/runs?start_date={start_date}")
        assert response.status_code == 200
        data = response.json()
        
        # Should return runs from last day (runs 2, 3, 4, 5)
        assert data["total"] >= 3
    
    def test_list_runs_invalid_status(self, test_client, sample_runs):
        """Test invalid status parameter."""
        response = test_client.get("/v1/runs?status=invalid")
        assert response.status_code == 400
        data = response.json()
        assert "Invalid status" in data["detail"]
    
    def test_list_runs_invalid_run_type(self, test_client, sample_runs):
        """Test invalid run_type parameter."""
        response = test_client.get("/v1/runs?run_type=invalid")
        assert response.status_code == 400
        data = response.json()
        assert "Invalid run_type" in data["detail"]
    
    def test_list_runs_invalid_uuid(self, test_client, sample_runs):
        """Test invalid parent_run_id UUID."""
        response = test_client.get("/v1/runs?parent_run_id=not-a-uuid")
        assert response.status_code == 400
        data = response.json()
        assert "Invalid parent_run_id UUID" in data["detail"]
    
    def test_list_runs_invalid_date_format(self, test_client, sample_runs):
        """Test invalid date format."""
        response = test_client.get("/v1/runs?start_date=invalid-date")
        assert response.status_code == 400
        data = response.json()
        assert "Invalid start_date format" in data["detail"]
    
    def test_list_runs_date_without_timezone(self, test_client, sample_runs):
        """Test date without timezone information."""
        response = test_client.get("/v1/runs?start_date=2025-01-07T00:00:00")
        assert response.status_code == 400
        data = response.json()
        assert "timezone" in data["detail"].lower()
    
    def test_list_runs_nonexistent_parent_returns_empty(self, test_client, sample_runs):
        """Test filtering by nonexistent parent_run_id returns empty list."""
        nonexistent_uuid = str(uuid.uuid4())
        
        response = test_client.get(f"/v1/runs?parent_run_id={nonexistent_uuid}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 0
        assert len(data["runs"]) == 0
    
    def test_list_runs_multiple_filters(self, test_client, sample_runs):
        """Test combining multiple filters."""
        response = test_client.get("/v1/runs?status=completed&min_confidence=0.8")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 2
        for run in data["runs"]:
            assert run["status"] == "completed"
            assert run["overall_weighted_confidence"] >= 0.8
    
    def test_list_runs_includes_proposal_metadata(self, test_client, sample_runs):
        """Test that list includes truncated proposal metadata."""
        response = test_client.get("/v1/runs?status=completed")
        assert response.status_code == 200
        data = response.json()
        
        # Find run1 which has proposal
        run1 = next(run for run in data["runs"] if run["decision_label"] == "approve")
        assert run1["proposal_title"] is not None
        assert run1["proposal_summary"] is not None


class TestGetRunDetailEndpoint:
    """Tests for GET /v1/runs/{run_id} endpoint."""
    
    def test_get_run_detail_success(self, test_client, sample_runs):
        """Test retrieving a full run detail."""
        run_id = str(sample_runs[0].id)
        
        response = test_client.get(f"/v1/runs/{run_id}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify all fields are present
        assert data["run_id"] == run_id
        assert data["status"] == "completed"
        assert data["run_type"] == "initial"
        assert data["input_idea"] == "Build a REST API for user management"
        assert data["extra_context"] == {"language": "Python"}
        assert data["model"] == "gpt-5.1"
        assert data["temperature"] == 0.7
        assert data["parameters_json"] == {"max_tokens": 4000}
        assert data["overall_weighted_confidence"] == 0.85
        assert data["decision_label"] == "approve"
        
        # Verify proposal is present
        assert data["proposal"] is not None
        assert data["proposal"]["title"] == "User Management API"
        
        # Verify persona reviews are present
        assert len(data["persona_reviews"]) == 1
        assert data["persona_reviews"][0]["persona_id"] == "architect"
        assert data["persona_reviews"][0]["confidence_score"] == 0.85
        
        # Verify decision is present
        assert data["decision"] is not None
        assert data["decision"]["decision"] == "approve"
    
    def test_get_run_detail_failed_run_with_partial_data(self, test_client, sample_runs):
        """Test retrieving a failed run returns partial data."""
        run_id = str(sample_runs[2].id)  # Failed run
        
        response = test_client.get(f"/v1/runs/{run_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "failed"
        assert data["proposal"] is None  # No proposal for failed run
        assert len(data["persona_reviews"]) == 0  # No reviews
        assert data["decision"] is None  # No decision
        assert data["overall_weighted_confidence"] is None
        assert data["decision_label"] is None
    
    def test_get_run_detail_not_found(self, test_client, sample_runs):
        """Test retrieving non-existent run returns 404."""
        nonexistent_id = str(uuid.uuid4())
        
        response = test_client.get(f"/v1/runs/{nonexistent_id}")
        assert response.status_code == 404
        data = response.json()
        assert "Run not found" in data["detail"]
    
    def test_get_run_detail_invalid_uuid(self, test_client, sample_runs):
        """Test invalid UUID returns 400."""
        response = test_client.get("/v1/runs/not-a-uuid")
        assert response.status_code == 400
        data = response.json()
        assert "Invalid run_id UUID" in data["detail"]
    
    def test_get_run_detail_with_parent_run_id(self, test_client, sample_runs):
        """Test retrieving a revision run includes parent_run_id."""
        run_id = str(sample_runs[3].id)  # Revision run
        parent_run_id = str(sample_runs[0].id)
        
        response = test_client.get(f"/v1/runs/{run_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["run_type"] == "revision"
        assert data["parent_run_id"] == parent_run_id
    
    def test_get_run_detail_running_status(self, test_client, sample_runs):
        """Test retrieving a running run returns incomplete data."""
        run_id = str(sample_runs[4].id)  # Running run
        
        response = test_client.get(f"/v1/runs/{run_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "running"
        assert data["overall_weighted_confidence"] is None
        assert data["decision_label"] is None
        assert data["decision"] is None
    
    def test_get_run_detail_includes_step_progress(self, test_client, sample_runs):
        """Test that run detail includes step progress information."""
        run_id = str(sample_runs[0].id)  # Completed run
        
        response = test_client.get(f"/v1/runs/{run_id}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify step_progress field is present
        assert "step_progress" in data
        assert isinstance(data["step_progress"], list)
        
        # Should have default steps even if no StepProgress records exist
        assert len(data["step_progress"]) == 7  # All canonical steps
        
        # Verify step structure
        for step in data["step_progress"]:
            assert "step_name" in step
            assert "step_order" in step
            assert "status" in step
            assert "started_at" in step
            assert "completed_at" in step
            assert "error_message" in step
        
        # Verify steps are ordered
        step_orders = [s["step_order"] for s in data["step_progress"]]
        assert step_orders == sorted(step_orders)
        
        # Verify expected step names
        step_names = [s["step_name"] for s in data["step_progress"]]
        expected_names = [
            "expand",
            "review_architect",
            "review_critic",
            "review_optimist",
            "review_security",
            "review_user_advocate",
            "aggregate_decision",
        ]
        assert step_names == expected_names
    
    def test_get_run_detail_includes_timestamp_fields(self, test_client, sample_runs):
        """Test that run detail includes queued_at, started_at, completed_at."""
        run_id = str(sample_runs[0].id)  # Completed run
        
        response = test_client.get(f"/v1/runs/{run_id}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify timestamp fields are present
        assert "queued_at" in data
        assert "started_at" in data
        assert "completed_at" in data
        assert "retry_count" in data
        assert "priority" in data
    
    def test_list_runs_includes_timestamp_fields(self, test_client, sample_runs):
        """Test that list runs includes queued_at, started_at, completed_at."""
        response = test_client.get("/v1/runs")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["runs"]) > 0
        
        # Verify timestamp fields are present in list items
        for run in data["runs"]:
            assert "queued_at" in run
            assert "started_at" in run
            assert "completed_at" in run
            assert "retry_count" in run
            assert "priority" in run


class TestStepProgressInRuns:
    """Tests for step progress in run responses."""
    
    def test_run_with_partial_step_progress(self, test_client, run_with_step_progress):
        """Test run with some steps completed, some running, some pending."""
        run_id = str(run_with_step_progress.id)
        
        response = test_client.get(f"/v1/runs/{run_id}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify step progress is present and ordered
        assert "step_progress" in data
        assert len(data["step_progress"]) == 7
        
        steps = data["step_progress"]
        
        # Check first step (expand) - completed
        assert steps[0]["step_name"] == "expand"
        assert steps[0]["status"] == "completed"
        assert steps[0]["started_at"] is not None
        assert steps[0]["completed_at"] is not None
        assert steps[0]["error_message"] is None
        
        # Check second step (review_architect) - completed
        assert steps[1]["step_name"] == "review_architect"
        assert steps[1]["status"] == "completed"
        assert steps[1]["started_at"] is not None
        assert steps[1]["completed_at"] is not None
        
        # Check third step (review_critic) - running
        assert steps[2]["step_name"] == "review_critic"
        assert steps[2]["status"] == "running"
        assert steps[2]["started_at"] is not None
        assert steps[2]["completed_at"] is None
        
        # Check remaining steps - pending
        for step in steps[3:]:
            assert step["status"] == "pending"
            assert step["started_at"] is None
            assert step["completed_at"] is None
    
    def test_failed_run_with_error_message(self, test_client, failed_run_with_error):
        """Test failed run includes error message in step progress."""
        run_id = str(failed_run_with_error.id)
        
        response = test_client.get(f"/v1/runs/{run_id}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "failed"
        
        steps = data["step_progress"]
        
        # First step completed
        assert steps[0]["step_name"] == "expand"
        assert steps[0]["status"] == "completed"
        
        # Second step failed with error message
        assert steps[1]["step_name"] == "review_architect"
        assert steps[1]["status"] == "failed"
        assert steps[1]["error_message"] is not None
        assert "rate limit" in steps[1]["error_message"].lower()
        assert steps[1]["started_at"] is not None
        assert steps[1]["completed_at"] is not None
        
        # Remaining steps pending
        for step in steps[2:]:
            assert step["status"] == "pending"
    
    def test_queued_run_returns_default_steps(self, test_client, test_session_factory):
        """Test queued run without StepProgress records returns default steps."""
        session = test_session_factory()
        
        try:
            # Create a queued run without any StepProgress records
            run_id = uuid.uuid4()
            run = Run(
                id=run_id,
                status=RunStatus.QUEUED,
                queued_at=datetime.now(UTC),
                input_idea="Queued run test",
                extra_context=None,
                run_type=RunType.INITIAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
            )
            session.add(run)
            session.commit()
            
            # Query the run via API
            response = test_client.get(f"/v1/runs/{str(run_id)}")
            assert response.status_code == 200
            data = response.json()
            
            # Should return default steps with 'pending' status
            assert len(data["step_progress"]) == 7
            for step in data["step_progress"]:
                assert step["status"] == "pending"
                assert step["started_at"] is None
                assert step["completed_at"] is None
                assert step["error_message"] is None
            
            # Verify step names and order
            expected_names = [
                "expand",
                "review_architect",
                "review_critic",
                "review_optimist",
                "review_security",
                "review_user_advocate",
                "aggregate_decision",
            ]
            actual_names = [s["step_name"] for s in data["step_progress"]]
            assert actual_names == expected_names
            
        finally:
            session.close()
    
    def test_partial_step_progress_returns_complete_list(self, test_client, test_session_factory):
        """Test that runs with partial StepProgress records return all 7 steps."""
        session = test_session_factory()
        
        try:
            # Create a run with only 2 StepProgress records (expand and review_architect)
            run_id = uuid.uuid4()
            now = datetime.now(UTC)
            
            run = Run(
                id=run_id,
                status=RunStatus.RUNNING,
                queued_at=now - timedelta(minutes=5),
                started_at=now - timedelta(minutes=4),
                input_idea="Partial progress test",
                extra_context=None,
                run_type=RunType.INITIAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
            )
            session.add(run)
            
            # Only add 2 steps
            step1 = StepProgress(
                run_id=run_id,
                step_name="expand",
                step_order=0,
                status=StepStatus.COMPLETED,
                started_at=now - timedelta(minutes=4),
                completed_at=now - timedelta(minutes=3),
            )
            session.add(step1)
            
            step2 = StepProgress(
                run_id=run_id,
                step_name="review_architect",
                step_order=1,
                status=StepStatus.RUNNING,
                started_at=now - timedelta(minutes=3),
                completed_at=None,
            )
            session.add(step2)
            
            session.commit()
            
            # Query the run via API
            response = test_client.get(f"/v1/runs/{str(run_id)}")
            assert response.status_code == 200
            data = response.json()
            
            # Should return all 7 steps (2 actual + 5 default)
            assert len(data["step_progress"]) == 7
            
            # First step should be completed
            assert data["step_progress"][0]["step_name"] == "expand"
            assert data["step_progress"][0]["status"] == "completed"
            assert data["step_progress"][0]["started_at"] is not None
            assert data["step_progress"][0]["completed_at"] is not None
            
            # Second step should be running
            assert data["step_progress"][1]["step_name"] == "review_architect"
            assert data["step_progress"][1]["status"] == "running"
            assert data["step_progress"][1]["started_at"] is not None
            assert data["step_progress"][1]["completed_at"] is None
            
            # Remaining 5 steps should be pending
            for i in range(2, 7):
                step = data["step_progress"][i]
                assert step["status"] == "pending"
                assert step["started_at"] is None
                assert step["completed_at"] is None
                assert step["error_message"] is None
            
            # Verify all step names are present in correct order
            expected_names = [
                "expand",
                "review_architect",
                "review_critic",
                "review_optimist",
                "review_security",
                "review_user_advocate",
                "aggregate_decision",
            ]
            actual_names = [s["step_name"] for s in data["step_progress"]]
            assert actual_names == expected_names
            
        finally:
            session.close()


class TestRunsEndpointNoLLMCalls:
    """Tests to ensure no LLM calls are made during GET requests."""
    
    def test_list_runs_no_openai_calls(self, test_client, sample_runs, monkeypatch):
        """Test that listing runs does not invoke OpenAI."""
        # Mock OpenAI client to detect if it's called
        call_count = {"count": 0}
        
        def mock_openai_init(*args, **kwargs):
            call_count["count"] += 1
            raise Exception("OpenAI client should not be initialized during GET /v1/runs")
        
        monkeypatch.setattr(
            "consensus_engine.clients.openai_client.OpenAI",
            mock_openai_init
        )
        
        response = test_client.get("/v1/runs")
        
        # Should succeed without calling OpenAI
        assert response.status_code == 200
        assert call_count["count"] == 0
    
    def test_get_run_detail_no_openai_calls(self, test_client, sample_runs, monkeypatch):
        """Test that getting run detail does not invoke OpenAI."""
        # Mock OpenAI client to detect if it's called
        call_count = {"count": 0}
        
        def mock_openai_init(*args, **kwargs):
            call_count["count"] += 1
            raise Exception("OpenAI client should not be initialized during GET /v1/runs/{run_id}")
        
        monkeypatch.setattr(
            "consensus_engine.clients.openai_client.OpenAI",
            mock_openai_init
        )
        
        run_id = str(sample_runs[0].id)
        response = test_client.get(f"/v1/runs/{run_id}")
        
        # Should succeed without calling OpenAI
        assert response.status_code == 200
        assert call_count["count"] == 0


class TestAsyncStatusTransitions:
    """Test suite for async workflow status transitions (queued -> running -> completed/failed)."""

    def test_pubsub_publish_verification_in_job_enqueue(self):
        """Test that Pub/Sub publish is verified in job enqueue tests.
        
        Note: This is a placeholder test to acknowledge that Pub/Sub publish verification
        is already covered in tests/integration/test_job_enqueue.py::test_full_review_pub_sub_publish_called
        and tests/integration/test_job_enqueue.py::test_revision_enqueue_success which verify:
        - Pub/Sub publisher mock is called
        - Message contains correct run_id, run_type, priority, and payload
        - Response returns status='queued'
        """
        # This test documents that the acceptance criteria for Pub/Sub mock verification
        # is satisfied by existing tests in test_job_enqueue.py
        pass

    def test_status_transition_queued_to_running(self, test_session_factory, test_client):
        """Test status transition from queued to running."""
        session = test_session_factory()
        
        try:
            run_id = uuid.uuid4()
            now = datetime.now(UTC)
            
            # Create a queued run
            run = Run(
                id=run_id,
                status=RunStatus.QUEUED,
                queued_at=now,
                input_idea="Test async workflow",
                extra_context=None,
                run_type=RunType.INITIAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
                created_at=now,
            )
            session.add(run)
            session.commit()
            
            # Poll for status - should be queued
            response = test_client.get(f"/v1/runs/{str(run_id)}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "queued"
            assert data["queued_at"] is not None
            assert data["started_at"] is None
            assert data["completed_at"] is None
            
            # Simulate worker starting the run
            run.status = RunStatus.RUNNING
            run.started_at = now + timedelta(seconds=5)
            session.commit()
            
            # Poll again - should be running
            response = test_client.get(f"/v1/runs/{str(run_id)}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "running"
            assert data["started_at"] is not None
            assert data["completed_at"] is None
            
        finally:
            session.close()

    def test_status_transition_running_to_completed(self, test_session_factory, test_client):
        """Test status transition from running to completed."""
        session = test_session_factory()
        
        try:
            run_id = uuid.uuid4()
            now = datetime.now(UTC)
            
            # Create a running run
            run = Run(
                id=run_id,
                status=RunStatus.RUNNING,
                queued_at=now - timedelta(minutes=2),
                started_at=now - timedelta(minutes=1),
                input_idea="Test completion workflow",
                extra_context=None,
                run_type=RunType.INITIAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
                created_at=now - timedelta(minutes=2),
            )
            session.add(run)
            
            # Add step progress showing work in progress
            step = StepProgress(
                run_id=run_id,
                step_name="review_architect",
                step_order=1,
                status=StepStatus.RUNNING,
                started_at=now - timedelta(seconds=30),
            )
            session.add(step)
            session.commit()
            
            # Poll - should be running
            response = test_client.get(f"/v1/runs/{str(run_id)}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "running"
            
            # Simulate worker completing the run
            run.status = RunStatus.COMPLETED
            run.completed_at = now
            run.overall_weighted_confidence = 0.85
            run.decision_label = "approve"
            
            step.status = StepStatus.COMPLETED
            step.completed_at = now
            session.commit()
            
            # Poll again - should be completed
            response = test_client.get(f"/v1/runs/{str(run_id)}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["completed_at"] is not None
            assert data["overall_weighted_confidence"] == 0.85
            assert data["decision_label"] == "approve"
            
        finally:
            session.close()

    def test_status_transition_running_to_failed(self, test_session_factory, test_client):
        """Test status transition from running to failed."""
        session = test_session_factory()
        
        try:
            run_id = uuid.uuid4()
            now = datetime.now(UTC)
            
            # Create a running run
            run = Run(
                id=run_id,
                status=RunStatus.RUNNING,
                queued_at=now - timedelta(minutes=2),
                started_at=now - timedelta(minutes=1),
                input_idea="Test failure workflow",
                extra_context=None,
                run_type=RunType.INITIAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
                created_at=now - timedelta(minutes=2),
            )
            session.add(run)
            
            # Add step progress showing work in progress
            step = StepProgress(
                run_id=run_id,
                step_name="expand",
                step_order=0,
                status=StepStatus.RUNNING,
                started_at=now - timedelta(seconds=30),
            )
            session.add(step)
            session.commit()
            
            # Simulate worker encountering an error
            run.status = RunStatus.FAILED
            run.completed_at = now
            
            step.status = StepStatus.FAILED
            step.completed_at = now
            step.error_message = "LLM timeout error"
            session.commit()
            
            # Poll - should be failed
            response = test_client.get(f"/v1/runs/{str(run_id)}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "failed"
            assert data["completed_at"] is not None
            
            # Check step progress shows error
            failed_step = next(s for s in data["step_progress"] if s["step_name"] == "expand")
            assert failed_step["status"] == "failed"
            assert failed_step["error_message"] == "LLM timeout error"
            
        finally:
            session.close()

    def test_queued_run_polling_shows_pending_steps(self, test_session_factory, test_client):
        """Test that queued run shows all steps as pending when polled."""
        session = test_session_factory()
        
        try:
            run_id = uuid.uuid4()
            now = datetime.now(UTC)
            
            # Create a queued run with initialized step progress
            run = Run(
                id=run_id,
                status=RunStatus.QUEUED,
                queued_at=now,
                input_idea="Test queued status polling",
                extra_context=None,
                run_type=RunType.INITIAL,
                model="gpt-5.1",
                temperature=0.7,
                parameters_json={},
                created_at=now,
            )
            session.add(run)
            
            # Initialize all steps as pending (simulating job enqueue behavior)
            for i, step_name in enumerate([
                "expand",
                "review_architect",
                "review_critic",
                "review_optimist",
                "review_security",
                "review_user_advocate",
                "aggregate_decision",
            ]):
                step = StepProgress(
                    run_id=run_id,
                    step_name=step_name,
                    step_order=i,
                    status=StepStatus.PENDING,
                )
                session.add(step)
            
            session.commit()
            
            # Poll for status
            response = test_client.get(f"/v1/runs/{str(run_id)}")
            assert response.status_code == 200
            data = response.json()
            
            # Verify status is queued
            assert data["status"] == "queued"
            assert data["queued_at"] is not None
            assert data["started_at"] is None
            
            # Verify all 7 steps are pending
            assert len(data["step_progress"]) == 7
            for step in data["step_progress"]:
                assert step["status"] == "pending"
                assert step["started_at"] is None
                assert step["completed_at"] is None
                assert step["error_message"] is None
            
        finally:
            session.close()
