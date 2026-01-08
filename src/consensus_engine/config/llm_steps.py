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
"""Centralized LLM step configuration for per-step model settings and prompt versioning.

This module provides audited configuration for model settings (model, temperature, and
sampling parameters) for each pipeline step, along with a versioned prompt set identifier.
All settings support environment variable overrides for flexible deployment configuration.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

# Prompt set version constant for tracking active prompt templates
PROMPT_SET_VERSION = "1.0.0"

# Schema version constant for tracking active schema version
SCHEMA_VERSION = "1.0.0"


class StepName(str, Enum):
    """Enumeration of pipeline step names."""

    EXPAND = "expand"
    REVIEW = "review"
    AGGREGATE = "aggregate"


class StepConfig(BaseModel):
    """Configuration for a single LLM pipeline step.

    Attributes:
        step_name: Name of the pipeline step
        model: Model identifier (e.g., 'gpt-5.1')
        temperature: Temperature for response generation (0.0-1.0)
        max_retries: Maximum retry attempts for this step
        timeout_seconds: Timeout for this step in seconds
        feature_flags: Optional feature flags for this step
    """

    step_name: StepName = Field(
        ...,
        description="Name of the pipeline step",
    )
    model: str = Field(
        ...,
        min_length=1,
        description="Model identifier (e.g., 'gpt-5.1')",
    )
    temperature: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Temperature for response generation (0.0-1.0)",
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for this step (1-10)",
    )
    timeout_seconds: int = Field(
        default=300,
        ge=10,
        le=1800,
        description="Timeout for this step in seconds (10-1800)",
    )
    feature_flags: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional feature flags for this step",
    )

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate model identifier is not empty.

        Args:
            v: Model identifier to validate

        Returns:
            Validated model identifier

        Raises:
            ValueError: If model identifier is empty or whitespace-only
        """
        v = v.strip()
        if not v:
            raise ValueError("Model identifier cannot be empty or whitespace-only")
        return v


class LLMStepsConfig(BaseModel):
    """Centralized configuration for all LLM pipeline steps.

    This class aggregates step configurations and provides validation
    for the entire pipeline configuration.

    Attributes:
        expand: Configuration for the expand step
        review: Configuration for the review step
        aggregate: Configuration for the aggregate step
        prompt_set_version: Version identifier for prompt templates
    """

    expand: StepConfig = Field(
        ...,
        description="Configuration for the expand step",
    )
    review: StepConfig = Field(
        ...,
        description="Configuration for the review step",
    )
    aggregate: StepConfig = Field(
        ...,
        description="Configuration for the aggregate step",
    )
    prompt_set_version: str = Field(
        default=PROMPT_SET_VERSION,
        min_length=1,
        description="Version identifier for prompt templates",
    )
    schema_version: str = Field(
        default=SCHEMA_VERSION,
        min_length=1,
        description="Version identifier for schema structures",
    )

    @model_validator(mode="after")
    def validate_step_configs(self) -> "LLMStepsConfig":
        """Validate that all step configs are consistent.

        Raises:
            ValueError: If configurations are inconsistent or invalid
        """
        # Ensure step names match
        if self.expand.step_name != StepName.EXPAND:
            raise ValueError(
                f"Expand config has wrong step_name: {self.expand.step_name}, expected 'expand'"
            )
        if self.review.step_name != StepName.REVIEW:
            raise ValueError(
                f"Review config has wrong step_name: {self.review.step_name}, expected 'review'"
            )
        if self.aggregate.step_name != StepName.AGGREGATE:
            raise ValueError(
                f"Aggregate config has wrong step_name: {self.aggregate.step_name}, "
                "expected 'aggregate'"
            )
        return self

    def get_step_config(self, step_name: StepName | str) -> StepConfig:
        """Get configuration for a specific step.

        Args:
            step_name: Name of the step (enum or string)

        Returns:
            StepConfig for the requested step

        Raises:
            ValueError: If step_name is not recognized
        """
        # Convert string to enum if needed
        if isinstance(step_name, str):
            try:
                step_name = StepName(step_name)
            except ValueError as e:
                available = ", ".join(s.value for s in StepName)
                raise ValueError(
                    f"Unknown step name '{step_name}'. Available steps: {available}"
                ) from e

        # Return the appropriate config
        if step_name == StepName.EXPAND:
            return self.expand
        elif step_name == StepName.REVIEW:
            return self.review
        elif step_name == StepName.AGGREGATE:
            return self.aggregate
        else:
            # Should never reach here due to enum validation
            raise ValueError(f"Unhandled step name: {step_name}")


def create_default_llm_steps_config() -> LLMStepsConfig:
    """Create default LLM steps configuration with standard settings.

    Returns:
        LLMStepsConfig with default settings for all steps
    """
    return LLMStepsConfig(
        expand=StepConfig(
            step_name=StepName.EXPAND,
            model="gpt-5.1",
            temperature=0.7,
            max_retries=3,
            timeout_seconds=300,
        ),
        review=StepConfig(
            step_name=StepName.REVIEW,
            model="gpt-5.1",
            temperature=0.2,
            max_retries=3,
            timeout_seconds=300,
        ),
        aggregate=StepConfig(
            step_name=StepName.AGGREGATE,
            model="gpt-5.1",
            temperature=0.0,
            max_retries=3,
            timeout_seconds=300,
        ),
        prompt_set_version=PROMPT_SET_VERSION,
        schema_version=SCHEMA_VERSION,
    )


__all__ = [
    "PROMPT_SET_VERSION",
    "SCHEMA_VERSION",
    "StepName",
    "StepConfig",
    "LLMStepsConfig",
    "create_default_llm_steps_config",
]
