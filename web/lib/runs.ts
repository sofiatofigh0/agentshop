/**
 * Cached demo runs.
 *
 * These are prerecorded outputs from real CLI runs, edited for length and with
 * fictional employers in the job descriptions. Loading them makes ZERO API
 * calls — the whole demo works with no key configured, so a portfolio visitor
 * never spends anyone's credits.
 */

import apply from "@/data/run-apply.json";
import maybe from "@/data/run-maybe.json";
import skip from "@/data/run-skip.json";
import type { AgentRun } from "./types";

export const DEMO_RUNS: AgentRun[] = [apply, maybe, skip] as unknown as AgentRun[];

export const SAMPLES = DEMO_RUNS.map((run) => ({
  id: run.id,
  verdict: run.recommendation,
  company: run.job.company,
  title: run.job.title,
  text: run.job.text,
}));

export function findRun(id: string): AgentRun | undefined {
  return DEMO_RUNS.find((run) => run.id === id);
}

/** Live mode is off unless the server env var is exactly "true". */
export const LIVE_ENABLED = process.env.ENABLE_LIVE_DEMO === "true";
