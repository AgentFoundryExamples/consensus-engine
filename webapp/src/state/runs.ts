/**
 * Zustand store for managing run history and active runs
 * Tracks submitted runs in the current session for timeline display and retry functionality
 */

import { create } from 'zustand';
import type { RunDetailResponse } from '../api/generated';

export interface RunSummary {
  run_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  created_at: string;
  input_idea: string;
  decision_label?: string | null;
  overall_weighted_confidence?: number | null;
  error_message?: string | null;
}

interface RunsState {
  // List of run summaries from this session
  runs: RunSummary[];

  // Currently active run being polled
  activeRunId: string | null;

  // Full details for the active run
  activeRunDetails: RunDetailResponse | null;

  // Actions
  addRun: (run: RunSummary) => void;
  updateRun: (run_id: string, updates: Partial<RunSummary>) => void;
  setActiveRun: (run_id: string | null) => void;
  setActiveRunDetails: (details: RunDetailResponse | null) => void;
  clearRuns: () => void;
}

export const useRunsStore = create<RunsState>((set) => ({
  runs: [],
  activeRunId: null,
  activeRunDetails: null,

  addRun: (run) =>
    set((state) => ({
      runs: [run, ...state.runs], // Add to beginning for newest-first ordering
    })),

  updateRun: (run_id, updates) =>
    set((state) => ({
      runs: state.runs.map((run) => (run.run_id === run_id ? { ...run, ...updates } : run)),
    })),

  setActiveRun: (run_id) =>
    set({
      activeRunId: run_id,
      activeRunDetails: null, // Clear stale details when switching runs
    }),

  setActiveRunDetails: (details) =>
    set({
      activeRunDetails: details,
    }),

  clearRuns: () =>
    set({
      runs: [],
      activeRunId: null,
      activeRunDetails: null,
    }),
}));
