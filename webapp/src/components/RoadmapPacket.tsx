/**
 * RoadmapPacket component for displaying completed run results
 * Shows summary, risks, next steps, acceptance criteria, and detailed views
 */

import { useState } from 'react';
import type { RunDetailResponse } from '../api/generated';
import {
  extractProposal,
  extractDecision,
  extractPersonaReviews,
  extractRoadmapSummary,
  extractRisks,
  extractNextSteps,
  extractAcceptanceCriteria,
} from '../state/selectors';
import { MinorityReport } from './MinorityReport';
import { PersonaReviewModal } from './PersonaReviewModal';
import { JsonToggle } from './JsonToggle';
import { RevisionModal } from './RevisionModal';
import { DiffView } from './DiffView';

export interface RoadmapPacketProps {
  /**
   * The completed run details
   */
  run: RunDetailResponse | null;

  /**
   * Optional CSS class name
   */
  className?: string;
}

/**
 * RoadmapPacket displays a comprehensive summary of the run results
 * Includes decision, risks, recommendations, and detailed views
 */
export function RoadmapPacket({ run, className = '' }: RoadmapPacketProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isRevisionModalOpen, setIsRevisionModalOpen] = useState(false);
  const [showDiff, setShowDiff] = useState(false);

  if (!run) {
    return (
      <div className={`rounded-lg border border-gray-200 bg-white p-6 ${className}`}>
        <p className="text-gray-500">No run data available</p>
      </div>
    );
  }

  // Check if run is completed
  if (run.status !== 'completed') {
    return (
      <div className={`rounded-lg border border-gray-200 bg-white p-6 ${className}`}>
        <p className="text-gray-500">
          Run is {run.status}. Roadmap packet will be available once the run completes.
        </p>
      </div>
    );
  }

  // Extract data
  const summary = extractRoadmapSummary(run);
  const decision = extractDecision(run);
  const proposal = extractProposal(run);
  const reviews = extractPersonaReviews(run);
  const risks = extractRisks(run);
  const nextSteps = extractNextSteps(run);
  const acceptanceCriteria = extractAcceptanceCriteria(run);

  // Categorize risks
  const blockingRisks = risks.filter((r) => r.isBlocking);
  const nonBlockingRisks = risks.filter((r) => !r.isBlocking);

  // Get decision badge color
  const getDecisionColor = (dec: string) => {
    switch (dec.toLowerCase()) {
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

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header Section */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow">
        <div className="mb-4 flex items-start justify-between">
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-gray-900">
              {summary?.title || 'Roadmap Packet'}
            </h2>
            <p className="mt-2 text-gray-600">{summary?.summary || 'Not provided yet'}</p>
          </div>
          {decision && (
            <span
              className={`ml-4 inline-flex items-center rounded-full px-4 py-2 text-sm font-semibold ${getDecisionColor(decision.decision)}`}
              role="status"
            >
              {decision.decision.toUpperCase()}
            </span>
          )}
        </div>

        {/* Confidence Score */}
        {decision && (
          <div className="mb-4">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-gray-700">Weighted Confidence</span>
              <span className="font-semibold text-gray-900">
                {(decision.weightedConfidence * 100).toFixed(0)}%
              </span>
            </div>
            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-gray-200">
              <div
                className="h-full bg-blue-600 transition-all"
                style={{ width: `${decision.weightedConfidence * 100}%` }}
                role="progressbar"
                aria-valuenow={decision.weightedConfidence * 100}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>
          </div>
        )}

        {/* Quick actions */}
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            View Detailed Proposal & Reviews
          </button>
          <button
            type="button"
            onClick={() => setIsRevisionModalOpen(true)}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Revise & Re-run
          </button>
          {run.parent_run_id && (
            <button
              type="button"
              onClick={() => setShowDiff(!showDiff)}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              {showDiff ? 'Hide Diff' : 'Compare with Parent'}
            </button>
          )}
        </div>
      </div>

      {/* Minority Report Section */}
      {decision?.minorityReports && decision.minorityReports.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-white p-6 shadow">
          <MinorityReport reports={decision.minorityReports} />
        </div>
      )}

      {/* Risks & Mitigations Section */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">Risks & Mitigations</h3>

        {blockingRisks.length > 0 && (
          <div className="mb-6">
            <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-red-800">
              <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
              Blocking Issues ({blockingRisks.length})
            </h4>
            <ul className="space-y-3">
              {blockingRisks.map((risk, idx) => (
                <li key={idx} className="rounded-md border-l-4 border-red-500 bg-red-50 p-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">{risk.concern}</p>
                      <p className="mt-1 text-xs text-gray-600">— {risk.personaName}</p>
                      {risk.mitigation && (
                        <p className="mt-2 text-sm italic text-gray-700">
                          Mitigation: {risk.mitigation}
                        </p>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {nonBlockingRisks.length > 0 && (
          <div>
            <h4 className="mb-3 text-sm font-semibold text-orange-800">
              Non-Blocking Concerns ({nonBlockingRisks.length})
            </h4>
            <ul className="space-y-2">
              {nonBlockingRisks.map((risk, idx) => (
                <li key={idx} className="rounded-md border-l-4 border-orange-300 bg-orange-50 p-3">
                  <p className="text-sm text-gray-900">{risk.concern}</p>
                  <p className="mt-1 text-xs text-gray-600">— {risk.personaName}</p>
                </li>
              ))}
            </ul>
          </div>
        )}

        {risks.length === 0 && (
          <p className="text-sm text-gray-500">No risks or concerns identified</p>
        )}
      </div>

      {/* Next Steps Section */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">Recommended Next Steps</h3>
        {nextSteps.length > 0 ? (
          <div className="space-y-4">
            {/* Group by persona for better organization */}
            {Object.entries(
              nextSteps.reduce(
                (acc, step) => {
                  if (!acc[step.personaName]) {
                    acc[step.personaName] = [];
                  }
                  acc[step.personaName].push(step.recommendation);
                  return acc;
                },
                {} as Record<string, string[]>
              )
            ).map(([personaName, recommendations]) => (
              <div key={personaName}>
                <h4 className="mb-2 text-sm font-semibold text-gray-700">{personaName}</h4>
                <ul className="list-inside list-disc space-y-1 text-sm text-gray-600">
                  {recommendations.map((rec, idx) => (
                    <li key={idx}>{rec}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">No recommendations provided</p>
        )}
      </div>

      {/* Acceptance Criteria / Implementation Notes */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">
          Acceptance Criteria & Implementation Notes
        </h3>
        {acceptanceCriteria.length > 0 ? (
          <ul className="list-inside list-disc space-y-2 text-sm text-gray-700">
            {acceptanceCriteria.map((criterion, idx) => (
              <li key={idx}>{criterion}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500">Not provided yet</p>
        )}

        {proposal && (
          <div className="mt-4 border-t border-gray-200 pt-4">
            <h4 className="mb-2 text-sm font-semibold text-gray-700">Proposal Scope</h4>
            <p className="mb-2 text-sm text-gray-600">
              <strong>Problem:</strong> {proposal.problemStatement}
            </p>
            <p className="text-sm text-gray-600">
              <strong>Solution:</strong> {proposal.proposedSolution}
            </p>
          </div>
        )}
      </div>

      {/* Optional JSON View */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow">
        <JsonToggle data={run} label="Raw Run Data" />
      </div>

      {/* Diff view (if comparing with parent) */}
      {showDiff && run.parent_run_id && (
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow">
          <DiffView runId={run.run_id} otherRunId={run.parent_run_id} />
        </div>
      )}

      {/* Modal for detailed view */}
      <PersonaReviewModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        proposal={proposal}
        reviews={reviews}
      />

      {/* Modal for creating revision */}
      <RevisionModal
        isOpen={isRevisionModalOpen}
        onClose={() => setIsRevisionModalOpen(false)}
        parentRun={run}
        onRevisionSubmitted={() => setIsRevisionModalOpen(false)}
      />
    </div>
  );
}
