"""Diff computation service for comparing proposal runs.

This module provides utilities for comparing two proposal runs and computing
structured diffs for proposal text, persona scores, and decision metrics.
"""

import difflib
from typing import Any

from consensus_engine.config.logging import get_logger
from consensus_engine.db.models import Run

logger = get_logger(__name__)


def compute_text_diff(old_text: str, new_text: str, context_lines: int = 3) -> list[str]:
    """Compute unified diff between two text strings.

    Args:
        old_text: Original text
        new_text: Modified text
        context_lines: Number of context lines to include (default: 3)

    Returns:
        List of diff lines in unified diff format
    """
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="original",
        tofile="modified",
        lineterm="",
        n=context_lines,
    )

    return list(diff)


def compute_proposal_changes(
    run1_proposal: dict[str, Any], run2_proposal: dict[str, Any]
) -> dict[str, Any]:
    """Compute changes between two proposal versions.

    Args:
        run1_proposal: First proposal JSON (from expanded_proposal_json)
        run2_proposal: Second proposal JSON (from expanded_proposal_json)

    Returns:
        Dictionary with per-section diffs and summary of changes
    """
    changes: dict[str, Any] = {}

    # Define sections to compare
    sections = [
        "title",
        "summary",
        "problem_statement",
        "proposed_solution",
        "assumptions",
        "scope_non_goals",
    ]

    for section in sections:
        old_value = run1_proposal.get(section)
        new_value = run2_proposal.get(section)

        # Handle None values
        if old_value is None and new_value is None:
            changes[section] = {"status": "unchanged", "diff": None}
            continue

        if old_value is None:
            changes[section] = {"status": "added", "new_value": new_value, "diff": None}
            continue

        if new_value is None:
            changes[section] = {"status": "removed", "old_value": old_value, "diff": None}
            continue

        # For list fields, convert to text for diffing
        if isinstance(old_value, list) and isinstance(new_value, list):
            old_text = "\n".join(str(item) for item in old_value)
            new_text = "\n".join(str(item) for item in new_value)
        else:
            old_text = str(old_value)
            new_text = str(new_value)

        # Check if changed
        if old_text == new_text:
            changes[section] = {"status": "unchanged", "diff": None}
        else:
            # Limit diff size for large sections
            max_diff_lines = 50
            diff_lines = compute_text_diff(old_text, new_text)

            if len(diff_lines) > max_diff_lines:
                diff_lines = diff_lines[:max_diff_lines] + [
                    f"... (truncated {len(diff_lines) - max_diff_lines} lines)"
                ]

            changes[section] = {
                "status": "modified",
                "diff": diff_lines,
                "old_length": len(old_text),
                "new_length": len(new_text),
            }

    return changes


def compute_persona_deltas(
    run1_reviews: list[dict[str, Any]], run2_reviews: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Compute persona score deltas between two runs.

    Args:
        run1_reviews: List of PersonaReview records from first run
        run2_reviews: List of PersonaReview records from second run

    Returns:
        List of persona deltas with old/new scores and blocking changes
    """
    deltas: list[dict[str, Any]] = []

    # Build maps by persona_id for easy lookup
    run1_map = {review["persona_id"]: review for review in run1_reviews}
    run2_map = {review["persona_id"]: review for review in run2_reviews}

    # Get all persona IDs from both runs
    all_persona_ids = set(run1_map.keys()) | set(run2_map.keys())

    for persona_id in sorted(all_persona_ids):
        review1 = run1_map.get(persona_id)
        review2 = run2_map.get(persona_id)

        delta: dict[str, Any] = {"persona_id": persona_id}

        if review1 and review2:
            # Both runs have this persona
            delta["persona_name"] = review2.get("persona_name", review1.get("persona_name"))
            delta["old_confidence"] = float(review1["confidence_score"])
            delta["new_confidence"] = float(review2["confidence_score"])
            delta["confidence_delta"] = delta["new_confidence"] - delta["old_confidence"]

            delta["old_blocking_issues"] = review1.get("blocking_issues_present", False)
            delta["new_blocking_issues"] = review2.get("blocking_issues_present", False)
            delta["blocking_changed"] = (
                delta["old_blocking_issues"] != delta["new_blocking_issues"]
            )

            delta["old_security_concerns"] = review1.get("security_concerns_present", False)
            delta["new_security_concerns"] = review2.get("security_concerns_present", False)
            delta["security_concerns_changed"] = (
                delta["old_security_concerns"] != delta["new_security_concerns"]
            )

        elif review1:
            # Only in first run (removed)
            delta["persona_name"] = review1.get("persona_name")
            delta["old_confidence"] = float(review1["confidence_score"])
            delta["new_confidence"] = None
            delta["confidence_delta"] = None
            delta["status"] = "removed_in_run2"

        else:
            # Only in second run (added)
            delta["persona_name"] = review2.get("persona_name")
            delta["old_confidence"] = None
            delta["new_confidence"] = float(review2["confidence_score"])
            delta["confidence_delta"] = None
            delta["status"] = "added_in_run2"

        deltas.append(delta)

    return deltas


def compute_decision_delta(run1: Run, run2: Run) -> dict[str, Any]:
    """Compute decision delta between two runs.

    Args:
        run1: First Run instance
        run2: Second Run instance

    Returns:
        Dictionary with decision comparison metrics
    """
    delta: dict[str, Any] = {}

    # Overall weighted confidence comparison
    conf1 = float(run1.overall_weighted_confidence) if run1.overall_weighted_confidence else None
    conf2 = float(run2.overall_weighted_confidence) if run2.overall_weighted_confidence else None

    delta["old_overall_weighted_confidence"] = conf1
    delta["new_overall_weighted_confidence"] = conf2

    if conf1 is not None and conf2 is not None:
        delta["confidence_delta"] = conf2 - conf1
    else:
        delta["confidence_delta"] = None

    # Decision label comparison
    delta["old_decision_label"] = run1.decision_label
    delta["new_decision_label"] = run2.decision_label
    delta["decision_changed"] = run1.decision_label != run2.decision_label

    return delta


def compute_run_diff(run1: Run, run2: Run) -> dict[str, Any]:
    """Compute comprehensive diff between two runs.

    Args:
        run1: First Run instance (with all relationships loaded)
        run2: Second Run instance (with all relationships loaded)

    Returns:
        Dictionary with structured diff containing:
        - metadata: Run IDs, relationship info
        - proposal_changes: Per-section diffs
        - persona_deltas: Score and blocking changes
        - decision_delta: Overall confidence and decision changes
    """
    logger.info(
        f"Computing diff between runs {run1.id} and {run2.id}",
        extra={"run1_id": str(run1.id), "run2_id": str(run2.id)},
    )

    # Detect parent/child relationship
    is_parent_child = False
    relationship = "unrelated"

    if run1.id == run2.parent_run_id:
        is_parent_child = True
        relationship = "run1_is_parent_of_run2"
    elif run2.id == run1.parent_run_id:
        is_parent_child = True
        relationship = "run2_is_parent_of_run1"

    # Build metadata
    metadata = {
        "run1_id": str(run1.id),
        "run2_id": str(run2.id),
        "run1_created_at": run1.created_at.isoformat(),
        "run2_created_at": run2.created_at.isoformat(),
        "is_parent_child": is_parent_child,
        "relationship": relationship,
    }

    # Compute proposal changes
    proposal_changes = None
    if (
        run1.proposal_version
        and run1.proposal_version.expanded_proposal_json
        and run2.proposal_version
        and run2.proposal_version.expanded_proposal_json
    ):
        proposal_changes = compute_proposal_changes(
            run1.proposal_version.expanded_proposal_json,
            run2.proposal_version.expanded_proposal_json,
        )
    elif (
        not run1.proposal_version
        or not run1.proposal_version.expanded_proposal_json
    ) and (not run2.proposal_version or not run2.proposal_version.expanded_proposal_json):
        proposal_changes = {"status": "both_missing"}
    elif not run1.proposal_version or not run1.proposal_version.expanded_proposal_json:
        proposal_changes = {"status": "run1_missing"}
    else:
        proposal_changes = {"status": "run2_missing"}

    # Compute persona deltas
    persona_deltas = []
    if run1.persona_reviews and run2.persona_reviews:
        # Convert to dictionaries for easier processing
        run1_reviews_data = [
            {
                "persona_id": r.persona_id,
                "persona_name": r.persona_name,
                "confidence_score": r.confidence_score,
                "blocking_issues_present": r.blocking_issues_present,
                "security_concerns_present": r.security_concerns_present,
            }
            for r in run1.persona_reviews
        ]

        run2_reviews_data = [
            {
                "persona_id": r.persona_id,
                "persona_name": r.persona_name,
                "confidence_score": r.confidence_score,
                "blocking_issues_present": r.blocking_issues_present,
                "security_concerns_present": r.security_concerns_present,
            }
            for r in run2.persona_reviews
        ]

        persona_deltas = compute_persona_deltas(run1_reviews_data, run2_reviews_data)

    # Compute decision delta
    decision_delta = compute_decision_delta(run1, run2)

    diff_result = {
        "metadata": metadata,
        "proposal_changes": proposal_changes,
        "persona_deltas": persona_deltas,
        "decision_delta": decision_delta,
    }

    logger.info(
        f"Diff computation complete for runs {run1.id} and {run2.id}",
        extra={
            "run1_id": str(run1.id),
            "run2_id": str(run2.id),
            "is_parent_child": is_parent_child,
            "proposal_sections_changed": sum(
                1
                for v in (proposal_changes or {}).values()
                if isinstance(v, dict) and v.get("status") == "modified"
            ),
            "personas_compared": len(persona_deltas),
        },
    )

    return diff_result
