/**
 * RevisionModal component for editing and resubmitting proposals
 * Allows users to revise completed proposals and spawn new runs
 */

import { useState, useEffect, useCallback } from 'react';
import { RunsService } from '../api/client';
import type { RunDetailResponse, CreateRevisionRequest } from '../api/generated';
import { useRunsStore } from '../state/runs';

export interface RevisionModalProps {
  /**
   * Whether the modal is open
   */
  isOpen: boolean;

  /**
   * Callback when modal should close
   */
  onClose: () => void;

  /**
   * The parent run to revise
   */
  parentRun: RunDetailResponse | null;

  /**
   * Callback when revision is successfully submitted
   */
  onRevisionSubmitted?: (revisionRunId: string) => void;
}

/**
 * Modal for creating a revision of an existing run
 * Pre-fills form with parent run's proposal data
 */
export function RevisionModal({
  isOpen,
  onClose,
  parentRun,
  onRevisionSubmitted,
}: RevisionModalProps) {
  const [editedProposal, setEditedProposal] = useState('');
  const [editNotes, setEditNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { addRun, setActiveRun } = useRunsStore();

  // Pre-fill form when parent run changes
  useEffect(() => {
    if (isOpen && parentRun?.proposal) {
      // Extract proposal text from structured proposal
      const proposal = parentRun.proposal;
      const proposalText = `# ${proposal.title || 'Proposal'}

${proposal.summary || ''}

## Problem Statement
${proposal.problem_statement || ''}

## Proposed Solution
${proposal.proposed_solution || ''}

## Assumptions
${proposal.assumptions?.join('\n- ') || 'None'}

## Scope / Non-Goals
${proposal.scope_non_goals?.join('\n- ') || 'None'}
`;
      setEditedProposal(proposalText);
      setEditNotes('');
      setError(null);
    }
  }, [isOpen, parentRun]);

  // Handle modal close
  const handleClose = useCallback(() => {
    if (!isSubmitting) {
      onClose();
    }
  }, [isSubmitting, onClose]);

  // Handle form submission
  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      if (!parentRun) return;

      // Validate input
      if (!editedProposal.trim() && !editNotes.trim()) {
        setError('Please provide either edited proposal text or edit notes');
        return;
      }

      setIsSubmitting(true);
      setError(null);

      try {
        const requestBody: CreateRevisionRequest = {
          edited_proposal: editedProposal.trim() || null,
          edit_notes: editNotes.trim() || null,
        };

        const response = await RunsService.createRevisionV1RunsRunIdRevisionsPost(
          parentRun.run_id,
          requestBody
        );

        // Add revision run to store
        addRun({
          run_id: response.run_id,
          status: 'queued',
          created_at: response.created_at,
          input_idea: `Revision of: ${parentRun.input_idea}`,
          run_type: 'revision',
          parent_run_id: parentRun.run_id,
        });

        // Set as active run to start polling
        setActiveRun(response.run_id);

        // Notify parent
        onRevisionSubmitted?.(response.run_id);

        // Close modal
        handleClose();
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to create revision. Please try again.';
        setError(errorMessage);
      } finally {
        setIsSubmitting(false);
      }
    },
    [parentRun, editedProposal, editNotes, addRun, setActiveRun, onRevisionSubmitted, handleClose]
  );

  // Don't render if not open
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black bg-opacity-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="revision-modal-title"
      onClick={handleClose}
    >
      <div
        className="relative w-full max-w-4xl rounded-lg bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 id="revision-modal-title" className="text-xl font-semibold text-gray-900">
            Revise & Re-run Proposal
          </h2>
          <button
            type="button"
            onClick={handleClose}
            disabled={isSubmitting}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
            aria-label="Close modal"
          >
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-4">
          {/* Error banner */}
          {error && (
            <div className="mb-4 rounded-md bg-red-50 p-4" role="alert">
              <div className="flex">
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
                <div className="ml-3">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Parent run info */}
          {parentRun && (
            <div className="mb-4 rounded-md bg-blue-50 p-4">
              <p className="text-sm text-blue-800">
                <strong>Revising:</strong> {parentRun.input_idea}
              </p>
              <p className="mt-1 text-xs text-blue-600">
                Created: {new Date(parentRun.created_at).toLocaleString()}
                {parentRun.decision_label && (
                  <span className="ml-2 capitalize">• Decision: {parentRun.decision_label}</span>
                )}
              </p>
            </div>
          )}

          {/* Edited proposal field */}
          <div className="mb-4">
            <label
              htmlFor="editedProposal"
              className="mb-2 block text-sm font-medium text-gray-700"
            >
              Edited Proposal Text
              <span className="ml-1 text-xs text-gray-500">(or leave for LLM re-expansion)</span>
            </label>
            <textarea
              id="editedProposal"
              value={editedProposal}
              onChange={(e) => setEditedProposal(e.target.value)}
              rows={12}
              className="w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="Edit the proposal text above or clear it to let the LLM re-expand based on your notes..."
              disabled={isSubmitting}
            />
            <p className="mt-1 text-xs text-gray-500">
              {editedProposal.length.toLocaleString()} / 100,000 characters
            </p>
          </div>

          {/* Edit notes field */}
          <div className="mb-6">
            <label htmlFor="editNotes" className="mb-2 block text-sm font-medium text-gray-700">
              Edit Notes
              <span className="ml-1 text-xs text-gray-500">(optional)</span>
            </label>
            <textarea
              id="editNotes"
              value={editNotes}
              onChange={(e) => setEditNotes(e.target.value)}
              rows={4}
              className="w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="Describe what you changed and why. This helps track the evolution of ideas..."
              disabled={isSubmitting}
            />
            <p className="mt-1 text-xs text-gray-500">
              {editNotes.length.toLocaleString()} / 10,000 characters
            </p>
          </div>

          {/* Action buttons */}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              disabled={isSubmitting}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || (!editedProposal.trim() && !editNotes.trim())}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
            >
              {isSubmitting ? (
                <span className="flex items-center gap-2">
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
                  Submitting...
                </span>
              ) : (
                'Create Revision'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
