/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { RunListItemResponse } from './RunListItemResponse';
/**
 * Response model for GET /v1/runs endpoint.
 *
 * Attributes:
 * runs: List of run items
 * total: Total number of runs matching filters
 * limit: Number of items per page
 * offset: Current offset
 */
export type RunListResponse = {
  /**
   * List of run items
   */
  runs: Array<RunListItemResponse>;
  /**
   * Total number of runs matching filters
   */
  total: number;
  /**
   * Number of items per page
   */
  limit: number;
  /**
   * Current offset
   */
  offset: number;
};
