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
"""Unit tests for LLM steps configuration module."""

import pytest
from pydantic import ValidationError

from consensus_engine.config.llm_steps import (
    PROMPT_SET_VERSION,
    LLMStepsConfig,
    StepConfig,
    StepName,
    create_default_llm_steps_config,
)


class TestStepConfig:
    """Test suite for StepConfig class."""

    def test_step_config_valid(self) -> None:
        """Test StepConfig with valid configuration."""
        config = StepConfig(
            step_name=StepName.EXPAND,
            model="gpt-5.1",
            temperature=0.7,
            max_retries=3,
            timeout_seconds=300,
        )

        assert config.step_name == StepName.EXPAND
        assert config.model == "gpt-5.1"
        assert config.temperature == 0.7
        assert config.max_retries == 3
        assert config.timeout_seconds == 300
        assert config.feature_flags == {}

    def test_step_config_with_feature_flags(self) -> None:
        """Test StepConfig with feature flags."""
        config = StepConfig(
            step_name=StepName.REVIEW,
            model="gpt-5.1",
            temperature=0.2,
            feature_flags={"enable_caching": True, "debug_mode": False},
        )

        assert config.feature_flags == {"enable_caching": True, "debug_mode": False}

    def test_step_config_temperature_bounds(self) -> None:
        """Test StepConfig temperature validation."""
        # Temperature too low
        with pytest.raises(ValidationError) as exc_info:
            StepConfig(
                step_name=StepName.EXPAND,
                model="gpt-5.1",
                temperature=-0.1,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("temperature",) for e in errors)

        # Temperature too high
        with pytest.raises(ValidationError) as exc_info:
            StepConfig(
                step_name=StepName.EXPAND,
                model="gpt-5.1",
                temperature=1.1,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("temperature",) for e in errors)

    def test_step_config_empty_model(self) -> None:
        """Test StepConfig rejects empty model identifier."""
        with pytest.raises(ValidationError) as exc_info:
            StepConfig(
                step_name=StepName.EXPAND,
                model="   ",
                temperature=0.7,
            )
        errors = exc_info.value.errors()
        assert any("empty" in str(e["msg"]).lower() for e in errors)

    def test_step_config_max_retries_bounds(self) -> None:
        """Test StepConfig max_retries validation."""
        # Too low
        with pytest.raises(ValidationError) as exc_info:
            StepConfig(
                step_name=StepName.EXPAND,
                model="gpt-5.1",
                temperature=0.7,
                max_retries=0,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("max_retries",) for e in errors)

        # Too high
        with pytest.raises(ValidationError) as exc_info:
            StepConfig(
                step_name=StepName.EXPAND,
                model="gpt-5.1",
                temperature=0.7,
                max_retries=11,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("max_retries",) for e in errors)


class TestLLMStepsConfig:
    """Test suite for LLMStepsConfig class."""

    def test_llm_steps_config_valid(self) -> None:
        """Test LLMStepsConfig with valid configuration."""
        config = LLMStepsConfig(
            expand=StepConfig(
                step_name=StepName.EXPAND,
                model="gpt-5.1",
                temperature=0.7,
            ),
            review=StepConfig(
                step_name=StepName.REVIEW,
                model="gpt-5.1",
                temperature=0.2,
            ),
            aggregate=StepConfig(
                step_name=StepName.AGGREGATE,
                model="gpt-5.1",
                temperature=0.0,
            ),
        )

        assert config.expand.step_name == StepName.EXPAND
        assert config.review.step_name == StepName.REVIEW
        assert config.aggregate.step_name == StepName.AGGREGATE
        assert config.prompt_set_version == PROMPT_SET_VERSION

    def test_llm_steps_config_get_step_config(self) -> None:
        """Test LLMStepsConfig.get_step_config method."""
        config = create_default_llm_steps_config()

        # Test with enum
        expand_config = config.get_step_config(StepName.EXPAND)
        assert expand_config.step_name == StepName.EXPAND
        assert expand_config.model == "gpt-5.1"
        assert expand_config.temperature == 0.7

        # Test with string
        review_config = config.get_step_config("review")
        assert review_config.step_name == StepName.REVIEW
        assert review_config.temperature == 0.2

        aggregate_config = config.get_step_config("aggregate")
        assert aggregate_config.step_name == StepName.AGGREGATE
        assert aggregate_config.temperature == 0.0

    def test_llm_steps_config_get_step_config_invalid(self) -> None:
        """Test LLMStepsConfig.get_step_config with invalid step name."""
        config = create_default_llm_steps_config()

        with pytest.raises(ValueError) as exc_info:
            config.get_step_config("invalid_step")

        assert "Unknown step name" in str(exc_info.value)
        assert "expand" in str(exc_info.value)
        assert "review" in str(exc_info.value)
        assert "aggregate" in str(exc_info.value)

    def test_llm_steps_config_custom_prompt_version(self) -> None:
        """Test LLMStepsConfig with custom prompt_set_version."""
        config = LLMStepsConfig(
            expand=StepConfig(
                step_name=StepName.EXPAND,
                model="gpt-5.1",
                temperature=0.7,
            ),
            review=StepConfig(
                step_name=StepName.REVIEW,
                model="gpt-5.1",
                temperature=0.2,
            ),
            aggregate=StepConfig(
                step_name=StepName.AGGREGATE,
                model="gpt-5.1",
                temperature=0.0,
            ),
            prompt_set_version="2.0.0",
        )

        assert config.prompt_set_version == "2.0.0"


class TestDefaultConfig:
    """Test suite for create_default_llm_steps_config function."""

    def test_create_default_llm_steps_config(self) -> None:
        """Test create_default_llm_steps_config creates valid config."""
        config = create_default_llm_steps_config()

        # Check expand config
        assert config.expand.step_name == StepName.EXPAND
        assert config.expand.model == "gpt-5.1"
        assert config.expand.temperature == 0.7
        assert config.expand.max_retries == 3
        assert config.expand.timeout_seconds == 300

        # Check review config
        assert config.review.step_name == StepName.REVIEW
        assert config.review.model == "gpt-5.1"
        assert config.review.temperature == 0.2
        assert config.review.max_retries == 3
        assert config.review.timeout_seconds == 300

        # Check aggregate config
        assert config.aggregate.step_name == StepName.AGGREGATE
        assert config.aggregate.model == "gpt-5.1"
        assert config.aggregate.temperature == 0.0
        assert config.aggregate.max_retries == 3
        assert config.aggregate.timeout_seconds == 300

        # Check prompt set version
        assert config.prompt_set_version == PROMPT_SET_VERSION


class TestStepName:
    """Test suite for StepName enum."""

    def test_step_name_values(self) -> None:
        """Test StepName enum has expected values."""
        assert StepName.EXPAND.value == "expand"
        assert StepName.REVIEW.value == "review"
        assert StepName.AGGREGATE.value == "aggregate"

    def test_step_name_from_string(self) -> None:
        """Test StepName can be created from string."""
        assert StepName("expand") == StepName.EXPAND
        assert StepName("review") == StepName.REVIEW
        assert StepName("aggregate") == StepName.AGGREGATE

    def test_step_name_invalid_string(self) -> None:
        """Test StepName rejects invalid string."""
        with pytest.raises(ValueError):
            StepName("invalid")
