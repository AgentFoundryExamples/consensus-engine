/**
 * JsonToggle component for switching between formatted UI and raw JSON view
 * Allows power users to inspect the underlying data structure
 */

import { useState } from 'react';
import { sanitizeJsonForDisplay } from '../state/selectors';

export interface JsonToggleProps {
  /**
   * The data object to display as JSON
   */
  data: Record<string, unknown> | null;

  /**
   * Label for the toggle button
   */
  label?: string;

  /**
   * Optional CSS class name
   */
  className?: string;
}

/**
 * JsonToggle component that shows/hides raw JSON data
 */
export function JsonToggle({ data, label = 'Show Raw JSON', className = '' }: JsonToggleProps) {
  const [isJsonVisible, setIsJsonVisible] = useState(false);

  if (!data) {
    return null;
  }

  const sanitizedData = sanitizeJsonForDisplay(data);

  return (
    <div className={className}>
      <button
        type="button"
        onClick={() => setIsJsonVisible(!isJsonVisible)}
        className="inline-flex items-center gap-2 rounded-md bg-gray-100 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        aria-expanded={isJsonVisible}
        aria-controls="json-display"
      >
        <svg
          className={`h-4 w-4 transition-transform ${isJsonVisible ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
        {isJsonVisible ? 'Hide' : 'Show'} {label}
      </button>

      {isJsonVisible && (
        <div
          id="json-display"
          className="mt-4 max-h-96 overflow-auto rounded-md border border-gray-300 bg-gray-50 p-4"
          role="region"
          aria-label="Raw JSON data"
        >
          <pre className="text-xs text-gray-800">
            <code>{JSON.stringify(sanitizedData, null, 2)}</code>
          </pre>
        </div>
      )}
    </div>
  );
}
