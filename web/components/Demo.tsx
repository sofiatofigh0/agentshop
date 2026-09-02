"use client";

import { useEffect, useRef, useState } from "react";
import type { AgentRun } from "@/lib/types";
import Timeline from "./Timeline";
import ResultTabs from "./ResultTabs";

/**
 * The interactive shell.
 *
 * In demo mode this makes no network request of any kind: the three runs are
 * imported at build time and replayed. The "Run Agent" button on a pasted job
 * description only reaches the API route when live mode is enabled server-side.
 */

const REVEAL_MS = 380;

export default function Demo({
  runs,
  liveEnabled,
}: {
  runs: AgentRun[];
  liveEnabled: boolean;
}) {
  const [jd, setJd] = useState("");
  const [run, setRun] = useState<AgentRun | null>(null);
  const [visible, setVisible] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const totalSteps = run ? run.agent_trace.length + run.workflow_trace.length : 0;

  // Reveal the trace one step at a time so the decision sequence is watchable.
  useEffect(() => {
    if (!run) return;
    if (timer.current) clearInterval(timer.current);
    timer.current = setInterval(() => {
      setVisible((v) => {
        if (v >= totalSteps) {
          if (timer.current) clearInterval(timer.current);
          return v;
        }
        return v + 1;
      });
    }, REVEAL_MS);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [run, totalSteps]);

  function replay(sample: AgentRun) {
    setError(null);
    setJd(sample.job.text);
    setVisible(0);
    setRun(sample);
  }

  async function runLive() {
    setError(null);
    if (!jd.trim()) {
      setError("Paste a job description first.");
      return;
    }
    if (!liveEnabled) {
      setError(
        "Live mode is off. This demo runs on prerecorded results so visitors never spend API credits — try one of the example runs below. To enable live runs, set ENABLE_LIVE_DEMO=true and provide a server-side API key.",
      );
      return;
    }
    setBusy(true);
    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_description: jd }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error ?? "The run failed.");
      } else {
        setVisible(0);
        setRun(data as AgentRun);
      }
    } catch {
      setError("Could not reach the server.");
    } finally {
      setBusy(false);
    }
  }

  const done = run !== null && visible >= totalSteps;

  return (
    <div>
      <label htmlFor="jd" style={{ display: "block", marginBottom: 8, fontSize: "0.9rem" }}>
        Paste a job description
      </label>
      <textarea
        id="jd"
        className="jd"
        value={jd}
        onChange={(e) => setJd(e.target.value)}
        placeholder="Paste the full job description here…"
        spellCheck={false}
      />

      <div className="controls">
        <button className="primary" onClick={runLive} disabled={busy}>
          {busy ? "Running…" : "Run Agent"}
        </button>
        <span className="muted" style={{ marginRight: 4 }}>Try a sample:</span>
        {runs.map((sample) => (
          <button key={sample.id} className="chip" onClick={() => replay(sample)}>
            {sample.recommendation} — {sample.job.company}
          </button>
        ))}
      </div>

      {error && <div className="notice">{error}</div>}

      {!liveEnabled && !error && (
        <div className="notice">
          <strong>Demo mode.</strong> The example runs below are prerecorded from real CLI runs
          and make zero API calls, so anyone can explore the system without spending credits.
          Employers in the sample job descriptions are fictional.
        </div>
      )}

      {run && (
        <div style={{ marginTop: 30 }}>
          <div className="phase-head" style={{ marginTop: 0 }}>
            <span className="tag eval">{run.label}</span>
            <span className="d">
              {run.job.title} · {run.job.company} · {run.job.location}
            </span>
          </div>

          <div className="trace-panel">
            <div className="trace-title">Execution trace</div>
            <p className="cap">
              Every step below the first heading was the model&rsquo;s choice. Every step below
              the second was fixed in code before the run started.
            </p>
            <Timeline run={run} visible={visible} />
          </div>

          {done && (
            <div className="results">
              <ResultTabs run={run} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
