/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FullReviewRequest } from '../models/FullReviewRequest';
import type { JobEnqueuedResponse } from '../models/JobEnqueuedResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class FullReviewService {
  /**
   * Enqueue a full review job for an idea
   * Accepts a brief idea (1-10 sentences) with optional extra context, creates a Run with status='queued', initializes StepProgress entries, publishes a job message to Pub/Sub, and returns run metadata immediately. Clients should poll GET /v1/runs/{run_id} to check status and retrieve results once processing completes.
   *
   * **Validation Rules:**
   * - Idea: 1-10 sentences, max 10,000 characters
   * - Extra context: max 50,000 characters (string or JSON)
   *
   *
   * **Version Headers (Optional):**
   * - X-Schema-Version: Schema version (current: 1.0.0)
   * - X-Prompt-Set-Version: Prompt set version (current: 1.0.0)
   * If not provided, defaults to current deployment versions with a warning.
   * @param requestBody
   * @param xSchemaVersion
   * @param xPromptSetVersion
   * @returns JobEnqueuedResponse Successful Response
   * @throws ApiError
   */
  public static fullReviewEndpointV1FullReviewPost(
    requestBody: FullReviewRequest,
    xSchemaVersion?: string | null,
    xPromptSetVersion?: string | null
  ): CancelablePromise<JobEnqueuedResponse> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/v1/full-review',
      headers: {
        'X-Schema-Version': xSchemaVersion,
        'X-Prompt-Set-Version': xPromptSetVersion,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation Error`,
      },
    });
  }
}
