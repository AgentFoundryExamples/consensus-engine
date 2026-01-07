"""Aggregation utilities for multi-persona consensus building.

This module provides deterministic aggregation logic that computes weighted
confidence scores, applies decision thresholds, enforces veto rules, and
generates minority reports.
"""

from consensus_engine.config.logging import get_logger
from consensus_engine.config.personas import (
    APPROVE_THRESHOLD,
    REVISE_THRESHOLD,
    get_persona_weights,
)
from consensus_engine.schemas.review import (
    DecisionAggregation,
    DecisionEnum,
    DetailedScoreBreakdown,
    MinorityReport,
    PersonaReview,
)

logger = get_logger(__name__)


def aggregate_persona_reviews(
    persona_reviews: list[PersonaReview],
) -> DecisionAggregation:
    """Aggregate multiple persona reviews into a single decision.

    This function implements the deterministic aggregation algorithm that:
    1. Computes weighted confidence using configured persona weights
    2. Applies decision thresholds (approve ≥0.80, revise ≥0.60, reject <0.60)
    3. Enforces SecurityGuardian veto rules for security_critical blocking issues
    4. Generates minority reports for dissenting personas
    5. Clamps weighted averages to [0.0, 1.0] range

    Args:
        persona_reviews: List of PersonaReview instances from all personas

    Returns:
        DecisionAggregation instance with decision, confidence, and breakdown

    Raises:
        ValueError: If persona_reviews is empty or contains invalid data
    """
    if not persona_reviews:
        raise ValueError("Cannot aggregate empty list of persona reviews")

    logger.info(
        f"Starting aggregation of {len(persona_reviews)} persona reviews",
        extra={"persona_count": len(persona_reviews)},
    )

    # Get persona weights from configuration
    persona_weights = get_persona_weights()

    # Build dictionaries for aggregation
    weights: dict[str, float] = {}
    individual_scores: dict[str, float] = {}
    weighted_contributions: dict[str, float] = {}

    # Collect scores and compute weighted contributions
    for review in persona_reviews:
        persona_id = review.persona_id
        confidence = review.confidence_score

        # Get weight for this persona (default to 0 if not in config)
        weight = persona_weights.get(persona_id, 0.0)

        weights[persona_id] = weight
        individual_scores[persona_id] = confidence
        weighted_contributions[persona_id] = weight * confidence

    # Calculate weighted confidence (sum of weighted contributions)
    weighted_confidence = sum(weighted_contributions.values())

    # Clamp to [0.0, 1.0] range to handle floating point drift
    weighted_confidence = max(0.0, min(1.0, weighted_confidence))

    logger.debug(
        f"Computed weighted confidence: {weighted_confidence:.4f}",
        extra={"weighted_confidence": weighted_confidence},
    )

    # Check for SecurityGuardian veto
    has_security_critical = any(
        issue.security_critical is True
        for review in persona_reviews
        if review.persona_id == "security_guardian"
        for issue in review.blocking_issues
    )

    # Determine base decision from thresholds
    if has_security_critical:
        # SecurityGuardian veto: force to at least REVISE
        if weighted_confidence >= APPROVE_THRESHOLD:
            decision = DecisionEnum.REVISE
            logger.info(
                "SecurityGuardian veto applied: changing APPROVE to REVISE",
                extra={"veto_reason": "security_critical blocking issue"},
            )
        else:
            # Already below approve threshold, use normal logic
            decision = (
                DecisionEnum.REVISE
                if weighted_confidence >= REVISE_THRESHOLD
                else DecisionEnum.REJECT
            )
    else:
        # Normal decision thresholds
        if weighted_confidence >= APPROVE_THRESHOLD:
            decision = DecisionEnum.APPROVE
        elif weighted_confidence >= REVISE_THRESHOLD:
            decision = DecisionEnum.REVISE
        else:
            decision = DecisionEnum.REJECT

    # Build detailed score breakdown
    formula = (
        f"weighted_confidence = sum(weight_i * score_i for each persona i) = "
        f"{weighted_confidence:.4f}"
    )

    detailed_breakdown = DetailedScoreBreakdown(
        weights=weights,
        individual_scores=individual_scores,
        weighted_contributions=weighted_contributions,
        formula=formula,
    )

    # Generate minority reports
    minority_reports = _generate_minority_reports(
        persona_reviews=persona_reviews,
        final_decision=decision,
        weighted_confidence=weighted_confidence,
    )

    # Build DecisionAggregation
    aggregation = DecisionAggregation(
        overall_weighted_confidence=weighted_confidence,
        weighted_confidence=weighted_confidence,
        decision=decision,
        detailed_score_breakdown=detailed_breakdown,
        minority_reports=minority_reports if minority_reports else None,
    )

    logger.info(
        f"Aggregation completed: decision={decision.value}, confidence={weighted_confidence:.4f}",
        extra={
            "decision": decision.value,
            "weighted_confidence": weighted_confidence,
            "minority_report_count": len(minority_reports) if minority_reports else 0,
        },
    )

    return aggregation


def _generate_minority_reports(
    persona_reviews: list[PersonaReview],
    final_decision: DecisionEnum,
    weighted_confidence: float,
) -> list[MinorityReport]:
    """Generate minority reports for dissenting personas.

    Minority reports are generated when:
    1. Final decision is APPROVE but any persona has confidence < 0.60
    2. Final decision is APPROVE or REVISE but any persona has blocking issues

    Args:
        persona_reviews: List of all persona reviews
        final_decision: The final aggregated decision
        weighted_confidence: The weighted confidence score

    Returns:
        List of MinorityReport instances for dissenting personas
    """
    minority_reports: list[MinorityReport] = []

    for review in persona_reviews:
        should_report = False
        dissent_reason = ""

        # Check if this persona dissents based on the rules
        if final_decision == DecisionEnum.APPROVE:
            if review.confidence_score < REVISE_THRESHOLD:
                should_report = True
                dissent_reason = (
                    f"Low confidence ({review.confidence_score:.2f}) "
                    f"despite APPROVE decision (threshold: {REVISE_THRESHOLD})"
                )
            elif review.blocking_issues:
                should_report = True
                dissent_reason = (
                    f"Has {len(review.blocking_issues)} blocking issue(s) "
                    "despite APPROVE decision"
                )

        elif final_decision == DecisionEnum.REVISE:
            if review.blocking_issues:
                should_report = True
                dissent_reason = (
                    f"Has {len(review.blocking_issues)} blocking issue(s) "
                    "despite REVISE decision"
                )

        if should_report:
            # Build blocking summary
            if review.blocking_issues:
                blocking_texts = [issue.text for issue in review.blocking_issues]
                blocking_summary = "; ".join(blocking_texts)
            else:
                blocking_summary = (
                    f"Low confidence ({review.confidence_score:.2f}) "
                    "indicates significant concerns"
                )

            # Build mitigation recommendation from persona's recommendations
            if review.recommendations:
                mitigation = "; ".join(review.recommendations)
            else:
                mitigation = "Address concerns raised by this persona before proceeding"

            minority_report = MinorityReport(
                persona_id=review.persona_id,
                persona_name=review.persona_name,
                confidence_score=review.confidence_score,
                blocking_summary=blocking_summary,
                mitigation_recommendation=mitigation,
                strengths=review.strengths if review.strengths else None,
                concerns=[c.text for c in review.concerns] if review.concerns else None,
            )

            minority_reports.append(minority_report)

            logger.debug(
                f"Generated minority report for persona={review.persona_name}",
                extra={
                    "persona_id": review.persona_id,
                    "persona_name": review.persona_name,
                    "dissent_reason": dissent_reason,
                },
            )

    return minority_reports
