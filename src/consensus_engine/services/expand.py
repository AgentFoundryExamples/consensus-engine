"""Expand service for transforming ideas into detailed proposals.

This module provides the expandIdea service that uses OpenAI's structured
outputs to expand a simple idea into a comprehensive proposal with validated
structure.
"""

from typing import Any

from consensus_engine.clients.openai_client import OpenAIClientWrapper
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
    ExpandedProposal model.

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

    # Construct user prompt
    user_prompt = f"Expand the following idea into a detailed proposal:\n\n{idea_input.idea}"

    # Add extra context if provided
    if idea_input.extra_context:
        user_prompt += f"\n\nAdditional Context:\n{idea_input.extra_context}"

    # Initialize OpenAI client
    client = OpenAIClientWrapper(settings)

    # Call OpenAI with structured output
    parsed_response, metadata = client.create_structured_response(
        system_instruction=SYSTEM_INSTRUCTION,
        user_prompt=user_prompt,
        response_model=ExpandedProposal,
        developer_instruction=DEVELOPER_INSTRUCTION,
    )

    # Log success without sensitive data
    logger.info(
        "Idea expansion completed successfully",
        extra={
            "request_id": metadata.get("request_id"),
            "model": metadata.get("model"),
            "temperature": metadata.get("temperature"),
            "elapsed_time": metadata.get("elapsed_time"),
            "status": "success",
        },
    )

    return parsed_response, metadata
