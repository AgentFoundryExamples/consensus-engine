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
"""API boundary validation utilities.

This module provides validation functions for API routes to enforce
configurable size limits and business rules before enqueueing jobs or
processing requests.
"""

import logging
from typing import Any

from consensus_engine.config import Settings
from consensus_engine.config.llm_steps import PROMPT_SET_VERSION, SCHEMA_VERSION
from consensus_engine.exceptions import UnsupportedVersionError, ValidationError

logger = logging.getLogger(__name__)


def validate_version_headers(
    schema_version: str | None,
    prompt_set_version: str | None,
    settings: Settings,
) -> dict[str, str]:
    """Validate schema and prompt set version headers.

    If versions are not provided, falls back to current deployment defaults
    with a warning. If versions are provided but unsupported, raises an error
    with guidance to upgrade.

    Args:
        schema_version: Requested schema version (e.g., from X-Schema-Version header)
        prompt_set_version: Requested prompt set version (e.g., from X-Prompt-Set-Version header)
        settings: Application settings

    Returns:
        Dictionary with validated/defaulted schema_version and prompt_set_version

    Raises:
        UnsupportedVersionError: If requested version is not supported
    """
    # Get supported versions from config
    llm_config = settings.get_llm_steps_config()
    supported_schema_version = llm_config.schema_version
    supported_prompt_version = llm_config.prompt_set_version

    # Validate or default schema_version
    if schema_version is None:
        logger.warning(
            "No schema_version header provided, using current deployment default",
            extra={"default_schema_version": supported_schema_version},
        )
        schema_version = supported_schema_version
    elif schema_version != supported_schema_version:
        raise UnsupportedVersionError(
            f"Schema version '{schema_version}' is not supported. "
            f"Current supported version: '{supported_schema_version}'. "
            f"Please upgrade your client to use the supported API version.",
            details={
                "requested_schema_version": schema_version,
                "supported_schema_version": supported_schema_version,
                "api_version": "v1",
            },
        )

    # Validate or default prompt_set_version
    if prompt_set_version is None:
        logger.warning(
            "No prompt_set_version header provided, using current deployment default",
            extra={"default_prompt_version": supported_prompt_version},
        )
        prompt_set_version = supported_prompt_version
    elif prompt_set_version != supported_prompt_version:
        raise UnsupportedVersionError(
            f"Prompt set version '{prompt_set_version}' is not supported. "
            f"Current supported version: '{supported_prompt_version}'. "
            f"Please upgrade your client to use the supported API version.",
            details={
                "requested_prompt_set_version": prompt_set_version,
                "supported_prompt_set_version": supported_prompt_version,
                "api_version": "v1",
            },
        )

    return {
        "schema_version": schema_version,
        "prompt_set_version": prompt_set_version,
    }


def log_validation_failure(
    field: str,
    rule: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Log validation failure with metadata for auditing.

    Does not log sensitive content like full proposal text, only metadata
    about the failure (field name, rule violated, length, etc).

    Args:
        field: Name of the field that failed validation
        rule: Name of the validation rule that was violated
        message: Human-readable error message
        metadata: Optional additional metadata (request_id, field_length, etc.)
    """
    log_metadata = {
        "field": field,
        "rule": rule,
        "validation_failure": True,
        **(metadata or {}),
    }

    # Sanitize metadata to avoid logging sensitive content
    # Whitelist of allowed metadata keys for logging
    allowed_keys = {
        "field", "rule", "validation_failure", "request_id", "field_length", "limit",
        "requested_schema_version", "supported_schema_version",
        "requested_prompt_set_version", "supported_prompt_set_version",
        "api_version", "run_id", "parent_run_id", "new_run_id"
    }
    sanitized_metadata = {}
    for key, value in log_metadata.items():
        # Only log metadata about size/length, not actual content
        if key in allowed_keys:
            sanitized_metadata[key] = value
        elif key.endswith("_length") or key.endswith("_size") or key.endswith("_count"):
            sanitized_metadata[key] = value

    logger.warning(
        f"Validation failure: {message}",
        extra=sanitized_metadata,
    )


__all__ = [
    "validate_version_headers",
    "log_validation_failure",
]
