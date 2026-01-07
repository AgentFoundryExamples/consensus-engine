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
"""Pydantic models for persona review and decision aggregation schemas.

This module defines the data models for persona reviews and decision aggregation,
including structured outputs for multi-persona consensus building.
"""

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class Concern(BaseModel):
    """A concern raised during a persona review.

    Attributes:
        text: The concern description
        is_blocking: Whether this concern is a blocking issue
    """

    text: str = Field(
        ...,
        min_length=1,
        description="The concern description",
    )
    is_blocking: bool = Field(
        ...,
        description="Whether this concern is a blocking issue",
    )

    @field_validator("text", mode="before")
    @classmethod
    def trim_text(cls, v: Any) -> Any:
        """Trim whitespace from text field.

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
                raise ValueError("Concern text cannot be empty or whitespace-only")
        return v


class PersonaReview(BaseModel):
    """Review from a specific persona evaluating a proposal.

    This model captures a single persona's evaluation including strengths,
    concerns, recommendations, and risk assessments.

    Attributes:
        persona_name: Name of the reviewing persona (required)
        persona_id: Optional UUID for tracking persona identity
        confidence_score: Confidence in the proposal, range [0.0, 1.0] (required)
        strengths: List of identified strengths in the proposal (required)
        concerns: List of concerns with blocking flags (required)
        recommendations: List of actionable recommendations (required)
        blocking_issues: List of critical blocking issues (required, can be empty)
        estimated_effort: Effort estimation as string or structured data (required)
        dependency_risks: List of identified dependency risks (required, can be empty)
    """

    persona_name: str = Field(
        ...,
        min_length=1,
        description="Name of the reviewing persona",
    )
    persona_id: UUID | None = Field(
        default=None,
        description="Optional UUID for tracking persona identity",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in the proposal, range [0.0, 1.0]",
    )
    strengths: list[str] = Field(
        ...,
        description="List of identified strengths in the proposal",
    )
    concerns: list[Concern] = Field(
        ...,
        description="List of concerns with blocking flags",
    )
    recommendations: list[str] = Field(
        ...,
        description="List of actionable recommendations",
    )
    blocking_issues: list[str] = Field(
        ...,
        description="List of critical blocking issues (can be empty)",
    )
    estimated_effort: str | dict[str, Any] = Field(
        ...,
        description="Effort estimation as string or structured data",
    )
    dependency_risks: list[str | dict[str, Any]] = Field(
        ...,
        description="List of identified dependency risks (can be empty)",
    )

    @field_validator("persona_name", mode="before")
    @classmethod
    def trim_persona_name(cls, v: Any) -> Any:
        """Trim whitespace from persona_name.

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
                raise ValueError("Persona name cannot be empty or whitespace-only")
        return v

    @field_validator("strengths", "recommendations", "blocking_issues", mode="before")
    @classmethod
    def validate_string_lists(cls, v: Any) -> Any:
        """Validate and trim string lists, ensuring non-empty strings when present.

        Args:
            v: The field value to validate

        Returns:
            List of trimmed, non-empty strings

        Raises:
            ValueError: If any list item is whitespace-only after trimming
        """
        if isinstance(v, list):
            trimmed = []
            for item in v:
                if isinstance(item, str):
                    trimmed_item = item.strip()
                    if not trimmed_item:  # Empty after trim
                        raise ValueError("List items cannot be whitespace-only")
                    trimmed.append(trimmed_item)
                else:
                    trimmed.append(item)
            return trimmed
        return v

    @field_validator("dependency_risks", mode="before")
    @classmethod
    def validate_dependency_risks(cls, v: Any) -> Any:
        """Validate and trim dependency_risks, handling both strings and dicts.

        Args:
            v: The field value to validate

        Returns:
            List of trimmed strings and/or dicts

        Raises:
            None - allows empty items to be filtered
        """
        if isinstance(v, list):
            trimmed = []
            for item in v:
                if isinstance(item, str):
                    trimmed_item = item.strip()
                    if trimmed_item:  # Only add non-empty strings
                        trimmed.append(trimmed_item)
                else:
                    trimmed.append(item)  # Keep dicts as-is
            return trimmed
        return v

    @field_validator("estimated_effort", mode="before")
    @classmethod
    def validate_effort(cls, v: Any) -> Any:
        """Validate and trim effort estimation string.

        Args:
            v: The field value to validate

        Returns:
            The trimmed string or dict value

        Raises:
            ValueError: If string effort is empty after trimming
        """
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Effort estimation cannot be empty or whitespace-only")
        return v


class DecisionEnum(str, Enum):
    """Enumeration of possible decision outcomes."""

    APPROVE = "approve"
    REVISE = "revise"
    REJECT = "reject"


class MinorityReport(BaseModel):
    """Minority opinion in a decision aggregation.

    Attributes:
        persona_name: Name of the dissenting persona
        strengths: Identified strengths from minority view
        concerns: Concerns from minority view
    """

    persona_name: str = Field(
        ...,
        min_length=1,
        description="Name of the dissenting persona",
    )
    strengths: list[str] = Field(
        ...,
        description="Identified strengths from minority view",
    )
    concerns: list[str] = Field(
        ...,
        description="Concerns from minority view",
    )

    @field_validator("persona_name", mode="before")
    @classmethod
    def trim_persona_name(cls, v: Any) -> Any:
        """Trim whitespace from persona_name.

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
                raise ValueError("Persona name cannot be empty or whitespace-only")
        return v

    @field_validator("strengths", "concerns", mode="before")
    @classmethod
    def validate_string_lists(cls, v: Any) -> Any:
        """Validate and trim string lists.

        Args:
            v: The field value to validate

        Returns:
            List of trimmed, non-empty strings

        Raises:
            ValueError: If any non-empty list item is whitespace-only after trimming
        """
        if isinstance(v, list):
            trimmed = []
            for item in v:
                if isinstance(item, str):
                    trimmed_item = item.strip()
                    if trimmed_item:
                        trimmed.append(trimmed_item)
                    elif item:
                        raise ValueError("List items cannot be whitespace-only")
                else:
                    trimmed.append(item)
            return trimmed
        return v


class PersonaScoreBreakdown(BaseModel):
    """Score breakdown for a single persona in decision aggregation.

    Attributes:
        weight: Weight assigned to this persona's review
        notes: Optional notes about this persona's contribution
    """

    weight: float = Field(
        ...,
        ge=0.0,
        description="Weight assigned to this persona's review",
    )
    notes: str | None = Field(
        default=None,
        description="Optional notes about this persona's contribution",
    )

    @field_validator("notes", mode="before")
    @classmethod
    def trim_notes(cls, v: Any) -> Any:
        """Trim whitespace from notes field.

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


class DecisionAggregation(BaseModel):
    """Aggregated decision from multiple persona reviews.

    This model encapsulates the consensus decision built from one or more
    persona reviews, including weighted confidence scoring and optional
    minority opinions.

    Attributes:
        overall_weighted_confidence: Weighted confidence score across all personas
        decision: Final decision outcome (approve/revise/reject)
        score_breakdown: Per-persona scoring details with weights and notes
        minority_report: Optional dissenting opinion from minority persona
    """

    overall_weighted_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Weighted confidence score across all personas",
    )
    decision: DecisionEnum = Field(
        ...,
        description="Final decision outcome (approve/revise/reject)",
    )
    score_breakdown: dict[str, PersonaScoreBreakdown] = Field(
        ...,
        description="Per-persona scoring details with weights and notes",
    )
    minority_report: MinorityReport | None = Field(
        default=None,
        description="Optional dissenting opinion from minority persona",
    )
