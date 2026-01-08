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
 * Detailed score breakdown for decision aggregation.
 *
 * Provides comprehensive scoring information including weights,
 * individual scores, weighted contributions, and formula used.
 *
 * Attributes:
 * weights: Dictionary mapping persona IDs to their weights
 * individual_scores: Dictionary mapping persona IDs to their confidence scores
 * weighted_contributions: Dictionary mapping persona IDs to their weighted contribution
 * formula: Description of the aggregation formula used
 */
export type DetailedScoreBreakdown = {
  /**
   * Dictionary mapping persona IDs to their weights
   */
  weights: Record<string, number>;
  /**
   * Dictionary mapping persona IDs to their confidence scores
   */
  individual_scores: Record<string, number>;
  /**
   * Dictionary mapping persona IDs to their weighted contribution (weight * score)
   */
  weighted_contributions: Record<string, number>;
  /**
   * Description of the aggregation formula used
   */
  formula: string;
};
