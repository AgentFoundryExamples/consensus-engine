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
"""Shared pytest fixtures and configuration for all tests.

This module provides reusable fixtures for mocking OpenAI responses,
settings configuration, and test utilities to ensure consistent
test behavior across unit and integration tests.
"""

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from consensus_engine.schemas.proposal import ExpandedProposal


@pytest.fixture
def mock_settings(monkeypatch: pytest.MonkeyPatch):
    """Fixture for creating mock settings with valid test environment variables.

    This fixture sets up a complete test environment with all required
    configuration values and clears the settings cache to ensure fresh state.

    Returns:
        Settings instance with test configuration
    """
    from consensus_engine.config.settings import Settings, get_settings

    # Clear the lru_cache for get_settings
    get_settings.cache_clear()

    # Set up valid test environment
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-fixtures")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.1")
    monkeypatch.setenv("TEMPERATURE", "0.7")
    monkeypatch.setenv("ENV", "testing")

    return Settings()


@pytest.fixture
def mock_openai_client():
    """Fixture for creating a mock OpenAI client wrapper.

    Returns a pre-configured MagicMock that simulates successful
    OpenAI API responses with structured outputs.

    Returns:
        MagicMock configured to return valid ExpandedProposal responses
    """
    mock_client = MagicMock()

    # Default successful response
    mock_proposal = ExpandedProposal(
        problem_statement="Test problem statement",
        proposed_solution="Test solution approach",
        assumptions=["Test assumption 1", "Test assumption 2"],
        scope_non_goals=["Test non-goal 1"],
        raw_expanded_proposal="Complete test proposal text",
    )
    mock_metadata = {
        "request_id": "test-request-id-123",
        "model": "gpt-5.1",
        "temperature": 0.7,
        "elapsed_time": 1.5,
        "finish_reason": "stop",
        "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
    }

    mock_client.create_structured_response.return_value = (mock_proposal, mock_metadata)

    return mock_client


@pytest.fixture
def mock_minimal_proposal() -> ExpandedProposal:
    """Fixture for a minimal valid ExpandedProposal.

    Returns:
        ExpandedProposal with only required fields populated
    """
    return ExpandedProposal(
        problem_statement="Minimal problem",
        proposed_solution="Minimal solution",
    )


@pytest.fixture
def mock_full_proposal() -> ExpandedProposal:
    """Fixture for a complete ExpandedProposal with all fields.

    Returns:
        ExpandedProposal with all fields populated
    """
    return ExpandedProposal(
        problem_statement="Comprehensive problem statement",
        proposed_solution="Detailed solution approach",
        assumptions=["Assumption 1", "Assumption 2", "Assumption 3"],
        scope_non_goals=["Non-goal 1", "Non-goal 2"],
        raw_expanded_proposal="Full detailed proposal text with additional context",
    )


@pytest.fixture
def sample_metadata() -> dict[str, Any]:
    """Fixture for sample request metadata.

    Returns:
        Dictionary containing typical metadata fields
    """
    return {
        "request_id": "test-request-abc123",
        "model": "gpt-5.1",
        "temperature": 0.7,
        "elapsed_time": 2.3,
        "finish_reason": "stop",
        "usage": {
            "prompt_tokens": 150,
            "completion_tokens": 250,
            "total_tokens": 400,
        },
    }


@pytest.fixture
def valid_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up valid test environment for integration tests.

    This fixture configures environment variables and clears caches
    to ensure a clean test environment for integration tests.
    """
    from consensus_engine.config import get_settings

    get_settings.cache_clear()

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-integration-tests")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.1")
    monkeypatch.setenv("TEMPERATURE", "0.7")
    monkeypatch.setenv("ENV", "testing")


@pytest.fixture
def test_client(valid_test_env: None) -> Generator[TestClient, None, None]:
    """Create FastAPI test client with valid configuration.

    This fixture creates a TestClient instance with proper environment
    configuration and yields it for use in integration tests.

    Yields:
        TestClient instance for making test requests
    """
    from consensus_engine.app import create_app
    from consensus_engine.config import get_settings

    get_settings.cache_clear()

    app = create_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clean all environment variables for isolated tests.

    This fixture removes all application environment variables
    and clears the settings cache to ensure test isolation.
    """
    from consensus_engine.config import get_settings

    get_settings.cache_clear()

    env_vars = [
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "TEMPERATURE",
        "ENV",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)
