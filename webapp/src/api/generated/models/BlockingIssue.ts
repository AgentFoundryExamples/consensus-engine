/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * A blocking issue identified during persona review.
 *
 * Attributes:
 * text: The blocking issue description
 * security_critical: Optional flag indicating if this is a security-critical issue
 * that gives SecurityGuardian veto power
 */
export type BlockingIssue = {
  /**
   * The blocking issue description
   */
  text: string;
  /**
   * Whether this is a security-critical issue (SecurityGuardian veto power)
   */
  security_critical?: boolean | null;
};
