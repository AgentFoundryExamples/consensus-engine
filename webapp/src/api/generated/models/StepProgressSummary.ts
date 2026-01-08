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
