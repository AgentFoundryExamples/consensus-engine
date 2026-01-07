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
"""Request and response schemas for API endpoints.

This module defines Pydantic models for API request validation and response
serialization, including custom validators for sentence-level constraints.
"""

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator


def count_sentences(text: str) -> int:
    """Count sentences in text using basic punctuation rules.

    Args:
        text: Text to count sentences in

    Returns:
        Number of sentences found
    """
    # Strip whitespace and check for empty string
    text = text.strip()
    if not text:
        return 0

    # Split on sentence-ending punctuation (.!?) followed by space or end of string
    # This handles common cases like "Hello. World!" or "Test! Another."
    sentences = re.split(r"[.!?]+\s+|[.!?]+$", text)

    # Filter out empty strings from the split
    sentences = [s.strip() for s in sentences if s.strip()]

    return len(sentences)


class ExpandIdeaRequest(BaseModel):
    """Request model for POST /v1/expand-idea endpoint.

    Attributes:
        idea: The core idea to expand (1-10 sentences)
        extra_context: Optional additional context as dict or string
    """

    idea: str = Field(
        ...,
        min_length=1,
        description="The core idea or problem to expand (1-10 sentences)",
        examples=["Build a REST API for user management with authentication support."],
    )
    extra_context: dict[str, Any] | str | None = Field(
        default=None,
        description="Optional additional context or constraints (dict or string)",
        examples=[
            "Must support Python 3.11+",
            {"language": "Python", "version": "3.11+", "features": ["auth", "CRUD"]},
        ],
    )

    @field_validator("idea")
    @classmethod
    def validate_sentence_count(cls, v: str) -> str:
        """Validate that idea contains 1-10 sentences.

        Args:
            v: The idea text to validate

        Returns:
            The validated idea text

        Raises:
            ValueError: If sentence count is outside 1-10 range
        """
        sentence_count = count_sentences(v)

        if sentence_count < 1:
            raise ValueError("Idea must contain at least 1 sentence")

        if sentence_count > 10:
            raise ValueError(f"Idea must contain at most 10 sentences (found {sentence_count})")

        return v


class ExpandIdeaResponse(BaseModel):
    """Response model for POST /v1/expand-idea endpoint.

    Attributes:
        problem_statement: Clear articulation of the problem
        proposed_solution: Detailed solution approach
        assumptions: List of underlying assumptions
        scope_non_goals: List of what is out of scope
        title: Optional short title for the proposal
        summary: Optional brief summary of the proposal
        raw_idea: Optional original idea text before expansion
        raw_expanded_proposal: Optional complete proposal text
        metadata: Request metadata (request_id, model, timing, etc.)
    """

    problem_statement: str = Field(
        ..., description="Clear articulation of the problem to be solved"
    )
    proposed_solution: str = Field(
        ..., description="Detailed description of the proposed solution approach"
    )
    assumptions: list[str] = Field(
        ..., description="List of underlying assumptions made in the proposal"
    )
    scope_non_goals: list[str] = Field(
        ...,
        description="List of what is explicitly out of scope or non-goals",
    )
    title: str | None = Field(default=None, description="Optional short title for the proposal")
    summary: str | None = Field(default=None, description="Optional brief summary of the proposal")
    raw_idea: str | None = Field(
        default=None, description="Optional original idea text before expansion"
    )
    raw_expanded_proposal: str | None = Field(
        default=None, description="Optional complete expanded proposal text or additional notes"
    )
    metadata: dict[str, Any] = Field(
        ...,
        description="Request metadata including request_id, model, temperature, timing, etc.",
    )


class ErrorResponse(BaseModel):
    """Error response model for API errors.

    Attributes:
        code: Machine-readable error code
        message: Human-readable error message
        details: Optional additional error details
        request_id: Optional request ID for tracing
    """

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(
        default=None, description="Optional additional error details"
    )
    request_id: str | None = Field(default=None, description="Request ID for tracing")


class HealthResponse(BaseModel):
    """Response model for GET /health endpoint.

    Attributes:
        status: Service health status
        environment: Application environment
        debug: Debug mode flag
        model: OpenAI model name
        temperature: Model temperature setting
        uptime_seconds: Service uptime in seconds
        config_status: Configuration sanity check status
    """

    status: str = Field(..., description="Service health status (healthy, degraded, unhealthy)")
    environment: str = Field(
        ..., description="Application environment (development, production, testing)"
    )
    debug: bool = Field(..., description="Debug mode flag")
    model: str = Field(..., description="OpenAI model name")
    temperature: float = Field(..., description="Model temperature setting")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    config_status: str = Field(..., description="Configuration sanity status (ok, warning, error)")
