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


class BlockingIssue(BaseModel):
    """A blocking issue identified during persona review.

    Attributes:
        text: The blocking issue description
        security_critical: Optional flag indicating if this is a security-critical issue
            that gives SecurityGuardian veto power
    """

    text: str = Field(
        ...,
        min_length=1,
        description="The blocking issue description",
    )
    security_critical: bool | None = Field(
        default=None,
        description="Whether this is a security-critical issue (SecurityGuardian veto power)",
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
                raise ValueError("Blocking issue text cannot be empty or whitespace-only")
        return v


class PersonaReview(BaseModel):
    """Review from a specific persona evaluating a proposal.

    This model captures a single persona's evaluation including strengths,
    concerns, recommendations, and risk assessments.

    Attributes:
        persona_name: Name of the reviewing persona (required)
        persona_id: Stable identifier for the persona (required, e.g., 'architect')
        confidence_score: Confidence in the proposal, range [0.0, 1.0] (required)
        strengths: List of identified strengths in the proposal (required)
        concerns: List of concerns with blocking flags (required)
        recommendations: List of actionable recommendations (required)
        blocking_issues: List of critical blocking issues with optional security flags
            (required, can be empty)
        estimated_effort: Effort estimation as string or structured data (required)
        dependency_risks: List of identified dependency risks (required, can be empty)
        internal_metadata: Optional metadata for tracking (e.g., model, duration)
    """

    persona_name: str = Field(
        ...,
        min_length=1,
        description="Name of the reviewing persona",
    )
    persona_id: str = Field(
        ...,
        min_length=1,
        description="Stable identifier for the persona (e.g., 'architect', 'security_guardian')",
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
    blocking_issues: list[BlockingIssue] = Field(
        ...,
        description=(
            "List of critical blocking issues with optional security_critical flags "
            "(can be empty)"
        ),
    )
    estimated_effort: str | dict[str, Any] = Field(
        ...,
        description="Effort estimation as string or structured data",
    )
    dependency_risks: list[str | dict[str, Any]] = Field(
        ...,
        description="List of identified dependency risks (can be empty)",
    )
    internal_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional internal metadata (e.g., model, duration, timestamps)",
    )

    @field_validator("persona_name", "persona_id", mode="before")
    @classmethod
    def trim_persona_fields(cls, v: Any) -> Any:
        """Trim whitespace from persona fields.

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
                raise ValueError("Persona field cannot be empty or whitespace-only")
        return v

    @field_validator("strengths", "recommendations", mode="before")
    @classmethod
    def validate_string_lists(cls, v: Any) -> Any:
        """Validate and trim string lists, ensuring non-empty strings.

        Args:
            v: The field value to validate

        Returns:
            List of trimmed, non-empty strings

        Raises:
            ValueError: If any list item is empty or whitespace-only after trimming
        """
        if isinstance(v, list):
            validated_list = []
            for item in v:
                if isinstance(item, str):
                    trimmed_item = item.strip()
                    if not trimmed_item:
                        raise ValueError("List items cannot be empty or whitespace-only")
                    validated_list.append(trimmed_item)
                else:
                    validated_list.append(item)
            return validated_list
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
            ValueError: If any string item is empty or whitespace-only after trimming
        """
        if isinstance(v, list):
            validated_list = []
            for item in v:
                if isinstance(item, str):
                    trimmed_item = item.strip()
                    if not trimmed_item:
                        raise ValueError("List items cannot be empty or whitespace-only")
                    validated_list.append(trimmed_item)
                else:
                    validated_list.append(item)  # Keep dicts as-is
            return validated_list
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
        persona_id: Stable identifier of the dissenting persona
        persona_name: Name of the dissenting persona
        confidence_score: The confidence score of the dissenting persona
        blocking_summary: Summary of blocking issues from dissenting persona
        mitigation_recommendation: Recommended mitigation for blocking issues
        strengths: Identified strengths from minority view (optional for backward compatibility)
        concerns: Concerns from minority view (optional for backward compatibility)
    """

    persona_id: str = Field(
        ...,
        min_length=1,
        description="Stable identifier of the dissenting persona",
    )
    persona_name: str = Field(
        ...,
        min_length=1,
        description="Name of the dissenting persona",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="The confidence score of the dissenting persona",
    )
    blocking_summary: str = Field(
        ...,
        min_length=1,
        description="Summary of blocking issues from dissenting persona",
    )
    mitigation_recommendation: str = Field(
        ...,
        min_length=1,
        description="Recommended mitigation for blocking issues",
    )
    strengths: list[str] | None = Field(
        default=None,
        description="Identified strengths from minority view (optional for backward compatibility)",
    )
    concerns: list[str] | None = Field(
        default=None,
        description="Concerns from minority view (optional for backward compatibility)",
    )

    @field_validator(
        "persona_id", "persona_name", "blocking_summary", "mitigation_recommendation", mode="before"
    )
    @classmethod
    def trim_string_fields(cls, v: Any) -> Any:
        """Trim whitespace from string fields.

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

    @field_validator("strengths", "concerns", mode="before")
    @classmethod
    def validate_string_lists(cls, v: Any) -> Any:
        """Validate and trim string lists.

        Args:
            v: The field value to validate

        Returns:
            List of trimmed, non-empty strings or None

        Raises:
            ValueError: If any list item is empty or whitespace-only after trimming
        """
        if v is None:
            return None
        if isinstance(v, list):
            validated_list = []
            for item in v:
                if isinstance(item, str):
                    trimmed_item = item.strip()
                    if not trimmed_item:
                        raise ValueError("List items cannot be empty or whitespace-only")
                    validated_list.append(trimmed_item)
                else:
                    validated_list.append(item)
            return validated_list
        return v


class PersonaScoreBreakdown(BaseModel):
    """Score breakdown for a single persona in decision aggregation.

    This is the legacy schema maintained for backward compatibility.
    New implementations should use DetailedScoreBreakdown.

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


class DetailedScoreBreakdown(BaseModel):
    """Detailed score breakdown for decision aggregation.

    Provides comprehensive scoring information including weights,
    individual scores, weighted contributions, and formula used.

    Attributes:
        weights: Dictionary mapping persona IDs to their weights
        individual_scores: Dictionary mapping persona IDs to their confidence scores
        weighted_contributions: Dictionary mapping persona IDs to their weighted contribution
        formula: Description of the aggregation formula used
    """

    weights: dict[str, float] = Field(
        ...,
        description="Dictionary mapping persona IDs to their weights",
    )
    individual_scores: dict[str, float] = Field(
        ...,
        description="Dictionary mapping persona IDs to their confidence scores",
    )
    weighted_contributions: dict[str, float] = Field(
        ...,
        description=(
            "Dictionary mapping persona IDs to their weighted contribution "
            "(weight * score)"
        ),
    )
    formula: str = Field(
        ...,
        min_length=1,
        description="Description of the aggregation formula used",
    )

    @field_validator("formula", mode="before")
    @classmethod
    def trim_formula(cls, v: Any) -> Any:
        """Trim whitespace from formula field.

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
                raise ValueError("Formula cannot be empty or whitespace-only")
        return v


class DecisionAggregation(BaseModel):
    """Aggregated decision from multiple persona reviews.

    This model encapsulates the consensus decision built from one or more
    persona reviews, including weighted confidence scoring and optional
    minority opinions.

    Attributes:
        overall_weighted_confidence: Weighted confidence score across all personas (legacy field)
        weighted_confidence: Weighted confidence score across all personas (new field)
        decision: Final decision outcome (approve/revise/reject)
        score_breakdown: Per-persona scoring details with weights and notes (legacy, optional)
        detailed_score_breakdown: Detailed scoring breakdown with formula (new field, optional)
        minority_report: Optional dissenting opinion from minority persona
            (supports multiple dissenters)
        minority_reports: Optional list of dissenting opinions from multiple personas (new field)
    """

    overall_weighted_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Weighted confidence score across all personas (legacy field)",
    )
    weighted_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Weighted confidence score across all personas (new field, mirrors "
            "overall_weighted_confidence)"
        ),
    )
    decision: DecisionEnum = Field(
        ...,
        description="Final decision outcome (approve/revise/reject)",
    )
    score_breakdown: dict[str, PersonaScoreBreakdown] | None = Field(
        default=None,
        description="Per-persona scoring details with weights and notes (legacy format)",
    )
    detailed_score_breakdown: DetailedScoreBreakdown | None = Field(
        default=None,
        description=(
            "Detailed score breakdown with weights, individual scores, "
            "contributions, and formula"
        ),
    )
    minority_report: MinorityReport | None = Field(
        default=None,
        description=(
            "Optional dissenting opinion from minority persona "
            "(single dissenter, legacy field)"
        ),
    )
    minority_reports: list[MinorityReport] | None = Field(
        default=None,
        description="Optional list of dissenting opinions from multiple personas (new field)",
    )
