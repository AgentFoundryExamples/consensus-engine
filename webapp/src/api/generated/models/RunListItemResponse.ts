/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for individual items in GET /v1/runs list.
 *
 * Attributes:
 * run_id: UUID of the run
 * created_at: Timestamp when run was created
 * status: Current status of the run
 * queued_at: Timestamp when run was queued
 * started_at: Timestamp when run processing started
 * completed_at: Timestamp when run finished
 * retry_count: Number of retry attempts for this run
 * run_type: Whether this is an initial run or revision
 * priority: Priority level for run execution
 * parent_run_id: Optional UUID of parent run for revisions
 * overall_weighted_confidence: Final weighted confidence score
 * decision_label: Final decision label
 * proposal_title: Title from the proposal (truncated metadata)
 * proposal_summary: Summary from the proposal (truncated metadata)
 */
export type RunListItemResponse = {
  /**
   * UUID of the run
   */
  run_id: string;
  /**
   * ISO timestamp when run was created
   */
  created_at: string;
  /**
   * Current status: queued, running, completed, or failed
   */
  status: string;
  /**
   * ISO timestamp when run was queued
   */
  queued_at?: string | null;
  /**
   * ISO timestamp when run processing started
   */
  started_at?: string | null;
  /**
   * ISO timestamp when run finished
   */
  completed_at?: string | null;
  /**
   * Number of retry attempts for this run
   */
  retry_count?: number;
  /**
   * Whether this is an initial run or revision
   */
  run_type: string;
  /**
   * Priority level: normal or high
   */
  priority: string;
  /**
   * Optional UUID of parent run for revisions
   */
  parent_run_id?: string | null;
  /**
   * Final weighted confidence score (null until decision)
   */
  overall_weighted_confidence?: number | null;
  /**
   * Final decision label (null until decision)
   */
  decision_label?: string | null;
  /**
   * Title from the proposal (truncated)
   */
  proposal_title?: string | null;
  /**
   * Summary from the proposal (truncated)
   */
  proposal_summary?: string | null;
};
