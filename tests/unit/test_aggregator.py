"""Unit tests for aggregator module."""

import pytest

from consensus_engine.schemas.review import (
    BlockingIssue,
    Concern,
    DecisionEnum,
    PersonaReview,
)
from consensus_engine.services.aggregator import aggregate_persona_reviews


def create_persona_review(
    persona_id: str,
    persona_name: str,
    confidence_score: float,
    blocking_issues: list[BlockingIssue] | None = None,
) -> PersonaReview:
    """Helper to create a PersonaReview for testing."""
    return PersonaReview(
        persona_name=persona_name,
        persona_id=persona_id,
        confidence_score=confidence_score,
        strengths=["Test strength"],
        concerns=[],
        recommendations=["Test recommendation"],
        blocking_issues=blocking_issues or [],
        estimated_effort="2 weeks",
        dependency_risks=[],
    )


class TestAggregatePersonaReviews:
    """Test suite for aggregate_persona_reviews function."""

    def test_aggregator_computes_weighted_average(self) -> None:
        """Test that aggregator correctly computes weighted confidence."""
        reviews = [
            create_persona_review("architect", "Architect", 0.80),  # weight 0.25
            create_persona_review("critic", "Critic", 0.70),  # weight 0.25
            create_persona_review("optimist", "Optimist", 0.90),  # weight 0.15
            create_persona_review("security_guardian", "SecurityGuardian", 0.75),  # weight 0.20
            create_persona_review("user_advocate", "UserAdvocate", 0.85),  # weight 0.15
        ]

        result = aggregate_persona_reviews(reviews)

        # Expected: 0.25*0.80 + 0.25*0.70 + 0.15*0.90 + 0.20*0.75 + 0.15*0.85
        #         = 0.20 + 0.175 + 0.135 + 0.15 + 0.1275 = 0.7875
        assert result.weighted_confidence == pytest.approx(0.7875, abs=0.0001)
        assert result.overall_weighted_confidence == result.weighted_confidence

    def test_aggregator_applies_approve_threshold(self) -> None:
        """Test that aggregator applies approve threshold (≥0.80)."""
        reviews = [
            create_persona_review("architect", "Architect", 0.85),
            create_persona_review("critic", "Critic", 0.80),
            create_persona_review("optimist", "Optimist", 0.90),
            create_persona_review("security_guardian", "SecurityGuardian", 0.80),
            create_persona_review("user_advocate", "UserAdvocate", 0.85),
        ]

        result = aggregate_persona_reviews(reviews)

        # All high scores should result in APPROVE
        assert result.decision == DecisionEnum.APPROVE
        assert result.weighted_confidence >= 0.80

    def test_aggregator_applies_revise_threshold(self) -> None:
        """Test that aggregator applies revise threshold (0.60-0.80)."""
        reviews = [
            create_persona_review("architect", "Architect", 0.70),
            create_persona_review("critic", "Critic", 0.65),
            create_persona_review("optimist", "Optimist", 0.75),
            create_persona_review("security_guardian", "SecurityGuardian", 0.70),
            create_persona_review("user_advocate", "UserAdvocate", 0.72),
        ]

        result = aggregate_persona_reviews(reviews)

        # Scores in revise range
        assert result.decision == DecisionEnum.REVISE
        assert 0.60 <= result.weighted_confidence < 0.80

    def test_aggregator_applies_reject_threshold(self) -> None:
        """Test that aggregator applies reject threshold (<0.60)."""
        reviews = [
            create_persona_review("architect", "Architect", 0.50),
            create_persona_review("critic", "Critic", 0.45),
            create_persona_review("optimist", "Optimist", 0.60),
            create_persona_review("security_guardian", "SecurityGuardian", 0.55),
            create_persona_review("user_advocate", "UserAdvocate", 0.52),
        ]

        result = aggregate_persona_reviews(reviews)

        # Low scores should result in REJECT
        assert result.decision == DecisionEnum.REJECT
        assert result.weighted_confidence < 0.60

    def test_aggregator_security_guardian_veto(self) -> None:
        """Test SecurityGuardian veto with security_critical blocking issue."""
        reviews = [
            create_persona_review("architect", "Architect", 0.90),
            create_persona_review("critic", "Critic", 0.85),
            create_persona_review("optimist", "Optimist", 0.95),
            create_persona_review(
                "security_guardian",
                "SecurityGuardian",
                0.80,
                blocking_issues=[
                    BlockingIssue(text="Critical vulnerability", security_critical=True)
                ],
            ),
            create_persona_review("user_advocate", "UserAdvocate", 0.90),
        ]

        result = aggregate_persona_reviews(reviews)

        # Despite high confidence, SecurityGuardian veto should force REVISE
        assert result.weighted_confidence >= 0.80
        assert result.decision == DecisionEnum.REVISE  # Veto downgrades from APPROVE

    def test_aggregator_security_guardian_no_veto_without_critical_flag(self) -> None:
        """Test SecurityGuardian without security_critical flag doesn't veto."""
        reviews = [
            create_persona_review("architect", "Architect", 0.90),
            create_persona_review("critic", "Critic", 0.85),
            create_persona_review("optimist", "Optimist", 0.95),
            create_persona_review(
                "security_guardian",
                "SecurityGuardian",
                0.80,
                blocking_issues=[
                    BlockingIssue(text="Minor issue", security_critical=False)
                ],
            ),
            create_persona_review("user_advocate", "UserAdvocate", 0.90),
        ]

        result = aggregate_persona_reviews(reviews)

        # Without security_critical flag, no veto
        assert result.weighted_confidence >= 0.80
        assert result.decision == DecisionEnum.APPROVE

    def test_aggregator_builds_detailed_score_breakdown(self) -> None:
        """Test that detailed score breakdown is properly constructed."""
        reviews = [
            create_persona_review("architect", "Architect", 0.80),
            create_persona_review("critic", "Critic", 0.70),
            create_persona_review("optimist", "Optimist", 0.90),
            create_persona_review("security_guardian", "SecurityGuardian", 0.75),
            create_persona_review("user_advocate", "UserAdvocate", 0.85),
        ]

        result = aggregate_persona_reviews(reviews)

        assert result.detailed_score_breakdown is not None
        breakdown = result.detailed_score_breakdown

        # Check weights
        assert breakdown.weights["architect"] == 0.25
        assert breakdown.weights["critic"] == 0.25
        assert breakdown.weights["optimist"] == 0.15
        assert breakdown.weights["security_guardian"] == 0.20
        assert breakdown.weights["user_advocate"] == 0.15

        # Check individual scores
        assert breakdown.individual_scores["architect"] == 0.80
        assert breakdown.individual_scores["critic"] == 0.70
        assert breakdown.individual_scores["optimist"] == 0.90
        assert breakdown.individual_scores["security_guardian"] == 0.75
        assert breakdown.individual_scores["user_advocate"] == 0.85

        # Check weighted contributions
        assert breakdown.weighted_contributions["architect"] == pytest.approx(0.20)
        assert breakdown.weighted_contributions["critic"] == pytest.approx(0.175)
        assert breakdown.weighted_contributions["optimist"] == pytest.approx(0.135)
        assert breakdown.weighted_contributions["security_guardian"] == pytest.approx(0.15)
        assert breakdown.weighted_contributions["user_advocate"] == pytest.approx(0.1275)

        # Check formula
        assert "weighted_confidence" in breakdown.formula
        assert "sum" in breakdown.formula

    def test_aggregator_generates_minority_report_for_low_confidence(self) -> None:
        """Test minority report for persona with low confidence when decision is APPROVE."""
        reviews = [
            create_persona_review("architect", "Architect", 0.95),
            create_persona_review("critic", "Critic", 0.55),  # Low confidence dissenter
            create_persona_review("optimist", "Optimist", 0.98),
            create_persona_review("security_guardian", "SecurityGuardian", 0.90),
            create_persona_review("user_advocate", "UserAdvocate", 0.95),
        ]

        result = aggregate_persona_reviews(reviews)

        # Should be APPROVE based on weighted average
        # 0.95*0.25 + 0.55*0.25 + 0.98*0.15 + 0.90*0.20 + 0.95*0.15 = 0.8445
        assert result.decision == DecisionEnum.APPROVE

        # Should have minority report for Critic
        assert result.minority_reports is not None
        assert len(result.minority_reports) > 0

        minority = result.minority_reports[0]
        assert minority.persona_id == "critic"
        assert minority.confidence_score == 0.55

    def test_aggregator_generates_minority_report_for_blocking_issues(self) -> None:
        """Test minority report for persona with blocking issues when decision is APPROVE."""
        reviews = [
            create_persona_review("architect", "Architect", 0.90),
            create_persona_review(
                "critic",
                "Critic",
                0.80,  # High confidence but has blocking issues
                blocking_issues=[BlockingIssue(text="Edge case not handled")],
            ),
            create_persona_review("optimist", "Optimist", 0.95),
            create_persona_review("security_guardian", "SecurityGuardian", 0.85),
            create_persona_review("user_advocate", "UserAdvocate", 0.90),
        ]

        result = aggregate_persona_reviews(reviews)

        # Should be APPROVE based on weighted average
        assert result.decision == DecisionEnum.APPROVE

        # Should have minority report for Critic due to blocking issues
        assert result.minority_reports is not None
        assert len(result.minority_reports) > 0

        minority = result.minority_reports[0]
        assert minority.persona_id == "critic"
        assert "Edge case not handled" in minority.blocking_summary

    def test_aggregator_no_minority_report_for_unanimous_approve(self) -> None:
        """Test no minority report when all personas agree with high confidence."""
        reviews = [
            create_persona_review("architect", "Architect", 0.90),
            create_persona_review("critic", "Critic", 0.85),
            create_persona_review("optimist", "Optimist", 0.95),
            create_persona_review("security_guardian", "SecurityGuardian", 0.88),
            create_persona_review("user_advocate", "UserAdvocate", 0.92),
        ]

        result = aggregate_persona_reviews(reviews)

        # Should be unanimous APPROVE
        assert result.decision == DecisionEnum.APPROVE

        # Should have no minority reports
        assert result.minority_reports is None or len(result.minority_reports) == 0

    def test_aggregator_clamps_weighted_confidence(self) -> None:
        """Test that weighted confidence is clamped to [0.0, 1.0]."""
        # This is a sanity test - with correct weights, we should never exceed 1.0
        reviews = [
            create_persona_review("architect", "Architect", 1.0),
            create_persona_review("critic", "Critic", 1.0),
            create_persona_review("optimist", "Optimist", 1.0),
            create_persona_review("security_guardian", "SecurityGuardian", 1.0),
            create_persona_review("user_advocate", "UserAdvocate", 1.0),
        ]

        result = aggregate_persona_reviews(reviews)

        # Should be clamped to 1.0
        assert result.weighted_confidence <= 1.0
        assert result.weighted_confidence >= 0.0

    def test_aggregator_raises_error_on_empty_reviews(self) -> None:
        """Test that aggregator raises error for empty review list."""
        with pytest.raises(ValueError, match="Cannot aggregate empty list"):
            aggregate_persona_reviews([])

    def test_aggregator_multiple_minority_reports(self) -> None:
        """Test multiple personas can have minority reports simultaneously."""
        reviews = [
            create_persona_review("architect", "Architect", 0.95),
            create_persona_review("critic", "Critic", 0.55),  # Low confidence
            create_persona_review("optimist", "Optimist", 0.98),
            create_persona_review(
                "security_guardian",
                "SecurityGuardian",
                0.85,
                blocking_issues=[BlockingIssue(text="Minor security concern")],
            ),
            create_persona_review("user_advocate", "UserAdvocate", 0.95),
        ]

        result = aggregate_persona_reviews(reviews)

        # Should be APPROVE based on weighted average
        # 0.95*0.25 + 0.55*0.25 + 0.98*0.15 + 0.85*0.20 + 0.95*0.15 = 0.8420
        assert result.decision == DecisionEnum.APPROVE

        # Should have minority reports for both Critic and SecurityGuardian
        assert result.minority_reports is not None
        assert len(result.minority_reports) == 2

        persona_ids = {report.persona_id for report in result.minority_reports}
        assert "critic" in persona_ids
        assert "security_guardian" in persona_ids
