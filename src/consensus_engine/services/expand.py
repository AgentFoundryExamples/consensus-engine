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
"""Expand service for transforming ideas into detailed proposals.

This module provides the expandIdea service that uses OpenAI's structured
outputs to expand a simple idea into a comprehensive proposal with validated
structure. Uses centralized configuration and instruction builder.
"""

import json
from datetime import UTC, datetime
from typing import Any

from consensus_engine.clients.openai_client import OpenAIClientWrapper
from consensus_engine.config.instruction_builder import InstructionBuilder
from consensus_engine.config.llm_steps import StepName
from consensus_engine.config.logging import get_logger
from consensus_engine.config.settings import Settings
from consensus_engine.schemas.proposal import ExpandedProposal, IdeaInput

logger = get_logger(__name__)

# System instruction enforcing safety boundaries and JSON-only responses
SYSTEM_INSTRUCTION = """You are a technical proposal assistant that expands brief ideas \
into detailed, structured proposals.

Your task is to:
1. Analyze the provided idea thoroughly
2. Articulate a clear problem statement
3. Propose a detailed solution approach
4. Identify key assumptions
5. Define scope boundaries and non-goals
6. Provide comprehensive documentation

You must respond ONLY with structured JSON matching the expected schema.
Do not include any free-form text outside the structured format.
Ensure all responses are professional, technically sound, and actionable."""

# Developer instruction for additional guidance
DEVELOPER_INSTRUCTION = """Focus on technical accuracy and completeness.
Ensure assumptions are realistic and scope boundaries are clearly defined.
The proposal should be implementable and maintainable."""


def expand_idea(
    idea_input: IdeaInput, settings: Settings
) -> tuple[ExpandedProposal, dict[str, Any]]:
    """Expand a simple idea into a detailed proposal using OpenAI structured outputs.

    This function validates the input payload, constructs appropriate prompts,
    invokes the OpenAI client with structured outputs, and returns a validated
    ExpandedProposal model. Uses centralized configuration and instruction builder.

    Args:
        idea_input: Validated input payload containing the idea and optional context
        settings: Application settings for OpenAI client configuration

    Returns:
        Tuple of (ExpandedProposal instance, metadata dict with request_id, timing, etc.)

    Raises:
        LLMServiceError: For OpenAI API errors
        SchemaValidationError: If response doesn't match expected schema
        ValidationError: If input validation fails
    """
    logger.info("Starting idea expansion")

    # Get centralized step configuration
    llm_config = settings.get_llm_steps_config()
    expand_config = llm_config.get_step_config(StepName.EXPAND)

    # Construct user prompt (note: prompt contains user input but is never logged)
    user_prompt = f"Expand the following idea into a detailed proposal:\n\n{idea_input.idea}"

    # Add extra context if provided
    if idea_input.extra_context:
        user_prompt += f"\n\nAdditional Context:\n{idea_input.extra_context}"

    # Build instruction payload using InstructionBuilder
    instruction_payload = InstructionBuilder.create_expand_payload(
        system_instruction=SYSTEM_INSTRUCTION,
        developer_instruction=DEVELOPER_INSTRUCTION,
        user_content=user_prompt,
    )

    # Initialize OpenAI client
    client = OpenAIClientWrapper(settings)

    # Call OpenAI with structured output using instruction payload
    parsed_response, metadata = client.create_structured_response_with_payload(
        instruction_payload=instruction_payload,
        response_model=ExpandedProposal,
        step_name="expand",
        schema_name="ExpandedProposal",
        model_override=expand_config.model,
        temperature_override=expand_config.temperature,
        max_retries=expand_config.max_retries,
    )

    # Log success without sensitive data
    logger.info(
        "Idea expansion completed successfully",
        extra={
            "request_id": metadata.get("request_id"),
            "step_name": "expand",
            "model": metadata.get("model"),
            "temperature": metadata.get("temperature"),
            "elapsed_time": metadata.get("elapsed_time"),
            "latency": metadata.get("latency"),
            "schema_version": metadata.get("schema_version"),
            "prompt_set_version": metadata.get("prompt_set_version"),
            "status": "success",
        },
    )

    return parsed_response, metadata


def expand_with_edits(
    parent_proposal: ExpandedProposal,
    edited_proposal: dict[str, Any] | str | None,
    edit_notes: str | None,
    settings: Settings,
) -> tuple[ExpandedProposal, dict[str, Any], dict[str, Any]]:
    """Expand a proposal with edits applied, generating a new version and diff.

    This function takes a parent proposal and edit inputs, merges them intelligently,
    re-expands via the LLM to ensure coherence, and computes a diff for auditability.
    Uses centralized configuration and instruction builder.

    Args:
        parent_proposal: The parent ExpandedProposal to base revisions on
        edited_proposal: Edited proposal as structured JSON or free-form text
        edit_notes: Optional notes about what was edited
        settings: Application settings for OpenAI client configuration

    Returns:
        Tuple of (new ExpandedProposal, metadata, diff_json)

    Raises:
        LLMServiceError: For OpenAI API errors
        SchemaValidationError: If response doesn't match expected schema
        ValidationError: If input validation fails
    """
    logger.info("Starting proposal expansion with edits")

    # Get centralized step configuration
    llm_config = settings.get_llm_steps_config()
    expand_config = llm_config.get_step_config(StepName.EXPAND)

    # Build the edit context from parent proposal and edit inputs
    parent_dict = json.loads(parent_proposal.model_dump_json())

    # Construct user prompt that merges parent with edits
    user_prompt = "Generate an improved proposal based on the following:\n\n"
    user_prompt += "**Original Proposal:**\n"
    user_prompt += f"Problem Statement: {parent_proposal.problem_statement}\n"
    user_prompt += f"Proposed Solution: {parent_proposal.proposed_solution}\n"
    user_prompt += f"Assumptions: {', '.join(parent_proposal.assumptions)}\n"
    user_prompt += f"Scope/Non-Goals: {', '.join(parent_proposal.scope_non_goals)}\n\n"

    # Add edit information
    if edited_proposal is not None:
        if isinstance(edited_proposal, str):
            user_prompt += f"**Edit Instructions:**\n{edited_proposal}\n\n"
        else:
            user_prompt += "**Proposed Changes:**\n"
            for key, value in edited_proposal.items():
                user_prompt += f"- {key}: {value}\n"
            user_prompt += "\n"

    if edit_notes:
        user_prompt += f"**Edit Notes:**\n{edit_notes}\n\n"

    user_prompt += (
        "Generate a complete, revised proposal that incorporates these edits "
        "while maintaining coherence and completeness."
    )

    # Build instruction payload using InstructionBuilder
    instruction_payload = InstructionBuilder.create_expand_payload(
        system_instruction=SYSTEM_INSTRUCTION,
        developer_instruction=DEVELOPER_INSTRUCTION,
        user_content=user_prompt,
    )

    # Initialize OpenAI client
    client = OpenAIClientWrapper(settings)

    # Call OpenAI with structured output using instruction payload
    parsed_response, metadata = client.create_structured_response_with_payload(
        instruction_payload=instruction_payload,
        response_model=ExpandedProposal,
        step_name="expand_with_edits",
        schema_name="ExpandedProposal",
        model_override=expand_config.model,
        temperature_override=expand_config.temperature,
        max_retries=expand_config.max_retries,
    )

    # Compute diff between parent and new proposal
    new_dict = json.loads(parsed_response.model_dump_json())
    diff_json = _compute_proposal_diff(parent_dict, new_dict)

    # Log success without sensitive data
    logger.info(
        "Proposal expansion with edits completed successfully",
        extra={
            "request_id": metadata.get("request_id"),
            "step_name": "expand_with_edits",
            "model": metadata.get("model"),
            "temperature": metadata.get("temperature"),
            "elapsed_time": metadata.get("elapsed_time"),
            "latency": metadata.get("latency"),
            "schema_version": metadata.get("schema_version"),
            "prompt_set_version": metadata.get("prompt_set_version"),
            "status": "success",
            "diff_fields": list(diff_json.get("changed_fields", {}).keys()),
        },
    )

    return parsed_response, metadata, diff_json


def _compute_proposal_diff(
    parent: dict[str, Any],
    revised: dict[str, Any],
) -> dict[str, Any]:
    """Compute a simple diff between parent and revised proposals.

    Args:
        parent: Parent proposal as dictionary
        revised: Revised proposal as dictionary

    Returns:
        Dictionary containing diff metadata with changed_fields and summary
    """
    changed_fields: dict[str, dict[str, Any]] = {}

    # Check each field for changes
    for key in set(parent.keys()) | set(revised.keys()):
        parent_value = parent.get(key)
        revised_value = revised.get(key)

        if parent_value != revised_value:
            changed_fields[key] = {
                "before": parent_value,
                "after": revised_value,
            }

    return {
        "changed_fields": changed_fields,
        "num_changes": len(changed_fields),
        "timestamp": datetime.now(UTC).isoformat(),
    }
