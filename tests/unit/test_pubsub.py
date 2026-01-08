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
"""Unit tests for Pub/Sub publisher client."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from google.api_core.exceptions import GoogleAPIError

from consensus_engine.clients.pubsub import (
    MockPubSubPublisher,
    PubSubPublishError,
    PubSubPublisher,
    get_publisher,
)
from consensus_engine.config.settings import Settings


class TestMockPubSubPublisher:
    """Test suite for MockPubSubPublisher."""

    def test_mock_publisher_init(self):
        """Test MockPubSubPublisher initialization."""
        settings = Settings(
            openai_api_key="test-key",
            pubsub_use_mock=True,
            pubsub_topic="test-topic",
        )
        publisher = MockPubSubPublisher(settings)
        assert publisher.topic_name == "test-topic"

    def test_mock_publisher_publish_success(self):
        """Test MockPubSubPublisher.publish returns run_id."""
        settings = Settings(
            openai_api_key="test-key",
            pubsub_use_mock=True,
            pubsub_topic="test-topic",
        )
        publisher = MockPubSubPublisher(settings)
        
        run_id = "test-run-id-123"
        message_id = publisher.publish(
            run_id=run_id,
            run_type="initial",
            priority="normal",
            payload={"idea": "test idea"},
        )
        
        assert message_id == run_id

    def test_mock_publisher_close(self):
        """Test MockPubSubPublisher.close is a no-op."""
        settings = Settings(
            openai_api_key="test-key",
            pubsub_use_mock=True,
            pubsub_topic="test-topic",
        )
        publisher = MockPubSubPublisher(settings)
        publisher.close()  # Should not raise


class TestPubSubPublisher:
    """Test suite for PubSubPublisher."""

    def test_publisher_init_with_project_id(self):
        """Test PubSubPublisher initialization with project_id."""
        settings = Settings(
            openai_api_key="test-key",
            pubsub_project_id="test-project",
            pubsub_topic="test-topic",
        )
        
        with patch("consensus_engine.clients.pubsub.pubsub_v1.PublisherClient") as mock_client:
            mock_instance = Mock()
            mock_instance.topic_path.return_value = "projects/test-project/topics/test-topic"
            mock_client.return_value = mock_instance
            
            publisher = PubSubPublisher(settings)
            
            assert publisher.project_id == "test-project"
            assert publisher.topic_name == "test-topic"
            mock_instance.topic_path.assert_called_once_with("test-project", "test-topic")

    def test_publisher_init_with_emulator(self):
        """Test PubSubPublisher initialization with emulator."""
        settings = Settings(
            openai_api_key="test-key",
            pubsub_project_id=None,
            pubsub_topic="test-topic",
            pubsub_emulator_host="localhost:8085",
        )
        
        with patch("consensus_engine.clients.pubsub.pubsub_v1.PublisherClient") as mock_client:
            mock_instance = Mock()
            mock_instance.topic_path.return_value = "projects/emulator-project/topics/test-topic"
            mock_client.return_value = mock_instance
            
            publisher = PubSubPublisher(settings)
            
            # Should use default project_id for emulator
            assert publisher.project_id == "emulator-project"
            assert publisher.topic_name == "test-topic"

    def test_publisher_init_without_project_id_fails(self):
        """Test PubSubPublisher initialization fails without project_id in production."""
        settings = Settings(
            openai_api_key="test-key",
            pubsub_project_id=None,
            pubsub_topic="test-topic",
            pubsub_emulator_host=None,
        )
        
        with pytest.raises(ValueError, match="PUBSUB_PROJECT_ID is required"):
            PubSubPublisher(settings)

    def test_publisher_publish_success(self):
        """Test PubSubPublisher.publish successful message."""
        settings = Settings(
            openai_api_key="test-key",
            pubsub_project_id="test-project",
            pubsub_topic="test-topic",
        )
        
        with patch("consensus_engine.clients.pubsub.pubsub_v1.PublisherClient") as mock_client:
            mock_instance = Mock()
            mock_instance.topic_path.return_value = "projects/test-project/topics/test-topic"
            
            # Mock future.result() to return message_id
            mock_future = Mock()
            mock_future.result.return_value = "message-id-123"
            mock_instance.publish.return_value = mock_future
            
            mock_client.return_value = mock_instance
            
            publisher = PubSubPublisher(settings)
            
            run_id = "test-run-id-123"
            message_id = publisher.publish(
                run_id=run_id,
                run_type="initial",
                priority="normal",
                payload={"idea": "test idea"},
            )
            
            assert message_id == "message-id-123"
            
            # Verify publish was called with correct arguments
            call_args = mock_instance.publish.call_args
            assert call_args[0][0] == "projects/test-project/topics/test-topic"
            
            # Verify message content
            message_bytes = call_args[0][1]
            message_data = json.loads(message_bytes.decode("utf-8"))
            assert message_data["run_id"] == run_id
            assert message_data["run_type"] == "initial"
            assert message_data["priority"] == "normal"
            assert message_data["payload"]["idea"] == "test idea"
            
            # Verify attributes
            assert call_args[1]["run_id"] == run_id
            assert call_args[1]["run_type"] == "initial"
            assert call_args[1]["priority"] == "normal"

    def test_publisher_publish_google_api_error(self):
        """Test PubSubPublisher.publish handles GoogleAPIError."""
        settings = Settings(
            openai_api_key="test-key",
            pubsub_project_id="test-project",
            pubsub_topic="test-topic",
        )
        
        with patch("consensus_engine.clients.pubsub.pubsub_v1.PublisherClient") as mock_client:
            mock_instance = Mock()
            mock_instance.topic_path.return_value = "projects/test-project/topics/test-topic"
            
            # Mock future.result() to raise GoogleAPIError
            mock_future = Mock()
            mock_future.result.side_effect = GoogleAPIError("Pub/Sub error")
            mock_instance.publish.return_value = mock_future
            
            mock_client.return_value = mock_instance
            
            publisher = PubSubPublisher(settings)
            
            with pytest.raises(PubSubPublishError, match="Failed to publish message to Pub/Sub"):
                publisher.publish(
                    run_id="test-run-id",
                    run_type="initial",
                    priority="normal",
                    payload={"idea": "test"},
                )

    def test_publisher_publish_unexpected_error(self):
        """Test PubSubPublisher.publish handles unexpected errors."""
        settings = Settings(
            openai_api_key="test-key",
            pubsub_project_id="test-project",
            pubsub_topic="test-topic",
        )
        
        with patch("consensus_engine.clients.pubsub.pubsub_v1.PublisherClient") as mock_client:
            mock_instance = Mock()
            mock_instance.topic_path.return_value = "projects/test-project/topics/test-topic"
            
            # Mock future.result() to raise unexpected error
            mock_future = Mock()
            mock_future.result.side_effect = RuntimeError("Unexpected error")
            mock_instance.publish.return_value = mock_future
            
            mock_client.return_value = mock_instance
            
            publisher = PubSubPublisher(settings)
            
            with pytest.raises(PubSubPublishError, match="Unexpected error publishing message"):
                publisher.publish(
                    run_id="test-run-id",
                    run_type="initial",
                    priority="normal",
                    payload={"idea": "test"},
                )

    def test_publisher_close(self):
        """Test PubSubPublisher.close."""
        settings = Settings(
            openai_api_key="test-key",
            pubsub_project_id="test-project",
            pubsub_topic="test-topic",
        )
        
        with patch("consensus_engine.clients.pubsub.pubsub_v1.PublisherClient") as mock_client:
            mock_instance = Mock()
            mock_instance.topic_path.return_value = "projects/test-project/topics/test-topic"
            mock_client.return_value = mock_instance
            
            publisher = PubSubPublisher(settings)
            publisher.close()  # Should not raise


class TestGetPublisher:
    """Test suite for get_publisher factory function."""

    def test_get_publisher_mock_mode(self):
        """Test get_publisher returns MockPubSubPublisher when use_mock=True."""
        settings = Settings(
            openai_api_key="test-key",
            pubsub_use_mock=True,
            pubsub_topic="test-topic",
        )
        
        publisher = get_publisher(settings)
        assert isinstance(publisher, MockPubSubPublisher)

    def test_get_publisher_production_mode(self):
        """Test get_publisher returns PubSubPublisher when use_mock=False."""
        settings = Settings(
            openai_api_key="test-key",
            pubsub_use_mock=False,
            pubsub_project_id="test-project",
            pubsub_topic="test-topic",
        )
        
        with patch("consensus_engine.clients.pubsub.pubsub_v1.PublisherClient") as mock_client:
            mock_instance = Mock()
            mock_instance.topic_path.return_value = "projects/test-project/topics/test-topic"
            mock_client.return_value = mock_instance
            
            publisher = get_publisher(settings)
            assert isinstance(publisher, PubSubPublisher)
