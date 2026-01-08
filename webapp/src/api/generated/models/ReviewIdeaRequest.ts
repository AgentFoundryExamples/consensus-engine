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
 * Request model for POST /v1/review-idea endpoint.
 *
 * Attributes:
 * idea: The core idea to expand and review (1-10 sentences)
 * extra_context: Optional additional context as dict or string
 */
export type ReviewIdeaRequest = {
  /**
   * The core idea or problem to expand and review (1-10 sentences)
   */
  idea: string;
  /**
   * Optional additional context or constraints (dict or string)
   */
  extra_context?: Record<string, any> | string | null;
};
