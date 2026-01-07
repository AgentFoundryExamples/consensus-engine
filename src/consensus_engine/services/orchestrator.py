"""Orchestrator for multi-persona review process.

This module provides orchestration of proposal reviews across multiple personas,
implementing deterministic failure handling and metadata collection.
"""

import time
import uuid
from typing import Any

from consensus_engine.clients.openai_client import OpenAIClientWrapper
from consensus_engine.config.logging import get_logger
from consensus_engine.config.personas import get_all_personas
from consensus_engine.config.settings import Settings
from consensus_engine.schemas.proposal import ExpandedProposal
from consensus_engine.schemas.review import PersonaReview

logger = get_logger(__name__)

# System instruction for the review process (shared across all personas)
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


def review_with_all_personas(
    expanded_proposal: ExpandedProposal,
    settings: Settings,
) -> tuple[list[PersonaReview], dict[str, Any]]:
    """Review an expanded proposal with all configured personas.

    This function orchestrates reviews from all five personas defined in the
    configuration, implementing deterministic failure handling where any single
    persona failure causes the entire operation to fail.

    Args:
        expanded_proposal: Validated ExpandedProposal to review
        settings: Application settings for OpenAI client configuration

    Returns:
        Tuple of (list of PersonaReview instances in config order, orchestration metadata)

    Raises:
        LLMServiceError: For OpenAI API errors (any persona failure causes full failure)
        SchemaValidationError: If any response doesn't match expected schema
        ValidationError: If input validation fails
    """
    run_id = str(uuid.uuid4())
    start_time = time.time()

    logger.info(
        f"Starting multi-persona orchestration with run_id={run_id}",
        extra={"run_id": run_id, "step_name": "orchestrate"},
    )

    # Get all personas in config order
    all_personas = get_all_personas()
    persona_reviews: list[PersonaReview] = []

    # Initialize OpenAI client once for all personas
    client = OpenAIClientWrapper(settings)

    # Construct user prompt with proposal details (truncate for token limits)
    max_field_length = 2000
    max_list_item_length = 500
    max_list_items = 10

    problem_statement = expanded_proposal.problem_statement[:max_field_length]
    proposed_solution = expanded_proposal.proposed_solution[:max_field_length]
    assumptions = expanded_proposal.assumptions[:max_list_items]
    scope_non_goals = expanded_proposal.scope_non_goals[:max_list_items]

    user_prompt = f"""Review the following proposal:

**Problem Statement:**
{problem_statement}

**Proposed Solution:**
{proposed_solution}

**Assumptions:**
{chr(10).join(f"- {a[:max_list_item_length]}" for a in assumptions)}

**Scope/Non-Goals:**
{chr(10).join(f"- {s[:max_list_item_length]}" for s in scope_non_goals)}
"""

    # Add optional fields if present
    if expanded_proposal.title:
        user_prompt = f"**Title:** {expanded_proposal.title}\n\n" + user_prompt

    if expanded_proposal.summary:
        summary_truncated = expanded_proposal.summary[:max_field_length]
        user_prompt = f"**Summary:** {summary_truncated}\n\n" + user_prompt

    # Iterate through personas sequentially
    for persona_id, persona_config in all_personas.items():
        logger.info(
            f"Starting review with persona={persona_config.display_name}",
            extra={
                "run_id": run_id,
                "persona_id": persona_id,
                "persona_name": persona_config.display_name,
            },
        )

        # Construct developer instruction with persona context
        developer_instruction = (
            f"Review this proposal from the perspective of: {persona_config.display_name}\n\n"
            f"Persona instructions: {persona_config.developer_instructions}\n\n"
            "Provide your review using the PersonaReview schema with the following fields:\n"
            f"- persona_name: Your assigned persona name ({persona_config.display_name})\n"
            f"- persona_id: Your assigned persona ID ({persona_id})\n"
            "- confidence_score: Float between 0.0 and 1.0 indicating confidence in the proposal\n"
            "- strengths: List of identified strengths\n"
            "- concerns: List of Concern objects with text and is_blocking flag\n"
            "- recommendations: List of actionable recommendations\n"
            "- blocking_issues: List of BlockingIssue objects with optional "
            "security_critical flags (can be empty)\n"
            "- estimated_effort: Effort estimation as string or structured data\n"
            "- dependency_risks: List of identified dependency risks (can be empty)\n\n"
            "Be thorough, specific, and constructive in your feedback."
        )

        try:
            # Call OpenAI with structured output for this persona
            # Note: persona_config.temperature is 0.2 for all personas (PERSONA_TEMPERATURE)
            # This ensures deterministic, consistent reviews across all personas
            parsed_response, metadata = client.create_structured_response(
                system_instruction=REVIEW_SYSTEM_INSTRUCTION,
                user_prompt=user_prompt,
                response_model=PersonaReview,
                developer_instruction=developer_instruction,
                step_name="review",
                model_override=settings.review_model,
                temperature_override=persona_config.temperature,
            )

            # Attach internal metadata to the review
            parsed_response.internal_metadata = {
                "model": metadata.get("model"),
                "latency": metadata.get("latency"),
                "request_id": metadata.get("request_id"),
                "timestamp": time.time(),
            }

            persona_reviews.append(parsed_response)

            logger.info(
                f"Completed review with persona={persona_config.display_name}",
                extra={
                    "run_id": run_id,
                    "persona_id": persona_id,
                    "persona_name": persona_config.display_name,
                    "confidence_score": parsed_response.confidence_score,
                    "blocking_issues_count": len(parsed_response.blocking_issues),
                    "request_id": metadata.get("request_id"),
                },
            )

        except Exception as e:
            # Deterministic failure: any persona failure causes full orchestration failure
            elapsed_time = time.time() - start_time
            logger.error(
                f"Orchestration failed at persona={persona_config.display_name}",
                extra={
                    "run_id": run_id,
                    "persona_id": persona_id,
                    "persona_name": persona_config.display_name,
                    "error": str(e),
                    "elapsed_time": f"{elapsed_time:.2f}s",
                },
                exc_info=True,
            )
            # Re-raise the exception to propagate failure
            raise

    # Calculate total elapsed time
    elapsed_time = time.time() - start_time

    # Build orchestration metadata
    orchestration_metadata = {
        "run_id": run_id,
        "step_name": "orchestrate",
        "elapsed_time": elapsed_time,
        "persona_count": len(persona_reviews),
        "status": "success",
    }

    logger.info(
        f"Multi-persona orchestration completed successfully with run_id={run_id}",
        extra={
            "run_id": run_id,
            "persona_count": len(persona_reviews),
            "elapsed_time": f"{elapsed_time:.2f}s",
            "status": "success",
        },
    )

    return persona_reviews, orchestration_metadata
