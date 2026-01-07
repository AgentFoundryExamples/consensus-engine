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
"""Unit tests for request validation edge cases.

This module tests boundary conditions, edge cases, and validation rules
for request schemas including sentence counting, payload size limits,
and input constraints.
"""

import pytest
from pydantic import ValidationError

from consensus_engine.schemas.requests import ExpandIdeaRequest, count_sentences


class TestSentenceCountingEdgeCases:
    """Test suite for sentence counting edge cases and boundary conditions."""

    def test_count_sentences_with_abbreviations(self) -> None:
        """Test sentence counting with common abbreviations."""
        # Abbreviations with periods are counted as separate sentences
        # due to simple period splitting - this is a known limitation
        text = "Dr. Smith works at U.S. headquarters. This is the second sentence."
        count = count_sentences(text)
        # The regex splits on periods, so "Dr." "U.S." and the two actual sentences = 4
        assert count == 4

    def test_count_sentences_with_multiple_spaces(self) -> None:
        """Test sentence counting with multiple spaces between sentences."""
        text = "First sentence.    Second sentence.     Third sentence."
        assert count_sentences(text) == 3

    def test_count_sentences_with_newlines(self) -> None:
        """Test sentence counting with newlines between sentences."""
        text = "First sentence.\nSecond sentence.\nThird sentence."
        assert count_sentences(text) == 3

    def test_count_sentences_with_tabs(self) -> None:
        """Test sentence counting with tabs."""
        text = "First sentence.\t\tSecond sentence."
        assert count_sentences(text) == 2

    def test_count_sentences_with_mixed_whitespace(self) -> None:
        """Test sentence counting with mixed whitespace characters."""
        text = "First.  \n\tSecond. \r\n Third."
        assert count_sentences(text) == 3

    def test_count_sentences_ellipsis(self) -> None:
        """Test sentence counting with ellipsis."""
        text = "This is incomplete... But this is complete."
        # Ellipsis is treated as sentence ending punctuation
        count = count_sentences(text)
        assert count == 2

    def test_count_sentences_no_ending_punctuation(self) -> None:
        """Test sentence counting with no ending punctuation."""
        text = "This is a single sentence without ending punctuation"
        assert count_sentences(text) == 1

    def test_count_sentences_only_punctuation(self) -> None:
        """Test sentence counting with only punctuation."""
        text = "...!!!"
        count = count_sentences(text)
        # A string with only punctuation should not count as a sentence
        assert count == 0


class TestExpandIdeaRequestEdgeCases:
    """Test suite for ExpandIdeaRequest validation edge cases."""

    def test_reject_whitespace_only_idea(self) -> None:
        """Test rejection of whitespace-only idea."""
        with pytest.raises(ValidationError) as exc_info:
            ExpandIdeaRequest(idea="   \n\t   ")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("idea",) for error in errors)

    def test_accept_idea_with_leading_trailing_whitespace(self) -> None:
        """Test that ideas with leading/trailing whitespace are accepted."""
        request = ExpandIdeaRequest(idea="  Build a REST API.  ")
        # Pydantic does not strip whitespace from string fields
        assert request.idea == "  Build a REST API.  "
        # The sentence counting validator operates on the stripped version
        # so whitespace doesn't affect validation

    def test_reject_idea_with_11_sentences(self) -> None:
        """Test rejection of idea with exactly 11 sentences (boundary)."""
        idea = " ".join([f"Sentence {i}." for i in range(1, 12)])
        with pytest.raises(ValidationError) as exc_info:
            ExpandIdeaRequest(idea=idea)

        errors = exc_info.value.errors()
        assert any("must contain at most 10 sentences" in str(error) for error in errors)

    def test_accept_idea_with_exactly_10_sentences(self) -> None:
        """Test acceptance of idea with exactly 10 sentences (boundary)."""
        idea = " ".join([f"Sentence {i}." for i in range(1, 11)])
        request = ExpandIdeaRequest(idea=idea)
        assert request.idea == idea

    def test_accept_idea_with_exactly_1_sentence(self) -> None:
        """Test acceptance of idea with exactly 1 sentence (boundary)."""
        request = ExpandIdeaRequest(idea="Single sentence.")
        assert request.idea == "Single sentence."

    def test_extra_context_as_empty_string(self) -> None:
        """Test that empty string extra_context is accepted."""
        request = ExpandIdeaRequest(idea="Build an API.", extra_context="")
        assert request.extra_context == ""

    def test_extra_context_as_empty_dict(self) -> None:
        """Test that empty dict extra_context is accepted."""
        request = ExpandIdeaRequest(idea="Build an API.", extra_context={})
        assert request.extra_context == {}

    def test_extra_context_with_nested_structures(self) -> None:
        """Test extra_context with deeply nested data structures."""
        context = {
            "requirements": {
                "technical": {
                    "language": "Python",
                    "version": "3.11+",
                    "frameworks": ["FastAPI", "SQLAlchemy"],
                },
                "business": {"budget": 50000, "timeline": "3 months"},
            },
            "constraints": ["Must be scalable", "Must be secure"],
        }
        request = ExpandIdeaRequest(idea="Build an API.", extra_context=context)
        assert request.extra_context == context

    def test_extra_context_with_special_characters(self) -> None:
        """Test extra_context with special characters and unicode."""
        context = 'Must support UTF-8: émojis 🎉, symbols ©, and quotes "test"'
        request = ExpandIdeaRequest(idea="Build an API.", extra_context=context)
        assert request.extra_context == context

    def test_idea_with_unicode_characters(self) -> None:
        """Test idea with unicode characters."""
        idea = "Build an API that supports émojis 🎉 and international characters."
        request = ExpandIdeaRequest(idea=idea)
        assert request.idea == idea

    def test_very_long_single_sentence(self) -> None:
        """Test validation of a very long single sentence."""
        # Create a very long single sentence (no ending punctuation until the end)
        long_sentence = (
            "Build a comprehensive REST API that supports user management, "
            "authentication, authorization, data persistence, caching, logging, "
            "monitoring, error handling, rate limiting, and documentation."
        )
        request = ExpandIdeaRequest(idea=long_sentence)
        assert request.idea == long_sentence

    def test_idea_with_multiple_question_marks(self) -> None:
        """Test idea with multiple consecutive question marks."""
        idea = "What is the problem?? How do we solve it?"
        request = ExpandIdeaRequest(idea=idea)
        assert request.idea == idea

    def test_idea_with_multiple_exclamation_marks(self) -> None:
        """Test idea with multiple consecutive exclamation marks."""
        idea = "Build an amazing API!! It will be great!"
        request = ExpandIdeaRequest(idea=idea)
        assert request.idea == idea

    def test_idea_with_mixed_endings(self) -> None:
        """Test idea with mixed sentence endings."""
        idea = "First. Second! Third? Fourth."
        request = ExpandIdeaRequest(idea=idea)
        assert request.idea == idea
        assert count_sentences(idea) == 4

    def test_reject_none_as_idea(self) -> None:
        """Test that None is rejected as idea value."""
        with pytest.raises(ValidationError):
            ExpandIdeaRequest(idea=None)  # type: ignore

    def test_reject_numeric_idea(self) -> None:
        """Test that numeric values are rejected as idea."""
        with pytest.raises(ValidationError):
            ExpandIdeaRequest(idea=123)  # type: ignore

    def test_reject_list_as_idea(self) -> None:
        """Test that list is rejected as idea value."""
        with pytest.raises(ValidationError):
            ExpandIdeaRequest(idea=["Build", "an", "API"])  # type: ignore


class TestConfigDefaultBehavior:
    """Test suite for configuration defaults and boundary values."""

    def test_extra_context_defaults_to_none(self) -> None:
        """Test that extra_context defaults to None when not provided."""
        request = ExpandIdeaRequest(idea="Build an API.")
        assert request.extra_context is None

    def test_model_serialization_excludes_none_by_default(self) -> None:
        """Test model serialization behavior with None values."""
        request = ExpandIdeaRequest(idea="Build an API.")
        # model_dump includes None values by default
        data = request.model_dump()
        assert "extra_context" in data
        assert data["extra_context"] is None

    def test_model_serialization_with_exclude_none(self) -> None:
        """Test model serialization with exclude_none option."""
        request = ExpandIdeaRequest(idea="Build an API.")
        data = request.model_dump(exclude_none=True)
        assert "extra_context" not in data

    def test_json_serialization_with_extra_context(self) -> None:
        """Test JSON serialization round-trip with extra_context."""
        original = ExpandIdeaRequest(
            idea="Build an API.", extra_context={"key": "value", "count": 42}
        )
        json_str = original.model_dump_json()
        # Perform a full round-trip validation
        rehydrated = ExpandIdeaRequest.model_validate_json(json_str)
        assert rehydrated == original


class TestExpandedProposalValidationEdgeCases:
    """Test suite for ExpandedProposal validation edge cases."""

    def test_expanded_proposal_with_unicode(self) -> None:
        """Test ExpandedProposal accepts unicode characters."""
        from consensus_engine.schemas.proposal import ExpandedProposal

        proposal = ExpandedProposal(
            problem_statement="Problème avec émojis 🎉",
            proposed_solution="Solution avec caractères spéciaux ©",
            assumptions=["Assumption with émojis 🚀"],
            scope_non_goals=["Non-goal with unicode ™"],
        )

        assert "émojis" in proposal.problem_statement
        assert "🎉" in proposal.problem_statement
        assert "©" in proposal.proposed_solution

    def test_expanded_proposal_very_long_strings(self) -> None:
        """Test ExpandedProposal handles very long strings."""
        from consensus_engine.schemas.proposal import ExpandedProposal

        long_text = "A" * 10000
        proposal = ExpandedProposal(
            problem_statement=long_text,
            proposed_solution=long_text,
            assumptions=[long_text],
            scope_non_goals=[long_text],
        )

        assert len(proposal.problem_statement) == 10000
        assert len(proposal.proposed_solution) == 10000
        assert len(proposal.assumptions[0]) == 10000

    def test_expanded_proposal_many_list_items(self) -> None:
        """Test ExpandedProposal handles many list items."""
        from consensus_engine.schemas.proposal import ExpandedProposal

        many_items = [f"Item {i}" for i in range(1000)]
        proposal = ExpandedProposal(
            problem_statement="Problem",
            proposed_solution="Solution",
            assumptions=many_items,
            scope_non_goals=many_items,
        )

        assert len(proposal.assumptions) == 1000
        assert len(proposal.scope_non_goals) == 1000


class TestPersonaReviewValidationEdgeCases:
    """Test suite for PersonaReview validation edge cases."""

    def test_persona_review_confidence_precision(self) -> None:
        """Test PersonaReview handles high-precision confidence scores."""
        from consensus_engine.schemas.review import PersonaReview

        review = PersonaReview(
            persona_name="Reviewer",
            persona_id="reviewer",
            confidence_score=0.123456789,
            strengths=[],
            concerns=[],
            recommendations=[],
            blocking_issues=[],
            estimated_effort="Unknown",
            dependency_risks=[],
        )

        assert review.confidence_score == 0.123456789

    def test_persona_review_mixed_dependency_risks(self) -> None:
        """Test PersonaReview handles mixed string and dict dependency risks."""
        from consensus_engine.schemas.review import PersonaReview

        review = PersonaReview(
            persona_name="Reviewer",
            persona_id="reviewer",
            confidence_score=0.8,
            strengths=[],
            concerns=[],
            recommendations=[],
            blocking_issues=[],
            estimated_effort="2 weeks",
            dependency_risks=[
                "Simple string risk",
                {"name": "Complex risk", "severity": "high", "mitigation": "Plan B"},
                "Another string risk",
            ],
        )

        assert len(review.dependency_risks) == 3
        assert review.dependency_risks[0] == "Simple string risk"
        assert review.dependency_risks[1]["severity"] == "high"

    def test_persona_review_concerns_with_mixed_blocking(self) -> None:
        """Test PersonaReview handles concerns with mixed blocking status."""
        from consensus_engine.schemas.review import BlockingIssue, Concern, PersonaReview

        review = PersonaReview(
            persona_name="Reviewer",
            persona_id="reviewer",
            confidence_score=0.7,
            strengths=[],
            concerns=[
                Concern(text="Blocking issue", is_blocking=True),
                Concern(text="Non-blocking concern", is_blocking=False),
                Concern(text="Another blocker", is_blocking=True),
            ],
            recommendations=[],
            blocking_issues=[
                BlockingIssue(text="Blocking issue"),
                BlockingIssue(text="Another blocker"),
            ],
            estimated_effort="Unknown",
            dependency_risks=[],
        )

        blocking_concerns = [c for c in review.concerns if c.is_blocking]
        non_blocking_concerns = [c for c in review.concerns if not c.is_blocking]

        assert len(blocking_concerns) == 2
        assert len(non_blocking_concerns) == 1

    def test_persona_review_duplicate_blocking_issues(self) -> None:
        """Test PersonaReview allows duplicate text in concerns and blocking_issues."""
        from consensus_engine.schemas.review import BlockingIssue, Concern, PersonaReview

        issue_text = "Critical security vulnerability"
        review = PersonaReview(
            persona_name="Security",
            persona_id="security_guardian",
            confidence_score=0.3,
            strengths=[],
            concerns=[
                Concern(text=issue_text, is_blocking=True),
            ],
            recommendations=[],
            blocking_issues=[BlockingIssue(text=issue_text)],  # Same text in both places
            estimated_effort="Unknown",
            dependency_risks=[],
        )

        # This should be allowed - same issue can appear in both lists
        assert review.concerns[0].text == issue_text
        assert review.blocking_issues[0].text == issue_text


class TestDecisionAggregationValidationEdgeCases:
    """Test suite for DecisionAggregation validation edge cases."""

    def test_decision_aggregation_multiple_personas(self) -> None:
        """Test DecisionAggregation with multiple personas."""
        from consensus_engine.schemas.review import (
            DecisionAggregation,
            DecisionEnum,
            PersonaScoreBreakdown,
        )

        aggregation = DecisionAggregation(
            overall_weighted_confidence=0.7,
            decision=DecisionEnum.REVISE,
            score_breakdown={
                "Security": PersonaScoreBreakdown(weight=0.3, notes="Security concerns"),
                "Performance": PersonaScoreBreakdown(weight=0.3, notes="Performance OK"),
                "UX": PersonaScoreBreakdown(weight=0.4, notes="UX needs work"),
            },
        )

        assert len(aggregation.score_breakdown) == 3
        total_weight = sum(p.weight for p in aggregation.score_breakdown.values())
        assert total_weight == pytest.approx(1.0)

    def test_decision_aggregation_uneven_weights(self) -> None:
        """Test DecisionAggregation allows uneven persona weights."""
        from consensus_engine.schemas.review import (
            DecisionAggregation,
            DecisionEnum,
            PersonaScoreBreakdown,
        )

        aggregation = DecisionAggregation(
            overall_weighted_confidence=0.8,
            decision=DecisionEnum.APPROVE,
            score_breakdown={
                "Senior": PersonaScoreBreakdown(weight=0.7, notes="Senior approval"),
                "Junior": PersonaScoreBreakdown(weight=0.3, notes="Junior approval"),
            },
        )

        assert aggregation.score_breakdown["Senior"].weight == 0.7
        assert aggregation.score_breakdown["Junior"].weight == 0.3

    def test_decision_aggregation_minority_report_structure(self) -> None:
        """Test DecisionAggregation with minority report."""
        from consensus_engine.schemas.review import (
            DecisionAggregation,
            DecisionEnum,
            MinorityReport,
            PersonaScoreBreakdown,
        )

        minority = MinorityReport(
            persona_id="conservative_reviewer",
            persona_name="Conservative Reviewer",
            confidence_score=0.5,
            blocking_summary="Too aggressive timeline and insufficient testing strategy",
            mitigation_recommendation="Extend timeline and add comprehensive test coverage",
            strengths=["Well-documented", "Clear scope"],
            concerns=[
                "Too aggressive timeline",
                "Insufficient testing strategy",
                "High technical debt risk",
            ],
        )

        aggregation = DecisionAggregation(
            overall_weighted_confidence=0.6,
            decision=DecisionEnum.APPROVE,
            score_breakdown={
                "Optimist": PersonaScoreBreakdown(weight=0.6, notes="Ready to go"),
                "Realist": PersonaScoreBreakdown(weight=0.4, notes="Acceptable risk"),
            },
            minority_report=minority,
        )

        assert aggregation.minority_report is not None
        assert len(aggregation.minority_report.concerns) == 3
        assert aggregation.minority_report.persona_name == "Conservative Reviewer"
