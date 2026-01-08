"""Additional unit tests for diff endpoint without database.

These tests use mocked dependencies to test the endpoint logic.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from consensus_engine.app import create_app
from consensus_engine.db.models import Run, RunStatus, RunType


@pytest.fixture
def test_client(monkeypatch):
    """Create a test client without database."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-diff-unit")
    
    app = create_app()
    with TestClient(app) as client:
        yield client


class TestDiffEndpointUnit:
    """Unit tests for diff endpoint with mocked database."""

    @patch("consensus_engine.api.routes.runs.RunRepository.get_run_with_relations")
    @patch("consensus_engine.api.routes.runs.compute_run_diff")
    def test_diff_endpoint_success(
        self, mock_compute_diff, mock_get_run, test_client, monkeypatch
    ):
        """Test successful diff computation."""
        # Mock database session
        mock_session = MagicMock()
        
        def mock_get_db():
            yield mock_session
        
        from consensus_engine.db.dependencies import get_db_session
        from consensus_engine.app import create_app
        
        app = create_app()
        app.dependency_overrides[get_db_session] = mock_get_db
        
        # Create mock runs
        run1 = MagicMock(spec=Run)
        run1.id = uuid.uuid4()
        run1.parent_run_id = None
        run1.created_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        run1.overall_weighted_confidence = 0.75
        run1.decision_label = "revise"
        run1.proposal_version = None
        run1.persona_reviews = []
        
        run2 = MagicMock(spec=Run)
        run2.id = uuid.uuid4()
        run2.parent_run_id = None
        run2.created_at = datetime(2026, 1, 2, 12, 0, 0, tzinfo=UTC)
        run2.overall_weighted_confidence = 0.85
        run2.decision_label = "approve"
        run2.proposal_version = None
        run2.persona_reviews = []
        
        # Mock repository calls
        mock_get_run.side_effect = [run1, run2]
        
        # Mock diff computation
        mock_compute_diff.return_value = {
            "metadata": {
                "run1_id": str(run1.id),
                "run2_id": str(run2.id),
                "is_parent_child": False,
                "relationship": "unrelated",
            },
            "proposal_changes": {"status": "both_missing"},
            "persona_deltas": [],
            "decision_delta": {
                "old_overall_weighted_confidence": 0.75,
                "new_overall_weighted_confidence": 0.85,
                "confidence_delta": 0.10,
                "old_decision_label": "revise",
                "new_decision_label": "approve",
                "decision_changed": True,
            },
        }
        
        # Make request
        with TestClient(app) as client:
            response = client.get(f"/v1/runs/{run1.id}/diff/{run2.id}")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["metadata"]["is_parent_child"] is False
        assert data["decision_delta"]["decision_changed"] is True

    def test_diff_identical_runs_validation(self, test_client):
        """Test validation rejects identical run IDs."""
        run_id = uuid.uuid4()
        
        response = test_client.get(f"/v1/runs/{run_id}/diff/{run_id}")
        
        assert response.status_code == 400
        data = response.json()
        assert "cannot diff a run against itself" in data["detail"].lower()

    def test_diff_invalid_uuid_validation(self, test_client):
        """Test validation rejects invalid UUIDs."""
        response = test_client.get("/v1/runs/invalid-uuid/diff/another-invalid")
        
        assert response.status_code == 400

    @patch("consensus_engine.api.routes.runs.RunRepository.get_run_with_relations")
    def test_diff_missing_run_returns_404(self, mock_get_run, test_client, monkeypatch):
        """Test 404 when run is missing."""
        # Mock database session
        mock_session = MagicMock()
        
        def mock_get_db():
            yield mock_session
        
        from consensus_engine.db.dependencies import get_db_session
        from consensus_engine.app import create_app
        
        app = create_app()
        app.dependency_overrides[get_db_session] = mock_get_db
        
        # Mock repository to return None (run not found)
        mock_get_run.return_value = None
        
        run1_id = uuid.uuid4()
        run2_id = uuid.uuid4()
        
        with TestClient(app) as client:
            response = client.get(f"/v1/runs/{run1_id}/diff/{run2_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
