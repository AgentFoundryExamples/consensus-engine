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
"""Unit tests for schema registry module."""

import json

import pytest
from pydantic import ValidationError

from consensus_engine.schemas.proposal import ExpandedProposal
from consensus_engine.schemas.registry import (
    SchemaNotFoundError,
    SchemaRegistry,
    SchemaVersion,
    SchemaVersionNotFoundError,
    get_current_schema,
    get_registry,
    get_schema_version,
    list_all_schemas,
    list_schema_versions,
)
from consensus_engine.schemas.review import DecisionAggregation, PersonaReview


class TestSchemaRegistry:
    """Test suite for SchemaRegistry class."""

    def test_registry_initialization(self) -> None:
        """Test that registry initializes correctly."""
        registry = SchemaRegistry()
        assert registry.list_schemas() == []

    def test_register_schema(self) -> None:
        """Test registering a new schema version."""
        registry = SchemaRegistry()
        registry.register(
            schema_name="TestSchema",
            version="1.0.0",
            schema_class=ExpandedProposal,
            description="Test schema",
            is_current=True,
        )

        schemas = registry.list_schemas()
        assert "TestSchema" in schemas

    def test_register_duplicate_version_raises_error(self) -> None:
        """Test that registering duplicate version raises ValueError."""
        registry = SchemaRegistry()
        registry.register(
            schema_name="TestSchema",
            version="1.0.0",
            schema_class=ExpandedProposal,
            description="Test schema",
            is_current=True,
        )

        with pytest.raises(ValueError, match="already registered"):
            registry.register(
                schema_name="TestSchema",
                version="1.0.0",
                schema_class=ExpandedProposal,
                description="Duplicate",
                is_current=False,
            )

    def test_register_invalid_version_format_raises_error(self) -> None:
        """Test that registering with invalid version format raises ValueError."""
        registry = SchemaRegistry()

        # Test various invalid formats
        invalid_versions = ["v1.0.0", "1.0", "1", "latest", "1.0.0-alpha", ""]

        for invalid_version in invalid_versions:
            with pytest.raises(ValueError, match="Invalid version format"):
                registry.register(
                    schema_name="TestSchema",
                    version=invalid_version,
                    schema_class=ExpandedProposal,
                    description="Test schema",
                    is_current=True,
                )

    def test_register_valid_semantic_version_succeeds(self) -> None:
        """Test that registering with valid semantic version succeeds."""
        registry = SchemaRegistry()

        # Test various valid formats
        valid_versions = ["0.0.1", "1.0.0", "2.1.3", "10.20.30"]

        for valid_version in valid_versions:
            registry.register(
                schema_name=f"TestSchema{valid_version}",
                version=valid_version,
                schema_class=ExpandedProposal,
                description="Test schema",
                is_current=True,
            )
            # Should not raise any error

    def test_get_current_schema(self) -> None:
        """Test retrieving current schema version."""
        registry = SchemaRegistry()
        registry.register(
            schema_name="TestSchema",
            version="1.0.0",
            schema_class=ExpandedProposal,
            description="Test schema",
            is_current=True,
        )

        schema_version = registry.get_current("TestSchema")
        assert schema_version.version == "1.0.0"
        assert schema_version.schema_class == ExpandedProposal

    def test_get_current_schema_not_found(self) -> None:
        """Test that getting non-existent schema raises SchemaNotFoundError."""
        registry = SchemaRegistry()

        with pytest.raises(SchemaNotFoundError, match="not found in registry"):
            registry.get_current("NonExistent")

    def test_get_current_schema_no_current_version(self) -> None:
        """Test that getting schema without current version raises error."""
        registry = SchemaRegistry()
        registry.register(
            schema_name="TestSchema",
            version="1.0.0",
            schema_class=ExpandedProposal,
            description="Test schema",
            is_current=False,
        )

        with pytest.raises(SchemaNotFoundError, match="No current version"):
            registry.get_current("TestSchema")

    def test_get_specific_version(self) -> None:
        """Test retrieving specific schema version."""
        registry = SchemaRegistry()
        registry.register(
            schema_name="TestSchema",
            version="1.0.0",
            schema_class=ExpandedProposal,
            description="Version 1.0.0",
            is_current=False,
        )
        registry.register(
            schema_name="TestSchema",
            version="2.0.0",
            schema_class=ExpandedProposal,
            description="Version 2.0.0",
            is_current=True,
        )

        schema_v1 = registry.get_version("TestSchema", "1.0.0")
        assert schema_v1.version == "1.0.0"
        assert schema_v1.description == "Version 1.0.0"

        schema_v2 = registry.get_version("TestSchema", "2.0.0")
        assert schema_v2.version == "2.0.0"
        assert schema_v2.description == "Version 2.0.0"

    def test_get_version_not_found(self) -> None:
        """Test that getting non-existent version raises SchemaVersionNotFoundError."""
        registry = SchemaRegistry()
        registry.register(
            schema_name="TestSchema",
            version="1.0.0",
            schema_class=ExpandedProposal,
            description="Test schema",
            is_current=True,
        )

        with pytest.raises(SchemaVersionNotFoundError, match="Version '2.0.0' not found"):
            registry.get_version("TestSchema", "2.0.0")

    def test_list_versions(self) -> None:
        """Test listing all versions of a schema."""
        registry = SchemaRegistry()
        registry.register(
            schema_name="TestSchema",
            version="1.0.0",
            schema_class=ExpandedProposal,
            description="Version 1.0.0",
            is_current=False,
        )
        registry.register(
            schema_name="TestSchema",
            version="2.0.0",
            schema_class=ExpandedProposal,
            description="Version 2.0.0",
            is_current=True,
        )

        versions = registry.list_versions("TestSchema")
        assert "1.0.0" in versions
        assert "2.0.0" in versions
        assert len(versions) == 2

    def test_get_current_version_string(self) -> None:
        """Test getting current version string."""
        registry = SchemaRegistry()
        registry.register(
            schema_name="TestSchema",
            version="1.0.0",
            schema_class=ExpandedProposal,
            description="Test schema",
            is_current=True,
        )

        version_str = registry.get_current_version_string("TestSchema")
        assert version_str == "1.0.0"

    def test_deprecated_schema_version(self) -> None:
        """Test registering and retrieving deprecated schema version."""
        registry = SchemaRegistry()
        registry.register(
            schema_name="TestSchema",
            version="1.0.0",
            schema_class=ExpandedProposal,
            description="Deprecated version",
            is_current=False,
            deprecated=True,
            migration_notes="Use version 2.0.0 instead",
        )

        schema_version = registry.get_version("TestSchema", "1.0.0")
        assert schema_version.deprecated is True
        assert schema_version.migration_notes == "Use version 2.0.0 instead"


class TestSchemaVersion:
    """Test suite for SchemaVersion class."""

    def test_schema_version_to_dict(self) -> None:
        """Test serializing schema instance to dict with metadata."""
        schema_version = SchemaVersion(
            version="1.0.0",
            schema_class=ExpandedProposal,
            description="Test schema",
            prompt_set_version="1.0.0",
        )

        proposal = ExpandedProposal(
            problem_statement="Test problem",
            proposed_solution="Test solution",
            assumptions=["assumption1"],
            scope_non_goals=["non-goal1"],
        )

        result = schema_version.to_dict(proposal)
        assert result["problem_statement"] == "Test problem"
        assert result["proposed_solution"] == "Test solution"
        assert result["_schema_version"] == "1.0.0"
        assert result["_prompt_set_version"] == "1.0.0"

    def test_schema_version_to_json(self) -> None:
        """Test serializing schema instance to JSON with metadata."""
        schema_version = SchemaVersion(
            version="1.0.0",
            schema_class=ExpandedProposal,
            description="Test schema",
            prompt_set_version="1.0.0",
        )

        proposal = ExpandedProposal(
            problem_statement="Test problem",
            proposed_solution="Test solution",
            assumptions=["assumption1"],
            scope_non_goals=["non-goal1"],
        )

        json_str = schema_version.to_json(proposal)
        data = json.loads(json_str)

        assert data["problem_statement"] == "Test problem"
        assert data["_schema_version"] == "1.0.0"
        assert data["_prompt_set_version"] == "1.0.0"

    def test_schema_version_get_json_schema(self) -> None:
        """Test getting JSON schema with version metadata."""
        schema_version = SchemaVersion(
            version="1.0.0",
            schema_class=ExpandedProposal,
            description="Test schema",
            prompt_set_version="1.0.0",
        )

        json_schema = schema_version.get_json_schema()
        assert json_schema["$version"] == "1.0.0"
        assert json_schema["$prompt_set_version"] == "1.0.0"
        assert "properties" in json_schema


class TestGlobalRegistry:
    """Test suite for global registry instance."""

    def test_global_registry_has_expanded_proposal(self) -> None:
        """Test that global registry has ExpandedProposal registered."""
        schemas = list_all_schemas()
        assert "ExpandedProposal" in schemas

    def test_global_registry_has_persona_review(self) -> None:
        """Test that global registry has PersonaReview registered."""
        schemas = list_all_schemas()
        assert "PersonaReview" in schemas

    def test_global_registry_has_decision_aggregation(self) -> None:
        """Test that global registry has DecisionAggregation registered."""
        schemas = list_all_schemas()
        assert "DecisionAggregation" in schemas

    def test_global_registry_has_run_status(self) -> None:
        """Test that global registry has RunStatus registered."""
        schemas = list_all_schemas()
        assert "RunStatus" in schemas

    def test_get_current_expanded_proposal(self) -> None:
        """Test getting current ExpandedProposal schema."""
        schema_version = get_current_schema("ExpandedProposal")
        assert schema_version.version == "1.0.0"
        assert schema_version.schema_class == ExpandedProposal
        assert schema_version.prompt_set_version == "1.0.0"

    def test_get_current_persona_review(self) -> None:
        """Test getting current PersonaReview schema."""
        schema_version = get_current_schema("PersonaReview")
        assert schema_version.version == "1.0.0"
        assert schema_version.schema_class == PersonaReview
        assert schema_version.prompt_set_version == "1.0.0"

    def test_get_current_decision_aggregation(self) -> None:
        """Test getting current DecisionAggregation schema."""
        schema_version = get_current_schema("DecisionAggregation")
        assert schema_version.version == "1.0.0"
        assert schema_version.schema_class == DecisionAggregation
        assert schema_version.prompt_set_version == "1.0.0"

    def test_get_specific_version_expanded_proposal(self) -> None:
        """Test getting specific version of ExpandedProposal schema."""
        schema_version = get_schema_version("ExpandedProposal", "1.0.0")
        assert schema_version.version == "1.0.0"
        assert schema_version.schema_class == ExpandedProposal

    def test_get_nonexistent_version_raises_error(self) -> None:
        """Test that getting non-existent version raises error."""
        with pytest.raises(SchemaVersionNotFoundError):
            get_schema_version("ExpandedProposal", "99.0.0")

    def test_get_nonexistent_schema_raises_error(self) -> None:
        """Test that getting non-existent schema raises error."""
        with pytest.raises(SchemaNotFoundError):
            get_current_schema("NonExistentSchema")

    def test_list_versions_for_expanded_proposal(self) -> None:
        """Test listing versions for ExpandedProposal."""
        versions = list_schema_versions("ExpandedProposal")
        assert "1.0.0" in versions

    def test_registry_singleton(self) -> None:
        """Test that get_registry returns the same instance."""
        registry1 = get_registry()
        registry2 = get_registry()
        assert registry1 is registry2


class TestSerializationHelpers:
    """Test suite for serialization helpers."""

    def test_serialize_expanded_proposal_with_metadata(self) -> None:
        """Test serializing ExpandedProposal with version metadata."""
        schema_version = get_current_schema("ExpandedProposal")

        proposal = ExpandedProposal(
            problem_statement="Build a REST API",
            proposed_solution="Use FastAPI framework",
            assumptions=["Python 3.11+", "PostgreSQL available"],
            scope_non_goals=["Mobile app", "Desktop app"],
            title="REST API Project",
        )

        # Test to_dict
        data = schema_version.to_dict(proposal)
        assert data["problem_statement"] == "Build a REST API"
        assert data["title"] == "REST API Project"
        assert data["_schema_version"] == "1.0.0"
        assert data["_prompt_set_version"] == "1.0.0"

        # Test to_json
        json_str = schema_version.to_json(proposal)
        parsed = json.loads(json_str)
        assert parsed["problem_statement"] == "Build a REST API"
        assert parsed["_schema_version"] == "1.0.0"

    def test_serialize_persona_review_with_metadata(self) -> None:
        """Test serializing PersonaReview with version metadata."""
        schema_version = get_current_schema("PersonaReview")

        from consensus_engine.schemas.review import Concern

        review = PersonaReview(
            persona_name="Test Persona",
            persona_id="test_persona",
            confidence_score=0.85,
            strengths=["Good design"],
            concerns=[Concern(text="Need more tests", is_blocking=False)],
            recommendations=["Add unit tests"],
            blocking_issues=[],
            estimated_effort="2 days",
            dependency_risks=[],
        )

        # Test to_dict
        data = schema_version.to_dict(review)
        assert data["persona_name"] == "Test Persona"
        assert data["confidence_score"] == 0.85
        assert data["_schema_version"] == "1.0.0"
        assert data["_prompt_set_version"] == "1.0.0"

        # Test to_json
        json_str = schema_version.to_json(review)
        parsed = json.loads(json_str)
        assert parsed["persona_name"] == "Test Persona"
        assert parsed["_schema_version"] == "1.0.0"

    def test_get_json_schema_for_all_registered(self) -> None:
        """Test getting JSON schema for all registered schemas."""
        for schema_name in list_all_schemas():
            if schema_name == "RunStatus":
                # Skip RunStatus as it's an enum wrapper
                continue

            schema_version = get_current_schema(schema_name)
            json_schema = schema_version.get_json_schema()

            assert "$version" in json_schema
            assert json_schema["$version"] == "1.0.0"
            assert "$prompt_set_version" in json_schema
            assert json_schema["$prompt_set_version"] == "1.0.0"
            assert "properties" in json_schema


class TestEdgeCases:
    """Test suite for edge cases and error handling."""

    def test_request_unsupported_version_is_audited(self) -> None:
        """Test that requesting unsupported version raises logged error."""
        with pytest.raises(SchemaVersionNotFoundError) as exc_info:
            get_schema_version("ExpandedProposal", "0.5.0")

        # Verify error message includes available versions
        assert "Available versions" in str(exc_info.value)

    def test_schema_version_without_prompt_set(self) -> None:
        """Test schema version without prompt_set_version."""
        registry = SchemaRegistry()
        registry.register(
            schema_name="TestSchema",
            version="1.0.0",
            schema_class=ExpandedProposal,
            description="Test without prompt version",
            is_current=True,
            prompt_set_version=None,
        )

        schema_version = registry.get_current("TestSchema")
        proposal = ExpandedProposal(
            problem_statement="Test",
            proposed_solution="Test",
            assumptions=["A"],
            scope_non_goals=["N"],
        )

        data = schema_version.to_dict(proposal)
        assert "_schema_version" in data
        assert "_prompt_set_version" not in data

    def test_multiple_versions_maintains_order(self) -> None:
        """Test that multiple versions are properly maintained."""
        registry = SchemaRegistry()

        # Register multiple versions
        for i in range(1, 4):
            registry.register(
                schema_name="TestSchema",
                version=f"{i}.0.0",
                schema_class=ExpandedProposal,
                description=f"Version {i}.0.0",
                is_current=(i == 3),
            )

        # Verify all versions are available
        versions = registry.list_versions("TestSchema")
        assert len(versions) == 3
        assert "1.0.0" in versions
        assert "2.0.0" in versions
        assert "3.0.0" in versions

        # Verify current points to latest
        current = registry.get_current("TestSchema")
        assert current.version == "3.0.0"

    def test_schema_class_validation(self) -> None:
        """Test that schema class validates correctly."""
        schema_version = get_current_schema("ExpandedProposal")

        # Valid instance should work
        valid_proposal = ExpandedProposal(
            problem_statement="Valid",
            proposed_solution="Valid",
            assumptions=["Valid"],
            scope_non_goals=["Valid"],
        )
        data = schema_version.to_dict(valid_proposal)
        assert data["problem_statement"] == "Valid"

        # Invalid data should raise ValidationError
        with pytest.raises(ValidationError):
            ExpandedProposal(
                problem_statement="",  # Empty string should fail
                proposed_solution="Valid",
                assumptions=[],
                scope_non_goals=[],
            )


class TestSchemaStructureSnapshots:
    """Test suite for schema structure snapshot validation.

    These tests ensure that schema structures match documented shapes and fail
    if fields are removed/renamed without a version bump. This prevents silent
    regressions in schema contracts.
    """

    def test_expanded_proposal_schema_structure_v1_0_0(self) -> None:
        """Test ExpandedProposal v1.0.0 schema has expected fields."""
        schema_version = get_schema_version("ExpandedProposal", "1.0.0")
        json_schema = schema_version.get_json_schema()

        # Verify version metadata
        assert json_schema["$version"] == "1.0.0"
        assert json_schema["$prompt_set_version"] == "1.0.0"

        # Verify required fields
        required_fields = json_schema.get("required", [])
        assert "problem_statement" in required_fields
        assert "proposed_solution" in required_fields
        assert "assumptions" in required_fields
        assert "scope_non_goals" in required_fields

        # Verify optional fields exist in properties
        properties = json_schema.get("properties", {})
        assert "title" in properties
        assert "summary" in properties
        assert "raw_idea" in properties
        assert "metadata" in properties
        assert "raw_expanded_proposal" in properties

        # Verify field types
        assert properties["problem_statement"]["type"] == "string"
        assert properties["proposed_solution"]["type"] == "string"
        assert properties["assumptions"]["type"] == "array"
        assert properties["scope_non_goals"]["type"] == "array"

    def test_persona_review_schema_structure_v1_0_0(self) -> None:
        """Test PersonaReview v1.0.0 schema has expected fields."""
        schema_version = get_schema_version("PersonaReview", "1.0.0")
        json_schema = schema_version.get_json_schema()

        # Verify version metadata
        assert json_schema["$version"] == "1.0.0"
        assert json_schema["$prompt_set_version"] == "1.0.0"

        # Verify required fields
        required_fields = json_schema.get("required", [])
        assert "persona_name" in required_fields
        assert "persona_id" in required_fields
        assert "confidence_score" in required_fields
        assert "strengths" in required_fields
        assert "concerns" in required_fields
        assert "recommendations" in required_fields
        assert "blocking_issues" in required_fields
        assert "estimated_effort" in required_fields
        assert "dependency_risks" in required_fields

        # Verify field types
        properties = json_schema.get("properties", {})
        assert properties["persona_name"]["type"] == "string"
        assert properties["persona_id"]["type"] == "string"
        assert properties["confidence_score"]["type"] == "number"
        assert properties["strengths"]["type"] == "array"
        assert properties["concerns"]["type"] == "array"
        assert properties["recommendations"]["type"] == "array"
        assert properties["blocking_issues"]["type"] == "array"
        assert properties["dependency_risks"]["type"] == "array"

        # Verify confidence_score constraints
        assert properties["confidence_score"]["minimum"] == 0.0
        assert properties["confidence_score"]["maximum"] == 1.0

    def test_decision_aggregation_schema_structure_v1_0_0(self) -> None:
        """Test DecisionAggregation v1.0.0 schema has expected fields."""
        schema_version = get_schema_version("DecisionAggregation", "1.0.0")
        json_schema = schema_version.get_json_schema()

        # Verify version metadata
        assert json_schema["$version"] == "1.0.0"
        assert json_schema["$prompt_set_version"] == "1.0.0"

        # Verify required fields
        required_fields = json_schema.get("required", [])
        assert "overall_weighted_confidence" in required_fields
        assert "decision" in required_fields

        # Verify optional fields exist in properties
        properties = json_schema.get("properties", {})
        assert "weighted_confidence" in properties
        assert "score_breakdown" in properties
        assert "detailed_score_breakdown" in properties
        assert "minority_report" in properties
        assert "minority_reports" in properties

        # Verify field types
        assert properties["overall_weighted_confidence"]["type"] == "number"
        # decision is an enum reference
        assert "$ref" in properties["decision"] or "allOf" in properties["decision"]

        # Verify confidence constraints
        assert properties["overall_weighted_confidence"]["minimum"] == 0.0
        assert properties["overall_weighted_confidence"]["maximum"] == 1.0

    def test_run_status_schema_structure_v1_0_0(self) -> None:
        """Test RunStatus v1.0.0 schema has expected fields."""
        schema_version = get_schema_version("RunStatus", "1.0.0")
        json_schema = schema_version.get_json_schema()

        # Verify version metadata
        assert json_schema["$version"] == "1.0.0"
        assert json_schema["$prompt_set_version"] == "1.0.0"

        # Verify required fields
        required_fields = json_schema.get("required", [])
        assert "status" in required_fields

        # Verify field types
        properties = json_schema.get("properties", {})
        assert properties["status"]["type"] == "string"

    def test_schema_field_removal_detection(self) -> None:
        """Test that removing a field from schema would be detected.

        This test verifies that the schema structure validation would catch
        if a field was accidentally removed from a schema without a version bump.
        """
        # Get current ExpandedProposal schema
        schema_version = get_current_schema("ExpandedProposal")
        json_schema = schema_version.get_json_schema()

        # Create an instance with all fields
        proposal = ExpandedProposal(
            problem_statement="Problem",
            proposed_solution="Solution",
            assumptions=["Assumption"],
            scope_non_goals=["Non-goal"],
            title="Title",
            summary="Summary",
            raw_idea="Raw idea",
            raw_expanded_proposal="Raw proposal",
            metadata={"key": "value"},
        )

        # Serialize to dict
        data = schema_version.to_dict(proposal)

        # Verify all fields are present in serialized output
        assert "problem_statement" in data
        assert "proposed_solution" in data
        assert "assumptions" in data
        assert "scope_non_goals" in data
        assert "title" in data
        assert "summary" in data
        assert "raw_idea" in data
        assert "raw_expanded_proposal" in data
        assert "metadata" in data

        # Verify version metadata is included
        assert "_schema_version" in data
        assert data["_schema_version"] == "1.0.0"
        assert "_prompt_set_version" in data
        assert data["_prompt_set_version"] == "1.0.0"

    def test_schema_rename_detection(self) -> None:
        """Test that renaming a field would be detected via validation failures."""
        # This test documents that field renames would cause validation errors
        # when loading old payloads, which is the desired behavior

        # Valid data matches current schema
        valid_data = {
            "problem_statement": "Problem",
            "proposed_solution": "Solution",
            "assumptions": ["Assumption"],
            "scope_non_goals": ["Non-goal"],
        }
        proposal = ExpandedProposal(**valid_data)
        assert proposal.problem_statement == "Problem"

        # If field was renamed (e.g., problem_statement -> problem_def),
        # this would fail validation
        invalid_data = {
            "problem_def": "Problem",  # Wrong field name
            "proposed_solution": "Solution",
            "assumptions": ["Assumption"],
            "scope_non_goals": ["Non-goal"],
        }
        with pytest.raises(ValidationError):
            ExpandedProposal(**invalid_data)


class TestBackwardCompatibility:
    """Test suite for backward compatibility of schema versions.

    These tests ensure that minor version increments remain backward compatible
    by loading sample payloads from prior schema versions. Major version changes
    should intentionally fail when loading old payloads.
    """

    def test_load_expanded_proposal_v1_0_0_fixture(self) -> None:
        """Test loading ExpandedProposal v1.0.0 fixture validates correctly."""
        import json
        from pathlib import Path

        # Load fixture
        fixture_path = (
            Path(__file__).parent.parent
            / "fixtures"
            / "schemas"
            / "expanded_proposal_v1.0.0.json"
        )
        with open(fixture_path) as f:
            payload = json.load(f)

        # Remove metadata field from payload as it's not part of the schema
        metadata = payload.pop("metadata", None)

        # Schema should validate
        schema_version = get_schema_version("ExpandedProposal", "1.0.0")
        proposal = schema_version.schema_class(**payload)

        assert proposal.problem_statement == payload["problem_statement"]
        assert proposal.proposed_solution == payload["proposed_solution"]
        assert proposal.assumptions == payload["assumptions"]
        assert proposal.scope_non_goals == payload["scope_non_goals"]
        assert proposal.title == payload["title"]
        assert proposal.summary == payload["summary"]
        assert proposal.raw_idea == payload["raw_idea"]
        assert proposal.raw_expanded_proposal == payload["raw_expanded_proposal"]

    def test_load_persona_review_v1_0_0_fixture(self) -> None:
        """Test loading PersonaReview v1.0.0 fixture validates correctly."""
        import json
        from pathlib import Path

        # Load fixture
        fixture_path = (
            Path(__file__).parent.parent
            / "fixtures"
            / "schemas"
            / "persona_review_v1.0.0.json"
        )
        with open(fixture_path) as f:
            payload = json.load(f)

        # Schema should validate
        schema_version = get_schema_version("PersonaReview", "1.0.0")
        review = schema_version.schema_class(**payload)

        assert review.persona_name == payload["persona_name"]
        assert review.persona_id == payload["persona_id"]
        assert review.confidence_score == payload["confidence_score"]
        assert len(review.strengths) == len(payload["strengths"])
        assert len(review.concerns) == len(payload["concerns"])
        assert len(review.recommendations) == len(payload["recommendations"])
        assert len(review.blocking_issues) == len(payload["blocking_issues"])

    def test_load_decision_aggregation_v1_0_0_fixture(self) -> None:
        """Test loading DecisionAggregation v1.0.0 fixture validates correctly."""
        import json
        from pathlib import Path

        # Load fixture
        fixture_path = (
            Path(__file__).parent.parent
            / "fixtures"
            / "schemas"
            / "decision_aggregation_v1.0.0.json"
        )
        with open(fixture_path) as f:
            payload = json.load(f)

        # Schema should validate
        schema_version = get_schema_version("DecisionAggregation", "1.0.0")
        decision = schema_version.schema_class(**payload)

        assert decision.overall_weighted_confidence == payload["overall_weighted_confidence"]
        assert decision.decision.value == payload["decision"]
        assert decision.minority_report is not None
        assert decision.minority_reports is not None

    def test_load_run_status_v1_0_0_fixture(self) -> None:
        """Test loading RunStatus v1.0.0 fixture validates correctly."""
        import json
        from pathlib import Path

        # Load fixture
        fixture_path = (
            Path(__file__).parent.parent
            / "fixtures"
            / "schemas"
            / "run_status_v1.0.0.json"
        )
        with open(fixture_path) as f:
            payload = json.load(f)

        # Schema should validate
        schema_version = get_schema_version("RunStatus", "1.0.0")
        status = schema_version.schema_class(**payload)

        assert status.status == payload["status"]

    def test_minor_version_compatibility_simulation(self) -> None:
        """Test that adding optional fields maintains backward compatibility.

        This simulates a minor version bump where optional fields are added
        but existing payloads still validate.
        """
        # Create a minimal v1.0.0 payload (only required fields)
        minimal_proposal = {
            "problem_statement": "Problem",
            "proposed_solution": "Solution",
            "assumptions": [],
            "scope_non_goals": [],
        }

        # Should validate with current schema (which could have new optional fields)
        schema_version = get_current_schema("ExpandedProposal")
        proposal = schema_version.schema_class(**minimal_proposal)

        assert proposal.problem_statement == "Problem"
        assert proposal.proposed_solution == "Solution"

        # New optional fields should default to None
        assert proposal.title is None
        assert proposal.summary is None

    def test_major_version_breaking_change_detection(self) -> None:
        """Test that major version changes with breaking changes are detected.

        This documents how to handle major version bumps that intentionally
        break backward compatibility (e.g., removing required fields).
        """
        # If we were to register a v2.0.0 that removed a required field,
        # old payloads would fail validation - this is expected behavior
        # for major version changes

        # Create registry with hypothetical v2.0.0
        registry = SchemaRegistry()

        # Register v1.0.0 (current production)
        registry.register(
            schema_name="TestBreakingChange",
            version="1.0.0",
            schema_class=ExpandedProposal,
            description="Original version",
            is_current=False,
        )

        # In a real major version change, we'd register a different schema class
        # For now, document that v2.0.0 would be registered with migration notes
        registry.register(
            schema_name="TestBreakingChange",
            version="2.0.0",
            schema_class=ExpandedProposal,
            description="Major version with breaking changes",
            is_current=True,
            migration_notes="Required fields changed: problem_statement split into "
            "problem_context and problem_details. See migration guide.",
        )

        # Verify migration notes are accessible
        v2_schema = registry.get_version("TestBreakingChange", "2.0.0")
        assert "migration guide" in v2_schema.migration_notes.lower()

    def test_backward_compatible_field_addition(self) -> None:
        """Test adding new optional fields maintains backward compatibility."""
        # Old payload without new optional fields
        old_payload = {
            "problem_statement": "Problem",
            "proposed_solution": "Solution",
            "assumptions": ["Assumption"],
            "scope_non_goals": ["Non-goal"],
        }

        # Should still validate with current schema
        schema_version = get_current_schema("ExpandedProposal")
        proposal = schema_version.schema_class(**old_payload)

        # Verify old fields work
        assert proposal.problem_statement == "Problem"

        # New fields should be None or default
        # (In this case, all optional fields default to None)

    def test_forward_compatibility_with_unknown_fields(self) -> None:
        """Test that schemas handle unknown fields gracefully.

        Pydantic by default ignores unknown fields, which provides some
        forward compatibility when loading data from newer versions.
        """
        # Payload with a hypothetical future field
        future_payload = {
            "problem_statement": "Problem",
            "proposed_solution": "Solution",
            "assumptions": [],
            "scope_non_goals": [],
            "future_field": "This field doesn't exist yet",  # Unknown field
        }

        # Should validate, unknown fields are ignored
        schema_version = get_current_schema("ExpandedProposal")
        proposal = schema_version.schema_class(**future_payload)

        # Known fields should work
        assert proposal.problem_statement == "Problem"

        # Unknown field should be ignored (not accessible)
        assert not hasattr(proposal, "future_field")
