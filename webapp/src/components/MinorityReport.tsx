/**
 * MinorityReport component for displaying dissenting opinions
 * Shows persona name, confidence score, concerns, and mitigation recommendations
 */

import type { MinorityReport as MinorityReportType } from '../api/generated';

export interface MinorityReportProps {
  /**
   * Array of minority reports from dissenting personas
   */
  reports: MinorityReportType[];

  /**
   * Optional CSS class name
   */
  className?: string;
}

/**
 * MinorityReport component that displays dissenting opinions with clear visual separation
 */
export function MinorityReport({ reports, className = '' }: MinorityReportProps) {
  if (!reports || reports.length === 0) {
    return null;
  }

  return (
    <div className={className}>
      <div className="mb-4 flex items-center gap-2">
        <span
          className="inline-flex items-center rounded-full bg-amber-100 px-3 py-1 text-sm font-medium text-amber-800"
          role="status"
          aria-label={`${reports.length} dissenting opinion${reports.length > 1 ? 's' : ''}`}
        >
          <svg
            className="mr-1.5 h-4 w-4"
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
          Dissenting Opinion{reports.length > 1 ? 's' : ''}
        </span>
        <h3 className="text-lg font-semibold text-gray-900">Minority Report</h3>
      </div>

      <div className="space-y-4">
        {reports.map((report, index) => (
          <div
            key={`${report.persona_id}-${index}`}
            className="rounded-lg border-2 border-amber-200 bg-amber-50 p-4"
          >
            {/* Persona Header */}
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h4 className="text-base font-semibold text-gray-900">{report.persona_name}</h4>
                <p className="text-sm text-gray-600">
                  Confidence: {(report.confidence_score * 100).toFixed(0)}%
                </p>
              </div>
            </div>

            {/* Blocking Summary */}
            <div className="mb-3">
              <h5 className="mb-1 text-sm font-semibold text-gray-900">Core Concerns</h5>
              <p className="text-sm text-gray-700">{report.blocking_summary}</p>
            </div>

            {/* Mitigation Recommendation */}
            {report.mitigation_recommendation && (
              <div className="mb-3">
                <h5 className="mb-1 text-sm font-semibold text-gray-900">Recommended Mitigation</h5>
                <p className="text-sm text-gray-700">{report.mitigation_recommendation}</p>
              </div>
            )}

            {/* Optional: Display strengths if available */}
            {report.strengths && report.strengths.length > 0 && (
              <div className="mb-3">
                <h5 className="mb-1 text-sm font-semibold text-gray-900">Acknowledged Strengths</h5>
                <ul className="list-inside list-disc space-y-1 text-sm text-gray-700">
                  {report.strengths.map((strength, idx) => (
                    <li key={idx}>{strength}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Optional: Display concerns if available */}
            {report.concerns && report.concerns.length > 0 && (
              <div>
                <h5 className="mb-1 text-sm font-semibold text-gray-900">Additional Concerns</h5>
                <ul className="list-inside list-disc space-y-1 text-sm text-gray-700">
                  {report.concerns.map((concern, idx) => (
                    <li key={idx}>{concern}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
