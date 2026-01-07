"""OpenAI client wrapper for Consensus Engine.

This module provides a wrapper around the OpenAI SDK for making
Responses API calls with structured outputs, proper error handling,
and logging.
"""

import time
import uuid
from typing import Any

from openai import OpenAI
from openai import APIConnectionError, APITimeoutError, AuthenticationError, RateLimitError
from pydantic import BaseModel

from consensus_engine.config.logging import get_logger
from consensus_engine.config.settings import Settings
from consensus_engine.exceptions import (
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMServiceError,
    LLMTimeoutError,
    SchemaValidationError,
)

logger = get_logger(__name__)


class OpenAIClientWrapper:
    """Wrapper for OpenAI SDK with structured outputs support.

    This class configures and manages OpenAI Responses API calls with
    structured outputs, ensuring only validated JSON is returned.

    Attributes:
        client: OpenAI SDK client instance
        model: Model name to use for API calls
        temperature: Temperature setting for response generation
    """

    def __init__(self, settings: Settings):
        """Initialize the OpenAI client wrapper.

        Args:
            settings: Application settings containing API key and configuration
        """
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.temperature = settings.temperature
        logger.debug(f"OpenAI client initialized with model={self.model}")

    def create_structured_response(
        self,
        system_instruction: str,
        user_prompt: str,
        response_model: type[BaseModel],
        developer_instruction: str | None = None,
    ) -> tuple[BaseModel, dict[str, Any]]:
        """Create a structured response using OpenAI Responses API.

        This method calls the OpenAI API with structured outputs to ensure
        only validated JSON matching the response_model schema is returned.

        Args:
            system_instruction: System-level instructions for the model
            user_prompt: User prompt containing the actual request
            response_model: Pydantic model defining the expected response structure
            developer_instruction: Optional developer instructions for additional guidance

        Returns:
            Tuple of (parsed response model instance, metadata dict with request_id, timing, etc.)

        Raises:
            LLMAuthenticationError: If API authentication fails
            LLMRateLimitError: If rate limit is exceeded
            LLMTimeoutError: If request times out
            LLMServiceError: For other API errors
            SchemaValidationError: If response doesn't match expected schema
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info(
            f"Starting OpenAI request",
            extra={
                "request_id": request_id,
                "model": self.model,
                "temperature": self.temperature,
            },
        )

        try:
            # Build messages list
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": system_instruction},
            ]

            # Add developer instruction if provided
            if developer_instruction:
                messages.append({"role": "developer", "content": developer_instruction})

            # Add user prompt
            messages.append({"role": "user", "content": user_prompt})

            # Make API call with structured output
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                response_format=response_model,
                temperature=self.temperature,
            )

            elapsed_time = time.time() - start_time

            # Extract the parsed response
            if not response.choices or not response.choices[0].message.parsed:
                raise SchemaValidationError(
                    "No parsed content in response",
                    details={"request_id": request_id},
                )

            parsed_response = response.choices[0].message.parsed

            # Build metadata
            metadata = {
                "request_id": request_id,
                "model": self.model,
                "temperature": self.temperature,
                "elapsed_time": elapsed_time,
                "finish_reason": response.choices[0].finish_reason if response.choices else None,
                "usage": response.usage.model_dump() if response.usage else None,
            }

            logger.info(
                f"OpenAI request completed successfully",
                extra={
                    "request_id": request_id,
                    "elapsed_time": f"{elapsed_time:.2f}s",
                    "finish_reason": metadata["finish_reason"],
                },
            )

            return parsed_response, metadata

        except AuthenticationError as e:
            logger.error(
                f"OpenAI authentication failed",
                extra={"request_id": request_id, "error": str(e)},
            )
            raise LLMAuthenticationError(
                f"OpenAI authentication failed: {str(e)}",
                details={"request_id": request_id},
            ) from e

        except RateLimitError as e:
            logger.warning(
                f"OpenAI rate limit exceeded",
                extra={"request_id": request_id, "error": str(e)},
            )
            raise LLMRateLimitError(
                f"OpenAI rate limit exceeded: {str(e)}",
                details={"request_id": request_id, "retryable": True},
            ) from e

        except APITimeoutError as e:
            logger.warning(
                f"OpenAI request timed out",
                extra={"request_id": request_id, "error": str(e)},
            )
            raise LLMTimeoutError(
                f"OpenAI request timed out: {str(e)}",
                details={"request_id": request_id, "retryable": True},
            ) from e

        except APIConnectionError as e:
            logger.error(
                f"OpenAI connection error",
                extra={"request_id": request_id, "error": str(e)},
            )
            raise LLMServiceError(
                f"OpenAI connection error: {str(e)}",
                code="LLM_CONNECTION_ERROR",
                details={"request_id": request_id, "retryable": True},
            ) from e

        except Exception as e:
            logger.error(
                f"Unexpected error in OpenAI request",
                extra={"request_id": request_id, "error": str(e)},
                exc_info=True,
            )
            raise LLMServiceError(
                f"Unexpected error in OpenAI request: {str(e)}",
                details={"request_id": request_id},
            ) from e
