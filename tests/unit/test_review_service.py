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
"""Unit tests for review service."""

from unittest.mock import MagicMock, patch

import pytest

from consensus_engine.config.settings import Settings
from consensus_engine.exceptions import LLMServiceError, SchemaValidationError
from consensus_engine.schemas.proposal import ExpandedProposal
from consensus_engine.schemas.review import BlockingIssue, Concern, PersonaReview
from consensus_engine.services.review import review_proposal


@pytest.fixture
def mock_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Create mock settings for tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-review-tests")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.1")
    monkeypatch.setenv("REVIEW_MODEL", "gpt-5.1")
    monkeypatch.setenv("REVIEW_TEMPERATURE", "0.2")
    monkeypatch.setenv("DEFAULT_PERSONA_NAME", "GenericReviewer")
    return Settings()


@pytest.fixture
def sample_proposal() -> ExpandedProposal:
    """Create a sample proposal for testing."""
    return ExpandedProposal(
        problem_statement="Build a scalable API",
        proposed_solution="Use FastAPI with async handlers",
        assumptions=["Python 3.11+", "PostgreSQL database"],
        scope_non_goals=["No mobile app", "No authentication"],
        title="API Development Proposal",
        summary="Building a new API service",
    )


class TestReviewProposal:
    """Test suite for review_proposal function."""

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    def test_review_proposal_success(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test successful proposal review."""
        # Setup mock response
        mock_review = PersonaReview(
            persona_name="GenericReviewer",
            persona_id="generic_reviewer",
            confidence_score=0.8,
            strengths=["Clear problem statement", "Good architecture choice"],
            concerns=[
                Concern(text="Missing error handling", is_blocking=False),
                Concern(text="No security considerations", is_blocking=True),
            ],
            recommendations=["Add authentication", "Implement rate limiting"],
            blocking_issues=[BlockingIssue(text="No security design")],
            estimated_effort="2-3 weeks",
            dependency_risks=["External API availability"],
        )
        mock_metadata = {
            "request_id": "test-request-123",
            "step_name": "review",
            "model": "gpt-5.1",
            "temperature": 0.2,
            "elapsed_time": 1.5,
            "latency": 1.5,
            "status": "success",
        }

        mock_client = MagicMock()
        mock_client.create_structured_response_with_payload.return_value = (mock_review, mock_metadata)
        mock_client_class.return_value = mock_client

        # Call service
        result, metadata = review_proposal(sample_proposal, mock_settings)

        # Verify result
        assert isinstance(result, PersonaReview)
        assert result.persona_name == "GenericReviewer"
        assert result.confidence_score == 0.8
        assert len(result.strengths) == 2
        assert len(result.concerns) == 2
        assert len(result.recommendations) == 2
        assert len(result.blocking_issues) == 1

        # Verify metadata
        assert metadata["request_id"] == "test-request-123"
        assert metadata["step_name"] == "review"
        assert metadata["model"] == "gpt-5.1"
        assert metadata["temperature"] == 0.2

        # Verify client was called correctly
        mock_client.create_structured_response_with_payload.assert_called_once()
        call_args = mock_client.create_structured_response_with_payload.call_args
        assert "Build a scalable API" in call_args[1]["user_prompt"]
        assert call_args[1]["response_model"] == PersonaReview
        assert call_args[1]["step_name"] == "review"
        assert "GenericReviewer" in call_args[1]["developer_instruction"]

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    def test_review_proposal_with_custom_persona(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test proposal review with custom persona."""
        mock_review = PersonaReview(
            persona_name="SecurityExpert",
            persona_id="security_expert",
            confidence_score=0.6,
            strengths=["Good use of HTTPS"],
            concerns=[Concern(text="No input validation", is_blocking=True)],
            recommendations=["Add security audit"],
            blocking_issues=[BlockingIssue(text="Missing security review")],
            estimated_effort="1 week",
            dependency_risks=[],
        )
        mock_metadata = {"request_id": "test-request-456", "step_name": "review"}

        mock_client = MagicMock()
        mock_client.create_structured_response_with_payload.return_value = (mock_review, mock_metadata)
        mock_client_class.return_value = mock_client

        # Call service with custom persona
        result, metadata = review_proposal(
            sample_proposal,
            mock_settings,
            persona_name="SecurityExpert",
            persona_instructions="Focus on security aspects",
        )

        # Verify custom persona was used
        assert result.persona_name == "SecurityExpert"
        call_args = mock_client.create_structured_response_with_payload.call_args
        instruction_payload = call_args[1]["instruction_payload"]; developer_instruction = instruction_payload.developer_instruction
        assert "SecurityExpert" in developer_instruction
        assert "Focus on security aspects" in developer_instruction

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    def test_review_proposal_uses_settings_defaults(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that review uses settings defaults when persona not provided."""
        mock_review = PersonaReview(
            persona_name="GenericReviewer",
            persona_id="generic_reviewer",
            confidence_score=0.7,
            strengths=["Good"],
            concerns=[],
            recommendations=["Improve"],
            blocking_issues=[],
            estimated_effort="1 week",
            dependency_risks=[],
        )
        mock_metadata = {"request_id": "test-request-789"}

        mock_client = MagicMock()
        mock_client.create_structured_response_with_payload.return_value = (mock_review, mock_metadata)
        mock_client_class.return_value = mock_client

        # Call service without persona params
        result, metadata = review_proposal(sample_proposal, mock_settings)

        # Verify settings defaults were used
        call_args = mock_client.create_structured_response_with_payload.call_args
        assert mock_settings.default_persona_name in call_args[1]["developer_instruction"]
        assert mock_settings.default_persona_instructions in call_args[1]["developer_instruction"]

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    def test_review_proposal_system_instruction_present(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that system instruction is provided."""
        mock_review = PersonaReview(
            persona_name="GenericReviewer",
            persona_id="generic_reviewer",
            confidence_score=0.7,
            strengths=["Good"],
            concerns=[],
            recommendations=["Improve"],
            blocking_issues=[],
            estimated_effort="1 week",
            dependency_risks=[],
        )
        mock_metadata = {"request_id": "test-request-xyz"}

        mock_client = MagicMock()
        mock_client.create_structured_response_with_payload.return_value = (mock_review, mock_metadata)
        mock_client_class.return_value = mock_client

        # Call service
        review_proposal(sample_proposal, mock_settings)

        # Verify system instruction was provided
        call_args = mock_client.create_structured_response_with_payload.call_args
        instruction_payload = call_args[1]["instruction_payload"]; system_instruction = instruction_payload.system_instruction
        assert len(system_instruction) > 0
        assert "review" in system_instruction.lower()
        assert "json" in system_instruction.lower()

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    def test_review_proposal_developer_instruction_present(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that developer instruction is provided."""
        mock_review = PersonaReview(
            persona_name="GenericReviewer",
            persona_id="generic_reviewer",
            confidence_score=0.7,
            strengths=["Good"],
            concerns=[],
            recommendations=["Improve"],
            blocking_issues=[],
            estimated_effort="1 week",
            dependency_risks=[],
        )
        mock_metadata = {"request_id": "test-request-dev"}

        mock_client = MagicMock()
        mock_client.create_structured_response_with_payload.return_value = (mock_review, mock_metadata)
        mock_client_class.return_value = mock_client

        # Call service
        review_proposal(sample_proposal, mock_settings)

        # Verify developer instruction was provided
        call_args = mock_client.create_structured_response_with_payload.call_args
        instruction_payload = call_args[1]["instruction_payload"]; developer_instruction = instruction_payload.developer_instruction
        assert developer_instruction is not None
        assert len(developer_instruction) > 0
        assert "PersonaReview" in developer_instruction

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    def test_review_proposal_uses_review_config(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that review uses review-specific model and temperature."""
        mock_review = PersonaReview(
            persona_name="GenericReviewer",
            persona_id="generic_reviewer",
            confidence_score=0.7,
            strengths=["Good"],
            concerns=[],
            recommendations=["Improve"],
            blocking_issues=[],
            estimated_effort="1 week",
            dependency_risks=[],
        )
        mock_metadata = {
            "request_id": "test-request-config",
            "model": "gpt-5.1",
            "temperature": 0.2,
        }

        mock_client = MagicMock()
        mock_client.create_structured_response_with_payload.return_value = (mock_review, mock_metadata)
        mock_client_class.return_value = mock_client

        # Call service
        review_proposal(sample_proposal, mock_settings)

        # Verify review-specific config was used
        call_args = mock_client.create_structured_response_with_payload.call_args
        assert call_args[1]["model_override"] == mock_settings.review_model
        assert call_args[1]["temperature_override"] == mock_settings.review_temperature
        assert call_args[1]["step_name"] == "review"

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    def test_review_proposal_truncates_long_fields(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
    ) -> None:
        """Test that very long proposal fields are truncated."""
        long_proposal = ExpandedProposal(
            problem_statement="x" * 3000,  # Very long
            proposed_solution="y" * 3000,  # Very long
            assumptions=["z" * 1000] * 20,  # Many long assumptions
            scope_non_goals=["a" * 1000] * 20,  # Many long non-goals
        )

        mock_review = PersonaReview(
            persona_name="GenericReviewer",
            persona_id="generic_reviewer",
            confidence_score=0.7,
            strengths=["Good"],
            concerns=[],
            recommendations=["Improve"],
            blocking_issues=[],
            estimated_effort="1 week",
            dependency_risks=[],
        )
        mock_metadata = {"request_id": "test-request-truncate"}

        mock_client = MagicMock()
        mock_client.create_structured_response_with_payload.return_value = (mock_review, mock_metadata)
        mock_client_class.return_value = mock_client

        # Call service
        review_proposal(long_proposal, mock_settings)

        # Verify user prompt was constructed (truncation happens internally)
        call_args = mock_client.create_structured_response_with_payload.call_args
        instruction_payload = call_args[1]["instruction_payload"]; user_prompt = instruction_payload.user_content
        # Problem and solution should be truncated to 2000 chars each
        # Plus assumptions and non-goals (first 10 items, each truncated to 500 chars)
        # This is reasonable as we limit both field length and list length
        assert len(user_prompt) < 20000  # Should still be reasonable due to truncation

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    def test_review_proposal_propagates_llm_errors(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that LLM errors are propagated correctly."""
        # Setup mock to raise error
        mock_client = MagicMock()
        mock_client.create_structured_response_with_payload.side_effect = LLMServiceError(
            "API error", code="LLM_SERVICE_ERROR"
        )
        mock_client_class.return_value = mock_client

        # Call service and expect error
        with pytest.raises(LLMServiceError) as exc_info:
            review_proposal(sample_proposal, mock_settings)

        assert exc_info.value.code == "LLM_SERVICE_ERROR"

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    def test_review_proposal_propagates_schema_errors(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that schema validation errors are propagated."""
        # Setup mock to raise schema error
        mock_client = MagicMock()
        mock_client.create_structured_response_with_payload.side_effect = SchemaValidationError(
            "Schema mismatch"
        )
        mock_client_class.return_value = mock_client

        # Call service and expect error
        with pytest.raises(SchemaValidationError):
            review_proposal(sample_proposal, mock_settings)

    @patch("consensus_engine.services.review.OpenAIClientWrapper")
    def test_review_proposal_includes_optional_fields(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
    ) -> None:
        """Test that optional proposal fields are included when present."""
        proposal_with_optionals = ExpandedProposal(
            problem_statement="Problem",
            proposed_solution="Solution",
            assumptions=["Assumption 1"],
            scope_non_goals=["Non-goal 1"],
            title="Test Title",
            summary="Test Summary",
        )

        mock_review = PersonaReview(
            persona_name="GenericReviewer",
            persona_id="generic_reviewer",
            confidence_score=0.7,
            strengths=["Good"],
            concerns=[],
            recommendations=["Improve"],
            blocking_issues=[],
            estimated_effort="1 week",
            dependency_risks=[],
        )
        mock_metadata = {"request_id": "test-request-optionals"}

        mock_client = MagicMock()
        mock_client.create_structured_response_with_payload.return_value = (mock_review, mock_metadata)
        mock_client_class.return_value = mock_client

        # Call service
        review_proposal(proposal_with_optionals, mock_settings)

        # Verify optional fields are included in prompt
        call_args = mock_client.create_structured_response_with_payload.call_args
        instruction_payload = call_args[1]["instruction_payload"]; user_prompt = instruction_payload.user_content
        assert "Test Title" in user_prompt
        assert "Test Summary" in user_prompt
