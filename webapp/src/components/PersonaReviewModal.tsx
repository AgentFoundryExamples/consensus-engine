/**
 * PersonaReviewModal component for displaying expanded proposal and persona reviews
 * Provides detailed view with keyboard focus trap and scrollable sections
 */

import { useEffect, useRef } from 'react';
import type { PersonaReview } from '../api/generated';
import type { ProposalData } from '../state/selectors';

export interface PersonaReviewModalProps {
  /**
   * Whether the modal is open
   */
  isOpen: boolean;

  /**
   * Callback to close the modal
   */
  onClose: () => void;

  /**
   * Proposal data to display
   */
  proposal: ProposalData | null;

  /**
   * Array of persona reviews
   */
  reviews: PersonaReview[];
}

/**
 * PersonaReviewModal displays expanded proposal and detailed persona reviews
 * Implements keyboard navigation and focus management
 */
export function PersonaReviewModal({
  isOpen,
  onClose,
  proposal,
  reviews,
}: PersonaReviewModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  });

  // Handle focus trap and escape key
  useEffect(() => {
    if (!isOpen) return;

    // Save the element that was focused before opening modal
    previousActiveElement.current = document.activeElement as HTMLElement;

    // Focus the close button when modal opens
    closeButtonRef.current?.focus();

    // Handle Escape key
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCloseRef.current();
      }
    };

    // Handle Tab key for focus trap
    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== 'Tab' || !modalRef.current) return;

      const focusableElements = modalRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );

      if (focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement?.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement?.focus();
      }
    };

    document.addEventListener('keydown', handleEscape);
    document.addEventListener('keydown', handleTab);

    // Prevent body scroll
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.removeEventListener('keydown', handleTab);
      document.body.style.overflow = '';

      // Restore focus to the triggering element
      previousActiveElement.current?.focus();
    };
  }, [isOpen]);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal content */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div ref={modalRef} className="relative w-full max-w-4xl rounded-lg bg-white shadow-xl">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
            <h2 id="modal-title" className="text-xl font-semibold text-gray-900">
              Detailed Proposal & Reviews
            </h2>
            <button
              ref={closeButtonRef}
              type="button"
              onClick={onClose}
              className="rounded-md text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Close modal"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* Scrollable content */}
          <div className="max-h-[70vh] overflow-y-auto px-6 py-4">
            {/* Proposal Section */}
            {proposal && (
              <section className="mb-8">
                <h3 className="mb-4 text-lg font-semibold text-gray-900">Expanded Proposal</h3>

                <div className="space-y-4">
                  <div>
                    <h4 className="mb-2 text-sm font-semibold text-gray-700">Title</h4>
                    <p className="text-sm text-gray-900">{proposal.title}</p>
                  </div>

                  <div>
                    <h4 className="mb-2 text-sm font-semibold text-gray-700">Summary</h4>
                    <p className="text-sm text-gray-700">{proposal.summary}</p>
                  </div>

                  <div>
                    <h4 className="mb-2 text-sm font-semibold text-gray-700">Problem Statement</h4>
                    <p className="text-sm text-gray-700">{proposal.problemStatement}</p>
                  </div>

                  <div>
                    <h4 className="mb-2 text-sm font-semibold text-gray-700">Proposed Solution</h4>
                    <p className="text-sm text-gray-700">{proposal.proposedSolution}</p>
                  </div>

                  {proposal.assumptions.length > 0 && (
                    <div>
                      <h4 className="mb-2 text-sm font-semibold text-gray-700">Assumptions</h4>
                      <ul className="list-inside list-disc space-y-1 text-sm text-gray-700">
                        {proposal.assumptions.map((assumption, idx) => (
                          <li key={idx}>{assumption}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {proposal.scopeNonGoals.length > 0 && (
                    <div>
                      <h4 className="mb-2 text-sm font-semibold text-gray-700">Out of Scope</h4>
                      <ul className="list-inside list-disc space-y-1 text-sm text-gray-700">
                        {proposal.scopeNonGoals.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {proposal.rawExpandedProposal && (
                    <div>
                      <h4 className="mb-2 text-sm font-semibold text-gray-700">
                        Full Proposal Text
                      </h4>
                      <p className="whitespace-pre-wrap text-sm text-gray-700">
                        {proposal.rawExpandedProposal}
                      </p>
                    </div>
                  )}
                </div>
              </section>
            )}

            {/* Persona Reviews Section */}
            {reviews.length > 0 && (
              <section>
                <h3 className="mb-4 text-lg font-semibold text-gray-900">Persona Reviews</h3>

                <div className="space-y-6">
                  {reviews.map((review, idx) => (
                    <details
                      key={`${review.persona_id}-${idx}`}
                      className="rounded-lg border border-gray-200 bg-gray-50"
                      open={idx === 0}
                    >
                      <summary className="cursor-pointer px-4 py-3 font-semibold text-gray-900 hover:bg-gray-100">
                        {review.persona_name} (Confidence:{' '}
                        {(review.confidence_score * 100).toFixed(0)}%)
                      </summary>

                      <div className="space-y-4 border-t border-gray-200 px-4 py-4">
                        {/* Strengths */}
                        {review.strengths.length > 0 && (
                          <div>
                            <h5 className="mb-2 text-sm font-semibold text-green-800">Strengths</h5>
                            <ul className="list-inside list-disc space-y-1 text-sm text-gray-700">
                              {review.strengths.map((strength, i) => (
                                <li key={i}>{strength}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Concerns */}
                        {review.concerns.length > 0 && (
                          <div>
                            <h5 className="mb-2 text-sm font-semibold text-orange-800">Concerns</h5>
                            <ul className="space-y-1 text-sm text-gray-700">
                              {review.concerns.map((concern, i) => (
                                <li key={i} className="flex items-start gap-2">
                                  {concern.is_blocking && (
                                    <span className="inline-block rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">
                                      BLOCKING
                                    </span>
                                  )}
                                  <span>{concern.text}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Blocking Issues */}
                        {review.blocking_issues.length > 0 && (
                          <div>
                            <h5 className="mb-2 text-sm font-semibold text-red-800">
                              Blocking Issues
                            </h5>
                            <ul className="space-y-1 text-sm text-gray-700">
                              {review.blocking_issues.map((issue, i) => (
                                <li key={i} className="flex items-start gap-2">
                                  {issue.security_critical && (
                                    <span className="inline-block rounded bg-red-600 px-2 py-0.5 text-xs font-medium text-white">
                                      SECURITY CRITICAL
                                    </span>
                                  )}
                                  <span>{issue.text}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Recommendations */}
                        {review.recommendations.length > 0 && (
                          <div>
                            <h5 className="mb-2 text-sm font-semibold text-blue-800">
                              Recommendations
                            </h5>
                            <ul className="list-inside list-disc space-y-1 text-sm text-gray-700">
                              {review.recommendations.map((rec, i) => (
                                <li key={i}>{rec}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Estimated Effort */}
                        <div>
                          <h5 className="mb-2 text-sm font-semibold text-gray-700">
                            Estimated Effort
                          </h5>
                          <p className="text-sm text-gray-700">
                            {typeof review.estimated_effort === 'string'
                              ? review.estimated_effort
                              : JSON.stringify(review.estimated_effort)}
                          </p>
                        </div>

                        {/* Dependency Risks */}
                        {review.dependency_risks.length > 0 && (
                          <div>
                            <h5 className="mb-2 text-sm font-semibold text-gray-700">
                              Dependency Risks
                            </h5>
                            <ul className="list-inside list-disc space-y-1 text-sm text-gray-700">
                              {review.dependency_risks.map((risk, i) => (
                                <li key={i}>
                                  {typeof risk === 'string' ? risk : JSON.stringify(risk)}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </details>
                  ))}
                </div>
              </section>
            )}

            {/* Empty state */}
            {!proposal && reviews.length === 0 && (
              <div className="py-12 text-center text-gray-500">
                <p>No detailed information available</p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-gray-200 px-6 py-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
