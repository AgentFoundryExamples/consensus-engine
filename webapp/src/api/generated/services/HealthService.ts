/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { HealthResponse } from '../models/HealthResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class HealthService {
  /**
   * Health check endpoint
   * Returns service health status, configuration metadata, and uptime. Performs configuration sanity checks without exposing secrets. Status can be 'healthy', 'degraded', or 'unhealthy'.
   * @returns HealthResponse Service is healthy or degraded
   * @throws ApiError
   */
  public static healthCheckHealthGet(): CancelablePromise<HealthResponse> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/health',
    });
  }
}
