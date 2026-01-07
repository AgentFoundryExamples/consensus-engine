"""Integration tests for FastAPI application."""

import pytest
from fastapi.testclient import TestClient

from consensus_engine.app import create_app


@pytest.fixture
def valid_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up valid test environment."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-integration")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.1")
    monkeypatch.setenv("TEMPERATURE", "0.7")
    monkeypatch.setenv("ENV", "testing")


@pytest.fixture
def client(valid_test_env: None) -> TestClient:
    """Create test client with valid environment."""
    # Reset settings singleton before creating app
    import consensus_engine.config.settings as settings_module

    settings_module._settings = None

    app = create_app()
    return TestClient(app)


class TestAppEndpoints:
    """Test suite for FastAPI application endpoints."""

    def test_root_endpoint(self, client: TestClient) -> None:
        """Test root endpoint returns welcome message."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Consensus Engine API"
        assert data["version"] == "0.1.0"
        assert data["docs"] == "/docs"

    def test_health_check_endpoint(self, client: TestClient) -> None:
        """Test health check endpoint returns status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["environment"] == "testing"
        assert data["debug"] is False
        assert data["model"] == "gpt-5.1"

    def test_docs_endpoint_accessible(self, client: TestClient) -> None:
        """Test OpenAPI docs endpoint is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_schema_endpoint(self, client: TestClient) -> None:
        """Test OpenAPI schema endpoint is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Consensus Engine API"
        assert schema["info"]["version"] == "0.1.0"


class TestAppStartupFailure:
    """Test suite for application startup error handling."""

    def test_app_fails_without_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test application fails to start without API key."""
        # Reset settings singleton
        import consensus_engine.config.settings as settings_module

        settings_module._settings = None

        # Clear API key
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Should raise validation error when trying to get settings in lifespan
        from pydantic import ValidationError

        # The error will be raised when the app tries to get_settings during lifespan
        # We test this by trying to create settings directly
        with pytest.raises(ValidationError):
            from consensus_engine.config import get_settings
            get_settings()


class TestDependencyInjection:
    """Test suite for dependency injection."""

    def test_health_endpoint_uses_settings(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test health endpoint correctly uses injected settings."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify settings are being used
        assert "environment" in data
        assert "model" in data
        assert data["model"] == "gpt-5.1"
