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
 * Response model for GET /health endpoint.
 *
 * Attributes:
 * status: Service health status
 * environment: Application environment
 * debug: Debug mode flag
 * model: OpenAI model name
 * temperature: Model temperature setting
 * uptime_seconds: Service uptime in seconds
 * config_status: Configuration sanity check status
 */
export type HealthResponse = {
  /**
   * Service health status (healthy, degraded, unhealthy)
   */
  status: string;
  /**
   * Application environment (development, production, testing)
   */
  environment: string;
  /**
   * Debug mode flag
   */
  debug: boolean;
  /**
   * OpenAI model name
   */
  model: string;
  /**
   * Model temperature setting
   */
  temperature: number;
  /**
   * Service uptime in seconds
   */
  uptime_seconds: number;
  /**
   * Configuration sanity status (ok, warning, error)
   */
  config_status: string;
};
