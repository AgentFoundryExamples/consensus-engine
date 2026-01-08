// Copyright 2025 John Brosnihan
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */

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
