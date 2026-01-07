"""Configuration module for Consensus Engine.

This module provides centralized configuration management using Pydantic Settings.
It handles environment variable loading, validation, and provides sensible defaults.
"""

from enum import Enum
from functools import lru_cache

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

    # Application Configuration
    env: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment mode",
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

    @field_validator("temperature")
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

    def get_safe_dict(self) -> dict:
        """Get a dictionary representation with sensitive data masked.

        Returns:
            Dictionary with API key masked for safe logging
        """
        data = self.model_dump()
        if "openai_api_key" in data and data["openai_api_key"]:
            # Mask API key for safe logging
            data["openai_api_key"] = "***" + data["openai_api_key"][-4:]
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
