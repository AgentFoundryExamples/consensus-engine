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
"""Configuration module for Consensus Engine.

This module provides centralized configuration management using Pydantic Settings.
It handles environment variable loading, validation, and provides sensible defaults.
"""

from enum import Enum
from functools import lru_cache
from typing import TYPE_CHECKING
from urllib.parse import quote_plus

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from consensus_engine.config.llm_steps import LLMStepsConfig


class Environment(str, Enum):
    """Application environment modes."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    This class uses Pydantic Settings to load and validate configuration
    from environment variables with proper type conversion and validation.

    Attributes:
        openai_api_key: OpenAI API key for authentication (required)
        openai_model: OpenAI model to use (default: gpt-5.1)
        temperature: Temperature for model responses (0.0-1.0, default: 0.7)
        expand_model: Model for expansion step (default: gpt-5.1)
        expand_temperature: Temperature for expansion (default: 0.7)
        review_model: Model for review step (default: gpt-5.1)
        review_temperature: Temperature for review (default: 0.2)
        default_persona_name: Default persona name for reviews (default: GenericReviewer)
        default_persona_instructions: Default persona instructions for reviews
        env: Application environment mode (default: development)
        log_level: Logging level based on environment
        debug: Debug mode flag based on environment
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI Configuration
    openai_api_key: str = Field(
        ...,
        description="OpenAI API key for authentication",
        min_length=1,
    )
    openai_model: str = Field(
        default="gpt-5.1",
        description="OpenAI model to use (default: gpt-5.1)",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperature for model responses (0.0-1.0)",
    )

    # Expansion Configuration
    expand_model: str = Field(
        default="gpt-5.1",
        description="Model for expansion step (default: gpt-5.1)",
    )
    expand_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperature for expansion (0.0-1.0, default: 0.7)",
    )

    # Review Configuration
    review_model: str = Field(
        default="gpt-5.1",
        description="Model for review step (default: gpt-5.1)",
    )
    review_temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Temperature for review (0.0-1.0, default: 0.2 for deterministic reviews)",
    )

    # Aggregation Configuration
    aggregate_model: str = Field(
        default="gpt-5.1",
        description="Model for aggregation step (default: gpt-5.1)",
    )
    aggregate_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "Temperature for aggregation (0.0-1.0, "
            "default: 0.0 for deterministic aggregation)"
        ),
    )

    # Persona Configuration
    default_persona_name: str = Field(
        default="GenericReviewer",
        description="Default persona name for reviews",
        min_length=1,
    )
    default_persona_instructions: str = Field(
        default=(
            "You are a technical reviewer evaluating proposals for feasibility, "
            "risks, and completeness. Provide balanced feedback identifying both "
            "strengths and concerns."
        ),
        description="Default persona instructions for reviews",
        min_length=1,
    )
    persona_template_version: str = Field(
        default="1.0.0",
        description="Version identifier for persona templates used",
        min_length=1,
    )

    # Retry Configuration
    max_retries_per_persona: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts per persona review (1-10, default: 3)",
    )
    retry_initial_backoff_seconds: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
        description="Initial backoff delay in seconds for retries (0.1-60.0, default: 1.0)",
    )
    retry_backoff_multiplier: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description="Exponential backoff multiplier for retries (1.0-10.0, default: 2.0)",
    )

    # Application Configuration
    env: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment mode",
    )

    # Database Configuration
    use_cloud_sql_connector: bool = Field(
        default=False,
        description="Use Cloud SQL Python Connector for IAM authentication",
    )
    db_instance_connection_name: str | None = Field(
        default=None,
        description="Cloud SQL instance connection name (project:region:instance)",
    )
    db_name: str = Field(
        default="consensus_engine",
        description="Database name",
    )
    db_user: str = Field(
        default="postgres",
        description="Database user",
    )
    db_password: str | None = Field(
        default=None,
        description="Database password (not used with IAM auth)",
    )
    db_host: str = Field(
        default="localhost",
        description="Database host (for local connections)",
    )
    db_port: int = Field(
        default=5432,
        ge=1,
        le=65535,
        description="Database port (for local connections)",
    )
    db_iam_auth: bool = Field(
        default=False,
        description="Use IAM authentication with Cloud SQL Connector",
    )
    db_pool_size: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Database connection pool size",
    )
    db_max_overflow: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Maximum overflow connections beyond pool size",
    )
    db_pool_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Connection pool timeout in seconds",
    )
    db_pool_recycle: int = Field(
        default=3600,
        ge=60,
        le=7200,
        description="Connection pool recycle time in seconds",
    )

    # Pub/Sub Configuration
    pubsub_project_id: str | None = Field(
        default=None,
        description="Google Cloud project ID for Pub/Sub (required for production)",
    )
    pubsub_topic: str = Field(
        default="consensus-engine-jobs",
        description="Pub/Sub topic name for job queue",
        min_length=1,
    )
    pubsub_credentials_file: str | None = Field(
        default=None,
        description="Path to service account JSON credentials file",
    )
    pubsub_emulator_host: str | None = Field(
        default=None,
        description="Pub/Sub emulator host (e.g., localhost:8085) for local testing",
    )
    pubsub_use_mock: bool = Field(
        default=False,
        description="Use mock publisher for testing (no-op that logs messages)",
    )
    pubsub_subscription: str = Field(
        default="consensus-engine-jobs-sub",
        description="Pub/Sub subscription name for worker to consume",
        min_length=1,
    )

    # Worker Configuration
    worker_max_concurrency: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Maximum concurrent message handlers for worker (1-1000, default: 10)",
    )
    worker_ack_deadline_seconds: int = Field(
        default=600,
        ge=60,
        le=3600,
        description="Pub/Sub ack deadline in seconds (60-3600, default: 600)",
    )
    worker_step_timeout_seconds: int = Field(
        default=300,
        ge=10,
        le=1800,
        description="Per-step timeout in seconds (10-1800, default: 300)",
    )
    worker_job_timeout_seconds: int = Field(
        default=1800,
        ge=60,
        le=7200,
        description="Overall job timeout in seconds (60-7200, default: 1800)",
    )

    @field_validator("openai_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate that API key is not a placeholder and strip whitespace.

        Args:
            v: The API key value to validate

        Returns:
            The validated API key

        Raises:
            ValueError: If API key is invalid or contains placeholder text
        """
        if not v.strip():
            raise ValueError("OPENAI_API_KEY cannot be empty or contain only whitespace")

        if "your_api_key" in v.lower() or "placeholder" in v.lower():
            raise ValueError(
                "OPENAI_API_KEY appears to be a placeholder. " "Please provide a valid API key."
            )

        return v.strip()

    @field_validator("temperature", "expand_temperature", "review_temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validate temperature is within the allowed range [0.0, 1.0].

        Args:
            v: The temperature value to validate

        Returns:
            The validated temperature value
        """
        # The range is already enforced by `ge=0.0` and `le=1.0` on the Field,
        # but this validator can be kept for clarity or future complex validation.
        return v

    @field_validator("db_instance_connection_name")
    @classmethod
    def validate_cloud_sql_connection_name(cls, v: str | None) -> str | None:
        """Validate Cloud SQL connection name format.

        Args:
            v: The connection name to validate

        Returns:
            The validated connection name or None

        Raises:
            ValueError: If connection name format is invalid
        """
        if v is not None and v.strip():
            # Expected format: project:region:instance
            parts = v.strip().split(":")
            if len(parts) != 3:
                raise ValueError(
                    "DB_INSTANCE_CONNECTION_NAME must be in format 'project:region:instance'"
                )
            return v.strip()
        return v

    @property
    def log_level(self) -> str:
        """Get the appropriate log level based on environment.

        Returns:
            Log level string (DEBUG, INFO, WARNING, ERROR)
        """
        if self.env == Environment.DEVELOPMENT:
            return "DEBUG"
        elif self.env == Environment.TESTING:
            return "INFO"
        else:
            return "WARNING"

    @property
    def debug(self) -> bool:
        """Check if debug mode is enabled.

        Returns:
            True if in development environment, False otherwise
        """
        return self.env == Environment.DEVELOPMENT

    @property
    def database_url(self) -> str:
        """Get the database URL for SQLAlchemy.

        This property is used for non-Cloud SQL connections (local development).
        URL-encodes credentials to handle special characters safely.

        Returns:
            PostgreSQL database URL with encoded credentials

        Raises:
            ValueError: If required database configuration is missing
        """
        if not self.db_name:
            raise ValueError("DB_NAME is required for database connections")

        # URL-encode user and password to handle special characters
        user = quote_plus(self.db_user)

        # Build the connection URL
        if self.db_password:
            password = quote_plus(self.db_password)
            return (
                f"postgresql+psycopg://{user}:{password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
            )
        else:
            return f"postgresql+psycopg://{user}" f"@{self.db_host}:{self.db_port}/{self.db_name}"

    def get_safe_dict(self) -> dict:
        """Get a dictionary representation with sensitive data masked.

        Returns:
            Dictionary with API key and password masked for safe logging
        """
        data = self.model_dump()
        if "openai_api_key" in data and data["openai_api_key"]:
            # Mask API key for safe logging
            data["openai_api_key"] = "***" + data["openai_api_key"][-4:]
        if "db_password" in data and data["db_password"]:
            # Mask database password for safe logging
            data["db_password"] = "***MASKED***"
        return data

    def get_llm_steps_config(self) -> "LLMStepsConfig":
        """Get centralized LLM steps configuration from settings.

        Creates an LLMStepsConfig instance populated with step-specific
        settings from environment variables. This provides a unified
        configuration surface for all LLM pipeline steps.

        Returns:
            LLMStepsConfig instance with expand, review, and aggregate configs

        Raises:
            ValidationError: If any step configuration is invalid
        """
        from consensus_engine.config.llm_steps import LLMStepsConfig, StepConfig, StepName

        return LLMStepsConfig(
            expand=StepConfig(
                step_name=StepName.EXPAND,
                model=self.expand_model,
                temperature=self.expand_temperature,
                max_retries=self.max_retries_per_persona,
                timeout_seconds=self.worker_step_timeout_seconds,
            ),
            review=StepConfig(
                step_name=StepName.REVIEW,
                model=self.review_model,
                temperature=self.review_temperature,
                max_retries=self.max_retries_per_persona,
                timeout_seconds=self.worker_step_timeout_seconds,
            ),
            aggregate=StepConfig(
                step_name=StepName.AGGREGATE,
                model=self.aggregate_model,
                temperature=self.aggregate_temperature,
                max_retries=self.max_retries_per_persona,
                timeout_seconds=self.worker_step_timeout_seconds,
            ),
            prompt_set_version=self.persona_template_version,
        )


@lru_cache
def get_settings() -> Settings:
    """Get the application settings instance.

    This function is cached to ensure only one Settings instance is created.

    Returns:
        Settings instance with loaded and validated configuration

    Raises:
        pydantic.ValidationError: If any environment variables are invalid.
    """
    return Settings()
