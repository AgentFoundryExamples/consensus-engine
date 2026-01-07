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
"""Pydantic models for proposal schemas.

This module defines the data models for proposal expansion, including
input payloads and structured output from the LLM service.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class IdeaInput(BaseModel):
    """Input payload for expanding an idea into a full proposal.

    Attributes:
        idea: The core idea or problem to expand into a detailed proposal
        extra_context: Optional additional context or constraints to consider
    """

    idea: str = Field(
        ...,
        min_length=1,
        description="The core idea or problem to expand into a detailed proposal",
    )
    extra_context: str | None = Field(
        default=None,
        description="Optional additional context or constraints to consider",
    )


class ExpandedProposal(BaseModel):
    """Structured output from the LLM expansion service.

    This model defines the expected structure when using OpenAI's Structured Outputs
    to ensure validated JSON-only responses.

    Attributes:
        problem_statement: Clear articulation of the problem to be solved (required, trimmed)
        proposed_solution: Detailed description of the proposed solution approach (required, trimmed)
        assumptions: List of underlying assumptions made in the proposal (required, non-empty strings)
        scope_non_goals: List of what is explicitly out of scope or non-goals (required, non-empty strings)
        title: Optional short title for the proposal
        summary: Optional brief summary of the proposal
        raw_idea: Optional original idea text before expansion
        metadata: Optional metadata dictionary for tracking and processing
        raw_expanded_proposal: Optional complete expanded proposal text or additional notes
    """

    problem_statement: str = Field(
        ...,
        min_length=1,
        description="Clear articulation of the problem to be solved",
    )
    proposed_solution: str = Field(
        ...,
        min_length=1,
        description="Detailed description of the proposed solution approach",
    )
    assumptions: list[str] = Field(
        ...,
        description="List of underlying assumptions made in the proposal",
    )
    scope_non_goals: list[str] = Field(
        ...,
        description="List of what is explicitly out of scope or non-goals",
    )
    title: str | None = Field(
        default=None,
        description="Optional short title for the proposal",
    )
    summary: str | None = Field(
        default=None,
        description="Optional brief summary of the proposal",
    )
    raw_idea: str | None = Field(
        default=None,
        description="Optional original idea text before expansion",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional metadata dictionary for tracking and processing",
    )
    raw_expanded_proposal: str | None = Field(
        default=None,
        description=(
            "Optional field for storing the complete expanded proposal text in narrative form "
            "or additional notes that don't fit into the structured fields above. "
            "This field allows the LLM to provide supplementary information beyond the "
            "structured problem_statement, proposed_solution, assumptions, and scope_non_goals."
        ),
    )

    @field_validator("problem_statement", "proposed_solution", mode="before")
    @classmethod
    def trim_required_strings(cls, v: Any) -> Any:
        """Trim whitespace from required string fields and validate non-empty.

        Args:
            v: The field value to validate

        Returns:
            The trimmed string value

        Raises:
            ValueError: If the trimmed string is empty
        """
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Field cannot be empty or whitespace-only")
        return v

    @field_validator("title", "summary", "raw_idea", "raw_expanded_proposal", mode="before")
    @classmethod
    def trim_optional_strings(cls, v: Any) -> Any:
        """Trim whitespace from optional string fields.

        Args:
            v: The field value to validate

        Returns:
            The trimmed string value or None if empty

        Raises:
            None
        """
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("assumptions", "scope_non_goals", mode="before")
    @classmethod
    def validate_string_lists(cls, v: Any) -> Any:
        """Validate and trim string lists, ensuring non-empty strings.

        Args:
            v: The field value to validate

        Returns:
            List of trimmed, non-empty strings

        Raises:
            ValueError: If any list item is empty after trimming
        """
        if isinstance(v, list):
            trimmed = []
            for item in v:
                if isinstance(item, str):
                    trimmed_item = item.strip()
                    if not trimmed_item:
                        raise ValueError("List items cannot be empty or whitespace-only")
                    trimmed.append(trimmed_item)
                else:
                    trimmed.append(item)
            return trimmed
        return v
