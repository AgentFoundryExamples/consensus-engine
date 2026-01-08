/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ReviewIdeaRequest } from '../models/ReviewIdeaRequest';
import type { ReviewIdeaResponse } from '../models/ReviewIdeaResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ReviewService {
  /**
   * Review an idea through expand, review, and decision aggregation
   * Accepts a brief idea (1-10 sentences) with optional extra context, expands it into a comprehensive proposal, reviews it with a single persona (GenericReviewer), and aggregates a draft decision. Returns the expanded proposal, review, and decision with telemetry. Errors include failed_step and any partial results.
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
   * @returns ReviewIdeaResponse Successfully expanded and reviewed idea
   * @throws ApiError
   */
  public static reviewIdeaEndpointV1ReviewIdeaPost(
    requestBody: ReviewIdeaRequest,
    xSchemaVersion?: string | null,
    xPromptSetVersion?: string | null
  ): CancelablePromise<ReviewIdeaResponse> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/v1/review-idea',
      headers: {
        'X-Schema-Version': xSchemaVersion,
        'X-Prompt-Set-Version': xPromptSetVersion,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        422: `Validation error - invalid request format or sentence count`,
        500: `Internal server error - expansion or review failure`,
      },
    });
  }
}
