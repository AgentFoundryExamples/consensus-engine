/**
 * Timeline component for visualizing pipeline step progress
 * Maps backend step states to visual badges and progress indicators
 * Provides accessible status text via aria-live regions
 */

import { useMemo } from 'react';
import { StatusBadge } from './ui';
import type { StepProgressSummary } from '../api/generated';

export interface TimelineProps {
  /**
   * Array of step progress from the API
   */
  steps: StepProgressSummary[];

  /**
   * Optional CSS class name
   */
  className?: string;
}

interface StepDisplay {
  name: string;
  label: string;
  description: string;
}

/**
 * Map step names to human-readable labels and descriptions
 */
const STEP_DISPLAY: Record<string, StepDisplay> = {
  expand: {
    name: 'expand',
    label: 'Expand',
    description: 'Transform idea into detailed proposal',
  },
  review_architect: {
    name: 'review_architect',
    label: 'Architect Review',
    description: 'System design and architecture analysis',
  },
  review_critic: {
    name: 'review_critic',
    label: 'Critic Review',
    description: 'Risk and edge case analysis',
  },
  review_optimist: {
    name: 'review_optimist',
    label: 'Optimist Review',
    description: 'Strengths and opportunities analysis',
  },
  review_security_guardian: {
    name: 'review_security_guardian',
    label: 'Security Review',
    description: 'Security vulnerabilities and data protection',
  },
  review_user_advocate: {
    name: 'review_user_advocate',
    label: 'User Advocate Review',
    description: 'Usability and user experience analysis',
  },
  aggregate_decision: {
    name: 'aggregate_decision',
    label: 'Decision',
    description: 'Aggregate reviews into final decision',
  },
};

/**
 * Get step display info with fallback for unknown steps
 */
function getStepDisplay(stepName: string): StepDisplay {
  return (
    STEP_DISPLAY[stepName] || {
      name: stepName,
      label: stepName,
      description: 'Processing step',
    }
  );
}

/**
 * Map step status to status badge variant
 */
function getStatusVariant(status: string): 'pending' | 'running' | 'completed' | 'failed' {
  switch (status) {
    case 'pending':
      return 'pending';
    case 'running':
      return 'running';
    case 'completed':
      return 'completed';
    case 'failed':
      return 'failed';
    default:
      return 'pending';
  }
}

/**
 * Calculate progress percentage for a step
 */
function calculateProgress(step: StepProgressSummary): number {
  if (step.status === 'completed') return 100;
  if (step.status === 'failed') return 100;
  if (step.status === 'running') return 50; // Arbitrary mid-point
  return 0;
}

export function Timeline({ steps, className = '' }: TimelineProps) {
  // Sort steps by step_order
  const sortedSteps = useMemo(() => {
    return [...steps].sort((a, b) => a.step_order - b.step_order);
  }, [steps]);

  // Generate aria-live announcement based on current state
  const announcement = useMemo(() => {
    const runningStep = sortedSteps.find((s) => s.status === 'running');
    if (runningStep) {
      const display = getStepDisplay(runningStep.step_name);
      return `Now processing: ${display.label}`;
    }

    const completedCount = sortedSteps.filter((s) => s.status === 'completed').length;
    const failedStep = sortedSteps.find((s) => s.status === 'failed');

    if (failedStep) {
      const display = getStepDisplay(failedStep.step_name);
      return `Pipeline failed at ${display.label}`;
    }

    if (completedCount === sortedSteps.length && sortedSteps.length > 0) {
      return 'Pipeline completed successfully';
    }

    return '';
  }, [sortedSteps]);

  if (sortedSteps.length === 0) {
    return (
      <div className={`rounded-lg border border-gray-200 bg-gray-50 p-6 ${className}`}>
        <p className="text-center text-sm text-gray-500">No pipeline steps to display</p>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`} role="region" aria-label="Pipeline progress">
      {/* Screen reader announcement */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {announcement}
      </div>

      {/* Step list */}
      <ol className="space-y-3">
        {sortedSteps.map((step, index) => {
          const display = getStepDisplay(step.step_name);
          const progress = calculateProgress(step);
          const isLast = index === sortedSteps.length - 1;

          return (
            <li key={step.step_name} className="relative">
              {/* Connector line */}
              {!isLast && (
                <div
                  className="absolute left-4 top-10 h-full w-0.5 bg-gray-200"
                  aria-hidden="true"
                />
              )}

              {/* Step card */}
              <div className="relative flex items-start gap-4">
                {/* Status indicator */}
                <div className="flex-shrink-0">
                  <div
                    className={`flex h-8 w-8 items-center justify-center rounded-full border-2 ${
                      step.status === 'completed'
                        ? 'border-green-500 bg-green-50'
                        : step.status === 'running'
                          ? 'animate-pulse border-blue-500 bg-blue-50'
                          : step.status === 'failed'
                            ? 'border-red-500 bg-red-50'
                            : 'border-gray-300 bg-white'
                    }`}
                    aria-hidden="true"
                  >
                    {step.status === 'completed' && (
                      <svg
                        className="h-4 w-4 text-green-600"
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
                    {step.status === 'failed' && (
                      <svg className="h-4 w-4 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                        <path
                          fillRule="evenodd"
                          d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                          clipRule="evenodd"
                        />
                      </svg>
                    )}
                    {step.status === 'running' && (
                      <div className="h-3 w-3 rounded-full bg-blue-600" />
                    )}
                  </div>
                </div>

                {/* Step content */}
                <div className="min-w-0 flex-1 pb-8">
                  <div className="flex items-center justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <h3 className="text-base font-medium text-gray-900">{display.label}</h3>
                      <p className="mt-0.5 text-sm text-gray-600">{display.description}</p>
                    </div>
                    <StatusBadge status={getStatusVariant(step.status)} />
                  </div>

                  {/* Progress bar for running steps */}
                  {step.status === 'running' && (
                    <div className="mt-2">
                      <div className="overflow-hidden rounded-full bg-gray-200">
                        <div
                          className="h-1.5 rounded-full bg-blue-600 transition-all duration-300"
                          style={{ width: `${progress}%` }}
                          role="progressbar"
                          aria-valuenow={progress}
                          aria-valuemin={0}
                          aria-valuemax={100}
                          aria-label={`${display.label} progress`}
                        />
                      </div>
                    </div>
                  )}

                  {/* Error message for failed steps */}
                  {step.status === 'failed' && step.error_message && (
                    <div className="mt-2 rounded-md bg-red-50 p-3" role="alert" aria-live="polite">
                      <p className="text-sm text-red-800">
                        <span className="font-medium">Error: </span>
                        {step.error_message}
                      </p>
                    </div>
                  )}

                  {/* Timestamps */}
                  {(step.started_at || step.completed_at) && (
                    <div className="mt-2 text-xs text-gray-500">
                      {step.started_at && (
                        <span>Started: {new Date(step.started_at).toLocaleTimeString()}</span>
                      )}
                      {step.started_at && step.completed_at && <span className="mx-2">•</span>}
                      {step.completed_at && (
                        <span>
                          {step.status === 'failed' ? 'Failed' : 'Completed'}:{' '}
                          {new Date(step.completed_at).toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
