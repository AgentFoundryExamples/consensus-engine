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
"""Unit tests for request schemas."""

import pytest
from pydantic import ValidationError

from consensus_engine.schemas.requests import (
    ErrorResponse,
    ExpandIdeaRequest,
    ExpandIdeaResponse,
    HealthResponse,
    count_sentences,
)


class TestCountSentences:
    """Test suite for sentence counting utility."""

    def test_count_single_sentence(self) -> None:
        """Test counting a single sentence."""
        assert count_sentences("This is a sentence.") == 1

    def test_count_multiple_sentences(self) -> None:
        """Test counting multiple sentences."""
        assert count_sentences("First sentence. Second sentence. Third sentence.") == 3

    def test_count_sentences_with_question_marks(self) -> None:
        """Test counting sentences with question marks."""
        assert count_sentences("Is this a question? Yes it is.") == 2

    def test_count_sentences_with_exclamations(self) -> None:
        """Test counting sentences with exclamation marks."""
        assert count_sentences("This is exciting! Very exciting!") == 2

    def test_count_mixed_punctuation(self) -> None:
        """Test counting sentences with mixed punctuation."""
        assert count_sentences("First. Second! Third?") == 3

    def test_count_empty_string(self) -> None:
        """Test counting empty string."""
        assert count_sentences("") == 0

    def test_count_whitespace_only(self) -> None:
        """Test counting whitespace-only string."""
        assert count_sentences("   ") == 0

    def test_count_sentence_without_ending_punctuation(self) -> None:
        """Test counting sentence without ending punctuation."""
        # Single sentence without ending punctuation counts as 1
        assert count_sentences("This is a sentence") == 1

    def test_count_ten_sentences(self) -> None:
        """Test counting exactly 10 sentences."""
        text = "One. Two. Three. Four. Five. Six. Seven. Eight. Nine. Ten."
        assert count_sentences(text) == 10

    def test_count_more_than_ten_sentences(self) -> None:
        """Test counting more than 10 sentences."""
        text = "One. Two. Three. Four. Five. Six. Seven. Eight. Nine. Ten. Eleven."
        assert count_sentences(text) == 11


class TestExpandIdeaRequest:
    """Test suite for ExpandIdeaRequest model."""

    def test_valid_request_with_single_sentence(self) -> None:
        """Test valid request with single sentence."""
        request = ExpandIdeaRequest(idea="Build a REST API.")
        assert request.idea == "Build a REST API."
        assert request.extra_context is None

    def test_valid_request_with_multiple_sentences(self) -> None:
        """Test valid request with multiple sentences."""
        idea = "Build a REST API. It should support authentication. Use Python 3.11+."
        request = ExpandIdeaRequest(idea=idea)
        assert request.idea == idea

    def test_valid_request_with_extra_context_string(self) -> None:
        """Test valid request with extra context as string."""
        request = ExpandIdeaRequest(idea="Build an API.", extra_context="Must be secure")
        assert request.extra_context == "Must be secure"

    def test_valid_request_with_extra_context_dict(self) -> None:
        """Test valid request with extra context as dict."""
        context = {"language": "Python", "version": "3.11+"}
        request = ExpandIdeaRequest(idea="Build an API.", extra_context=context)
        assert request.extra_context == context

    def test_valid_request_with_ten_sentences(self) -> None:
        """Test valid request with exactly 10 sentences."""
        idea = "One. Two. Three. Four. Five. Six. Seven. Eight. Nine. Ten."
        request = ExpandIdeaRequest(idea=idea)
        assert request.idea == idea

    def test_reject_empty_idea(self) -> None:
        """Test rejection of empty idea."""
        with pytest.raises(ValidationError) as exc_info:
            ExpandIdeaRequest(idea="")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("idea",) for error in errors)

    def test_reject_idea_with_too_many_sentences(self) -> None:
        """Test rejection of idea with more than 10 sentences."""
        idea = "One. Two. Three. Four. Five. Six. Seven. Eight. Nine. Ten. Eleven."
        with pytest.raises(ValidationError) as exc_info:
            ExpandIdeaRequest(idea=idea)

        errors = exc_info.value.errors()
        assert any("must contain at most 10 sentences" in str(error) for error in errors)

    def test_json_serializable(self) -> None:
        """Test that request is JSON serializable."""
        request = ExpandIdeaRequest(idea="Build an API.", extra_context="Context")
        json_data = request.model_dump()
        assert json_data["idea"] == "Build an API."
        assert json_data["extra_context"] == "Context"

    def test_deeply_nested_dict_context(self) -> None:
        """Test handling of deeply nested dict as extra_context."""
        context = {
            "level1": {"level2": {"level3": {"value": "deep"}}},
            "features": ["auth", "crud"],
        }
        request = ExpandIdeaRequest(idea="Build an API.", extra_context=context)
        assert request.extra_context == context


class TestExpandIdeaResponse:
    """Test suite for ExpandIdeaResponse model."""

    def test_valid_response(self) -> None:
        """Test valid response creation."""
        response = ExpandIdeaResponse(
            problem_statement="Problem",
            proposed_solution="Solution",
            assumptions=["Assumption 1"],
            scope_non_goals=["Non-goal 1"],
            title="Test Title",
            summary="Test Summary",
            raw_idea="Original idea",
            raw_expanded_proposal="Full proposal",
            metadata={"request_id": "test-123"},
        )
        assert response.problem_statement == "Problem"
        assert response.proposed_solution == "Solution"
        assert len(response.assumptions) == 1
        assert len(response.scope_non_goals) == 1
        assert response.title == "Test Title"
        assert response.summary == "Test Summary"
        assert response.raw_idea == "Original idea"
        assert response.metadata["request_id"] == "test-123"

    def test_minimal_response(self) -> None:
        """Test minimal response with required fields only."""
        response = ExpandIdeaResponse(
            problem_statement="Problem",
            proposed_solution="Solution",
            assumptions=[],
            scope_non_goals=[],
            metadata={"request_id": "test-456"},
        )
        assert response.assumptions == []
        assert response.scope_non_goals == []
        assert response.title is None
        assert response.summary is None
        assert response.raw_idea is None
        assert response.raw_expanded_proposal is None

    def test_json_serializable(self) -> None:
        """Test that response is JSON serializable."""
        response = ExpandIdeaResponse(
            problem_statement="Problem",
            proposed_solution="Solution",
            assumptions=[],
            scope_non_goals=[],
            metadata={"request_id": "test-789"},
        )
        json_data = response.model_dump()
        assert json_data["problem_statement"] == "Problem"
        assert json_data["metadata"]["request_id"] == "test-789"


class TestErrorResponse:
    """Test suite for ErrorResponse model."""

    def test_valid_error_response(self) -> None:
        """Test valid error response creation."""
        error = ErrorResponse(
            code="TEST_ERROR",
            message="Test error message",
            details={"key": "value"},
            request_id="req-123",
        )
        assert error.code == "TEST_ERROR"
        assert error.message == "Test error message"
        assert error.details == {"key": "value"}
        assert error.request_id == "req-123"

    def test_minimal_error_response(self) -> None:
        """Test minimal error response."""
        error = ErrorResponse(code="ERROR", message="Message")
        assert error.details is None
        assert error.request_id is None

    def test_json_serializable(self) -> None:
        """Test that error response is JSON serializable."""
        error = ErrorResponse(code="ERROR", message="Message")
        json_data = error.model_dump()
        assert json_data["code"] == "ERROR"
        assert json_data["message"] == "Message"


class TestHealthResponse:
    """Test suite for HealthResponse model."""

    def test_valid_health_response(self) -> None:
        """Test valid health response creation."""
        health = HealthResponse(
            status="healthy",
            environment="production",
            debug=False,
            model="gpt-5.1",
            temperature=0.7,
            uptime_seconds=3600.0,
            config_status="ok",
        )
        assert health.status == "healthy"
        assert health.environment == "production"
        assert not health.debug
        assert health.model == "gpt-5.1"
        assert health.temperature == 0.7
        assert health.uptime_seconds == 3600.0
        assert health.config_status == "ok"

    def test_degraded_health_response(self) -> None:
        """Test degraded health response."""
        health = HealthResponse(
            status="degraded",
            environment="production",
            debug=False,
            model="gpt-5.1",
            temperature=0.7,
            uptime_seconds=1234.5,
            config_status="warning",
        )
        assert health.status == "degraded"
        assert health.config_status == "warning"

    def test_json_serializable(self) -> None:
        """Test that health response is JSON serializable."""
        health = HealthResponse(
            status="healthy",
            environment="development",
            debug=True,
            model="gpt-5.1",
            temperature=0.7,
            uptime_seconds=100.0,
            config_status="ok",
        )
        json_data = health.model_dump()
        assert json_data["status"] == "healthy"
        assert json_data["debug"] is True
