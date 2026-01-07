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
"""Unit tests for aggregator module."""

import pytest

from consensus_engine.schemas.review import (
    BlockingIssue,
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

    def test_aggregator_raises_error_on_unknown_persona_id(self) -> None:
        """Test that aggregator raises error for unknown persona_id."""
        reviews = [
            create_persona_review("unknown_persona", "UnknownPersona", 0.80),
        ]

        with pytest.raises(ValueError, match="Unknown persona_id 'unknown_persona'"):
            aggregate_persona_reviews(reviews)

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

    def test_aggregator_boundary_approve_threshold_exactly_080(self) -> None:
        """Test decision at exact approve threshold boundary (0.80)."""
        # Create reviews that result in exactly 0.80 weighted confidence
        # Using: 0.80*0.25 + 0.80*0.25 + 0.80*0.15 + 0.80*0.20 + 0.80*0.15 = 0.80
        reviews = [
            create_persona_review("architect", "Architect", 0.80),
            create_persona_review("critic", "Critic", 0.80),
            create_persona_review("optimist", "Optimist", 0.80),
            create_persona_review("security_guardian", "SecurityGuardian", 0.80),
            create_persona_review("user_advocate", "UserAdvocate", 0.80),
        ]

        result = aggregate_persona_reviews(reviews)

        # At exactly 0.80, should use >= comparison and result in APPROVE
        assert result.weighted_confidence == pytest.approx(0.80, abs=0.0001)
        assert result.decision == DecisionEnum.APPROVE

    def test_aggregator_boundary_revise_threshold_exactly_060(self) -> None:
        """Test decision at exact revise threshold boundary (0.60)."""
        # Create reviews that result in exactly 0.60 weighted confidence
        # Using: 0.60*0.25 + 0.60*0.25 + 0.60*0.15 + 0.60*0.20 + 0.60*0.15 = 0.60
        reviews = [
            create_persona_review("architect", "Architect", 0.60),
            create_persona_review("critic", "Critic", 0.60),
            create_persona_review("optimist", "Optimist", 0.60),
            create_persona_review("security_guardian", "SecurityGuardian", 0.60),
            create_persona_review("user_advocate", "UserAdvocate", 0.60),
        ]

        result = aggregate_persona_reviews(reviews)

        # At exactly 0.60, should use >= comparison and result in REVISE
        assert result.weighted_confidence == pytest.approx(0.60, abs=0.0001)
        assert result.decision == DecisionEnum.REVISE

    def test_aggregator_boundary_just_below_approve_threshold(self) -> None:
        """Test decision just below approve threshold (0.7999)."""
        # Create reviews that result in just below 0.80
        # Target: 0.7999
        # Using weighted average to get close to but below 0.80
        reviews = [
            create_persona_review("architect", "Architect", 0.7996),
            create_persona_review("critic", "Critic", 0.7996),
            create_persona_review("optimist", "Optimist", 0.7996),
            create_persona_review("security_guardian", "SecurityGuardian", 0.7996),
            create_persona_review("user_advocate", "UserAdvocate", 0.7996),
        ]

        result = aggregate_persona_reviews(reviews)

        # Just below 0.80 should result in REVISE
        assert result.weighted_confidence < 0.80
        assert result.weighted_confidence >= 0.60
        assert result.decision == DecisionEnum.REVISE

    def test_aggregator_boundary_just_below_revise_threshold(self) -> None:
        """Test decision just below revise threshold (0.5999)."""
        # Create reviews that result in just below 0.60
        reviews = [
            create_persona_review("architect", "Architect", 0.5996),
            create_persona_review("critic", "Critic", 0.5996),
            create_persona_review("optimist", "Optimist", 0.5996),
            create_persona_review("security_guardian", "SecurityGuardian", 0.5996),
            create_persona_review("user_advocate", "UserAdvocate", 0.5996),
        ]

        result = aggregate_persona_reviews(reviews)

        # Just below 0.60 should result in REJECT
        assert result.weighted_confidence < 0.60
        assert result.decision == DecisionEnum.REJECT

    def test_aggregator_floating_point_precision_near_threshold(self) -> None:
        """Test that floating point arithmetic doesn't cause incorrect decisions."""
        # Use confidence scores that could cause floating point drift
        # but should still be above 0.80
        reviews = [
            create_persona_review("architect", "Architect", 0.80000001),
            create_persona_review("critic", "Critic", 0.79999999),
            create_persona_review("optimist", "Optimist", 0.80000002),
            create_persona_review("security_guardian", "SecurityGuardian", 0.79999998),
            create_persona_review("user_advocate", "UserAdvocate", 0.80000001),
        ]

        result = aggregate_persona_reviews(reviews)

        # Should handle floating point precision and result in APPROVE
        # Weighted: ~0.80 (within floating point tolerance)
        assert result.weighted_confidence >= 0.799
        assert result.decision == DecisionEnum.APPROVE

    def test_aggregator_security_guardian_veto_with_null_security_critical(self) -> None:
        """Test SecurityGuardian with security_critical=None doesn't trigger veto."""
        reviews = [
            create_persona_review("architect", "Architect", 0.90),
            create_persona_review("critic", "Critic", 0.85),
            create_persona_review("optimist", "Optimist", 0.95),
            create_persona_review(
                "security_guardian",
                "SecurityGuardian",
                0.80,
                blocking_issues=[
                    BlockingIssue(text="Issue", security_critical=None)  # Explicitly None
                ],
            ),
            create_persona_review("user_advocate", "UserAdvocate", 0.90),
        ]

        result = aggregate_persona_reviews(reviews)

        # security_critical=None should not trigger veto
        assert result.weighted_confidence >= 0.80
        assert result.decision == DecisionEnum.APPROVE

    def test_aggregator_security_guardian_veto_forces_reject_when_below_revise(self) -> None:
        """Test SecurityGuardian veto doesn't upgrade a REJECT to REVISE."""
        reviews = [
            create_persona_review("architect", "Architect", 0.50),
            create_persona_review("critic", "Critic", 0.45),
            create_persona_review("optimist", "Optimist", 0.60),
            create_persona_review(
                "security_guardian",
                "SecurityGuardian",
                0.40,
                blocking_issues=[
                    BlockingIssue(text="Critical vuln", security_critical=True)
                ],
            ),
            create_persona_review("user_advocate", "UserAdvocate", 0.50),
        ]

        result = aggregate_persona_reviews(reviews)

        # Weighted confidence below 0.60 with security veto should still be REJECT
        # Veto only downgrades APPROVE to REVISE, doesn't change REJECT
        assert result.weighted_confidence < 0.60
        assert result.decision == DecisionEnum.REJECT

    def test_aggregator_minority_report_includes_concerns_and_strengths(self) -> None:
        """Test minority report includes concerns and strengths from review."""
        from consensus_engine.schemas.review import Concern

        concern1 = Concern(text="Major concern", is_blocking=True)
        concern2 = Concern(text="Minor concern", is_blocking=False)

        review_with_concerns = PersonaReview(
            persona_name="Critic",
            persona_id="critic",
            confidence_score=0.55,  # Low confidence
            strengths=["Good idea", "Clear goals"],
            concerns=[concern1, concern2],
            recommendations=["Fix the concerns"],
            blocking_issues=[],
            estimated_effort="2 weeks",
            dependency_risks=[],
        )

        reviews = [
            create_persona_review("architect", "Architect", 0.95),
            review_with_concerns,
            create_persona_review("optimist", "Optimist", 0.98),
            create_persona_review("security_guardian", "SecurityGuardian", 0.90),
            create_persona_review("user_advocate", "UserAdvocate", 0.95),
        ]

        result = aggregate_persona_reviews(reviews)

        # Should be APPROVE but with minority report for Critic
        assert result.decision == DecisionEnum.APPROVE
        assert result.minority_reports is not None
        assert len(result.minority_reports) > 0

        minority = result.minority_reports[0]
        assert minority.persona_id == "critic"
        assert minority.strengths == ["Good idea", "Clear goals"]
        assert minority.concerns == ["Major concern", "Minor concern"]
        assert "Fix the concerns" in minority.mitigation_recommendation
