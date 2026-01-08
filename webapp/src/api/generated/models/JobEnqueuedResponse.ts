/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response model for job enqueueing endpoints (POST /v1/full-review, POST /v1/runs/{run_id}/revisions).
 *
 * This response is returned immediately after a run is created and a job is enqueued
 * to Pub/Sub. Clients can poll GET /v1/runs/{run_id} to check status and retrieve
 * results once processing completes.
 *
 * Attributes:
 * run_id: UUID of the created run
 * status: Current status of the run ('queued')
 * run_type: Type of run ('initial' or 'revision')
 * priority: Priority level ('normal' or 'high')
 * created_at: ISO timestamp when run was created
 * queued_at: ISO timestamp when run was enqueued
 * message: Human-readable message about the enqueued job
 */
export type JobEnqueuedResponse = {
  /**
   * UUID of the created run
   */
  run_id: string;
  /**
   * Current status: 'queued'
   */
  status: string;
  /**
   * Type of run: 'initial' or 'revision'
   */
  run_type: string;
  /**
   * Priority level: 'normal' or 'high'
   */
  priority: string;
  /**
   * ISO timestamp when run was created
   */
  created_at: string;
  /**
   * ISO timestamp when run was enqueued
   */
  queued_at: string;
  /**
   * Human-readable message about the enqueued job
   */
  message: string;
};
