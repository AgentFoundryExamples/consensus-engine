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
