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
"""Unit tests for API validation utilities."""

import pytest

from consensus_engine.api.validation import log_validation_failure, validate_version_headers
from consensus_engine.config import Settings
from consensus_engine.exceptions import UnsupportedVersionError


class TestValidateVersionHeaders:
    """Test suite for validate_version_headers function."""

    def test_valid_versions(self) -> None:
        """Test validation with matching versions."""
        settings = Settings(
            openai_api_key="test-key",
            env="testing",
        )
        
        result = validate_version_headers(
            schema_version="1.0.0",
            prompt_set_version="1.0.0",
            settings=settings,
        )
        
        assert result["schema_version"] == "1.0.0"
        assert result["prompt_set_version"] == "1.0.0"

    def test_none_versions_uses_defaults(self) -> None:
        """Test that None versions fall back to defaults."""
        settings = Settings(
            openai_api_key="test-key",
            env="testing",
        )
        
        result = validate_version_headers(
            schema_version=None,
            prompt_set_version=None,
            settings=settings,
        )
        
        # Should get current versions from config
        assert result["schema_version"] == "1.0.0"
        assert result["prompt_set_version"] == "1.0.0"

    def test_unsupported_schema_version(self) -> None:
        """Test rejection of unsupported schema version."""
        settings = Settings(
            openai_api_key="test-key",
            env="testing",
        )
        
        with pytest.raises(UnsupportedVersionError) as exc_info:
            validate_version_headers(
                schema_version="0.9.0",
                prompt_set_version="1.0.0",
                settings=settings,
            )
        
        error = exc_info.value
        assert error.code == "UNSUPPORTED_VERSION"
        assert "0.9.0" in error.message
        assert "1.0.0" in error.message
        assert error.details["requested_schema_version"] == "0.9.0"
        assert error.details["supported_schema_version"] == "1.0.0"

    def test_unsupported_prompt_set_version(self) -> None:
        """Test rejection of unsupported prompt set version."""
        settings = Settings(
            openai_api_key="test-key",
            env="testing",
        )
        
        with pytest.raises(UnsupportedVersionError) as exc_info:
            validate_version_headers(
                schema_version="1.0.0",
                prompt_set_version="0.9.0",
                settings=settings,
            )
        
        error = exc_info.value
        assert error.code == "UNSUPPORTED_VERSION"
        assert "0.9.0" in error.message
        assert "1.0.0" in error.message
        assert error.details["requested_prompt_set_version"] == "0.9.0"
        assert error.details["supported_prompt_set_version"] == "1.0.0"

    def test_partial_version_specification(self) -> None:
        """Test with only schema_version specified."""
        settings = Settings(
            openai_api_key="test-key",
            env="testing",
        )
        
        result = validate_version_headers(
            schema_version="1.0.0",
            prompt_set_version=None,
            settings=settings,
        )
        
        assert result["schema_version"] == "1.0.0"
        assert result["prompt_set_version"] == "1.0.0"

    def test_error_message_includes_upgrade_guidance(self) -> None:
        """Test that error messages include upgrade guidance."""
        settings = Settings(
            openai_api_key="test-key",
            env="testing",
        )
        
        with pytest.raises(UnsupportedVersionError) as exc_info:
            validate_version_headers(
                schema_version="2.0.0",
                prompt_set_version="1.0.0",
                settings=settings,
            )
        
        error = exc_info.value
        assert "upgrade" in error.message.lower()
        assert "supported" in error.message.lower()


class TestLogValidationFailure:
    """Test suite for log_validation_failure function."""

    def test_logs_validation_failure(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that validation failures are logged."""
        log_validation_failure(
            field="idea",
            rule="max_length",
            message="Idea exceeds maximum length",
            metadata={"field_length": 15000, "limit": 10000},
        )
        
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        assert "Validation failure" in record.message
        assert "idea" in record.message

    def test_sanitizes_sensitive_metadata(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that sensitive metadata is not logged."""
        log_validation_failure(
            field="edited_proposal",
            rule="max_length",
            message="Edited proposal too large",
            metadata={
                "field_length": 150000,
                "limit": 100000,
                "proposal_content": "This is sensitive content that should not be logged",
            },
        )
        
        assert len(caplog.records) == 1
        record = caplog.records[0]
        
        # Should log length metadata
        assert "field_length" in str(record.__dict__)
        assert "limit" in str(record.__dict__)
        
        # Should not log actual content
        assert "sensitive content" not in str(record.__dict__)

    def test_logs_with_request_id(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that request_id is included in logs."""
        log_validation_failure(
            field="extra_context",
            rule="max_json_size",
            message="Context too large",
            metadata={"request_id": "test-request-123", "field_length": 60000},
        )
        
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert "request_id" in str(record.__dict__)
        assert "test-request-123" in str(record.__dict__)

    def test_logs_without_metadata(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test logging without optional metadata."""
        log_validation_failure(
            field="idea",
            rule="sentence_count",
            message="Idea has too many sentences",
        )
        
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        assert "Validation failure" in record.message
