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
"""Unit tests for proposal schemas."""

import pytest
from pydantic import ValidationError

from consensus_engine.schemas.proposal import ExpandedProposal, IdeaInput


class TestIdeaInput:
    """Test suite for IdeaInput schema."""

    def test_idea_input_valid(self) -> None:
        """Test IdeaInput with valid data."""
        idea = IdeaInput(idea="Build a new API", extra_context="Use Python")

        assert idea.idea == "Build a new API"
        assert idea.extra_context == "Use Python"

    def test_idea_input_without_extra_context(self) -> None:
        """Test IdeaInput with only required field."""
        idea = IdeaInput(idea="Build a new API")

        assert idea.idea == "Build a new API"
        assert idea.extra_context is None

    def test_idea_input_empty_idea_rejected(self) -> None:
        """Test IdeaInput rejects empty idea string."""
        with pytest.raises(ValidationError) as exc_info:
            IdeaInput(idea="")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("idea",) for e in errors)

    def test_idea_input_missing_idea_rejected(self) -> None:
        """Test IdeaInput rejects missing idea field."""
        with pytest.raises(ValidationError) as exc_info:
            IdeaInput()  # type: ignore

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("idea",) for e in errors)

    def test_idea_input_json_serializable(self) -> None:
        """Test IdeaInput can be serialized to JSON."""
        idea = IdeaInput(idea="Build a new API", extra_context="Use Python")
        json_data = idea.model_dump_json()

        assert "Build a new API" in json_data
        assert "Use Python" in json_data


class TestExpandedProposal:
    """Test suite for ExpandedProposal schema."""

    def test_expanded_proposal_full(self) -> None:
        """Test ExpandedProposal with all fields."""
        proposal = ExpandedProposal(
            problem_statement="We need better APIs",
            proposed_solution="Build a RESTful API",
            assumptions=["Users know REST", "Python 3.11+"],
            scope_non_goals=["Mobile apps", "Desktop clients"],
            raw_expanded_proposal="Full detailed proposal text here",
        )

        assert proposal.problem_statement == "We need better APIs"
        assert proposal.proposed_solution == "Build a RESTful API"
        assert len(proposal.assumptions) == 2
        assert "Users know REST" in proposal.assumptions
        assert len(proposal.scope_non_goals) == 2
        assert "Mobile apps" in proposal.scope_non_goals
        assert proposal.raw_expanded_proposal == "Full detailed proposal text here"

    def test_expanded_proposal_minimal(self) -> None:
        """Test ExpandedProposal with only required fields."""
        proposal = ExpandedProposal(
            problem_statement="We need better APIs",
            proposed_solution="Build a RESTful API",
        )

        assert proposal.problem_statement == "We need better APIs"
        assert proposal.proposed_solution == "Build a RESTful API"
        assert proposal.assumptions == []
        assert proposal.scope_non_goals == []
        assert proposal.raw_expanded_proposal == ""

    def test_expanded_proposal_missing_required_fields(self) -> None:
        """Test ExpandedProposal rejects missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            ExpandedProposal()  # type: ignore

        errors = exc_info.value.errors()
        # Should have errors for both required fields
        assert any(e["loc"] == ("problem_statement",) for e in errors)
        assert any(e["loc"] == ("proposed_solution",) for e in errors)

    def test_expanded_proposal_empty_lists_accepted(self) -> None:
        """Test ExpandedProposal accepts empty lists for optional fields."""
        proposal = ExpandedProposal(
            problem_statement="Problem",
            proposed_solution="Solution",
            assumptions=[],
            scope_non_goals=[],
        )

        assert isinstance(proposal.assumptions, list)
        assert isinstance(proposal.scope_non_goals, list)
        assert len(proposal.assumptions) == 0
        assert len(proposal.scope_non_goals) == 0

    def test_expanded_proposal_json_serializable(self) -> None:
        """Test ExpandedProposal can be serialized to JSON."""
        proposal = ExpandedProposal(
            problem_statement="We need better APIs",
            proposed_solution="Build a RESTful API",
            assumptions=["Users know REST"],
            scope_non_goals=["Mobile apps"],
            raw_expanded_proposal="Full proposal",
        )

        json_data = proposal.model_dump_json()
        assert "We need better APIs" in json_data
        assert "Build a RESTful API" in json_data
        assert "Users know REST" in json_data
        assert "Mobile apps" in json_data

    def test_expanded_proposal_dict_conversion(self) -> None:
        """Test ExpandedProposal can be converted to dict."""
        proposal = ExpandedProposal(
            problem_statement="Problem",
            proposed_solution="Solution",
            assumptions=["Assumption 1"],
            scope_non_goals=["Non-goal 1"],
            raw_expanded_proposal="Notes",
        )

        data = proposal.model_dump()
        assert data["problem_statement"] == "Problem"
        assert data["proposed_solution"] == "Solution"
        assert data["assumptions"] == ["Assumption 1"]
        assert data["scope_non_goals"] == ["Non-goal 1"]
        assert data["raw_expanded_proposal"] == "Notes"
