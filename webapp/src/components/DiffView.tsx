/**
 * DiffView component for comparing two runs
 * Shows proposal changes, persona score deltas, and decision changes
 */

import { useState, useEffect } from 'react';
import { RunsService } from '../api/client';
import type { RunDiffResponse } from '../api/generated';

export interface DiffViewProps {
  /**
   * First run ID to compare
   */
  runId: string;

  /**
   * Second run ID to compare
   */
  otherRunId: string;

  /**
   * Optional CSS class name
   */
  className?: string;
}

/**
 * Displays a diff between two runs with proposal changes and score deltas
 */
export function DiffView({ runId, otherRunId, className = '' }: DiffViewProps) {
  const [diff, setDiff] = useState<RunDiffResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch diff on mount or when IDs change
  useEffect(() => {
    const fetchDiff = async () => {
      if (!runId || !otherRunId) return;

      setIsLoading(true);
      setError(null);

      try {
        const result = await RunsService.getRunDiffV1RunsRunIdDiffOtherRunIdGet(runId, otherRunId);
        setDiff(result);
      } catch (err) {
        const errorMessage =
          err instanceof Error
            ? err.message
            : 'Failed to load diff. The diff endpoint may not be available.';
        setError(errorMessage);
        setDiff(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDiff();
  }, [runId, otherRunId]);

  if (isLoading) {
    return (
      <div className={`rounded-lg border border-gray-200 bg-white p-6 ${className}`}>
        <div className="flex items-center justify-center">
          <div
            className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"
            role="status"
          >
            <span className="sr-only">Loading diff...</span>
          </div>
          <p className="ml-3 text-sm text-gray-600">Computing diff...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`rounded-lg border border-gray-200 bg-white p-6 ${className}`}>
        <div className="rounded-md bg-yellow-50 p-4">
          <div className="flex">
            <svg
              className="h-5 w-5 text-yellow-400"
              fill="currentColor"
              viewBox="0 0 20 20"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">Diff Not Available</h3>
              <div className="mt-2 text-sm text-yellow-700">
                <p>{error}</p>
                <p className="mt-2">
                  You can still view each run separately to compare them manually.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!diff) {
    return null;
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Metadata section */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">Comparison Metadata</h3>
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="font-medium text-gray-700">First Run</dt>
            <dd className="mt-1 text-gray-600">{diff.metadata.run_id}</dd>
          </div>
          <div>
            <dt className="font-medium text-gray-700">Second Run</dt>
            <dd className="mt-1 text-gray-600">{diff.metadata.other_run_id}</dd>
          </div>
          <div>
            <dt className="font-medium text-gray-700">First Run Created</dt>
            <dd className="mt-1 text-gray-600">
              {new Date(diff.metadata.run_created_at).toLocaleString()}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-gray-700">Second Run Created</dt>
            <dd className="mt-1 text-gray-600">
              {new Date(diff.metadata.other_run_created_at).toLocaleString()}
            </dd>
          </div>
          {diff.metadata.parent_child_relationship && (
            <div className="col-span-2">
              <dt className="font-medium text-gray-700">Relationship</dt>
              <dd className="mt-1 text-gray-600">{diff.metadata.parent_child_relationship}</dd>
            </div>
          )}
        </dl>
      </div>

      {/* Decision delta */}
      {diff.decision_delta && (
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">Decision Changes</h3>
          <div className="space-y-4">
            {/* Confidence change */}
            <div>
              <p className="text-sm font-medium text-gray-700">Weighted Confidence</p>
              <div className="mt-2 flex items-center gap-4">
                <div className="flex-1">
                  <p className="text-xs text-gray-600">Before</p>
                  <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-gray-200">
                    <div
                      className="h-full bg-blue-600"
                      style={{
                        width: `${(diff.decision_delta.old_confidence || 0) * 100}%`,
                      }}
                    />
                  </div>
                  <p className="mt-1 text-sm text-gray-900">
                    {((diff.decision_delta.old_confidence || 0) * 100).toFixed(1)}%
                  </p>
                </div>
                <svg className="h-5 w-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z"
                    clipRule="evenodd"
                  />
                </svg>
                <div className="flex-1">
                  <p className="text-xs text-gray-600">After</p>
                  <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-gray-200">
                    <div
                      className="h-full bg-green-600"
                      style={{
                        width: `${(diff.decision_delta.new_confidence || 0) * 100}%`,
                      }}
                    />
                  </div>
                  <p className="mt-1 text-sm text-gray-900">
                    {((diff.decision_delta.new_confidence || 0) * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
              {diff.decision_delta.confidence_delta !== undefined && (
                <p className="mt-2 text-sm text-gray-600">
                  Change:{' '}
                  <span
                    className={
                      diff.decision_delta.confidence_delta > 0 ? 'text-green-600' : 'text-red-600'
                    }
                  >
                    {diff.decision_delta.confidence_delta > 0 ? '+' : ''}
                    {(diff.decision_delta.confidence_delta * 100).toFixed(1)}%
                  </span>
                </p>
              )}
            </div>

            {/* Decision label change */}
            {diff.decision_delta.old_decision && diff.decision_delta.new_decision && (
              <div>
                <p className="text-sm font-medium text-gray-700">Decision</p>
                <div className="mt-2 flex items-center gap-4">
                  <span className="inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-sm font-medium capitalize text-gray-800">
                    {diff.decision_delta.old_decision}
                  </span>
                  <svg className="h-5 w-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span className="inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-sm font-medium capitalize text-gray-800">
                    {diff.decision_delta.new_decision}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Persona deltas */}
      {diff.persona_deltas && diff.persona_deltas.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">Persona Score Changes</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Persona
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Before
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    After
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    Change
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {diff.persona_deltas.map((delta, idx) => (
                  <tr key={idx}>
                    <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                      {delta.persona_name || delta.persona_id}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                      {((delta.old_confidence || 0) * 100).toFixed(1)}%
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-600">
                      {((delta.new_confidence || 0) * 100).toFixed(1)}%
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-sm">
                      <span
                        className={
                          (delta.confidence_delta || 0) > 0 ? 'text-green-600' : 'text-red-600'
                        }
                      >
                        {(delta.confidence_delta || 0) > 0 ? '+' : ''}
                        {((delta.confidence_delta || 0) * 100).toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Proposal changes */}
      {diff.proposal_changes && Object.keys(diff.proposal_changes).length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">Proposal Changes</h3>
          <div className="space-y-4">
            {Object.entries(diff.proposal_changes).map(
              ([section, change]: [string, Record<string, unknown>]) => {
                const changeData = change as { status?: string; diff?: string };
                return (
                  <div key={section} className="border-l-4 border-blue-500 pl-4">
                    <h4 className="text-sm font-semibold capitalize text-gray-900">
                      {section.replace(/_/g, ' ')}
                    </h4>
                    <p className="mt-1 text-xs text-gray-600">
                      Status: {changeData.status || 'unknown'}
                    </p>
                    {changeData.diff && (
                      <pre className="mt-2 overflow-x-auto rounded bg-gray-100 p-3 font-mono text-xs">
                        {changeData.diff}
                      </pre>
                    )}
                  </div>
                );
              }
            )}
          </div>
        </div>
      )}
    </div>
  );
}
