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
from urllib.parse import quote_plus

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
