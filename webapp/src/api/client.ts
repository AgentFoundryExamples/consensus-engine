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
/**
 * Centralized API client with authentication and base URL configuration
 * Wraps the generated OpenAPI client with environment-specific settings
 */

import { OpenAPI } from './generated';
import { config } from '../config';

/**
 * Configure the OpenAPI client with base URL and authentication
 * This should be called once at app startup
 *
 * @throws Error if configuration is invalid or fails
 */
export function configureApiClient(): void {
  try {
    // Validate base URL
    if (!config.apiBaseUrl) {
      throw new Error(
        'API base URL is not configured. Set VITE_API_BASE_URL environment variable.'
      );
    }

    // Set base URL from environment
    OpenAPI.BASE = config.apiBaseUrl;

    // Configure authentication if IAM token is provided
    if (config.iamToken) {
      OpenAPI.TOKEN = config.iamToken;
    }

    // Add request interceptor for IAM authentication headers
    // This is a placeholder for Cloud IAP/IAM authentication
    OpenAPI.HEADERS = async () => {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      // If IAM token is available, add it to Authorization header
      if (config.iamToken) {
        headers['Authorization'] = `Bearer ${config.iamToken}`;
      }

      return headers;
    };

    // Log configuration success (without exposing sensitive data)
    console.log('API client configured:', {
      baseUrl: OpenAPI.BASE,
      hasAuth: !!config.iamToken,
    });
  } catch (error) {
    console.error('Failed to configure API client:', error);
    throw error;
  }
}

/**
 * Get the current API base URL
 */
export function getApiBaseUrl(): string {
  return OpenAPI.BASE;
}

// Re-export all services from generated client for convenience
export * from './generated';
