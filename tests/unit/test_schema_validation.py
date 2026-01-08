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
"""Unit tests for schema validation utilities.

This module tests the registry-based validation functions that ensure
LLM responses conform to expected schema contracts.
"""

import pytest

from consensus_engine.exceptions import SchemaValidationError
from consensus_engine.schemas.proposal import ExpandedProposal
from consensus_engine.schemas.registry import get_current_schema
from consensus_engine.schemas.review import DecisionAggregation, DecisionEnum, PersonaReview
from consensus_engine.schemas.validation import (
    check_version_consistency,
    get_schema_version_info,
    validate_against_schema,
)


class TestValidateAgainstSchema:
    """Test suite for validate_against_schema function."""

    def test_validate_valid_expanded_proposal(self) -> None:
        """Test validation passes for a valid ExpandedProposal."""
        proposal = ExpandedProposal(
            problem_statement="Build a REST API",
            proposed_solution="Use FastAPI framework",
            assumptions=["Python 3.11+", "PostgreSQL"],
            scope_non_goals=["Mobile app", "UI design"],
        )

        # Should not raise
        validate_against_schema(
            instance=proposal,
            schema_name="ExpandedProposal",
            context={"test": "validate_valid"},
        )

    def test_validate_valid_persona_review(self) -> None:
        """Test validation passes for a valid PersonaReview."""
        review = PersonaReview(
            persona_name="Architect",
            persona_id="architect",
            confidence_score=0.85,
            strengths=["Good architecture", "Clear design"],
            concerns=[],
            recommendations=["Add error handling"],
            blocking_issues=[],
            estimated_effort="2-3 weeks",
            dependency_risks=[],
        )

        # Should not raise
        validate_against_schema(
            instance=review,
            schema_name="PersonaReview",
            context={"test": "validate_valid"},
        )

    def test_validate_with_wrong_type(self) -> None:
        """Test validation fails when instance type doesn't match schema."""
        proposal = ExpandedProposal(
            problem_statement="Build a REST API",
            proposed_solution="Use FastAPI framework",
            assumptions=["Python 3.11+"],
            scope_non_goals=["Mobile app"],
        )

        # Try to validate as PersonaReview (wrong type)
        with pytest.raises(SchemaValidationError) as exc_info:
            validate_against_schema(
                instance=proposal,
                schema_name="PersonaReview",
                context={"test": "wrong_type"},
            )

        assert "type mismatch" in str(exc_info.value).lower()
        assert "ExpandedProposal" in str(exc_info.value)
        assert "PersonaReview" in str(exc_info.value)

    def test_validate_with_invalid_schema_name(self) -> None:
        """Test validation fails with invalid schema name."""
        proposal = ExpandedProposal(
            problem_statement="Build a REST API",
            proposed_solution="Use FastAPI framework",
            assumptions=["Python 3.11+"],
            scope_non_goals=["Mobile app"],
        )

        with pytest.raises(SchemaValidationError) as exc_info:
            validate_against_schema(
                instance=proposal,
                schema_name="NonExistentSchema",
                context={"test": "invalid_schema"},
            )

        assert "not found" in str(exc_info.value).lower()

    def test_validate_includes_context_in_error(self) -> None:
        """Test validation errors include context information."""
        proposal = ExpandedProposal(
            problem_statement="Build a REST API",
            proposed_solution="Use FastAPI framework",
            assumptions=["Python 3.11+"],
            scope_non_goals=["Mobile app"],
        )

        try:
            validate_against_schema(
                instance=proposal,
                schema_name="PersonaReview",
                context={"request_id": "test-123", "step_name": "expand"},
            )
            pytest.fail("Expected SchemaValidationError")
        except SchemaValidationError as e:
            assert "request_id" in e.details
            assert e.details["request_id"] == "test-123"
            assert e.details["step_name"] == "expand"


class TestGetSchemaVersionInfo:
    """Test suite for get_schema_version_info function."""

    def test_get_version_info_for_expanded_proposal(self) -> None:
        """Test getting version info for ExpandedProposal."""
        info = get_schema_version_info("ExpandedProposal")

        assert info["schema_name"] == "ExpandedProposal"
        assert "schema_version" in info
        assert info["schema_version"] == "1.0.0"
        assert "prompt_set_version" in info
        assert "description" in info
        assert "deprecated" in info

    def test_get_version_info_for_persona_review(self) -> None:
        """Test getting version info for PersonaReview."""
        info = get_schema_version_info("PersonaReview")

        assert info["schema_name"] == "PersonaReview"
        assert info["schema_version"] == "1.0.0"
        assert info["prompt_set_version"] == "1.0.0"

    def test_get_version_info_for_decision_aggregation(self) -> None:
        """Test getting version info for DecisionAggregation."""
        info = get_schema_version_info("DecisionAggregation")

        assert info["schema_name"] == "DecisionAggregation"
        assert info["schema_version"] == "1.0.0"

    def test_get_version_info_invalid_schema(self) -> None:
        """Test get_schema_version_info raises error for invalid schema."""
        with pytest.raises(SchemaValidationError) as exc_info:
            get_schema_version_info("InvalidSchema")

        assert "not found" in str(exc_info.value).lower() or "failed to get" in str(
            exc_info.value
        ).lower()


class TestCheckVersionConsistency:
    """Test suite for check_version_consistency function."""

    def test_consistency_with_single_schema(self) -> None:
        """Test consistency check passes with single schema version."""
        schema_versions = [
            {"schema_name": "ExpandedProposal", "schema_version": "1.0.0"},
        ]

        # Should not raise
        check_version_consistency(
            schema_versions=schema_versions, context={"run_id": "test-run"}
        )

    def test_consistency_with_multiple_consistent_schemas(self) -> None:
        """Test consistency check passes with multiple consistent schemas."""
        schema_versions = [
            {"schema_name": "ExpandedProposal", "schema_version": "1.0.0"},
            {"schema_name": "PersonaReview", "schema_version": "1.0.0"},
            {"schema_name": "PersonaReview", "schema_version": "1.0.0"},  # Duplicate OK
            {"schema_name": "DecisionAggregation", "schema_version": "1.0.0"},
        ]

        # Should not raise
        check_version_consistency(
            schema_versions=schema_versions, context={"run_id": "test-run"}
        )

    def test_inconsistency_with_mixed_versions(self) -> None:
        """Test consistency check fails with mixed versions of same schema."""
        schema_versions = [
            {"schema_name": "PersonaReview", "schema_version": "1.0.0"},
            {"schema_name": "PersonaReview", "schema_version": "2.0.0"},  # Different version!
        ]

        with pytest.raises(SchemaValidationError) as exc_info:
            check_version_consistency(
                schema_versions=schema_versions, context={"run_id": "test-run"}
            )

        error = exc_info.value
        assert "mixed schema versions" in str(error).lower()
        assert "inconsistent_schemas" in error.details
        assert "PersonaReview" in error.details["inconsistent_schemas"]

    def test_inconsistency_with_multiple_schemas(self) -> None:
        """Test consistency check detects inconsistencies across multiple schemas."""
        schema_versions = [
            {"schema_name": "ExpandedProposal", "schema_version": "1.0.0"},
            {"schema_name": "ExpandedProposal", "schema_version": "1.1.0"},  # Inconsistent
            {"schema_name": "PersonaReview", "schema_version": "1.0.0"},
            {"schema_name": "PersonaReview", "schema_version": "2.0.0"},  # Inconsistent
            {"schema_name": "DecisionAggregation", "schema_version": "1.0.0"},  # Consistent
        ]

        with pytest.raises(SchemaValidationError) as exc_info:
            check_version_consistency(
                schema_versions=schema_versions, context={"run_id": "test-run"}
            )

        error = exc_info.value
        inconsistent = error.details["inconsistent_schemas"]
        assert "ExpandedProposal" in inconsistent
        assert "PersonaReview" in inconsistent
        assert "DecisionAggregation" not in inconsistent  # This one was consistent

    def test_consistency_with_empty_list(self) -> None:
        """Test consistency check handles empty list gracefully."""
        schema_versions: list[dict[str, str]] = []

        # Should not raise with empty list
        check_version_consistency(schema_versions=schema_versions, context={})

    def test_consistency_with_missing_fields(self) -> None:
        """Test consistency check handles missing fields gracefully."""
        schema_versions = [
            {"schema_name": "ExpandedProposal"},  # Missing schema_version
            {"schema_version": "1.0.0"},  # Missing schema_name
        ]

        # Should not raise - just skip entries with missing fields
        check_version_consistency(schema_versions=schema_versions, context={})

    def test_consistency_includes_context_in_error(self) -> None:
        """Test consistency check includes context in error details."""
        schema_versions = [
            {"schema_name": "PersonaReview", "schema_version": "1.0.0"},
            {"schema_name": "PersonaReview", "schema_version": "2.0.0"},
        ]

        with pytest.raises(SchemaValidationError) as exc_info:
            check_version_consistency(
                schema_versions=schema_versions,
                context={"run_id": "test-123", "run_type": "initial"},
            )

        error = exc_info.value
        assert "run_id" in error.details
        assert error.details["run_id"] == "test-123"
        assert error.details["run_type"] == "initial"


class TestSchemaVersionIntegration:
    """Integration tests for schema version tracking and validation."""

    def test_end_to_end_validation_workflow(self) -> None:
        """Test complete workflow: get schema, create instance, validate."""
        # Step 1: Get schema version info
        schema_version = get_current_schema("ExpandedProposal")
        version_info = get_schema_version_info("ExpandedProposal")

        # Step 2: Create instance
        proposal = ExpandedProposal(
            problem_statement="Build a REST API",
            proposed_solution="Use FastAPI",
            assumptions=["Python 3.11+"],
            scope_non_goals=["Mobile app"],
        )

        # Step 3: Validate against schema
        validate_against_schema(
            instance=proposal,
            schema_name="ExpandedProposal",
            schema_version=schema_version,
            context={"test": "e2e"},
        )

        # All steps should succeed
        assert version_info["schema_version"] == "1.0.0"

    def test_version_consistency_across_run(self) -> None:
        """Test version consistency checking across a full run."""
        # Simulate a run with multiple outputs
        proposal_version = get_schema_version_info("ExpandedProposal")
        review_version = get_schema_version_info("PersonaReview")
        decision_version = get_schema_version_info("DecisionAggregation")

        schema_versions = [
            {
                "schema_name": "ExpandedProposal",
                "schema_version": proposal_version["schema_version"],
            },
            {
                "schema_name": "PersonaReview",
                "schema_version": review_version["schema_version"],
            },
            {
                "schema_name": "PersonaReview",
                "schema_version": review_version["schema_version"],
            },
            {
                "schema_name": "DecisionAggregation",
                "schema_version": decision_version["schema_version"],
            },
        ]

        # Should not raise - all using current versions
        check_version_consistency(
            schema_versions=schema_versions, context={"run_id": "test-run-123"}
        )
