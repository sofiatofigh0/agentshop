import { NextResponse } from "next/server";

/**
 * Live mode endpoint.
 *
 * Everything that protects this route is implemented and enforced here,
 * server-side. The agent loop itself is not yet ported — see the TODO at the
 * bottom. Until it is, the route fails closed with a clear message rather than
 * pretending to run.
 *
 * SECURITY: ANTHROPIC_API_KEY is read only inside this file, which never runs
 * in the browser. It is not prefixed NEXT_PUBLIC_, so Next.js will not inline
 * it into the client bundle. It is never returned in a response and never
 * logged.
 */

export const runtime = "nodejs";

const LIVE_ENABLED = process.env.ENABLE_LIVE_DEMO === "true";
const MAX_JD_CHARS = Number(process.env.MAX_JD_CHARS ?? 12000);
const MAX_SEARCHES = Number(process.env.MAX_SEARCHES ?? 2);

/**
 * Best-effort per-IP throttle.
 *
 * TODO: this Map lives in the memory of one serverless instance. It resets on
 * cold start and is not shared between instances, so it slows casual abuse and
 * nothing more. Before enabling live mode on a public URL, replace it with a
 * durable store (Upstash Redis, Vercel KV) or put the route behind a
 * platform-level rate limiter. Do not mistake this for real protection.
 */
const RATE_LIMIT_WINDOW_MS = 60 * 60 * 1000;
const RATE_LIMIT_MAX = 5;
const hits = new Map<string, number[]>();

function rateLimited(ip: string): boolean {
  const now = Date.now();
  const recent = (hits.get(ip) ?? []).filter((t) => now - t < RATE_LIMIT_WINDOW_MS);
  recent.push(now);
  hits.set(ip, recent);
  return recent.length > RATE_LIMIT_MAX;
}

export async function POST(request: Request) {
  if (!LIVE_ENABLED) {
    return NextResponse.json(
      {
        error:
          "Live mode is disabled. This demo runs on prerecorded results so visitors never spend API credits. Set ENABLE_LIVE_DEMO=true with a server-side key to enable it.",
      },
      { status: 503 },
    );
  }

  if (!process.env.ANTHROPIC_API_KEY || !process.env.ANTHROPIC_MODEL) {
    // Note what is missing, never what the value is.
    return NextResponse.json(
      { error: "Live mode is enabled but the server is missing model credentials." },
      { status: 500 },
    );
  }

  const ip =
    request.headers.get("x-forwarded-for")?.split(",")[0].trim() ??
    request.headers.get("x-real-ip") ??
    "unknown";
  if (rateLimited(ip)) {
    return NextResponse.json(
      { error: "Rate limit reached. Try one of the example runs instead." },
      { status: 429 },
    );
  }

  let body: { job_description?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Malformed request." }, { status: 400 });
  }

  const jd = typeof body.job_description === "string" ? body.job_description.trim() : "";
  if (!jd) {
    return NextResponse.json({ error: "No job description given." }, { status: 400 });
  }
  if (jd.length > MAX_JD_CHARS) {
    return NextResponse.json(
      { error: `Job description is too long (limit ${MAX_JD_CHARS} characters).` },
      { status: 413 },
    );
  }

  // The visitor's job description is used for this request and then dropped.
  // Nothing here writes it to disk, a database, or a log.

  /**
   * TODO — port the agent loop.
   *
   * The Python CLI already implements this: call the model with the search_web
   * tool, check stop_reason for "tool_use", execute the tool, append the
   * tool_result, repeat until it stops, capped at MAX_SEARCHES. Two options:
   *
   *   1. Reimplement the loop here with @anthropic-ai/sdk, reading the
   *      sanitized data/portfolio_profile.json rather than the private bank.
   *   2. Deploy the Python side as a small service and proxy to it.
   *
   * Either way the response must be shaped exactly like AgentRun in lib/types
   * so the renderer needs no branching, and generation must stay capped —
   * six model calls per visitor is not a public endpoint.
   */
  void MAX_SEARCHES;

  return NextResponse.json(
    {
      error:
        "Live mode is switched on but the agent loop has not been ported to the web backend yet. The example runs show the full system.",
    },
    { status: 501 },
  );
}
