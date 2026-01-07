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
"""Integration tests for full-review endpoint."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from consensus_engine.app import create_app
from consensus_engine.exceptions import (
    LLMAuthenticationError,
    LLMRateLimitError,
)
from consensus_engine.schemas.proposal import ExpandedProposal
from consensus_engine.schemas.review import Concern, PersonaReview


@pytest.fixture
def valid_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up valid test environment."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-full-review-endpoint")
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


class TestFullReviewEndpoint:
    """Test suite for POST /v1/full-review endpoint."""

    @patch("consensus_engine.services.orchestrator.OpenAIClientWrapper")
    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_full_review_success(
        self,
        mock_expand_client_class: MagicMock,
        mock_orchestrator_client_class: MagicMock,
        client: TestClient,
    ) -> None:
        """Test successful full review orchestration (happy path)."""
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

        # Setup orchestrator mock - create 5 persona reviews
        persona_reviews = []
        persona_configs = [
            ("architect", "Architect", 0.85),
            ("critic", "Critic", 0.75),
            ("optimist", "Optimist", 0.90),
            ("security_guardian", "SecurityGuardian", 0.80),
            ("user_advocate", "UserAdvocate", 0.88),
        ]

        for persona_id, persona_name, confidence in persona_configs:
            review = PersonaReview(
                persona_name=persona_name,
                persona_id=persona_id,
                confidence_score=confidence,
                strengths=["Good architecture", "Clear scope"],
                concerns=[
                    Concern(text="Minor issue", is_blocking=False),
                ],
                recommendations=["Add tests"],
                blocking_issues=[],
                estimated_effort="2-3 weeks",
                dependency_risks=[],
            )
            persona_reviews.append(review)

        mock_orchestrator_client = MagicMock()
        # Simulate the orchestrator calling create_structured_response multiple times
        mock_orchestrator_client.create_structured_response.side_effect = [
            (persona_reviews[i], {"request_id": f"review-{i}", "latency": 2.0})
            for i in range(5)
        ]
        mock_orchestrator_client_class.return_value = mock_orchestrator_client

        # Make request
        response = client.post(
            "/v1/full-review",
            json={"idea": "Build a REST API for user management."},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        # Check expanded_proposal
        assert "expanded_proposal" in data
        assert data["expanded_proposal"]["problem_statement"] == "Clear problem statement"
        assert data["expanded_proposal"]["proposed_solution"] == "Detailed solution approach"

        # Check persona_reviews (should have 5)
        assert "persona_reviews" in data
        assert len(data["persona_reviews"]) == 5

        # Verify all personas are present
        persona_ids = [review["persona_id"] for review in data["persona_reviews"]]
        assert "architect" in persona_ids
        assert "critic" in persona_ids
        assert "optimist" in persona_ids
        assert "security_guardian" in persona_ids
        assert "user_advocate" in persona_ids

        # Check decision
        assert "decision" in data
        assert "overall_weighted_confidence" in data["decision"]
        assert "decision" in data["decision"]
        assert "detailed_score_breakdown" in data["decision"]

        # Check run metadata
        assert "run_id" in data
        assert "elapsed_time" in data
        assert data["elapsed_time"] > 0

        # Verify request ID header
        assert "X-Request-ID" in response.headers

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_full_review_expand_failure(
        self, mock_expand_client_class: MagicMock, client: TestClient
    ) -> None:
        """Test full review when expand step fails."""
        # Setup expand mock to raise error
        mock_expand_client = MagicMock()
        mock_expand_client.create_structured_response.side_effect = LLMAuthenticationError(
            message="Invalid API key",
            details={"retryable": False},
        )
        mock_expand_client_class.return_value = mock_expand_client

        # Make request
        response = client.post(
            "/v1/full-review",
            json={"idea": "Build a REST API for user management."},
        )

        # Verify error response
        assert response.status_code == 401
        data = response.json()
        assert data["code"] == "LLM_AUTH_ERROR"
        assert data["message"] == "Invalid API key"
        assert data["failed_step"] == "expand"
        assert "run_id" in data
        assert data["partial_results"] is None  # No partial results on expand failure

    @patch("consensus_engine.services.orchestrator.OpenAIClientWrapper")
    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_full_review_orchestrator_failure(
        self,
        mock_expand_client_class: MagicMock,
        mock_orchestrator_client_class: MagicMock,
        client: TestClient,
    ) -> None:
        """Test full review when orchestrator step fails."""
        # Setup expand mock (success)
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

        # Setup orchestrator mock to raise error
        mock_orchestrator_client = MagicMock()
        mock_orchestrator_client.create_structured_response.side_effect = LLMRateLimitError(
            message="Rate limit exceeded",
            details={"retryable": True, "retry_after": 60},
        )
        mock_orchestrator_client_class.return_value = mock_orchestrator_client

        # Make request
        response = client.post(
            "/v1/full-review",
            json={"idea": "Build a REST API for user management."},
        )

        # Verify error response
        assert response.status_code == 503
        data = response.json()
        assert data["code"] == "LLM_RATE_LIMIT"
        assert data["message"] == "Rate limit exceeded"
        assert data["failed_step"] == "review"
        assert "run_id" in data
        # Should have partial results (expanded proposal)
        assert data["partial_results"] is not None
        assert "expanded_proposal" in data["partial_results"]

    def test_full_review_validation_error_too_many_sentences(self, client: TestClient) -> None:
        """Test validation error when idea has too many sentences."""
        # Create an idea with more than 10 sentences
        long_idea = ". ".join([f"Sentence {i}" for i in range(15)]) + "."

        response = client.post(
            "/v1/full-review",
            json={"idea": long_idea},
        )

        # Verify validation error
        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert "validation failed" in data["message"].lower()

    def test_full_review_validation_error_empty_idea(self, client: TestClient) -> None:
        """Test validation error when idea is empty."""
        response = client.post(
            "/v1/full-review",
            json={"idea": ""},
        )

        # Verify validation error
        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"

    @patch("consensus_engine.services.orchestrator.OpenAIClientWrapper")
    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_full_review_with_extra_context_dict(
        self,
        mock_expand_client_class: MagicMock,
        mock_orchestrator_client_class: MagicMock,
        client: TestClient,
    ) -> None:
        """Test full review with extra context as dictionary."""
        # Setup expand mock
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

        # Setup orchestrator mock with minimal persona reviews
        persona_reviews = []
        for persona_id, persona_name in [
            ("architect", "Architect"),
            ("critic", "Critic"),
            ("optimist", "Optimist"),
            ("security_guardian", "SecurityGuardian"),
            ("user_advocate", "UserAdvocate"),
        ]:
            review = PersonaReview(
                persona_name=persona_name,
                persona_id=persona_id,
                confidence_score=0.80,
                strengths=["Good"],
                concerns=[],
                recommendations=[],
                blocking_issues=[],
                estimated_effort="1 week",
                dependency_risks=[],
            )
            persona_reviews.append(review)

        mock_orchestrator_client = MagicMock()
        mock_orchestrator_client.create_structured_response.side_effect = [
            (persona_reviews[i], {"request_id": f"review-{i}", "latency": 2.0})
            for i in range(5)
        ]
        mock_orchestrator_client_class.return_value = mock_orchestrator_client

        # Make request with dict extra_context
        response = client.post(
            "/v1/full-review",
            json={
                "idea": "Build a REST API for user management.",
                "extra_context": {"language": "Python", "version": "3.11+"},
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "expanded_proposal" in data
        assert len(data["persona_reviews"]) == 5
        assert "decision" in data

    @patch("consensus_engine.services.orchestrator.OpenAIClientWrapper")
    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_full_review_with_extra_context_string(
        self,
        mock_expand_client_class: MagicMock,
        mock_orchestrator_client_class: MagicMock,
        client: TestClient,
    ) -> None:
        """Test full review with extra context as string."""
        # Setup expand mock
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

        # Setup orchestrator mock
        persona_reviews = []
        for persona_id, persona_name in [
            ("architect", "Architect"),
            ("critic", "Critic"),
            ("optimist", "Optimist"),
            ("security_guardian", "SecurityGuardian"),
            ("user_advocate", "UserAdvocate"),
        ]:
            review = PersonaReview(
                persona_name=persona_name,
                persona_id=persona_id,
                confidence_score=0.80,
                strengths=["Good"],
                concerns=[],
                recommendations=[],
                blocking_issues=[],
                estimated_effort="1 week",
                dependency_risks=[],
            )
            persona_reviews.append(review)

        mock_orchestrator_client = MagicMock()
        mock_orchestrator_client.create_structured_response.side_effect = [
            (persona_reviews[i], {"request_id": f"review-{i}", "latency": 2.0})
            for i in range(5)
        ]
        mock_orchestrator_client_class.return_value = mock_orchestrator_client

        # Make request with string extra_context
        response = client.post(
            "/v1/full-review",
            json={
                "idea": "Build a REST API for user management.",
                "extra_context": "Must support Python 3.11+",
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "expanded_proposal" in data
        assert len(data["persona_reviews"]) == 5
        assert "decision" in data
