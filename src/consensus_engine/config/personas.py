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
"""Centralized persona configuration for multi-persona consensus building.

This module defines the persona templates, weights, and thresholds used
in the multi-persona pipeline for deterministic consensus aggregation.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class PersonaConfig(BaseModel):
    """Configuration for a single persona.

    Attributes:
        id: Unique stable identifier for the persona (e.g., 'architect')
        display_name: Human-readable name (e.g., 'Architect')
        developer_instructions: Instructions for developers about persona's role
        system_prompt: Reusable system prompt for LLM calls
        default_weight: Default weight in consensus aggregation (0.0-1.0)
        temperature: Temperature setting for LLM calls (0.0-1.0)
    """

    id: str = Field(
        ...,
        min_length=1,
        description="Unique stable identifier for the persona",
    )
    display_name: str = Field(
        ...,
        min_length=1,
        description="Human-readable name for the persona",
    )
    developer_instructions: str = Field(
        ...,
        min_length=1,
        description="Instructions for developers about persona's role and focus",
    )
    system_prompt: str = Field(
        ...,
        min_length=1,
        description="Reusable system prompt for LLM calls",
    )
    default_weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Default weight in consensus aggregation",
    )
    temperature: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Temperature setting for LLM calls",
    )

    @field_validator("id", "display_name", "developer_instructions", "system_prompt")
    @classmethod
    def trim_strings(cls, v: str) -> str:
        """Trim whitespace from string fields and validate non-empty.

        Args:
            v: The field value to validate

        Returns:
            The trimmed string value

        Raises:
            ValueError: If the trimmed string is empty
        """
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace-only")
        return v


# Shared low temperature for deterministic persona reviews
PERSONA_TEMPERATURE = 0.2

# Decision threshold constants
APPROVE_THRESHOLD = 0.80
REVISE_THRESHOLD = 0.60

# Persona definitions with stable IDs, display names, instructions, and weights
PERSONAS: dict[str, PersonaConfig] = {
    "architect": PersonaConfig(
        id="architect",
        display_name="Architect",
        developer_instructions=(
            "The Architect persona focuses on system design, scalability, "
            "maintainability, and technical architecture. Evaluates proposals "
            "for architectural soundness, design patterns, and long-term viability."
        ),
        system_prompt=(
            "You are an experienced software architect reviewing technical proposals. "
            "Focus on system design, scalability, maintainability, architectural patterns, "
            "and long-term technical viability. Identify design flaws, scalability concerns, "
            "and suggest architectural improvements. Provide detailed technical feedback "
            "on the proposed solution's structure and design."
        ),
        default_weight=0.25,
        temperature=PERSONA_TEMPERATURE,
    ),
    "critic": PersonaConfig(
        id="critic",
        display_name="Critic",
        developer_instructions=(
            "The Critic persona identifies risks, edge cases, potential failures, "
            "and implementation challenges. Provides skeptical analysis to ensure "
            "thorough consideration of downsides and failure modes."
        ),
        system_prompt=(
            "You are a critical technical reviewer who identifies risks, edge cases, "
            "and potential failures. Your role is to be constructively skeptical, "
            "questioning assumptions, identifying gaps, and highlighting implementation "
            "challenges. Focus on what could go wrong, edge cases that might be missed, "
            "and risks that need mitigation. Provide thorough analysis of potential pitfalls."
        ),
        default_weight=0.25,
        temperature=PERSONA_TEMPERATURE,
    ),
    "optimist": PersonaConfig(
        id="optimist",
        display_name="Optimist",
        developer_instructions=(
            "The Optimist persona identifies strengths, opportunities, and positive "
            "aspects of proposals. Balances critical feedback with recognition of "
            "good ideas and feasible approaches."
        ),
        system_prompt=(
            "You are an encouraging technical reviewer who identifies strengths, "
            "opportunities, and positive aspects of proposals. While maintaining "
            "technical rigor, you focus on what works well, feasible approaches, "
            "and potential for success. Highlight good ideas, sound reasoning, and "
            "practical implementations. Balance constructive feedback with recognition "
            "of merit and opportunity."
        ),
        default_weight=0.15,
        temperature=PERSONA_TEMPERATURE,
    ),
    "security_guardian": PersonaConfig(
        id="security_guardian",
        display_name="SecurityGuardian",
        developer_instructions=(
            "The SecurityGuardian persona focuses on security vulnerabilities, "
            "data protection, authentication, authorization, and compliance. "
            "Has veto power through security_critical blocking issues."
        ),
        system_prompt=(
            "You are a security expert reviewing technical proposals. Focus on security "
            "vulnerabilities, data protection, authentication, authorization, encryption, "
            "input validation, and compliance requirements. Identify security risks and "
            "recommend security best practices. Mark critical security issues as blocking "
            "with the security_critical flag to exercise veto power. Be thorough in "
            "evaluating security implications."
        ),
        default_weight=0.20,
        temperature=PERSONA_TEMPERATURE,
    ),
    "user_advocate": PersonaConfig(
        id="user_advocate",
        display_name="UserAdvocate",
        developer_instructions=(
            "The UserAdvocate persona evaluates proposals from the user's perspective, "
            "focusing on usability, user experience, accessibility, and value delivery. "
            "Ensures solutions meet user needs effectively."
        ),
        system_prompt=(
            "You are a user experience advocate reviewing technical proposals. Focus on "
            "usability, user experience, accessibility, user value, and practical utility. "
            "Evaluate whether the solution effectively meets user needs, is intuitive to use, "
            "and delivers clear value. Identify UX issues, accessibility concerns, and "
            "opportunities to improve user satisfaction. Advocate for user-centric design."
        ),
        default_weight=0.15,
        temperature=PERSONA_TEMPERATURE,
    ),
}


def validate_persona_weights() -> None:
    """Validate that persona weights sum to 1.0.

    Raises:
        ValueError: If weights don't sum to 1.0 within tolerance
    """
    total_weight = sum(persona.default_weight for persona in PERSONAS.values())
    tolerance = 0.0001

    if abs(total_weight - 1.0) > tolerance:
        raise ValueError(
            f"Persona weights must sum to 1.0, got {total_weight:.4f}. "
            f"Individual weights: {{{', '.join(f'{k}: {v.default_weight}' for k, v in PERSONAS.items())}}}"
        )


def get_persona(persona_id: str) -> PersonaConfig:
    """Get persona configuration by ID.

    Args:
        persona_id: The persona identifier

    Returns:
        PersonaConfig for the requested persona

    Raises:
        KeyError: If persona_id is not found
    """
    if persona_id not in PERSONAS:
        available = ", ".join(PERSONAS.keys())
        raise KeyError(
            f"Unknown persona_id '{persona_id}'. Available personas: {available}"
        )
    return PERSONAS[persona_id]


def get_all_personas() -> dict[str, PersonaConfig]:
    """Get all persona configurations.

    Returns:
        Dictionary mapping persona IDs to PersonaConfig objects
    """
    return PERSONAS.copy()


def get_persona_weights() -> dict[str, float]:
    """Get default weights for all personas.

    Returns:
        Dictionary mapping persona IDs to their default weights
    """
    return {persona_id: persona.default_weight for persona_id, persona in PERSONAS.items()}


# Validate weights at module import time
validate_persona_weights()


__all__ = [
    "PersonaConfig",
    "PERSONAS",
    "PERSONA_TEMPERATURE",
    "APPROVE_THRESHOLD",
    "REVISE_THRESHOLD",
    "validate_persona_weights",
    "get_persona",
    "get_all_personas",
    "get_persona_weights",
]
