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
"""Integration tests for database functionality.

These tests require a running PostgreSQL instance.
They can be run against the Docker Compose database or a test database.
"""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Column, Integer, String, create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from consensus_engine.config import get_settings
from consensus_engine.db import (
    Base,
    check_database_health,
    create_engine_from_settings,
    create_session_factory,
    get_session,
)


# Skip integration tests if database is not available
def is_database_available():
    """Check if a test database is available."""
    try:
        test_url = os.getenv(
            "TEST_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
        )
        engine = create_engine(test_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


# Mark all tests in this module to be skipped if database is not available
pytestmark = pytest.mark.skipif(
    not is_database_available(), reason="Database not available for integration tests"
)


@pytest.fixture(scope="module")
def test_engine():
    """Create a test database engine."""
    test_url = os.getenv(
        "TEST_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
    )
    engine = create_engine(test_url, pool_pre_ping=True, echo=False)
    yield engine
    engine.dispose()


@pytest.fixture
def clean_database(test_engine):
    """Clean database before each test."""
    # Drop all tables
    Base.metadata.drop_all(test_engine)
    # Create all tables
    Base.metadata.create_all(test_engine)
    yield
    # Clean up after test
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def test_session_factory(test_engine):
    """Create a session factory for tests."""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def test_settings(monkeypatch):
    """Set up test settings with local database."""
    get_settings.cache_clear()

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123456789")
    monkeypatch.setenv("USE_CLOUD_SQL_CONNECTOR", "false")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "postgres")
    monkeypatch.setenv("DB_USER", "postgres")
    monkeypatch.setenv("DB_PASSWORD", "postgres")

    return get_settings()


class TestDatabaseConnection:
    """Test database connection establishment."""

    def test_create_engine_from_settings(self, test_settings):
        """Test creating an engine from settings."""
        engine = create_engine_from_settings(test_settings)

        assert engine is not None
        assert check_database_health(engine)

        engine.dispose()

    def test_database_health_check_success(self, test_engine):
        """Test successful database health check."""
        result = check_database_health(test_engine)

        assert result is True

    def test_database_health_check_failure(self):
        """Test health check with invalid connection."""
        # Create engine with invalid connection
        bad_engine = create_engine(
            "postgresql+psycopg://invalid:invalid@localhost:9999/invalid", pool_pre_ping=False
        )

        result = check_database_health(bad_engine)

        assert result is False

        bad_engine.dispose()

    def test_connection_pooling(self, test_settings):
        """Test that connection pooling works correctly."""
        engine = create_engine_from_settings(test_settings)

        # Create multiple connections
        connections = []
        for _ in range(3):
            conn = engine.connect()
            connections.append(conn)

        # Verify all connections work
        for conn in connections:
            result = conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1

        # Close all connections
        for conn in connections:
            conn.close()

        engine.dispose()


class TestSessionManagement:
    """Test session management and operations."""

    def test_create_session_factory_from_engine(self, test_engine):
        """Test creating a session factory."""
        factory = create_session_factory(test_engine)

        assert factory is not None

        # Create a session
        session = factory()
        assert session is not None

        # Verify session can execute queries
        result = session.execute(text("SELECT 1"))
        assert result.fetchone()[0] == 1

        session.close()

    def test_get_session_context_manager(self, test_session_factory):
        """Test session context manager."""
        session_used = None

        for session in get_session(test_session_factory):
            session_used = session
            result = session.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1

        # Session should be closed after context
        assert session_used is not None
        # Note: We can't easily test if session is closed without internal access

    def test_session_transaction_commit(self, clean_database, test_session_factory):
        """Test session transaction commit."""

        # Define a test model
        class TestModel(Base):
            __tablename__ = "test_model"
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        # Create table
        Base.metadata.create_all(bind=test_session_factory.kw["bind"])

        # Insert data
        for session in get_session(test_session_factory):
            test_obj = TestModel(name="test")
            session.add(test_obj)
            session.commit()

        # Verify data persists
        for session in get_session(test_session_factory):
            result = session.query(TestModel).filter_by(name="test").first()
            assert result is not None
            assert result.name == "test"

    def test_session_transaction_rollback(self, clean_database, test_session_factory):
        """Test session transaction rollback."""

        # Define a test model
        class TestModel(Base):
            __tablename__ = "test_model_rollback"
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        # Create table
        Base.metadata.create_all(bind=test_session_factory.kw["bind"])

        # Insert data but rollback
        for session in get_session(test_session_factory):
            test_obj = TestModel(name="test")
            session.add(test_obj)
            session.rollback()

        # Verify data was not persisted
        for session in get_session(test_session_factory):
            result = session.query(TestModel).filter_by(name="test").first()
            assert result is None


class TestAlembicMigrations:
    """Test Alembic migration functionality."""

    def test_alembic_config_exists(self):
        """Test that Alembic configuration exists."""
        alembic_ini_path = Path(__file__).parent.parent.parent / "alembic.ini"
        assert alembic_ini_path.exists()

    def test_migrations_directory_exists(self):
        """Test that migrations directory exists."""
        migrations_dir = Path(__file__).parent.parent.parent / "migrations"
        assert migrations_dir.exists()
        assert (migrations_dir / "env.py").exists()

    def test_initial_migration_exists(self):
        """Test that initial migration exists."""
        migrations_dir = Path(__file__).parent.parent.parent / "migrations" / "versions"
        assert migrations_dir.exists()

        # Check that at least one migration file exists
        migration_files = list(migrations_dir.glob("*.py"))
        assert len(migration_files) > 0

    def test_run_migrations_up_and_down(self, test_engine, test_settings, monkeypatch):
        """Test running migrations up and down."""
        # Set up test database URL
        monkeypatch.setenv(
            "TEST_DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/postgres",
        )

        # Get alembic config
        alembic_ini_path = Path(__file__).parent.parent.parent / "alembic.ini"
        alembic_cfg = Config(str(alembic_ini_path))

        # Set the database URL in the config
        alembic_cfg.set_main_option("sqlalchemy.url", test_settings.database_url)

        try:
            # Run migrations to head (upgrade)
            command.upgrade(alembic_cfg, "head")

            # Check alembic version table exists
            with test_engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT EXISTS (SELECT FROM information_schema.tables "
                        "WHERE table_name = 'alembic_version')"
                    )
                )
                assert result.fetchone()[0] is True

            # Downgrade one revision
            command.downgrade(alembic_cfg, "-1")

            # Verify alembic version table still exists (we only went back one migration)
            with test_engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT EXISTS (SELECT FROM information_schema.tables "
                        "WHERE table_name = 'alembic_version')"
                    )
                )
                # Table should still exist after downgrade of empty migration
                assert result.fetchone()[0] is True

        except (OperationalError, OSError) as e:
            # OperationalError: Database connection/query issues
            # OSError: File system or network issues
            pytest.skip(f"Migration test requires database connection: {e}")
        except Exception as e:
            # Re-raise unexpected errors to surface them properly
            pytest.fail(f"Unexpected error in migration test: {e}")


class TestDatabaseModels:
    """Test database model functionality."""

    def test_base_metadata(self, clean_database, test_engine):
        """Test Base metadata operations."""

        # Create a test model
        class TestModel(Base):
            __tablename__ = "test_metadata_model"
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        # Create tables
        Base.metadata.create_all(test_engine)

        # Verify table was created
        with test_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_name = 'test_metadata_model')"
                )
            )
            assert result.fetchone()[0] is True

        # Drop tables
        Base.metadata.drop_all(test_engine)

        # Verify table was dropped
        with test_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    "WHERE table_name = 'test_metadata_model')"
                )
            )
            assert result.fetchone()[0] is False
