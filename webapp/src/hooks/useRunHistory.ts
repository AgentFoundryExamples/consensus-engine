/**
 * Custom hook for fetching and managing run history
 * Fetches runs from GET /v1/runs API endpoint and merges with session-only runs
 */

import { useEffect, useState, useCallback } from 'react';
import { RunsService } from '../api/client';
import type { RunListResponse, RunListItemResponse } from '../api/generated';
import { useRunsStore, type RunSummary } from '../state/runs';

export interface UseRunHistoryOptions {
  /**
   * Whether to fetch history on mount
   * @default true
   */
  autoFetch?: boolean;

  /**
   * Number of items per page
   * @default 30
   */
  limit?: number;

  /**
   * Filter by status
   */
  status?: 'queued' | 'running' | 'completed' | 'failed';

  /**
   * Filter by run type
   */
  runType?: 'initial' | 'revision';

  /**
   * Filter by parent run ID
   */
  parentRunId?: string;

  /**
   * Callback when fetch completes
   */
  onFetchComplete?: (data: RunListResponse) => void;

  /**
   * Callback when an error occurs
   */
  onError?: (error: Error) => void;
}

export interface UseRunHistoryResult {
  /**
   * Combined list of runs (from API and session)
   */
  runs: RunListItemResponse[];

  /**
   * Total count from API
   */
  total: number;

  /**
   * Whether data is being fetched
   */
  isLoading: boolean;

  /**
   * Error from last fetch
   */
  error: Error | null;

  /**
   * Manually trigger a fetch
   */
  refetch: () => Promise<void>;

  /**
   * Load next page
   */
  loadMore: () => Promise<void>;

  /**
   * Whether there are more pages to load
   */
  hasMore: boolean;
}

/**
 * Hook to fetch run history from API and merge with session runs
 */
export function useRunHistory(options: UseRunHistoryOptions = {}): UseRunHistoryResult {
  const {
    autoFetch = true,
    limit = 30,
    status,
    runType,
    parentRunId,
    onFetchComplete,
    onError,
  } = options;

  const [state, setState] = useState<{
    runs: RunListItemResponse[];
    total: number;
    isLoading: boolean;
    error: Error | null;
    offset: number;
  }>({
    runs: [],
    total: 0,
    isLoading: false,
    error: null,
    offset: 0,
  });

  const sessionRuns = useRunsStore((s: { runs: RunSummary[] }) => s.runs);

  // Fetch runs from API
  const fetchRuns = useCallback(
    async (offset: number = 0, append: boolean = false) => {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));

      try {
        const result = await RunsService.listRunsV1RunsGet(
          limit,
          offset,
          status,
          runType,
          parentRunId
        );

        setState((prev) => ({
          ...prev,
          runs: append ? [...prev.runs, ...result.runs] : result.runs,
          total: result.total,
          isLoading: false,
          offset,
        }));

        onFetchComplete?.(result);
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to fetch run history');
        setState((prev) => ({ ...prev, error, isLoading: false }));
        onError?.(error);
      }
    },
    [limit, status, runType, parentRunId, onFetchComplete, onError]
  );

  // Refetch from beginning
  const refetch = useCallback(async () => {
    await fetchRuns(0, false);
  }, [fetchRuns]);

  // Load more (next page)
  const loadMore = useCallback(async () => {
    if (state.isLoading || state.runs.length >= state.total) return;
    await fetchRuns(state.offset + limit, true);
  }, [fetchRuns, state.isLoading, state.offset, state.runs.length, state.total, limit]);

  // Check if there are more pages
  const hasMore = state.runs.length < state.total;

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (!autoFetch) return;

    let cancelled = false;

    const doFetch = async () => {
      if (cancelled) return;
      await fetchRuns(0, false);
    };

    doFetch();

    return () => {
      cancelled = true;
    };
  }, [autoFetch, fetchRuns]);

  // Merge session runs with API runs (deduplicate by run_id)
  const mergedRuns = (() => {
    const apiRunIds = new Set(state.runs.map((r) => r.run_id));
    const sessionOnlyRuns = sessionRuns
      .filter((r: RunSummary) => !apiRunIds.has(r.run_id))
      .map(
        (r: RunSummary): RunListItemResponse => ({
          run_id: r.run_id,
          created_at: r.created_at,
          status: r.status,
          run_type: r.run_type || 'initial',
          priority: 'normal',
          parent_run_id: r.parent_run_id || null,
          overall_weighted_confidence: r.overall_weighted_confidence || null,
          decision_label: r.decision_label || null,
          proposal_title: null,
          proposal_summary: null,
        })
      );

    return [...sessionOnlyRuns, ...state.runs];
  })();

  return {
    runs: mergedRuns,
    total: state.total,
    isLoading: state.isLoading,
    error: state.error,
    refetch,
    loadMore,
    hasMore,
  };
}
