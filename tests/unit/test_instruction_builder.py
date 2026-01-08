"""Unit tests for instruction builder module."""

import pytest

from consensus_engine.config.instruction_builder import InstructionBuilder, InstructionPayload
from consensus_engine.config.llm_steps import PROMPT_SET_VERSION


class TestInstructionPayload:
    """Test suite for InstructionPayload class."""

    def test_instruction_payload_valid(self) -> None:
        """Test InstructionPayload with valid data."""
        payload = InstructionPayload(
            system_instruction="System instruction",
            developer_instruction="Developer instruction",
            user_content="User content",
            combined_instruction="System instruction\n\nDeveloper instruction",
            metadata={"key": "value"},
        )

        assert payload.system_instruction == "System instruction"
        assert payload.developer_instruction == "Developer instruction"
        assert payload.user_content == "User content"
        assert payload.combined_instruction == "System instruction\n\nDeveloper instruction"
        assert payload.metadata == {"key": "value"}

    def test_instruction_payload_no_developer_instruction(self) -> None:
        """Test InstructionPayload with no developer instruction."""
        payload = InstructionPayload(
            system_instruction="System instruction",
            developer_instruction=None,
            user_content="User content",
            combined_instruction="System instruction",
            metadata={},
        )

        assert payload.developer_instruction is None
        assert payload.combined_instruction == "System instruction"


class TestInstructionBuilder:
    """Test suite for InstructionBuilder class."""

    def test_instruction_builder_basic(self) -> None:
        """Test InstructionBuilder with basic usage."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("System instruction")
            .with_developer_instruction("Developer instruction")
            .with_user_content("User content")
            .build()
        )

        assert payload.system_instruction == "System instruction"
        assert payload.developer_instruction == "Developer instruction"
        assert payload.user_content == "User content"
        assert "System instruction" in payload.combined_instruction
        assert "Developer instruction" in payload.combined_instruction
        assert "User content" in payload.combined_instruction
        assert payload.metadata["prompt_set_version"] == PROMPT_SET_VERSION

    def test_instruction_builder_without_developer_instruction(self) -> None:
        """Test InstructionBuilder without developer instruction."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("System instruction")
            .with_user_content("User content")
            .build()
        )

        assert payload.system_instruction == "System instruction"
        assert payload.developer_instruction is None
        assert payload.user_content == "User content"
        assert payload.combined_instruction == "System instruction\n\nUser content"

    def test_instruction_builder_with_persona(self) -> None:
        """Test InstructionBuilder with persona injection."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("System instruction")
            .with_developer_instruction("Developer instruction")
            .with_user_content("User content")
            .with_persona(
                persona_name="SecurityGuardian",
                persona_instructions="Focus on security concerns",
            )
            .build()
        )

        assert payload.system_instruction == "System instruction"
        assert payload.user_content == "User content"
        # Developer instruction should include persona context
        assert "SecurityGuardian" in payload.developer_instruction
        assert "Focus on security concerns" in payload.developer_instruction
        assert "Developer instruction" in payload.developer_instruction
        # Combined instruction should include everything
        assert "System instruction" in payload.combined_instruction
        assert "SecurityGuardian" in payload.combined_instruction
        assert payload.metadata["persona_name"] == "SecurityGuardian"

    def test_instruction_builder_with_persona_no_developer_instruction(self) -> None:
        """Test InstructionBuilder with persona but no developer instruction."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("System instruction")
            .with_user_content("User content")
            .with_persona(
                persona_name="Architect",
                persona_instructions="Focus on architecture",
            )
            .build()
        )

        # Developer instruction should be created from persona
        assert "Architect" in payload.developer_instruction
        assert "Focus on architecture" in payload.developer_instruction
        assert "System instruction" in payload.combined_instruction
        assert "Architect" in payload.combined_instruction

    def test_instruction_builder_with_metadata(self) -> None:
        """Test InstructionBuilder with additional metadata."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("System instruction")
            .with_user_content("User content")
            .with_metadata("custom_key", "custom_value")
            .with_metadata("step_name", "expand")
            .build()
        )

        assert payload.metadata["custom_key"] == "custom_value"
        assert payload.metadata["step_name"] == "expand"
        assert payload.metadata["prompt_set_version"] == PROMPT_SET_VERSION

    def test_instruction_builder_missing_system_instruction(self) -> None:
        """Test InstructionBuilder raises error when system instruction is missing."""
        builder = InstructionBuilder()

        with pytest.raises(ValueError) as exc_info:
            builder.with_user_content("User content").build()

        assert "System instruction is required" in str(exc_info.value)

    def test_instruction_builder_missing_user_content(self) -> None:
        """Test InstructionBuilder raises error when user content is missing."""
        builder = InstructionBuilder()

        with pytest.raises(ValueError) as exc_info:
            builder.with_system_instruction("System instruction").build()

        assert "User content is required" in str(exc_info.value)

    def test_instruction_builder_create_expand_payload(self) -> None:
        """Test InstructionBuilder.create_expand_payload convenience method."""
        payload = InstructionBuilder.create_expand_payload(
            system_instruction="System instruction",
            developer_instruction="Developer instruction",
            user_content="User content",
        )

        assert payload.system_instruction == "System instruction"
        assert payload.developer_instruction == "Developer instruction"
        assert payload.user_content == "User content"
        assert payload.metadata["step_name"] == "expand"
        assert payload.metadata["prompt_set_version"] == PROMPT_SET_VERSION

    def test_instruction_builder_create_review_payload(self) -> None:
        """Test InstructionBuilder.create_review_payload convenience method."""
        payload = InstructionBuilder.create_review_payload(
            system_instruction="System instruction",
            developer_instruction="Developer instruction",
            user_content="User content",
        )

        assert payload.system_instruction == "System instruction"
        assert payload.developer_instruction == "Developer instruction"
        assert payload.user_content == "User content"
        assert payload.metadata["step_name"] == "review"
        assert payload.metadata["prompt_set_version"] == PROMPT_SET_VERSION

    def test_instruction_builder_create_review_payload_with_persona(self) -> None:
        """Test InstructionBuilder.create_review_payload with persona."""
        payload = InstructionBuilder.create_review_payload(
            system_instruction="System instruction",
            developer_instruction="Developer instruction",
            user_content="User content",
            persona_name="Critic",
            persona_instructions="Focus on risks",
        )

        assert payload.system_instruction == "System instruction"
        assert payload.user_content == "User content"
        assert "Critic" in payload.developer_instruction
        assert "Focus on risks" in payload.developer_instruction
        assert "Developer instruction" in payload.developer_instruction
        assert payload.metadata["step_name"] == "review"
        assert payload.metadata["persona_name"] == "Critic"

    def test_instruction_builder_method_chaining(self) -> None:
        """Test InstructionBuilder supports method chaining."""
        builder = InstructionBuilder()

        # All methods should return self for chaining
        result1 = builder.with_system_instruction("System")
        assert result1 is builder

        result2 = builder.with_developer_instruction("Developer")
        assert result2 is builder

        result3 = builder.with_user_content("User")
        assert result3 is builder

        result4 = builder.with_persona("Persona", "Instructions")
        assert result4 is builder

        result5 = builder.with_metadata("key", "value")
        assert result5 is builder

        # Final build should return payload
        payload = builder.build()
        assert isinstance(payload, InstructionPayload)
