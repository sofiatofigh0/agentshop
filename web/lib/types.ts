/**
 * One agent run. Cached demo runs and live runs share this exact shape, so the
 * renderer never needs to know which it is looking at.
 */

export type Verdict = "APPLY" | "MAYBE" | "SKIP";

/** A step in the agentic phase. The model chose each of these. */
export type TraceStep =
  | { type: "model_decision"; message: string }
  | { type: "tool_call"; tool: string; input: { query: string } }
  | { type: "tool_result"; summary: string }
  | { type: "recommendation"; message: string };

/** A stage in the deterministic phase. Python chose each of these. */
export interface WorkflowStage {
  stage: string;
  detail: string;
}

export interface EvidenceRow {
  requirement: string;
  priority: "HIGH" | "MEDIUM" | "LOW";
  evidence: string;
  source: string;
  metric: string;
  strength: "STRONG" | "PARTIAL" | "NONE";
  gap: string;
}

export interface FactualityReview {
  claims_checked: number;
  supported: number;
  partially_supported: number;
  unsupported: number;
  required_fixes: { claim: string; verdict: string; basis: string; action: string }[];
  sample_supported: { claim: string; verdict: string; basis: string }[];
}

export interface Strategy {
  fit_areas: string[];
  gaps: string[];
  emphasize: string[];
  avoid: string[];
  questions: { question: string; story: string }[];
}

export interface AgentRun {
  id: string;
  label: string;
  mode: "cached" | "live";
  job: { company: string; title: string; location: string; text: string };
  recommendation: Verdict;
  recommendation_note?: string;
  reasoning: string;
  strengths: string[];
  concerns: string[];
  research_summary: string;
  agent_trace: TraceStep[];
  workflow_trace: WorkflowStage[];
  evidence_map: EvidenceRow[];
  resume: string | null;
  factuality_review: FactualityReview | null;
  cover_letter: string | null;
  strategy: Strategy | null;
  metrics: {
    searches: number;
    tool_calls: number;
    agent_turns: number;
    agent_input_tokens: number;
    agent_output_tokens: number;
    generation_calls: number;
  };
}
