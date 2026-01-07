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
"""Unit tests for database module."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from consensus_engine.config import Settings, get_settings
from consensus_engine.db import (
    Base,
    check_database_health,
    close_connector,
    create_engine_from_settings,
    create_session_factory,
    get_connector,
    get_session,
)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch):
    """Clean environment variables before each test."""
    get_settings.cache_clear()

    # Set minimum required env vars
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")

    # Clear database env vars
    db_vars = [
        "USE_CLOUD_SQL_CONNECTOR",
        "DB_INSTANCE_CONNECTION_NAME",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "DB_HOST",
        "DB_PORT",
        "DB_IAM_AUTH",
        "DB_POOL_SIZE",
    ]
    for var in db_vars:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def local_db_settings(monkeypatch: pytest.MonkeyPatch):
    """Set up local database settings."""
    get_settings.cache_clear()

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")
    monkeypatch.setenv("USE_CLOUD_SQL_CONNECTOR", "false")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "test_db")
    monkeypatch.setenv("DB_USER", "test_user")
    monkeypatch.setenv("DB_PASSWORD", "test_pass")

    return get_settings()


@pytest.fixture
def cloud_sql_settings(monkeypatch: pytest.MonkeyPatch):
    """Set up Cloud SQL settings."""
    get_settings.cache_clear()

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")
    monkeypatch.setenv("USE_CLOUD_SQL_CONNECTOR", "true")
    monkeypatch.setenv("DB_INSTANCE_CONNECTION_NAME", "project:region:instance")
    monkeypatch.setenv("DB_NAME", "test_db")
    monkeypatch.setenv("DB_USER", "test_user")
    monkeypatch.setenv("DB_IAM_AUTH", "true")

    return get_settings()


class TestDatabaseConfiguration:
    """Test database configuration in Settings."""

    def test_default_database_settings(self, clean_env):
        """Test default database configuration values."""
        settings = get_settings()

        assert settings.use_cloud_sql_connector is False
        assert settings.db_name == "consensus_engine"
        assert settings.db_user == "postgres"
        assert settings.db_host == "localhost"
        assert settings.db_port == 5432
        assert settings.db_iam_auth is False
        assert settings.db_pool_size == 5
        assert settings.db_max_overflow == 10
        assert settings.db_pool_timeout == 30
        assert settings.db_pool_recycle == 3600

    def test_database_url_with_password(self, local_db_settings):
        """Test database URL generation with password."""
        url = local_db_settings.database_url

        assert "postgresql+psycopg://" in url
        assert "test_user:test_pass" in url
        assert "localhost:5432" in url
        assert "test_db" in url

    def test_database_url_without_password(self, clean_env, monkeypatch):
        """Test database URL generation without password."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")
        monkeypatch.setenv("DB_NAME", "test_db")
        monkeypatch.setenv("DB_USER", "test_user")
        monkeypatch.setenv("DB_HOST", "localhost")

        settings = get_settings()
        url = settings.database_url

        assert "postgresql+psycopg://" in url
        assert "test_user@localhost" in url
        assert "test_db" in url
        assert ":" not in url.split("@")[0].split("//")[1]  # No password in URL

    def test_cloud_sql_connection_name_validation(self, clean_env, monkeypatch):
        """Test Cloud SQL connection name format validation."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")

        # Valid format
        monkeypatch.setenv("DB_INSTANCE_CONNECTION_NAME", "project:region:instance")
        settings = get_settings()
        assert settings.db_instance_connection_name == "project:region:instance"

        # Invalid format should raise error
        get_settings.cache_clear()
        monkeypatch.setenv("DB_INSTANCE_CONNECTION_NAME", "invalid-format")

        with pytest.raises(Exception):  # ValidationError from pydantic
            get_settings()

    def test_safe_dict_masks_password(self, local_db_settings):
        """Test that get_safe_dict masks database password."""
        safe_dict = local_db_settings.get_safe_dict()

        assert safe_dict["db_password"] == "***MASKED***"
        assert safe_dict["openai_api_key"].startswith("***")


class TestEngineCreation:
    """Test database engine creation."""

    @patch("consensus_engine.db.create_engine")
    def test_create_local_engine(self, mock_create_engine, local_db_settings):
        """Test creating a local database engine."""
        mock_engine = MagicMock(spec=Engine)
        # Add pool attribute to avoid event listener issues
        mock_engine.pool = MagicMock()
        mock_create_engine.return_value = mock_engine

        engine = create_engine_from_settings(local_db_settings)

        assert engine == mock_engine
        mock_create_engine.assert_called_once()

        # Verify connection parameters
        call_args = mock_create_engine.call_args
        assert "postgresql+psycopg://" in call_args[0][0]
        assert call_args[1]["pool_size"] == 5
        assert call_args[1]["max_overflow"] == 10
        assert call_args[1]["pool_timeout"] == 30
        assert call_args[1]["pool_recycle"] == 3600
        assert call_args[1]["pool_pre_ping"] is True

    @patch("consensus_engine.db.create_engine")
    @patch("consensus_engine.db.get_connector")
    def test_create_cloud_sql_engine(
        self, mock_get_connector, mock_create_engine, cloud_sql_settings
    ):
        """Test creating a Cloud SQL engine."""
        mock_connector = MagicMock()
        mock_get_connector.return_value = mock_connector
        mock_engine = MagicMock(spec=Engine)
        # Add pool attribute to avoid event listener issues
        mock_engine.pool = MagicMock()
        mock_create_engine.return_value = mock_engine

        engine = create_engine_from_settings(cloud_sql_settings)

        assert engine == mock_engine
        mock_create_engine.assert_called_once()

        # Verify Cloud SQL parameters
        call_args = mock_create_engine.call_args
        assert call_args[0][0] == "postgresql+pg8000://"
        assert "creator" in call_args[1]
        assert "poolclass" in call_args[1]

    @patch("consensus_engine.db.create_engine")
    def test_create_engine_with_debug(self, mock_create_engine, local_db_settings):
        """Test that debug mode is passed to create_engine."""
        mock_engine = MagicMock(spec=Engine)
        # Add pool attribute to avoid event listener issues
        mock_engine.pool = MagicMock()
        mock_create_engine.return_value = mock_engine

        create_engine_from_settings(local_db_settings)

        call_args = mock_create_engine.call_args
        assert "echo" in call_args[1]
        assert call_args[1]["echo"] == local_db_settings.debug


class TestCloudSQLConnector:
    """Test Cloud SQL connector functionality."""

    def test_get_connector_creates_singleton(self):
        """Test that get_connector returns a singleton."""
        # Clean up any existing connector
        close_connector()

        with patch("consensus_engine.db.Connector") as mock_connector_class:
            mock_connector = MagicMock()
            mock_connector_class.return_value = mock_connector

            connector1 = get_connector()
            connector2 = get_connector()

            # Should only create one connector
            assert connector1 == connector2
            mock_connector_class.assert_called_once()

        # Clean up
        close_connector()

    def test_close_connector(self):
        """Test closing the Cloud SQL connector."""
        with patch("consensus_engine.db.Connector") as mock_connector_class:
            mock_connector = MagicMock()
            mock_connector_class.return_value = mock_connector

            # Get connector (creates it)
            get_connector()

            # Close it
            close_connector()

            mock_connector.close.assert_called_once()

            # Next call should create a new one
            get_connector()
            assert mock_connector_class.call_count == 2

        # Clean up
        close_connector()


class TestSessionManagement:
    """Test database session management."""

    def test_create_session_factory(self):
        """Test creating a session factory."""
        mock_engine = MagicMock(spec=Engine)

        factory = create_session_factory(mock_engine)

        assert factory is not None
        assert factory.kw["bind"] == mock_engine
        assert factory.kw["autocommit"] is False
        assert factory.kw["autoflush"] is False

    def test_get_session(self):
        """Test getting a session with automatic cleanup."""
        mock_session = MagicMock(spec=Session)

        # Create a mock factory that returns our mock session
        mock_factory = MagicMock(return_value=mock_session)

        # Use the session generator
        sessions = list(get_session(mock_factory))

        assert len(sessions) == 1
        # Verify factory was called
        mock_factory.assert_called_once()
        # Verify session was closed
        mock_session.close.assert_called_once()

    def test_get_session_closes_on_exception(self):
        """Test that session is closed even on exception."""
        mock_session = MagicMock(spec=Session)

        # Create a mock factory that returns our mock session
        mock_factory = MagicMock(return_value=mock_session)

        # Simulate exception during session use
        try:
            for session in get_session(mock_factory):
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Verify session was still closed
        mock_session.close.assert_called_once()


class TestDatabaseHealth:
    """Test database health checks."""

    def test_check_database_health_success(self):
        """Test successful database health check."""
        mock_engine = MagicMock(spec=Engine)
        mock_connection = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)

        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=False)
        mock_connection.execute.return_value = mock_result

        mock_engine.connect.return_value = mock_connection

        result = check_database_health(mock_engine)

        assert result is True
        mock_connection.execute.assert_called_once()

    def test_check_database_health_failure(self):
        """Test failed database health check."""
        mock_engine = MagicMock(spec=Engine)
        mock_engine.connect.side_effect = OperationalError("Connection failed", None, None)

        result = check_database_health(mock_engine)

        assert result is False

    def test_check_database_health_operational_error(self):
        """Test health check with operational error."""
        mock_engine = MagicMock(spec=Engine)
        mock_connection = MagicMock()

        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=False)
        mock_connection.execute.side_effect = OperationalError("Query failed", None, None)

        mock_engine.connect.return_value = mock_connection

        result = check_database_health(mock_engine)

        assert result is False


class TestBaseMetadata:
    """Test Base declarative metadata."""

    def test_base_exists(self):
        """Test that Base class exists and can be used."""
        assert Base is not None
        assert hasattr(Base, "metadata")

    def test_base_metadata(self):
        """Test that Base has proper metadata."""
        metadata = Base.metadata

        assert metadata is not None
        assert hasattr(metadata, "tables")
        assert hasattr(metadata, "create_all")
        assert hasattr(metadata, "drop_all")
