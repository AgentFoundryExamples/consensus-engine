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
"""OpenAI client wrapper for Consensus Engine.

This module provides a wrapper around the OpenAI SDK for making
Responses API calls with structured outputs, proper error handling,
and logging.
"""

import time
import uuid
from typing import Any, TypeVar, cast

from openai import APIConnectionError, APITimeoutError, AuthenticationError, OpenAI, RateLimitError
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

# Type variable for generic response model
T = TypeVar("T", bound=BaseModel)


class OpenAIClientWrapper:
    """Wrapper for OpenAI SDK with structured outputs support.

    This class configures and manages OpenAI Responses API calls with
    structured outputs, ensuring only validated JSON is returned.

    Attributes:
        client: OpenAI SDK client instance
        model: Model name to use for API calls
        temperature: Temperature setting for response generation
        settings: Application settings for access to step-specific config
    """

    def __init__(self, settings: Settings):
        """Initialize the OpenAI client wrapper.

        Args:
            settings: Application settings containing API key and configuration
        """
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.temperature = settings.temperature
        self.settings = settings
        logger.debug(f"OpenAI client initialized with model={self.model}")

    def create_structured_response(
        self,
        system_instruction: str,
        user_prompt: str,
        response_model: type[T],
        developer_instruction: str | None = None,
        step_name: str = "llm_call",
        model_override: str | None = None,
        temperature_override: float | None = None,
    ) -> tuple[T, dict[str, Any]]:
        """Create a structured response using OpenAI Responses API.

        This method calls the OpenAI API with structured outputs to ensure
        only validated JSON matching the response_model schema is returned.

        Args:
            system_instruction: System-level instructions for the model
            user_prompt: User prompt containing the actual request
            response_model: Pydantic model defining the expected response structure
            developer_instruction: Optional developer instructions for additional guidance
            step_name: Name of the step for telemetry logging (default: "llm_call")
            model_override: Override the default model for this call
            temperature_override: Override the default temperature for this call

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

        # Use overrides or fall back to defaults
        model = model_override or self.model
        temperature = temperature_override if temperature_override is not None else self.temperature

        logger.info(
            f"Starting OpenAI request for step={step_name}",
            extra={
                "request_id": request_id,
                "step_name": step_name,
                "model": model,
                "temperature": temperature,
            },
        )

        try:
            # Build messages list
            # Note: Developer instruction is merged into system instruction if provided
            # to avoid using non-standard message roles
            combined_system = system_instruction
            if developer_instruction:
                combined_system = f"{system_instruction}\n\n{developer_instruction}"

            messages: list[dict[str, str]] = [
                {"role": "system", "content": combined_system},
                {"role": "user", "content": user_prompt},
            ]

            # Make API call with structured output
            response = self.client.beta.chat.completions.parse(
                model=model,
                messages=messages,  # type: ignore[arg-type]
                response_format=response_model,
                temperature=temperature,
            )

            elapsed_time = time.time() - start_time

            # Extract the parsed response
            if not response.choices or not response.choices[0].message.parsed:
                raise SchemaValidationError(
                    "No parsed content in response",
                    details={"request_id": request_id, "step_name": step_name},
                )

            parsed_response = cast(T, response.choices[0].message.parsed)

            # Build metadata
            metadata = {
                "request_id": request_id,
                "step_name": step_name,
                "model": model,
                "temperature": temperature,
                "elapsed_time": elapsed_time,
                "latency": elapsed_time,
                "finish_reason": response.choices[0].finish_reason,
                "usage": response.usage.model_dump() if response.usage else None,
                "status": "success",
            }

            logger.info(
                f"OpenAI request completed successfully for step={step_name}",
                extra={
                    "request_id": request_id,
                    "step_name": step_name,
                    "model": model,
                    "temperature": temperature,
                    "latency": f"{elapsed_time:.2f}s",
                    "elapsed_time": f"{elapsed_time:.2f}s",
                    "finish_reason": metadata["finish_reason"],
                    "status": "success",
                },
            )

            return parsed_response, metadata

        except AuthenticationError as e:
            elapsed_time = time.time() - start_time
            logger.error(
                f"OpenAI authentication failed for step={step_name}",
                extra={
                    "request_id": request_id,
                    "step_name": step_name,
                    "latency": f"{elapsed_time:.2f}s",
                    "status": "error",
                    "error": str(e),
                },
            )
            raise LLMAuthenticationError(
                f"OpenAI authentication failed: {str(e)}",
                details={"request_id": request_id, "step_name": step_name},
            ) from e

        except RateLimitError as e:
            elapsed_time = time.time() - start_time
            logger.warning(
                f"OpenAI rate limit exceeded for step={step_name}",
                extra={
                    "request_id": request_id,
                    "step_name": step_name,
                    "latency": f"{elapsed_time:.2f}s",
                    "status": "rate_limited",
                    "error": str(e),
                },
            )
            raise LLMRateLimitError(
                f"OpenAI rate limit exceeded: {str(e)}",
                details={"request_id": request_id, "step_name": step_name, "retryable": True},
            ) from e

        except APITimeoutError as e:
            elapsed_time = time.time() - start_time
            logger.warning(
                f"OpenAI request timed out for step={step_name}",
                extra={
                    "request_id": request_id,
                    "step_name": step_name,
                    "latency": f"{elapsed_time:.2f}s",
                    "status": "timeout",
                    "error": str(e),
                },
            )
            raise LLMTimeoutError(
                f"OpenAI request timed out: {str(e)}",
                details={"request_id": request_id, "step_name": step_name, "retryable": True},
            ) from e

        except APIConnectionError as e:
            elapsed_time = time.time() - start_time
            logger.error(
                f"OpenAI connection error for step={step_name}",
                extra={
                    "request_id": request_id,
                    "step_name": step_name,
                    "latency": f"{elapsed_time:.2f}s",
                    "status": "connection_error",
                    "error": str(e),
                },
            )
            raise LLMServiceError(
                f"OpenAI connection error: {str(e)}",
                code="LLM_CONNECTION_ERROR",
                details={"request_id": request_id, "step_name": step_name, "retryable": True},
            ) from e

        except SchemaValidationError:
            elapsed_time = time.time() - start_time
            logger.error(
                f"Schema validation error for step={step_name}",
                extra={
                    "request_id": request_id,
                    "step_name": step_name,
                    "latency": f"{elapsed_time:.2f}s",
                    "status": "validation_error",
                },
            )
            # Re-raise SchemaValidationError as-is (don't wrap it)
            raise

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(
                f"Unexpected error in OpenAI request for step={step_name}",
                extra={
                    "request_id": request_id,
                    "step_name": step_name,
                    "latency": f"{elapsed_time:.2f}s",
                    "status": "error",
                    "error": str(e),
                },
                exc_info=True,
            )
            raise LLMServiceError(
                f"Unexpected error in OpenAI request: {str(e)}",
                details={"request_id": request_id, "step_name": step_name},
            ) from e
