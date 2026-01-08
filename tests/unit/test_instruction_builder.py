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


class TestInstructionHierarchyOrdering:
    """Test suite for instruction hierarchy and ordering.

    These tests verify that instructions are ordered correctly (system -> developer -> user)
    and that the combined instruction follows the expected structure.
    """

    def test_instruction_ordering_system_developer_user(self) -> None:
        """Test that instructions are ordered: system, developer, user."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("SYSTEM_INSTRUCTION")
            .with_developer_instruction("DEVELOPER_INSTRUCTION")
            .with_user_content("USER_CONTENT")
            .build()
        )

        combined = payload.combined_instruction

        # Find positions of each instruction
        system_pos = combined.find("SYSTEM_INSTRUCTION")
        developer_pos = combined.find("DEVELOPER_INSTRUCTION")
        user_pos = combined.find("USER_CONTENT")

        # Verify all are present
        assert system_pos != -1, "System instruction not found in combined"
        assert developer_pos != -1, "Developer instruction not found in combined"
        assert user_pos != -1, "User content not found in combined"

        # Verify ordering: system < developer < user
        assert (
            system_pos < developer_pos
        ), "System instruction should come before developer"
        assert developer_pos < user_pos, "Developer instruction should come before user"

    def test_instruction_ordering_system_user_only(self) -> None:
        """Test ordering with only system and user (no developer)."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("SYSTEM_INSTRUCTION")
            .with_user_content("USER_CONTENT")
            .build()
        )

        combined = payload.combined_instruction

        system_pos = combined.find("SYSTEM_INSTRUCTION")
        user_pos = combined.find("USER_CONTENT")

        assert system_pos != -1, "System instruction not found"
        assert user_pos != -1, "User content not found"
        assert system_pos < user_pos, "System should come before user"

    def test_instruction_separation_with_newlines(self) -> None:
        """Test that instructions are separated by double newlines."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("System")
            .with_developer_instruction("Developer")
            .with_user_content("User")
            .build()
        )

        combined = payload.combined_instruction

        # Combined instruction should contain double newlines as separators
        assert "\n\n" in combined, "Instructions should be separated by double newlines"

    def test_persona_injection_preserves_ordering(self) -> None:
        """Test that persona injection doesn't break instruction ordering."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("SYSTEM")
            .with_developer_instruction("BASE_DEVELOPER")
            .with_persona(
                persona_name="TestPersona",
                persona_instructions="PERSONA_SPECIFIC",
            )
            .with_user_content("USER")
            .build()
        )

        combined = payload.combined_instruction

        system_pos = combined.find("SYSTEM")
        # Developer instruction should contain both base and persona content
        developer_part = payload.developer_instruction
        assert "BASE_DEVELOPER" in developer_part
        assert "TestPersona" in developer_part
        assert "PERSONA_SPECIFIC" in developer_part

        user_pos = combined.find("USER")

        # Verify ordering still holds
        assert system_pos != -1
        assert user_pos != -1
        assert system_pos < user_pos


class TestPersonaContentInjection:
    """Test suite for persona content injection into developer instructions.

    These tests verify that persona information is correctly injected into
    developer instructions and that the injection format is consistent.
    """

    def test_persona_name_appears_in_developer_instruction(self) -> None:
        """Test that persona name is included in developer instruction."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("System")
            .with_user_content("User")
            .with_persona(
                persona_name="SecurityGuardian",
                persona_instructions="Focus on security",
            )
            .build()
        )

        assert "SecurityGuardian" in payload.developer_instruction

    def test_persona_instructions_appear_in_developer_instruction(self) -> None:
        """Test that persona-specific instructions are included."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("System")
            .with_user_content("User")
            .with_persona(
                persona_name="Architect",
                persona_instructions="Evaluate architectural patterns",
            )
            .build()
        )

        assert "Evaluate architectural patterns" in payload.developer_instruction

    def test_persona_injection_with_existing_developer_instruction(self) -> None:
        """Test persona injection when developer instruction already exists."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("System")
            .with_developer_instruction("Base developer instructions")
            .with_user_content("User")
            .with_persona(
                persona_name="Critic",
                persona_instructions="Identify risks",
            )
            .build()
        )

        developer = payload.developer_instruction

        # Both base and persona content should be present
        assert "Base developer instructions" in developer
        assert "Critic" in developer
        assert "Identify risks" in developer

    def test_persona_injection_creates_developer_instruction_if_missing(self) -> None:
        """Test that persona injection creates developer instruction if none exists."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("System")
            .with_user_content("User")
            .with_persona(
                persona_name="Optimist",
                persona_instructions="Highlight opportunities",
            )
            .build()
        )

        assert payload.developer_instruction is not None
        assert "Optimist" in payload.developer_instruction
        assert "Highlight opportunities" in payload.developer_instruction

    def test_persona_metadata_stored(self) -> None:
        """Test that persona name is stored in metadata."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("System")
            .with_user_content("User")
            .with_persona(
                persona_name="UserAdvocate",
                persona_instructions="Consider user needs",
            )
            .build()
        )

        assert "persona_name" in payload.metadata
        assert payload.metadata["persona_name"] == "UserAdvocate"

    def test_multiple_personas_not_supported(self) -> None:
        """Test that calling with_persona multiple times overwrites previous persona."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("System")
            .with_user_content("User")
            .with_persona(
                persona_name="FirstPersona",
                persona_instructions="First instructions",
            )
            .with_persona(
                persona_name="SecondPersona",
                persona_instructions="Second instructions",
            )
            .build()
        )

        # Only the last persona should be present
        assert payload.metadata["persona_name"] == "SecondPersona"
        assert "SecondPersona" in payload.developer_instruction
        assert "Second instructions" in payload.developer_instruction


class TestPromptSetVersionTagging:
    """Test suite for prompt_set_version tagging.

    These tests verify that prompt_set_version is correctly tagged in metadata
    for all step types (expand, review, aggregate).
    """

    def test_prompt_set_version_in_basic_payload(self) -> None:
        """Test that prompt_set_version is included in basic payload."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("System")
            .with_user_content("User")
            .build()
        )

        assert "prompt_set_version" in payload.metadata
        assert payload.metadata["prompt_set_version"] == PROMPT_SET_VERSION

    def test_prompt_set_version_in_expand_payload(self) -> None:
        """Test prompt_set_version in expand step payload."""
        payload = InstructionBuilder.create_expand_payload(
            system_instruction="System",
            developer_instruction="Developer",
            user_content="User",
        )

        assert "prompt_set_version" in payload.metadata
        assert payload.metadata["prompt_set_version"] == PROMPT_SET_VERSION
        assert payload.metadata["step_name"] == "expand"

    def test_prompt_set_version_in_review_payload(self) -> None:
        """Test prompt_set_version in review step payload."""
        payload = InstructionBuilder.create_review_payload(
            system_instruction="System",
            developer_instruction="Developer",
            user_content="User",
        )

        assert "prompt_set_version" in payload.metadata
        assert payload.metadata["prompt_set_version"] == PROMPT_SET_VERSION
        assert payload.metadata["step_name"] == "review"

    def test_prompt_set_version_in_review_payload_with_persona(self) -> None:
        """Test prompt_set_version in review payload with persona."""
        payload = InstructionBuilder.create_review_payload(
            system_instruction="System",
            developer_instruction="Developer",
            user_content="User",
            persona_name="Architect",
            persona_instructions="Evaluate architecture",
        )

        assert "prompt_set_version" in payload.metadata
        assert payload.metadata["prompt_set_version"] == PROMPT_SET_VERSION
        assert payload.metadata["step_name"] == "review"
        assert payload.metadata["persona_name"] == "Architect"

    def test_prompt_set_version_constant_value(self) -> None:
        """Test that PROMPT_SET_VERSION constant has expected format."""
        # Verify it's a semantic version string
        import re

        assert isinstance(PROMPT_SET_VERSION, str)
        # Should match semantic versioning format: X.Y.Z
        assert re.match(r"^\d+\.\d+\.\d+$", PROMPT_SET_VERSION)

    def test_prompt_set_version_immutable_across_calls(self) -> None:
        """Test that prompt_set_version remains consistent across multiple builds."""
        payload1 = (
            InstructionBuilder()
            .with_system_instruction("System1")
            .with_user_content("User1")
            .build()
        )
        payload2 = (
            InstructionBuilder()
            .with_system_instruction("System2")
            .with_user_content("User2")
            .build()
        )

        assert payload1.metadata["prompt_set_version"] == payload2.metadata[
            "prompt_set_version"
        ]
        assert payload1.metadata["prompt_set_version"] == PROMPT_SET_VERSION


class TestInstructionPayloadMetadata:
    """Test suite for instruction payload metadata completeness.

    These tests verify that all expected metadata is present and correct
    in instruction payloads.
    """

    def test_metadata_contains_prompt_set_version(self) -> None:
        """Test that metadata always contains prompt_set_version."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("System")
            .with_user_content("User")
            .build()
        )

        assert "prompt_set_version" in payload.metadata
        assert isinstance(payload.metadata["prompt_set_version"], str)

    def test_metadata_step_name_for_expand(self) -> None:
        """Test that expand payload has step_name metadata."""
        payload = InstructionBuilder.create_expand_payload(
            system_instruction="System",
            developer_instruction="Developer",
            user_content="User",
        )

        assert "step_name" in payload.metadata
        assert payload.metadata["step_name"] == "expand"

    def test_metadata_step_name_for_review(self) -> None:
        """Test that review payload has step_name metadata."""
        payload = InstructionBuilder.create_review_payload(
            system_instruction="System",
            developer_instruction="Developer",
            user_content="User",
        )

        assert "step_name" in payload.metadata
        assert payload.metadata["step_name"] == "review"

    def test_metadata_custom_keys_preserved(self) -> None:
        """Test that custom metadata keys are preserved."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("System")
            .with_user_content("User")
            .with_metadata("custom_key_1", "value_1")
            .with_metadata("custom_key_2", 42)
            .with_metadata("custom_key_3", {"nested": "data"})
            .build()
        )

        assert payload.metadata["custom_key_1"] == "value_1"
        assert payload.metadata["custom_key_2"] == 42
        assert payload.metadata["custom_key_3"] == {"nested": "data"}

        # Verify prompt_set_version still present
        assert "prompt_set_version" in payload.metadata

    def test_metadata_persona_name_when_persona_used(self) -> None:
        """Test that persona_name appears in metadata when persona is used."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("System")
            .with_user_content("User")
            .with_persona(
                persona_name="TestPersona",
                persona_instructions="Instructions",
            )
            .build()
        )

        assert "persona_name" in payload.metadata
        assert payload.metadata["persona_name"] == "TestPersona"

    def test_metadata_no_persona_name_when_no_persona(self) -> None:
        """Test that persona_name is absent when no persona is used."""
        builder = InstructionBuilder()
        payload = (
            builder.with_system_instruction("System")
            .with_user_content("User")
            .build()
        )

        # persona_name should not be in metadata
        assert "persona_name" not in payload.metadata

    def test_metadata_complete_for_full_review_payload(self) -> None:
        """Test metadata completeness for a full review payload with all options."""
        payload = InstructionBuilder.create_review_payload(
            system_instruction="System",
            developer_instruction="Developer",
            user_content="User",
            persona_name="Critic",
            persona_instructions="Focus on risks",
        )

        # All expected metadata should be present
        assert "prompt_set_version" in payload.metadata
        assert "step_name" in payload.metadata
        assert "persona_name" in payload.metadata

        # Values should be correct
        assert payload.metadata["prompt_set_version"] == PROMPT_SET_VERSION
        assert payload.metadata["step_name"] == "review"
        assert payload.metadata["persona_name"] == "Critic"
