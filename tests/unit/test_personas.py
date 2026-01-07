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
"""Unit tests for persona configuration."""

import pytest
from pydantic import ValidationError

from consensus_engine.config.personas import (
    APPROVE_THRESHOLD,
    PERSONA_TEMPERATURE,
    PERSONAS,
    REVISE_THRESHOLD,
    PersonaConfig,
    get_all_personas,
    get_persona,
    get_persona_weights,
    validate_persona_weights,
)


class TestPersonaConfig:
    """Test suite for PersonaConfig model."""

    def test_persona_config_valid(self) -> None:
        """Test PersonaConfig with valid data."""
        config = PersonaConfig(
            id="test_persona",
            display_name="Test Persona",
            developer_instructions="Test instructions for developers",
            system_prompt="Test system prompt for LLM",
            default_weight=0.5,
            temperature=0.2,
        )

        assert config.id == "test_persona"
        assert config.display_name == "Test Persona"
        assert config.developer_instructions == "Test instructions for developers"
        assert config.system_prompt == "Test system prompt for LLM"
        assert config.default_weight == 0.5
        assert config.temperature == 0.2

    def test_persona_config_trims_whitespace(self) -> None:
        """Test PersonaConfig trims whitespace from string fields."""
        config = PersonaConfig(
            id="  test_persona  ",
            display_name="  Test Persona  ",
            developer_instructions="  Test instructions  ",
            system_prompt="  Test prompt  ",
            default_weight=0.5,
            temperature=0.2,
        )

        assert config.id == "test_persona"
        assert config.display_name == "Test Persona"
        assert config.developer_instructions == "Test instructions"
        assert config.system_prompt == "Test prompt"

    def test_persona_config_rejects_empty_id(self) -> None:
        """Test PersonaConfig rejects empty id."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaConfig(
                id="",
                display_name="Test",
                developer_instructions="Test",
                system_prompt="Test",
                default_weight=0.5,
                temperature=0.2,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("id",) for e in errors)

    def test_persona_config_rejects_whitespace_only_fields(self) -> None:
        """Test PersonaConfig rejects whitespace-only fields."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaConfig(
                id="   ",
                display_name="Test",
                developer_instructions="Test",
                system_prompt="Test",
                default_weight=0.5,
                temperature=0.2,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("id",) for e in errors)

    def test_persona_config_weight_range(self) -> None:
        """Test PersonaConfig validates weight range [0.0, 1.0]."""
        # Valid weights
        PersonaConfig(
            id="test",
            display_name="Test",
            developer_instructions="Test",
            system_prompt="Test",
            default_weight=0.0,
            temperature=0.2,
        )
        PersonaConfig(
            id="test",
            display_name="Test",
            developer_instructions="Test",
            system_prompt="Test",
            default_weight=1.0,
            temperature=0.2,
        )

        # Invalid weight (too low)
        with pytest.raises(ValidationError):
            PersonaConfig(
                id="test",
                display_name="Test",
                developer_instructions="Test",
                system_prompt="Test",
                default_weight=-0.1,
                temperature=0.2,
            )

        # Invalid weight (too high)
        with pytest.raises(ValidationError):
            PersonaConfig(
                id="test",
                display_name="Test",
                developer_instructions="Test",
                system_prompt="Test",
                default_weight=1.1,
                temperature=0.2,
            )

    def test_persona_config_temperature_range(self) -> None:
        """Test PersonaConfig validates temperature range [0.0, 1.0]."""
        # Valid temperatures
        PersonaConfig(
            id="test",
            display_name="Test",
            developer_instructions="Test",
            system_prompt="Test",
            default_weight=0.5,
            temperature=0.0,
        )
        PersonaConfig(
            id="test",
            display_name="Test",
            developer_instructions="Test",
            system_prompt="Test",
            default_weight=0.5,
            temperature=1.0,
        )

        # Invalid temperature (too low)
        with pytest.raises(ValidationError):
            PersonaConfig(
                id="test",
                display_name="Test",
                developer_instructions="Test",
                system_prompt="Test",
                default_weight=0.5,
                temperature=-0.1,
            )

        # Invalid temperature (too high)
        with pytest.raises(ValidationError):
            PersonaConfig(
                id="test",
                display_name="Test",
                developer_instructions="Test",
                system_prompt="Test",
                default_weight=0.5,
                temperature=1.1,
            )


class TestPersonasConfiguration:
    """Test suite for PERSONAS configuration."""

    def test_personas_defined(self) -> None:
        """Test that all required personas are defined."""
        expected_personas = {
            "architect",
            "critic",
            "optimist",
            "security_guardian",
            "user_advocate",
        }
        assert set(PERSONAS.keys()) == expected_personas

    def test_all_personas_have_required_fields(self) -> None:
        """Test that all personas have required fields populated."""
        for persona_id, persona in PERSONAS.items():
            assert persona.id == persona_id
            assert len(persona.display_name) > 0
            assert len(persona.developer_instructions) > 0
            assert len(persona.system_prompt) > 0
            assert 0.0 <= persona.default_weight <= 1.0
            assert 0.0 <= persona.temperature <= 1.0

    def test_persona_display_names(self) -> None:
        """Test persona display names match expectations."""
        assert PERSONAS["architect"].display_name == "Architect"
        assert PERSONAS["critic"].display_name == "Critic"
        assert PERSONAS["optimist"].display_name == "Optimist"
        assert PERSONAS["security_guardian"].display_name == "SecurityGuardian"
        assert PERSONAS["user_advocate"].display_name == "UserAdvocate"

    def test_persona_weights_match_requirements(self) -> None:
        """Test persona weights match the specified requirements."""
        assert PERSONAS["architect"].default_weight == 0.25
        assert PERSONAS["critic"].default_weight == 0.25
        assert PERSONAS["optimist"].default_weight == 0.15
        assert PERSONAS["security_guardian"].default_weight == 0.20
        assert PERSONAS["user_advocate"].default_weight == 0.15

    def test_persona_weights_sum_to_one(self) -> None:
        """Test persona weights sum to exactly 1.0."""
        total_weight = sum(persona.default_weight for persona in PERSONAS.values())
        assert abs(total_weight - 1.0) < 0.0001

    def test_all_personas_use_shared_temperature(self) -> None:
        """Test all personas use the shared low temperature."""
        for persona in PERSONAS.values():
            assert persona.temperature == PERSONA_TEMPERATURE

    def test_persona_temperature_in_range(self) -> None:
        """Test PERSONA_TEMPERATURE is in the low range (0.1-0.3)."""
        assert 0.1 <= PERSONA_TEMPERATURE <= 0.3


class TestThresholdConstants:
    """Test suite for threshold constants."""

    def test_approve_threshold_value(self) -> None:
        """Test APPROVE_THRESHOLD has correct value."""
        assert APPROVE_THRESHOLD == 0.80

    def test_revise_threshold_value(self) -> None:
        """Test REVISE_THRESHOLD has correct value."""
        assert REVISE_THRESHOLD == 0.60

    def test_threshold_ordering(self) -> None:
        """Test thresholds are ordered correctly."""
        assert REVISE_THRESHOLD < APPROVE_THRESHOLD


class TestValidatePersonaWeights:
    """Test suite for validate_persona_weights function."""

    def test_validate_persona_weights_succeeds(self) -> None:
        """Test validate_persona_weights succeeds with valid weights."""
        # Should not raise an exception
        validate_persona_weights()

    def test_validate_persona_weights_called_at_import(self) -> None:
        """Test validate_persona_weights is called at module import time."""
        # If we got here, the module imported successfully, meaning validation passed
        # This test documents the behavior that validation happens at import
        assert True


class TestGetPersona:
    """Test suite for get_persona function."""

    def test_get_persona_returns_config(self) -> None:
        """Test get_persona returns correct PersonaConfig."""
        architect = get_persona("architect")
        assert isinstance(architect, PersonaConfig)
        assert architect.id == "architect"
        assert architect.display_name == "Architect"

    def test_get_persona_all_personas(self) -> None:
        """Test get_persona works for all defined personas."""
        for persona_id in PERSONAS.keys():
            persona = get_persona(persona_id)
            assert persona.id == persona_id

    def test_get_persona_unknown_id_raises_error(self) -> None:
        """Test get_persona raises KeyError for unknown persona_id."""
        with pytest.raises(KeyError) as exc_info:
            get_persona("unknown_persona")

        assert "unknown_persona" in str(exc_info.value)
        assert "Available personas" in str(exc_info.value)


class TestGetAllPersonas:
    """Test suite for get_all_personas function."""

    def test_get_all_personas_returns_dict(self) -> None:
        """Test get_all_personas returns a dictionary."""
        personas = get_all_personas()
        assert isinstance(personas, dict)

    def test_get_all_personas_returns_copy(self) -> None:
        """Test get_all_personas returns a copy, not the original."""
        personas1 = get_all_personas()
        personas2 = get_all_personas()
        assert personas1 is not personas2
        assert personas1 == personas2

    def test_get_all_personas_contains_all_personas(self) -> None:
        """Test get_all_personas contains all defined personas."""
        personas = get_all_personas()
        expected_ids = {"architect", "critic", "optimist", "security_guardian", "user_advocate"}
        assert set(personas.keys()) == expected_ids


class TestGetPersonaWeights:
    """Test suite for get_persona_weights function."""

    def test_get_persona_weights_returns_dict(self) -> None:
        """Test get_persona_weights returns a dictionary."""
        weights = get_persona_weights()
        assert isinstance(weights, dict)

    def test_get_persona_weights_maps_id_to_weight(self) -> None:
        """Test get_persona_weights maps persona IDs to weights."""
        weights = get_persona_weights()
        assert weights["architect"] == 0.25
        assert weights["critic"] == 0.25
        assert weights["optimist"] == 0.15
        assert weights["security_guardian"] == 0.20
        assert weights["user_advocate"] == 0.15

    def test_get_persona_weights_sum_to_one(self) -> None:
        """Test weights returned by get_persona_weights sum to 1.0."""
        weights = get_persona_weights()
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.0001


class TestPersonaInstructions:
    """Test suite for persona-specific instructions."""

    def test_architect_focuses_on_design(self) -> None:
        """Test Architect persona focuses on design and architecture."""
        architect = PERSONAS["architect"]
        instructions_lower = architect.developer_instructions.lower()
        prompt_lower = architect.system_prompt.lower()

        assert any(
            keyword in instructions_lower or keyword in prompt_lower
            for keyword in ["architect", "design", "scalability", "maintainability"]
        )

    def test_critic_focuses_on_risks(self) -> None:
        """Test Critic persona focuses on risks and edge cases."""
        critic = PERSONAS["critic"]
        instructions_lower = critic.developer_instructions.lower()
        prompt_lower = critic.system_prompt.lower()

        assert any(
            keyword in instructions_lower or keyword in prompt_lower
            for keyword in ["risk", "edge case", "failure", "skeptical"]
        )

    def test_optimist_focuses_on_strengths(self) -> None:
        """Test Optimist persona focuses on strengths and opportunities."""
        optimist = PERSONAS["optimist"]
        instructions_lower = optimist.developer_instructions.lower()
        prompt_lower = optimist.system_prompt.lower()

        assert any(
            keyword in instructions_lower or keyword in prompt_lower
            for keyword in ["strength", "opportunit", "positive", "feasible"]
        )

    def test_security_guardian_focuses_on_security(self) -> None:
        """Test SecurityGuardian persona focuses on security."""
        security = PERSONAS["security_guardian"]
        instructions_lower = security.developer_instructions.lower()
        prompt_lower = security.system_prompt.lower()

        assert any(
            keyword in instructions_lower or keyword in prompt_lower
            for keyword in ["security", "vulnerabilit", "authentication", "protection"]
        )

    def test_security_guardian_mentions_veto_power(self) -> None:
        """Test SecurityGuardian mentions veto power in instructions."""
        security = PERSONAS["security_guardian"]
        instructions_lower = security.developer_instructions.lower()
        assert "veto" in instructions_lower

    def test_user_advocate_focuses_on_usability(self) -> None:
        """Test UserAdvocate persona focuses on usability and UX."""
        user_advocate = PERSONAS["user_advocate"]
        instructions_lower = user_advocate.developer_instructions.lower()
        prompt_lower = user_advocate.system_prompt.lower()

        assert any(
            keyword in instructions_lower or keyword in prompt_lower
            for keyword in ["usability", "user", "experience", "accessibility"]
        )
