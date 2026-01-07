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
"""Unit tests for OpenAI client wrapper."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)
from pydantic import BaseModel

from consensus_engine.clients.openai_client import OpenAIClientWrapper
from consensus_engine.config.settings import Settings
from consensus_engine.exceptions import (
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMServiceError,
    LLMTimeoutError,
    SchemaValidationError,
)


class MockResponseModel(BaseModel):
    """Mock response model for structured output tests."""

    test_field: str
    test_number: int


@pytest.fixture
def mock_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Create mock settings for tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-client-tests")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.1")
    monkeypatch.setenv("TEMPERATURE", "0.7")
    return Settings()


class TestOpenAIClientWrapperInit:
    """Test suite for OpenAIClientWrapper initialization."""

    @patch("consensus_engine.clients.openai_client.OpenAI")
    def test_client_initialization(self, mock_openai: Mock, mock_settings: Settings) -> None:
        """Test client initializes with correct settings."""
        wrapper = OpenAIClientWrapper(mock_settings)

        assert wrapper.model == "gpt-5.1"
        assert wrapper.temperature == 0.7
        mock_openai.assert_called_once_with(api_key="sk-test-key-for-client-tests")

    @patch("consensus_engine.clients.openai_client.OpenAI")
    def test_client_uses_custom_model(
        self, mock_openai: Mock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test client uses custom model from settings."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4.0")
        settings = Settings()

        wrapper = OpenAIClientWrapper(settings)

        assert wrapper.model == "gpt-4.0"


class TestOpenAIClientWrapperStructuredResponse:
    """Test suite for create_structured_response method."""

    @patch("consensus_engine.clients.openai_client.OpenAI")
    def test_successful_structured_response(
        self, mock_openai: Mock, mock_settings: Settings
    ) -> None:
        """Test successful structured response creation."""
        # Setup mock response
        mock_parsed = MockResponseModel(test_field="success", test_number=42)
        mock_choice = MagicMock()
        mock_choice.message.parsed = mock_parsed
        mock_choice.finish_reason = "stop"

        mock_usage = MagicMock()
        mock_usage.model_dump.return_value = {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_openai.return_value = mock_client

        # Create wrapper and make request
        wrapper = OpenAIClientWrapper(mock_settings)
        result, metadata = wrapper.create_structured_response(
            system_instruction="Test system",
            user_prompt="Test prompt",
            response_model=MockResponseModel,
        )

        # Verify result
        assert isinstance(result, MockResponseModel)
        assert result.test_field == "success"
        assert result.test_number == 42

        # Verify metadata
        assert "request_id" in metadata
        assert metadata["model"] == "gpt-5.1"
        assert metadata["temperature"] == 0.7
        assert metadata["finish_reason"] == "stop"
        assert metadata["usage"]["total_tokens"] == 30

        # Verify API call
        mock_client.beta.chat.completions.parse.assert_called_once()
        call_args = mock_client.beta.chat.completions.parse.call_args
        assert call_args[1]["model"] == "gpt-5.1"
        assert call_args[1]["temperature"] == 0.7
        assert call_args[1]["response_format"] == MockResponseModel

    @patch("consensus_engine.clients.openai_client.OpenAI")
    def test_structured_response_with_developer_instruction(
        self, mock_openai: Mock, mock_settings: Settings
    ) -> None:
        """Test structured response with developer instruction."""
        # Setup mock response
        mock_parsed = MockResponseModel(test_field="success", test_number=42)
        mock_choice = MagicMock()
        mock_choice.message.parsed = mock_parsed
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = None

        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_openai.return_value = mock_client

        # Create wrapper and make request
        wrapper = OpenAIClientWrapper(mock_settings)
        result, metadata = wrapper.create_structured_response(
            system_instruction="Test system",
            user_prompt="Test prompt",
            response_model=MockResponseModel,
            developer_instruction="Test developer instruction",
        )

        # Verify developer instruction is merged into system instruction
        call_args = mock_client.beta.chat.completions.parse.call_args
        messages = call_args[1]["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "Test system" in messages[0]["content"]
        assert "Test developer instruction" in messages[0]["content"]
        assert messages[1]["role"] == "user"

    @patch("consensus_engine.clients.openai_client.OpenAI")
    def test_authentication_error_handling(
        self, mock_openai: Mock, mock_settings: Settings
    ) -> None:
        """Test authentication error is properly wrapped."""
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.side_effect = AuthenticationError(
            "Invalid API key", response=MagicMock(), body=None
        )
        mock_openai.return_value = mock_client

        wrapper = OpenAIClientWrapper(mock_settings)

        with pytest.raises(LLMAuthenticationError) as exc_info:
            wrapper.create_structured_response(
                system_instruction="Test",
                user_prompt="Test",
                response_model=MockResponseModel,
            )

        assert "authentication failed" in str(exc_info.value).lower()
        assert exc_info.value.code == "LLM_AUTH_ERROR"
        assert "request_id" in exc_info.value.details

    @patch("consensus_engine.clients.openai_client.OpenAI")
    def test_rate_limit_error_handling(self, mock_openai: Mock, mock_settings: Settings) -> None:
        """Test rate limit error is properly wrapped."""
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.side_effect = RateLimitError(
            "Rate limit exceeded", response=MagicMock(), body=None
        )
        mock_openai.return_value = mock_client

        wrapper = OpenAIClientWrapper(mock_settings)

        with pytest.raises(LLMRateLimitError) as exc_info:
            wrapper.create_structured_response(
                system_instruction="Test",
                user_prompt="Test",
                response_model=MockResponseModel,
            )

        assert "rate limit" in str(exc_info.value).lower()
        assert exc_info.value.code == "LLM_RATE_LIMIT"
        assert exc_info.value.details["retryable"] is True

    @patch("consensus_engine.clients.openai_client.OpenAI")
    def test_timeout_error_handling(self, mock_openai: Mock, mock_settings: Settings) -> None:
        """Test timeout error is properly wrapped."""
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.side_effect = APITimeoutError(request=MagicMock())
        mock_openai.return_value = mock_client

        wrapper = OpenAIClientWrapper(mock_settings)

        with pytest.raises(LLMTimeoutError) as exc_info:
            wrapper.create_structured_response(
                system_instruction="Test",
                user_prompt="Test",
                response_model=MockResponseModel,
            )

        assert "timed out" in str(exc_info.value).lower()
        assert exc_info.value.code == "LLM_TIMEOUT"
        assert exc_info.value.details["retryable"] is True

    @patch("consensus_engine.clients.openai_client.OpenAI")
    def test_connection_error_handling(self, mock_openai: Mock, mock_settings: Settings) -> None:
        """Test connection error is properly wrapped."""
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.side_effect = APIConnectionError(
            request=MagicMock()
        )
        mock_openai.return_value = mock_client

        wrapper = OpenAIClientWrapper(mock_settings)

        with pytest.raises(LLMServiceError) as exc_info:
            wrapper.create_structured_response(
                system_instruction="Test",
                user_prompt="Test",
                response_model=MockResponseModel,
            )

        assert "connection error" in str(exc_info.value).lower()
        assert exc_info.value.code == "LLM_CONNECTION_ERROR"
        assert exc_info.value.details["retryable"] is True

    @patch("consensus_engine.clients.openai_client.OpenAI")
    def test_no_parsed_content_error(self, mock_openai: Mock, mock_settings: Settings) -> None:
        """Test error when response has no parsed content."""
        mock_response = MagicMock()
        mock_response.choices = []

        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_openai.return_value = mock_client

        wrapper = OpenAIClientWrapper(mock_settings)

        with pytest.raises(SchemaValidationError) as exc_info:
            wrapper.create_structured_response(
                system_instruction="Test",
                user_prompt="Test",
                response_model=MockResponseModel,
            )

        assert "no parsed content" in str(exc_info.value).lower()
        assert exc_info.value.code == "SCHEMA_VALIDATION_ERROR"

    @patch("consensus_engine.clients.openai_client.OpenAI")
    def test_unexpected_error_handling(self, mock_openai: Mock, mock_settings: Settings) -> None:
        """Test unexpected error is properly wrapped."""
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.side_effect = Exception("Unexpected error")
        mock_openai.return_value = mock_client

        wrapper = OpenAIClientWrapper(mock_settings)

        with pytest.raises(LLMServiceError) as exc_info:
            wrapper.create_structured_response(
                system_instruction="Test",
                user_prompt="Test",
                response_model=MockResponseModel,
            )

        assert "unexpected error" in str(exc_info.value).lower()
        assert "request_id" in exc_info.value.details
