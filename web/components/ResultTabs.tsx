"use client";

import { useState } from "react";
import type { AgentRun } from "@/lib/types";
import Markdown from "./Markdown";
import CopyButton from "./CopyButton";

const TABS = [
  "Recommendation",
  "Evidence Map",
  "Tailored Resume",
  "Cover Letter",
  "Interview Strategy",
  "Agent Trace",
] as const;

function List({ items }: { items: string[] }) {
  return (
    <ul style={{ margin: 0, paddingLeft: 20 }}>
      {items.map((item, i) => (
        <li key={i} style={{ marginBottom: 6, color: "var(--text-2)", fontSize: "0.9rem" }}>
          {item}
        </li>
      ))}
    </ul>
  );
}

function NotGenerated({ verdict }: { verdict: string }) {
  return (
    <div className="notice">
      No application materials were generated for this run. The verdict was{" "}
      <strong>{verdict}</strong>, and on a SKIP the CLI asks before generating anything —
      defaulting to no. Spending six model calls on a role the agent just advised against
      would be the wrong default.
    </div>
  );
}

export default function ResultTabs({ run }: { run: AgentRun }) {
  const [tab, setTab] = useState<(typeof TABS)[number]>("Recommendation");

  return (
    <div>
      <div className="tabs" role="tablist">
        {TABS.map((name) => (
          <button
            key={name}
            role="tab"
            className="tab"
            aria-selected={tab === name}
            onClick={() => setTab(name)}
          >
            {name}
          </button>
        ))}
      </div>

      <div className="panel" role="tabpanel">
        {tab === "Recommendation" && (
          <>
            <div className="verdict-row" style={{ marginBottom: 18 }}>
              <span className={`verdict ${run.recommendation}`}>{run.recommendation}</span>
              <span className="muted">
                {run.metrics.searches} search{run.metrics.searches === 1 ? "" : "es"} ·{" "}
                {run.metrics.agent_turns} agent turn{run.metrics.agent_turns === 1 ? "" : "s"}
              </span>
            </div>
            <p style={{ maxWidth: "72ch", color: "var(--text-2)" }}>{run.reasoning}</p>
            {run.recommendation_note && <div className="notice">{run.recommendation_note}</div>}
            <div className="grid2" style={{ marginTop: 22 }}>
              <div className="card">
                <h4>Top strengths</h4>
                <List items={run.strengths} />
              </div>
              <div className="card">
                <h4>Main concerns</h4>
                <List items={run.concerns} />
              </div>
            </div>
            <div className="card">
              <h4>Research performed</h4>
              <p style={{ margin: 0, fontSize: "0.9rem", color: "var(--text-2)" }}>
                {run.research_summary}
              </p>
            </div>
          </>
        )}

        {tab === "Evidence Map" && (
          <>
            <p className="lede">
              Built before any prose is written. Asking for a resume directly produces keyword
              stuffing; asking first which requirement each experience answers, and how strongly,
              forces the selection to be justified.
            </p>
            <div className="tablewrap">
              <table>
                <thead>
                  <tr>
                    <th>Requirement</th>
                    <th>Priority</th>
                    <th>Evidence</th>
                    <th>Source</th>
                    <th>Metric</th>
                    <th>Strength</th>
                    <th>Gap</th>
                  </tr>
                </thead>
                <tbody>
                  {run.evidence_map.map((row, i) => (
                    <tr key={i}>
                      <td style={{ fontWeight: 500 }}>{row.requirement}</td>
                      <td><span className={`pill ${row.priority}`}>{row.priority}</span></td>
                      <td style={{ color: "var(--text-2)" }}>{row.evidence}</td>
                      <td style={{ color: "var(--text-3)", fontSize: "0.8rem" }}>{row.source}</td>
                      <td style={{ color: "var(--text-2)", fontSize: "0.8rem" }}>{row.metric}</td>
                      <td><span className={`pill ${row.strength}`}>{row.strength}</span></td>
                      <td style={{ color: "var(--text-3)", fontSize: "0.8rem" }}>{row.gap}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {tab === "Tailored Resume" && (
          <>
            {run.resume ? (
              <>
                <div className="doc-head">
                  <span className="muted">
                    Generated for this role. Every claim traced to the experience bank.
                  </span>
                  <CopyButton text={run.resume} />
                </div>
                <div className="doc">
                  <Markdown source={run.resume} />
                </div>
                {run.factuality_review && (
                  <div className="card" style={{ marginTop: 18 }}>
                    <h4>
                      <span className="tag eval">Factuality gate</span>{" "}
                      <span style={{ marginLeft: 8 }}>
                        {run.factuality_review.claims_checked} claims checked
                      </span>
                    </h4>
                    <p style={{ fontSize: "0.87rem", color: "var(--text-2)", margin: "8px 0 12px" }}>
                      {run.factuality_review.supported} supported ·{" "}
                      {run.factuality_review.partially_supported} partially supported ·{" "}
                      {run.factuality_review.unsupported} unsupported. A separate model call
                      reviews the draft against the experience bank; Python — not the model —
                      reads the verdict and forces a revision pass if anything failed.
                    </p>
                    {run.factuality_review.required_fixes.length > 0 ? (
                      run.factuality_review.required_fixes.map((fix, i) => (
                        <div key={i} className="card" style={{ background: "var(--surface-2)" }}>
                          <div style={{ fontSize: "0.87rem", marginBottom: 6 }}>
                            <span className="pill PARTIAL">{fix.verdict}</span>{" "}
                            <span style={{ marginLeft: 6 }}>{fix.claim}</span>
                          </div>
                          <div className="muted">{fix.basis}</div>
                          <div style={{ fontSize: "0.85rem", color: "var(--apply)", marginTop: 6 }}>
                            {fix.action}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="muted">No fixes required — every claim was supported.</div>
                    )}
                  </div>
                )}
              </>
            ) : (
              <NotGenerated verdict={run.recommendation} />
            )}
          </>
        )}

        {tab === "Cover Letter" && (
          <>
            {run.cover_letter ? (
              <>
                <div className="doc-head">
                  <span className="muted">Under 400 words. No generic enthusiasm.</span>
                  <CopyButton text={run.cover_letter} />
                </div>
                <div className="doc">
                  {run.cover_letter.split("\n\n").map((para, i) => (
                    <p key={i}>{para}</p>
                  ))}
                </div>
              </>
            ) : (
              <NotGenerated verdict={run.recommendation} />
            )}
          </>
        )}

        {tab === "Interview Strategy" && (
          <>
            {run.strategy ? (
              <>
                <div className="grid2">
                  <div className="card">
                    <h4>Strongest fit areas</h4>
                    <List items={run.strategy.fit_areas} />
                  </div>
                  <div className="card">
                    <h4>Gaps</h4>
                    <List items={run.strategy.gaps} />
                  </div>
                  <div className="card">
                    <h4>What to emphasize</h4>
                    <List items={run.strategy.emphasize} />
                  </div>
                  <div className="card">
                    <h4>What not to emphasize</h4>
                    <List items={run.strategy.avoid} />
                  </div>
                </div>
                <h3>Likely questions, and the story to answer with</h3>
                <div className="tablewrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Likely question</th>
                        <th>Best experience to use</th>
                      </tr>
                    </thead>
                    <tbody>
                      {run.strategy.questions.map((q, i) => (
                        <tr key={i}>
                          <td style={{ fontWeight: 500 }}>{q.question}</td>
                          <td style={{ color: "var(--text-2)" }}>{q.story}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <NotGenerated verdict={run.recommendation} />
            )}
          </>
        )}

        {tab === "Agent Trace" && (
          <>
            <div className="grid2">
              <div className="card">
                <h4><span className="tag model">Model controlled</span></h4>
                <List
                  items={[
                    "Whether external research was needed at all",
                    "Which query to issue",
                    "Whether the first result was enough or another search was warranted",
                    "Which uncertainties actually matter to the decision",
                    "The final APPLY / MAYBE / SKIP judgement",
                  ]}
                />
              </div>
              <div className="card">
                <h4><span className="tag flow">Software controlled</span></h4>
                <List
                  items={[
                    "Maximum number of searches (hard ceiling of 3 in the CLI, 2 in live demo mode)",
                    "Loop termination — bounded in Python, not requested in the prompt",
                    "Which output stages must run, and in what order",
                    "The factuality gate: whether a revision pass is forced",
                    "API credential handling — server-side only",
                    "Error handling and graceful failure",
                  ]}
                />
              </div>
            </div>

            <h3>Tool-call sequence from this run</h3>
            <div className="card" style={{ fontFamily: "var(--mono)", fontSize: "0.82rem" }}>
              {(() => {
                let turn = 1;
                const lines: string[] = [];
                for (const step of run.agent_trace) {
                  if (step.type === "tool_call") {
                    lines.push(`Agent turn ${turn}\n  → requested ${step.tool}("${step.input.query}")`);
                    turn += 1;
                  } else if (step.type === "tool_result") {
                    lines.push(`Tool result\n  → ${step.summary.slice(0, 120)}${step.summary.length > 120 ? "…" : ""}`);
                  } else if (step.type === "recommendation") {
                    lines.push(`Agent turn ${turn}\n  → end_turn (${step.message})`);
                  }
                }
                if (lines.length === 1) {
                  lines.unshift("No tool calls. The model judged that research could not change the answer.");
                }
                return lines.map((line, i) => (
                  <div key={i} style={{ whiteSpace: "pre-wrap", marginBottom: 10, color: "var(--text-2)" }}>
                    {line}
                  </div>
                ));
              })()}
            </div>

            <h3>Run metrics</h3>
            <dl className="kv">
              <dt>Searches</dt><dd>{run.metrics.searches}</dd>
              <dt>Tool calls</dt><dd>{run.metrics.tool_calls}</dd>
              <dt>Agent turns</dt><dd>{run.metrics.agent_turns}</dd>
              <dt>Agent input</dt><dd>{run.metrics.agent_input_tokens.toLocaleString()} tokens</dd>
              <dt>Agent output</dt><dd>{run.metrics.agent_output_tokens.toLocaleString()} tokens</dd>
              <dt>Generation calls</dt><dd>{run.metrics.generation_calls}</dd>
            </dl>
          </>
        )}
      </div>
    </div>
  );
}
