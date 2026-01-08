/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ExpandIdeaRequest } from '../models/ExpandIdeaRequest';
import type { ExpandIdeaResponse } from '../models/ExpandIdeaResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ExpandService {
  /**
   * Expand an idea into a detailed proposal
   * Accepts a brief idea (1-10 sentences) with optional extra context and expands it into a comprehensive, structured proposal using LLM. Returns problem statement, proposed solution, assumptions, and scope boundaries.
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
   * @returns ExpandIdeaResponse Successfully expanded idea into structured proposal
   * @throws ApiError
   */
  public static expandIdeaEndpointV1ExpandIdeaPost(
    requestBody: ExpandIdeaRequest,
    xSchemaVersion?: string | null,
    xPromptSetVersion?: string | null
  ): CancelablePromise<ExpandIdeaResponse> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/v1/expand-idea',
      headers: {
        'X-Schema-Version': xSchemaVersion,
        'X-Prompt-Set-Version': xPromptSetVersion,
      },
      body: requestBody,
      mediaType: 'application/json',
      errors: {
        400: `Bad request - unsupported version`,
        422: `Validation error - invalid request format or sentence count`,
        500: `Internal server error - service or LLM error`,
        503: `Service unavailable - rate limit or timeout`,
      },
    });
  }
}
