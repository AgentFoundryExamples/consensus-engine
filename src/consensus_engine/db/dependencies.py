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
"""Database dependency injection for FastAPI routes.

This module provides dependency functions for database sessions that can be
used with FastAPI's dependency injection system without circular imports.
"""

from collections.abc import Generator

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Global state for database engine and session factory
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def set_engine(engine: Engine) -> None:
    """Set the global database engine.

    Args:
        engine: SQLAlchemy Engine instance
    """
    global _engine
    _engine = engine


def set_session_factory(factory: sessionmaker[Session]) -> None:
    """Set the global session factory.

    Args:
        factory: SQLAlchemy session factory
    """
    global _session_factory
    _session_factory = factory


def get_engine() -> Engine | None:
    """Get the global database engine.

    Returns:
        Engine instance or None if not initialized
    """
    return _engine


def get_session_factory() -> sessionmaker[Session] | None:
    """Get the global session factory.

    Returns:
        Session factory or None if not initialized
    """
    return _session_factory


def cleanup() -> None:
    """Clean up database resources."""
    global _engine, _session_factory
    if _engine:
        _engine.dispose()
        _engine = None
        _session_factory = None


def get_db_session() -> Generator[Session, None, None]:
    """Dependency function to get a database session.

    This function is used with FastAPI's dependency injection system
    to provide database sessions to route handlers.

    Note: Does NOT auto-commit. The route handler is responsible for 
    committing or rolling back the transaction as appropriate.

    Yields:
        Database session

    Raises:
        RuntimeError: If database session factory is not initialized
    """
    if _session_factory is None:
        raise RuntimeError("Database session factory not initialized")

    session = _session_factory()
    try:
        yield session
    finally:
        session.close()
