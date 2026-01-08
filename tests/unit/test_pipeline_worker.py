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
"""Unit tests for pipeline worker."""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from google.cloud import pubsub_v1
from pydantic import ValidationError

from consensus_engine.config.settings import Settings
from consensus_engine.db.models import (
    Run,
    RunPriority,
    RunStatus,
    RunType,
    StepProgress,
    StepStatus,
)
from consensus_engine.workers.pipeline_worker import JobMessage, PipelineWorker


class TestJobMessage:
    """Test suite for JobMessage validation."""

    def test_valid_message(self):
        """Test valid job message."""
        data = {
            "run_id": str(uuid.uuid4()),
            "run_type": "initial",
            "priority": "normal",
            "payload": {"idea": "test idea"},
        }
        msg = JobMessage(**data)
        assert msg.run_id == data["run_id"]
        assert msg.run_type == "initial"
        assert msg.priority == "normal"
        assert msg.payload == {"idea": "test idea"}

    def test_missing_required_field(self):
        """Test that missing required field raises ValidationError."""
        data = {
            "run_id": str(uuid.uuid4()),
            "run_type": "initial",
            # Missing priority
            "payload": {"idea": "test idea"},
        }
        with pytest.raises(ValidationError):
            JobMessage(**data)

    def test_revision_message(self):
        """Test revision job message."""
        data = {
            "run_id": str(uuid.uuid4()),
            "run_type": "revision",
            "priority": "high",
            "payload": {"edited_proposal": "updated proposal"},
        }
        msg = JobMessage(**data)
        assert msg.run_type == "revision"
        assert msg.priority == "high"


class TestPipelineWorker:
    """Test suite for PipelineWorker."""

    @pytest.fixture
    def settings(self, monkeypatch: pytest.MonkeyPatch) -> Settings:
        """Create test settings."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("PUBSUB_USE_MOCK", "true")
        monkeypatch.setenv("PUBSUB_EMULATOR_HOST", "localhost:8085")
        monkeypatch.setenv("PUBSUB_PROJECT_ID", "test-project")
        monkeypatch.setenv("PUBSUB_SUBSCRIPTION", "test-sub")
        return Settings()

    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    def test_worker_initialization(
        self, mock_subscriber_cls: MagicMock, mock_get_engine: MagicMock, settings: Settings
    ):
        """Test worker initialization."""
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine

        worker = PipelineWorker(settings)

        assert worker.settings == settings
        assert worker.project_id == "test-project"
        assert worker.should_stop is False
        mock_subscriber.subscription_path.assert_called_once_with("test-project", "test-sub")

    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    def test_validate_message_success(
        self, mock_subscriber_cls: MagicMock, mock_get_engine: MagicMock, settings: Settings
    ):
        """Test successful message validation."""
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        worker = PipelineWorker(settings)

        message_data = {
            "run_id": str(uuid.uuid4()),
            "run_type": "initial",
            "priority": "normal",
            "payload": {"idea": "test idea"},
        }

        job_msg = worker._validate_message(message_data)
        assert isinstance(job_msg, JobMessage)
        assert job_msg.run_id == message_data["run_id"]

    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    def test_validate_message_failure(
        self, mock_subscriber_cls: MagicMock, mock_get_engine: MagicMock, settings: Settings
    ):
        """Test message validation failure."""
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        worker = PipelineWorker(settings)

        message_data = {
            "run_id": str(uuid.uuid4()),
            "run_type": "initial",
            # Missing priority
            "payload": {"idea": "test idea"},
        }

        with pytest.raises(ValidationError):
            worker._validate_message(message_data)

    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    def test_check_idempotency_completed_run(
        self, mock_subscriber_cls: MagicMock, mock_get_engine: MagicMock, settings: Settings
    ):
        """Test idempotency check for completed run."""
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        worker = PipelineWorker(settings)

        # Mock session with execute method for SELECT FOR UPDATE
        mock_session = Mock()
        run_id = uuid.uuid4()
        mock_run = Mock(spec=Run)
        mock_run.id = run_id
        mock_run.status = RunStatus.COMPLETED
        
        # Mock the execute method to return a result with scalar_one_or_none
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_run
        mock_session.execute.return_value = mock_result

        should_skip, run = worker._check_idempotency(mock_session, run_id)
        assert should_skip is True
        assert run == mock_run

    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    def test_check_idempotency_queued_run(
        self, mock_subscriber_cls: MagicMock, mock_get_engine: MagicMock, settings: Settings
    ):
        """Test idempotency check for queued run."""
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        worker = PipelineWorker(settings)

        # Mock session with execute method
        mock_session = Mock()
        run_id = uuid.uuid4()
        mock_run = Mock(spec=Run)
        mock_run.id = run_id
        mock_run.status = RunStatus.QUEUED
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_run
        mock_session.execute.return_value = mock_result

        should_skip, run = worker._check_idempotency(mock_session, run_id)
        assert should_skip is False
        assert run == mock_run

    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    def test_check_idempotency_run_not_found(
        self, mock_subscriber_cls: MagicMock, mock_get_engine: MagicMock, settings: Settings
    ):
        """Test idempotency check when run not found."""
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        worker = PipelineWorker(settings)

        # Mock session with execute method returning None
        mock_session = Mock()
        run_id = uuid.uuid4()
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        should_skip, run = worker._check_idempotency(mock_session, run_id)
        assert should_skip is False
        assert run is None

    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    def test_transition_to_running(
        self, mock_subscriber_cls: MagicMock, mock_get_engine: MagicMock, settings: Settings
    ):
        """Test transitioning run to RUNNING status."""
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        worker = PipelineWorker(settings)

        # Mock session and run
        mock_session = Mock()
        mock_run = Mock(spec=Run)
        mock_run.id = uuid.uuid4()
        mock_run.status = RunStatus.QUEUED

        worker._transition_to_running(mock_session, mock_run)

        assert mock_run.status == RunStatus.RUNNING
        assert mock_run.started_at is not None
        assert mock_run.updated_at is not None
        mock_session.flush.assert_called_once()

    @patch("consensus_engine.workers.pipeline_worker.StepProgressRepository")
    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    def test_mark_step_started(
        self,
        mock_subscriber_cls: MagicMock,
        mock_get_engine: MagicMock,
        mock_step_repo: MagicMock,
        settings: Settings,
    ):
        """Test marking step as started."""
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        worker = PipelineWorker(settings)

        # Mock session
        mock_session = Mock()
        run_id = uuid.uuid4()

        worker._mark_step_started(mock_session, run_id, "expand")

        mock_step_repo.upsert_step_progress.assert_called_once()
        call_args = mock_step_repo.upsert_step_progress.call_args
        assert call_args[1]["run_id"] == run_id
        assert call_args[1]["step_name"] == "expand"
        assert call_args[1]["status"] == StepStatus.RUNNING
        mock_session.commit.assert_called_once()

    @patch("consensus_engine.workers.pipeline_worker.StepProgressRepository")
    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    def test_mark_step_completed(
        self,
        mock_subscriber_cls: MagicMock,
        mock_get_engine: MagicMock,
        mock_step_repo: MagicMock,
        settings: Settings,
    ):
        """Test marking step as completed."""
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        worker = PipelineWorker(settings)

        # Mock session
        mock_session = Mock()
        run_id = uuid.uuid4()

        worker._mark_step_completed(mock_session, run_id, "expand", 1000.0)

        mock_step_repo.upsert_step_progress.assert_called_once()
        call_args = mock_step_repo.upsert_step_progress.call_args
        assert call_args[1]["run_id"] == run_id
        assert call_args[1]["step_name"] == "expand"
        assert call_args[1]["status"] == StepStatus.COMPLETED
        mock_session.commit.assert_called_once()

    @patch("consensus_engine.workers.pipeline_worker.StepProgressRepository")
    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    def test_mark_step_failed(
        self,
        mock_subscriber_cls: MagicMock,
        mock_get_engine: MagicMock,
        mock_step_repo: MagicMock,
        settings: Settings,
    ):
        """Test marking step as failed."""
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        worker = PipelineWorker(settings)

        # Mock session
        mock_session = Mock()
        run_id = uuid.uuid4()
        error_msg = "Test error"

        worker._mark_step_failed(mock_session, run_id, "expand", error_msg, 1000.0)

        mock_step_repo.upsert_step_progress.assert_called_once()
        call_args = mock_step_repo.upsert_step_progress.call_args
        assert call_args[1]["run_id"] == run_id
        assert call_args[1]["step_name"] == "expand"
        assert call_args[1]["status"] == StepStatus.FAILED
        assert call_args[1]["error_message"] == error_msg
        mock_session.commit.assert_called_once()

    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    def test_message_callback_success(
        self, mock_subscriber_cls: MagicMock, mock_get_engine: MagicMock, settings: Settings
    ):
        """Test successful message callback."""
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        worker = PipelineWorker(settings)

        # Mock message
        mock_message = Mock(spec=pubsub_v1.subscriber.message.Message)
        run_id = str(uuid.uuid4())
        message_data = {
            "run_id": run_id,
            "run_type": "initial",
            "priority": "normal",
            "payload": {"idea": "test idea"},
        }
        mock_message.data = json.dumps(message_data).encode("utf-8")
        mock_message.message_id = "test-message-id"

        # Mock _process_job to do nothing
        with patch.object(worker, "_process_job"):
            worker._message_callback(mock_message)

        # Message should be acknowledged
        mock_message.ack.assert_called_once()

    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    def test_message_callback_invalid_schema(
        self, mock_subscriber_cls: MagicMock, mock_get_engine: MagicMock, settings: Settings
    ):
        """Test message callback with invalid schema."""
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        worker = PipelineWorker(settings)

        # Mock message with invalid schema
        mock_message = Mock(spec=pubsub_v1.subscriber.message.Message)
        message_data = {
            "run_id": str(uuid.uuid4()),
            # Missing required fields
        }
        mock_message.data = json.dumps(message_data).encode("utf-8")
        mock_message.message_id = "test-message-id"

        worker._message_callback(mock_message)

        # Message should be acknowledged (to remove from queue)
        mock_message.ack.assert_called_once()
        mock_message.nack.assert_not_called()

    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    def test_message_callback_processing_error(
        self, mock_subscriber_cls: MagicMock, mock_get_engine: MagicMock, settings: Settings
    ):
        """Test message callback with processing error."""
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        worker = PipelineWorker(settings)

        # Mock message
        mock_message = Mock(spec=pubsub_v1.subscriber.message.Message)
        run_id = str(uuid.uuid4())
        message_data = {
            "run_id": run_id,
            "run_type": "initial",
            "priority": "normal",
            "payload": {"idea": "test idea"},
        }
        mock_message.data = json.dumps(message_data).encode("utf-8")
        mock_message.message_id = "test-message-id"

        # Mock _process_job to raise error
        with patch.object(worker, "_process_job", side_effect=Exception("Test error")):
            worker._message_callback(mock_message)

        # Message should be nacked (for retry)
        mock_message.nack.assert_called_once()
        mock_message.ack.assert_not_called()


class TestWorkerIdempotencyAndRetries:
    """Test suite for worker idempotency and retry behavior."""

    @pytest.fixture
    def settings(self, monkeypatch: pytest.MonkeyPatch) -> Settings:
        """Create test settings."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("PUBSUB_USE_MOCK", "true")
        monkeypatch.setenv("PUBSUB_EMULATOR_HOST", "localhost:8085")
        monkeypatch.setenv("PUBSUB_PROJECT_ID", "test-project")
        monkeypatch.setenv("PUBSUB_SUBSCRIPTION", "test-sub")
        monkeypatch.setenv("WORKER_STEP_TIMEOUT_SECONDS", "300")
        monkeypatch.setenv("WORKER_JOB_TIMEOUT_SECONDS", "1800")
        return Settings()

    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    def test_step_timeout_configuration(
        self, mock_subscriber_cls: MagicMock, mock_get_engine: MagicMock, settings: Settings
    ):
        """Test that step timeouts are properly configured."""
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        worker = PipelineWorker(settings)

        # Verify timeout settings are properly loaded
        assert settings.worker_step_timeout_seconds == 300
        assert settings.worker_job_timeout_seconds == 1800

    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    def test_retry_count_tracking(
        self, mock_subscriber_cls: MagicMock, mock_get_engine: MagicMock, settings: Settings
    ):
        """Test that retry attempts are tracked per run."""
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        worker = PipelineWorker(settings)

        # Verify retry_counts dict is initialized
        assert isinstance(worker.retry_counts, dict)
        assert len(worker.retry_counts) == 0

        # Simulate tracking retry for a run
        run_id = str(uuid.uuid4())
        worker.retry_counts[run_id] = 1
        assert worker.retry_counts[run_id] == 1

        # Increment retry count
        worker.retry_counts[run_id] += 1
        assert worker.retry_counts[run_id] == 2

    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    def test_worker_initialization_settings(
        self, mock_subscriber_cls: MagicMock, mock_get_engine: MagicMock, settings: Settings
    ):
        """Test that worker initializes with correct settings."""
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        worker = PipelineWorker(settings)

        # Verify worker attributes
        assert worker.settings == settings
        assert worker.project_id == "test-project"
        assert worker.should_stop is False
        assert isinstance(worker.retry_counts, dict)

    @patch("consensus_engine.workers.pipeline_worker.get_engine")
    @patch("consensus_engine.workers.pipeline_worker.pubsub_v1.SubscriberClient")
    def test_worker_concurrency_configuration(
        self, mock_subscriber_cls: MagicMock, mock_get_engine: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        """Test that worker concurrency settings are configurable."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.setenv("PUBSUB_USE_MOCK", "true")
        monkeypatch.setenv("PUBSUB_PROJECT_ID", "test-project")
        monkeypatch.setenv("PUBSUB_SUBSCRIPTION", "test-sub")
        monkeypatch.setenv("WORKER_MAX_CONCURRENCY", "20")
        
        settings = Settings()
        
        mock_subscriber = Mock()
        mock_subscriber.subscription_path.return_value = "projects/test-project/subscriptions/test-sub"
        mock_subscriber_cls.return_value = mock_subscriber

        worker = PipelineWorker(settings)

        # Verify concurrency settings are properly loaded
        assert settings.worker_max_concurrency == 20
