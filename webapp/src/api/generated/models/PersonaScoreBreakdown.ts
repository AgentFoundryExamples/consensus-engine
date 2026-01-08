/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Score breakdown for a single persona in decision aggregation.
 *
 * This is the legacy schema maintained for backward compatibility.
 * New implementations should use DetailedScoreBreakdown.
 *
 * Attributes:
 * weight: Weight assigned to this persona's review
 * notes: Optional notes about this persona's contribution
 */
export type PersonaScoreBreakdown = {
  /**
   * Weight assigned to this persona's review
   */
  weight: number;
  /**
   * Optional notes about this persona's contribution
   */
  notes?: string | null;
};
