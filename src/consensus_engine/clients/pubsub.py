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
"""Google Cloud Pub/Sub publisher client for job enqueueing.

This module provides a PubSubPublisher class for publishing job messages to
Google Cloud Pub/Sub. It supports:
- Production mode with Application Default Credentials (ADC)
- Local development with service account credentials
- Emulator mode for testing
- Mock mode for testing without Pub/Sub
- Retry logic with exponential backoff
- Structured logging of publish events
"""

import json
import os
import time
from typing import Any

from google.api_core import retry
from google.api_core.exceptions import GoogleAPIError
from google.cloud import pubsub_v1

from consensus_engine.config.logging import get_logger
from consensus_engine.config.settings import Settings

logger = get_logger(__name__)

# Pub/Sub publish timeout and warning threshold
PUBLISH_TIMEOUT_SECONDS = 30.0
PUBLISH_LATENCY_WARNING_MS = 30000  # Log warning if publish takes > 30s


class PubSubPublishError(Exception):
    """Exception raised when message publishing fails after retries."""

    def __init__(self, message: str, original_error: Exception | None = None):
        """Initialize PubSubPublishError.

        Args:
            message: Error message
            original_error: Original exception that caused the error
        """
        super().__init__(message)
        self.original_error = original_error


class MockPubSubPublisher:
    """Mock Pub/Sub publisher for testing without real Pub/Sub.

    This publisher logs messages instead of sending them to Pub/Sub.
    Useful for local development and testing without credentials or emulator.
    """

    def __init__(self, settings: Settings):
        """Initialize mock publisher.

        Args:
            settings: Application settings
        """
        self.topic_name = settings.pubsub_topic
        logger.info(
            "Initialized MockPubSubPublisher (no messages will be sent to Pub/Sub)",
            extra={"topic": self.topic_name, "mode": "mock"},
        )

    def publish(
        self,
        run_id: str,
        run_type: str,
        priority: str,
        payload: dict[str, Any],
    ) -> str:
        """Mock publish that logs the message instead of sending.

        Args:
            run_id: UUID of the run
            run_type: Type of run ('initial' or 'revision')
            priority: Priority level ('normal' or 'high')
            payload: Sanitized request payload

        Returns:
            Mock message ID (run_id)
        """
        message_data = {
            "run_id": run_id,
            "run_type": run_type,
            "priority": priority,
            "payload": payload,
        }

        logger.info(
            "Mock publish: message logged but not sent to Pub/Sub",
            extra={
                "run_id": run_id,
                "run_type": run_type,
                "priority": priority,
                "topic": self.topic_name,
                "mode": "mock",
                "message_size_bytes": len(json.dumps(message_data)),
            },
        )

        return run_id

    def close(self) -> None:
        """Close the mock publisher (no-op)."""
        logger.debug("Closing MockPubSubPublisher")


class PubSubPublisher:
    """Google Cloud Pub/Sub publisher for enqueueing job messages.

    This class handles publishing job messages to Pub/Sub with:
    - Automatic retry with exponential backoff
    - Structured logging of publish events and latency
    - Support for emulator and production modes
    - Graceful error handling and reporting
    """

    def __init__(self, settings: Settings):
        """Initialize Pub/Sub publisher client.

        Args:
            settings: Application settings with Pub/Sub configuration

        Raises:
            ValueError: If project_id is missing in production mode
        """
        self.settings = settings
        self.topic_name = settings.pubsub_topic

        # Check if using emulator
        if settings.pubsub_emulator_host:
            os.environ["PUBSUB_EMULATOR_HOST"] = settings.pubsub_emulator_host
            logger.info(
                f"Using Pub/Sub emulator at {settings.pubsub_emulator_host}",
                extra={"emulator_host": settings.pubsub_emulator_host},
            )
            # For emulator, project_id can be any non-empty string
            self.project_id = settings.pubsub_project_id or "emulator-project"
        else:
            # Production mode - project_id is required
            if not settings.pubsub_project_id:
                raise ValueError(
                    "PUBSUB_PROJECT_ID is required when not using emulator or mock mode"
                )
            self.project_id = settings.pubsub_project_id

        # Initialize publisher client with credentials if provided
        if settings.pubsub_credentials_file and not settings.pubsub_emulator_host:
            logger.info(
                f"Using service account credentials from {settings.pubsub_credentials_file}",
                extra={"credentials_file": settings.pubsub_credentials_file},
            )
            # Credentials file will be picked up automatically by the client library
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.pubsub_credentials_file

        self.client = pubsub_v1.PublisherClient()
        self.topic_path = self.client.topic_path(self.project_id, self.topic_name)

        logger.info(
            "Initialized PubSubPublisher",
            extra={
                "project_id": self.project_id,
                "topic": self.topic_name,
                "topic_path": self.topic_path,
                "emulator_mode": settings.pubsub_emulator_host is not None,
            },
        )

    def publish(
        self,
        run_id: str,
        run_type: str,
        priority: str,
        payload: dict[str, Any],
    ) -> str:
        """Publish a job message to Pub/Sub.

        This method publishes a message with automatic retry using exponential backoff.
        It logs the publish event and latency, and raises PubSubPublishError if
        publishing fails after retries.

        Args:
            run_id: UUID of the run
            run_type: Type of run ('initial' or 'revision')
            priority: Priority level ('normal' or 'high')
            payload: Sanitized request payload

        Returns:
            Message ID from Pub/Sub

        Raises:
            PubSubPublishError: If publishing fails after retries
        """
        start_time = time.time()

        # Construct message data
        message_data = {
            "run_id": run_id,
            "run_type": run_type,
            "priority": priority,
            "payload": payload,
        }

        # Serialize to JSON
        message_bytes = json.dumps(message_data).encode("utf-8")
        message_size_bytes = len(message_bytes)

        logger.info(
            "Publishing job message to Pub/Sub",
            extra={
                "run_id": run_id,
                "run_type": run_type,
                "priority": priority,
                "topic": self.topic_name,
                "message_size_bytes": message_size_bytes,
            },
        )

        try:
            # Publish with explicit retry configuration
            # Use exponential backoff with jitter for transient failures
            retry_config = retry.Retry(
                initial=1.0,  # Initial delay in seconds
                maximum=10.0,  # Maximum delay in seconds
                multiplier=2.0,  # Exponential backoff multiplier
                deadline=PUBLISH_TIMEOUT_SECONDS,  # Overall deadline
            )
            
            future = self.client.publish(
                self.topic_path,
                message_bytes,
                run_id=run_id,
                run_type=run_type,
                priority=priority,
                retry=retry_config,
            )

            # Wait for publish to complete (with timeout)
            message_id = future.result(timeout=PUBLISH_TIMEOUT_SECONDS)

            # Calculate publish latency
            publish_latency_ms = (time.time() - start_time) * 1000

            # Log warning if latency exceeds threshold (even though request succeeded)
            if publish_latency_ms > PUBLISH_LATENCY_WARNING_MS:
                logger.warning(
                    "Pub/Sub publish latency exceeded 30 seconds",
                    extra={
                        "run_id": run_id,
                        "run_type": run_type,
                        "priority": priority,
                        "publish_latency_ms": publish_latency_ms,
                        "message_id": message_id,
                    },
                )

            logger.info(
                "Job enqueued successfully",
                extra={
                    "run_id": run_id,
                    "run_type": run_type,
                    "priority": priority,
                    "message_id": message_id,
                    "publish_latency_ms": publish_latency_ms,
                    "lifecycle_event": "enqueued",
                },
            )

            return message_id

        except GoogleAPIError as e:
            publish_latency_ms = (time.time() - start_time) * 1000
            logger.error(
                "Failed to publish job message to Pub/Sub after retries",
                extra={
                    "run_id": run_id,
                    "run_type": run_type,
                    "priority": priority,
                    "publish_latency_ms": publish_latency_ms,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise PubSubPublishError(
                f"Failed to publish message to Pub/Sub: {str(e)}", original_error=e
            ) from e

        except Exception as e:
            publish_latency_ms = (time.time() - start_time) * 1000
            logger.error(
                "Unexpected error publishing job message to Pub/Sub",
                extra={
                    "run_id": run_id,
                    "run_type": run_type,
                    "priority": priority,
                    "publish_latency_ms": publish_latency_ms,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise PubSubPublishError(
                f"Unexpected error publishing message: {str(e)}", original_error=e
            ) from e

    def close(self) -> None:
        """Close the publisher client and release resources.

        This should be called when the publisher is no longer needed.
        """
        logger.info("Closing PubSubPublisher")
        # The publisher client doesn't need explicit cleanup in newer versions
        # but we keep this method for future compatibility


def get_publisher(settings: Settings) -> PubSubPublisher | MockPubSubPublisher:
    """Factory function to get the appropriate publisher based on settings.

    Args:
        settings: Application settings

    Returns:
        PubSubPublisher or MockPubSubPublisher instance
    """
    if settings.pubsub_use_mock:
        return MockPubSubPublisher(settings)
    else:
        return PubSubPublisher(settings)
