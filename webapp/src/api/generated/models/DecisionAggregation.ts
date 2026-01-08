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

import type { DecisionEnum } from './DecisionEnum';
import type { DetailedScoreBreakdown } from './DetailedScoreBreakdown';
import type { MinorityReport } from './MinorityReport';
import type { PersonaScoreBreakdown } from './PersonaScoreBreakdown';
/**
 * Aggregated decision from multiple persona reviews.
 *
 * This model encapsulates the consensus decision built from one or more
 * persona reviews, including weighted confidence scoring and optional
 * minority opinions.
 *
 * Attributes:
 * overall_weighted_confidence: Weighted confidence score across all personas (legacy field)
 * weighted_confidence: Weighted confidence score across all personas (new field)
 * decision: Final decision outcome (approve/revise/reject)
 * score_breakdown: Per-persona scoring details with weights and notes (legacy, optional)
 * detailed_score_breakdown: Detailed scoring breakdown with formula (new field, optional)
 * minority_report: Optional dissenting opinion from minority persona
 * (supports multiple dissenters)
 * minority_reports: Optional list of dissenting opinions from multiple personas (new field)
 */
export type DecisionAggregation = {
  /**
   * Weighted confidence score across all personas (legacy field)
   */
  overall_weighted_confidence: number;
  /**
   * Weighted confidence score across all personas (new field, mirrors overall_weighted_confidence)
   */
  weighted_confidence?: number | null;
  /**
   * Final decision outcome (approve/revise/reject)
   */
  decision: DecisionEnum;
  /**
   * Per-persona scoring details with weights and notes (legacy format)
   */
  score_breakdown?: Record<string, PersonaScoreBreakdown> | null;
  /**
   * Detailed score breakdown with weights, individual scores, contributions, and formula
   */
  detailed_score_breakdown?: DetailedScoreBreakdown | null;
  /**
   * Optional dissenting opinion from minority persona (single dissenter, legacy field)
   */
  minority_report?: MinorityReport | null;
  /**
   * Optional list of dissenting opinions from multiple personas (new field)
   */
  minority_reports?: Array<MinorityReport> | null;
};
