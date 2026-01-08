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
 * Summary of a persona review for run list/detail responses.
 *
 * Attributes:
 * persona_id: Stable identifier for the persona
 * persona_name: Display name for the persona
 * confidence_score: Numeric confidence score [0.0, 1.0]
 * blocking_issues_present: Boolean flag indicating presence of blocking issues
 * prompt_parameters_json: Prompt parameters used for this review
 */
export type PersonaReviewSummary = {
  /**
   * Stable identifier for the persona
   */
  persona_id: string;
  /**
   * Display name for the persona
   */
  persona_name: string;
  /**
   * Numeric confidence score [0.0, 1.0]
   */
  confidence_score: number;
  /**
   * Boolean flag indicating presence of blocking issues
   */
  blocking_issues_present: boolean;
  /**
   * Prompt parameters (model, temperature, persona version, retries)
   */
  prompt_parameters_json: Record<string, any>;
};
