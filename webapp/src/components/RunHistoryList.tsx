/**
 * RunHistoryList component for displaying run history with status badges
 * Shows runs from current session and optionally fetched via GET /v1/runs
 */

import { useCallback } from 'react';
import type { RunListItemResponse } from '../api/generated';

export interface RunHistoryListProps {
  /**
   * List of runs to display
   */
  runs: RunListItemResponse[];

  /**
   * Whether data is loading
   */
  isLoading?: boolean;

  /**
   * Callback when a run is selected
   */
  onSelectRun: (runId: string) => void;

  /**
   * Currently selected run ID
   */
  selectedRunId?: string | null;

  /**
   * Whether to show load more button
   */
  hasMore?: boolean;

  /**
   * Callback to load more runs
   */
  onLoadMore?: () => void;

  /**
   * Optional CSS class name
   */
  className?: string;
}

/**
 * Displays a list of runs with status indicators and revision badges
 */
export function RunHistoryList({
  runs,
  isLoading = false,
  onSelectRun,
  selectedRunId,
  hasMore = false,
  onLoadMore,
  className = '',
}: RunHistoryListProps) {
  // Get status badge color
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'queued':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // Get decision badge color
  const getDecisionColor = (decision: string) => {
    switch (decision.toLowerCase()) {
      case 'approve':
        return 'bg-green-100 text-green-800';
      case 'revise':
        return 'bg-yellow-100 text-yellow-800';
      case 'reject':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // Handle run selection
  const handleSelectRun = useCallback(
    (runId: string) => {
      onSelectRun(runId);
    },
    [onSelectRun]
  );

  // Group runs by parent/child relationships
  const groupedRuns = (() => {
    const groups: { root: RunListItemResponse; children: RunListItemResponse[] }[] = [];
    const runMap = new Map<string, RunListItemResponse>();
    const childrenMap = new Map<string, RunListItemResponse[]>();

    // Build maps for O(1) lookups
    runs.forEach((run) => {
      runMap.set(run.run_id, run);
      if (run.parent_run_id) {
        if (!childrenMap.has(run.parent_run_id)) {
          childrenMap.set(run.parent_run_id, []);
        }
        childrenMap.get(run.parent_run_id)!.push(run);
      }
    });

    const processed = new Set<string>();

    // First pass: create groups for root runs
    runs.forEach((run) => {
      if (processed.has(run.run_id)) return;

      // If this is a root run (no parent), create a group
      if (!run.parent_run_id) {
        const children = childrenMap.get(run.run_id) || [];
        groups.push({ root: run, children });
        processed.add(run.run_id);
        children.forEach((child) => processed.add(child.run_id));
      }
    });

    // Second pass: add orphaned runs (parent not in list)
    runs.forEach((run) => {
      if (!processed.has(run.run_id)) {
        groups.push({ root: run, children: [] });
        processed.add(run.run_id);
      }
    });

    return groups;
  })();

  if (runs.length === 0 && !isLoading) {
    return (
      <div className={`rounded-lg border border-gray-200 bg-gray-50 p-6 text-center ${className}`}>
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
          />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">No runs yet</h3>
        <p className="mt-1 text-sm text-gray-500">Submit an idea to get started</p>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {isLoading && runs.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-6 text-center">
          <div
            className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"
            role="status"
          >
            <span className="sr-only">Loading...</span>
          </div>
          <p className="mt-2 text-sm text-gray-600">Loading run history...</p>
        </div>
      ) : (
        <>
          {groupedRuns.map(({ root, children }) => (
            <div key={root.run_id} className="rounded-lg border border-gray-200 bg-white shadow-sm">
              {/* Root run */}
              <button
                type="button"
                onClick={() => handleSelectRun(root.run_id)}
                className={`w-full p-4 text-left transition-colors hover:bg-gray-50 ${
                  selectedRunId === root.run_id ? 'bg-blue-50' : ''
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      {/* Run type badge */}
                      <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
                        {root.run_type === 'revision' ? 'Revision' : 'Original'}
                      </span>

                      {/* Status badge */}
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${getStatusColor(root.status)}`}
                      >
                        {root.status}
                      </span>

                      {/* Decision badge (if completed) */}
                      {root.decision_label && (
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${getDecisionColor(root.decision_label)}`}
                        >
                          {root.decision_label}
                        </span>
                      )}
                    </div>

                    {/* Proposal title or summary */}
                    <p className="mb-1 text-sm font-medium text-gray-900">
                      {root.proposal_title || root.proposal_summary || 'Untitled'}
                    </p>

                    {/* Metadata */}
                    <p className="text-xs text-gray-500">
                      {new Date(root.created_at).toLocaleString()}
                      {root.overall_weighted_confidence !== null &&
                        root.overall_weighted_confidence !== undefined && (
                          <span className="ml-2">
                            • Confidence: {(root.overall_weighted_confidence * 100).toFixed(0)}%
                          </span>
                        )}
                    </p>
                  </div>

                  {/* Selection indicator */}
                  {selectedRunId === root.run_id && (
                    <svg
                      className="h-5 w-5 text-blue-600"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                </div>
              </button>

              {/* Child revisions */}
              {children.length > 0 && (
                <div className="border-t border-gray-200 bg-gray-50 px-4 py-2">
                  <p className="mb-2 text-xs font-semibold text-gray-700">
                    Revisions ({children.length})
                  </p>
                  <ul className="space-y-2">
                    {children.map((child, idx) => (
                      <li key={child.run_id}>
                        <button
                          type="button"
                          onClick={() => handleSelectRun(child.run_id)}
                          className={`w-full rounded-md border border-gray-200 p-2 text-left transition-colors hover:bg-white ${
                            selectedRunId === child.run_id
                              ? 'bg-blue-50 ring-2 ring-blue-500'
                              : 'bg-white'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0 flex-1">
                              <div className="mb-1 flex items-center gap-2">
                                <span className="text-xs font-medium text-gray-700">
                                  v{idx + 2}
                                </span>
                                <span
                                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${getStatusColor(child.status)}`}
                                >
                                  {child.status}
                                </span>
                                {child.decision_label && (
                                  <span
                                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${getDecisionColor(child.decision_label)}`}
                                  >
                                    {child.decision_label}
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-gray-600">
                                {new Date(child.created_at).toLocaleString()}
                              </p>
                            </div>
                            {selectedRunId === child.run_id && (
                              <svg
                                className="h-4 w-4 text-blue-600"
                                fill="currentColor"
                                viewBox="0 0 20 20"
                              >
                                <path
                                  fillRule="evenodd"
                                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                  clipRule="evenodd"
                                />
                              </svg>
                            )}
                          </div>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}

          {/* Load more button */}
          {hasMore && (
            <button
              type="button"
              onClick={onLoadMore}
              disabled={isLoading}
              className="w-full rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
            >
              {isLoading ? 'Loading...' : 'Load More'}
            </button>
          )}
        </>
      )}
    </div>
  );
}
