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
 * Minority opinion in a decision aggregation.
 *
 * Attributes:
 * persona_id: Stable identifier of the dissenting persona
 * persona_name: Name of the dissenting persona
 * confidence_score: The confidence score of the dissenting persona
 * blocking_summary: Summary of blocking issues from dissenting persona
 * mitigation_recommendation: Recommended mitigation for blocking issues
 * strengths: Identified strengths from minority view (optional for backward compatibility)
 * concerns: Concerns from minority view (optional for backward compatibility)
 */
export type MinorityReport = {
  /**
   * Stable identifier of the dissenting persona
   */
  persona_id: string;
  /**
   * Name of the dissenting persona
   */
  persona_name: string;
  /**
   * The confidence score of the dissenting persona
   */
  confidence_score: number;
  /**
   * Summary of blocking issues from dissenting persona
   */
  blocking_summary: string;
  /**
   * Recommended mitigation for blocking issues
   */
  mitigation_recommendation: string;
  /**
   * Identified strengths from minority view (optional for backward compatibility)
   */
  strengths?: Array<string> | null;
  /**
   * Concerns from minority view (optional for backward compatibility)
   */
  concerns?: Array<string> | null;
};
