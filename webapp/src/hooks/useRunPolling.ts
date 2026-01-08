/**
 * Custom hook for polling run status with exponential backoff and page visibility handling
 * Polls GET /v1/runs/{run_id} until terminal state (completed/failed)
 * Automatically stops polling when tab is hidden to save resources
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { RunsService } from '../api/client';
import type { RunDetailResponse } from '../api/generated';

export interface UseRunPollingOptions {
  /**
   * Initial polling interval in milliseconds
   * @default 2000 (2 seconds)
   */
  initialInterval?: number;

  /**
   * Maximum polling interval in milliseconds for exponential backoff
   * @default 10000 (10 seconds)
   */
  maxInterval?: number;

  /**
   * Whether to use exponential backoff
   * @default true
   */
  useBackoff?: boolean;

  /**
   * Callback when polling stops due to terminal state
   */
  onComplete?: (data: RunDetailResponse) => void;

  /**
   * Callback when an error occurs during polling
   */
  onError?: (error: Error) => void;
}

export interface UseRunPollingResult {
  /**
   * Current run data
   */
  data: RunDetailResponse | null;

  /**
   * Whether polling is active
   */
  isPolling: boolean;

  /**
   * Error from the last poll attempt
   */
  error: Error | null;

  /**
   * Manually stop polling
   */
  stopPolling: () => void;

  /**
   * Manually trigger a poll
   */
  pollNow: () => Promise<void>;
}

interface PollingState {
  data: RunDetailResponse | null;
  isPolling: boolean;
  error: Error | null;
}

const TERMINAL_STATUSES = ['completed', 'failed'];

/**
 * Hook to poll run status until terminal state
 * Handles exponential backoff, page visibility, and automatic cleanup
 */
export function useRunPolling(
  runId: string | null,
  options: UseRunPollingOptions = {}
): UseRunPollingResult {
  const {
    initialInterval = 2000,
    maxInterval = 10000,
    useBackoff = true,
    onComplete,
    onError,
  } = options;

  const [state, setState] = useState<PollingState>({
    data: null,
    isPolling: false,
    error: null,
  });

  const intervalRef = useRef<number | null>(null);
  const currentIntervalRef = useRef(initialInterval);
  const isPageVisibleRef = useRef(true);
  const isMountedRef = useRef(true);

  // Use ref to store latest poll function to avoid stale closures in intervals
  const pollRef = useRef<(() => Promise<void>) | undefined>(undefined);

  // Poll function that fetches run status
  useEffect(() => {
    pollRef.current = async () => {
      if (!runId) return;

      try {
        const result = await RunsService.getRunDetailV1RunsRunIdGet(runId);

        if (!isMountedRef.current) return;

        setState((prev) => ({ ...prev, data: result, error: null }));

        // Check if terminal state reached
        if (TERMINAL_STATUSES.includes(result.status)) {
          setState((prev) => ({ ...prev, isPolling: false }));
          if (intervalRef.current) {
            window.clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          onComplete?.(result);
        } else if (useBackoff) {
          // Increase interval for next poll (exponential backoff)
          currentIntervalRef.current = Math.min(
            currentIntervalRef.current * 1.5,
            maxInterval
          );
        }
      } catch (err) {
        if (!isMountedRef.current) return;

        const error =
          err instanceof Error ? err : new Error('Unknown error during polling');
        setState((prev) => ({ ...prev, error }));
        onError?.(error);

        // Continue polling even on error (transient network issues)
        // but use backoff to avoid hammering a failing endpoint
        if (useBackoff) {
          currentIntervalRef.current = Math.min(
            currentIntervalRef.current * 2,
            maxInterval
          );
        }
      }
    };
  }, [runId, useBackoff, maxInterval, onComplete, onError]);

  // Manual poll trigger using ref to avoid stale closures
  const pollNow = useCallback(async () => {
    await pollRef.current?.();
  }, []);

  // Stop polling manually
  const stopPolling = useCallback(() => {
    setState((prev) => ({ ...prev, isPolling: false }));
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Handle page visibility changes using ref to avoid stale closures
  useEffect(() => {
    const handleVisibilityChange = () => {
      isPageVisibleRef.current = !document.hidden;

      if (!document.hidden && state.isPolling && runId && !intervalRef.current) {
        // Resume polling when page becomes visible
        pollRef.current?.(); // Immediate poll
        intervalRef.current = window.setInterval(
          () => pollRef.current?.(),
          currentIntervalRef.current
        );
      } else if (document.hidden && intervalRef.current) {
        // Pause polling when page is hidden
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [state.isPolling, runId]);

  // Start/stop polling based on runId and current status
  useEffect(() => {
    // Reset state when runId becomes null
    if (!runId) {
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    // Reset interval on new runId
    currentIntervalRef.current = initialInterval;

    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState((prev) => ({ ...prev, isPolling: true }));

    // Initial poll using ref to avoid stale closure
    pollRef.current?.();

    // Set up interval only if page is visible, using ref to avoid stale closure
    if (!document.hidden) {
      intervalRef.current = window.setInterval(
        () => pollRef.current?.(),
        currentIntervalRef.current
      );
    }

    return () => {
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [runId, initialInterval]);

  // Reset state when runId changes to null
  useEffect(() => {
    if (!runId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setState({ data: null, error: null, isPolling: false });
    }
  }, [runId]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
      }
    };
  }, []);

  return {
    data: state.data,
    isPolling: state.isPolling,
    error: state.error,
    stopPolling,
    pollNow,
  };
}
