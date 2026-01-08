/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Detailed score breakdown for decision aggregation.
 *
 * Provides comprehensive scoring information including weights,
 * individual scores, weighted contributions, and formula used.
 *
 * Attributes:
 * weights: Dictionary mapping persona IDs to their weights
 * individual_scores: Dictionary mapping persona IDs to their confidence scores
 * weighted_contributions: Dictionary mapping persona IDs to their weighted contribution
 * formula: Description of the aggregation formula used
 */
export type DetailedScoreBreakdown = {
  /**
   * Dictionary mapping persona IDs to their weights
   */
  weights: Record<string, number>;
  /**
   * Dictionary mapping persona IDs to their confidence scores
   */
  individual_scores: Record<string, number>;
  /**
   * Dictionary mapping persona IDs to their weighted contribution (weight * score)
   */
  weighted_contributions: Record<string, number>;
  /**
   * Description of the aggregation formula used
   */
  formula: string;
};
