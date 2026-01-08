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
import type { DecisionAggregation } from './DecisionAggregation';
import type { ExpandIdeaResponse } from './ExpandIdeaResponse';
import type { PersonaReview } from './PersonaReview';
/**
 * Response model for POST /v1/review-idea endpoint.
 *
 * Attributes:
 * expanded_proposal: The expanded proposal data
 * reviews: List of PersonaReview objects (exactly one for single-persona review)
 * draft_decision: Aggregated decision with weighted confidence and breakdown
 * run_id: Unique identifier for this orchestration run
 * elapsed_time: Total wall time for the entire orchestration in seconds
 */
export type ReviewIdeaResponse = {
  /**
   * The expanded proposal with problem statement, solution, etc.
   */
  expanded_proposal: ExpandIdeaResponse;
  /**
   * List of persona reviews (exactly one for GenericReviewer)
   */
  reviews: Array<PersonaReview>;
  /**
   * Aggregated decision with weighted confidence and score breakdown
   */
  draft_decision: DecisionAggregation;
  /**
   * Unique identifier for this orchestration run
   */
  run_id: string;
  /**
   * Total wall time for the entire orchestration in seconds
   */
  elapsed_time: number;
};
