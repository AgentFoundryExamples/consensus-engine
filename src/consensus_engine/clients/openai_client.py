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
retry logic with exponential backoff, and logging.
"""

import time
import uuid
from typing import TYPE_CHECKING, Any, TypeVar, cast

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

if TYPE_CHECKING:
    from consensus_engine.config.instruction_builder import InstructionPayload

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
        max_retries: int | None = None,
    ) -> tuple[T, dict[str, Any]]:
        """Create a structured response using OpenAI Responses API.

        This method calls the OpenAI Responses API with structured outputs to ensure
        only validated JSON matching the response_model schema is returned.
        Implements retry logic with exponential backoff for retryable errors.

        Args:
            system_instruction: System-level instructions for the model
            user_prompt: User prompt containing the actual request
            response_model: Pydantic model defining the expected response structure
            developer_instruction: Optional developer instructions for additional guidance
            step_name: Name of the step for telemetry logging (default: "llm_call")
            model_override: Override the default model for this call
            temperature_override: Override the default temperature for this call
            max_retries: Maximum retry attempts (default: from settings)

        Returns:
            Tuple of (parsed response model instance, metadata dict with request_id, timing, etc.)

        Raises:
            LLMAuthenticationError: If API authentication fails
            LLMRateLimitError: If rate limit is exceeded after all retries
            LLMTimeoutError: If request times out after all retries
            LLMServiceError: For other API errors
            SchemaValidationError: If response doesn't match expected schema
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Use overrides or fall back to defaults
        model = model_override or self.model
        temperature = temperature_override if temperature_override is not None else self.temperature
        max_retries_count = (
            max_retries if max_retries is not None else self.settings.max_retries_per_persona
        )

        logger.info(
            f"Starting OpenAI request for step={step_name}",
            extra={
                "request_id": request_id,
                "step_name": step_name,
                "model": model,
                "temperature": temperature,
                "max_retries": max_retries_count,
            },
        )

        # Build combined instruction with system + developer instructions
        combined_instruction = system_instruction
        if developer_instruction:
            combined_instruction = f"{system_instruction}\n\n{developer_instruction}"

        # Retry loop with exponential backoff
        attempt = 0
        last_exception: Exception | None = None

        while attempt < max_retries_count:
            attempt += 1
            attempt_start = time.time()

            try:
                logger.debug(
                    f"OpenAI request attempt {attempt}/{max_retries_count}",
                    extra={
                        "request_id": request_id,
                        "step_name": step_name,
                        "attempt": attempt,
                        "max_retries": max_retries_count,
                    },
                )

                # Make API call with Responses API and structured parsing
                # Using responses.parse() for structured outputs with text_format parameter
                response = self.client.responses.parse(
                    model=model,
                    input=user_prompt,
                    instructions=combined_instruction,
                    temperature=temperature,
                    text_format=response_model,
                )

                # Calculate elapsed time immediately after API call
                elapsed_time = time.time() - start_time
                attempt_elapsed = time.time() - attempt_start

                # Extract the parsed response from output_parsed property
                parsed_response = response.output_parsed
                if parsed_response is None:
                    raise SchemaValidationError(
                        "No parsed content in response",
                        details={
                            "request_id": request_id,
                            "step_name": step_name,
                            "attempt": attempt,
                        },
                    )

                # Ensure it's the correct type
                parsed_response = cast(T, parsed_response)

                # Build metadata
                metadata = {
                    "request_id": request_id,
                    "step_name": step_name,
                    "model": model,
                    "temperature": temperature,
                    "elapsed_time": elapsed_time,
                    "latency": elapsed_time,
                    "attempt_count": attempt,
                    "attempt_elapsed": attempt_elapsed,
                    "status": "success",
                }

                # Add usage info if available
                if hasattr(response, "usage") and response.usage:
                    metadata["usage"] = {
                        "input_tokens": getattr(response.usage, "input_tokens", None),
                        "output_tokens": getattr(response.usage, "output_tokens", None),
                        "total_tokens": getattr(response.usage, "total_tokens", None),
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
                        "attempt_count": attempt,
                        "status": "success",
                    },
                )

                return parsed_response, metadata

            except AuthenticationError as e:
                # Authentication errors are not retryable
                elapsed_time = time.time() - start_time
                logger.error(
                    f"OpenAI authentication failed for step={step_name}",
                    extra={
                        "request_id": request_id,
                        "step_name": step_name,
                        "latency": f"{elapsed_time:.2f}s",
                        "status": "error",
                        "error": str(e),
                        "attempt": attempt,
                    },
                )
                raise LLMAuthenticationError(
                    f"OpenAI authentication failed: {str(e)}",
                    details={"request_id": request_id, "step_name": step_name, "attempt": attempt},
                ) from e

            except (RateLimitError, APITimeoutError, APIConnectionError) as e:
                # These errors are retryable
                elapsed_time = time.time() - start_time
                last_exception = e

                error_type = "rate_limited" if isinstance(e, RateLimitError) else (
                    "timeout" if isinstance(e, APITimeoutError) else "connection_error"
                )

                if attempt < max_retries_count:
                    # Calculate backoff delay with exponential increase
                    backoff_delay = (
                        self.settings.retry_initial_backoff_seconds
                        * (self.settings.retry_backoff_multiplier ** (attempt - 1))
                    )

                    logger.warning(
                        f"OpenAI {error_type} for step={step_name}, "
                        f"retrying in {backoff_delay:.2f}s (attempt {attempt}/{max_retries_count})",
                        extra={
                            "request_id": request_id,
                            "step_name": step_name,
                            "latency": f"{elapsed_time:.2f}s",
                            "status": error_type,
                            "error": str(e),
                            "attempt": attempt,
                            "max_retries": max_retries_count,
                            "backoff_delay": backoff_delay,
                        },
                    )

                    time.sleep(backoff_delay)
                    continue
                else:
                    # Exhausted all retries
                    logger.error(
                        f"OpenAI {error_type} for step={step_name}, exhausted all retries",
                        extra={
                            "request_id": request_id,
                            "step_name": step_name,
                            "latency": f"{elapsed_time:.2f}s",
                            "status": error_type,
                            "error": str(e),
                            "attempt": attempt,
                            "max_retries": max_retries_count,
                        },
                    )

                    if isinstance(e, RateLimitError):
                        raise LLMRateLimitError(
                            f"OpenAI rate limit exceeded after {attempt} attempts: {str(e)}",
                            details={
                                "request_id": request_id,
                                "step_name": step_name,
                                "retryable": False,
                                "attempt": attempt,
                            },
                        ) from e
                    elif isinstance(e, APITimeoutError):
                        raise LLMTimeoutError(
                            f"OpenAI request timed out after {attempt} attempts: {str(e)}",
                            details={
                                "request_id": request_id,
                                "step_name": step_name,
                                "retryable": False,
                                "attempt": attempt,
                            },
                        ) from e
                    else:
                        raise LLMServiceError(
                            f"OpenAI connection error after {attempt} attempts: {str(e)}",
                            code="LLM_CONNECTION_ERROR",
                            details={
                                "request_id": request_id,
                                "step_name": step_name,
                                "retryable": False,
                                "attempt": attempt,
                            },
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
                        "attempt": attempt,
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
                        "attempt": attempt,
                    },
                    exc_info=True,
                )
                raise LLMServiceError(
                    f"Unexpected error in OpenAI request: {str(e)}",
                    details={"request_id": request_id, "step_name": step_name, "attempt": attempt},
                ) from e

        # Should never reach here, but handle it just in case
        elapsed_time = time.time() - start_time
        logger.error(
            f"OpenAI request failed after {max_retries_count} attempts for step={step_name}",
            extra={
                "request_id": request_id,
                "step_name": step_name,
                "latency": f"{elapsed_time:.2f}s",
                "max_retries": max_retries_count,
            },
        )

        if last_exception:
            raise LLMServiceError(
                f"OpenAI request failed after {max_retries_count} attempts: {str(last_exception)}",
                details={
                    "request_id": request_id,
                    "step_name": step_name,
                    "attempt": max_retries_count,
                },
            ) from last_exception
        else:
            raise LLMServiceError(
                f"OpenAI request failed after {max_retries_count} attempts",
                details={
                    "request_id": request_id,
                    "step_name": step_name,
                    "attempt": max_retries_count,
                },
            )

    def create_structured_response_with_payload(
        self,
        instruction_payload: "InstructionPayload",
        response_model: type[T],
        step_name: str = "llm_call",
        model_override: str | None = None,
        temperature_override: float | None = None,
        max_retries: int | None = None,
    ) -> tuple[T, dict[str, Any]]:
        """Create a structured response using an InstructionPayload.

        This method is a convenience wrapper around create_structured_response
        that accepts an InstructionPayload from the InstructionBuilder.

        Args:
            instruction_payload: InstructionPayload with system, developer, and user content
            response_model: Pydantic model defining the expected response structure
            step_name: Name of the step for telemetry logging (default: "llm_call")
            model_override: Override the default model for this call
            temperature_override: Override the default temperature for this call
            max_retries: Maximum retry attempts (default: from settings)

        Returns:
            Tuple of (parsed response model instance, metadata dict with request_id, timing, etc.)

        Raises:
            LLMAuthenticationError: If API authentication fails
            LLMRateLimitError: If rate limit is exceeded after all retries
            LLMTimeoutError: If request times out after all retries
            LLMServiceError: For other API errors
            SchemaValidationError: If response doesn't match expected schema
        """
        # Extract prompt_set_version from payload metadata
        prompt_set_version = instruction_payload.metadata.get("prompt_set_version")

        # Call the main method
        parsed_response, metadata = self.create_structured_response(
            system_instruction=instruction_payload.system_instruction,
            user_prompt=instruction_payload.user_content,
            response_model=response_model,
            developer_instruction=instruction_payload.developer_instruction,
            step_name=step_name,
            model_override=model_override,
            temperature_override=temperature_override,
            max_retries=max_retries,
        )

        # Add prompt_set_version to metadata
        if prompt_set_version:
            metadata["prompt_set_version"] = prompt_set_version

        # Add payload metadata to response metadata
        metadata["instruction_payload_metadata"] = instruction_payload.metadata

        return parsed_response, metadata
