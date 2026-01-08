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
"""Expand idea endpoint router.

This module implements the POST /v1/expand-idea endpoint that validates
requests, calls the expand_idea service, and returns structured responses.
"""

import json
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status

from consensus_engine.api.dependencies import get_expand_service_with_settings
from consensus_engine.api.validation import log_validation_failure, validate_version_headers
from consensus_engine.config import Settings, get_settings
from consensus_engine.config.logging import get_logger
from consensus_engine.exceptions import (
    ConsensusEngineError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    SchemaValidationError,
    UnsupportedVersionError,
    ValidationError,
)
from consensus_engine.schemas.proposal import ExpandedProposal, IdeaInput
from consensus_engine.schemas.requests import ExpandIdeaRequest, ExpandIdeaResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["expand"])


@router.post(
    "/expand-idea",
    response_model=ExpandIdeaResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully expanded idea into structured proposal",
            "content": {
                "application/json": {
                    "example": {
                        "problem_statement": (
                            "Users need an efficient way to manage their accounts..."
                        ),
                        "proposed_solution": "Build a REST API with authentication...",
                        "assumptions": ["Python 3.11+ is available", "Users have API keys"],
                        "scope_non_goals": ["Mobile app development", "UI design"],
                        "raw_expanded_proposal": "Complete proposal text...",
                        "metadata": {
                            "request_id": "550e8400-e29b-41d4-a716-446655440000",
                            "model": "gpt-5.1",
                            "temperature": 0.7,
                            "elapsed_time": 2.5,
                        },
                    }
                }
            },
        },
        400: {
            "description": "Bad request - unsupported version",
            "content": {
                "application/json": {
                    "example": {
                        "code": "UNSUPPORTED_VERSION",
                        "message": "Schema version '0.9.0' is not supported. Current supported version: '1.0.0'. Please upgrade your client to use the supported API version.",
                        "details": {
                            "requested_schema_version": "0.9.0",
                            "supported_schema_version": "1.0.0",
                            "api_version": "v1",
                        },
                    }
                }
            },
        },
        422: {
            "description": "Validation error - invalid request format or sentence count",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "type": "value_error",
                                "loc": ["body", "idea"],
                                "msg": "Idea must contain at most 10 sentences (found 15)",
                            }
                        ]
                    }
                }
            },
        },
        500: {
            "description": "Internal server error - service or LLM error",
            "content": {
                "application/json": {
                    "example": {
                        "code": "LLM_SERVICE_ERROR",
                        "message": "Failed to process request",
                        "details": {"request_id": "550e8400-e29b-41d4-a716-446655440000"},
                    }
                }
            },
        },
        503: {
            "description": "Service unavailable - rate limit or timeout",
            "content": {
                "application/json": {
                    "example": {
                        "code": "LLM_RATE_LIMIT",
                        "message": "Rate limit exceeded, please retry later",
                        "details": {"retryable": True},
                    }
                }
            },
        },
    },
    summary="Expand an idea into a detailed proposal",
    description=(
        "Accepts a brief idea (1-10 sentences) with optional extra context "
        "and expands it into a comprehensive, structured proposal using LLM. "
        "Returns problem statement, proposed solution, assumptions, and scope boundaries. "
        "\n\n"
        "**Validation Rules:**\n"
        "- Idea: 1-10 sentences, max 10,000 characters\n"
        "- Extra context: max 50,000 characters (string or JSON)\n"
        "\n\n"
        "**Version Headers (Optional):**\n"
        "- X-Schema-Version: Schema version (current: 1.0.0)\n"
        "- X-Prompt-Set-Version: Prompt set version (current: 1.0.0)\n"
        "If not provided, defaults to current deployment versions with a warning."
    ),
)
async def expand_idea_endpoint(
    request: ExpandIdeaRequest,
    expand_service: Callable[[IdeaInput], tuple[ExpandedProposal, dict[str, Any]]] = Depends(
        get_expand_service_with_settings
    ),
    settings: Settings = Depends(get_settings),
    x_schema_version: str | None = Header(default=None, alias="X-Schema-Version"),
    x_prompt_set_version: str | None = Header(default=None, alias="X-Prompt-Set-Version"),
) -> ExpandIdeaResponse:
    """Expand an idea into a detailed proposal.

    This endpoint validates the request, converts extra_context to string
    format if needed, calls the expand_idea service, and returns a structured
    response with both the expanded proposal and metadata.

    Args:
        request: Validated request containing idea and optional extra_context
        expand_service: Injected expand_idea service with settings pre-applied
        settings: Application settings injected via dependency
        x_schema_version: Optional schema version header
        x_prompt_set_version: Optional prompt set version header

    Returns:
        ExpandIdeaResponse with structured proposal and metadata

    Raises:
        HTTPException: For validation errors (400, 422), auth errors (401),
                      rate limits (503), and service errors (500)
    """
    try:
        # Validate version headers
        versions = validate_version_headers(
            x_schema_version,
            x_prompt_set_version,
            settings,
        )
        schema_version = versions["schema_version"]
        prompt_set_version = versions["prompt_set_version"]

    except UnsupportedVersionError as e:
        log_validation_failure(
            field="version_headers",
            rule="supported_version",
            message=e.message,
            metadata=e.details,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": e.code,
                "message": e.message,
                "details": e.details,
            },
        ) from e

    # Convert extra_context to string if it's a dict
    extra_context_str: str | None = None
    if request.extra_context is not None:
        if isinstance(request.extra_context, dict):
            # Serialize dict to readable string format
            extra_context_str = json.dumps(request.extra_context, indent=2)
        else:
            extra_context_str = request.extra_context

    # Create IdeaInput for service
    idea_input = IdeaInput(idea=request.idea, extra_context=extra_context_str)

    # Log request without sensitive data
    logger.info(
        "Processing expand-idea request",
        extra={
            "has_extra_context": extra_context_str is not None,
            "schema_version": schema_version,
            "prompt_set_version": prompt_set_version,
        },
    )

    try:
        # Call expand service
        proposal, metadata = expand_service(idea_input)

        # Extract version information from metadata
        # Override with validated versions from headers
        metadata["schema_version"] = schema_version
        metadata["prompt_set_version"] = prompt_set_version

        # Build response
        response = ExpandIdeaResponse(
            problem_statement=proposal.problem_statement,
            proposed_solution=proposal.proposed_solution,
            assumptions=proposal.assumptions,
            scope_non_goals=proposal.scope_non_goals,
            raw_expanded_proposal=proposal.raw_expanded_proposal,
            schema_version=schema_version,
            prompt_set_version=prompt_set_version,
            metadata=metadata,
        )

        logger.info(
            "Successfully processed expand-idea request",
            extra={
                "request_id": metadata.get("request_id"),
                "schema_version": schema_version,
                "prompt_set_version": prompt_set_version,
            },
        )

        return response

    except LLMAuthenticationError as e:
        logger.error(
            "Authentication error",
            extra={"code": e.code, "details": e.details},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": e.code,
                "message": e.message,
                "details": e.details,
            },
        ) from e

    except LLMRateLimitError as e:
        logger.warning(
            "Rate limit exceeded",
            extra={"code": e.code, "details": e.details},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": e.code,
                "message": e.message,
                "details": e.details,
            },
        ) from e

    except LLMTimeoutError as e:
        logger.warning(
            "Request timeout",
            extra={"code": e.code, "details": e.details},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": e.code,
                "message": e.message,
                "details": e.details,
            },
        ) from e

    except SchemaValidationError as e:
        logger.error(
            "Schema validation error",
            extra={"code": e.code, "details": e.details},
        )
        # Build error detail with schema_version and field_errors if available
        error_detail = {
            "code": e.code,
            "message": e.message,
            "details": e.details,
            **({
                "schema_version": e.details["schema_version"],
                "field_errors": e.details["field_errors"],
            } if "schema_version" in e.details and "field_errors" in e.details else {})
        }

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail,
        ) from e

    except ConsensusEngineError as e:
        logger.error(
            "Service error",
            extra={"code": e.code, "details": e.details},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": e.code,
                "message": e.message,
                "details": e.details,
            },
        ) from e

    except Exception as e:
        logger.error(
            "Unexpected error processing expand-idea request",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {},
            },
        ) from e
