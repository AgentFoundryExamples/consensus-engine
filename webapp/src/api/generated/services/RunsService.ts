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

import type { CreateRevisionRequest } from '../models/CreateRevisionRequest';
import type { JobEnqueuedResponse } from '../models/JobEnqueuedResponse';
import type { RunDetailResponse } from '../models/RunDetailResponse';
import type { RunDiffResponse } from '../models/RunDiffResponse';
import type { RunListResponse } from '../models/RunListResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class RunsService {
  /**
   * List runs with filtering and pagination
   * Returns a paginated list of runs sorted by created_at descending. Supports filtering by status, run_type, parent_run_id, decision, min_confidence, and date ranges. Returns empty list (200) for no matches.
   * @param limit Number of items per page (1-100)
   * @param offset Offset for pagination
   * @param status Filter by status: running, completed, or failed
   * @param runType Filter by run_type: initial or revision
   * @param parentRunId Filter by parent_run_id (UUID)
   * @param decision Filter by decision_label (e.g., approve, revise, reject)
   * @param minConfidence Filter by minimum overall_weighted_confidence (0.0-1.0)
   * @param startDate Filter by created_at >= start_date (ISO 8601 format)
   * @param endDate Filter by created_at <= end_date (ISO 8601 format)
   * @returns RunListResponse Successful Response
   * @throws ApiError
   */
  public static listRunsV1RunsGet(
    limit: number = 30,
    offset?: number,
    status?: string | null,
    runType?: string | null,
    parentRunId?: string | null,
    decision?: string | null,
    minConfidence?: number | null,
    startDate?: string | null,
    endDate?: string | null
  ): CancelablePromise<RunListResponse> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/v1/runs',
      query: {
        limit: limit,
        offset: offset,
        status: status,
        run_type: runType,
        parent_run_id: parentRunId,
        decision: decision,
        min_confidence: minConfidence,
        start_date: startDate,
        end_date: endDate,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Get full run details by ID
   * Returns the full run detail including metadata, proposal JSON, persona reviews, and decision JSON. Returns 404 for missing run_id.
   * @param runId
   * @returns RunDetailResponse Successful Response
   * @throws ApiError
   */
  public static getRunDetailV1RunsRunIdGet(runId: string): CancelablePromise<RunDetailResponse> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/v1/runs/{run_id}',
      path: {
        run_id: runId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Compare two runs and compute diff
   * Computes structured diff between two runs including proposal changes, persona score deltas, and decision changes. Returns 400 for identical runs, 404 for missing runs. All diffs are computed from stored JSONB without re-running models.
   * @param runId
   * @param otherRunId
   * @returns RunDiffResponse Successful Response
   * @throws ApiError
   */
  public static getRunDiffV1RunsRunIdDiffOtherRunIdGet(
    runId: string,
    otherRunId: string
  ): CancelablePromise<RunDiffResponse> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/v1/runs/{run_id}/diff/{other_run_id}',
      path: {
        run_id: runId,
        other_run_id: otherRunId,
      },
      errors: {
        422: `Validation Error`,
      },
    });
  }
  /**
   * Enqueue a revision job from an existing run
   * Creates a revision run with status='queued', initializes StepProgress entries, publishes a job message to Pub/Sub, and returns run metadata immediately. Clients should poll GET /v1/runs/{run_id} to check status and retrieve results once processing completes.
   *
   * **Validation Rules:**
   * - edited_proposal: max 100,000 characters (string or JSON)
   * - edit_notes: max 10,000 characters
   * - input_idea: max 10,000 characters
   * - extra_context: max 50,000 characters (string or JSON)
   * - At least one of edited_proposal or edit_notes must be provided
   *
   *
   * **Version Headers (Optional):**
   * - X-Schema-Version: Schema version (current: 1.0.0)
   * - X-Prompt-Set-Version: Prompt set version (current: 1.0.0)
   * If not provided, defaults to current deployment versions with a warning.
   * @param runId
   * @param requestBody
   * @param xSchemaVersion
   * @param xPromptSetVersion
   * @returns JobEnqueuedResponse Successful Response
   * @throws ApiError
   */
  public static createRevisionV1RunsRunIdRevisionsPost(
    runId: string,
    requestBody: CreateRevisionRequest,
    xSchemaVersion?: string | null,
    xPromptSetVersion?: string | null
  ): CancelablePromise<JobEnqueuedResponse> {
    return __request(OpenAPI, {
      method: 'POST',
      url: '/v1/runs/{run_id}/revisions',
      path: {
        run_id: runId,
      },
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
