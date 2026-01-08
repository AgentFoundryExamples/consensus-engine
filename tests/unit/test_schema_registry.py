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
