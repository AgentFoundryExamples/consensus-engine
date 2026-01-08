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
"""Integration tests for version tracking in runs API.

These tests validate that version metadata is properly persisted and exposed
through the API endpoints.
"""

import os
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from consensus_engine.app import create_app
from consensus_engine.db import Base
from consensus_engine.db.dependencies import get_db_session
from consensus_engine.db.models import Run, RunPriority, RunStatus, RunType, StepProgress, StepStatus
from consensus_engine.db.repositories import RunRepository, StepProgressRepository


def is_database_available():
    """Check if a test database is available."""
    try:
        from sqlalchemy import text
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
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield
    Base.metadata.drop_all(test_engine)


@pytest.fixture
def test_session_factory(test_engine):
    """Create a session factory for tests."""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def test_client(test_session_factory, clean_database, monkeypatch):
    """Create a test client with database override."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-version-tracking")
    
    app = create_app()
    
    def override_get_db_session():
        session = test_session_factory()
        try:
            yield session
        finally:
            session.close()
    
    app.dependency_overrides[get_db_session] = override_get_db_session
    
    with TestClient(app) as client:
        yield client


def test_run_with_version_metadata_exposed_via_api(test_client, test_session_factory):
    """Test that run version metadata is exposed through API endpoint."""
    # Create a run with version metadata
    session = test_session_factory()
    try:
        run_id = uuid.uuid4()
        schema_version = "1.0.0"
        prompt_set_version = "1.0.0"
        
        run = RunRepository.create_run(
            session=session,
            run_id=run_id,
            input_idea="Test idea with versions",
            extra_context=None,
            run_type=RunType.INITIAL,
            model="gpt-5.1",
            temperature=0.7,
            parameters_json={},
            schema_version=schema_version,
            prompt_set_version=prompt_set_version,
        )
        session.commit()
        
        # Query the run via API
        response = test_client.get(f"/v1/runs/{run_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify version metadata is present in response
        assert data["schema_version"] == schema_version
        assert data["prompt_set_version"] == prompt_set_version
        assert data["run_id"] == str(run_id)
        
    finally:
        session.close()


def test_run_without_version_metadata_returns_defaults(test_client, test_session_factory):
    """Test that runs without version metadata return 'unknown' as defaults."""
    # Create a run without version metadata (historical data scenario)
    session = test_session_factory()
    try:
        run_id = uuid.uuid4()
        
        run = RunRepository.create_run(
            session=session,
            run_id=run_id,
            input_idea="Test idea without versions",
            extra_context=None,
            run_type=RunType.INITIAL,
            model="gpt-5.1",
            temperature=0.7,
            parameters_json={},
            # Not providing schema_version and prompt_set_version
        )
        session.commit()
        
        # Query the run via API
        response = test_client.get(f"/v1/runs/{run_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify default values are returned
        assert data["schema_version"] == "unknown"
        assert data["prompt_set_version"] == "unknown"
        assert data["run_id"] == str(run_id)
        
    finally:
        session.close()


def test_step_progress_with_metadata_persists(test_session_factory):
    """Test that step progress metadata is persisted correctly."""
    session = test_session_factory()
    try:
        run_id = uuid.uuid4()
        
        # Create a run
        run = RunRepository.create_run(
            session=session,
            run_id=run_id,
            input_idea="Test idea",
            extra_context=None,
            run_type=RunType.INITIAL,
            model="gpt-5.1",
            temperature=0.7,
            parameters_json={},
            schema_version="1.0.0",
            prompt_set_version="1.0.0",
        )
        session.commit()
        
        # Create step progress with metadata
        step_metadata = {
            "schema_version": "1.0.0",
            "prompt_set_version": "1.0.0",
            "model": "gpt-5.1",
            "temperature": 0.7,
        }
        
        step_progress = StepProgressRepository.upsert_step_progress(
            session=session,
            run_id=run_id,
            step_name="expand",
            status=StepStatus.COMPLETED,
            step_metadata=step_metadata,
        )
        session.commit()
        
        # Retrieve and verify
        retrieved_steps = StepProgressRepository.get_run_steps(session, run_id)
        assert len(retrieved_steps) == 1
        assert retrieved_steps[0].step_metadata == step_metadata
        assert retrieved_steps[0].step_name == "expand"
        
    finally:
        session.close()
