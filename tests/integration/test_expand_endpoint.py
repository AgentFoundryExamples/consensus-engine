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
"""Integration tests for expand-idea endpoint."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from consensus_engine.app import create_app
from consensus_engine.exceptions import (
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    SchemaValidationError,
)
from consensus_engine.schemas.proposal import ExpandedProposal


@pytest.fixture
def valid_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up valid test environment."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-expand-endpoint")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.1")
    monkeypatch.setenv("TEMPERATURE", "0.7")
    monkeypatch.setenv("ENV", "testing")


@pytest.fixture
def client(valid_test_env: None) -> Generator[TestClient, None, None]:
    """Create test client with valid environment."""
    from consensus_engine.config import get_settings

    get_settings.cache_clear()

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


class TestExpandIdeaEndpoint:
    """Test suite for POST /v1/expand-idea endpoint."""

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_success(self, mock_client_class: MagicMock, client: TestClient) -> None:
        """Test successful idea expansion."""
        # Setup mock
        mock_proposal = ExpandedProposal(
            problem_statement="Clear problem statement",
            proposed_solution="Detailed solution approach",
            assumptions=["Assumption 1", "Assumption 2"],
            scope_non_goals=["Out of scope 1"],
            raw_expanded_proposal="Full proposal text",
        )
        mock_metadata = {
            "request_id": "test-request-123",
            "model": "gpt-5.1",
            "temperature": 0.7,
            "elapsed_time": 2.5,
        }

        mock_client = MagicMock()
        mock_client.create_structured_response.return_value = (mock_proposal, mock_metadata)
        mock_client_class.return_value = mock_client

        # Make request
        response = client.post(
            "/v1/expand-idea",
            json={"idea": "Build a REST API for user management."},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["problem_statement"] == "Clear problem statement"
        assert data["proposed_solution"] == "Detailed solution approach"
        assert len(data["assumptions"]) == 2
        assert len(data["scope_non_goals"]) == 1
        assert data["metadata"]["request_id"] == "test-request-123"
        assert "X-Request-ID" in response.headers

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_with_extra_context_string(
        self, mock_client_class: MagicMock, client: TestClient
    ) -> None:
        """Test idea expansion with extra context as string."""
        # Setup mock
        mock_proposal = ExpandedProposal(
            problem_statement="Problem",
            proposed_solution="Solution",
        )
        mock_metadata = {"request_id": "test-request-456"}

        mock_client = MagicMock()
        mock_client.create_structured_response.return_value = (mock_proposal, mock_metadata)
        mock_client_class.return_value = mock_client

        # Make request
        response = client.post(
            "/v1/expand-idea",
            json={"idea": "Build an API.", "extra_context": "Must support Python 3.11+"},
        )

        # Verify response
        assert response.status_code == 200

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_with_extra_context_dict(
        self, mock_client_class: MagicMock, client: TestClient
    ) -> None:
        """Test idea expansion with extra context as dict."""
        # Setup mock
        mock_proposal = ExpandedProposal(
            problem_statement="Problem",
            proposed_solution="Solution",
        )
        mock_metadata = {"request_id": "test-request-789"}

        mock_client = MagicMock()
        mock_client.create_structured_response.return_value = (mock_proposal, mock_metadata)
        mock_client_class.return_value = mock_client

        # Make request
        response = client.post(
            "/v1/expand-idea",
            json={
                "idea": "Build an API.",
                "extra_context": {"language": "Python", "version": "3.11+"},
            },
        )

        # Verify response
        assert response.status_code == 200

    def test_expand_idea_validation_error_empty_idea(self, client: TestClient) -> None:
        """Test validation error for empty idea."""
        response = client.post(
            "/v1/expand-idea",
            json={"idea": ""},
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert "request_id" in data

    def test_expand_idea_validation_error_missing_idea(self, client: TestClient) -> None:
        """Test validation error for missing idea field."""
        response = client.post(
            "/v1/expand-idea",
            json={},
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"

    def test_expand_idea_validation_error_too_many_sentences(self, client: TestClient) -> None:
        """Test validation error for too many sentences."""
        # Create idea with more than 10 sentences
        idea = "One. Two. Three. Four. Five. Six. Seven. Eight. Nine. Ten. Eleven."
        response = client.post(
            "/v1/expand-idea",
            json={"idea": idea},
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert any("must contain at most 10 sentences" in str(detail) for detail in data["details"])

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_authentication_error(
        self, mock_client_class: MagicMock, client: TestClient
    ) -> None:
        """Test authentication error handling."""
        # Setup mock to raise auth error
        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = LLMAuthenticationError(
            "Invalid API key", details={"request_id": "test-auth-error"}
        )
        mock_client_class.return_value = mock_client

        # Make request
        response = client.post(
            "/v1/expand-idea",
            json={"idea": "Build an API."},
        )

        # Verify response
        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["code"] == "LLM_AUTH_ERROR"
        assert "Invalid API key" in data["detail"]["message"]

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_rate_limit_error(
        self, mock_client_class: MagicMock, client: TestClient
    ) -> None:
        """Test rate limit error handling."""
        # Setup mock to raise rate limit error
        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = LLMRateLimitError(
            "Rate limit exceeded", details={"request_id": "test-rate-limit", "retryable": True}
        )
        mock_client_class.return_value = mock_client

        # Make request
        response = client.post(
            "/v1/expand-idea",
            json={"idea": "Build an API."},
        )

        # Verify response
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["code"] == "LLM_RATE_LIMIT"
        assert data["detail"]["details"]["retryable"] is True

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_timeout_error(
        self, mock_client_class: MagicMock, client: TestClient
    ) -> None:
        """Test timeout error handling."""
        # Setup mock to raise timeout error
        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = LLMTimeoutError(
            "Request timed out", details={"request_id": "test-timeout", "retryable": True}
        )
        mock_client_class.return_value = mock_client

        # Make request
        response = client.post(
            "/v1/expand-idea",
            json={"idea": "Build an API."},
        )

        # Verify response
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["code"] == "LLM_TIMEOUT"

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_schema_validation_error(
        self, mock_client_class: MagicMock, client: TestClient
    ) -> None:
        """Test schema validation error handling."""
        # Setup mock to raise schema error
        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = SchemaValidationError(
            "Invalid response schema", details={"request_id": "test-schema-error"}
        )
        mock_client_class.return_value = mock_client

        # Make request
        response = client.post(
            "/v1/expand-idea",
            json={"idea": "Build an API."},
        )

        # Verify response
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["code"] == "SCHEMA_VALIDATION_ERROR"

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_unexpected_error(
        self, mock_client_class: MagicMock, client: TestClient
    ) -> None:
        """Test unexpected error handling."""
        # Setup mock to raise unexpected error
        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = RuntimeError("Unexpected error")
        mock_client_class.return_value = mock_client

        # Make request
        response = client.post(
            "/v1/expand-idea",
            json={"idea": "Build an API."},
        )

        # Verify response
        assert response.status_code == 500
        data = response.json()
        assert data["detail"]["code"] == "INTERNAL_ERROR"

    def test_expand_idea_endpoint_in_openapi_schema(self, client: TestClient) -> None:
        """Test that expand-idea endpoint is documented in OpenAPI schema."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()

        # Verify endpoint exists
        assert "/v1/expand-idea" in schema["paths"]
        assert "post" in schema["paths"]["/v1/expand-idea"]

        # Verify endpoint details
        endpoint = schema["paths"]["/v1/expand-idea"]["post"]
        assert endpoint["summary"] == "Expand an idea into a detailed proposal"
        assert "200" in endpoint["responses"]
        assert "422" in endpoint["responses"]
        assert "500" in endpoint["responses"]
        assert "503" in endpoint["responses"]


class TestHealthEndpoint:
    """Test suite for GET /health endpoint."""

    def test_health_check_success(self, client: TestClient) -> None:
        """Test health check returns correct information."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["environment"] == "testing"
        assert data["debug"] is False
        assert data["model"] == "gpt-5.1"
        assert data["temperature"] == 0.7
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0
        assert data["config_status"] == "ok"
        assert "X-Request-ID" in response.headers

    def test_health_check_multiple_calls(self, client: TestClient) -> None:
        """Test health check uptime increases across calls."""
        import time

        response1 = client.get("/health")
        uptime1 = response1.json()["uptime_seconds"]

        time.sleep(0.1)

        response2 = client.get("/health")
        uptime2 = response2.json()["uptime_seconds"]

        assert uptime2 > uptime1

    def test_health_endpoint_in_openapi_schema(self, client: TestClient) -> None:
        """Test that health endpoint is documented in OpenAPI schema."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()

        # Verify endpoint exists
        assert "/health" in schema["paths"]
        assert "get" in schema["paths"]["/health"]

        # Verify endpoint details
        endpoint = schema["paths"]["/health"]["get"]
        assert endpoint["summary"] == "Health check endpoint"
        assert "200" in endpoint["responses"]


class TestMiddleware:
    """Test suite for middleware functionality."""

    def test_request_id_in_response_headers(self, client: TestClient) -> None:
        """Test that request ID is added to response headers."""
        response = client.get("/")
        assert "X-Request-ID" in response.headers
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) > 0

    def test_unique_request_ids(self, client: TestClient) -> None:
        """Test that each request gets a unique request ID."""
        response1 = client.get("/")
        response2 = client.get("/")

        request_id1 = response1.headers["X-Request-ID"]
        request_id2 = response2.headers["X-Request-ID"]

        assert request_id1 != request_id2


class TestExceptionHandlers:
    """Test suite for global exception handlers."""

    def test_validation_error_handler(self, client: TestClient) -> None:
        """Test global validation error handler."""
        response = client.post("/v1/expand-idea", json={"invalid": "data"})

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert data["message"] == "Request validation failed"
        assert "details" in data
        assert "request_id" in data
