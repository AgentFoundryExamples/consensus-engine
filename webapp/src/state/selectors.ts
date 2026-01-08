/**
 * Selectors and helper functions to extract structured data from run payloads
 * These functions handle optional fields and provide fallbacks for missing data
 */

import type {
  RunDetailResponse,
  PersonaReview,
  MinorityReport,
  DecisionAggregation,
} from '../api/generated';

/**
 * Extract proposal data from run details
 */
export interface ProposalData {
  title: string;
  summary: string;
  problemStatement: string;
  proposedSolution: string;
  assumptions: string[];
  scopeNonGoals: string[];
  rawExpandedProposal?: string;
}

export function extractProposal(run: RunDetailResponse | null): ProposalData | null {
  if (!run?.proposal) {
    return null;
  }

  const proposal = run.proposal;
  return {
    title: (proposal.title as string) || 'Untitled Proposal',
    summary: (proposal.summary as string) || 'No summary provided',
    problemStatement: (proposal.problem_statement as string) || 'Not provided',
    proposedSolution: (proposal.proposed_solution as string) || 'Not provided',
    assumptions: (proposal.assumptions as string[]) || [],
    scopeNonGoals: (proposal.scope_non_goals as string[]) || [],
    rawExpandedProposal: proposal.raw_expanded_proposal as string | undefined,
  };
}

/**
 * Extract decision data from run details
 */
export interface DecisionData {
  decision: string;
  weightedConfidence: number;
  hasMinorityReport: boolean;
  minorityReports: MinorityReport[];
}

export function extractDecision(run: RunDetailResponse | null): DecisionData | null {
  if (!run?.decision) {
    return null;
  }

  const decision = run.decision as DecisionAggregation;
  const minorityReports: MinorityReport[] = [];

  // Handle both single minority_report and array minority_reports
  if (decision.minority_report) {
    minorityReports.push(decision.minority_report);
  }
  if (decision.minority_reports) {
    minorityReports.push(...decision.minority_reports);
  }

  return {
    decision: decision.decision || 'unknown',
    weightedConfidence: decision.weighted_confidence ?? decision.overall_weighted_confidence ?? 0,
    hasMinorityReport: minorityReports.length > 0,
    minorityReports,
  };
}

/**
 * Extract persona reviews with full details
 * Note: RunDetailResponse only provides PersonaReviewSummary, not full PersonaReview
 * We construct a basic review structure from available summary data
 */
export function extractPersonaReviews(run: RunDetailResponse | null): PersonaReview[] {
  if (!run?.persona_reviews) {
    return [];
  }

  // Convert PersonaReviewSummary to basic PersonaReview structure
  // Full review details are not available in the API response
  return run.persona_reviews.map((summary) => {
    return {
      persona_name: summary.persona_name,
      persona_id: summary.persona_id,
      confidence_score: summary.confidence_score ?? 0,
      strengths: [],
      concerns: [],
      recommendations: [],
      blocking_issues: summary.blocking_issues_present
        ? [{ text: 'Blocking issues present (details not available in API)' }]
        : [],
      estimated_effort: 'Not available in summary',
      dependency_risks: [],
    } as PersonaReview;
  });
}

/**
 * Extract summary information for roadmap packet
 */
export interface RoadmapSummary {
  title: string;
  summary: string;
  decision: string;
  confidence: number;
  hasBlockingIssues: boolean;
  hasMinorityReport: boolean;
}

export function extractRoadmapSummary(run: RunDetailResponse | null): RoadmapSummary | null {
  if (!run) {
    return null;
  }

  const proposal = extractProposal(run);
  const decision = extractDecision(run);

  return {
    title: proposal?.title || run.input_idea,
    summary: proposal?.summary || 'No summary available',
    decision: decision?.decision || 'pending',
    confidence: decision?.weightedConfidence || 0,
    hasBlockingIssues: run.persona_reviews?.some((r) => r.blocking_issues_present) || false,
    hasMinorityReport: decision?.hasMinorityReport || false,
  };
}

/**
 * Extract risks and mitigations from persona reviews
 */
export interface RiskItem {
  personaName: string;
  personaId: string;
  concern: string;
  isBlocking: boolean;
  mitigation?: string;
}

export function extractRisks(run: RunDetailResponse | null): RiskItem[] {
  const reviews = extractPersonaReviews(run);
  const risks: RiskItem[] = [];

  reviews.forEach((review) => {
    // Add concerns as risks
    review.concerns.forEach((concern) => {
      risks.push({
        personaName: review.persona_name,
        personaId: review.persona_id,
        concern: concern.text,
        isBlocking: concern.is_blocking,
      });
    });

    // Add blocking issues as critical risks
    review.blocking_issues.forEach((issue) => {
      risks.push({
        personaName: review.persona_name,
        personaId: review.persona_id,
        concern: issue.text,
        isBlocking: true,
        mitigation: issue.security_critical
          ? 'Security critical - requires immediate attention'
          : undefined,
      });
    });
  });

  return risks;
}

/**
 * Extract next steps and recommendations from persona reviews
 */
export interface NextStep {
  personaName: string;
  personaId: string;
  recommendation: string;
}

export function extractNextSteps(run: RunDetailResponse | null): NextStep[] {
  const reviews = extractPersonaReviews(run);
  const steps: NextStep[] = [];

  reviews.forEach((review) => {
    review.recommendations.forEach((rec) => {
      steps.push({
        personaName: review.persona_name,
        personaId: review.persona_id,
        recommendation: rec,
      });
    });
  });

  return steps;
}

/**
 * Extract acceptance criteria from proposal and reviews
 */
export function extractAcceptanceCriteria(run: RunDetailResponse | null): string[] {
  const proposal = extractProposal(run);
  if (!proposal) {
    return [];
  }

  // For now, return scope/non-goals as implicit criteria
  // This could be enhanced to parse specific acceptance criteria from the proposal
  const criteria: string[] = [];

  if (proposal.assumptions.length > 0) {
    criteria.push(`Verify all assumptions: ${proposal.assumptions.join(', ')}`);
  }

  if (proposal.scopeNonGoals.length > 0) {
    criteria.push(
      `Ensure out-of-scope items are not included: ${proposal.scopeNonGoals.join(', ')}`
    );
  }

  return criteria;
}

/**
 * Sanitize JSON for display by removing sensitive fields
 */
export function sanitizeJsonForDisplay(
  obj: Record<string, unknown> | null
): Record<string, unknown> | null {
  if (!obj) {
    return null;
  }

  // Create a deep copy
  const sanitized = JSON.parse(JSON.stringify(obj)) as Record<string, unknown>;

  // List of keys to redact (case-insensitive patterns)
  const sensitiveKeys = ['token', 'key', 'secret', 'password', 'auth', 'credential'];

  function redactSensitiveFields(o: unknown): unknown {
    if (typeof o !== 'object' || o === null) {
      return o;
    }

    if (Array.isArray(o)) {
      return o.map(redactSensitiveFields);
    }

    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(o)) {
      const lowerKey = key.toLowerCase();
      if (sensitiveKeys.some((pattern) => lowerKey.includes(pattern))) {
        result[key] = '[REDACTED]';
      } else {
        result[key] = redactSensitiveFields(value);
      }
    }
    return result;
  }

  return redactSensitiveFields(sanitized) as Record<string, unknown>;
}
