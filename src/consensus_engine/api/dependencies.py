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
"""API dependencies for dependency injection.

This module provides FastAPI dependencies for injecting services,
settings, and other shared resources into route handlers.
"""

from collections.abc import Callable
from typing import Any

from fastapi import Depends

from consensus_engine.config import Settings, get_settings
from consensus_engine.schemas.proposal import ExpandedProposal, IdeaInput
from consensus_engine.schemas.review import PersonaReview
from consensus_engine.services.expand import expand_idea
from consensus_engine.services.review import review_proposal


def get_expand_idea_service() -> (
    Callable[[IdeaInput, Settings], tuple[ExpandedProposal, dict[str, Any]]]
):
    """Get the expand_idea service function.

    This dependency provides the expand_idea service function for
    injection into route handlers.

    Returns:
        The expand_idea service function
    """
    return expand_idea


def get_expand_service_with_settings(
    settings: Settings = Depends(get_settings),
) -> Callable[[IdeaInput], tuple[ExpandedProposal, dict[str, Any]]]:
    """Get a partially-applied expand_idea service with settings injected.

    This dependency provides a version of expand_idea that already has
    settings injected, so routes only need to pass the IdeaInput.

    Args:
        settings: Application settings injected via dependency

    Returns:
        Partially-applied expand_idea function
    """

    def expand_with_settings(idea_input: IdeaInput) -> tuple[ExpandedProposal, dict[str, Any]]:
        return expand_idea(idea_input, settings)

    return expand_with_settings


def get_review_proposal_service() -> (
    Callable[
        [ExpandedProposal, Settings, str | None, str | None],
        tuple[PersonaReview, dict[str, Any]],
    ]
):
    """Get the review_proposal service function.

    This dependency provides the review_proposal service function for
    injection into route handlers.

    Returns:
        The review_proposal service function
    """
    return review_proposal


def get_review_service_with_settings(
    settings: Settings = Depends(get_settings),
) -> Callable[[ExpandedProposal, str | None, str | None], tuple[PersonaReview, dict[str, Any]]]:
    """Get a partially-applied review_proposal service with settings injected.

    This dependency provides a version of review_proposal that already has
    settings injected, so routes only need to pass the proposal and optional persona params.

    Args:
        settings: Application settings injected via dependency

    Returns:
        Partially-applied review_proposal function
    """

    def review_with_settings(
        expanded_proposal: ExpandedProposal,
        persona_name: str | None = None,
        persona_instructions: str | None = None,
    ) -> tuple[PersonaReview, dict[str, Any]]:
        return review_proposal(expanded_proposal, settings, persona_name, persona_instructions)

    return review_with_settings
