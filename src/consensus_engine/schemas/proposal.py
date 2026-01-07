"""Pydantic models for proposal schemas.

This module defines the data models for proposal expansion, including
input payloads and structured output from the LLM service.
"""

from pydantic import BaseModel, Field


class IdeaInput(BaseModel):
    """Input payload for expanding an idea into a full proposal.

    Attributes:
        idea: The core idea or problem to expand into a detailed proposal
        extra_context: Optional additional context or constraints to consider
    """

    idea: str = Field(
        ...,
        min_length=1,
        description="The core idea or problem to expand into a detailed proposal",
    )
    extra_context: str | None = Field(
        default=None,
        description="Optional additional context or constraints to consider",
    )


class ExpandedProposal(BaseModel):
    """Structured output from the LLM expansion service.

    This model defines the expected structure when using OpenAI's Structured Outputs
    to ensure validated JSON-only responses.

    Attributes:
        problem_statement: Clear articulation of the problem to be solved
        proposed_solution: Detailed description of the proposed solution approach
        assumptions: List of underlying assumptions made in the proposal
        scope_non_goals: List of what is explicitly out of scope or non-goals
        raw_expanded_proposal: The complete expanded proposal text or additional notes
    """

    problem_statement: str = Field(
        ...,
        description="Clear articulation of the problem to be solved",
    )
    proposed_solution: str = Field(
        ...,
        description="Detailed description of the proposed solution approach",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="List of underlying assumptions made in the proposal",
    )
    scope_non_goals: list[str] = Field(
        default_factory=list,
        description="List of what is explicitly out of scope or non-goals",
    )
    raw_expanded_proposal: str = Field(
        default="",
        description=(
            "Optional field for storing the complete expanded proposal text in narrative form "
            "or additional notes that don't fit into the structured fields above. "
            "This field allows the LLM to provide supplementary information beyond the "
            "structured problem_statement, proposed_solution, assumptions, and scope_non_goals."
        ),
    )
