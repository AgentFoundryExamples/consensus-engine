"""Versioned schema registry for deterministic contract management.

This module provides a centralized registry for all JSON schemas used in the
consensus engine, with explicit version metadata and serialization helpers.
Each schema contract (ExpandedProposal, PersonaReview, Decision, RunStatus)
is registered with semantic version identifiers to enable deterministic
contracts and safe prompt evolution.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from consensus_engine.db.models import RunStatus as DBRunStatus
from consensus_engine.schemas.proposal import ExpandedProposal
from consensus_engine.schemas.review import DecisionAggregation, PersonaReview

# Module-level logger
logger = logging.getLogger(__name__)


class SchemaNotFoundError(Exception):
    """Raised when a schema is not found in the registry."""

    pass


class SchemaVersionNotFoundError(Exception):
    """Raised when a specific schema version is not found."""

    pass


@dataclass
class SchemaVersion:
    """Metadata for a versioned schema definition.

    Attributes:
        version: Semantic version string (e.g., "1.0.0")
        schema_class: Pydantic model class for this version
        description: Human-readable description of this schema version
        prompt_set_version: Optional version identifier for associated prompts
        deprecated: Whether this version is deprecated
        migration_notes: Optional notes for migrating to/from this version
    """

    version: str
    schema_class: type[BaseModel]
    description: str
    prompt_set_version: str | None = None
    deprecated: bool = False
    migration_notes: str | None = None

    def to_dict(self, instance: BaseModel) -> dict[str, Any]:
        """Serialize a schema instance to a dictionary.

        Args:
            instance: Pydantic model instance to serialize

        Returns:
            Dictionary representation with version metadata
        """
        data = instance.model_dump(mode="python", exclude_none=False)
        data["_schema_version"] = self.version
        if self.prompt_set_version:
            data["_prompt_set_version"] = self.prompt_set_version
        return data

    def to_json(self, instance: BaseModel) -> str:
        """Serialize a schema instance to JSON.

        Args:
            instance: Pydantic model instance to serialize

        Returns:
            JSON string with version metadata
        """
        # Add version metadata to the JSON output
        data = self.to_dict(instance)
        return json.dumps(data, indent=2)

    def get_json_schema(self) -> dict[str, Any]:
        """Get the JSON schema for this version.

        Returns:
            JSON schema dictionary
        """
        schema = self.schema_class.model_json_schema()
        schema["$version"] = self.version
        if self.prompt_set_version:
            schema["$prompt_set_version"] = self.prompt_set_version
        return schema


class SchemaRegistry:
    """Centralized registry for versioned schemas.

    This registry maintains all schema contracts used in the consensus engine
    with explicit version tracking. It provides APIs to fetch current versions,
    request specific versions, and perform serialization with metadata.
    """

    def __init__(self) -> None:
        """Initialize the schema registry."""
        self._schemas: dict[str, dict[str, SchemaVersion]] = {}
        self._current_versions: dict[str, str] = {}

    def register(
        self,
        schema_name: str,
        version: str,
        schema_class: type[BaseModel],
        description: str,
        is_current: bool = False,
        prompt_set_version: str | None = None,
        deprecated: bool = False,
        migration_notes: str | None = None,
    ) -> None:
        """Register a schema version in the registry.

        Args:
            schema_name: Unique name for the schema (e.g., "ExpandedProposal")
            version: Semantic version string (e.g., "1.0.0")
            schema_class: Pydantic model class
            description: Human-readable description
            is_current: Whether this is the current active version
            prompt_set_version: Optional prompt version identifier
            deprecated: Whether this version is deprecated
            migration_notes: Optional migration guidance

        Raises:
            ValueError: If version format is invalid or already registered
        """
        # Validate semantic versioning format (MAJOR.MINOR.PATCH)
        semver_pattern = r"^\d+\.\d+\.\d+$"
        if not re.match(semver_pattern, version):
            raise ValueError(
                f"Invalid version format '{version}'. "
                f"Expected semantic versioning format: MAJOR.MINOR.PATCH (e.g., '1.0.0')"
            )

        if schema_name not in self._schemas:
            self._schemas[schema_name] = {}

        if version in self._schemas[schema_name]:
            raise ValueError(
                f"Schema '{schema_name}' version '{version}' is already registered"
            )

        schema_version = SchemaVersion(
            version=version,
            schema_class=schema_class,
            description=description,
            prompt_set_version=prompt_set_version,
            deprecated=deprecated,
            migration_notes=migration_notes,
        )

        self._schemas[schema_name][version] = schema_version

        if is_current:
            self._current_versions[schema_name] = version

    def get_current(self, schema_name: str) -> SchemaVersion:
        """Get the current version of a schema.

        Args:
            schema_name: Name of the schema to retrieve

        Returns:
            SchemaVersion for the current version

        Raises:
            SchemaNotFoundError: If schema is not registered
        """
        if schema_name not in self._schemas:
            raise SchemaNotFoundError(
                f"Schema '{schema_name}' not found in registry. "
                f"Available schemas: {list(self._schemas.keys())}"
            )

        if schema_name not in self._current_versions:
            raise SchemaNotFoundError(
                f"No current version set for schema '{schema_name}'"
            )

        version = self._current_versions[schema_name]
        return self._schemas[schema_name][version]

    def get_version(self, schema_name: str, version: str) -> SchemaVersion:
        """Get a specific version of a schema.

        Args:
            schema_name: Name of the schema to retrieve
            version: Version string to retrieve

        Returns:
            SchemaVersion for the requested version

        Raises:
            SchemaNotFoundError: If schema is not registered
            SchemaVersionNotFoundError: If version is not found
        """
        if schema_name not in self._schemas:
            raise SchemaNotFoundError(
                f"Schema '{schema_name}' not found in registry. "
                f"Available schemas: {list(self._schemas.keys())}"
            )

        if version not in self._schemas[schema_name]:
            available_versions = list(self._schemas[schema_name].keys())
            raise SchemaVersionNotFoundError(
                f"Version '{version}' not found for schema '{schema_name}'. "
                f"Available versions: {available_versions}"
            )

        schema_version = self._schemas[schema_name][version]

        # Log warning if version is deprecated
        if schema_version.deprecated:
            logger.warning(
                f"Schema '{schema_name}' version '{version}' is deprecated. "
                f"Migration notes: {schema_version.migration_notes or 'None provided'}"
            )

        return schema_version

    def list_schemas(self) -> list[str]:
        """List all registered schema names.

        Returns:
            List of schema names
        """
        return list(self._schemas.keys())

    def list_versions(self, schema_name: str) -> list[str]:
        """List all registered versions for a schema.

        Args:
            schema_name: Name of the schema

        Returns:
            List of version strings

        Raises:
            SchemaNotFoundError: If schema is not registered
        """
        if schema_name not in self._schemas:
            raise SchemaNotFoundError(
                f"Schema '{schema_name}' not found in registry. "
                f"Available schemas: {list(self._schemas.keys())}"
            )

        return list(self._schemas[schema_name].keys())

    def get_current_version_string(self, schema_name: str) -> str:
        """Get the current version string for a schema.

        Args:
            schema_name: Name of the schema

        Returns:
            Current version string

        Raises:
            SchemaNotFoundError: If schema is not registered or no current version set
        """
        if schema_name not in self._current_versions:
            raise SchemaNotFoundError(
                f"No current version set for schema '{schema_name}'"
            )
        return self._current_versions[schema_name]


# Global registry instance
_registry = SchemaRegistry()


def get_registry() -> SchemaRegistry:
    """Get the global schema registry instance.

    Returns:
        The global SchemaRegistry instance
    """
    return _registry


# Register all schemas with version 1.0.0
_registry.register(
    schema_name="ExpandedProposal",
    version="1.0.0",
    schema_class=ExpandedProposal,
    description="Structured output from LLM expansion service with problem statement, "
    "solution, assumptions, and scope",
    is_current=True,
    prompt_set_version="1.0.0",
)

_registry.register(
    schema_name="PersonaReview",
    version="1.0.0",
    schema_class=PersonaReview,
    description="Review from a specific persona evaluating a proposal with confidence, "
    "strengths, concerns, and blocking issues",
    is_current=True,
    prompt_set_version="1.0.0",
)

_registry.register(
    schema_name="DecisionAggregation",
    version="1.0.0",
    schema_class=DecisionAggregation,
    description="Aggregated decision from multiple persona reviews with weighted "
    "confidence and optional minority reports",
    is_current=True,
    prompt_set_version="1.0.0",
)

# Note: RunStatus is an enum in the database models, not a Pydantic schema
# For compatibility, we'll add a simple wrapper model with conversion helpers


class RunStatusModel(BaseModel):
    """Simple Pydantic model wrapper for RunStatus enum metadata.

    This provides a consistent interface for the registry while maintaining
    compatibility with the database enum.
    """

    status: str

    @classmethod
    def from_enum(cls, status: DBRunStatus) -> "RunStatusModel":
        """Create from database enum.

        Args:
            status: RunStatus enum value

        Returns:
            RunStatusModel instance
        """
        return cls(status=status.value)

    def to_enum(self) -> DBRunStatus:
        """Convert to database enum.

        Returns:
            RunStatus enum value
        """
        return DBRunStatus(self.status)


_registry.register(
    schema_name="RunStatus",
    version="1.0.0",
    schema_class=RunStatusModel,
    description="Run lifecycle state enum (queued, running, completed, failed)",
    is_current=True,
    prompt_set_version="1.0.0",
)


# Public API functions
def get_current_schema(schema_name: str) -> SchemaVersion:
    """Get the current version of a schema.

    Args:
        schema_name: Name of the schema to retrieve

    Returns:
        SchemaVersion for the current version

    Raises:
        SchemaNotFoundError: If schema is not registered
    """
    return _registry.get_current(schema_name)


def get_schema_version(schema_name: str, version: str) -> SchemaVersion:
    """Get a specific version of a schema.

    Args:
        schema_name: Name of the schema to retrieve
        version: Version string to retrieve

    Returns:
        SchemaVersion for the requested version

    Raises:
        SchemaNotFoundError: If schema is not registered
        SchemaVersionNotFoundError: If version is not found
    """
    return _registry.get_version(schema_name, version)


def list_all_schemas() -> list[str]:
    """List all registered schema names.

    Returns:
        List of schema names
    """
    return _registry.list_schemas()


def list_schema_versions(schema_name: str) -> list[str]:
    """List all registered versions for a schema.

    Args:
        schema_name: Name of the schema

    Returns:
        List of version strings

    Raises:
        SchemaNotFoundError: If schema is not registered
    """
    return _registry.list_versions(schema_name)


__all__ = [
    "SchemaVersion",
    "SchemaRegistry",
    "SchemaNotFoundError",
    "SchemaVersionNotFoundError",
    "get_registry",
    "get_current_schema",
    "get_schema_version",
    "list_all_schemas",
    "list_schema_versions",
    "RunStatusModel",
]
