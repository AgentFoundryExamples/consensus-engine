/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PersonaReviewSummary } from './PersonaReviewSummary';
import type { StepProgressSummary } from './StepProgressSummary';
/**
 * Response model for GET /v1/runs/{run_id} endpoint.
 *
 * Attributes:
 * run_id: UUID of the run
 * created_at: Timestamp when run was created
 * updated_at: Timestamp when run was last updated
 * status: Current status of the run
 * queued_at: Timestamp when run was queued
 * started_at: Timestamp when run processing started
 * completed_at: Timestamp when run finished
 * retry_count: Number of retry attempts for this run
 * run_type: Whether this is an initial run or revision
 * priority: Priority level for run execution
 * parent_run_id: Optional UUID of parent run for revisions
 * input_idea: The original idea text
 * extra_context: Optional additional context as JSON
 * model: LLM model identifier used for this run
 * temperature: Temperature parameter used for LLM calls
 * parameters_json: Additional LLM parameters as JSON
 * overall_weighted_confidence: Final weighted confidence score
 * decision_label: Final decision label
 * schema_version: Schema version used for this run's outputs
 * prompt_set_version: Prompt set version used for this run
 * proposal: Structured proposal JSON (nullable if run failed early)
 * persona_reviews: Array of persona reviews with scores and blocking flags
 * decision: Decision JSON (nullable if run failed or incomplete)
 * step_progress: Array of step progress records showing pipeline execution
 */
export type RunDetailResponse = {
  /**
   * UUID of the run
   */
  run_id: string;
  /**
   * ISO timestamp when run was created
   */
  created_at: string;
  /**
   * ISO timestamp when run was last updated
   */
  updated_at: string;
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
   * The original idea text
   */
  input_idea: string;
  /**
   * Optional additional context as JSON
   */
  extra_context?: Record<string, any> | null;
  /**
   * LLM model identifier used for this run
   */
  model: string;
  /**
   * Temperature parameter used for LLM calls
   */
  temperature: number;
  /**
   * Additional LLM parameters as JSON
   */
  parameters_json: Record<string, any>;
  /**
   * Final weighted confidence score (null until decision)
   */
  overall_weighted_confidence?: number | null;
  /**
   * Final decision label (null until decision)
   */
  decision_label?: string | null;
  /**
   * Schema version used for this run's outputs (e.g., '1.0.0')
   */
  schema_version: string;
  /**
   * Prompt set version used for this run (e.g., '1.0.0')
   */
  prompt_set_version: string;
  /**
   * Structured proposal JSON (null if run failed early)
   */
  proposal?: Record<string, any> | null;
  /**
   * Array of persona reviews with scores and blocking flags
   */
  persona_reviews?: Array<PersonaReviewSummary>;
  /**
   * Decision JSON (null if run failed or incomplete)
   */
  decision?: Record<string, any> | null;
  /**
   * Array of step progress records showing pipeline execution ordered by step_order
   */
  step_progress?: Array<StepProgressSummary>;
};
