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
"""Unit tests for expand service."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from consensus_engine.config.settings import Settings
from consensus_engine.exceptions import LLMServiceError, SchemaValidationError
from consensus_engine.schemas.proposal import ExpandedProposal, IdeaInput
from consensus_engine.services.expand import expand_idea


@pytest.fixture
def mock_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Create mock settings for tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-expand-tests")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.1")
    monkeypatch.setenv("TEMPERATURE", "0.7")
    return Settings()


class TestExpandIdea:
    """Test suite for expand_idea function."""

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_success(
        self, mock_client_class: MagicMock, mock_settings: Settings
    ) -> None:
        """Test successful idea expansion."""
        # Setup mock response
        mock_proposal = ExpandedProposal(
            problem_statement="Test problem",
            proposed_solution="Test solution",
            assumptions=["Assumption 1"],
            scope_non_goals=["Non-goal 1"],
            raw_expanded_proposal="Full proposal text",
        )
        mock_metadata = {
            "request_id": "test-request-123",
            "model": "gpt-5.1",
            "temperature": 0.7,
            "elapsed_time": 1.5,
        }

        mock_client = MagicMock()
        mock_client.create_structured_response.return_value = (mock_proposal, mock_metadata)
        mock_client_class.return_value = mock_client

        # Create input and call service
        idea_input = IdeaInput(idea="Build a new API")
        result, metadata = expand_idea(idea_input, mock_settings)

        # Verify result
        assert isinstance(result, ExpandedProposal)
        assert result.problem_statement == "Test problem"
        assert result.proposed_solution == "Test solution"
        assert len(result.assumptions) == 1
        assert len(result.scope_non_goals) == 1

        # Verify metadata
        assert metadata["request_id"] == "test-request-123"
        assert metadata["model"] == "gpt-5.1"

        # Verify client was called correctly
        mock_client.create_structured_response.assert_called_once()
        call_args = mock_client.create_structured_response.call_args
        assert "Build a new API" in call_args[1]["user_prompt"]
        assert call_args[1]["response_model"] == ExpandedProposal

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_with_extra_context(
        self, mock_client_class: MagicMock, mock_settings: Settings
    ) -> None:
        """Test idea expansion with extra context."""
        # Setup mock response
        mock_proposal = ExpandedProposal(
            problem_statement="Test problem",
            proposed_solution="Test solution",
            assumptions=[],
            scope_non_goals=[],
        )
        mock_metadata = {"request_id": "test-request-456"}

        mock_client = MagicMock()
        mock_client.create_structured_response.return_value = (mock_proposal, mock_metadata)
        mock_client_class.return_value = mock_client

        # Create input with extra context
        idea_input = IdeaInput(idea="Build a new API", extra_context="Must support Python 3.11+")
        result, metadata = expand_idea(idea_input, mock_settings)

        # Verify extra context was included in prompt
        call_args = mock_client.create_structured_response.call_args
        user_prompt = call_args[1]["user_prompt"]
        assert "Build a new API" in user_prompt
        assert "Must support Python 3.11+" in user_prompt
        assert "Additional Context" in user_prompt

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_without_extra_context(
        self, mock_client_class: MagicMock, mock_settings: Settings
    ) -> None:
        """Test idea expansion without extra context."""
        # Setup mock response
        mock_proposal = ExpandedProposal(
            problem_statement="Test problem",
            proposed_solution="Test solution",
            assumptions=[],
            scope_non_goals=[],
        )
        mock_metadata = {"request_id": "test-request-789"}

        mock_client = MagicMock()
        mock_client.create_structured_response.return_value = (mock_proposal, mock_metadata)
        mock_client_class.return_value = mock_client

        # Create input without extra context
        idea_input = IdeaInput(idea="Build a new API")
        result, metadata = expand_idea(idea_input, mock_settings)

        # Verify extra context was not included in prompt
        call_args = mock_client.create_structured_response.call_args
        user_prompt = call_args[1]["user_prompt"]
        assert "Build a new API" in user_prompt
        assert "Additional Context" not in user_prompt

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_system_instruction_present(
        self, mock_client_class: MagicMock, mock_settings: Settings
    ) -> None:
        """Test that system instruction is provided."""
        # Setup mock response
        mock_proposal = ExpandedProposal(
            problem_statement="Test problem",
            proposed_solution="Test solution",
            assumptions=[],
            scope_non_goals=[],
        )
        mock_metadata = {"request_id": "test-request-xyz"}

        mock_client = MagicMock()
        mock_client.create_structured_response.return_value = (mock_proposal, mock_metadata)
        mock_client_class.return_value = mock_client

        # Call service
        idea_input = IdeaInput(idea="Build a new API")
        expand_idea(idea_input, mock_settings)

        # Verify system instruction was provided
        call_args = mock_client.create_structured_response.call_args
        system_instruction = call_args[1]["system_instruction"]
        assert len(system_instruction) > 0
        assert "proposal" in system_instruction.lower()
        assert "json" in system_instruction.lower()

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_developer_instruction_present(
        self, mock_client_class: MagicMock, mock_settings: Settings
    ) -> None:
        """Test that developer instruction is provided."""
        # Setup mock response
        mock_proposal = ExpandedProposal(
            problem_statement="Test problem",
            proposed_solution="Test solution",
            assumptions=[],
            scope_non_goals=[],
        )
        mock_metadata = {"request_id": "test-request-dev"}

        mock_client = MagicMock()
        mock_client.create_structured_response.return_value = (mock_proposal, mock_metadata)
        mock_client_class.return_value = mock_client

        # Call service
        idea_input = IdeaInput(idea="Build a new API")
        expand_idea(idea_input, mock_settings)

        # Verify developer instruction was provided
        call_args = mock_client.create_structured_response.call_args
        developer_instruction = call_args[1]["developer_instruction"]
        assert developer_instruction is not None
        assert len(developer_instruction) > 0

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_propagates_llm_errors(
        self, mock_client_class: MagicMock, mock_settings: Settings
    ) -> None:
        """Test that LLM errors are propagated correctly."""
        # Setup mock to raise error
        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = LLMServiceError(
            "API error", code="LLM_SERVICE_ERROR"
        )
        mock_client_class.return_value = mock_client

        # Call service and expect error
        idea_input = IdeaInput(idea="Build a new API")

        with pytest.raises(LLMServiceError) as exc_info:
            expand_idea(idea_input, mock_settings)

        assert exc_info.value.code == "LLM_SERVICE_ERROR"

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_propagates_schema_errors(
        self, mock_client_class: MagicMock, mock_settings: Settings
    ) -> None:
        """Test that schema validation errors are propagated."""
        # Setup mock to raise schema error
        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = SchemaValidationError(
            "Schema mismatch"
        )
        mock_client_class.return_value = mock_client

        # Call service and expect error
        idea_input = IdeaInput(idea="Build a new API")

        with pytest.raises(SchemaValidationError):
            expand_idea(idea_input, mock_settings)

    def test_expand_idea_input_validation(self, mock_settings: Settings) -> None:
        """Test that input validation works correctly."""
        # Test with empty idea should fail at IdeaInput level
        with pytest.raises(ValidationError):
            IdeaInput(idea="")

    @patch("consensus_engine.services.expand.OpenAIClientWrapper")
    def test_expand_idea_minimal_proposal(
        self, mock_client_class: MagicMock, mock_settings: Settings
    ) -> None:
        """Test expand with minimal proposal response."""
        # Setup mock response with minimal fields
        mock_proposal = ExpandedProposal(
            problem_statement="Minimal problem",
            proposed_solution="Minimal solution",
            assumptions=[],
            scope_non_goals=[],
        )
        mock_metadata = {"request_id": "test-minimal"}

        mock_client = MagicMock()
        mock_client.create_structured_response.return_value = (mock_proposal, mock_metadata)
        mock_client_class.return_value = mock_client

        # Call service
        idea_input = IdeaInput(idea="Simple idea")
        result, metadata = expand_idea(idea_input, mock_settings)

        # Verify minimal proposal is valid
        assert result.problem_statement == "Minimal problem"
        assert result.proposed_solution == "Minimal solution"
        assert result.assumptions == []
        assert result.scope_non_goals == []
        assert result.raw_expanded_proposal is None
