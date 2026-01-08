/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Summary of a step progress for run detail responses.
 *
 * Attributes:
 * step_name: Canonical step name (e.g., 'expand', 'review_architect')
 * step_order: Integer ordering for deterministic step sequence
 * status: Current status of the step (pending, running, completed, failed)
 * started_at: ISO timestamp when step processing started (null until started)
 * completed_at: ISO timestamp when step finished (null until completed/failed)
 * error_message: Optional error message if step failed
 */
export type StepProgressSummary = {
  /**
   * Canonical step name
   */
  step_name: string;
  /**
   * Integer ordering for deterministic step sequence
   */
  step_order: number;
  /**
   * Current status: pending, running, completed, or failed
   */
  status: string;
  /**
   * ISO timestamp when step processing started
   */
  started_at?: string | null;
  /**
   * ISO timestamp when step finished
   */
  completed_at?: string | null;
  /**
   * Optional error message if step failed
   */
  error_message?: string | null;
};
