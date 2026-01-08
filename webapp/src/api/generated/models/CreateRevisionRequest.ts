/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request model for POST /v1/runs/{run_id}/revisions endpoint.
 *
 * Attributes:
 * edited_proposal: Full structured proposal object or text edits to apply
 * edit_notes: Optional notes about what was edited and why
 * input_idea: Optional new input idea text (overrides parent if provided)
 * extra_context: Optional new additional context (overrides parent if provided)
 * model: Optional new LLM model identifier (overrides parent if provided)
 * temperature: Optional new temperature parameter (overrides parent if provided)
 * parameters_json: Optional new LLM parameters (overrides parent if provided)
 */
export type CreateRevisionRequest = {
  /**
   * Edited proposal as structured JSON object or free-form text to merge with parent. If omitted, edit_notes is used to guide re-expansion.
   */
  edited_proposal?: Record<string, any> | string | null;
  /**
   * Optional notes about edits or guidance for re-expansion
   */
  edit_notes?: string | null;
  /**
   * Optional new input idea text (overrides parent)
   */
  input_idea?: string | null;
  /**
   * Optional new additional context (overrides parent)
   */
  extra_context?: Record<string, any> | string | null;
  /**
   * Optional new LLM model identifier (overrides parent)
   */
  model?: string | null;
  /**
   * Optional new temperature parameter (overrides parent)
   */
  temperature?: number | null;
  /**
   * Optional new LLM parameters (overrides parent)
   */
  parameters_json?: Record<string, any> | null;
};
