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

import json
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


def validate_text_length(
    text: str | None,
    field_name: str,
    max_length: int,
    min_length: int = 1,
) -> None:
    """Validate text length against configured limits.

    Args:
        text: Text to validate (can be None)
        field_name: Name of the field for error messages
        max_length: Maximum allowed character length
        min_length: Minimum allowed character length (default: 1)

    Raises:
        ValueError: If text length violates the limits
    """
    if text is None:
        return

    text_len = len(text)
    if text_len < min_length:
        raise ValueError(
            f"{field_name} must be at least {min_length} characters (got {text_len})"
        )

    if text_len > max_length:
        raise ValueError(
            f"{field_name} exceeds maximum length of {max_length} characters "
            f"(got {text_len}). Please shorten your input."
        )


def validate_dict_json_size(
    data: dict[str, Any] | None,
    field_name: str,
    max_length: int,
) -> None:
    """Validate that a dict's JSON serialization is within size limits.

    Args:
        data: Dictionary to validate (can be None)
        field_name: Name of the field for error messages
        max_length: Maximum allowed character length for JSON serialization

    Raises:
        ValueError: If JSON size exceeds the limit
    """
    if data is None:
        return

    try:
        json_str = json.dumps(data)
        json_len = len(json_str)
        if json_len > max_length:
            raise ValueError(
                f"{field_name} JSON exceeds maximum size of {max_length} characters "
                f"(got {json_len}). Please reduce the data size."
            )
    except (TypeError, ValueError) as e:
        raise ValueError(f"{field_name} contains non-serializable data: {str(e)}") from e


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
    def validate_idea(cls, v: str) -> str:
        """Validate that idea is within length limits and contains 1-10 sentences.

        Args:
            v: The idea text to validate

        Returns:
            The validated idea text

        Raises:
            ValueError: If idea violates validation rules
        """
        # Validate sentence count
        sentence_count = count_sentences(v)

        if sentence_count < 1:
            raise ValueError("Idea must contain at least 1 sentence")

        if sentence_count > 10:
            raise ValueError(
                f"Idea must contain at most 10 sentences (found {sentence_count}). "
                "Please provide a more concise description."
            )

        # Validate length (default limit: 10000 chars, configurable via env)
        # Note: Actual limit will be enforced at the API route level with settings
        # This is a reasonable hard limit to prevent parsing issues
        max_length = 10000
        validate_text_length(v, "idea", max_length=max_length)

        return v

    @field_validator("extra_context")
    @classmethod
    def validate_extra_context(cls, v: dict[str, Any] | str | None) -> dict[str, Any] | str | None:
        """Validate that extra_context is within size limits.

        Args:
            v: The extra_context value to validate

        Returns:
            The validated extra_context value

        Raises:
            ValueError: If extra_context exceeds size limits
        """
        if v is None:
            return v

        # Validate based on type
        max_length = 50000  # Default limit, configurable via env at API level
        if isinstance(v, str):
            validate_text_length(v, "extra_context", max_length=max_length)
        elif isinstance(v, dict):
            validate_dict_json_size(v, "extra_context", max_length=max_length)

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
        schema_version: Schema version used for this response
        prompt_set_version: Prompt set version used for this response
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
    schema_version: str = Field(
        ..., description="Schema version used for this response (e.g., '1.0.0')"
    )
    prompt_set_version: str = Field(
        ..., description="Prompt set version used for this response (e.g., '1.0.0')"
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
    def validate_idea(cls, v: str) -> str:
        """Validate that idea is within length limits and contains 1-10 sentences.

        Args:
            v: The idea text to validate

        Returns:
            The validated idea text

        Raises:
            ValueError: If idea violates validation rules
        """
        # Validate sentence count
        sentence_count = count_sentences(v)

        if sentence_count < 1:
            raise ValueError("Idea must contain at least 1 sentence")

        if sentence_count > 10:
            raise ValueError(
                f"Idea must contain at most 10 sentences (found {sentence_count}). "
                "Please provide a more concise description."
            )

        # Validate length
        max_length = 10000
        validate_text_length(v, "idea", max_length=max_length)

        return v

    @field_validator("extra_context")
    @classmethod
    def validate_extra_context(cls, v: dict[str, Any] | str | None) -> dict[str, Any] | str | None:
        """Validate that extra_context is within size limits.

        Args:
            v: The extra_context value to validate

        Returns:
            The validated extra_context value

        Raises:
            ValueError: If extra_context exceeds size limits
        """
        if v is None:
            return v

        max_length = 50000
        if isinstance(v, str):
            validate_text_length(v, "extra_context", max_length=max_length)
        elif isinstance(v, dict):
            validate_dict_json_size(v, "extra_context", max_length=max_length)

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
    def validate_idea(cls, v: str) -> str:
        """Validate that idea is within length limits and contains 1-10 sentences.

        Args:
            v: The idea text to validate

        Returns:
            The validated idea text

        Raises:
            ValueError: If idea violates validation rules
        """
        # Validate sentence count
        sentence_count = count_sentences(v)

        if sentence_count < 1:
            raise ValueError("Idea must contain at least 1 sentence")

        if sentence_count > 10:
            raise ValueError(
                f"Idea must contain at most 10 sentences (found {sentence_count}). "
                "Please provide a more concise description."
            )

        # Validate length
        max_length = 10000
        validate_text_length(v, "idea", max_length=max_length)

        return v

    @field_validator("extra_context")
    @classmethod
    def validate_extra_context(cls, v: dict[str, Any] | str | None) -> dict[str, Any] | str | None:
        """Validate that extra_context is within size limits.

        Args:
            v: The extra_context value to validate

        Returns:
            The validated extra_context value

        Raises:
            ValueError: If extra_context exceeds size limits
        """
        if v is None:
            return v

        max_length = 50000
        if isinstance(v, str):
            validate_text_length(v, "extra_context", max_length=max_length)
        elif isinstance(v, dict):
            validate_dict_json_size(v, "extra_context", max_length=max_length)

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


class StepProgressSummary(BaseModel):
    """Summary of a step progress for run detail responses.

    Attributes:
        step_name: Canonical step name (e.g., 'expand', 'review_architect')
        step_order: Integer ordering for deterministic step sequence
        status: Current status of the step (pending, running, completed, failed)
        started_at: ISO timestamp when step processing started (null until started)
        completed_at: ISO timestamp when step finished (null until completed/failed)
        error_message: Optional error message if step failed
    """

    step_name: str = Field(..., description="Canonical step name")
    step_order: int = Field(..., description="Integer ordering for deterministic step sequence")
    status: str = Field(..., description="Current status: pending, running, completed, or failed")
    started_at: str | None = Field(
        default=None, description="ISO timestamp when step processing started"
    )
    completed_at: str | None = Field(
        default=None, description="ISO timestamp when step finished"
    )
    error_message: str | None = Field(
        default=None, description="Optional error message if step failed"
    )


class RunListItemResponse(BaseModel):
    """Response model for individual items in GET /v1/runs list.

    Attributes:
        run_id: UUID of the run
        created_at: Timestamp when run was created
        status: Current status of the run
        queued_at: Timestamp when run was queued
        started_at: Timestamp when run processing started
        completed_at: Timestamp when run finished
        retry_count: Number of retry attempts for this run
        run_type: Whether this is an initial run or revision
        priority: Priority level for run execution
        parent_run_id: Optional UUID of parent run for revisions
        overall_weighted_confidence: Final weighted confidence score
        decision_label: Final decision label
        proposal_title: Title from the proposal (truncated metadata)
        proposal_summary: Summary from the proposal (truncated metadata)
    """

    run_id: str = Field(..., description="UUID of the run")
    created_at: str = Field(..., description="ISO timestamp when run was created")
    status: str = Field(..., description="Current status: queued, running, completed, or failed")
    queued_at: str | None = Field(
        default=None, description="ISO timestamp when run was queued"
    )
    started_at: str | None = Field(
        default=None, description="ISO timestamp when run processing started"
    )
    completed_at: str | None = Field(
        default=None, description="ISO timestamp when run finished"
    )
    retry_count: int = Field(default=0, description="Number of retry attempts for this run")
    run_type: str = Field(..., description="Whether this is an initial run or revision")
    priority: str = Field(..., description="Priority level: normal or high")
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
        queued_at: Timestamp when run was queued
        started_at: Timestamp when run processing started
        completed_at: Timestamp when run finished
        retry_count: Number of retry attempts for this run
        run_type: Whether this is an initial run or revision
        priority: Priority level for run execution
        parent_run_id: Optional UUID of parent run for revisions
        input_idea: The original idea text
        extra_context: Optional additional context as JSON
        model: LLM model identifier used for this run
        temperature: Temperature parameter used for LLM calls
        parameters_json: Additional LLM parameters as JSON
        overall_weighted_confidence: Final weighted confidence score
        decision_label: Final decision label
        schema_version: Schema version used for this run's outputs
        prompt_set_version: Prompt set version used for this run
        proposal: Structured proposal JSON (nullable if run failed early)
        persona_reviews: Array of persona reviews with scores and blocking flags
        decision: Decision JSON (nullable if run failed or incomplete)
        step_progress: Array of step progress records showing pipeline execution
    """

    run_id: str = Field(..., description="UUID of the run")
    created_at: str = Field(..., description="ISO timestamp when run was created")
    updated_at: str = Field(..., description="ISO timestamp when run was last updated")
    status: str = Field(..., description="Current status: queued, running, completed, or failed")
    queued_at: str | None = Field(
        default=None, description="ISO timestamp when run was queued"
    )
    started_at: str | None = Field(
        default=None, description="ISO timestamp when run processing started"
    )
    completed_at: str | None = Field(
        default=None, description="ISO timestamp when run finished"
    )
    retry_count: int = Field(default=0, description="Number of retry attempts for this run")
    run_type: str = Field(..., description="Whether this is an initial run or revision")
    priority: str = Field(..., description="Priority level: normal or high")
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
    schema_version: str = Field(
        ..., description="Schema version used for this run's outputs (e.g., '1.0.0')"
    )
    prompt_set_version: str = Field(
        ..., description="Prompt set version used for this run (e.g., '1.0.0')"
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
    step_progress: list[StepProgressSummary] = Field(
        default_factory=list,
        description="Array of step progress records showing pipeline execution ordered by step_order",
    )


class CreateRevisionRequest(BaseModel):
    """Request model for POST /v1/runs/{run_id}/revisions endpoint.

    Attributes:
        edited_proposal: Full structured proposal object or text edits to apply
        edit_notes: Optional notes about what was edited and why
        input_idea: Optional new input idea text (overrides parent if provided)
        extra_context: Optional new additional context (overrides parent if provided)
        model: Optional new LLM model identifier (overrides parent if provided)
        temperature: Optional new temperature parameter (overrides parent if provided)
        parameters_json: Optional new LLM parameters (overrides parent if provided)
    """

    edited_proposal: dict[str, Any] | str | None = Field(
        default=None,
        description=(
            "Edited proposal as structured JSON object or free-form text to merge with parent. "
            "If omitted, edit_notes is used to guide re-expansion."
        ),
        examples=[
            {"problem_statement": "Updated problem", "proposed_solution": "New approach"},
            "Revise the security section to use OAuth 2.0 instead of basic auth",
        ],
    )
    edit_notes: str | None = Field(
        default=None,
        min_length=1,
        description="Optional notes about edits or guidance for re-expansion",
        examples=["Added security requirements based on SecurityGuardian feedback"],
    )
    input_idea: str | None = Field(
        default=None,
        min_length=1,
        description="Optional new input idea text (overrides parent)",
    )
    extra_context: dict[str, Any] | str | None = Field(
        default=None,
        description="Optional new additional context (overrides parent)",
    )
    model: str | None = Field(
        default=None,
        min_length=1,
        description="Optional new LLM model identifier (overrides parent)",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Optional new temperature parameter (overrides parent)",
    )
    parameters_json: dict[str, Any] | None = Field(
        default=None,
        description="Optional new LLM parameters (overrides parent)",
    )

    @field_validator("edited_proposal")
    @classmethod
    def validate_edited_proposal(cls, v: dict[str, Any] | str | None) -> dict[str, Any] | str | None:
        """Validate that edited_proposal is within size limits.

        Args:
            v: The edited_proposal value to validate

        Returns:
            The validated edited_proposal value

        Raises:
            ValueError: If edited_proposal exceeds size limits
        """
        if v is None:
            return v

        max_length = 100000  # Default limit, configurable via env at API level
        if isinstance(v, str):
            validate_text_length(v, "edited_proposal", max_length=max_length)
        elif isinstance(v, dict):
            validate_dict_json_size(v, "edited_proposal", max_length=max_length)

        return v

    @field_validator("edit_notes")
    @classmethod
    def validate_edit_notes(cls, v: str | None) -> str | None:
        """Validate that edit_notes is within size limits.

        Args:
            v: The edit_notes value to validate

        Returns:
            The validated edit_notes value

        Raises:
            ValueError: If edit_notes exceeds size limits
        """
        if v is None:
            return v

        max_length = 10000  # Default limit, configurable via env at API level
        validate_text_length(v, "edit_notes", max_length=max_length)

        return v

    @field_validator("input_idea")
    @classmethod
    def validate_input_idea(cls, v: str | None) -> str | None:
        """Validate that input_idea is within size limits.

        Args:
            v: The input_idea value to validate

        Returns:
            The validated input_idea value

        Raises:
            ValueError: If input_idea exceeds size limits
        """
        if v is None:
            return v

        max_length = 10000  # Default limit, configurable via env at API level
        validate_text_length(v, "input_idea", max_length=max_length)

        return v

    @field_validator("extra_context")
    @classmethod
    def validate_extra_context(cls, v: dict[str, Any] | str | None) -> dict[str, Any] | str | None:
        """Validate that extra_context is within size limits.

        Args:
            v: The extra_context value to validate

        Returns:
            The validated extra_context value

        Raises:
            ValueError: If extra_context exceeds size limits
        """
        if v is None:
            return v

        max_length = 50000
        if isinstance(v, str):
            validate_text_length(v, "extra_context", max_length=max_length)
        elif isinstance(v, dict):
            validate_dict_json_size(v, "extra_context", max_length=max_length)

        return v

    @field_validator("edited_proposal", "edit_notes")
    @classmethod
    def require_at_least_one_edit_field(cls, v: Any, info: Any) -> Any:
        """Validate that at least one of edited_proposal or edit_notes is provided.

        Args:
            v: Field value
            info: Field info with context

        Returns:
            The validated field value

        Note:
            This validator runs per-field. Use the class-level validation in the
            endpoint to ensure at least one edit field is provided.
        """
        return v


class CreateRevisionResponse(BaseModel):
    """Response model for POST /v1/runs/{run_id}/revisions endpoint.

    Attributes:
        run_id: UUID of the newly created revision run
        parent_run_id: UUID of the parent run
        status: Current status of the revision run
        created_at: Timestamp when revision run was created
        personas_rerun: List of persona IDs that were re-executed
        personas_reused: List of persona IDs whose reviews were reused from parent
        message: Human-readable message about the revision
    """

    run_id: str = Field(..., description="UUID of the newly created revision run")
    parent_run_id: str = Field(..., description="UUID of the parent run")
    status: str = Field(..., description="Current status: running, completed, or failed")
    created_at: str = Field(..., description="ISO timestamp when revision run was created")
    personas_rerun: list[str] = Field(
        default_factory=list,
        description="List of persona IDs that were re-executed",
    )
    personas_reused: list[str] = Field(
        default_factory=list,
        description="List of persona IDs whose reviews were reused from parent",
    )
    message: str = Field(
        ...,
        description="Human-readable message about the revision",
    )


class RunDiffResponse(BaseModel):
    """Response model for GET /v1/runs/{run_id}/diff/{other_run_id} endpoint.

    Attributes:
        metadata: Metadata about the two runs and their relationship
        proposal_changes: Per-section diffs of proposal text
        persona_deltas: Changes in persona confidence scores and blocking flags
        decision_delta: Changes in overall weighted confidence and decision label
    """

    metadata: dict[str, Any] = Field(
        ...,
        description=(
            "Metadata including run IDs, timestamps, and parent/child relationship status"
        ),
    )
    proposal_changes: dict[str, Any] = Field(
        ...,
        description=(
            "Per-section proposal diffs with status (unchanged/modified/added/removed) "
            "and unified diff output for modified sections"
        ),
    )
    persona_deltas: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "List of persona score deltas with old/new confidence, blocking issues changes, "
            "and security concerns changes"
        ),
    )
    decision_delta: dict[str, Any] = Field(
        ...,
        description=(
            "Overall decision comparison including confidence delta and decision label changes"
        ),
    )


class JobEnqueuedResponse(BaseModel):
    """Response model for job enqueueing endpoints (POST /v1/full-review, POST /v1/runs/{run_id}/revisions).

    This response is returned immediately after a run is created and a job is enqueued
    to Pub/Sub. Clients can poll GET /v1/runs/{run_id} to check status and retrieve
    results once processing completes.

    Attributes:
        run_id: UUID of the created run
        status: Current status of the run ('queued')
        run_type: Type of run ('initial' or 'revision')
        priority: Priority level ('normal' or 'high')
        created_at: ISO timestamp when run was created
        queued_at: ISO timestamp when run was enqueued
        message: Human-readable message about the enqueued job
    """

    run_id: str = Field(..., description="UUID of the created run")
    status: str = Field(..., description="Current status: 'queued'")
    run_type: str = Field(..., description="Type of run: 'initial' or 'revision'")
    priority: str = Field(..., description="Priority level: 'normal' or 'high'")
    created_at: str = Field(..., description="ISO timestamp when run was created")
    queued_at: str = Field(..., description="ISO timestamp when run was enqueued")
    message: str = Field(
        ...,
        description="Human-readable message about the enqueued job",
    )
