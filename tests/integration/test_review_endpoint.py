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
"""Integration tests for review-idea endpoint."""

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
from consensus_engine.schemas.review import BlockingIssue, Concern, PersonaReview


@pytest.fixture
def valid_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up valid test environment."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-review-endpoint")
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


class TestReviewIdeaEndpoint:
    """Test suite for POST /v1/review-idea endpoint."""

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_review_idea_success(
        self,
        mock_expand_client_class: MagicMock,
        mock_review_client_class: MagicMock,
        client: TestClient,
    ) -> None:
        """Test successful idea review orchestration (happy path)."""
        # Setup expand mock
        mock_proposal = ExpandedProposal(
            problem_statement="Clear problem statement",
            proposed_solution="Detailed solution approach",
            assumptions=["Assumption 1", "Assumption 2"],
            scope_non_goals=["Out of scope 1"],
            raw_expanded_proposal="Full proposal text",
        )
        mock_expand_metadata = {
            "request_id": "expand-request-123",
            "model": "gpt-5.1",
            "temperature": 0.7,
            "elapsed_time": 2.5,
        }

        mock_expand_client = MagicMock()
        mock_expand_client.create_structured_response.return_value = (
            mock_proposal,
            mock_expand_metadata,
        )
        mock_expand_client_class.return_value = mock_expand_client

        # Setup review mock
        mock_review = PersonaReview(
            persona_name="GenericReviewer",
            persona_id="genericreviewer",
            confidence_score=0.85,
            strengths=["Good architecture", "Clear scope"],
            concerns=[
                Concern(text="Missing error handling", is_blocking=False),
            ],
            recommendations=["Add error handling", "Include monitoring"],
            blocking_issues=[],
            estimated_effort="2-3 weeks",
            dependency_risks=["Database setup"],
        )
        mock_review_metadata = {
            "request_id": "review-request-456",
            "model": "gpt-5.1",
            "temperature": 0.2,
            "elapsed_time": 1.8,
        }

        mock_review_client = MagicMock()
        mock_review_client.create_structured_response.return_value = (
            mock_review,
            mock_review_metadata,
        )
        mock_review_client_class.return_value = mock_review_client

        # Make request
        response = client.post(
            "/v1/review-idea",
            json={"idea": "Build a REST API for user management."},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        # Check expanded_proposal
        assert "expanded_proposal" in data
        assert data["expanded_proposal"]["problem_statement"] == "Clear problem statement"
        assert data["expanded_proposal"]["proposed_solution"] == "Detailed solution approach"
        assert len(data["expanded_proposal"]["assumptions"]) == 2
        assert len(data["expanded_proposal"]["scope_non_goals"]) == 1

        # Check reviews
        assert "reviews" in data
        assert len(data["reviews"]) == 1
        assert data["reviews"][0]["persona_name"] == "GenericReviewer"
        assert data["reviews"][0]["confidence_score"] == 0.85
        assert len(data["reviews"][0]["strengths"]) == 2
        assert len(data["reviews"][0]["concerns"]) == 1
        assert data["reviews"][0]["concerns"][0]["is_blocking"] is False
        assert len(data["reviews"][0]["blocking_issues"]) == 0

        # Check draft_decision
        assert "draft_decision" in data
        assert data["draft_decision"]["overall_weighted_confidence"] == 0.85
        assert data["draft_decision"]["decision"] == "approve"  # >= 0.7 and no blocking issues
        assert "score_breakdown" in data["draft_decision"]
        assert "GenericReviewer" in data["draft_decision"]["score_breakdown"]
        assert data["draft_decision"]["score_breakdown"]["GenericReviewer"]["weight"] == 1.0
        assert data["draft_decision"]["minority_report"] is None

        # Check metadata
        assert "run_id" in data
        assert "elapsed_time" in data
        assert isinstance(data["elapsed_time"], int | float)
        assert data["elapsed_time"] > 0

        # Verify X-Request-ID header
        assert "X-Request-ID" in response.headers

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_review_idea_with_blocking_issues(
        self,
        mock_expand_client_class: MagicMock,
        mock_review_client_class: MagicMock,
        client: TestClient,
    ) -> None:
        """Test review-idea with blocking issues results in reject decision."""
        # Setup expand mock
        mock_proposal = ExpandedProposal(
            problem_statement="Problem statement",
            proposed_solution="Solution approach",
            assumptions=["Assumption 1"],
            scope_non_goals=["Out of scope 1"],
        )
        mock_expand_metadata = {
            "request_id": "expand-123",
            "model": "gpt-5.1",
            "temperature": 0.7,
            "elapsed_time": 2.0,
        }

        mock_expand_client = MagicMock()
        mock_expand_client.create_structured_response.return_value = (
            mock_proposal,
            mock_expand_metadata,
        )
        mock_expand_client_class.return_value = mock_expand_client

        # Setup review mock with blocking issues
        mock_review = PersonaReview(
            persona_name="GenericReviewer",
            persona_id="genericreviewer",
            confidence_score=0.75,  # High confidence but has blocking issues
            strengths=["Good architecture"],
            concerns=[
                Concern(text="Missing security audit", is_blocking=True),
            ],
            recommendations=["Add security audit"],
            blocking_issues=[BlockingIssue(text="Missing security audit")],
            estimated_effort="4 weeks",
            dependency_risks=[],
        )
        mock_review_metadata = {
            "request_id": "review-456",
            "model": "gpt-5.1",
            "temperature": 0.2,
            "elapsed_time": 1.5,
        }

        mock_review_client = MagicMock()
        mock_review_client.create_structured_response.return_value = (
            mock_review,
            mock_review_metadata,
        )
        mock_review_client_class.return_value = mock_review_client

        # Make request
        response = client.post(
            "/v1/review-idea",
            json={"idea": "Build a secure payment processing system."},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        # Check draft_decision reflects blocking issues
        assert data["draft_decision"]["decision"] == "reject"
        assert data["draft_decision"]["overall_weighted_confidence"] == 0.75

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_review_idea_with_low_confidence(
        self,
        mock_expand_client_class: MagicMock,
        mock_review_client_class: MagicMock,
        client: TestClient,
    ) -> None:
        """Test review-idea with low confidence results in revise decision."""
        # Setup expand mock
        mock_proposal = ExpandedProposal(
            problem_statement="Problem statement",
            proposed_solution="Solution approach",
            assumptions=["Assumption 1"],
            scope_non_goals=["Out of scope 1"],
        )
        mock_expand_metadata = {
            "request_id": "expand-123",
            "model": "gpt-5.1",
            "temperature": 0.7,
            "elapsed_time": 2.0,
        }

        mock_expand_client = MagicMock()
        mock_expand_client.create_structured_response.return_value = (
            mock_proposal,
            mock_expand_metadata,
        )
        mock_expand_client_class.return_value = mock_expand_client

        # Setup review mock with low confidence
        mock_review = PersonaReview(
            persona_name="GenericReviewer",
            persona_id="genericreviewer",
            confidence_score=0.5,  # Low confidence, no blocking issues
            strengths=["Clear problem statement"],
            concerns=[
                Concern(text="Unclear implementation details", is_blocking=False),
            ],
            recommendations=["Add more details", "Clarify architecture"],
            blocking_issues=[],
            estimated_effort="Unknown",
            dependency_risks=["Technology stack unclear"],
        )
        mock_review_metadata = {
            "request_id": "review-456",
            "model": "gpt-5.1",
            "temperature": 0.2,
            "elapsed_time": 1.5,
        }

        mock_review_client = MagicMock()
        mock_review_client.create_structured_response.return_value = (
            mock_review,
            mock_review_metadata,
        )
        mock_review_client_class.return_value = mock_review_client

        # Make request
        response = client.post(
            "/v1/review-idea",
            json={"idea": "Build something with AI."},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        # Check draft_decision reflects low confidence
        assert data["draft_decision"]["decision"] == "revise"
        assert data["draft_decision"]["overall_weighted_confidence"] == 0.5

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_review_idea_expansion_failure(
        self, mock_expand_client_class: MagicMock, client: TestClient
    ) -> None:
        """Test review-idea when expansion fails."""
        # Setup expand mock to raise error
        mock_expand_client = MagicMock()
        mock_expand_client.create_structured_response.side_effect = LLMTimeoutError(
            "Request timed out", details={"retryable": True}
        )
        mock_expand_client_class.return_value = mock_expand_client

        # Make request
        response = client.post(
            "/v1/review-idea",
            json={"idea": "Build a REST API for user management."},
        )

        # Verify error response
        assert response.status_code == 503  # Service unavailable for timeout
        data = response.json()

        # Check error structure
        assert data["code"] == "LLM_TIMEOUT"
        assert "message" in data
        assert data["failed_step"] == "expand"
        assert "run_id" in data
        assert data["partial_results"] is None  # No partial results since expand failed
        assert "details" in data
        assert data["details"]["retryable"] is True

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_review_idea_review_failure_with_partial_results(
        self,
        mock_expand_client_class: MagicMock,
        mock_review_client_class: MagicMock,
        client: TestClient,
    ) -> None:
        """Test review-idea when review fails after successful expansion."""
        # Setup expand mock to succeed
        mock_proposal = ExpandedProposal(
            problem_statement="Clear problem statement",
            proposed_solution="Detailed solution approach",
            assumptions=["Assumption 1"],
            scope_non_goals=["Out of scope 1"],
            raw_expanded_proposal="Full proposal text",
        )
        mock_expand_metadata = {
            "request_id": "expand-request-123",
            "model": "gpt-5.1",
            "temperature": 0.7,
            "elapsed_time": 2.5,
        }

        mock_expand_client = MagicMock()
        mock_expand_client.create_structured_response.return_value = (
            mock_proposal,
            mock_expand_metadata,
        )
        mock_expand_client_class.return_value = mock_expand_client

        # Setup review mock to raise error
        mock_review_client = MagicMock()
        mock_review_client.create_structured_response.side_effect = LLMRateLimitError(
            "Rate limit exceeded", details={"retryable": True}
        )
        mock_review_client_class.return_value = mock_review_client

        # Make request
        response = client.post(
            "/v1/review-idea",
            json={"idea": "Build a REST API for user management."},
        )

        # Verify error response
        assert response.status_code == 503  # Service unavailable for rate limit
        data = response.json()

        # Check error structure
        assert data["code"] == "LLM_RATE_LIMIT"
        assert "message" in data
        assert data["failed_step"] == "review"
        assert "run_id" in data

        # Check partial results include expanded proposal
        assert data["partial_results"] is not None
        assert "expanded_proposal" in data["partial_results"]
        assert (
            data["partial_results"]["expanded_proposal"]["problem_statement"]
            == "Clear problem statement"
        )
        assert (
            data["partial_results"]["expanded_proposal"]["proposed_solution"]
            == "Detailed solution approach"
        )

    def test_review_idea_invalid_input_empty_idea(self, client: TestClient) -> None:
        """Test review-idea with empty idea."""
        response = client.post(
            "/v1/review-idea",
            json={"idea": ""},
        )

        # Verify validation error
        assert response.status_code == 422
        data = response.json()

        assert data["code"] == "VALIDATION_ERROR"
        assert "details" in data
        assert len(data["details"]) > 0

    def test_review_idea_invalid_input_too_many_sentences(self, client: TestClient) -> None:
        """Test review-idea with too many sentences."""
        # Create an idea with 15 sentences (exceeds 10 limit)
        long_idea = " ".join([f"This is sentence {i}." for i in range(1, 16)])

        response = client.post(
            "/v1/review-idea",
            json={"idea": long_idea},
        )

        # Verify validation error
        assert response.status_code == 422
        data = response.json()

        assert data["code"] == "VALIDATION_ERROR"
        assert "details" in data

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_review_idea_with_extra_context_dict(
        self,
        mock_expand_client_class: MagicMock,
        mock_review_client_class: MagicMock,
        client: TestClient,
    ) -> None:
        """Test review-idea with extra context as dictionary."""
        # Setup mocks
        mock_proposal = ExpandedProposal(
            problem_statement="Problem statement",
            proposed_solution="Solution",
            assumptions=["Assumption 1"],
            scope_non_goals=["Out of scope"],
        )
        mock_expand_metadata = {
            "request_id": "expand-123",
            "model": "gpt-5.1",
            "temperature": 0.7,
            "elapsed_time": 2.0,
        }

        mock_expand_client = MagicMock()
        mock_expand_client.create_structured_response.return_value = (
            mock_proposal,
            mock_expand_metadata,
        )
        mock_expand_client_class.return_value = mock_expand_client

        mock_review = PersonaReview(
            persona_name="GenericReviewer",
            persona_id="genericreviewer",
            confidence_score=0.8,
            strengths=["Good"],
            concerns=[],
            recommendations=["Add tests"],
            blocking_issues=[],
            estimated_effort="2 weeks",
            dependency_risks=[],
        )
        mock_review_metadata = {
            "request_id": "review-456",
            "model": "gpt-5.1",
            "temperature": 0.2,
            "elapsed_time": 1.5,
        }

        mock_review_client = MagicMock()
        mock_review_client.create_structured_response.return_value = (
            mock_review,
            mock_review_metadata,
        )
        mock_review_client_class.return_value = mock_review_client

        # Make request with extra_context as dict
        response = client.post(
            "/v1/review-idea",
            json={
                "idea": "Build a REST API.",
                "extra_context": {"language": "Python", "version": "3.11+"},
            },
        )

        # Verify success
        assert response.status_code == 200
        data = response.json()
        assert "expanded_proposal" in data
        assert "reviews" in data
        assert "draft_decision" in data

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_review_idea_authentication_error(
        self, mock_expand_client_class: MagicMock, client: TestClient
    ) -> None:
        """Test review-idea with authentication error."""
        # Setup expand mock to raise auth error
        mock_expand_client = MagicMock()
        mock_expand_client.create_structured_response.side_effect = LLMAuthenticationError(
            "Invalid API key", details={}
        )
        mock_expand_client_class.return_value = mock_expand_client

        # Make request
        response = client.post(
            "/v1/review-idea",
            json={"idea": "Build a REST API."},
        )

        # Verify error response
        assert response.status_code == 401  # Unauthorized
        data = response.json()

        assert data["code"] == "LLM_AUTH_ERROR"
        assert data["failed_step"] == "expand"

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_review_idea_schema_validation_error(
        self, mock_expand_client_class: MagicMock, client: TestClient
    ) -> None:
        """Test review-idea with schema validation error."""
        # Setup expand mock to raise schema validation error
        mock_expand_client = MagicMock()
        mock_expand_client.create_structured_response.side_effect = SchemaValidationError(
            "Invalid schema", details={"field": "problem_statement"}
        )
        mock_expand_client_class.return_value = mock_expand_client

        # Make request
        response = client.post(
            "/v1/review-idea",
            json={"idea": "Build a REST API."},
        )

        # Verify error response
        assert response.status_code == 500  # Internal server error
        data = response.json()

        assert data["code"] == "SCHEMA_VALIDATION_ERROR"
        assert data["failed_step"] == "expand"

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_review_idea_client_cannot_control_model_settings(
        self,
        mock_expand_client_class: MagicMock,
        mock_review_client_class: MagicMock,
        client: TestClient,
    ) -> None:
        """Test that client cannot control model or temperature settings."""
        # Setup mocks
        mock_proposal = ExpandedProposal(
            problem_statement="Problem",
            proposed_solution="Solution",
            assumptions=["Assumption"],
            scope_non_goals=["Out of scope"],
        )
        mock_expand_metadata = {
            "request_id": "expand-123",
            "model": "gpt-5.1",
            "temperature": 0.7,
            "elapsed_time": 2.0,
        }

        mock_expand_client = MagicMock()
        mock_expand_client.create_structured_response.return_value = (
            mock_proposal,
            mock_expand_metadata,
        )
        mock_expand_client_class.return_value = mock_expand_client

        mock_review = PersonaReview(
            persona_name="GenericReviewer",
            persona_id="genericreviewer",
            confidence_score=0.8,
            strengths=["Good"],
            concerns=[],
            recommendations=["Add tests"],
            blocking_issues=[],
            estimated_effort="2 weeks",
            dependency_risks=[],
        )
        mock_review_metadata = {
            "request_id": "review-456",
            "model": "gpt-5.1",
            "temperature": 0.2,
            "elapsed_time": 1.5,
        }

        mock_review_client = MagicMock()
        mock_review_client.create_structured_response.return_value = (
            mock_review,
            mock_review_metadata,
        )
        mock_review_client_class.return_value = mock_review_client

        # Try to pass model and temperature in request (should be ignored)
        response = client.post(
            "/v1/review-idea",
            json={
                "idea": "Build a REST API.",
                "model": "gpt-4",  # This should be ignored
                "temperature": 1.0,  # This should be ignored
            },
        )

        # Verify success (extra fields ignored by Pydantic)
        assert response.status_code == 200
        data = response.json()

        # Verify model settings from config were used (not client-provided)
        assert data["expanded_proposal"]["metadata"]["model"] == "gpt-5.1"
        assert data["expanded_proposal"]["metadata"]["temperature"] == 0.7
