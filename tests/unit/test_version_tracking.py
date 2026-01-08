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
"""Unit tests for version tracking in runs and step progress."""

import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from consensus_engine.db.models import Run, RunPriority, RunStatus, RunType, StepProgress, StepStatus
from consensus_engine.db.repositories import RunRepository, StepProgressRepository


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = MagicMock(spec=Session)
    return session


def test_create_run_with_versions(mock_session):
    """Test creating a run with schema and prompt versions."""
    run_id = uuid.uuid4()
    schema_version = "1.0.0"
    prompt_set_version = "1.0.0"
    
    # Create run with version metadata
    run = RunRepository.create_run(
        session=mock_session,
        run_id=run_id,
        input_idea="Test idea",
        extra_context=None,
        run_type=RunType.INITIAL,
        model="gpt-5.1",
        temperature=0.7,
        parameters_json={},
        schema_version=schema_version,
        prompt_set_version=prompt_set_version,
    )
    
    # Verify versions are set
    assert run.schema_version == schema_version
    assert run.prompt_set_version == prompt_set_version
    assert run.id == run_id
    
    # Verify session.add was called
    mock_session.add.assert_called_once_with(run)


def test_create_run_without_versions(mock_session):
    """Test creating a run without version metadata (backward compatibility)."""
    run_id = uuid.uuid4()
    
    # Create run without version metadata
    run = RunRepository.create_run(
        session=mock_session,
        run_id=run_id,
        input_idea="Test idea",
        extra_context=None,
        run_type=RunType.INITIAL,
        model="gpt-5.1",
        temperature=0.7,
        parameters_json={},
    )
    
    # Verify versions are None (backward compatible)
    assert run.schema_version is None
    assert run.prompt_set_version is None
    assert run.id == run_id
    
    # Verify session.add was called
    mock_session.add.assert_called_once_with(run)


def test_upsert_step_progress_with_metadata(mock_session):
    """Test creating step progress with metadata."""
    run_id = uuid.uuid4()
    step_name = "expand"
    step_metadata = {
        "schema_version": "1.0.0",
        "prompt_set_version": "1.0.0",
        "model": "gpt-5.1",
        "temperature": 0.7,
    }
    
    # Mock the query to return no existing step
    mock_session.execute.return_value.scalar_one_or_none.return_value = None
    
    # Create step progress with metadata
    step_progress = StepProgressRepository.upsert_step_progress(
        session=mock_session,
        run_id=run_id,
        step_name=step_name,
        status=StepStatus.RUNNING,
        step_metadata=step_metadata,
    )
    
    # Verify metadata is set
    assert step_progress.step_metadata == step_metadata
    assert step_progress.run_id == run_id
    assert step_progress.step_name == step_name
    assert step_progress.status == StepStatus.RUNNING
    
    # Verify session.add and flush were called
    mock_session.add.assert_called_once_with(step_progress)
    mock_session.flush.assert_called_once()


def test_upsert_step_progress_update_metadata(mock_session):
    """Test updating existing step progress with new metadata."""
    run_id = uuid.uuid4()
    step_name = "review_architect"
    
    # Create existing step progress
    existing_step = StepProgress(
        run_id=run_id,
        step_name=step_name,
        step_order=1,
        status=StepStatus.PENDING,
        step_metadata={"old_key": "old_value"},
    )
    
    # Mock the query to return existing step
    mock_session.execute.return_value.scalar_one_or_none.return_value = existing_step
    
    new_metadata = {
        "schema_version": "1.0.0",
        "prompt_set_version": "1.0.0",
        "model": "gpt-5.1",
    }
    
    # Update step progress with new metadata
    updated_step = StepProgressRepository.upsert_step_progress(
        session=mock_session,
        run_id=run_id,
        step_name=step_name,
        status=StepStatus.RUNNING,
        step_metadata=new_metadata,
    )
    
    # Verify metadata is updated
    assert updated_step.step_metadata == new_metadata
    assert updated_step.status == StepStatus.RUNNING
    
    # Verify flush was called (update, not add)
    mock_session.flush.assert_called_once()
    mock_session.add.assert_not_called()


def test_step_progress_without_metadata(mock_session):
    """Test creating step progress without metadata (backward compatibility)."""
    run_id = uuid.uuid4()
    step_name = "aggregate_decision"
    
    # Mock the query to return no existing step
    mock_session.execute.return_value.scalar_one_or_none.return_value = None
    
    # Create step progress without metadata
    step_progress = StepProgressRepository.upsert_step_progress(
        session=mock_session,
        run_id=run_id,
        step_name=step_name,
        status=StepStatus.COMPLETED,
    )
    
    # Verify metadata is None (backward compatible)
    assert step_progress.step_metadata is None
    assert step_progress.run_id == run_id
    assert step_progress.step_name == step_name
    
    # Verify session.add and flush were called
    mock_session.add.assert_called_once_with(step_progress)
    mock_session.flush.assert_called_once()
