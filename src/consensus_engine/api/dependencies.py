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
from consensus_engine.services.expand import expand_idea


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
