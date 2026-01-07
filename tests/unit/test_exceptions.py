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
"""Unit tests for domain exceptions."""

import pytest

from consensus_engine.exceptions import (
    ConsensusEngineError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMServiceError,
    LLMTimeoutError,
    SchemaValidationError,
)


class TestConsensusEngineError:
    """Test suite for base ConsensusEngineError."""

    def test_base_error_creation(self) -> None:
        """Test creating base error with message."""
        error = ConsensusEngineError("Test error")

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.code == "INTERNAL_ERROR"
        assert error.details == {}

    def test_base_error_with_code(self) -> None:
        """Test creating base error with custom code."""
        error = ConsensusEngineError("Test error", code="CUSTOM_CODE")

        assert error.code == "CUSTOM_CODE"

    def test_base_error_with_details(self) -> None:
        """Test creating base error with details."""
        details = {"key": "value", "request_id": "123"}
        error = ConsensusEngineError("Test error", details=details)

        assert error.details == details
        assert error.details["key"] == "value"
        assert error.details["request_id"] == "123"

    def test_base_error_is_exception(self) -> None:
        """Test base error is an Exception."""
        error = ConsensusEngineError("Test error")

        assert isinstance(error, Exception)


class TestLLMServiceError:
    """Test suite for LLMServiceError."""

    def test_llm_service_error_creation(self) -> None:
        """Test creating LLM service error."""
        error = LLMServiceError("API failed")

        assert str(error) == "API failed"
        assert error.message == "API failed"
        assert error.code == "LLM_SERVICE_ERROR"

    def test_llm_service_error_custom_code(self) -> None:
        """Test creating LLM service error with custom code."""
        error = LLMServiceError("API failed", code="CUSTOM_LLM_ERROR")

        assert error.code == "CUSTOM_LLM_ERROR"

    def test_llm_service_error_inherits_base(self) -> None:
        """Test LLM service error inherits from base error."""
        error = LLMServiceError("API failed")

        assert isinstance(error, ConsensusEngineError)
        assert isinstance(error, Exception)


class TestLLMTimeoutError:
    """Test suite for LLMTimeoutError."""

    def test_timeout_error_default_message(self) -> None:
        """Test timeout error with default message."""
        error = LLMTimeoutError()

        assert str(error) == "LLM request timed out"
        assert error.code == "LLM_TIMEOUT"

    def test_timeout_error_custom_message(self) -> None:
        """Test timeout error with custom message."""
        error = LLMTimeoutError("Custom timeout message")

        assert str(error) == "Custom timeout message"
        assert error.code == "LLM_TIMEOUT"

    def test_timeout_error_with_details(self) -> None:
        """Test timeout error with details."""
        error = LLMTimeoutError(details={"request_id": "abc", "retryable": True})

        assert error.details["request_id"] == "abc"
        assert error.details["retryable"] is True

    def test_timeout_error_inherits_llm_service_error(self) -> None:
        """Test timeout error inherits from LLM service error."""
        error = LLMTimeoutError()

        assert isinstance(error, LLMServiceError)
        assert isinstance(error, ConsensusEngineError)


class TestLLMRateLimitError:
    """Test suite for LLMRateLimitError."""

    def test_rate_limit_error_default_message(self) -> None:
        """Test rate limit error with default message."""
        error = LLMRateLimitError()

        assert str(error) == "LLM rate limit exceeded"
        assert error.code == "LLM_RATE_LIMIT"

    def test_rate_limit_error_custom_message(self) -> None:
        """Test rate limit error with custom message."""
        error = LLMRateLimitError("Rate limit hit at 1000 requests")

        assert str(error) == "Rate limit hit at 1000 requests"

    def test_rate_limit_error_inherits_llm_service_error(self) -> None:
        """Test rate limit error inherits from LLM service error."""
        error = LLMRateLimitError()

        assert isinstance(error, LLMServiceError)


class TestLLMAuthenticationError:
    """Test suite for LLMAuthenticationError."""

    def test_auth_error_default_message(self) -> None:
        """Test authentication error with default message."""
        error = LLMAuthenticationError()

        assert str(error) == "LLM authentication failed"
        assert error.code == "LLM_AUTH_ERROR"

    def test_auth_error_custom_message(self) -> None:
        """Test authentication error with custom message."""
        error = LLMAuthenticationError("Invalid API key")

        assert str(error) == "Invalid API key"

    def test_auth_error_inherits_llm_service_error(self) -> None:
        """Test authentication error inherits from LLM service error."""
        error = LLMAuthenticationError()

        assert isinstance(error, LLMServiceError)


class TestSchemaValidationError:
    """Test suite for SchemaValidationError."""

    def test_schema_error_default_message(self) -> None:
        """Test schema validation error with default message."""
        error = SchemaValidationError()

        assert str(error) == "Schema validation failed"
        assert error.code == "SCHEMA_VALIDATION_ERROR"

    def test_schema_error_custom_message(self) -> None:
        """Test schema validation error with custom message."""
        error = SchemaValidationError("Missing required field 'name'")

        assert str(error) == "Missing required field 'name'"

    def test_schema_error_with_details(self) -> None:
        """Test schema validation error with details."""
        details = {"field": "name", "expected": "string", "got": "null"}
        error = SchemaValidationError("Field type mismatch", details=details)

        assert error.details == details
        assert error.details["field"] == "name"

    def test_schema_error_inherits_base(self) -> None:
        """Test schema validation error inherits from base error."""
        error = SchemaValidationError()

        assert isinstance(error, ConsensusEngineError)


class TestExceptionHierarchy:
    """Test suite for exception hierarchy."""

    def test_all_errors_inherit_from_base(self) -> None:
        """Test all custom errors inherit from base error."""
        errors = [
            LLMServiceError("test"),
            LLMTimeoutError(),
            LLMRateLimitError(),
            LLMAuthenticationError(),
            SchemaValidationError(),
        ]

        for error in errors:
            assert isinstance(error, ConsensusEngineError)
            assert isinstance(error, Exception)

    def test_error_catching_by_base_class(self) -> None:
        """Test errors can be caught by base class."""
        with pytest.raises(ConsensusEngineError):
            raise LLMTimeoutError()

        with pytest.raises(ConsensusEngineError):
            raise SchemaValidationError()

    def test_error_catching_by_parent_class(self) -> None:
        """Test errors can be caught by parent class."""
        with pytest.raises(LLMServiceError):
            raise LLMTimeoutError()

        with pytest.raises(LLMServiceError):
            raise LLMRateLimitError()
