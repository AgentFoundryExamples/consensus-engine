"""Integration tests for multi-persona orchestration and aggregation."""

from unittest.mock import MagicMock, patch

import pytest

from consensus_engine.config.settings import Settings
from consensus_engine.schemas.proposal import ExpandedProposal
from consensus_engine.schemas.review import (
    BlockingIssue,
    Concern,
    DecisionEnum,
    PersonaReview,
)
from consensus_engine.services.aggregator import aggregate_persona_reviews
from consensus_engine.services.orchestrator import review_with_all_personas


@pytest.fixture
def mock_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Create mock settings for integration tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-integration")
    monkeypatch.setenv("REVIEW_MODEL", "gpt-5.1")
    monkeypatch.setenv("REVIEW_TEMPERATURE", "0.2")
    return Settings()


@pytest.fixture
def sample_proposal() -> ExpandedProposal:
    """Create a sample proposal for testing."""
    return ExpandedProposal(
        problem_statement="Build a scalable user management API with authentication",
        proposed_solution="FastAPI backend with JWT auth, PostgreSQL, and async handlers",
        assumptions=["Python 3.11+", "PostgreSQL 14+", "Docker deployment"],
        scope_non_goals=["No mobile app", "No real-time features"],
        title="User Management API",
    )


class TestMultiPersonaIntegration:
    """Integration tests for end-to-end multi-persona workflow."""

    @patch("consensus_engine.services.orchestrator.OpenAIClientWrapper")
    def test_end_to_end_multi_persona_approve_scenario(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test complete workflow resulting in APPROVE decision."""
        # Create reviews from all five personas with high confidence
        mock_reviews = [
            PersonaReview(
                persona_name="Architect",
                persona_id="architect",
                confidence_score=0.88,
                strengths=["Well-designed architecture", "Scalable approach"],
                concerns=[Concern(text="Minor: Consider connection pooling", is_blocking=False)],
                recommendations=["Add connection pooling for better performance"],
                blocking_issues=[],
                estimated_effort="3-4 weeks",
                dependency_risks=["PostgreSQL setup"],
            ),
            PersonaReview(
                persona_name="Critic",
                persona_id="critic",
                confidence_score=0.82,
                strengths=["Realistic assumptions", "Clear scope boundaries"],
                concerns=[Concern(text="Edge case: concurrent updates", is_blocking=False)],
                recommendations=["Add optimistic locking for concurrent updates"],
                blocking_issues=[],
                estimated_effort="4 weeks with testing",
                dependency_risks=["Database race conditions"],
            ),
            PersonaReview(
                persona_name="Optimist",
                persona_id="optimist",
                confidence_score=0.92,
                strengths=["Feasible with current tech", "Good tech stack choice"],
                concerns=[],
                recommendations=["Great proposal, ready to implement"],
                blocking_issues=[],
                estimated_effort="3 weeks",
                dependency_risks=[],
            ),
            PersonaReview(
                persona_name="SecurityGuardian",
                persona_id="security_guardian",
                confidence_score=0.85,
                strengths=["JWT authentication mentioned", "HTTPS implied"],
                concerns=[
                    Concern(text="Need to specify token expiration", is_blocking=False),
                    Concern(text="Rate limiting not mentioned", is_blocking=False),
                ],
                recommendations=["Add rate limiting", "Define token expiration policy"],
                blocking_issues=[],
                estimated_effort="1 week for security hardening",
                dependency_risks=["JWT library security updates"],
            ),
            PersonaReview(
                persona_name="UserAdvocate",
                persona_id="user_advocate",
                confidence_score=0.87,
                strengths=["Clear user value", "Good API design"],
                concerns=[Concern(text="API documentation needed", is_blocking=False)],
                recommendations=["Add OpenAPI documentation", "Include usage examples"],
                blocking_issues=[],
                estimated_effort="3 weeks",
                dependency_risks=[],
            ),
        ]

        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = [
            (review, {"request_id": f"req-{i}", "model": "gpt-5.1", "latency": 1.5})
            for i, review in enumerate(mock_reviews)
        ]
        mock_client_class.return_value = mock_client

        # Run orchestration
        reviews, orchestration_metadata = review_with_all_personas(
            sample_proposal, mock_settings
        )

        # Verify orchestration
        assert len(reviews) == 5
        assert orchestration_metadata["status"] == "success"
        assert orchestration_metadata["persona_count"] == 5

        # Run aggregation
        decision = aggregate_persona_reviews(reviews)

        # Verify decision
        # Expected weighted: 0.88*0.25 + 0.82*0.25 + 0.92*0.15 + 0.85*0.20 + 0.87*0.15 = 0.8655
        assert decision.decision == DecisionEnum.APPROVE
        assert decision.weighted_confidence >= 0.80
        assert decision.detailed_score_breakdown is not None

        # Verify no minority reports (all personas confident)
        assert decision.minority_reports is None or len(decision.minority_reports) == 0

    @patch("consensus_engine.services.orchestrator.OpenAIClientWrapper")
    def test_end_to_end_security_guardian_veto(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test SecurityGuardian veto power with security_critical blocking issue."""
        mock_reviews = [
            PersonaReview(
                persona_name="Architect",
                persona_id="architect",
                confidence_score=0.90,
                strengths=["Great design"],
                concerns=[],
                recommendations=["Proceed with implementation"],
                blocking_issues=[],
                estimated_effort="3 weeks",
                dependency_risks=[],
            ),
            PersonaReview(
                persona_name="Critic",
                persona_id="critic",
                confidence_score=0.85,
                strengths=["Well thought out"],
                concerns=[],
                recommendations=["Looks good"],
                blocking_issues=[],
                estimated_effort="3 weeks",
                dependency_risks=[],
            ),
            PersonaReview(
                persona_name="Optimist",
                persona_id="optimist",
                confidence_score=0.95,
                strengths=["Excellent"],
                concerns=[],
                recommendations=["Ready to go"],
                blocking_issues=[],
                estimated_effort="2 weeks",
                dependency_risks=[],
            ),
            PersonaReview(
                persona_name="SecurityGuardian",
                persona_id="security_guardian",
                confidence_score=0.88,
                strengths=["Good intent"],
                concerns=[
                    Concern(text="SQL injection vulnerability", is_blocking=True),
                ],
                recommendations=["Use parameterized queries"],
                blocking_issues=[
                    BlockingIssue(
                        text="No mention of SQL injection protection",
                        security_critical=True,  # This triggers veto
                    )
                ],
                estimated_effort="1 week to fix",
                dependency_risks=[],
            ),
            PersonaReview(
                persona_name="UserAdvocate",
                persona_id="user_advocate",
                confidence_score=0.90,
                strengths=["User-friendly"],
                concerns=[],
                recommendations=["Good UX"],
                blocking_issues=[],
                estimated_effort="3 weeks",
                dependency_risks=[],
            ),
        ]

        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = [
            (review, {"request_id": f"req-{i}"}) for i, review in enumerate(mock_reviews)
        ]
        mock_client_class.return_value = mock_client

        # Run orchestration and aggregation
        reviews, _ = review_with_all_personas(sample_proposal, mock_settings)
        decision = aggregate_persona_reviews(reviews)

        # Despite high weighted confidence, SecurityGuardian veto forces REVISE
        assert decision.weighted_confidence >= 0.80
        assert decision.decision == DecisionEnum.REVISE  # Vetoed from APPROVE

    @patch("consensus_engine.services.orchestrator.OpenAIClientWrapper")
    def test_end_to_end_minority_report_generation(
        self,
        mock_client_class: MagicMock,
        mock_settings: Settings,
        sample_proposal: ExpandedProposal,
    ) -> None:
        """Test minority report generation for dissenting personas."""
        mock_reviews = [
            PersonaReview(
                persona_name="Architect",
                persona_id="architect",
                confidence_score=0.92,
                strengths=["Excellent design"],
                concerns=[],
                recommendations=["Proceed"],
                blocking_issues=[],
                estimated_effort="3 weeks",
                dependency_risks=[],
            ),
            PersonaReview(
                persona_name="Critic",
                persona_id="critic",
                confidence_score=0.55,  # Low confidence dissenter
                strengths=["Some good ideas"],
                concerns=[
                    Concern(text="Too many unknowns", is_blocking=False),
                    Concern(text="Insufficient testing plan", is_blocking=False),
                ],
                recommendations=["Add comprehensive testing strategy", "Clarify requirements"],
                blocking_issues=[],
                estimated_effort="5-6 weeks realistically",
                dependency_risks=["Unclear dependencies"],
            ),
            PersonaReview(
                persona_name="Optimist",
                persona_id="optimist",
                confidence_score=0.95,
                strengths=["Feasible", "Good approach"],
                concerns=[],
                recommendations=["Go for it"],
                blocking_issues=[],
                estimated_effort="3 weeks",
                dependency_risks=[],
            ),
            PersonaReview(
                persona_name="SecurityGuardian",
                persona_id="security_guardian",
                confidence_score=0.90,
                strengths=["Security considered"],
                concerns=[],
                recommendations=["Add security audit"],
                blocking_issues=[],
                estimated_effort="1 week",
                dependency_risks=[],
            ),
            PersonaReview(
                persona_name="UserAdvocate",
                persona_id="user_advocate",
                confidence_score=0.88,
                strengths=["User-centric"],
                concerns=[],
                recommendations=["Add user docs"],
                blocking_issues=[],
                estimated_effort="3 weeks",
                dependency_risks=[],
            ),
        ]

        mock_client = MagicMock()
        mock_client.create_structured_response.side_effect = [
            (review, {"request_id": f"req-{i}"}) for i, review in enumerate(mock_reviews)
        ]
        mock_client_class.return_value = mock_client

        # Run orchestration and aggregation
        reviews, _ = review_with_all_personas(sample_proposal, mock_settings)
        decision = aggregate_persona_reviews(reviews)

        # Should be APPROVE but with minority report from Critic
        # 0.92*0.25 + 0.55*0.25 + 0.95*0.15 + 0.90*0.20 + 0.88*0.15 = 0.8395
        assert decision.decision == DecisionEnum.APPROVE

        # Should have minority report for Critic
        assert decision.minority_reports is not None
        assert len(decision.minority_reports) == 1
        assert decision.minority_reports[0].persona_id == "critic"
        assert decision.minority_reports[0].confidence_score == 0.55

        # Check that dissent details are captured
        minority = decision.minority_reports[0]
        # Verify that concerns are captured in either blocking_summary or concerns field
        has_concern_in_summary = "Too many unknowns" in minority.blocking_summary
        has_concern_in_list = minority.concerns and any(
            "Too many unknowns" in concern for concern in minority.concerns
        )
        assert has_concern_in_summary or has_concern_in_list
