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
"""Integration tests for expand service with mocked OpenAI responses.

This module tests the expand_idea service behavior with various
stubbed OpenAI responses, verifying proper handling of success cases,
error propagation, logging behavior, and schema validation.
"""

from unittest.mock import MagicMock, patch

import pytest

from consensus_engine.exceptions import (
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMServiceError,
    LLMTimeoutError,
    SchemaValidationError,
)
from consensus_engine.schemas.proposal import ExpandedProposal, IdeaInput
from consensus_engine.services.expand import expand_idea


class TestExpandIdeaServiceIntegration:
    """Integration test suite for expand_idea service with stubbed responses."""

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_returns_serialized_proposal(
        self, mock_client_class: MagicMock, mock_settings
    ) -> None:
        """Test that expandIdea returns properly serialized ExpandedProposal."""
        # Setup mock with complete response
        mock_proposal = ExpandedProposal(
            problem_statement="Clear problem statement",
            proposed_solution="Detailed solution approach",
            assumptions=["Assumption 1", "Assumption 2"],
            scope_non_goals=["Non-goal 1", "Non-goal 2"],
            raw_expanded_proposal="Full proposal text",
        )
        mock_metadata = {
            "request_id": "test-integration-123",
            "model": "gpt-5.1",
            "temperature": 0.7,
            "elapsed_time": 2.5,
            "finish_reason": "stop",
        }

        mock_client = MagicMock()
        mock_client.create_structured_response.return_value = (mock_proposal, mock_metadata)
        mock_client_class.return_value = mock_client

        # Execute service call
        idea_input = IdeaInput(idea="Build a REST API for user management.")
        result, metadata = expand_idea(idea_input, mock_settings)

        # Verify result is properly structured
        assert isinstance(result, ExpandedProposal)
        assert result.problem_statement == "Clear problem statement"
        assert result.proposed_solution == "Detailed solution approach"
        assert len(result.assumptions) == 2
        assert len(result.scope_non_goals) == 2
        assert result.raw_expanded_proposal == "Full proposal text"

        # Verify metadata is returned
        assert metadata["request_id"] == "test-integration-123"
        assert metadata["model"] == "gpt-5.1"
        assert metadata["temperature"] == 0.7

        # Verify result can be serialized to dict
        result_dict = result.model_dump()
        assert "problem_statement" in result_dict
        assert "proposed_solution" in result_dict
        assert "assumptions" in result_dict
        assert "scope_non_goals" in result_dict

        # Verify result can be serialized to JSON
        result_json = result.model_dump_json()
        assert "Clear problem statement" in result_json

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    @patch("consensus_engine.services.expand.logger")
    def test_expand_idea_logs_success_without_sensitive_data(
        self, mock_logger: MagicMock, mock_client_class: MagicMock, mock_settings
    ) -> None:
        """Test that expandIdea logs success without exposing sensitive data."""
        # Setup mock
        mock_proposal = ExpandedProposal(
            problem_statement="Problem",
            proposed_solution="Solution",
        )
        mock_metadata = {
            "request_id": "test-log-123",
            "model": "gpt-5.1",
            "temperature": 0.7,
            "elapsed_time": 1.5,
        }

        mock_client = MagicMock()
        mock_client.create_structured_response.return_value = (mock_proposal, mock_metadata)
        mock_client_class.return_value = mock_client

        # Execute service call
        idea_input = IdeaInput(
            idea="Sensitive business idea that should not be logged",
            extra_context="Confidential context",
        )
        expand_idea(idea_input, mock_settings)

        # Verify logging was called
        assert mock_logger.info.called
        log_calls = mock_logger.info.call_args_list

        # Verify no sensitive data in logs
        for call in log_calls:
            call_str = str(call)
            # Verify the idea text is not in any log call
            assert "Sensitive business idea" not in call_str
            assert "Confidential context" not in call_str

        # Verify metadata IS logged (non-sensitive)
        success_log_call = log_calls[-1]  # Last call should be success log
        assert "extra" in success_log_call.kwargs
        log_extra = success_log_call.kwargs["extra"]
        assert "request_id" in log_extra
        assert "model" in log_extra
        assert "temperature" in log_extra
        assert "elapsed_time" in log_extra
        assert "status" in log_extra

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_with_minimal_response(
        self, mock_client_class: MagicMock, mock_settings
    ) -> None:
        """Test expandIdea with minimal response (only required fields)."""
        # Setup mock with minimal proposal
        mock_proposal = ExpandedProposal(
            problem_statement="Minimal problem",
            proposed_solution="Minimal solution",
            # assumptions, scope_non_goals, raw_expanded_proposal use defaults
        )
        mock_metadata = {"request_id": "test-minimal-456"}

        mock_client = MagicMock()
        mock_client.create_structured_response.return_value = (mock_proposal, mock_metadata)
        mock_client_class.return_value = mock_client

        # Execute service call
        idea_input = IdeaInput(idea="Simple idea.")
        result, metadata = expand_idea(idea_input, mock_settings)

        # Verify minimal response is handled correctly
        assert result.problem_statement == "Minimal problem"
        assert result.proposed_solution == "Minimal solution"
        assert result.assumptions == []
        assert result.scope_non_goals == []
        assert result.raw_expanded_proposal == ""

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_propagates_authentication_error(
        self, mock_client_class: MagicMock, mock_settings
    ) -> None:
        """Test that authentication errors are properly propagated."""
        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = LLMAuthenticationError(
            "Invalid API key", details={"request_id": "test-auth-error"}
        )
        mock_client_class.return_value = mock_client

        idea_input = IdeaInput(idea="Test idea.")

        with pytest.raises(LLMAuthenticationError) as exc_info:
            expand_idea(idea_input, mock_settings)

        assert exc_info.value.code == "LLM_AUTH_ERROR"
        assert "Invalid API key" in exc_info.value.message

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_propagates_rate_limit_error(
        self, mock_client_class: MagicMock, mock_settings
    ) -> None:
        """Test that rate limit errors are properly propagated."""
        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = LLMRateLimitError(
            "Rate limit exceeded", details={"retryable": True, "retry_after": 60}
        )
        mock_client_class.return_value = mock_client

        idea_input = IdeaInput(idea="Test idea.")

        with pytest.raises(LLMRateLimitError) as exc_info:
            expand_idea(idea_input, mock_settings)

        assert exc_info.value.code == "LLM_RATE_LIMIT"
        assert exc_info.value.details["retryable"] is True

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_propagates_timeout_error(
        self, mock_client_class: MagicMock, mock_settings
    ) -> None:
        """Test that timeout errors are properly propagated."""
        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = LLMTimeoutError(
            "Request timed out", details={"retryable": True, "timeout_seconds": 30}
        )
        mock_client_class.return_value = mock_client

        idea_input = IdeaInput(idea="Test idea.")

        with pytest.raises(LLMTimeoutError) as exc_info:
            expand_idea(idea_input, mock_settings)

        assert exc_info.value.code == "LLM_TIMEOUT"
        assert exc_info.value.details["retryable"] is True

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_propagates_schema_validation_error(
        self, mock_client_class: MagicMock, mock_settings
    ) -> None:
        """Test that schema validation errors are properly propagated.

        This simulates the case where OpenAI returns a response missing
        required fields, causing schema validation to fail.
        """
        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = SchemaValidationError(
            "Response missing required field: problem_statement",
            details={"missing_fields": ["problem_statement"]},
        )
        mock_client_class.return_value = mock_client

        idea_input = IdeaInput(idea="Test idea.")

        with pytest.raises(SchemaValidationError) as exc_info:
            expand_idea(idea_input, mock_settings)

        assert exc_info.value.code == "SCHEMA_VALIDATION_ERROR"
        assert "problem_statement" in exc_info.value.message

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_propagates_generic_llm_error(
        self, mock_client_class: MagicMock, mock_settings
    ) -> None:
        """Test that generic LLM service errors are properly propagated."""
        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = LLMServiceError(
            "OpenAI service unavailable",
            code="LLM_SERVICE_ERROR",
            details={"status_code": 503},
        )
        mock_client_class.return_value = mock_client

        idea_input = IdeaInput(idea="Test idea.")

        with pytest.raises(LLMServiceError) as exc_info:
            expand_idea(idea_input, mock_settings)

        assert exc_info.value.code == "LLM_SERVICE_ERROR"

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_constructs_proper_prompt_with_context(
        self, mock_client_class: MagicMock, mock_settings
    ) -> None:
        """Test that expandIdea constructs proper prompts with extra context."""
        mock_proposal = ExpandedProposal(
            problem_statement="Problem",
            proposed_solution="Solution",
        )
        mock_metadata = {"request_id": "test-prompt-789"}

        mock_client = MagicMock()
        mock_client.create_structured_response.return_value = (mock_proposal, mock_metadata)
        mock_client_class.return_value = mock_client

        # Execute with extra context
        idea_input = IdeaInput(
            idea="Build an API.", extra_context="Must support Python 3.11+ and FastAPI"
        )
        expand_idea(idea_input, mock_settings)

        # Verify the client was called with proper prompt structure
        mock_client.create_structured_response.assert_called_once()
        call_kwargs = mock_client.create_structured_response.call_args.kwargs

        # Verify user prompt includes both idea and context
        user_prompt = call_kwargs["user_prompt"]
        assert "Build an API." in user_prompt
        assert "Must support Python 3.11+ and FastAPI" in user_prompt
        assert "Additional Context" in user_prompt

        # Verify system and developer instructions are provided
        assert "system_instruction" in call_kwargs
        assert "developer_instruction" in call_kwargs
        assert len(call_kwargs["system_instruction"]) > 0
        assert len(call_kwargs["developer_instruction"]) > 0

        # Verify response model is specified
        assert call_kwargs["response_model"] == ExpandedProposal

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_constructs_proper_prompt_without_context(
        self, mock_client_class: MagicMock, mock_settings
    ) -> None:
        """Test that expandIdea constructs proper prompts without extra context."""
        mock_proposal = ExpandedProposal(
            problem_statement="Problem",
            proposed_solution="Solution",
        )
        mock_metadata = {"request_id": "test-prompt-no-ctx"}

        mock_client = MagicMock()
        mock_client.create_structured_response.return_value = (mock_proposal, mock_metadata)
        mock_client_class.return_value = mock_client

        # Execute without extra context
        idea_input = IdeaInput(idea="Build an API.")
        expand_idea(idea_input, mock_settings)

        # Verify the client was called
        call_kwargs = mock_client.create_structured_response.call_args.kwargs

        # Verify user prompt includes idea but not context header
        user_prompt = call_kwargs["user_prompt"]
        assert "Build an API." in user_prompt
        assert "Additional Context" not in user_prompt
