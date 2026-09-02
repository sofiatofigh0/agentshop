"use client";

import type { AgentRun, TraceStep, WorkflowStage } from "@/lib/types";

/**
 * The execution timeline — the centrepiece of the demo.
 *
 * It renders two visually distinct phases from the same run object:
 *
 *   AGENTIC PHASE      every step here was the model's choice. Whether to
 *                      search, what to search for, whether to search again.
 *   DETERMINISTIC      every stage here runs in a fixed order regardless of
 *   PHASE              what the model would prefer. Python decides.
 *
 * `visible` lets the parent reveal steps one at a time so a visitor can watch
 * the decision sequence rather than being handed a finished wall of text.
 */

function StepRow({ step }: { step: TraceStep }) {
  if (step.type === "model_decision") {
    return (
      <li className="step is-model">
        <span className="tag model">Model decision</span>
        <div className="body">{step.message}</div>
      </li>
    );
  }
  if (step.type === "tool_call") {
    return (
      <li className="step is-tool">
        <span className="tag tool">Tool call</span>
        <code className="q">
          {step.tool}(&ldquo;{step.input.query}&rdquo;)
        </code>
      </li>
    );
  }
  if (step.type === "tool_result") {
    return (
      <li className="step is-obs">
        <span className="tag obs">Observation</span>
        <div className="body">{step.summary}</div>
      </li>
    );
  }
  return (
    <li className="step is-flow">
      <span className="tag flow">Recommendation</span>
      <div className="verdict-row">
        <span className={`verdict ${step.message}`}>{step.message}</span>
      </div>
    </li>
  );
}

function StageRow({ stage }: { stage: WorkflowStage }) {
  return (
    <li className="step is-flow">
      <span className="tag flow">Workflow</span>
      <div className="body">
        <strong style={{ color: "var(--text)" }}>{stage.stage}</strong> — {stage.detail}
      </div>
    </li>
  );
}

export default function Timeline({
  run,
  visible,
}: {
  run: AgentRun;
  visible: number;
}) {
  const agentSteps = run.agent_trace.slice(0, visible);
  const remaining = visible - run.agent_trace.length;
  const workflowSteps = remaining > 0 ? run.workflow_trace.slice(0, remaining) : [];
  const agentDone = visible >= run.agent_trace.length;

  return (
    <div>
      <div className="phase-head">
        <span className="t">Agentic phase</span>
        <span className="d">the model chooses the path</span>
      </div>
      <ul className="timeline">
        {agentSteps.map((step, i) => (
          <StepRow key={i} step={step} />
        ))}
      </ul>

      {agentDone && run.workflow_trace.length > 0 && (
        <>
          <div className="phase-head">
            <span className="t">Deterministic workflow</span>
            <span className="d">fixed order, enforced in Python</span>
          </div>
          <ul className="timeline">
            {workflowSteps.map((stage, i) => (
              <StageRow key={i} stage={stage} />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
