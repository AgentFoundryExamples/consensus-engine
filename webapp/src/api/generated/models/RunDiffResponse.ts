/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for GET /v1/runs/{run_id}/diff/{other_run_id} endpoint.
 *
 * Attributes:
 * metadata: Metadata about the two runs and their relationship
 * proposal_changes: Per-section diffs of proposal text
 * persona_deltas: Changes in persona confidence scores and blocking flags
 * decision_delta: Changes in overall weighted confidence and decision label
 */
export type RunDiffResponse = {
  /**
   * Metadata including run IDs, timestamps, and parent/child relationship status
   */
  metadata: Record<string, any>;
  /**
   * Per-section proposal diffs with status (unchanged/modified/added/removed) and unified diff output for modified sections
   */
  proposal_changes: Record<string, any>;
  /**
   * List of persona score deltas with old/new confidence, blocking issues changes, and security concerns changes
   */
  persona_deltas?: Array<Record<string, any>>;
  /**
   * Overall decision comparison including confidence delta and decision label changes
   */
  decision_delta: Record<string, any>;
};
