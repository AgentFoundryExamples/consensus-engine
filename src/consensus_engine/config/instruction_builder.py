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
"""Instruction builder for composing Responses API payloads.

This module provides a reusable instruction hierarchy builder that composes
OpenAI Responses API payloads with clear separation of system instructions,
developer instructions, and user content, while supporting persona injection
and schema enforcement.
"""

from typing import Any

from pydantic import BaseModel, Field

from consensus_engine.config.llm_steps import PROMPT_SET_VERSION


class InstructionPayload(BaseModel):
    """Structured payload for Responses API calls.

    This class encapsulates the complete instruction hierarchy for an LLM call,
    separating concerns between system-level requirements, developer guidance,
    and user-provided content.

    Attributes:
        system_instruction: System-level instructions (safety, schema requirements)
        developer_instruction: Developer instructions (house style, persona role)
        user_content: User-provided content or prompt
        combined_instruction: Full combined instruction for the API
        metadata: Additional metadata about the payload
    """

    system_instruction: str = Field(
        ...,
        min_length=1,
        description="System-level instructions (safety, schema requirements)",
    )
    developer_instruction: str | None = Field(
        default=None,
        description="Developer instructions (house style, persona role)",
    )
    user_content: str = Field(
        ...,
        min_length=1,
        description="User-provided content or prompt",
    )
    combined_instruction: str = Field(
        ...,
        min_length=1,
        description="Full combined instruction for the API",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the payload",
    )


class InstructionBuilder:
    """Builder for composing Responses API instruction payloads.

    This builder provides a fluent interface for constructing instruction
    payloads with clear separation of system, developer, and user content.
    It ensures consistency across all LLM calls and supports persona injection.

    Example:
        >>> builder = InstructionBuilder()
        >>> payload = builder.with_system_instruction(
        ...     "You are a technical reviewer..."
        ... ).with_developer_instruction(
        ...     "Focus on security concerns..."
        ... ).with_user_content(
        ...     "Review this proposal..."
        ... ).with_persona(
        ...     persona_name="SecurityGuardian",
        ...     persona_instructions="You are a security expert...",
        ... ).build()
    """

    def __init__(self) -> None:
        """Initialize the instruction builder."""
        self._system_instruction: str | None = None
        self._developer_instruction: str | None = None
        self._user_content: str | None = None
        self._persona_name: str | None = None
        self._persona_instructions: str | None = None
        self._metadata: dict[str, Any] = {
            "prompt_set_version": PROMPT_SET_VERSION,
        }

    def with_system_instruction(self, system_instruction: str) -> "InstructionBuilder":
        """Set the system-level instruction.

        System instructions define safety boundaries, schema requirements,
        and fundamental behavior constraints.

        Args:
            system_instruction: System-level instruction text

        Returns:
            Self for method chaining
        """
        self._system_instruction = system_instruction
        return self

    def with_developer_instruction(self, developer_instruction: str) -> "InstructionBuilder":
        """Set the developer instruction.

        Developer instructions provide additional guidance on house style,
        formatting preferences, and context-specific requirements.

        Args:
            developer_instruction: Developer instruction text

        Returns:
            Self for method chaining
        """
        self._developer_instruction = developer_instruction
        return self

    def with_user_content(self, user_content: str) -> "InstructionBuilder":
        """Set the user-provided content.

        User content is the actual prompt or input from the user that the
        LLM should respond to.

        Args:
            user_content: User content text

        Returns:
            Self for method chaining
        """
        self._user_content = user_content
        return self

    def with_persona(
        self, persona_name: str, persona_instructions: str
    ) -> "InstructionBuilder":
        """Inject persona context into the instruction.

        Persona injection adds role-specific guidance to the developer
        instruction, ensuring the LLM responds from the correct perspective.

        Args:
            persona_name: Name of the persona (e.g., "SecurityGuardian")
            persona_instructions: Instructions specific to this persona

        Returns:
            Self for method chaining
        """
        self._persona_name = persona_name
        self._persona_instructions = persona_instructions
        return self

    def with_metadata(self, key: str, value: Any) -> "InstructionBuilder":
        """Add metadata to the payload.

        Args:
            key: Metadata key
            value: Metadata value

        Returns:
            Self for method chaining
        """
        self._metadata[key] = value
        return self

    def build(self) -> InstructionPayload:
        """Build the final instruction payload.

        This method combines all instruction components in the correct order:
        1. System instruction (required)
        2. Developer instruction (optional, includes persona if set)
        3. User content (required)

        Returns:
            InstructionPayload with all components combined

        Raises:
            ValueError: If required components are missing
        """
        # Validate required components
        if not self._system_instruction:
            raise ValueError("System instruction is required")
        if not self._user_content:
            raise ValueError("User content is required")

        # Build combined instruction with all parts
        parts = [self._system_instruction]

        # Prepare developer instruction with persona
        developer_instruction = self._developer_instruction
        if self._persona_name and self._persona_instructions:
            persona_context = (
                f"You are reviewing from the perspective of: {self._persona_name}\n\n"
                f"Persona instructions: {self._persona_instructions}"
            )
            if developer_instruction:
                developer_instruction = f"{persona_context}\n\n{developer_instruction}"
            else:
                developer_instruction = persona_context

        if developer_instruction:
            parts.append(developer_instruction)

        # Add user content
        parts.append(self._user_content)

        combined_instruction = "\n\n".join(parts)

        # Add metadata
        if self._persona_name:
            self._metadata["persona_name"] = self._persona_name

        return InstructionPayload(
            system_instruction=self._system_instruction,
            developer_instruction=developer_instruction,
            user_content=self._user_content,
            combined_instruction=combined_instruction,
            metadata=self._metadata,
        )

    @classmethod
    def create_expand_payload(
        cls, system_instruction: str, developer_instruction: str, user_content: str
    ) -> InstructionPayload:
        """Create a payload for the expand step.

        Convenience method for creating expand step payloads.

        Args:
            system_instruction: System instruction for expand
            developer_instruction: Developer instruction for expand
            user_content: User content to expand

        Returns:
            InstructionPayload for expand step
        """
        return (
            cls()
            .with_system_instruction(system_instruction)
            .with_developer_instruction(developer_instruction)
            .with_user_content(user_content)
            .with_metadata("step_name", "expand")
            .build()
        )

    @classmethod
    def create_review_payload(
        cls,
        system_instruction: str,
        developer_instruction: str,
        user_content: str,
        persona_name: str | None = None,
        persona_instructions: str | None = None,
    ) -> InstructionPayload:
        """Create a payload for the review step.

        Convenience method for creating review step payloads with optional
        persona injection.

        Args:
            system_instruction: System instruction for review
            developer_instruction: Developer instruction for review
            user_content: User content to review
            persona_name: Optional persona name
            persona_instructions: Optional persona instructions

        Returns:
            InstructionPayload for review step
        """
        builder = (
            cls()
            .with_system_instruction(system_instruction)
            .with_developer_instruction(developer_instruction)
            .with_user_content(user_content)
            .with_metadata("step_name", "review")
        )

        if persona_name and persona_instructions:
            builder = builder.with_persona(persona_name, persona_instructions)

        return builder.build()


__all__ = [
    "InstructionPayload",
    "InstructionBuilder",
]
