// Copyright 2025 John Brosnihan
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
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
  run_type?: 'initial' | 'revision';
  parent_run_id?: string | null;
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

  // Helper functions for run relationships
  getChildRuns: (parent_run_id: string) => RunSummary[];
  getParentRun: (run_id: string) => RunSummary | null;
  getRunChain: (run_id: string) => RunSummary[];
}

export const useRunsStore = create<RunsState>((set, get) => ({
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

  getChildRuns: (parent_run_id) => {
    return get().runs.filter((run) => run.parent_run_id === parent_run_id);
  },

  getParentRun: (run_id) => {
    const runs = get().runs;
    const run = runs.find((r) => r.run_id === run_id);
    if (!run || !run.parent_run_id) return null;
    return runs.find((r) => r.run_id === run.parent_run_id) || null;
  },

  getRunChain: (run_id) => {
    const runs = get().runs;
    const chain: RunSummary[] = [];
    let current = runs.find((r) => r.run_id === run_id);

    // Walk up the chain to find the root
    while (current) {
      chain.unshift(current);
      if (!current.parent_run_id) break;
      current = runs.find((r) => r.run_id === current!.parent_run_id);
    }

    return chain;
  },
}));
