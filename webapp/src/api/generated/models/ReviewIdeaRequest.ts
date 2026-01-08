/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request model for POST /v1/review-idea endpoint.
 *
 * Attributes:
 * idea: The core idea to expand and review (1-10 sentences)
 * extra_context: Optional additional context as dict or string
 */
export type ReviewIdeaRequest = {
  /**
   * The core idea or problem to expand and review (1-10 sentences)
   */
  idea: string;
  /**
   * Optional additional context or constraints (dict or string)
   */
  extra_context?: Record<string, any> | string | null;
};
