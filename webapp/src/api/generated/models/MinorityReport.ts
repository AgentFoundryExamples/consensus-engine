/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Minority opinion in a decision aggregation.
 *
 * Attributes:
 * persona_id: Stable identifier of the dissenting persona
 * persona_name: Name of the dissenting persona
 * confidence_score: The confidence score of the dissenting persona
 * blocking_summary: Summary of blocking issues from dissenting persona
 * mitigation_recommendation: Recommended mitigation for blocking issues
 * strengths: Identified strengths from minority view (optional for backward compatibility)
 * concerns: Concerns from minority view (optional for backward compatibility)
 */
export type MinorityReport = {
  /**
   * Stable identifier of the dissenting persona
   */
  persona_id: string;
  /**
   * Name of the dissenting persona
   */
  persona_name: string;
  /**
   * The confidence score of the dissenting persona
   */
  confidence_score: number;
  /**
   * Summary of blocking issues from dissenting persona
   */
  blocking_summary: string;
  /**
   * Recommended mitigation for blocking issues
   */
  mitigation_recommendation: string;
  /**
   * Identified strengths from minority view (optional for backward compatibility)
   */
  strengths?: Array<string> | null;
  /**
   * Concerns from minority view (optional for backward compatibility)
   */
  concerns?: Array<string> | null;
};
