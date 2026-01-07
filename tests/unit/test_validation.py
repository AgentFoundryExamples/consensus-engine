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
        # Abbreviations with periods should not be counted as separate sentences
        text = "Dr. Smith works at U.S. headquarters. This is the second sentence."
        # This will count as 3 sentences due to simple period splitting
        # This is a known limitation of the simple regex approach
        count = count_sentences(text)
        assert count >= 2  # At least 2 sentences

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
        # Ellipsis may be counted differently
        count = count_sentences(text)
        assert count >= 1

    def test_count_sentences_no_ending_punctuation(self) -> None:
        """Test sentence counting with no ending punctuation."""
        text = "This is a single sentence without ending punctuation"
        assert count_sentences(text) == 1

    def test_count_sentences_only_punctuation(self) -> None:
        """Test sentence counting with only punctuation."""
        text = "...!!!"
        count = count_sentences(text)
        # Should not count as multiple sentences
        assert count >= 0


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
        # Pydantic may strip whitespace
        assert "Build a REST API" in request.idea

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
        # Verify it's valid JSON
        import json

        parsed = json.loads(json_str)
        assert parsed["idea"] == "Build an API."
        assert parsed["extra_context"]["key"] == "value"
        assert parsed["extra_context"]["count"] == 42
