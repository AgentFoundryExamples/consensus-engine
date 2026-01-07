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
"""Review service for evaluating proposals with persona-based analysis.

This module provides the reviewProposal service that uses OpenAI's structured
outputs to generate persona-based reviews of expanded proposals with validated
structure.
"""

from typing import Any

from consensus_engine.clients.openai_client import OpenAIClientWrapper
from consensus_engine.config.logging import get_logger
from consensus_engine.config.settings import Settings
from consensus_engine.schemas.proposal import ExpandedProposal
from consensus_engine.schemas.review import PersonaReview

logger = get_logger(__name__)

# System instruction for the review process
REVIEW_SYSTEM_INSTRUCTION = """You are an expert technical reviewer evaluating proposals \
for feasibility, completeness, and potential risks.

Your task is to:
1. Evaluate the proposal objectively from your assigned persona perspective
2. Identify key strengths and positive aspects
3. Surface concerns and potential issues, marking blocking issues clearly
4. Provide actionable recommendations for improvement
5. Assess dependency risks and effort estimation
6. Assign a confidence score reflecting your assessment

You must respond ONLY with structured JSON matching the PersonaReview schema.
Do not include any free-form text outside the structured format.
Base your review on technical merit, feasibility, and completeness."""

# Developer instruction template for persona-specific guidance
REVIEW_DEVELOPER_INSTRUCTION_TEMPLATE = (
    """Review this proposal from the perspective of: {persona_name}

Persona instructions: {persona_instructions}

Provide your review using the PersonaReview schema with the following fields:
- persona_name: Your assigned persona name
- confidence_score: Float between 0.0 and 1.0 indicating confidence in the proposal
- strengths: List of identified strengths
- concerns: List of Concern objects with text and is_blocking flag
- recommendations: List of actionable recommendations
- blocking_issues: List of critical blocking issues (can be empty)
- estimated_effort: Effort estimation as string or structured data
- dependency_risks: List of identified dependency risks (can be empty)

Be thorough, specific, and constructive in your feedback."""
)


def review_proposal(
    expanded_proposal: ExpandedProposal,
    settings: Settings,
    persona_name: str | None = None,
    persona_instructions: str | None = None,
) -> tuple[PersonaReview, dict[str, Any]]:
    """Review an expanded proposal using OpenAI structured outputs with persona context.

    This function validates the input proposal, constructs persona-aware prompts,
    invokes the OpenAI client with structured outputs, and returns a validated
    PersonaReview model.

    Args:
        expanded_proposal: Validated ExpandedProposal to review
        settings: Application settings for OpenAI client configuration
        persona_name: Name of the reviewing persona (default: from settings)
        persona_instructions: Custom persona instructions (default: from settings)

    Returns:
        Tuple of (PersonaReview instance, metadata dict with request_id, timing, etc.)

    Raises:
        LLMServiceError: For OpenAI API errors
        SchemaValidationError: If response doesn't match expected schema
        ValidationError: If input validation fails
    """
    # Use defaults from settings if not provided
    persona_name = persona_name or settings.default_persona_name
    persona_instructions = persona_instructions or settings.default_persona_instructions

    logger.info(
        f"Starting proposal review with persona={persona_name}",
        extra={"persona_name": persona_name},
    )

    # Construct developer instruction with persona context
    developer_instruction = REVIEW_DEVELOPER_INSTRUCTION_TEMPLATE.format(
        persona_name=persona_name,
        persona_instructions=persona_instructions,
    )

    # Construct user prompt with proposal details
    # Note: prompt contains proposal but is never logged
    # Truncate very long fields to avoid token limits
    max_field_length = 2000
    problem_statement = expanded_proposal.problem_statement[:max_field_length]
    proposed_solution = expanded_proposal.proposed_solution[:max_field_length]

    user_prompt = f"""Review the following proposal:

**Problem Statement:**
{problem_statement}

**Proposed Solution:**
{proposed_solution}

**Assumptions:**
{chr(10).join(f"- {a[:500]}" for a in expanded_proposal.assumptions[:10])}

**Scope/Non-Goals:**
{chr(10).join(f"- {s[:500]}" for s in expanded_proposal.scope_non_goals[:10])}
"""

    # Add optional fields if present
    if expanded_proposal.title:
        user_prompt = f"**Title:** {expanded_proposal.title}\n\n" + user_prompt

    if expanded_proposal.summary:
        summary_truncated = expanded_proposal.summary[:max_field_length]
        user_prompt = f"**Summary:** {summary_truncated}\n\n" + user_prompt

    # Initialize OpenAI client
    client = OpenAIClientWrapper(settings)

    # Call OpenAI with structured output for review
    parsed_response, metadata = client.create_structured_response(
        system_instruction=REVIEW_SYSTEM_INSTRUCTION,
        user_prompt=user_prompt,
        response_model=PersonaReview,
        developer_instruction=developer_instruction,
        step_name="review",
        model_override=settings.review_model,
        temperature_override=settings.review_temperature,
    )

    # Log success without sensitive data
    logger.info(
        f"Proposal review completed successfully with persona={persona_name}",
        extra={
            "request_id": metadata.get("request_id"),
            "step_name": "review",
            "persona_name": persona_name,
            "model": metadata.get("model"),
            "temperature": metadata.get("temperature"),
            "elapsed_time": metadata.get("elapsed_time"),
            "latency": metadata.get("latency"),
            "status": "success",
        },
    )

    return parsed_response, metadata
