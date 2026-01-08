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
 * Score breakdown for a single persona in decision aggregation.
 *
 * This is the legacy schema maintained for backward compatibility.
 * New implementations should use DetailedScoreBreakdown.
 *
 * Attributes:
 * weight: Weight assigned to this persona's review
 * notes: Optional notes about this persona's contribution
 */
export type PersonaScoreBreakdown = {
  /**
   * Weight assigned to this persona's review
   */
  weight: number;
  /**
   * Optional notes about this persona's contribution
   */
  notes?: string | null;
};
