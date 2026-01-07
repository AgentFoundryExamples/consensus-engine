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
"""Domain exceptions for Consensus Engine.

This module defines custom exceptions with machine-readable error codes
for proper error handling and HTTP status code mapping.
"""


class ConsensusEngineError(Exception):
    """Base exception for all Consensus Engine errors.

    Attributes:
        message: Human-readable error message
        code: Machine-readable error code for HTTP translation
        details: Optional additional error details
    """

    def __init__(self, message: str, code: str = "INTERNAL_ERROR", details: dict | None = None):
        """Initialize the exception.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Optional additional error details
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class LLMServiceError(ConsensusEngineError):
    """Exception for LLM service errors.

    Used for wrapping OpenAI API errors and transport failures.
    """

    def __init__(self, message: str, code: str = "LLM_SERVICE_ERROR", details: dict | None = None):
        """Initialize LLM service error.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
            details: Optional additional error details
        """
        super().__init__(message, code, details)


class LLMTimeoutError(LLMServiceError):
    """Exception for LLM request timeouts."""

    def __init__(self, message: str = "LLM request timed out", details: dict | None = None):
        """Initialize timeout error.

        Args:
            message: Human-readable error message
            details: Optional additional error details
        """
        super().__init__(message, "LLM_TIMEOUT", details)


class LLMRateLimitError(LLMServiceError):
    """Exception for LLM rate limit errors."""

    def __init__(self, message: str = "LLM rate limit exceeded", details: dict | None = None):
        """Initialize rate limit error.

        Args:
            message: Human-readable error message
            details: Optional additional error details
        """
        super().__init__(message, "LLM_RATE_LIMIT", details)


class LLMAuthenticationError(LLMServiceError):
    """Exception for LLM authentication errors."""

    def __init__(self, message: str = "LLM authentication failed", details: dict | None = None):
        """Initialize authentication error.

        Args:
            message: Human-readable error message
            details: Optional additional error details
        """
        super().__init__(message, "LLM_AUTH_ERROR", details)


class SchemaValidationError(ConsensusEngineError):
    """Exception for structured output schema validation failures."""

    def __init__(self, message: str = "Schema validation failed", details: dict | None = None):
        """Initialize schema validation error.

        Args:
            message: Human-readable error message
            details: Optional additional error details
        """
        super().__init__(message, "SCHEMA_VALIDATION_ERROR", details)
