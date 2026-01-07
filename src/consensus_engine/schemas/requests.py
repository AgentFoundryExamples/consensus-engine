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

# Import schemas for use in response models
from consensus_engine.schemas.review import DecisionAggregation, PersonaReview


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


class ReviewIdeaRequest(BaseModel):
    """Request model for POST /v1/review-idea endpoint.

    Attributes:
        idea: The core idea to expand and review (1-10 sentences)
        extra_context: Optional additional context as dict or string
    """

    idea: str = Field(
        ...,
        min_length=1,
        description="The core idea or problem to expand and review (1-10 sentences)",
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


class ReviewIdeaResponse(BaseModel):
    """Response model for POST /v1/review-idea endpoint.

    Attributes:
        expanded_proposal: The expanded proposal data
        reviews: List of PersonaReview objects (exactly one for single-persona review)
        draft_decision: Aggregated decision with weighted confidence and breakdown
        run_id: Unique identifier for this orchestration run
        elapsed_time: Total wall time for the entire orchestration in seconds
    """

    expanded_proposal: ExpandIdeaResponse = Field(
        ..., description="The expanded proposal with problem statement, solution, etc."
    )
    reviews: list[PersonaReview] = Field(
        ..., description="List of persona reviews (exactly one for GenericReviewer)"
    )
    draft_decision: DecisionAggregation = Field(
        ..., description="Aggregated decision with weighted confidence and score breakdown"
    )
    run_id: str = Field(..., description="Unique identifier for this orchestration run")
    elapsed_time: float = Field(
        ..., description="Total wall time for the entire orchestration in seconds"
    )


class ReviewIdeaErrorResponse(BaseModel):
    """Error response model for POST /v1/review-idea endpoint.

    This structured error response includes information about which step failed,
    a human-readable message, and any partial results that were successfully
    computed before the failure.

    Attributes:
        code: Machine-readable error code
        message: Human-readable error message
        failed_step: Which step failed ('expand' or 'review')
        run_id: Unique identifier for this orchestration run
        partial_results: Optional partial results (e.g., expanded proposal if review failed)
        details: Optional additional error details
    """

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    failed_step: str = Field(
        ..., description="Which step failed: 'expand' or 'review' or 'validation'"
    )
    run_id: str = Field(..., description="Unique identifier for this orchestration run")
    partial_results: dict[str, Any] | None = Field(
        default=None,
        description="Optional partial results (e.g., expanded_proposal if review failed)",
    )
    details: dict[str, Any] | None = Field(
        default=None, description="Optional additional error details"
    )


class FullReviewRequest(BaseModel):
    """Request model for POST /v1/full-review endpoint.

    Attributes:
        idea: The core idea to expand and review (1-10 sentences)
        extra_context: Optional additional context as dict or string
    """

    idea: str = Field(
        ...,
        min_length=1,
        description=(
            "The core idea or problem to expand and review with all personas (1-10 sentences)"
        ),
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


class FullReviewResponse(BaseModel):
    """Response model for POST /v1/full-review endpoint.

    Attributes:
        expanded_proposal: The expanded proposal data
        persona_reviews: List of PersonaReview objects (exactly five for all personas)
        decision: Aggregated decision with weighted confidence and breakdown
        run_id: Unique identifier for this orchestration run
        elapsed_time: Total wall time for the entire orchestration in seconds
    """

    expanded_proposal: ExpandIdeaResponse = Field(
        ..., description="The expanded proposal with problem statement, solution, etc."
    )
    persona_reviews: list[PersonaReview] = Field(
        ..., description="List of all five persona reviews in configuration order"
    )
    decision: DecisionAggregation = Field(
        ..., description="Aggregated decision with weighted confidence and detailed breakdown"
    )
    run_id: str = Field(..., description="Unique identifier for this orchestration run")
    elapsed_time: float = Field(
        ..., description="Total wall time for the entire orchestration in seconds"
    )


class FullReviewErrorResponse(BaseModel):
    """Error response model for POST /v1/full-review endpoint.

    This structured error response includes information about which step failed,
    a human-readable message, and any partial results that were successfully
    computed before the failure.

    Attributes:
        code: Machine-readable error code
        message: Human-readable error message
        failed_step: Which step failed ('expand', 'review', or 'aggregate')
        run_id: Unique identifier for this orchestration run
        partial_results: Optional partial results (e.g., expanded proposal if review failed)
        details: Optional additional error details
    """

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    failed_step: str = Field(
        ..., description="Which step failed: 'expand', 'review', or 'aggregate'"
    )
    run_id: str = Field(..., description="Unique identifier for this orchestration run")
    partial_results: dict[str, Any] | None = Field(
        default=None,
        description="Optional partial results (e.g., expanded_proposal if review failed)",
    )
    details: dict[str, Any] | None = Field(
        default=None, description="Optional additional error details"
    )


class PersonaReviewSummary(BaseModel):
    """Summary of a persona review for run list/detail responses.
    
    Attributes:
        persona_id: Stable identifier for the persona
        persona_name: Display name for the persona
        confidence_score: Numeric confidence score [0.0, 1.0]
        blocking_issues_present: Boolean flag indicating presence of blocking issues
        prompt_parameters_json: Prompt parameters used for this review
    """
    
    persona_id: str = Field(..., description="Stable identifier for the persona")
    persona_name: str = Field(..., description="Display name for the persona")
    confidence_score: float = Field(..., description="Numeric confidence score [0.0, 1.0]")
    blocking_issues_present: bool = Field(
        ..., description="Boolean flag indicating presence of blocking issues"
    )
    prompt_parameters_json: dict[str, Any] = Field(
        ..., description="Prompt parameters (model, temperature, persona version, retries)"
    )


class RunListItemResponse(BaseModel):
    """Response model for individual items in GET /v1/runs list.
    
    Attributes:
        run_id: UUID of the run
        created_at: Timestamp when run was created
        status: Current status of the run
        run_type: Whether this is an initial run or revision
        parent_run_id: Optional UUID of parent run for revisions
        overall_weighted_confidence: Final weighted confidence score
        decision_label: Final decision label
        proposal_title: Title from the proposal (truncated metadata)
        proposal_summary: Summary from the proposal (truncated metadata)
    """
    
    run_id: str = Field(..., description="UUID of the run")
    created_at: str = Field(..., description="ISO timestamp when run was created")
    status: str = Field(..., description="Current status: running, completed, or failed")
    run_type: str = Field(..., description="Whether this is an initial run or revision")
    parent_run_id: str | None = Field(
        default=None, description="Optional UUID of parent run for revisions"
    )
    overall_weighted_confidence: float | None = Field(
        default=None, description="Final weighted confidence score (null until decision)"
    )
    decision_label: str | None = Field(
        default=None, description="Final decision label (null until decision)"
    )
    proposal_title: str | None = Field(
        default=None, description="Title from the proposal (truncated)"
    )
    proposal_summary: str | None = Field(
        default=None, description="Summary from the proposal (truncated)"
    )


class RunListResponse(BaseModel):
    """Response model for GET /v1/runs endpoint.
    
    Attributes:
        runs: List of run items
        total: Total number of runs matching filters
        limit: Number of items per page
        offset: Current offset
    """
    
    runs: list[RunListItemResponse] = Field(..., description="List of run items")
    total: int = Field(..., description="Total number of runs matching filters")
    limit: int = Field(..., description="Number of items per page")
    offset: int = Field(..., description="Current offset")


class RunDetailResponse(BaseModel):
    """Response model for GET /v1/runs/{run_id} endpoint.
    
    Attributes:
        run_id: UUID of the run
        created_at: Timestamp when run was created
        updated_at: Timestamp when run was last updated
        status: Current status of the run
        run_type: Whether this is an initial run or revision
        parent_run_id: Optional UUID of parent run for revisions
        input_idea: The original idea text
        extra_context: Optional additional context as JSON
        model: LLM model identifier used for this run
        temperature: Temperature parameter used for LLM calls
        parameters_json: Additional LLM parameters as JSON
        overall_weighted_confidence: Final weighted confidence score
        decision_label: Final decision label
        proposal: Structured proposal JSON (nullable if run failed early)
        persona_reviews: Array of persona reviews with scores and blocking flags
        decision: Decision JSON (nullable if run failed or incomplete)
    """
    
    run_id: str = Field(..., description="UUID of the run")
    created_at: str = Field(..., description="ISO timestamp when run was created")
    updated_at: str = Field(..., description="ISO timestamp when run was last updated")
    status: str = Field(..., description="Current status: running, completed, or failed")
    run_type: str = Field(..., description="Whether this is an initial run or revision")
    parent_run_id: str | None = Field(
        default=None, description="Optional UUID of parent run for revisions"
    )
    input_idea: str = Field(..., description="The original idea text")
    extra_context: dict[str, Any] | None = Field(
        default=None, description="Optional additional context as JSON"
    )
    model: str = Field(..., description="LLM model identifier used for this run")
    temperature: float = Field(..., description="Temperature parameter used for LLM calls")
    parameters_json: dict[str, Any] = Field(
        ..., description="Additional LLM parameters as JSON"
    )
    overall_weighted_confidence: float | None = Field(
        default=None, description="Final weighted confidence score (null until decision)"
    )
    decision_label: str | None = Field(
        default=None, description="Final decision label (null until decision)"
    )
    proposal: dict[str, Any] | None = Field(
        default=None, description="Structured proposal JSON (null if run failed early)"
    )
    persona_reviews: list[PersonaReviewSummary] = Field(
        default_factory=list,
        description="Array of persona reviews with scores and blocking flags",
    )
    decision: dict[str, Any] | None = Field(
        default=None, description="Decision JSON (null if run failed or incomplete)"
    )
