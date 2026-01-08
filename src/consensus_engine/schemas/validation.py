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
"""Schema validation utilities for registry-based validation.

This module provides helper functions to validate Pydantic model instances
against registered schema versions, ensuring responses match expected contracts.
"""

import logging
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from consensus_engine.exceptions import SchemaValidationError
from consensus_engine.schemas.registry import SchemaVersion, get_current_schema

logger = logging.getLogger(__name__)

# Type variable for generic response model
T = TypeVar("T", bound=BaseModel)


def validate_against_schema(
    instance: BaseModel,
    schema_name: str,
    schema_version: SchemaVersion | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """Validate a Pydantic model instance against a registered schema version.

    This function ensures that the instance conforms to the expected schema
    contract. If schema_version is not provided, uses the current version.

    Args:
        instance: The Pydantic model instance to validate
        schema_name: Name of the schema in the registry (e.g., "ExpandedProposal")
        schema_version: Optional specific SchemaVersion to validate against
        context: Optional context for error reporting (request_id, step_name, etc.)

    Raises:
        SchemaValidationError: If validation fails, includes schema_version and field path
    """
    context = context or {}

    # Get schema version if not provided
    if schema_version is None:
        try:
            schema_version = get_current_schema(schema_name)
        except Exception as e:
            raise SchemaValidationError(
                f"Failed to get current schema for '{schema_name}': {str(e)}",
                details={
                    "schema_name": schema_name,
                    **context,
                },
            ) from e

    # Get the expected Pydantic class
    expected_class = schema_version.schema_class

    # Check if instance is of the expected type
    if not isinstance(instance, expected_class):
        raise SchemaValidationError(
            f"Instance type mismatch: expected {expected_class.__name__}, "
            f"got {type(instance).__name__}",
            details={
                "schema_name": schema_name,
                "schema_version": schema_version.version,
                "expected_type": expected_class.__name__,
                "actual_type": type(instance).__name__,
                **context,
            },
        )

    # Validate the instance by re-parsing it through the model
    # This ensures all validators and constraints are checked
    try:
        # Serialize and re-parse to trigger all validation
        data = instance.model_dump(mode="python")
        expected_class.model_validate(data)
    except ValidationError as e:
        # Extract field paths and error messages
        field_errors = []
        for error in e.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            field_errors.append({
                "field": field_path,
                "message": error["msg"],
                "type": error["type"],
            })

        raise SchemaValidationError(
            f"Schema validation failed for {schema_name} v{schema_version.version}",
            details={
                "schema_name": schema_name,
                "schema_version": schema_version.version,
                "field_errors": field_errors,
                "error_count": len(field_errors),
                **context,
            },
        ) from e

    logger.debug(
        f"Successfully validated instance against {schema_name} v{schema_version.version}",
        extra={
            "schema_name": schema_name,
            "schema_version": schema_version.version,
            **context,
        },
    )


def get_schema_version_info(schema_name: str) -> dict[str, Any]:
    """Get version information for a schema.

    Args:
        schema_name: Name of the schema in the registry

    Returns:
        Dictionary with schema version information

    Raises:
        SchemaValidationError: If schema is not found
    """
    try:
        schema_version = get_current_schema(schema_name)
        return {
            "schema_name": schema_name,
            "schema_version": schema_version.version,
            "prompt_set_version": schema_version.prompt_set_version,
            "description": schema_version.description,
            "deprecated": schema_version.deprecated,
        }
    except Exception as e:
        raise SchemaValidationError(
            f"Failed to get schema version info for '{schema_name}': {str(e)}",
            details={"schema_name": schema_name},
        ) from e


def check_version_consistency(
    schema_versions: list[dict[str, Any]],
    context: dict[str, Any] | None = None,
) -> None:
    """Check that all schema versions in a collection are consistent.

    This function ensures that all schemas used within a single deployment/run
    are using the same schema versions, preventing mixed version scenarios.

    Args:
        schema_versions: List of schema version info dicts with schema_name and schema_version
        context: Optional context for error reporting (run_id, etc.)

    Raises:
        SchemaValidationError: If version inconsistency is detected
    """
    context = context or {}

    if not schema_versions:
        return

    # Group by schema name and track prompt_set_version
    versions_by_schema: dict[str, set[str]] = {}
    prompt_set_versions: set[str] = set()
    
    for info in schema_versions:
        schema_name = info.get("schema_name")
        schema_version = info.get("schema_version")

        if not schema_name or not schema_version:
            continue

        if schema_name not in versions_by_schema:
            versions_by_schema[schema_name] = set()
        versions_by_schema[schema_name].add(schema_version)
        
        # Track prompt_set_version if present
        prompt_set_version = info.get("prompt_set_version")
        if prompt_set_version:
            prompt_set_versions.add(prompt_set_version)

    # Check for multiple versions of the same schema
    inconsistent_schemas = {
        name: versions
        for name, versions in versions_by_schema.items()
        if len(versions) > 1
    }

    # Check for multiple prompt_set_versions
    has_mixed_prompts = len(prompt_set_versions) > 1
    
    if inconsistent_schemas or has_mixed_prompts:
        error_details = {
            **context,
        }
        message = []

        if inconsistent_schemas:
            error_details["inconsistent_schemas"] = {
                name: list(versions)
                for name, versions in inconsistent_schemas.items()
            }
            message.append("Mixed schema versions detected")
        
        if has_mixed_prompts:
            error_details["mixed_prompt_versions"] = list(prompt_set_versions)
            message.append("Mixed prompt versions detected")
            # Provide detailed context for debugging mixed prompt versions
            affected_sources = [
                info.get("source", "unknown") 
                for info in schema_versions 
                if info.get("prompt_set_version") in prompt_set_versions
            ]
            logger.warning(
                "Mixed prompt_set_versions detected within run - this may indicate "
                "a deployment issue or concurrent version rollout. Review the affected "
                "pipeline steps and ensure all workers are running the same version.",
                extra={
                    "prompt_versions": list(prompt_set_versions),
                    "affected_sources": affected_sources,
                    "version_count": len(prompt_set_versions),
                    **context,
                },
            )
        
        raise SchemaValidationError(
            f"{' and '.join(message)} within deployment.",
            details=error_details,
        )

    logger.debug(
        "Schema version consistency check passed",
        extra={
            "schema_count": len(versions_by_schema),
            "schemas": list(versions_by_schema.keys()),
            "prompt_set_versions": list(prompt_set_versions) if prompt_set_versions else ["none"],
            **context,
        },
    )


__all__ = [
    "validate_against_schema",
    "get_schema_version_info",
    "check_version_consistency",
]
