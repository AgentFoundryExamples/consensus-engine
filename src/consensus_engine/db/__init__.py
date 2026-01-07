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
"""Database module for Consensus Engine.

This module provides SQLAlchemy engine and session management with support for:
- Local PostgreSQL connections via standard DSN
- Cloud SQL connections via Cloud SQL Python Connector with IAM authentication
- Connection pooling with configurable parameters
- Health checks and connection validation
"""

import logging
from collections.abc import Generator
from typing import Any

from google.cloud.sql.connector import Connector
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from consensus_engine.config.settings import Settings

logger = logging.getLogger(__name__)

# Base class for declarative models
Base = declarative_base()

# Global connector instance for Cloud SQL
_connector: Connector | None = None


def get_connector() -> Connector:
    """Get or create the global Cloud SQL Connector instance.

    Returns:
        Connector instance for Cloud SQL connections

    Note:
        The connector is created once and reused for all connections.
        It should be closed when the application shuts down.
    """
    global _connector
    if _connector is None:
        _connector = Connector()
    return _connector


def close_connector() -> None:
    """Close the global Cloud SQL Connector instance.

    This should be called during application shutdown to clean up resources.
    """
    global _connector
    if _connector is not None:
        _connector.close()
        _connector = None
        logger.info("Cloud SQL Connector closed")


def get_cloud_sql_connection(
    settings: Settings,
) -> Any:
    """Create a connection to Cloud SQL using the Python Connector.

    Args:
        settings: Application settings with database configuration

    Returns:
        Database connection object (pg8000 connection)

    Raises:
        ValueError: If required Cloud SQL configuration is missing
        Exception: If connection fails
    """
    if not settings.db_instance_connection_name:
        raise ValueError(
            "DB_INSTANCE_CONNECTION_NAME is required when USE_CLOUD_SQL_CONNECTOR is true"
        )

    connector = get_connector()

    try:
        # Use IAM authentication if enabled
        if settings.db_iam_auth:
            logger.info(
                f"Connecting to Cloud SQL instance {settings.db_instance_connection_name} "
                f"with IAM authentication for user {settings.db_user}"
            )
            conn = connector.connect(
                settings.db_instance_connection_name,
                "pg8000",
                user=settings.db_user,
                db=settings.db_name,
                enable_iam_auth=True,
            )
        else:
            # Use password authentication
            if not settings.db_password:
                raise ValueError(
                    "DB_PASSWORD is required when DB_IAM_AUTH is false with Cloud SQL Connector"
                )
            logger.info(
                f"Connecting to Cloud SQL instance {settings.db_instance_connection_name} "
                f"with password authentication for user {settings.db_user}"
            )
            conn = connector.connect(
                settings.db_instance_connection_name,
                "pg8000",
                user=settings.db_user,
                password=settings.db_password,
                db=settings.db_name,
            )

        logger.info("Successfully connected to Cloud SQL instance")
        return conn

    except Exception as e:
        logger.error(
            f"Failed to connect to Cloud SQL instance "
            f"{settings.db_instance_connection_name}: {e}",
            exc_info=True,
        )
        raise


def create_engine_from_settings(settings: Settings) -> Engine:
    """Create a SQLAlchemy engine from application settings.

    This function supports two connection modes:
    1. Local/standard PostgreSQL connection via DSN (USE_CLOUD_SQL_CONNECTOR=false)
    2. Cloud SQL connection via Python Connector (USE_CLOUD_SQL_CONNECTOR=true)

    Args:
        settings: Application settings with database configuration

    Returns:
        Configured SQLAlchemy Engine instance

    Raises:
        ValueError: If required configuration is missing
        Exception: If engine creation fails
    """
    try:
        if settings.use_cloud_sql_connector:
            logger.info("Creating engine with Cloud SQL Python Connector")

            # Use NullPool with Cloud SQL Connector as it manages connections
            engine = create_engine(
                "postgresql+pg8000://",
                creator=lambda: get_cloud_sql_connection(settings),
                poolclass=NullPool,
                echo=settings.debug,
            )
        else:
            logger.info(f"Creating engine with standard DSN connection to {settings.db_host}")

            # Use standard connection pooling for local connections
            engine = create_engine(
                settings.database_url,
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_timeout=settings.db_pool_timeout,
                pool_recycle=settings.db_pool_recycle,
                pool_pre_ping=True,  # Verify connections before using them
                echo=settings.debug,
            )

        # Add connection event listeners for logging
        @event.listens_for(engine, "connect")
        def receive_connect(dbapi_conn: Any, connection_record: Any) -> None:
            """Log database connections."""
            logger.debug("Database connection established")

        @event.listens_for(engine, "close")
        def receive_close(dbapi_conn: Any, connection_record: Any) -> None:
            """Log database connection closures."""
            logger.debug("Database connection closed")

        logger.info("Database engine created successfully")
        return engine

    except Exception as e:
        logger.error(f"Failed to create database engine: {e}", exc_info=True)
        raise


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory from a SQLAlchemy engine.

    Args:
        engine: SQLAlchemy Engine instance

    Returns:
        Session factory for creating database sessions
    """
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """Get a database session with automatic cleanup.

    This is a generator function that yields a session and ensures
    it is properly closed after use, even if an exception occurs.

    Args:
        session_factory: Session factory for creating sessions

    Yields:
        Database session

    Example:
        >>> factory = create_session_factory(engine)
        >>> for session in get_session(factory):
        ...     # Use session
        ...     session.query(Model).all()
    """
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def check_database_health(engine: Engine) -> bool:
    """Check if the database is reachable and healthy.

    Args:
        engine: SQLAlchemy Engine instance

    Returns:
        True if database is healthy, False otherwise
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        logger.info("Database health check passed")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        return False


__all__ = [
    "Base",
    "create_engine_from_settings",
    "create_session_factory",
    "get_session",
    "check_database_health",
    "get_connector",
    "close_connector",
]
