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

# Persona ID for SecurityGuardian (used for veto logic)
SECURITY_GUARDIAN_PERSONA_ID = "security_guardian"

# Confidence threshold for re-running personas in revisions (0.70)
RERUN_CONFIDENCE_THRESHOLD = 0.70


def determine_personas_to_rerun(
    parent_persona_reviews: list[tuple[str, dict[str, Any], bool]],
) -> list[str]:
    """Determine which personas should be re-run for a revision.

    Re-run criteria:
    1. Confidence score < 0.70 (RERUN_CONFIDENCE_THRESHOLD)
    2. blocking_issues_present is True
    3. Persona is SecurityGuardian AND security_concerns_present is True

    Args:
        parent_persona_reviews: List of (persona_id, review_json, security_concerns_present)
            tuples from parent

    Returns:
        List of persona IDs that should be re-executed
    """
    personas_to_rerun: list[str] = []

    logger.info(
        f"Determining personas to rerun from {len(parent_persona_reviews)} parent reviews",
        extra={"parent_review_count": len(parent_persona_reviews)},
    )

    for persona_id, review_json, security_concerns_present in parent_persona_reviews:
        should_rerun = False
        reason = ""

        # Extract relevant fields from review_json
        confidence_score = review_json.get("confidence_score", 1.0)
        blocking_issues = review_json.get("blocking_issues", [])
        blocking_issues_present = len(blocking_issues) > 0

        # Check criterion 1: Low confidence
        if confidence_score < RERUN_CONFIDENCE_THRESHOLD:
            should_rerun = True
            reason = f"Low confidence ({confidence_score:.2f} < {RERUN_CONFIDENCE_THRESHOLD})"

        # Check criterion 2: Blocking issues present
        if blocking_issues_present:
            should_rerun = True
            reason = (
                f"Blocking issues present ({len(blocking_issues)} issues)"
                if not reason
                else f"{reason}; Blocking issues present"
            )

        # Check criterion 3: SecurityGuardian with security concerns
        # Use the security_concerns_present flag from the DB for consistency
        if persona_id == SECURITY_GUARDIAN_PERSONA_ID and security_concerns_present:
            should_rerun = True
            reason = (
                "Security Guardian with security_critical issues"
                if not reason
                else f"{reason}; Security concerns present"
            )

        if should_rerun:
            personas_to_rerun.append(persona_id)
            logger.info(
                f"Persona '{persona_id}' marked for re-run: {reason}",
                extra={
                    "persona_id": persona_id,
                    "confidence_score": confidence_score,
                    "blocking_issues_count": len(blocking_issues),
                    "reason": reason,
                },
            )
        else:
            logger.info(
                f"Persona '{persona_id}' will reuse parent review "
                f"(confidence: {confidence_score:.2f}, no blocking issues)",
                extra={
                    "persona_id": persona_id,
                    "confidence_score": confidence_score,
                    "will_reuse": True,
                },
            )

    logger.info(
        (
            f"Determined {len(personas_to_rerun)} personas to rerun "
            f"out of {len(parent_persona_reviews)}"
        ),
        extra={
            "rerun_count": len(personas_to_rerun),
            "total_count": len(parent_persona_reviews),
            "personas_to_rerun": personas_to_rerun,
        },
    )

    return personas_to_rerun


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
    # Truncation limits are chosen to:
    # - Stay well within typical LLM context windows (8k-128k tokens)
    # - Balance comprehensive context vs. token efficiency
    # - Prevent excessive API costs from overly long proposals
    # Note: Truncation is applied uniformly to all personas for consistency
    # The proposal content is user-provided and passed to the LLM as-is within
    # these limits. The OpenAI API handles any necessary escaping/sanitization.
    max_field_length = 2000  # Max chars for problem_statement, proposed_solution fields
    max_list_item_length = 500  # Max chars per assumption or non-goal item
    max_list_items = 10  # Max number of assumptions or non-goals to include

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


def review_with_selective_personas(
    expanded_proposal: ExpandedProposal,
    parent_persona_reviews: list[tuple[str, dict[str, Any], bool]],
    personas_to_rerun: list[str],
    settings: Settings,
) -> tuple[list[PersonaReview], dict[str, Any]]:
    """Review an expanded proposal with selective persona re-runs.

    This function orchestrates reviews for a revision run, re-running only selected
    personas while reusing cached reviews from the parent run for others.

    Args:
        expanded_proposal: Validated ExpandedProposal to review
        parent_persona_reviews: List of (persona_id, review_json, security_concerns_present)
            tuples from parent
        personas_to_rerun: List of persona IDs to re-execute
        settings: Application settings for OpenAI client configuration

    Returns:
        Tuple of (list of PersonaReview instances, orchestration metadata)

    Raises:
        LLMServiceError: For OpenAI API errors (any persona failure causes full failure)
        SchemaValidationError: If any response doesn't match expected schema
        ValidationError: If input validation fails
    """
    run_id = str(uuid.uuid4())
    start_time = time.time()

    logger.info(
        f"Starting selective persona orchestration with run_id={run_id}",
        extra={
            "run_id": run_id,
            "step_name": "orchestrate_selective",
            "personas_to_rerun": personas_to_rerun,
            "total_personas": len(parent_persona_reviews),
        },
    )

    # Get all personas in config order
    all_personas = get_all_personas()
    persona_reviews: list[PersonaReview] = []

    # Initialize OpenAI client once for all personas
    client = OpenAIClientWrapper(settings)

    # Build parent reviews lookup
    parent_reviews_map: dict[str, dict[str, Any]] = {}
    for persona_id, review_json, _ in parent_persona_reviews:
        parent_reviews_map[persona_id] = review_json

    # Construct user prompt (same as in review_with_all_personas)
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

    # Process each persona: rerun or reuse
    rerun_count = 0
    reused_count = 0

    for persona_id, persona_config in all_personas.items():
        if persona_id in personas_to_rerun:
            # Re-run this persona
            logger.info(
                f"Re-running persona={persona_config.display_name}",
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
                "- confidence_score: Float between 0.0 and 1.0 indicating confidence\n"
                "- strengths: List of identified strengths\n"
                "- concerns: List of Concern objects with text and is_blocking flag\n"
                "- recommendations: List of actionable recommendations\n"
                "- blocking_issues: List of BlockingIssue objects (can be empty)\n"
                "- estimated_effort: Effort estimation as string or structured data\n"
                "- dependency_risks: List of identified dependency risks (can be empty)\n\n"
                "Be thorough, specific, and constructive in your feedback."
            )

            try:
                # Call OpenAI with structured output for this persona
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
                    "reused": False,
                }

                persona_reviews.append(parsed_response)
                rerun_count += 1

                logger.info(
                    f"Completed re-run with persona={persona_config.display_name}",
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
                    f"Selective orchestration failed at persona={persona_config.display_name}",
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

        else:
            # Reuse parent review
            if persona_id not in parent_reviews_map:
                # Log error but don't fail the entire run
                logger.error(
                    f"Persona '{persona_id}' not found in parent reviews, skipping reuse",
                    extra={
                        "run_id": run_id,
                        "persona_id": persona_id,
                        "persona_name": persona_config.display_name,
                    },
                )
                continue

            logger.info(
                f"Reusing parent review for persona={persona_config.display_name}",
                extra={
                    "run_id": run_id,
                    "persona_id": persona_id,
                    "persona_name": persona_config.display_name,
                },
            )

            # Reconstruct PersonaReview from parent JSON with error handling
            parent_review_json = parent_reviews_map[persona_id]
            try:
                parsed_response = PersonaReview(**parent_review_json)
            except Exception as e:
                # Log validation error and skip this persona
                logger.error(
                    f"Failed to reconstruct parent review for persona {persona_id}, skipping",
                    extra={
                        "run_id": run_id,
                        "persona_id": persona_id,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                continue

            # Mark as reused in metadata
            parsed_response.internal_metadata = {
                "reused": True,
                "timestamp": time.time(),
            }

            persona_reviews.append(parsed_response)
            reused_count += 1

    # Calculate total elapsed time
    elapsed_time = time.time() - start_time

    # Build orchestration metadata
    orchestration_metadata = {
        "run_id": run_id,
        "step_name": "orchestrate_selective",
        "elapsed_time": elapsed_time,
        "persona_count": len(persona_reviews),
        "rerun_count": rerun_count,
        "reused_count": reused_count,
        "personas_rerun": personas_to_rerun,
        "status": "success",
    }

    logger.info(
        f"Selective persona orchestration completed successfully with run_id={run_id}",
        extra={
            "run_id": run_id,
            "persona_count": len(persona_reviews),
            "rerun_count": rerun_count,
            "reused_count": reused_count,
            "elapsed_time": f"{elapsed_time:.2f}s",
            "status": "success",
        },
    )

    return persona_reviews, orchestration_metadata
