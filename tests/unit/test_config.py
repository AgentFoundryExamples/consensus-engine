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
"""Unit tests for configuration module."""

import pytest
from pydantic import ValidationError

from consensus_engine.config import Environment, Settings, get_settings


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clean environment variables before each test."""
    # Clear the lru_cache for get_settings
    get_settings.cache_clear()

    env_vars = [
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "TEMPERATURE",
        "ENV",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def valid_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Set up valid environment variables."""
    env_vars = {
        "OPENAI_API_KEY": "sk-test-key-123456789",
        "OPENAI_MODEL": "gpt-5.1",
        "TEMPERATURE": "0.7",
        "ENV": "development",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


class TestSettings:
    """Test suite for Settings class."""

    def test_settings_with_valid_config(self, clean_env: None, valid_env: dict[str, str]) -> None:
        """Test Settings loads correctly with valid configuration."""
        settings = Settings()

        assert settings.openai_api_key == "sk-test-key-123456789"
        assert settings.openai_model == "gpt-5.1"
        assert settings.temperature == 0.7
        assert settings.env == Environment.DEVELOPMENT

    def test_settings_missing_api_key(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test Settings raises error when OPENAI_API_KEY is missing."""
        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("openai_api_key",) for e in errors)

    def test_settings_empty_api_key(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Settings raises error when OPENAI_API_KEY is empty."""
        monkeypatch.setenv("OPENAI_API_KEY", "")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        # Check for validation error on openai_api_key field
        # Empty string fails min_length validation
        assert any(
            e["loc"] == ("openai_api_key",) and e["type"] == "string_too_short" for e in errors
        )

    def test_settings_placeholder_api_key(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test Settings rejects placeholder API keys."""
        monkeypatch.setenv("OPENAI_API_KEY", "your_api_key_here")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        # Check for validation error on openai_api_key field with placeholder message
        assert any(
            e["loc"] == ("openai_api_key",) and "placeholder" in str(e["msg"]).lower()
            for e in errors
        )

    def test_settings_default_values(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test Settings uses default values when optional vars are missing."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")

        settings = Settings()

        assert settings.openai_model == "gpt-5.1"
        assert settings.temperature == 0.7
        assert settings.env == Environment.DEVELOPMENT

    def test_temperature_validation_min(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test temperature validation rejects values below 0.0."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")
        monkeypatch.setenv("TEMPERATURE", "-0.1")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("temperature",) for e in errors)

    def test_temperature_validation_max(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test temperature validation rejects values above 1.0."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")
        monkeypatch.setenv("TEMPERATURE", "1.1")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("temperature",) for e in errors)

    def test_temperature_edge_cases(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test temperature accepts boundary values 0.0 and 1.0."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")

        # Test 0.0
        monkeypatch.setenv("TEMPERATURE", "0.0")
        settings_min = Settings()
        assert settings_min.temperature == 0.0

        # Test 1.0
        monkeypatch.setenv("TEMPERATURE", "1.0")
        settings_max = Settings()
        assert settings_max.temperature == 1.0

    def test_environment_enum_values(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test environment accepts valid enum values."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")

        for env_value in ["development", "production", "testing"]:
            monkeypatch.setenv("ENV", env_value)
            settings = Settings()
            assert settings.env.value == env_value

    def test_log_level_property(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test log_level property returns correct level based on environment."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")

        # Development
        monkeypatch.setenv("ENV", "development")
        settings_dev = Settings()
        assert settings_dev.log_level == "DEBUG"

        # Testing
        monkeypatch.setenv("ENV", "testing")
        settings_test = Settings()
        assert settings_test.log_level == "INFO"

        # Production
        monkeypatch.setenv("ENV", "production")
        settings_prod = Settings()
        assert settings_prod.log_level == "WARNING"

    def test_debug_property(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test debug property is True only in development."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")

        # Development
        monkeypatch.setenv("ENV", "development")
        settings_dev = Settings()
        assert settings_dev.debug is True

        # Production
        monkeypatch.setenv("ENV", "production")
        settings_prod = Settings()
        assert settings_prod.debug is False

    def test_get_safe_dict_masks_api_key(self, clean_env: None, valid_env: dict[str, str]) -> None:
        """Test get_safe_dict masks the API key for safe logging."""
        settings = Settings()
        safe_dict = settings.get_safe_dict()

        assert "openai_api_key" in safe_dict
        assert safe_dict["openai_api_key"].startswith("***")
        assert safe_dict["openai_api_key"].endswith("6789")
        assert "sk-test-key" not in safe_dict["openai_api_key"]

    def test_api_key_stripped(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test API key is stripped of leading/trailing whitespace."""
        monkeypatch.setenv("OPENAI_API_KEY", "  sk-test-key-123456789  ")

        settings = Settings()
        assert settings.openai_api_key == "sk-test-key-123456789"
        assert not settings.openai_api_key.startswith(" ")
        assert not settings.openai_api_key.endswith(" ")


class TestGetSettings:
    """Test suite for get_settings cached function."""

    def test_get_settings_returns_instance(
        self, clean_env: None, valid_env: dict[str, str]
    ) -> None:
        """Test get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_cached(self, clean_env: None, valid_env: dict[str, str]) -> None:
        """Test get_settings returns the same instance on multiple calls (cached)."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_get_settings_raises_on_missing_key(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test get_settings raises error when API key is missing."""
        with pytest.raises(ValidationError):
            get_settings()


class TestEnvironmentEnum:
    """Test suite for Environment enum."""

    def test_environment_enum_values(self) -> None:
        """Test Environment enum has expected values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.PRODUCTION.value == "production"
        assert Environment.TESTING.value == "testing"

    def test_environment_enum_string_comparison(self) -> None:
        """Test Environment enum can be compared with strings."""
        assert Environment.DEVELOPMENT == "development"
        assert Environment.PRODUCTION == "production"
        assert Environment.TESTING == "testing"


class TestCORSConfiguration:
    """Test suite for CORS configuration settings."""

    def test_cors_origins_default(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test CORS origins defaults to localhost:5173."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")

        settings = Settings()
        assert settings.cors_origins == "http://localhost:5173"
        assert settings.cors_origins_list == ["http://localhost:5173"]

    def test_cors_origins_single(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test CORS origins with a single origin."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")
        monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")

        settings = Settings()
        assert settings.cors_origins == "https://app.example.com"
        assert settings.cors_origins_list == ["https://app.example.com"]

    def test_cors_origins_multiple(self, clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test CORS origins with multiple origins."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")
        monkeypatch.setenv(
            "CORS_ORIGINS", "https://app.example.com,https://staging.example.com,http://localhost:3000"
        )

        settings = Settings()
        assert settings.cors_origins_list == [
            "https://app.example.com",
            "https://staging.example.com",
            "http://localhost:3000",
        ]

    def test_cors_origins_with_spaces(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test CORS origins handles spaces around commas."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")
        monkeypatch.setenv(
            "CORS_ORIGINS", "https://app.example.com , https://staging.example.com , http://localhost:3000"
        )

        settings = Settings()
        assert settings.cors_origins_list == [
            "https://app.example.com",
            "https://staging.example.com",
            "http://localhost:3000",
        ]

    def test_cors_origins_rejects_wildcard(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test CORS origins rejects wildcard for security."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")
        monkeypatch.setenv("CORS_ORIGINS", "*")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        assert any(
            e["loc"] == ("cors_origins",) and "wildcard" in str(e["msg"]).lower() for e in errors
        )

    def test_cors_origins_rejects_wildcard_in_list(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test CORS origins rejects wildcard even in a list."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")
        monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com,*")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        assert any(
            e["loc"] == ("cors_origins",) and "wildcard" in str(e["msg"]).lower() for e in errors
        )

    def test_cors_origins_rejects_empty(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test CORS origins rejects empty string."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")
        monkeypatch.setenv("CORS_ORIGINS", "")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("cors_origins",) for e in errors)

    def test_cors_origins_validates_url_format(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test CORS origins validates URL format for non-localhost origins."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")
        monkeypatch.setenv("CORS_ORIGINS", "invalid-url")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        assert any(
            e["loc"] == ("cors_origins",) and "invalid" in str(e["msg"]).lower() for e in errors
        )

    def test_cors_origins_allows_localhost(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test CORS origins allows localhost URLs."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:3000")

        settings = Settings()
        assert settings.cors_origins_list == ["http://localhost:5173", "http://127.0.0.1:3000"]

    def test_cors_allow_headers_default(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test CORS allow headers defaults to wildcard."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")

        settings = Settings()
        assert settings.cors_allow_headers == "*"
        assert settings.cors_allow_headers_list == ["*"]

    def test_cors_allow_headers_explicit(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test CORS allow headers with explicit list."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")
        monkeypatch.setenv("CORS_ALLOW_HEADERS", "Content-Type,Authorization,X-Request-ID")

        settings = Settings()
        assert settings.cors_allow_headers_list == [
            "Content-Type",
            "Authorization",
            "X-Request-ID",
        ]

    def test_cors_allow_headers_with_spaces(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test CORS allow headers handles spaces around commas."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")
        monkeypatch.setenv("CORS_ALLOW_HEADERS", "Content-Type , Authorization , X-Request-ID")

        settings = Settings()
        assert settings.cors_allow_headers_list == [
            "Content-Type",
            "Authorization",
            "X-Request-ID",
        ]

    def test_cors_allow_headers_wildcard_only(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test CORS allow headers returns wildcard as single item list."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")
        monkeypatch.setenv("CORS_ALLOW_HEADERS", "*")

        settings = Settings()
        assert settings.cors_allow_headers_list == ["*"]

    def test_cors_production_recommendation(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test CORS configuration for production environment."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")
        monkeypatch.setenv("ENV", "production")
        monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com,https://staging.example.com")
        monkeypatch.setenv(
            "CORS_ALLOW_HEADERS", "Content-Type,Authorization,X-Request-ID,X-Schema-Version,X-Prompt-Set-Version"
        )

        settings = Settings()

        # Verify production settings
        assert settings.env == Environment.PRODUCTION
        assert "*" not in settings.cors_origins
        assert len(settings.cors_origins_list) == 2
        assert all("https://" in origin for origin in settings.cors_origins_list)
        assert "*" not in settings.cors_allow_headers_list
        assert "Content-Type" in settings.cors_allow_headers_list
        assert "Authorization" in settings.cors_allow_headers_list

