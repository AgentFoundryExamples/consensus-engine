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
"""Unit tests for orchestrator module."""

from unittest.mock import MagicMock, patch

import pytest

from consensus_engine.config.settings import Settings
from consensus_engine.exceptions import LLMServiceError
from consensus_engine.schemas.proposal import ExpandedProposal
from consensus_engine.schemas.review import BlockingIssue, Concern, PersonaReview
from consensus_engine.services.orchestrator import review_with_all_personas


@pytest.fixture
def mock_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Create mock settings for tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-orchestrator")
    monkeypatch.setenv("REVIEW_MODEL", "gpt-5.1")
    monkeypatch.setenv("REVIEW_TEMPERATURE", "0.2")
    return Settings()


@pytest.fixture
def sample_proposal() -> ExpandedProposal:
    """Create a sample proposal for testing."""
    return ExpandedProposal(
        problem_statement="Build a scalable API",
        proposed_solution="Use FastAPI with async handlers",
        assumptions=["Python 3.11+", "PostgreSQL database"],
        scope_non_goals=["No mobile app", "No authentication"],
        title="API Development Proposal",
    )


class TestReviewWithAllPersonas:
    """Test suite for review_with_all_personas function."""

    @patch("consensus_engine.services.orchestrator.OpenAIClientWrapper")
    def test_orchestrator_calls_all_five_personas(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that orchestrator calls all five personas in order."""
        # Create mock reviews for each persona
        mock_reviews = [
            PersonaReview(
                persona_name="Architect",
                persona_id="architect",
                confidence_score=0.85,
                strengths=["Good design"],
                concerns=[],
                recommendations=["Add diagrams"],
                blocking_issues=[],
                estimated_effort="2 weeks",
                dependency_risks=[],
            ),
            PersonaReview(
                persona_name="Critic",
                persona_id="critic",
                confidence_score=0.70,
                strengths=["Clear scope"],
                concerns=[Concern(text="Missing edge cases", is_blocking=False)],
                recommendations=["Add edge case handling"],
                blocking_issues=[],
                estimated_effort="3 weeks",
                dependency_risks=[],
            ),
            PersonaReview(
                persona_name="Optimist",
                persona_id="optimist",
                confidence_score=0.90,
                strengths=["Feasible", "Good tech stack"],
                concerns=[],
                recommendations=["Good to go"],
                blocking_issues=[],
                estimated_effort="2 weeks",
                dependency_risks=[],
            ),
            PersonaReview(
                persona_name="SecurityGuardian",
                persona_id="security_guardian",
                confidence_score=0.75,
                strengths=["Uses HTTPS"],
                concerns=[Concern(text="No auth mentioned", is_blocking=True)],
                recommendations=["Add authentication"],
                blocking_issues=[BlockingIssue(text="Missing auth", security_critical=True)],
                estimated_effort="1 week for auth",
                dependency_risks=["JWT library"],
            ),
            PersonaReview(
                persona_name="UserAdvocate",
                persona_id="user_advocate",
                confidence_score=0.80,
                strengths=["User-friendly API"],
                concerns=[],
                recommendations=["Add API docs"],
                blocking_issues=[],
                estimated_effort="2 weeks",
                dependency_risks=[],
            ),
        ]

        mock_client = MagicMock()
        # Return different reviews for each call
        mock_client.create_structured_response_with_payload.side_effect = [
            (review, {"request_id": f"req-{i}", "model": "gpt-5.1", "latency": 1.0})
            for i, review in enumerate(mock_reviews)
        ]
        mock_client_class.return_value = mock_client

        # Call orchestrator
        reviews, metadata = review_with_all_personas(sample_proposal, mock_settings)

        # Verify all five personas were called
        assert len(reviews) == 5
        assert mock_client.create_structured_response_with_payload.call_count == 5

        # Verify persona order matches config
        assert reviews[0].persona_id == "architect"
        assert reviews[1].persona_id == "critic"
        assert reviews[2].persona_id == "optimist"
        assert reviews[3].persona_id == "security_guardian"
        assert reviews[4].persona_id == "user_advocate"

        # Verify metadata
        assert "run_id" in metadata
        assert metadata["persona_count"] == 5
        assert metadata["status"] == "success"

    @patch("consensus_engine.services.orchestrator.OpenAIClientWrapper")
    def test_orchestrator_attaches_internal_metadata(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that internal_metadata is attached to each review."""
        mock_review = PersonaReview(
            persona_name="Architect",
            persona_id="architect",
            confidence_score=0.85,
            strengths=["Good"],
            concerns=[],
            recommendations=["Improve"],
            blocking_issues=[],
            estimated_effort="2 weeks",
            dependency_risks=[],
        )

        mock_client = MagicMock()
        # Return same review 5 times
        mock_client.create_structured_response_with_payload.return_value = (
            mock_review,
            {
                "request_id": "test-req",
                "model": "gpt-5.1",
                "latency": 2.5,
            },
        )
        mock_client_class.return_value = mock_client

        # Call orchestrator
        reviews, _ = review_with_all_personas(sample_proposal, mock_settings)

        # Verify internal_metadata on each review
        for review in reviews:
            assert review.internal_metadata is not None
            assert "model" in review.internal_metadata
            assert "latency" in review.internal_metadata
            assert "request_id" in review.internal_metadata
            assert "timestamp" in review.internal_metadata

    @patch("consensus_engine.services.orchestrator.OpenAIClientWrapper")
    def test_orchestrator_fails_on_first_persona_error(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that orchestrator fails immediately if first persona fails."""
        mock_client = MagicMock()
        mock_client.create_structured_response_with_payload.side_effect = LLMServiceError(
            "API error", code="LLM_SERVICE_ERROR"
        )
        mock_client_class.return_value = mock_client

        # Call orchestrator and expect error
        with pytest.raises(LLMServiceError):
            review_with_all_personas(sample_proposal, mock_settings)

        # Verify only one call was made (failed immediately)
        assert mock_client.create_structured_response_with_payload.call_count == 1

    @patch("consensus_engine.services.orchestrator.OpenAIClientWrapper")
    def test_orchestrator_fails_on_middle_persona_error(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that orchestrator fails if any persona in the middle fails."""
        mock_review = PersonaReview(
            persona_name="Test",
            persona_id="test",
            confidence_score=0.85,
            strengths=["Good"],
            concerns=[],
            recommendations=["Improve"],
            blocking_issues=[],
            estimated_effort="2 weeks",
            dependency_risks=[],
        )

        mock_client = MagicMock()
        # First two succeed, third fails
        mock_client.create_structured_response_with_payload.side_effect = [
            (mock_review, {"request_id": "req-1"}),
            (mock_review, {"request_id": "req-2"}),
            LLMServiceError("API error", code="LLM_SERVICE_ERROR"),
        ]
        mock_client_class.return_value = mock_client

        # Call orchestrator and expect error
        with pytest.raises(LLMServiceError):
            review_with_all_personas(sample_proposal, mock_settings)

        # Verify three calls were made before failure
        assert mock_client.create_structured_response_with_payload.call_count == 3

    @patch("consensus_engine.services.orchestrator.OpenAIClientWrapper")
    def test_orchestrator_uses_correct_temperature_per_persona(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that orchestrator uses persona-specific temperature (0.2)."""
        mock_review = PersonaReview(
            persona_name="Test",
            persona_id="test",
            confidence_score=0.85,
            strengths=["Good"],
            concerns=[],
            recommendations=["Improve"],
            blocking_issues=[],
            estimated_effort="2 weeks",
            dependency_risks=[],
        )

        mock_client = MagicMock()
        mock_client.create_structured_response_with_payload.return_value = (
            mock_review,
            {"request_id": "test-req"},
        )
        mock_client_class.return_value = mock_client

        # Call orchestrator
        review_with_all_personas(sample_proposal, mock_settings)

        # Verify all calls used temperature 0.2
        for call in mock_client.create_structured_response_with_payload.call_args_list:
            assert call[1]["temperature_override"] == 0.2

    @patch("consensus_engine.services.orchestrator.OpenAIClientWrapper")
    def test_orchestrator_includes_persona_specific_instructions(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test that orchestrator includes persona-specific developer instructions."""
        mock_review = PersonaReview(
            persona_name="Test",
            persona_id="test",
            confidence_score=0.85,
            strengths=["Good"],
            concerns=[],
            recommendations=["Improve"],
            blocking_issues=[],
            estimated_effort="2 weeks",
            dependency_risks=[],
        )

        mock_client = MagicMock()
        mock_client.create_structured_response_with_payload.return_value = (
            mock_review,
            {"request_id": "test-req"},
        )
        mock_client_class.return_value = mock_client

        # Call orchestrator
        review_with_all_personas(sample_proposal, mock_settings)

        # Verify developer instructions contain persona names
        calls = mock_client.create_structured_response_with_payload.call_args_list
        assert len(calls) == 5

        # Check that each call has different persona instructions
        persona_names = ["Architect", "Critic", "Optimist", "SecurityGuardian", "UserAdvocate"]
        for i, call in enumerate(calls):
            developer_instruction = call[1]["developer_instruction"]
            assert persona_names[i] in developer_instruction


class TestDeterminePersonasToRerun:
    """Test suite for determine_personas_to_rerun function."""

    def test_rerun_low_confidence_persona(self) -> None:
        """Test that personas with confidence < 0.70 are marked for re-run."""
        from consensus_engine.services.orchestrator import determine_personas_to_rerun

        parent_reviews = [
            (
                "architect",
                {
                    "persona_id": "architect",
                    "confidence_score": 0.65,
                    "blocking_issues": [],
                },
                False,  # security_concerns_present
            ),
            (
                "critic",
                {
                    "persona_id": "critic",
                    "confidence_score": 0.85,
                    "blocking_issues": [],
                },
                False,  # security_concerns_present
            ),
        ]

        personas_to_rerun = determine_personas_to_rerun(parent_reviews)

        assert "architect" in personas_to_rerun
        assert "critic" not in personas_to_rerun

    def test_rerun_persona_with_blocking_issues(self) -> None:
        """Test that personas with blocking issues are marked for re-run."""
        from consensus_engine.services.orchestrator import determine_personas_to_rerun

        parent_reviews = [
            (
                "architect",
                {
                    "persona_id": "architect",
                    "confidence_score": 0.85,
                    "blocking_issues": [{"text": "Critical issue", "security_critical": False}],
                },
                False,  # security_concerns_present
            ),
            (
                "critic",
                {
                    "persona_id": "critic",
                    "confidence_score": 0.80,
                    "blocking_issues": [],
                },
                False,  # security_concerns_present
            ),
        ]

        personas_to_rerun = determine_personas_to_rerun(parent_reviews)

        assert "architect" in personas_to_rerun
        assert "critic" not in personas_to_rerun

    def test_rerun_security_guardian_with_security_concerns(self) -> None:
        """Test that SecurityGuardian with security_critical issues is marked for re-run."""
        from consensus_engine.services.orchestrator import determine_personas_to_rerun

        parent_reviews = [
            (
                "security_guardian",
                {
                    "persona_id": "security_guardian",
                    "confidence_score": 0.85,
                    "blocking_issues": [
                        {"text": "SQL injection risk", "security_critical": True}
                    ],
                },
                True,  # security_concerns_present from DB
            ),
            (
                "critic",
                {
                    "persona_id": "critic",
                    "confidence_score": 0.80,
                    "blocking_issues": [],
                },
                False,  # security_concerns_present
            ),
        ]

        personas_to_rerun = determine_personas_to_rerun(parent_reviews)

        assert "security_guardian" in personas_to_rerun
        assert "critic" not in personas_to_rerun

    def test_no_rerun_for_high_confidence_no_issues(self) -> None:
        """Test that personas with high confidence and no issues are not marked for re-run."""
        from consensus_engine.services.orchestrator import determine_personas_to_rerun

        parent_reviews = [
            (
                "architect",
                {
                    "persona_id": "architect",
                    "confidence_score": 0.85,
                    "blocking_issues": [],
                },
                False,  # security_concerns_present
            ),
            (
                "critic",
                {
                    "persona_id": "critic",
                    "confidence_score": 0.90,
                    "blocking_issues": [],
                },
                False,  # security_concerns_present
            ),
        ]

        personas_to_rerun = determine_personas_to_rerun(parent_reviews)

        assert len(personas_to_rerun) == 0

    def test_multiple_criteria_trigger_rerun(self) -> None:
        """Test that multiple criteria can trigger re-run for same persona."""
        from consensus_engine.services.orchestrator import determine_personas_to_rerun

        parent_reviews = [
            (
                "architect",
                {
                    "persona_id": "architect",
                    "confidence_score": 0.65,
                    "blocking_issues": [{"text": "Issue", "security_critical": False}],
                },
                False,  # security_concerns_present
            ),
        ]

        personas_to_rerun = determine_personas_to_rerun(parent_reviews)

        # Should be marked for re-run due to both low confidence and blocking issues
        assert "architect" in personas_to_rerun
        assert len(personas_to_rerun) == 1
