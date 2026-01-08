/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class RootService {
  /**
   * Root
   * Root endpoint with API information.
   *
   * Returns:
   * API welcome message and version
   * @returns any Successful Response
   * @throws ApiError
   */
  public static rootGet(): CancelablePromise<Record<string, any>> {
    return __request(OpenAPI, {
      method: 'GET',
      url: '/',
    });
  }
}
