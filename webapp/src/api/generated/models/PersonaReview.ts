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
import type { BlockingIssue } from './BlockingIssue';
import type { Concern } from './Concern';
/**
 * Review from a specific persona evaluating a proposal.
 *
 * This model captures a single persona's evaluation including strengths,
 * concerns, recommendations, and risk assessments.
 *
 * Attributes:
 * persona_name: Name of the reviewing persona (required)
 * persona_id: Stable identifier for the persona (required, e.g., 'architect')
 * confidence_score: Confidence in the proposal, range [0.0, 1.0] (required)
 * strengths: List of identified strengths in the proposal (required)
 * concerns: List of concerns with blocking flags (required)
 * recommendations: List of actionable recommendations (required)
 * blocking_issues: List of critical blocking issues with optional security flags
 * (required, can be empty)
 * estimated_effort: Effort estimation as string or structured data (required)
 * dependency_risks: List of identified dependency risks (required, can be empty)
 * internal_metadata: Optional metadata for tracking (e.g., model, duration)
 */
export type PersonaReview = {
  /**
   * Name of the reviewing persona
   */
  persona_name: string;
  /**
   * Stable identifier for the persona (e.g., 'architect', 'security_guardian')
   */
  persona_id: string;
  /**
   * Confidence in the proposal, range [0.0, 1.0]
   */
  confidence_score: number;
  /**
   * List of identified strengths in the proposal
   */
  strengths: Array<string>;
  /**
   * List of concerns with blocking flags
   */
  concerns: Array<Concern>;
  /**
   * List of actionable recommendations
   */
  recommendations: Array<string>;
  /**
   * List of critical blocking issues with optional security_critical flags (can be empty)
   */
  blocking_issues: Array<BlockingIssue>;
  /**
   * Effort estimation as string or structured data
   */
  estimated_effort: string | Record<string, any>;
  /**
   * List of identified dependency risks (can be empty)
   */
  dependency_risks: Array<string | Record<string, any>>;
  /**
   * Optional internal metadata (e.g., model, duration, timestamps)
   */
  internal_metadata?: Record<string, any> | null;
};
