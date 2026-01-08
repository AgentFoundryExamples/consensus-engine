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
"""Unit tests for enhanced request schema validation."""

import json

import pytest
from pydantic import ValidationError

from consensus_engine.schemas.requests import (
    CreateRevisionRequest,
    ExpandIdeaRequest,
    FullReviewRequest,
    ReviewIdeaRequest,
    validate_dict_json_size,
    validate_text_length,
)


class TestValidateTextLength:
    """Test suite for validate_text_length helper function."""

    def test_valid_text(self) -> None:
        """Test validation with text within limits."""
        text = "This is a valid text."
        validate_text_length(text, "test_field", max_length=100)
        # No exception should be raised

    def test_text_at_max_length(self) -> None:
        """Test validation with text exactly at max length."""
        text = "a" * 100
        validate_text_length(text, "test_field", max_length=100)
        # No exception should be raised

    def test_text_exceeds_max_length(self) -> None:
        """Test validation rejects text exceeding max length."""
        text = "a" * 101
        with pytest.raises(ValueError) as exc_info:
            validate_text_length(text, "test_field", max_length=100)
        
        assert "exceeds maximum length of 100 characters" in str(exc_info.value)
        assert "got 101" in str(exc_info.value)

    def test_text_below_min_length(self) -> None:
        """Test validation rejects text below min length."""
        text = ""
        with pytest.raises(ValueError) as exc_info:
            validate_text_length(text, "test_field", max_length=100, min_length=1)
        
        assert "must be at least 1 characters" in str(exc_info.value)

    def test_none_text_allowed(self) -> None:
        """Test that None text is allowed."""
        validate_text_length(None, "test_field", max_length=100)
        # No exception should be raised


class TestValidateDictJsonSize:
    """Test suite for validate_dict_json_size helper function."""

    def test_valid_dict(self) -> None:
        """Test validation with dict within size limits."""
        data = {"key": "value", "number": 123}
        validate_dict_json_size(data, "test_field", max_length=1000)
        # No exception should be raised

    def test_dict_at_max_size(self) -> None:
        """Test validation with dict at max JSON size."""
        # Create a dict that serializes to exactly max_length
        data = {"key": "a" * 80}  # Approximately 100 chars JSON
        json_str = json.dumps(data)
        max_length = len(json_str)
        validate_dict_json_size(data, "test_field", max_length=max_length)
        # No exception should be raised

    def test_dict_exceeds_max_size(self) -> None:
        """Test validation rejects dict exceeding max JSON size."""
        data = {"key": "a" * 1000}
        with pytest.raises(ValueError) as exc_info:
            validate_dict_json_size(data, "test_field", max_length=100)
        
        assert "exceeds maximum size of 100 characters" in str(exc_info.value)

    def test_non_serializable_dict(self) -> None:
        """Test validation rejects non-serializable data."""
        data = {"key": lambda x: x}  # Functions are not JSON serializable
        with pytest.raises(ValueError) as exc_info:
            validate_dict_json_size(data, "test_field", max_length=1000)
        
        assert "non-serializable data" in str(exc_info.value)

    def test_none_dict_allowed(self) -> None:
        """Test that None dict is allowed."""
        validate_dict_json_size(None, "test_field", max_length=1000)
        # No exception should be raised


class TestExpandIdeaRequestValidation:
    """Test suite for ExpandIdeaRequest enhanced validation."""

    def test_valid_request_with_reasonable_lengths(self) -> None:
        """Test valid request with reasonable text lengths."""
        request = ExpandIdeaRequest(
            idea="Build a REST API. It should be secure.",
            extra_context="Must support Python 3.11+",
        )
        assert request.idea is not None
        assert request.extra_context is not None

    def test_idea_exceeding_max_length(self) -> None:
        """Test rejection of idea exceeding max length."""
        long_idea = "a" * 10001  # Exceeds default 10000 char limit
        with pytest.raises(ValidationError) as exc_info:
            ExpandIdeaRequest(idea=long_idea)
        
        errors = exc_info.value.errors()
        assert any("exceeds maximum length" in str(error) for error in errors)

    def test_extra_context_string_exceeding_max_length(self) -> None:
        """Test rejection of extra_context string exceeding max length."""
        valid_idea = "Build an API."
        long_context = "a" * 50001  # Exceeds default 50000 char limit
        with pytest.raises(ValidationError) as exc_info:
            ExpandIdeaRequest(idea=valid_idea, extra_context=long_context)
        
        errors = exc_info.value.errors()
        assert any("exceeds maximum length" in str(error) for error in errors)

    def test_extra_context_dict_exceeding_max_size(self) -> None:
        """Test rejection of extra_context dict with large JSON size."""
        valid_idea = "Build an API."
        large_dict = {"data": "a" * 50000}  # JSON will exceed 50000 chars
        with pytest.raises(ValidationError) as exc_info:
            ExpandIdeaRequest(idea=valid_idea, extra_context=large_dict)
        
        errors = exc_info.value.errors()
        assert any("exceeds maximum size" in str(error) for error in errors)

    def test_idea_with_too_many_sentences(self) -> None:
        """Test rejection of idea with more than 10 sentences."""
        # 11 sentences
        long_idea = ". ".join([f"Sentence {i}" for i in range(11)]) + "."
        with pytest.raises(ValidationError) as exc_info:
            ExpandIdeaRequest(idea=long_idea)
        
        errors = exc_info.value.errors()
        assert any("at most 10 sentences" in str(error) for error in errors)

    def test_idea_with_exactly_10_sentences(self) -> None:
        """Test acceptance of idea with exactly 10 sentences."""
        # 10 sentences
        valid_idea = ". ".join([f"Sentence {i}" for i in range(10)]) + "."
        request = ExpandIdeaRequest(idea=valid_idea)
        assert request.idea == valid_idea


class TestReviewIdeaRequestValidation:
    """Test suite for ReviewIdeaRequest enhanced validation."""

    def test_valid_request(self) -> None:
        """Test valid request with all validation passing."""
        request = ReviewIdeaRequest(
            idea="Build a secure API. Use modern standards.",
            extra_context={"language": "Python"},
        )
        assert request.idea is not None

    def test_idea_exceeding_max_length(self) -> None:
        """Test rejection of idea exceeding max length."""
        long_idea = "a" * 10001
        with pytest.raises(ValidationError) as exc_info:
            ReviewIdeaRequest(idea=long_idea)
        
        errors = exc_info.value.errors()
        assert any("exceeds maximum length" in str(error) for error in errors)


class TestFullReviewRequestValidation:
    """Test suite for FullReviewRequest enhanced validation."""

    def test_valid_request(self) -> None:
        """Test valid request with all validation passing."""
        request = FullReviewRequest(
            idea="Build a REST API. Make it scalable.",
        )
        assert request.idea is not None

    def test_idea_exceeding_max_length(self) -> None:
        """Test rejection of idea exceeding max length."""
        long_idea = "a" * 10001
        with pytest.raises(ValidationError) as exc_info:
            FullReviewRequest(idea=long_idea)
        
        errors = exc_info.value.errors()
        assert any("exceeds maximum length" in str(error) for error in errors)


class TestCreateRevisionRequestValidation:
    """Test suite for CreateRevisionRequest enhanced validation."""

    def test_valid_request_with_edited_proposal_string(self) -> None:
        """Test valid request with edited_proposal as string."""
        request = CreateRevisionRequest(
            edited_proposal="Updated proposal text",
        )
        assert request.edited_proposal is not None

    def test_valid_request_with_edited_proposal_dict(self) -> None:
        """Test valid request with edited_proposal as dict."""
        request = CreateRevisionRequest(
            edited_proposal={"problem_statement": "Updated problem"},
        )
        assert request.edited_proposal is not None

    def test_valid_request_with_edit_notes(self) -> None:
        """Test valid request with edit_notes."""
        request = CreateRevisionRequest(
            edit_notes="Added security requirements",
        )
        assert request.edit_notes is not None

    def test_edited_proposal_string_exceeding_max_length(self) -> None:
        """Test rejection of edited_proposal string exceeding max length."""
        long_proposal = "a" * 100001  # Exceeds default 100000 char limit
        with pytest.raises(ValidationError) as exc_info:
            CreateRevisionRequest(edited_proposal=long_proposal)
        
        errors = exc_info.value.errors()
        assert any("exceeds maximum length" in str(error) for error in errors)

    def test_edited_proposal_dict_exceeding_max_size(self) -> None:
        """Test rejection of edited_proposal dict with large JSON size."""
        large_dict = {"data": "a" * 100000}  # JSON will exceed 100000 chars
        with pytest.raises(ValidationError) as exc_info:
            CreateRevisionRequest(edited_proposal=large_dict)
        
        errors = exc_info.value.errors()
        assert any("exceeds maximum size" in str(error) for error in errors)

    def test_edit_notes_exceeding_max_length(self) -> None:
        """Test rejection of edit_notes exceeding max length."""
        long_notes = "a" * 10001  # Exceeds default 10000 char limit
        with pytest.raises(ValidationError) as exc_info:
            CreateRevisionRequest(edit_notes=long_notes)
        
        errors = exc_info.value.errors()
        assert any("exceeds maximum length" in str(error) for error in errors)

    def test_input_idea_exceeding_max_length(self) -> None:
        """Test rejection of input_idea exceeding max length."""
        long_idea = "a" * 10001
        with pytest.raises(ValidationError) as exc_info:
            CreateRevisionRequest(edited_proposal="Update", input_idea=long_idea)
        
        errors = exc_info.value.errors()
        assert any("exceeds maximum length" in str(error) for error in errors)

    def test_extra_context_exceeding_max_length(self) -> None:
        """Test rejection of extra_context exceeding max length."""
        long_context = "a" * 50001
        with pytest.raises(ValidationError) as exc_info:
            CreateRevisionRequest(edited_proposal="Update", extra_context=long_context)
        
        errors = exc_info.value.errors()
        assert any("exceeds maximum" in str(error) for error in errors)
