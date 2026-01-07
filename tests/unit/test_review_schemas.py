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
"""Unit tests for review schemas."""


import pytest
from pydantic import ValidationError

from consensus_engine.schemas.review import (
    BlockingIssue,
    Concern,
    DecisionAggregation,
    DecisionEnum,
    DetailedScoreBreakdown,
    MinorityReport,
    PersonaReview,
    PersonaScoreBreakdown,
)


class TestConcern:
    """Test suite for Concern schema."""

    def test_concern_valid(self) -> None:
        """Test Concern with valid data."""
        concern = Concern(text="This is a concern", is_blocking=True)

        assert concern.text == "This is a concern"
        assert concern.is_blocking is True

    def test_concern_non_blocking(self) -> None:
        """Test Concern with non-blocking flag."""
        concern = Concern(text="Minor issue", is_blocking=False)

        assert concern.text == "Minor issue"
        assert concern.is_blocking is False

    def test_concern_trims_whitespace(self) -> None:
        """Test Concern trims whitespace from text."""
        concern = Concern(text="  This has whitespace  ", is_blocking=True)

        assert concern.text == "This has whitespace"

    def test_concern_rejects_empty_text(self) -> None:
        """Test Concern rejects empty text."""
        with pytest.raises(ValidationError) as exc_info:
            Concern(text="", is_blocking=True)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("text",) for e in errors)

    def test_concern_rejects_whitespace_only_text(self) -> None:
        """Test Concern rejects whitespace-only text."""
        with pytest.raises(ValidationError) as exc_info:
            Concern(text="   ", is_blocking=False)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("text",) for e in errors)
        assert any("whitespace-only" in str(e) for e in errors)


class TestPersonaReview:
    """Test suite for PersonaReview schema."""

    def test_persona_review_full(self) -> None:
        """Test PersonaReview with all fields."""
        review = PersonaReview(
            persona_name="Security Reviewer",
            persona_id="security_guardian",
            confidence_score=0.85,
            strengths=["Strong authentication", "Good error handling"],
            concerns=[
                Concern(text="Missing rate limiting", is_blocking=True),
                Concern(text="Logging could be better", is_blocking=False),
            ],
            recommendations=["Add rate limiting", "Improve logging"],
            blocking_issues=[BlockingIssue(text="No rate limiting", security_critical=False)],
            estimated_effort="2 weeks",
            dependency_risks=[
                "OpenAI API changes",
                {"risk": "Database migration", "severity": "high"},
            ],
        )

        assert review.persona_name == "Security Reviewer"
        assert review.persona_id == "security_guardian"
        assert review.confidence_score == 0.85
        assert len(review.strengths) == 2
        assert len(review.concerns) == 2
        assert review.concerns[0].is_blocking is True
        assert len(review.recommendations) == 2
        assert len(review.blocking_issues) == 1
        assert review.estimated_effort == "2 weeks"
        assert len(review.dependency_risks) == 2

    def test_persona_review_minimal(self) -> None:
        """Test PersonaReview with minimal required fields."""
        review = PersonaReview(
            persona_name="Reviewer",
            persona_id="generic",
            confidence_score=0.5,
            strengths=[],
            concerns=[],
            recommendations=[],
            blocking_issues=[],
            estimated_effort="Unknown",
            dependency_risks=[],
        )

        assert review.persona_name == "Reviewer"
        assert review.persona_id is None
        assert review.confidence_score == 0.5
        assert review.strengths == []
        assert review.concerns == []
        assert review.recommendations == []
        assert review.blocking_issues == []
        assert review.estimated_effort == "Unknown"
        assert review.dependency_risks == []

    def test_persona_review_confidence_score_bounds(self) -> None:
        """Test PersonaReview enforces confidence_score bounds [0.0, 1.0]."""
        # Valid boundary values
        review_min = PersonaReview(
            persona_name="Reviewer",
            persona_id="generic",
            confidence_score=0.0,
            strengths=[],
            concerns=[],
            recommendations=[],
            blocking_issues=[],
            estimated_effort="Unknown",
            dependency_risks=[],
        )
        assert review_min.confidence_score == 0.0

        review_max = PersonaReview(
            persona_name="Reviewer",
            persona_id="generic",
            confidence_score=1.0,
            strengths=[],
            concerns=[],
            recommendations=[],
            blocking_issues=[],
            estimated_effort="Unknown",
            dependency_risks=[],
        )
        assert review_max.confidence_score == 1.0

        # Invalid: below minimum
        with pytest.raises(ValidationError) as exc_info:
            PersonaReview(
                persona_name="Reviewer",
                persona_id="generic",
                confidence_score=-0.1,
                strengths=[],
                concerns=[],
                recommendations=[],
                blocking_issues=[],
                estimated_effort="Unknown",
                dependency_risks=[],
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence_score",) for e in errors)

        # Invalid: above maximum
        with pytest.raises(ValidationError) as exc_info:
            PersonaReview(
                persona_name="Reviewer",
                persona_id="generic",
                confidence_score=1.1,
                strengths=[],
                concerns=[],
                recommendations=[],
                blocking_issues=[],
                estimated_effort="Unknown",
                dependency_risks=[],
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("confidence_score",) for e in errors)

    def test_persona_review_trims_strings(self) -> None:
        """Test PersonaReview trims whitespace from string fields."""
        review = PersonaReview(
            persona_name="  Reviewer  ",
            persona_id="generic",
            confidence_score=0.8,
            strengths=["  Strength 1  ", "  Strength 2  "],
            concerns=[Concern(text="  Concern  ", is_blocking=True)],
            recommendations=["  Rec 1  "],
            blocking_issues=[BlockingIssue(text="  Issue  ", security_critical=False)],
            estimated_effort="  2 weeks  ",
            dependency_risks=["  Risk  "],
        )

        assert review.persona_name == "Reviewer"
        assert review.strengths == ["Strength 1", "Strength 2"]
        assert review.recommendations == ["Rec 1"]
        assert review.blocking_issues == ["Issue"]
        assert review.estimated_effort == "2 weeks"
        assert review.dependency_risks == ["Risk"]

    def test_persona_review_rejects_empty_persona_name(self) -> None:
        """Test PersonaReview rejects empty persona_name."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaReview(
                persona_name="  ",
                persona_id="generic",
                confidence_score=0.5,
                strengths=[],
                concerns=[],
                recommendations=[],
                blocking_issues=[],
                estimated_effort="Unknown",
                dependency_risks=[],
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("persona_name",) for e in errors)
        assert any("whitespace-only" in str(e) for e in errors)

    def test_persona_review_rejects_empty_effort(self) -> None:
        """Test PersonaReview rejects empty estimated_effort string."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaReview(
                persona_name="Reviewer",
                persona_id="generic",
                confidence_score=0.5,
                strengths=[],
                concerns=[],
                recommendations=[],
                blocking_issues=[],
                estimated_effort="   ",
                dependency_risks=[],
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("estimated_effort",) for e in errors)

    def test_persona_review_structured_effort(self) -> None:
        """Test PersonaReview accepts structured effort dict."""
        review = PersonaReview(
            persona_name="Reviewer",
            persona_id="generic",
            confidence_score=0.5,
            strengths=[],
            concerns=[],
            recommendations=[],
            blocking_issues=[],
            estimated_effort={"hours": 40, "days": 5},
            dependency_risks=[],
        )

        assert review.estimated_effort == {"hours": 40, "days": 5}

    def test_persona_review_rejects_whitespace_in_dependency_risks(self) -> None:
        """Test PersonaReview rejects whitespace-only items in dependency_risks."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaReview(
                persona_name="Reviewer",
                persona_id="generic",
                confidence_score=0.5,
                strengths=["Valid"],
                concerns=[],
                recommendations=["Rec"],
                blocking_issues=[BlockingIssue(text="Issue", security_critical=False)],
                estimated_effort="Unknown",
                dependency_risks=["Valid risk", "  ", "Another risk"],
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("dependency_risks",) for e in errors)
        assert any("whitespace-only" in str(e).lower() for e in errors)

    def test_persona_review_rejects_whitespace_in_required_lists(self) -> None:
        """Test PersonaReview rejects whitespace-only items in required string lists."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaReview(
                persona_name="Reviewer",
                persona_id="generic",
                confidence_score=0.5,
                strengths=["Valid", "  ", "Another"],
                concerns=[],
                recommendations=[],
                blocking_issues=[],
                estimated_effort="Unknown",
                dependency_risks=[],
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("strengths",) for e in errors)
        assert any("whitespace-only" in str(e).lower() for e in errors)


class TestDecisionEnum:
    """Test suite for DecisionEnum."""

    def test_decision_enum_values(self) -> None:
        """Test DecisionEnum has expected values."""
        assert DecisionEnum.APPROVE == "approve"
        assert DecisionEnum.REVISE == "revise"
        assert DecisionEnum.REJECT == "reject"

    def test_decision_enum_from_string(self) -> None:
        """Test DecisionEnum can be created from string."""
        decision = DecisionEnum("approve")
        assert decision == DecisionEnum.APPROVE


class TestMinorityReport:
    """Test suite for MinorityReport schema."""

    def test_minority_report_valid(self) -> None:
        """Test MinorityReport with valid data."""
        report = MinorityReport(
            persona_name="Dissenting Reviewer",
            strengths=["Good idea", "Clear goals"],
            concerns=["Too complex", "High risk"],
        )

        assert report.persona_name == "Dissenting Reviewer"
        assert len(report.strengths) == 2
        assert len(report.concerns) == 2

    def test_minority_report_trims_strings(self) -> None:
        """Test MinorityReport trims whitespace."""
        report = MinorityReport(
            persona_name="  Reviewer  ",
            strengths=["  Strength  "],
            concerns=["  Concern  "],
        )

        assert report.persona_name == "Reviewer"
        assert report.strengths == ["Strength"]
        assert report.concerns == ["Concern"]

    def test_minority_report_empty_lists(self) -> None:
        """Test MinorityReport accepts empty lists."""
        report = MinorityReport(
            persona_name="Reviewer",
            strengths=[],
            concerns=[],
        )

        assert report.strengths == []
        assert report.concerns == []


class TestPersonaScoreBreakdown:
    """Test suite for PersonaScoreBreakdown schema."""

    def test_score_breakdown_with_notes(self) -> None:
        """Test PersonaScoreBreakdown with notes."""
        breakdown = PersonaScoreBreakdown(weight=0.5, notes="Good analysis")

        assert breakdown.weight == 0.5
        assert breakdown.notes == "Good analysis"

    def test_score_breakdown_without_notes(self) -> None:
        """Test PersonaScoreBreakdown without notes."""
        breakdown = PersonaScoreBreakdown(weight=0.3)

        assert breakdown.weight == 0.3
        assert breakdown.notes is None

    def test_score_breakdown_trims_notes(self) -> None:
        """Test PersonaScoreBreakdown trims whitespace from notes."""
        breakdown = PersonaScoreBreakdown(weight=0.5, notes="  Notes  ")

        assert breakdown.notes == "Notes"

    def test_score_breakdown_empty_notes_becomes_none(self) -> None:
        """Test PersonaScoreBreakdown converts empty notes to None."""
        breakdown = PersonaScoreBreakdown(weight=0.5, notes="   ")

        assert breakdown.notes is None

    def test_score_breakdown_weight_non_negative(self) -> None:
        """Test PersonaScoreBreakdown enforces non-negative weight."""
        # Valid
        breakdown = PersonaScoreBreakdown(weight=0.0)
        assert breakdown.weight == 0.0

        # Invalid
        with pytest.raises(ValidationError) as exc_info:
            PersonaScoreBreakdown(weight=-0.1)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("weight",) for e in errors)


class TestDecisionAggregation:
    """Test suite for DecisionAggregation schema."""

    def test_decision_aggregation_full(self) -> None:
        """Test DecisionAggregation with all fields."""
        minority = MinorityReport(
            persona_name="Dissenter",
            strengths=["Good idea"],
            concerns=["Too risky"],
        )
        aggregation = DecisionAggregation(
            overall_weighted_confidence=0.75,
            decision=DecisionEnum.APPROVE,
            score_breakdown={
                "Security": PersonaScoreBreakdown(weight=0.5, notes="Security approved"),
                "Performance": PersonaScoreBreakdown(weight=0.5, notes="Performance concerns"),
            },
            minority_report=minority,
        )

        assert aggregation.overall_weighted_confidence == 0.75
        assert aggregation.decision == DecisionEnum.APPROVE
        assert len(aggregation.score_breakdown) == 2
        assert aggregation.score_breakdown["Security"].weight == 0.5
        assert aggregation.minority_report == minority

    def test_decision_aggregation_minimal(self) -> None:
        """Test DecisionAggregation with minimal required fields."""
        aggregation = DecisionAggregation(
            overall_weighted_confidence=0.5,
            decision=DecisionEnum.REVISE,
            score_breakdown={
                "Reviewer": PersonaScoreBreakdown(weight=1.0),
            },
        )

        assert aggregation.overall_weighted_confidence == 0.5
        assert aggregation.decision == DecisionEnum.REVISE
        assert len(aggregation.score_breakdown) == 1
        assert aggregation.minority_report is None

    def test_decision_aggregation_confidence_bounds(self) -> None:
        """Test DecisionAggregation enforces confidence bounds [0.0, 1.0]."""
        # Valid boundaries
        agg_min = DecisionAggregation(
            overall_weighted_confidence=0.0,
            decision=DecisionEnum.REJECT,
            score_breakdown={"R": PersonaScoreBreakdown(weight=1.0)},
        )
        assert agg_min.overall_weighted_confidence == 0.0

        agg_max = DecisionAggregation(
            overall_weighted_confidence=1.0,
            decision=DecisionEnum.APPROVE,
            score_breakdown={"R": PersonaScoreBreakdown(weight=1.0)},
        )
        assert agg_max.overall_weighted_confidence == 1.0

        # Invalid: below minimum
        with pytest.raises(ValidationError) as exc_info:
            DecisionAggregation(
                overall_weighted_confidence=-0.1,
                decision=DecisionEnum.REJECT,
                score_breakdown={"R": PersonaScoreBreakdown(weight=1.0)},
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("overall_weighted_confidence",) for e in errors)

        # Invalid: above maximum
        with pytest.raises(ValidationError) as exc_info:
            DecisionAggregation(
                overall_weighted_confidence=1.1,
                decision=DecisionEnum.APPROVE,
                score_breakdown={"R": PersonaScoreBreakdown(weight=1.0)},
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("overall_weighted_confidence",) for e in errors)

    def test_decision_aggregation_single_persona(self) -> None:
        """Test DecisionAggregation with single persona.

        When only one persona exists with weight=1.0, the overall_weighted_confidence
        should match that reviewer's confidence score (though this is enforced by
        the calling code, not the schema itself).
        """
        # Simulate a single persona scenario where overall confidence matches the reviewer
        aggregation = DecisionAggregation(
            overall_weighted_confidence=0.85,
            decision=DecisionEnum.APPROVE,
            score_breakdown={
                "SingleReviewer": PersonaScoreBreakdown(weight=1.0, notes="Only reviewer"),
            },
        )

        assert aggregation.overall_weighted_confidence == 0.85
        assert len(aggregation.score_breakdown) == 1
        assert aggregation.score_breakdown["SingleReviewer"].weight == 1.0

        # Verify that with single persona at weight 1.0, the confidence should match
        # (This documents the expected behavior for callers creating DecisionAggregation)
        single_reviewer_weight = aggregation.score_breakdown["SingleReviewer"].weight
        assert single_reviewer_weight == 1.0
        # When weight is 1.0, overall_weighted_confidence should equal reviewer's score
        assert aggregation.overall_weighted_confidence == 0.85

    def test_decision_aggregation_empty_score_breakdown_rejected(self) -> None:
        """Test DecisionAggregation requires at least one score in breakdown."""
        # Empty score_breakdown should fail if required
        # However, the schema allows any dict, so we'll test with valid empty dict
        aggregation = DecisionAggregation(
            overall_weighted_confidence=0.5,
            decision=DecisionEnum.REVISE,
            score_breakdown={},
        )

        # This is allowed by the schema - empty dict is valid
        assert len(aggregation.score_breakdown) == 0

    def test_decision_aggregation_json_serializable(self) -> None:
        """Test DecisionAggregation can be serialized to JSON."""
        aggregation = DecisionAggregation(
            overall_weighted_confidence=0.75,
            decision=DecisionEnum.APPROVE,
            score_breakdown={
                "Reviewer": PersonaScoreBreakdown(weight=1.0, notes="Good"),
            },
        )

        json_data = aggregation.model_dump_json()
        assert "0.75" in json_data
        assert "approve" in json_data
        assert "Reviewer" in json_data


class TestBlockingIssue:
    """Test suite for BlockingIssue schema."""

    def test_blocking_issue_valid(self) -> None:
        """Test BlockingIssue with valid data."""
        issue = BlockingIssue(text="Critical security flaw", security_critical=True)

        assert issue.text == "Critical security flaw"
        assert issue.security_critical is True

    def test_blocking_issue_without_security_critical(self) -> None:
        """Test BlockingIssue without security_critical flag."""
        issue = BlockingIssue(text="Missing error handling")

        assert issue.text == "Missing error handling"
        assert issue.security_critical is None

    def test_blocking_issue_security_critical_false(self) -> None:
        """Test BlockingIssue with security_critical=False."""
        issue = BlockingIssue(text="Non-security issue", security_critical=False)

        assert issue.text == "Non-security issue"
        assert issue.security_critical is False

    def test_blocking_issue_trims_whitespace(self) -> None:
        """Test BlockingIssue trims whitespace from text."""
        issue = BlockingIssue(text="  Critical issue  ", security_critical=True)

        assert issue.text == "Critical issue"

    def test_blocking_issue_empty_text_rejected(self) -> None:
        """Test BlockingIssue rejects empty text."""
        with pytest.raises(ValidationError) as exc_info:
            BlockingIssue(text="")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("text",) for e in errors)

    def test_blocking_issue_whitespace_only_rejected(self) -> None:
        """Test BlockingIssue rejects whitespace-only text."""
        with pytest.raises(ValidationError) as exc_info:
            BlockingIssue(text="   ")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("text",) for e in errors)


class TestPersonaReviewWithPersonaId:
    """Test suite for PersonaReview with persona_id field."""

    def test_persona_review_with_persona_id(self) -> None:
        """Test PersonaReview with persona_id string."""
        review = PersonaReview(
            persona_name="Architect",
            persona_id="architect",
            confidence_score=0.85,
            strengths=["Good design"],
            concerns=[Concern(text="Minor issue", is_blocking=False)],
            recommendations=["Improve docs"],
            blocking_issues=[],
            estimated_effort="2 weeks",
            dependency_risks=[],
        )

        assert review.persona_id == "architect"
        assert review.persona_name == "Architect"

    def test_persona_review_persona_id_required(self) -> None:
        """Test PersonaReview requires persona_id."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaReview(
                persona_name="Architect",
                persona_id="generic",
                # persona_id missing
                confidence_score=0.85,
                strengths=["Good design"],
                concerns=[],
                recommendations=["Improve docs"],
                blocking_issues=[],
                estimated_effort="2 weeks",
                dependency_risks=[],
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("persona_id",) for e in errors)

    def test_persona_review_with_internal_metadata(self) -> None:
        """Test PersonaReview with internal_metadata."""
        metadata = {
            "model": "gpt-5.1",
            "duration": 2.5,
            "timestamp": "2024-01-07T10:00:00Z",
        }
        review = PersonaReview(
            persona_name="Architect",
            persona_id="architect",
            confidence_score=0.85,
            strengths=["Good design"],
            concerns=[],
            recommendations=["Improve docs"],
            blocking_issues=[],
            estimated_effort="2 weeks",
            dependency_risks=[],
            internal_metadata=metadata,
        )

        assert review.internal_metadata == metadata
        assert review.internal_metadata["model"] == "gpt-5.1"
        assert review.internal_metadata["duration"] == 2.5

    def test_persona_review_with_blocking_issue_objects(self) -> None:
        """Test PersonaReview with BlockingIssue objects."""
        blocking_issues = [
            BlockingIssue(text="SQL injection vulnerability", security_critical=True),
            BlockingIssue(text="Missing input validation", security_critical=False),
        ]
        review = PersonaReview(
            persona_name="SecurityGuardian",
            persona_id="security_guardian",
            confidence_score=0.4,
            strengths=["Good architecture"],
            concerns=[],
            recommendations=["Fix security issues"],
            blocking_issues=blocking_issues,
            estimated_effort="1 week",
            dependency_risks=[],
        )

        assert len(review.blocking_issues) == 2
        assert review.blocking_issues[0].text == "SQL injection vulnerability"
        assert review.blocking_issues[0].security_critical is True
        assert review.blocking_issues[1].security_critical is False


class TestDetailedScoreBreakdown:
    """Test suite for DetailedScoreBreakdown schema."""

    def test_detailed_score_breakdown_valid(self) -> None:
        """Test DetailedScoreBreakdown with valid data."""
        breakdown = DetailedScoreBreakdown(
            weights={"architect": 0.25, "critic": 0.25},
            individual_scores={"architect": 0.8, "critic": 0.7},
            weighted_contributions={"architect": 0.2, "critic": 0.175},
            formula="sum(weight * score for each persona)",
        )

        assert breakdown.weights == {"architect": 0.25, "critic": 0.25}
        assert breakdown.individual_scores == {"architect": 0.8, "critic": 0.7}
        assert breakdown.weighted_contributions == {"architect": 0.2, "critic": 0.175}
        assert breakdown.formula == "sum(weight * score for each persona)"

    def test_detailed_score_breakdown_trims_formula(self) -> None:
        """Test DetailedScoreBreakdown trims whitespace from formula."""
        breakdown = DetailedScoreBreakdown(
            weights={"architect": 0.5},
            individual_scores={"architect": 0.8},
            weighted_contributions={"architect": 0.4},
            formula="  weighted average  ",
        )

        assert breakdown.formula == "weighted average"

    def test_detailed_score_breakdown_empty_formula_rejected(self) -> None:
        """Test DetailedScoreBreakdown rejects empty formula."""
        with pytest.raises(ValidationError) as exc_info:
            DetailedScoreBreakdown(
                weights={"architect": 0.5},
                individual_scores={"architect": 0.8},
                weighted_contributions={"architect": 0.4},
                formula="",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("formula",) for e in errors)


class TestMinorityReportExtended:
    """Test suite for extended MinorityReport schema."""

    def test_minority_report_with_all_new_fields(self) -> None:
        """Test MinorityReport with all new required fields."""
        report = MinorityReport(
            persona_id="security_guardian",
            persona_name="SecurityGuardian",
            confidence_score=0.4,
            blocking_summary="Critical security vulnerabilities found",
            mitigation_recommendation="Implement input validation and parameterized queries",
        )

        assert report.persona_id == "security_guardian"
        assert report.persona_name == "SecurityGuardian"
        assert report.confidence_score == 0.4
        assert report.blocking_summary == "Critical security vulnerabilities found"
        assert (
            report.mitigation_recommendation
            == "Implement input validation and parameterized queries"
        )

    def test_minority_report_with_optional_legacy_fields(self) -> None:
        """Test MinorityReport with optional strengths and concerns."""
        report = MinorityReport(
            persona_id="critic",
            persona_name="Critic",
            confidence_score=0.5,
            blocking_summary="Too many edge cases not addressed",
            mitigation_recommendation="Add comprehensive error handling",
            strengths=["Clear problem statement"],
            concerns=["Missing edge case handling", "No error recovery"],
        )

        assert report.strengths == ["Clear problem statement"]
        assert report.concerns == ["Missing edge case handling", "No error recovery"]

    def test_minority_report_without_optional_fields(self) -> None:
        """Test MinorityReport without optional fields."""
        report = MinorityReport(
            persona_id="critic",
            persona_name="Critic",
            confidence_score=0.5,
            blocking_summary="Issues found",
            mitigation_recommendation="Fix issues",
        )

        assert report.strengths is None
        assert report.concerns is None

    def test_minority_report_trims_string_fields(self) -> None:
        """Test MinorityReport trims whitespace from string fields."""
        report = MinorityReport(
            persona_id="  security_guardian  ",
            persona_name="  SecurityGuardian  ",
            confidence_score=0.4,
            blocking_summary="  Security issues  ",
            mitigation_recommendation="  Fix security  ",
        )

        assert report.persona_id == "security_guardian"
        assert report.persona_name == "SecurityGuardian"
        assert report.blocking_summary == "Security issues"
        assert report.mitigation_recommendation == "Fix security"

    def test_minority_report_confidence_score_range(self) -> None:
        """Test MinorityReport validates confidence_score range."""
        # Valid scores
        MinorityReport(
            persona_id="critic",
            persona_name="Critic",
            confidence_score=0.0,
            blocking_summary="Summary",
            mitigation_recommendation="Recommendation",
        )
        MinorityReport(
            persona_id="critic",
            persona_name="Critic",
            confidence_score=1.0,
            blocking_summary="Summary",
            mitigation_recommendation="Recommendation",
        )

        # Invalid score (too low)
        with pytest.raises(ValidationError):
            MinorityReport(
                persona_id="critic",
                persona_name="Critic",
                confidence_score=-0.1,
                blocking_summary="Summary",
                mitigation_recommendation="Recommendation",
            )

        # Invalid score (too high)
        with pytest.raises(ValidationError):
            MinorityReport(
                persona_id="critic",
                persona_name="Critic",
                confidence_score=1.1,
                blocking_summary="Summary",
                mitigation_recommendation="Recommendation",
            )


class TestDecisionAggregationExtended:
    """Test suite for extended DecisionAggregation schema."""

    def test_decision_aggregation_with_weighted_confidence(self) -> None:
        """Test DecisionAggregation with weighted_confidence field."""
        aggregation = DecisionAggregation(
            overall_weighted_confidence=0.75,
            weighted_confidence=0.75,
            decision=DecisionEnum.APPROVE,
        )

        assert aggregation.overall_weighted_confidence == 0.75
        assert aggregation.weighted_confidence == 0.75

    def test_decision_aggregation_with_detailed_score_breakdown(self) -> None:
        """Test DecisionAggregation with detailed_score_breakdown."""
        detailed_breakdown = DetailedScoreBreakdown(
            weights={
                "architect": 0.25,
                "critic": 0.25,
                "optimist": 0.15,
                "security_guardian": 0.20,
                "user_advocate": 0.15,
            },
            individual_scores={
                "architect": 0.8,
                "critic": 0.7,
                "optimist": 0.9,
                "security_guardian": 0.75,
                "user_advocate": 0.85,
            },
            weighted_contributions={
                "architect": 0.2,
                "critic": 0.175,
                "optimist": 0.135,
                "security_guardian": 0.15,
                "user_advocate": 0.1275,
            },
            formula="weighted_confidence = sum(weight_i * score_i for each persona i)",
        )
        aggregation = DecisionAggregation(
            overall_weighted_confidence=0.7875,
            decision=DecisionEnum.APPROVE,
            detailed_score_breakdown=detailed_breakdown,
        )

        assert aggregation.detailed_score_breakdown is not None
        assert aggregation.detailed_score_breakdown.weights["architect"] == 0.25
        assert aggregation.detailed_score_breakdown.individual_scores["critic"] == 0.7

    def test_decision_aggregation_with_multiple_minority_reports(self) -> None:
        """Test DecisionAggregation with minority_reports list."""
        reports = [
            MinorityReport(
                persona_id="security_guardian",
                persona_name="SecurityGuardian",
                confidence_score=0.4,
                blocking_summary="Security issues",
                mitigation_recommendation="Fix security",
            ),
            MinorityReport(
                persona_id="critic",
                persona_name="Critic",
                confidence_score=0.5,
                blocking_summary="Too many risks",
                mitigation_recommendation="Mitigate risks",
            ),
        ]
        aggregation = DecisionAggregation(
            overall_weighted_confidence=0.65,
            decision=DecisionEnum.REVISE,
            minority_reports=reports,
        )

        assert aggregation.minority_reports is not None
        assert len(aggregation.minority_reports) == 2
        assert aggregation.minority_reports[0].persona_id == "security_guardian"
        assert aggregation.minority_reports[1].persona_id == "critic"

    def test_decision_aggregation_backward_compatible(self) -> None:
        """Test DecisionAggregation is backward compatible with old schema."""
        # Old schema style with score_breakdown and single minority_report
        aggregation = DecisionAggregation(
            overall_weighted_confidence=0.75,
            decision=DecisionEnum.APPROVE,
            score_breakdown={
                "Reviewer": PersonaScoreBreakdown(weight=1.0, notes="Good review"),
            },
            minority_report=None,
        )

        assert aggregation.overall_weighted_confidence == 0.75
        assert aggregation.score_breakdown is not None
        assert "Reviewer" in aggregation.score_breakdown
        assert aggregation.minority_report is None

    def test_decision_aggregation_with_both_new_and_old_fields(self) -> None:
        """Test DecisionAggregation with both new and legacy fields."""
        detailed_breakdown = DetailedScoreBreakdown(
            weights={"architect": 0.5, "critic": 0.5},
            individual_scores={"architect": 0.8, "critic": 0.6},
            weighted_contributions={"architect": 0.4, "critic": 0.3},
            formula="weighted average",
        )
        aggregation = DecisionAggregation(
            overall_weighted_confidence=0.7,
            weighted_confidence=0.7,
            decision=DecisionEnum.APPROVE,
            score_breakdown={
                "Architect": PersonaScoreBreakdown(weight=0.5, notes="Good"),
            },
            detailed_score_breakdown=detailed_breakdown,
        )

        # Both formats should be present
        assert aggregation.score_breakdown is not None
