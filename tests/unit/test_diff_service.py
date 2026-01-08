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
"""Unit tests for diff service.

These tests validate the diff computation logic without database interactions.
"""

import pytest
from datetime import UTC, datetime
from unittest.mock import MagicMock

from consensus_engine.services.diff import (
    compute_text_diff,
    compute_proposal_changes,
    compute_persona_deltas,
    compute_decision_delta,
    compute_run_diff,
)


class TestTextDiff:
    """Test suite for compute_text_diff function."""

    def test_identical_text(self):
        """Test diff of identical text."""
        old = "This is a test.\nWith multiple lines."
        new = "This is a test.\nWith multiple lines."
        
        diff = compute_text_diff(old, new)
        assert len(diff) == 0, "Identical text should produce no diff lines"

    def test_simple_change(self):
        """Test diff with simple change."""
        old = "This is a test.\nWith multiple lines."
        new = "This is a test.\nWith modified lines."
        
        diff = compute_text_diff(old, new)
        assert len(diff) > 0, "Changed text should produce diff lines"
        assert any("-With multiple lines." in line for line in diff)
        assert any("+With modified lines." in line for line in diff)

    def test_addition(self):
        """Test diff with added lines."""
        old = "Line 1"
        new = "Line 1\nLine 2"
        
        diff = compute_text_diff(old, new)
        assert len(diff) > 0, "Added lines should produce diff"
        assert any("+Line 2" in line for line in diff)

    def test_removal(self):
        """Test diff with removed lines."""
        old = "Line 1\nLine 2"
        new = "Line 1"
        
        diff = compute_text_diff(old, new)
        assert len(diff) > 0, "Removed lines should produce diff"
        assert any("-Line 2" in line for line in diff)


class TestProposalChanges:
    """Test suite for compute_proposal_changes function."""

    def test_identical_proposals(self):
        """Test diff of identical proposals."""
        proposal = {
            "title": "Test Proposal",
            "summary": "Test summary",
            "problem_statement": "Problem",
            "proposed_solution": "Solution",
            "assumptions": ["Assumption 1"],
            "scope_non_goals": ["Non-goal 1"],
        }
        
        changes = compute_proposal_changes(proposal, proposal)
        
        # All sections should be unchanged
        for section in ["title", "summary", "problem_statement", "proposed_solution", 
                        "assumptions", "scope_non_goals"]:
            assert changes[section]["status"] == "unchanged"
            assert changes[section]["diff"] is None

    def test_modified_text_section(self):
        """Test diff with modified text section."""
        proposal1 = {
            "problem_statement": "Original problem statement",
            "proposed_solution": "Solution",
            "assumptions": [],
            "scope_non_goals": [],
        }
        
        proposal2 = {
            "problem_statement": "Modified problem statement",
            "proposed_solution": "Solution",
            "assumptions": [],
            "scope_non_goals": [],
        }
        
        changes = compute_proposal_changes(proposal1, proposal2)
        
        assert changes["problem_statement"]["status"] == "modified"
        assert changes["problem_statement"]["diff"] is not None
        assert len(changes["problem_statement"]["diff"]) > 0
        assert changes["proposed_solution"]["status"] == "unchanged"

    def test_added_section(self):
        """Test diff with added section."""
        proposal1 = {
            "problem_statement": "Problem",
            "proposed_solution": "Solution",
            "assumptions": [],
            "scope_non_goals": [],
        }
        
        proposal2 = {
            "title": "New Title",
            "problem_statement": "Problem",
            "proposed_solution": "Solution",
            "assumptions": [],
            "scope_non_goals": [],
        }
        
        changes = compute_proposal_changes(proposal1, proposal2)
        
        assert changes["title"]["status"] == "added"
        assert changes["title"]["new_value"] == "New Title"

    def test_removed_section(self):
        """Test diff with removed section."""
        proposal1 = {
            "title": "Original Title",
            "problem_statement": "Problem",
            "proposed_solution": "Solution",
            "assumptions": [],
            "scope_non_goals": [],
        }
        
        proposal2 = {
            "problem_statement": "Problem",
            "proposed_solution": "Solution",
            "assumptions": [],
            "scope_non_goals": [],
        }
        
        changes = compute_proposal_changes(proposal1, proposal2)
        
        assert changes["title"]["status"] == "removed"
        assert changes["title"]["old_value"] == "Original Title"

    def test_modified_list_section(self):
        """Test diff with modified list section."""
        proposal1 = {
            "problem_statement": "Problem",
            "proposed_solution": "Solution",
            "assumptions": ["Assumption 1", "Assumption 2"],
            "scope_non_goals": [],
        }
        
        proposal2 = {
            "problem_statement": "Problem",
            "proposed_solution": "Solution",
            "assumptions": ["Assumption 1", "Assumption 3"],
            "scope_non_goals": [],
        }
        
        changes = compute_proposal_changes(proposal1, proposal2)
        
        assert changes["assumptions"]["status"] == "modified"
        assert changes["assumptions"]["diff"] is not None

    def test_large_diff_truncation(self):
        """Test that large diffs are truncated."""
        # Create large proposals
        old_lines = [f"Line {i}" for i in range(100)]
        new_lines = [f"Modified line {i}" for i in range(100)]
        
        proposal1 = {
            "problem_statement": "\n".join(old_lines),
            "proposed_solution": "Solution",
            "assumptions": [],
            "scope_non_goals": [],
        }
        
        proposal2 = {
            "problem_statement": "\n".join(new_lines),
            "proposed_solution": "Solution",
            "assumptions": [],
            "scope_non_goals": [],
        }
        
        changes = compute_proposal_changes(proposal1, proposal2)
        
        # Diff should be truncated
        assert len(changes["problem_statement"]["diff"]) <= 51  # 50 lines + truncation message


class TestPersonaDeltas:
    """Test suite for compute_persona_deltas function."""

    def test_identical_reviews(self):
        """Test deltas with identical reviews."""
        reviews = [
            {
                "persona_id": "architect",
                "persona_name": "Architect",
                "confidence_score": 0.85,
                "blocking_issues_present": False,
                "security_concerns_present": False,
            }
        ]
        
        deltas = compute_persona_deltas(reviews, reviews)
        
        assert len(deltas) == 1
        assert deltas[0]["persona_id"] == "architect"
        assert deltas[0]["old_confidence"] == 0.85
        assert deltas[0]["new_confidence"] == 0.85
        assert deltas[0]["confidence_delta"] == 0.0
        assert deltas[0]["blocking_changed"] is False

    def test_confidence_increase(self):
        """Test deltas with confidence increase."""
        reviews1 = [
            {
                "persona_id": "architect",
                "persona_name": "Architect",
                "confidence_score": 0.70,
                "blocking_issues_present": False,
                "security_concerns_present": False,
            }
        ]
        
        reviews2 = [
            {
                "persona_id": "architect",
                "persona_name": "Architect",
                "confidence_score": 0.90,
                "blocking_issues_present": False,
                "security_concerns_present": False,
            }
        ]
        
        deltas = compute_persona_deltas(reviews1, reviews2)
        
        assert len(deltas) == 1
        assert abs(deltas[0]["confidence_delta"] - 0.20) < 0.001

    def test_blocking_issues_changed(self):
        """Test deltas with blocking issues change."""
        reviews1 = [
            {
                "persona_id": "security_guardian",
                "persona_name": "SecurityGuardian",
                "confidence_score": 0.60,
                "blocking_issues_present": True,
                "security_concerns_present": True,
            }
        ]
        
        reviews2 = [
            {
                "persona_id": "security_guardian",
                "persona_name": "SecurityGuardian",
                "confidence_score": 0.90,
                "blocking_issues_present": False,
                "security_concerns_present": False,
            }
        ]
        
        deltas = compute_persona_deltas(reviews1, reviews2)
        
        assert len(deltas) == 1
        assert deltas[0]["blocking_changed"] is True
        assert deltas[0]["security_concerns_changed"] is True
        assert deltas[0]["old_blocking_issues"] is True
        assert deltas[0]["new_blocking_issues"] is False

    def test_persona_added(self):
        """Test deltas when persona is added in second run."""
        reviews1 = []
        
        reviews2 = [
            {
                "persona_id": "new_persona",
                "persona_name": "NewPersona",
                "confidence_score": 0.80,
                "blocking_issues_present": False,
                "security_concerns_present": False,
            }
        ]
        
        deltas = compute_persona_deltas(reviews1, reviews2)
        
        assert len(deltas) == 1
        assert deltas[0]["status"] == "added_in_run2"
        assert deltas[0]["old_confidence"] is None
        assert deltas[0]["new_confidence"] == 0.80

    def test_persona_removed(self):
        """Test deltas when persona is removed in second run."""
        reviews1 = [
            {
                "persona_id": "removed_persona",
                "persona_name": "RemovedPersona",
                "confidence_score": 0.75,
                "blocking_issues_present": False,
                "security_concerns_present": False,
            }
        ]
        
        reviews2 = []
        
        deltas = compute_persona_deltas(reviews1, reviews2)
        
        assert len(deltas) == 1
        assert deltas[0]["status"] == "removed_in_run2"
        assert deltas[0]["old_confidence"] == 0.75
        assert deltas[0]["new_confidence"] is None

    def test_multiple_personas(self):
        """Test deltas with multiple personas."""
        reviews1 = [
            {
                "persona_id": "architect",
                "persona_name": "Architect",
                "confidence_score": 0.75,
                "blocking_issues_present": False,
                "security_concerns_present": False,
            },
            {
                "persona_id": "critic",
                "persona_name": "Critic",
                "confidence_score": 0.60,
                "blocking_issues_present": True,
                "security_concerns_present": False,
            },
        ]
        
        reviews2 = [
            {
                "persona_id": "architect",
                "persona_name": "Architect",
                "confidence_score": 0.85,
                "blocking_issues_present": False,
                "security_concerns_present": False,
            },
            {
                "persona_id": "critic",
                "persona_name": "Critic",
                "confidence_score": 0.80,
                "blocking_issues_present": False,
                "security_concerns_present": False,
            },
        ]
        
        deltas = compute_persona_deltas(reviews1, reviews2)
        
        assert len(deltas) == 2
        
        # Check sorted by persona_id
        assert deltas[0]["persona_id"] == "architect"
        assert deltas[1]["persona_id"] == "critic"
        
        # Check confidence changes
        assert abs(deltas[0]["confidence_delta"] - 0.10) < 0.001
        assert abs(deltas[1]["confidence_delta"] - 0.20) < 0.001
        assert deltas[1]["blocking_changed"] is True


class TestDecisionDelta:
    """Test suite for compute_decision_delta function."""

    def test_both_runs_complete(self):
        """Test decision delta with both runs complete."""
        run1 = MagicMock()
        run1.overall_weighted_confidence = 0.72
        run1.decision_label = "revise"
        
        run2 = MagicMock()
        run2.overall_weighted_confidence = 0.84
        run2.decision_label = "approve"
        
        delta = compute_decision_delta(run1, run2)
        
        assert delta["old_overall_weighted_confidence"] == 0.72
        assert delta["new_overall_weighted_confidence"] == 0.84
        assert delta["confidence_delta"] == 0.12
        assert delta["old_decision_label"] == "revise"
        assert delta["new_decision_label"] == "approve"
        assert delta["decision_changed"] is True

    def test_decision_unchanged(self):
        """Test decision delta when decision unchanged."""
        run1 = MagicMock()
        run1.overall_weighted_confidence = 0.85
        run1.decision_label = "approve"
        
        run2 = MagicMock()
        run2.overall_weighted_confidence = 0.87
        run2.decision_label = "approve"
        
        delta = compute_decision_delta(run1, run2)
        
        assert abs(delta["confidence_delta"] - 0.02) < 0.001
        assert delta["decision_changed"] is False

    def test_null_confidence(self):
        """Test decision delta with null confidence."""
        run1 = MagicMock()
        run1.overall_weighted_confidence = None
        run1.decision_label = None
        
        run2 = MagicMock()
        run2.overall_weighted_confidence = 0.85
        run2.decision_label = "approve"
        
        delta = compute_decision_delta(run1, run2)
        
        assert delta["old_overall_weighted_confidence"] is None
        assert delta["new_overall_weighted_confidence"] == 0.85
        assert delta["confidence_delta"] is None


class TestComputeRunDiff:
    """Test suite for compute_run_diff function."""

    def test_parent_child_relationship_detection(self):
        """Test parent/child relationship detection."""
        # Create mock runs with parent/child relationship
        run1 = MagicMock()
        run1.id = "parent-uuid"
        run1.parent_run_id = None
        run1.created_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        run1.overall_weighted_confidence = 0.75
        run1.decision_label = "revise"
        run1.proposal_version = None
        run1.persona_reviews = []
        
        run2 = MagicMock()
        run2.id = "child-uuid"
        run2.parent_run_id = "parent-uuid"
        run2.created_at = datetime(2026, 1, 1, 13, 0, 0, tzinfo=UTC)
        run2.overall_weighted_confidence = 0.85
        run2.decision_label = "approve"
        run2.proposal_version = None
        run2.persona_reviews = []
        
        diff = compute_run_diff(run1, run2)
        
        assert diff["metadata"]["is_parent_child"] is True
        assert diff["metadata"]["relationship"] == "run1_is_parent_of_run2"

    def test_unrelated_runs(self):
        """Test unrelated runs."""
        # Create mock runs with no relationship
        run1 = MagicMock()
        run1.id = "run1-uuid"
        run1.parent_run_id = None
        run1.created_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        run1.overall_weighted_confidence = 0.75
        run1.decision_label = "revise"
        run1.proposal_version = None
        run1.persona_reviews = []
        
        run2 = MagicMock()
        run2.id = "run2-uuid"
        run2.parent_run_id = None
        run2.created_at = datetime(2026, 1, 2, 12, 0, 0, tzinfo=UTC)
        run2.overall_weighted_confidence = 0.85
        run2.decision_label = "approve"
        run2.proposal_version = None
        run2.persona_reviews = []
        
        diff = compute_run_diff(run1, run2)
        
        assert diff["metadata"]["is_parent_child"] is False
        assert diff["metadata"]["relationship"] == "unrelated"

    def test_complete_diff_structure(self):
        """Test that diff has all required keys."""
        run1 = MagicMock()
        run1.id = "run1-uuid"
        run1.parent_run_id = None
        run1.created_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        run1.overall_weighted_confidence = 0.75
        run1.decision_label = "revise"
        run1.proposal_version = None
        run1.persona_reviews = []
        
        run2 = MagicMock()
        run2.id = "run2-uuid"
        run2.parent_run_id = None
        run2.created_at = datetime(2026, 1, 2, 12, 0, 0, tzinfo=UTC)
        run2.overall_weighted_confidence = 0.85
        run2.decision_label = "approve"
        run2.proposal_version = None
        run2.persona_reviews = []
        
        diff = compute_run_diff(run1, run2)
        
        # Check all required top-level keys
        assert "metadata" in diff
        assert "proposal_changes" in diff
        assert "persona_deltas" in diff
        assert "decision_delta" in diff
        
        # Check metadata keys
        assert "run1_id" in diff["metadata"]
        assert "run2_id" in diff["metadata"]
        assert "is_parent_child" in diff["metadata"]
        assert "relationship" in diff["metadata"]
