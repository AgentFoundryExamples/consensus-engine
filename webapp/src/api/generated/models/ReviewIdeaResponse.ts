/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DecisionAggregation } from './DecisionAggregation';
import type { ExpandIdeaResponse } from './ExpandIdeaResponse';
import type { PersonaReview } from './PersonaReview';
/**
 * Response model for POST /v1/review-idea endpoint.
 *
 * Attributes:
 * expanded_proposal: The expanded proposal data
 * reviews: List of PersonaReview objects (exactly one for single-persona review)
 * draft_decision: Aggregated decision with weighted confidence and breakdown
 * run_id: Unique identifier for this orchestration run
 * elapsed_time: Total wall time for the entire orchestration in seconds
 */
export type ReviewIdeaResponse = {
  /**
   * The expanded proposal with problem statement, solution, etc.
   */
  expanded_proposal: ExpandIdeaResponse;
  /**
   * List of persona reviews (exactly one for GenericReviewer)
   */
  reviews: Array<PersonaReview>;
  /**
   * Aggregated decision with weighted confidence and score breakdown
   */
  draft_decision: DecisionAggregation;
  /**
   * Unique identifier for this orchestration run
   */
  run_id: string;
  /**
   * Total wall time for the entire orchestration in seconds
   */
  elapsed_time: number;
};
