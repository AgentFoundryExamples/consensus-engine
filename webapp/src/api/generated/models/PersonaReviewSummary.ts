/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Summary of a persona review for run list/detail responses.
 *
 * Attributes:
 * persona_id: Stable identifier for the persona
 * persona_name: Display name for the persona
 * confidence_score: Numeric confidence score [0.0, 1.0]
 * blocking_issues_present: Boolean flag indicating presence of blocking issues
 * prompt_parameters_json: Prompt parameters used for this review
 */
export type PersonaReviewSummary = {
  /**
   * Stable identifier for the persona
   */
  persona_id: string;
  /**
   * Display name for the persona
   */
  persona_name: string;
  /**
   * Numeric confidence score [0.0, 1.0]
   */
  confidence_score: number;
  /**
   * Boolean flag indicating presence of blocking issues
   */
  blocking_issues_present: boolean;
  /**
   * Prompt parameters (model, temperature, persona version, retries)
   */
  prompt_parameters_json: Record<string, any>;
};
