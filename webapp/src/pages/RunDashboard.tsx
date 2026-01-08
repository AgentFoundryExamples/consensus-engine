/**
 * Main dashboard page for submitting ideas and tracking review progress
 * Integrates IdeaForm, Timeline, and polling to provide real-time feedback
 */

import { useState, useCallback, useEffect } from 'react';
import { Container } from '../components/layout';
import { Button } from '../components/ui';
import { IdeaForm } from '../components/IdeaForm';
import { Timeline } from '../components/Timeline';
import { useRunPolling } from '../hooks/useRunPolling';
import { useRunsStore } from '../state/runs';
import { FullReviewService } from '../api/client';

export function RunDashboard() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const {
    runs,
    activeRunId,
    activeRunDetails,
    addRun,
    updateRun,
    setActiveRun,
    setActiveRunDetails,
  } = useRunsStore();

  // Poll active run
  const { data: pollingData, error: pollingError } = useRunPolling(activeRunId, {
    initialInterval: 2000,
    maxInterval: 10000,
    useBackoff: true,
    onComplete: (data) => {
      // Update run in store when completed
      updateRun(data.run_id, {
        status: data.status as 'completed' | 'failed',
        decision_label: data.decision_label,
        overall_weighted_confidence: data.overall_weighted_confidence,
      });
    },
    onError: (error) => {
      setGlobalError(`Polling error: ${error.message}`);
    },
  });

  // Update active run details when polling returns new data
  useEffect(() => {
    if (pollingData) {
      setActiveRunDetails(pollingData);
    }
  }, [pollingData, setActiveRunDetails]);

  // Handle form submission
  const handleSubmit = useCallback(
    async (idea: string) => {
      setIsSubmitting(true);
      setSubmitError(null);
      setGlobalError(null);

      try {
        const response = await FullReviewService.fullReviewEndpointV1FullReviewPost({
          idea,
        });

        // Add run to store
        addRun({
          run_id: response.run_id,
          status: 'queued',
          created_at: response.created_at,
          input_idea: idea,
        });

        // Set as active run to start polling
        setActiveRun(response.run_id);
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Failed to submit idea';
        setSubmitError(message);
        setGlobalError(message);
      } finally {
        setIsSubmitting(false);
      }
    },
    [addRun, setActiveRun]
  );

  // Retry failed run
  const handleRetry = useCallback(
    (runId: string) => {
      const run = runs.find((r) => r.run_id === runId);
      if (run) {
        // Re-submit with the same idea
        handleSubmit(run.input_idea);
      }
    },
    [runs, handleSubmit]
  );

  // View a previous run
  const handleViewRun = useCallback(
    (runId: string) => {
      setActiveRun(runId);
    },
    [setActiveRun]
  );

  const hasActiveRun = activeRunId !== null;
  const showTimeline = activeRunDetails && activeRunDetails.step_progress;

  return (
    <Container className="py-8">
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Consensus Engine</h1>
          <p className="mt-2 text-lg text-gray-600">
            Submit your idea for comprehensive multi-persona review
          </p>
        </div>

        {/* Global error banner */}
        {globalError && (
          <div className="rounded-md bg-red-50 p-4" role="alert" aria-live="assertive">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg
                  className="h-5 w-5 text-red-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  aria-hidden="true"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <div className="mt-2 text-sm text-red-700">{globalError}</div>
              </div>
              <div className="ml-auto pl-3">
                <button
                  type="button"
                  onClick={() => setGlobalError(null)}
                  className="-mx-1.5 -my-1.5 inline-flex rounded-md bg-red-50 p-1.5 text-red-500 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2 focus:ring-offset-red-50"
                  aria-label="Dismiss error"
                >
                  <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Polling error banner */}
        {pollingError && !globalError && (
          <div className="rounded-md bg-yellow-50 p-4" role="alert" aria-live="polite">
            <div className="flex">
              <div className="flex-shrink-0">
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
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-yellow-800">Connection Issue</h3>
                <div className="mt-2 text-sm text-yellow-700">
                  {pollingError.message}. Retrying automatically...
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Main content grid */}
        <div className="grid gap-8 lg:grid-cols-2">
          {/* Left column: Form */}
          <div>
            <div className="rounded-lg bg-white p-6 shadow">
              <h2 className="mb-4 text-xl font-semibold text-gray-900">Submit Your Idea</h2>
              <IdeaForm onSubmit={handleSubmit} disabled={isSubmitting || hasActiveRun} />
              {submitError && (
                <div className="mt-4 rounded-md bg-red-50 p-3" role="alert">
                  <p className="text-sm text-red-800">{submitError}</p>
                </div>
              )}
            </div>

            {/* Run history */}
            {runs.length > 0 && (
              <div className="mt-6 rounded-lg bg-white p-6 shadow">
                <h3 className="mb-4 text-lg font-semibold text-gray-900">Recent Runs</h3>
                <ul className="space-y-3">
                  {runs.slice(0, 5).map((run) => (
                    <li
                      key={run.run_id}
                      className="flex items-center justify-between rounded-md border border-gray-200 p-3"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-gray-900">
                          {run.input_idea}
                        </p>
                        <p className="mt-1 text-xs text-gray-500">
                          {new Date(run.created_at).toLocaleString()} •{' '}
                          <span
                            className={
                              run.status === 'completed'
                                ? 'text-green-600'
                                : run.status === 'failed'
                                  ? 'text-red-600'
                                  : 'text-blue-600'
                            }
                          >
                            {run.status}
                          </span>
                          {run.decision_label && (
                            <>
                              {' '}
                              • <span className="capitalize">{run.decision_label}</span>
                            </>
                          )}
                        </p>
                      </div>
                      <div className="ml-4 flex gap-2">
                        {run.status === 'failed' && (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => handleRetry(run.run_id)}
                            disabled={hasActiveRun}
                            aria-label={`Retry run ${run.run_id}`}
                          >
                            Retry
                          </Button>
                        )}
                        {run.run_id !== activeRunId && (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => handleViewRun(run.run_id)}
                            aria-label={`View run ${run.run_id}`}
                          >
                            View
                          </Button>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Right column: Timeline */}
          <div>
            {showTimeline ? (
              <div className="rounded-lg bg-white p-6 shadow">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-xl font-semibold text-gray-900">Review Progress</h2>
                  {activeRunDetails.status === 'running' && (
                    <span className="inline-flex items-center gap-2 text-sm text-blue-600">
                      <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        />
                      </svg>
                      Processing...
                    </span>
                  )}
                </div>
                <Timeline steps={activeRunDetails.step_progress || []} />

                {/* Show decision when completed */}
                {activeRunDetails.status === 'completed' && activeRunDetails.decision && (
                  <div className="mt-6 rounded-lg bg-gray-50 p-4">
                    <h3 className="text-base font-semibold text-gray-900">Final Decision</h3>
                    <div className="mt-2 space-y-2">
                      <p className="text-sm">
                        <span className="font-medium">Result: </span>
                        <span
                          className={`capitalize ${
                            activeRunDetails.decision_label === 'approve'
                              ? 'text-green-600'
                              : activeRunDetails.decision_label === 'reject'
                                ? 'text-red-600'
                                : 'text-yellow-600'
                          }`}
                        >
                          {activeRunDetails.decision_label}
                        </span>
                      </p>
                      {activeRunDetails.overall_weighted_confidence !== null &&
                        activeRunDetails.overall_weighted_confidence !== undefined && (
                          <p className="text-sm">
                            <span className="font-medium">Confidence: </span>
                            {(activeRunDetails.overall_weighted_confidence * 100).toFixed(1)}%
                          </p>
                        )}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 p-12 text-center">
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
                <h3 className="mt-2 text-sm font-medium text-gray-900">No active review</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Submit an idea to see the review progress
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </Container>
  );
}
