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
from consensus_engine.schemas.review import PersonaReview


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
    from consensus_engine.config.settings import get_settings

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
    from consensus_engine.config.settings import get_settings

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
    from consensus_engine.config.settings import get_settings

    get_settings.cache_clear()

    env_vars = [
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "TEMPERATURE",
        "ENV",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)


# ==============================================================================
# Multi-Persona Review Fixtures
# ==============================================================================
# These fixtures provide reusable persona review payloads for testing the
# multi-persona consensus pipeline with various scenarios.


@pytest.fixture
def persona_review_architect_high_confidence() -> PersonaReview:
    """Fixture for Architect persona review with high confidence.

    Returns:
        PersonaReview with Architect persona at 0.85 confidence
    """
    from consensus_engine.schemas.review import BlockingIssue, Concern, PersonaReview

    return PersonaReview(
        persona_name="Architect",
        persona_id="architect",
        confidence_score=0.85,
        strengths=[
            "Well-structured system design",
            "Scalable architecture approach",
            "Clear separation of concerns",
        ],
        concerns=[
            Concern(text="Potential database performance bottleneck", is_blocking=False),
        ],
        recommendations=[
            "Consider adding caching layer",
            "Review database indexing strategy",
        ],
        blocking_issues=[],
        estimated_effort="3-4 weeks",
        dependency_risks=["Database migration complexity"],
    )


@pytest.fixture
def persona_review_critic_medium_confidence() -> PersonaReview:
    """Fixture for Critic persona review with medium confidence.

    Returns:
        PersonaReview with Critic persona at 0.70 confidence
    """
    from consensus_engine.schemas.review import Concern, PersonaReview

    return PersonaReview(
        persona_name="Critic",
        persona_id="critic",
        confidence_score=0.70,
        strengths=["Clear problem statement"],
        concerns=[
            Concern(text="Edge case handling unclear", is_blocking=True),
            Concern(text="Error recovery not specified", is_blocking=False),
        ],
        recommendations=[
            "Document edge case handling",
            "Add comprehensive error recovery plan",
        ],
        blocking_issues=[],
        estimated_effort="2 weeks",
        dependency_risks=["Third-party API changes", "Network reliability"],
    )


@pytest.fixture
def persona_review_optimist_high_confidence() -> PersonaReview:
    """Fixture for Optimist persona review with high confidence.

    Returns:
        PersonaReview with Optimist persona at 0.90 confidence
    """
    from consensus_engine.schemas.review import PersonaReview

    return PersonaReview(
        persona_name="Optimist",
        persona_id="optimist",
        confidence_score=0.90,
        strengths=[
            "Innovative approach",
            "Clear value proposition",
            "Feasible implementation path",
            "Good use of existing technologies",
        ],
        concerns=[],
        recommendations=["Consider expanding scope to include mobile support"],
        blocking_issues=[],
        estimated_effort="2-3 weeks",
        dependency_risks=[],
    )


@pytest.fixture
def persona_review_security_guardian_with_critical_issue() -> PersonaReview:
    """Fixture for SecurityGuardian with critical security issue (veto).

    Returns:
        PersonaReview with SecurityGuardian at 0.65 confidence and security_critical issue
    """
    from consensus_engine.schemas.review import BlockingIssue, Concern, PersonaReview

    return PersonaReview(
        persona_name="SecurityGuardian",
        persona_id="security_guardian",
        confidence_score=0.65,
        strengths=["Uses HTTPS for all communications"],
        concerns=[
            Concern(text="Missing input validation", is_blocking=True),
            Concern(text="No rate limiting", is_blocking=True),
        ],
        recommendations=[
            "Implement comprehensive input validation",
            "Add rate limiting to all endpoints",
            "Conduct security audit before deployment",
        ],
        blocking_issues=[
            BlockingIssue(
                text="SQL injection vulnerability in user input handling",
                security_critical=True,  # Triggers veto
            ),
        ],
        estimated_effort="1 week for security fixes",
        dependency_risks=["Security library updates"],
    )


@pytest.fixture
def persona_review_security_guardian_no_veto() -> PersonaReview:
    """Fixture for SecurityGuardian without critical security issue (no veto).

    Returns:
        PersonaReview with SecurityGuardian at 0.80 confidence, no security_critical
    """
    from consensus_engine.schemas.review import BlockingIssue, Concern, PersonaReview

    return PersonaReview(
        persona_name="SecurityGuardian",
        persona_id="security_guardian",
        confidence_score=0.80,
        strengths=["Good authentication design", "Proper use of HTTPS"],
        concerns=[
            Concern(text="Logging could expose sensitive data", is_blocking=False),
        ],
        recommendations=["Review logging implementation for PII"],
        blocking_issues=[
            BlockingIssue(text="Minor: consider adding CSRF tokens", security_critical=False)
        ],
        estimated_effort="1-2 days",
        dependency_risks=[],
    )


@pytest.fixture
def persona_review_user_advocate_high_confidence() -> PersonaReview:
    """Fixture for UserAdvocate persona review with high confidence.

    Returns:
        PersonaReview with UserAdvocate persona at 0.85 confidence
    """
    from consensus_engine.schemas.review import Concern, PersonaReview

    return PersonaReview(
        persona_name="UserAdvocate",
        persona_id="user_advocate",
        confidence_score=0.85,
        strengths=[
            "Clear user value proposition",
            "Intuitive API design",
            "Good error messages",
        ],
        concerns=[
            Concern(text="Accessibility not explicitly addressed", is_blocking=False),
        ],
        recommendations=[
            "Add accessibility documentation",
            "Consider internationalization support",
        ],
        blocking_issues=[],
        estimated_effort="2 weeks",
        dependency_risks=[],
    )


@pytest.fixture
def persona_review_critic_low_confidence() -> PersonaReview:
    """Fixture for Critic persona review with low confidence (dissenter).

    Returns:
        PersonaReview with Critic persona at 0.55 confidence (triggers minority report)
    """
    from consensus_engine.schemas.review import BlockingIssue, Concern, PersonaReview

    return PersonaReview(
        persona_name="Critic",
        persona_id="critic",
        confidence_score=0.55,  # Low confidence - triggers minority report
        strengths=["Problem is well-defined"],
        concerns=[
            Concern(text="Too many unknowns in implementation", is_blocking=True),
            Concern(text="High complexity without clear benefits", is_blocking=True),
            Concern(text="Timeline appears optimistic", is_blocking=False),
        ],
        recommendations=[
            "Break down into smaller phases",
            "Conduct proof-of-concept first",
            "Add more detailed technical specification",
        ],
        blocking_issues=[
            BlockingIssue(text="Implementation complexity not adequately addressed"),
        ],
        estimated_effort="6-8 weeks (much higher than estimated)",
        dependency_risks=[
            "Multiple external API dependencies",
            "Unproven technology stack",
            "Team expertise gaps",
        ],
    )


@pytest.fixture
def all_personas_approve_scenario() -> list[PersonaReview]:
    """Fixture for all five personas with high confidence (approve scenario).

    Returns:
        List of PersonaReview instances representing unanimous approval
    """
    from consensus_engine.schemas.review import PersonaReview

    return [
        PersonaReview(
            persona_name="Architect",
            persona_id="architect",
            confidence_score=0.88,
            strengths=["Excellent architecture"],
            concerns=[],
            recommendations=["Minor: Consider adding monitoring"],
            blocking_issues=[],
            estimated_effort="3 weeks",
            dependency_risks=[],
        ),
        PersonaReview(
            persona_name="Critic",
            persona_id="critic",
            confidence_score=0.82,
            strengths=["Well thought out"],
            concerns=[],
            recommendations=["Add more test coverage"],
            blocking_issues=[],
            estimated_effort="3 weeks",
            dependency_risks=[],
        ),
        PersonaReview(
            persona_name="Optimist",
            persona_id="optimist",
            confidence_score=0.95,
            strengths=["Great potential", "Clear value"],
            concerns=[],
            recommendations=[],
            blocking_issues=[],
            estimated_effort="2-3 weeks",
            dependency_risks=[],
        ),
        PersonaReview(
            persona_name="SecurityGuardian",
            persona_id="security_guardian",
            confidence_score=0.87,
            strengths=["Good security design"],
            concerns=[],
            recommendations=["Schedule security audit"],
            blocking_issues=[],
            estimated_effort="3 weeks",
            dependency_risks=[],
        ),
        PersonaReview(
            persona_name="UserAdvocate",
            persona_id="user_advocate",
            confidence_score=0.90,
            strengths=["Excellent UX"],
            concerns=[],
            recommendations=[],
            blocking_issues=[],
            estimated_effort="2-3 weeks",
            dependency_risks=[],
        ),
    ]


@pytest.fixture
def all_personas_revise_scenario() -> list[PersonaReview]:
    """Fixture for all five personas with medium confidence (revise scenario).

    Returns:
        List of PersonaReview instances representing revise decision
    """
    from consensus_engine.schemas.review import Concern, PersonaReview

    return [
        PersonaReview(
            persona_name="Architect",
            persona_id="architect",
            confidence_score=0.70,
            strengths=["Decent approach"],
            concerns=[Concern(text="Some design concerns", is_blocking=False)],
            recommendations=["Refine architecture"],
            blocking_issues=[],
            estimated_effort="4 weeks",
            dependency_risks=[],
        ),
        PersonaReview(
            persona_name="Critic",
            persona_id="critic",
            confidence_score=0.68,
            strengths=["Problem is clear"],
            concerns=[Concern(text="Implementation risks", is_blocking=False)],
            recommendations=["Add more detail"],
            blocking_issues=[],
            estimated_effort="4 weeks",
            dependency_risks=["External dependencies"],
        ),
        PersonaReview(
            persona_name="Optimist",
            persona_id="optimist",
            confidence_score=0.75,
            strengths=["Has potential"],
            concerns=[],
            recommendations=["Expand on benefits"],
            blocking_issues=[],
            estimated_effort="3-4 weeks",
            dependency_risks=[],
        ),
        PersonaReview(
            persona_name="SecurityGuardian",
            persona_id="security_guardian",
            confidence_score=0.72,
            strengths=["Basic security covered"],
            concerns=[Concern(text="Need more security details", is_blocking=False)],
            recommendations=["Add security specification"],
            blocking_issues=[],
            estimated_effort="4 weeks",
            dependency_risks=[],
        ),
        PersonaReview(
            persona_name="UserAdvocate",
            persona_id="user_advocate",
            confidence_score=0.68,
            strengths=["Clear user need"],
            concerns=[Concern(text="UX could be better", is_blocking=False)],
            recommendations=["Improve UX design"],
            blocking_issues=[],
            estimated_effort="3-4 weeks",
            dependency_risks=[],
        ),
    ]
