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
"""Integration tests for review service."""

from unittest.mock import MagicMock, patch

import pytest

from consensus_engine.config.settings import Settings
from consensus_engine.exceptions import (
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMServiceError,
    LLMTimeoutError,
    SchemaValidationError,
)
from consensus_engine.schemas.proposal import ExpandedProposal
from consensus_engine.schemas.review import Concern, PersonaReview
from consensus_engine.services.review import review_proposal


@pytest.fixture
def mock_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Create mock settings for integration tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-review-integration")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.1")
    monkeypatch.setenv("REVIEW_MODEL", "gpt-5.1")
    monkeypatch.setenv("REVIEW_TEMPERATURE", "0.2")
    monkeypatch.setenv("DEFAULT_PERSONA_NAME", "GenericReviewer")
    return Settings()


@pytest.fixture
def sample_proposal() -> ExpandedProposal:
    """Create a sample proposal for testing."""
    return ExpandedProposal(
        problem_statement="We need a secure, scalable API to manage user data",
        proposed_solution=(
            "Build a RESTful API using FastAPI with async handlers, "
            "PostgreSQL for data persistence, and JWT for authentication"
        ),
        assumptions=["Python 3.11+", "PostgreSQL 14+", "Docker deployment"],
        scope_non_goals=["No mobile app", "No real-time websockets"],
        title="User Management API",
        summary="Secure and scalable user data management system",
    )


class TestReviewProposalServiceIntegration:
    """Integration tests for review_proposal service."""

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    def test_review_proposal_returns_serialized_review(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that review_proposal returns a properly serialized PersonaReview."""
        mock_review = PersonaReview(
            persona_name="GenericReviewer",
            confidence_score=0.75,
            strengths=[
                "Well-defined problem statement",
                "Modern technology stack",
                "Security consideration with JWT",
            ],
            concerns=[
                Concern(text="No mention of input validation", is_blocking=False),
                Concern(text="Missing rate limiting strategy", is_blocking=True),
            ],
            recommendations=[
                "Add comprehensive input validation",
                "Implement rate limiting",
                "Add monitoring and logging",
            ],
            blocking_issues=["Missing security audit plan"],
            estimated_effort="3-4 weeks for MVP",
            dependency_risks=["PostgreSQL cluster setup", "JWT library security updates"],
        )
        mock_metadata = {
            "request_id": "test-integration-123",
            "step_name": "review",
            "model": "gpt-5.1",
            "temperature": 0.2,
            "elapsed_time": 2.5,
            "status": "success",
        }

        mock_client = MagicMock()
        mock_client.create_structured_response.return_value = (mock_review, mock_metadata)
        mock_client_class.return_value = mock_client

        # Call service
        result, metadata = review_proposal(sample_proposal, mock_settings)

        # Verify result is properly serialized
        assert isinstance(result, PersonaReview)
        assert result.model_dump() == mock_review.model_dump()

        # Verify metadata
        assert metadata["step_name"] == "review"
        assert "request_id" in metadata

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    @patch("consensus_engine.services.review.logger")
    def test_review_proposal_logs_success_without_sensitive_data(
        self,
        mock_logger: MagicMock,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that review logs success without exposing sensitive proposal data."""
        mock_review = PersonaReview(
            persona_name="GenericReviewer",
            confidence_score=0.8,
            strengths=["Good"],
            concerns=[],
            recommendations=["Improve"],
            blocking_issues=[],
            estimated_effort="1 week",
            dependency_risks=[],
        )
        mock_metadata = {
            "request_id": "test-log-123",
            "step_name": "review",
            "model": "gpt-5.1",
            "temperature": 0.2,
            "elapsed_time": 1.0,
            "latency": 1.0,
            "status": "success",
        }

        mock_client = MagicMock()
        mock_client.create_structured_response.return_value = (mock_review, mock_metadata)
        mock_client_class.return_value = mock_client

        # Call service with logging enabled
        review_proposal(sample_proposal, mock_settings)

        # Verify logger was called for success
        assert mock_logger.info.call_count >= 2  # Start and completion logs

        # Get all log calls and verify no sensitive data
        all_calls_str = str(mock_logger.info.call_args_list)
        # Ensure proposal text is not in logs
        assert "user data" not in all_calls_str.lower()
        assert "fastapi" not in all_calls_str.lower()

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    def test_review_proposal_with_minimal_review(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test review with minimal fields populated."""
        mock_review = PersonaReview(
            persona_name="GenericReviewer",
            confidence_score=0.5,
            strengths=[],
            concerns=[],
            recommendations=[],
            blocking_issues=[],
            estimated_effort="Unknown",
            dependency_risks=[],
        )
        mock_metadata = {"request_id": "test-minimal", "step_name": "review"}

        mock_client = MagicMock()
        mock_client.create_structured_response.return_value = (mock_review, mock_metadata)
        mock_client_class.return_value = mock_client

        # Call service
        result, metadata = review_proposal(sample_proposal, mock_settings)

        # Verify minimal review is valid
        assert result.confidence_score == 0.5
        assert result.strengths == []
        assert result.concerns == []
        assert result.estimated_effort == "Unknown"

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    def test_review_proposal_propagates_authentication_error(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that authentication errors are properly propagated."""
        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = LLMAuthenticationError(
            "Invalid API key", details={"request_id": "test-auth-error"}
        )
        mock_client_class.return_value = mock_client

        with pytest.raises(LLMAuthenticationError) as exc_info:
            review_proposal(sample_proposal, mock_settings)

        assert exc_info.value.code == "LLM_AUTH_ERROR"
        assert "request_id" in exc_info.value.details

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    def test_review_proposal_propagates_rate_limit_error(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that rate limit errors are properly propagated."""
        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = LLMRateLimitError(
            "Rate limit exceeded", details={"request_id": "test-rate-limit", "retryable": True}
        )
        mock_client_class.return_value = mock_client

        with pytest.raises(LLMRateLimitError) as exc_info:
            review_proposal(sample_proposal, mock_settings)

        assert exc_info.value.code == "LLM_RATE_LIMIT"
        assert exc_info.value.details["retryable"] is True

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    def test_review_proposal_propagates_timeout_error(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that timeout errors are properly propagated."""
        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = LLMTimeoutError(
            "Request timed out", details={"request_id": "test-timeout", "retryable": True}
        )
        mock_client_class.return_value = mock_client

        with pytest.raises(LLMTimeoutError) as exc_info:
            review_proposal(sample_proposal, mock_settings)

        assert exc_info.value.code == "LLM_TIMEOUT"
        assert exc_info.value.details["retryable"] is True

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    def test_review_proposal_propagates_schema_validation_error(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that schema validation errors are properly propagated."""
        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = SchemaValidationError(
            "Response does not match PersonaReview schema",
            details={"request_id": "test-schema-error"},
        )
        mock_client_class.return_value = mock_client

        with pytest.raises(SchemaValidationError) as exc_info:
            review_proposal(sample_proposal, mock_settings)

        assert exc_info.value.code == "SCHEMA_VALIDATION_ERROR"

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    def test_review_proposal_propagates_generic_llm_error(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that generic LLM errors are properly propagated."""
        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = LLMServiceError(
            "Unknown error", code="LLM_SERVICE_ERROR", details={"request_id": "test-error"}
        )
        mock_client_class.return_value = mock_client

        with pytest.raises(LLMServiceError) as exc_info:
            review_proposal(sample_proposal, mock_settings)

        assert exc_info.value.code == "LLM_SERVICE_ERROR"

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    def test_review_proposal_constructs_proper_prompt_with_all_fields(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that review constructs proper prompt including all proposal fields."""
        mock_review = PersonaReview(
            persona_name="GenericReviewer",
            confidence_score=0.7,
            strengths=["Good"],
            concerns=[],
            recommendations=["Improve"],
            blocking_issues=[],
            estimated_effort="1 week",
            dependency_risks=[],
        )
        mock_metadata = {"request_id": "test-prompt"}

        mock_client = MagicMock()
        mock_client.create_structured_response.return_value = (mock_review, mock_metadata)
        mock_client_class.return_value = mock_client

        # Call service
        review_proposal(sample_proposal, mock_settings)

        # Verify prompt construction
        call_args = mock_client.create_structured_response.call_args
        user_prompt = call_args[1]["user_prompt"]

        # Check that all key fields are in the prompt
        assert "User Management API" in user_prompt
        assert "Secure and scalable user data management system" in user_prompt
        assert "secure, scalable API" in user_prompt
        assert "FastAPI" in user_prompt
        assert "Python 3.11+" in user_prompt
        assert "No mobile app" in user_prompt

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    def test_review_proposal_uses_custom_persona_name(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that custom persona name is properly used."""
        mock_review = PersonaReview(
            persona_name="SecurityAuditor",
            confidence_score=0.6,
            strengths=["Good"],
            concerns=[],
            recommendations=["Improve"],
            blocking_issues=[],
            estimated_effort="1 week",
            dependency_risks=[],
        )
        mock_metadata = {"request_id": "test-persona-name"}

        mock_client = MagicMock()
        mock_client.create_structured_response.return_value = (mock_review, mock_metadata)
        mock_client_class.return_value = mock_client

        # Call service with custom persona
        review_proposal(
            sample_proposal,
            mock_settings,
            persona_name="SecurityAuditor",
            persona_instructions="Focus on security vulnerabilities",
        )

        # Verify persona is in developer instruction
        call_args = mock_client.create_structured_response.call_args
        dev_instruction = call_args[1]["developer_instruction"]
        assert "SecurityAuditor" in dev_instruction
        assert "security vulnerabilities" in dev_instruction
