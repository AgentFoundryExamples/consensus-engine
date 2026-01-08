/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for POST /v1/expand-idea endpoint.
 *
 * Attributes:
 * problem_statement: Clear articulation of the problem
 * proposed_solution: Detailed solution approach
 * assumptions: List of underlying assumptions
 * scope_non_goals: List of what is out of scope
 * title: Optional short title for the proposal
 * summary: Optional brief summary of the proposal
 * raw_idea: Optional original idea text before expansion
 * raw_expanded_proposal: Optional complete proposal text
 * schema_version: Schema version used for this response
 * prompt_set_version: Prompt set version used for this response
 * metadata: Request metadata (request_id, model, timing, etc.)
 */
export type ExpandIdeaResponse = {
  /**
   * Clear articulation of the problem to be solved
   */
  problem_statement: string;
  /**
   * Detailed description of the proposed solution approach
   */
  proposed_solution: string;
  /**
   * List of underlying assumptions made in the proposal
   */
  assumptions: Array<string>;
  /**
   * List of what is explicitly out of scope or non-goals
   */
  scope_non_goals: Array<string>;
  /**
   * Optional short title for the proposal
   */
  title?: string | null;
  /**
   * Optional brief summary of the proposal
   */
  summary?: string | null;
  /**
   * Optional original idea text before expansion
   */
  raw_idea?: string | null;
  /**
   * Optional complete expanded proposal text or additional notes
   */
  raw_expanded_proposal?: string | null;
  /**
   * Schema version used for this response (e.g., '1.0.0')
   */
  schema_version: string;
  /**
   * Prompt set version used for this response (e.g., '1.0.0')
   */
  prompt_set_version: string;
  /**
   * Request metadata including request_id, model, temperature, timing, etc.
   */
  metadata: Record<string, any>;
};
