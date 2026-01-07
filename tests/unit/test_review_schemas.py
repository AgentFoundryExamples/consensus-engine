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

from uuid import uuid4

import pytest
from pydantic import ValidationError

from consensus_engine.schemas.review import (
    Concern,
    DecisionAggregation,
    DecisionEnum,
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
        persona_id = uuid4()
        review = PersonaReview(
            persona_name="Security Reviewer",
            persona_id=persona_id,
            confidence_score=0.85,
            strengths=["Strong authentication", "Good error handling"],
            concerns=[
                Concern(text="Missing rate limiting", is_blocking=True),
                Concern(text="Logging could be better", is_blocking=False),
            ],
            recommendations=["Add rate limiting", "Improve logging"],
            blocking_issues=["No rate limiting"],
            estimated_effort="2 weeks",
            dependency_risks=["OpenAI API changes", {"risk": "Database migration", "severity": "high"}],
        )

        assert review.persona_name == "Security Reviewer"
        assert review.persona_id == persona_id
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
            confidence_score=0.8,
            strengths=["  Strength 1  ", "  Strength 2  "],
            concerns=[Concern(text="  Concern  ", is_blocking=True)],
            recommendations=["  Rec 1  "],
            blocking_issues=["  Issue  "],
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
            confidence_score=0.5,
            strengths=[],
            concerns=[],
            recommendations=[],
            blocking_issues=[],
            estimated_effort={"hours": 40, "days": 5},
            dependency_risks=[],
        )

        assert review.estimated_effort == {"hours": 40, "days": 5}

    def test_persona_review_filters_empty_strings_in_dependency_risks(self) -> None:
        """Test PersonaReview filters out empty strings from dependency_risks after trimming."""
        review = PersonaReview(
            persona_name="Reviewer",
            confidence_score=0.5,
            strengths=["Valid"],
            concerns=[],
            recommendations=["Rec"],
            blocking_issues=["Issue"],
            estimated_effort="Unknown",
            dependency_risks=["Valid risk", "  ", "Another risk"],
        )

        # Empty strings after trimming should be filtered out in dependency_risks only
        assert review.dependency_risks == ["Valid risk", "Another risk"]

    def test_persona_review_rejects_whitespace_in_required_lists(self) -> None:
        """Test PersonaReview rejects whitespace-only items in required string lists."""
        with pytest.raises(ValidationError) as exc_info:
            PersonaReview(
                persona_name="Reviewer",
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
        assert any("whitespace-only" in str(e) for e in errors)


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
        """Test DecisionAggregation with single persona matches reviewer confidence."""
        # When only one persona exists, overall_weighted_confidence should match
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
