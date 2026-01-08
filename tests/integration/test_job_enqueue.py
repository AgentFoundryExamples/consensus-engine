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
"""Integration tests for job enqueueing endpoints."""

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from consensus_engine.app import create_app
from consensus_engine.clients.pubsub import PubSubPublishError
from consensus_engine.db.models import Run, RunPriority, RunStatus, RunType


@pytest.fixture
def valid_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up valid test environment with mock Pub/Sub."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-job-enqueue-tests")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.1")
    monkeypatch.setenv("TEMPERATURE", "0.7")
    monkeypatch.setenv("ENV", "testing")
    monkeypatch.setenv("PUBSUB_USE_MOCK", "true")
    monkeypatch.setenv("PUBSUB_TOPIC", "test-jobs")


@pytest.fixture
def client(valid_test_env: None) -> Generator[TestClient, None, None]:
    """Create test client with valid environment."""
    from consensus_engine.config import get_settings

    get_settings.cache_clear()

    app = create_app()
    
    with TestClient(app) as test_client:
        yield test_client


class TestFullReviewJobEnqueue:
    """Test suite for POST /v1/full-review job enqueueing."""

    @patch("consensus_engine.api.routes.full_review.get_publisher")
    @patch("consensus_engine.api.routes.full_review.StepProgressRepository")
    @patch("consensus_engine.api.routes.full_review.RunRepository")
    def test_full_review_enqueue_success(
        self,
        mock_run_repo: MagicMock,
        mock_step_repo: MagicMock,
        mock_get_publisher: MagicMock,
        client: TestClient,
    ) -> None:
        """Test successful job enqueueing for full review."""
        # Mock database operations
        mock_run = Mock(spec=Run)
        mock_run.id = UUID("00000000-0000-0000-0000-000000000001")
        mock_run.status = RunStatus.QUEUED
        mock_run.run_type = RunType.INITIAL
        mock_run.priority = RunPriority.NORMAL
        mock_run.created_at = datetime.now(UTC)
        mock_run.queued_at = datetime.now(UTC)
        
        mock_run_repo.create_run.return_value = mock_run
        
        # Mock Pub/Sub publisher
        mock_publisher = Mock()
        mock_publisher.publish.return_value = "mock-message-id"
        mock_get_publisher.return_value = mock_publisher
        
        request_data = {
            "idea": "Build a REST API for user management with authentication.",
            "extra_context": {"language": "Python", "version": "3.11+"},
        }

        response = client.post("/v1/full-review", json=request_data)

        assert response.status_code == 202
        data = response.json()
        
        # Verify response structure
        assert "run_id" in data
        assert data["status"] == "queued"
        assert data["run_type"] == "initial"
        assert data["priority"] == "normal"
        assert "created_at" in data
        assert "queued_at" in data
        assert "message" in data
        assert "Poll GET /v1/runs/" in data["message"]
        
        # Verify database and publisher were called
        mock_run_repo.create_run.assert_called_once()
        mock_publisher.publish.assert_called_once()

    def test_full_review_enqueue_validates_idea(self, client: TestClient) -> None:
        """Test that idea validation still works."""
        # Too many sentences (>10)
        request_data = {
            "idea": ". ".join(["Test sentence" for _ in range(15)]),
        }

        response = client.post("/v1/full-review", json=request_data)

        assert response.status_code == 422
        data = response.json()
        # FastAPI wraps validation errors in a different structure
        assert "code" in data or "detail" in data

    @patch("consensus_engine.api.routes.full_review.get_publisher")
    @patch("consensus_engine.api.routes.full_review.StepProgressRepository")
    @patch("consensus_engine.api.routes.full_review.RunRepository")
    def test_full_review_enqueue_with_string_context(
        self,
        mock_run_repo: MagicMock,
        mock_step_repo: MagicMock,
        mock_get_publisher: MagicMock,
        client: TestClient,
    ) -> None:
        """Test full review with string extra_context."""
        # Mock database operations
        mock_run = Mock(spec=Run)
        mock_run.id = UUID("00000000-0000-0000-0000-000000000001")
        mock_run.status = RunStatus.QUEUED
        mock_run.run_type = RunType.INITIAL
        mock_run.priority = RunPriority.NORMAL
        mock_run.created_at = datetime.now(UTC)
        mock_run.queued_at = datetime.now(UTC)
        
        mock_run_repo.create_run.return_value = mock_run
        
        # Mock Pub/Sub publisher
        mock_publisher = Mock()
        mock_publisher.publish.return_value = "mock-message-id"
        mock_get_publisher.return_value = mock_publisher
        
        request_data = {
            "idea": "Build a REST API for user management.",
            "extra_context": "Must support Python 3.11+",
        }

        response = client.post("/v1/full-review", json=request_data)

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "queued"

    @patch("consensus_engine.api.routes.full_review.get_publisher")
    @patch("consensus_engine.api.routes.full_review.StepProgressRepository")
    @patch("consensus_engine.api.routes.full_review.RunRepository")
    @patch("consensus_engine.api.routes.full_review.uuid.uuid4")
    def test_full_review_pub_sub_publish_called(
        self,
        mock_uuid: MagicMock,
        mock_run_repo: MagicMock,
        mock_step_repo: MagicMock,
        mock_get_publisher: MagicMock,
        client: TestClient,
    ) -> None:
        """Test that Pub/Sub publish is called with correct parameters."""
        # Mock UUID generation
        test_run_id = UUID("00000000-0000-0000-0000-000000000001")
        mock_uuid.return_value = test_run_id
        
        # Mock database operations
        mock_run = Mock(spec=Run)
        mock_run.id = test_run_id
        mock_run.status = RunStatus.QUEUED
        mock_run.run_type = RunType.INITIAL
        mock_run.priority = RunPriority.NORMAL
        mock_run.created_at = datetime.now(UTC)
        mock_run.queued_at = datetime.now(UTC)
        
        mock_run_repo.create_run.return_value = mock_run
        
        # Mock Pub/Sub publisher
        mock_publisher = Mock()
        mock_publisher.publish.return_value = "mock-message-id"
        mock_get_publisher.return_value = mock_publisher
        
        request_data = {
            "idea": "Build a REST API for user management.",
        }

        response = client.post("/v1/full-review", json=request_data)

        assert response.status_code == 202
        data = response.json()
        
        # Verify publish was called
        mock_publisher.publish.assert_called_once()
        call_args = mock_publisher.publish.call_args[1]
        
        # The run_id in the response should match the mocked UUID
        assert call_args["run_id"] == str(test_run_id)
        assert call_args["run_type"] == "initial"
        assert call_args["priority"] == "normal"
        assert "payload" in call_args
        assert call_args["payload"]["idea"] == request_data["idea"]

    @patch("consensus_engine.api.routes.full_review.get_publisher")
    @patch("consensus_engine.api.routes.full_review.StepProgressRepository")
    @patch("consensus_engine.api.routes.full_review.RunRepository")
    def test_full_review_rollback_on_publish_failure(
        self,
        mock_run_repo: MagicMock,
        mock_step_repo: MagicMock,
        mock_get_publisher: MagicMock,
        client: TestClient,
    ) -> None:
        """Test that database changes are rolled back when Pub/Sub publish fails."""
        # Mock database operations
        mock_run = Mock(spec=Run)
        mock_run.id = UUID("00000000-0000-0000-0000-000000000001")
        mock_run.status = RunStatus.QUEUED
        mock_run.run_type = RunType.INITIAL
        mock_run.priority = RunPriority.NORMAL
        mock_run.created_at = datetime.now(UTC)
        mock_run.queued_at = datetime.now(UTC)
        
        mock_run_repo.create_run.return_value = mock_run
        
        # Mock Pub/Sub publisher to raise error
        mock_publisher = Mock()
        mock_publisher.publish.side_effect = PubSubPublishError("Pub/Sub error")
        mock_get_publisher.return_value = mock_publisher
        
        request_data = {
            "idea": "Build a REST API for user management.",
        }

        response = client.post("/v1/full-review", json=request_data)

        # Should return 503 Service Unavailable
        assert response.status_code == 503
        data = response.json()
        assert data["code"] == "PUBSUB_PUBLISH_ERROR"
        assert "run_id" in data


class TestRevisionJobEnqueue:
    """Test suite for POST /v1/runs/{run_id}/revisions job enqueueing."""

    @patch("consensus_engine.api.routes.runs.get_publisher")
    @patch("consensus_engine.api.routes.runs.StepProgressRepository")
    @patch("consensus_engine.api.routes.runs.RunRepository")
    def test_revision_enqueue_requires_completed_parent(
        self,
        mock_run_repo: MagicMock,
        mock_step_repo: MagicMock,
        mock_get_publisher: MagicMock,
        client: TestClient,
    ) -> None:
        """Test that revision requires a completed parent run."""
        # Mock RunRepository.get_run_with_relations to return None (not found)
        mock_run_repo.get_run_with_relations.return_value = None
        
        request_data = {
            "edited_proposal": "Updated proposal text",
            "edit_notes": "Revised based on feedback",
        }

        response = client.post(
            "/v1/runs/00000000-0000-0000-0000-000000000001/revisions",
            json=request_data,
        )

        # Should return 404 Not Found for non-existent parent
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_revision_enqueue_validates_edit_inputs(self, client: TestClient) -> None:
        """Test that revision requires at least one edit input."""
        request_data = {}

        response = client.post(
            "/v1/runs/00000000-0000-0000-0000-000000000001/revisions",
            json=request_data,
        )

        # Should return 400 Bad Request
        assert response.status_code == 400
        data = response.json()
        assert "edit" in data["detail"].lower()

    def test_revision_enqueue_validates_parent_run_id(self, client: TestClient) -> None:
        """Test that invalid parent run_id is rejected."""
        request_data = {
            "edited_proposal": "Updated proposal text",
        }

        response = client.post(
            "/v1/runs/invalid-uuid/revisions",
            json=request_data,
        )

        # Should return 400 Bad Request for invalid UUID
        assert response.status_code == 400
        data = response.json()
        assert "invalid" in data["detail"].lower()

    @patch("consensus_engine.api.routes.runs.get_publisher")
    @patch("consensus_engine.api.routes.runs.StepProgressRepository")
    @patch("consensus_engine.api.routes.runs.RunRepository")
    def test_revision_enqueue_success(
        self,
        mock_run_repo: MagicMock,
        mock_step_repo: MagicMock,
        mock_get_publisher: MagicMock,
        client: TestClient,
    ) -> None:
        """Test successful revision job enqueueing."""
        # Mock parent run with required relations
        parent_run = Mock(spec=Run)
        parent_run.id = UUID("00000000-0000-0000-0000-000000000001")
        parent_run.status = RunStatus.COMPLETED
        parent_run.input_idea = "Original idea"
        parent_run.extra_context = None
        parent_run.model = "gpt-5.1"
        parent_run.temperature = 0.7
        parent_run.parameters_json = {}
        parent_run.priority = RunPriority.NORMAL
        # Add required relations
        parent_run.proposal_version = Mock()
        parent_run.persona_reviews = [Mock()]
        
        mock_run_repo.get_run_with_relations.return_value = parent_run
        
        # Mock new run
        new_run = Mock(spec=Run)
        new_run.id = UUID("00000000-0000-0000-0000-000000000002")
        new_run.status = RunStatus.QUEUED
        new_run.run_type = RunType.REVISION
        new_run.priority = RunPriority.NORMAL
        new_run.created_at = datetime.now(UTC)
        new_run.queued_at = datetime.now(UTC)
        
        mock_run_repo.create_run.return_value = new_run
        
        # Mock Pub/Sub publisher
        mock_publisher = Mock()
        mock_publisher.publish.return_value = "mock-message-id"
        mock_get_publisher.return_value = mock_publisher
        
        request_data = {
            "edited_proposal": "Updated proposal text",
            "edit_notes": "Revised based on feedback",
        }

        response = client.post(
            "/v1/runs/00000000-0000-0000-0000-000000000001/revisions",
            json=request_data,
        )

        assert response.status_code == 202
        data = response.json()
        
        # Verify response structure
        assert "run_id" in data
        assert data["status"] == "queued"
        assert data["run_type"] == "revision"
        assert data["priority"] == "normal"
        assert "created_at" in data
        assert "queued_at" in data
        assert "message" in data
        
        # Verify database and publisher were called
        mock_run_repo.create_run.assert_called_once()
        mock_publisher.publish.assert_called_once()


class TestPubSubIntegration:
    """Test suite for Pub/Sub integration behavior."""

    @patch("consensus_engine.api.routes.full_review.get_publisher")
    @patch("consensus_engine.api.routes.full_review.StepProgressRepository")
    @patch("consensus_engine.api.routes.full_review.RunRepository")
    def test_mock_publisher_used_in_test_mode(
        self,
        mock_run_repo: MagicMock,
        mock_step_repo: MagicMock,
        mock_get_publisher: MagicMock,
        client: TestClient,
    ) -> None:
        """Test that mock publisher is used when PUBSUB_USE_MOCK=true."""
        # Mock database operations
        mock_run = Mock(spec=Run)
        mock_run.id = UUID("00000000-0000-0000-0000-000000000001")
        mock_run.status = RunStatus.QUEUED
        mock_run.run_type = RunType.INITIAL
        mock_run.priority = RunPriority.NORMAL
        mock_run.created_at = datetime.now(UTC)
        mock_run.queued_at = datetime.now(UTC)
        
        mock_run_repo.create_run.return_value = mock_run
        
        # Mock Pub/Sub publisher
        mock_publisher = Mock()
        mock_publisher.publish.return_value = "mock-message-id"
        mock_get_publisher.return_value = mock_publisher
        
        request_data = {
            "idea": "Build a REST API for user management.",
        }

        # This should succeed without needing real Pub/Sub credentials
        response = client.post("/v1/full-review", json=request_data)

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "queued"
