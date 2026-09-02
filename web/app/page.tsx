import Demo from "@/components/Demo";
import { DEMO_RUNS, LIVE_ENABLED } from "@/lib/runs";

export default function Page() {
  return (
    <main>
      <div className="wrap">
        {/* ---------------- intro ---------------- */}
        <header className="hero">
          <h1>Job Opportunity Agent</h1>
          <p className="sub">
            A personalized agent that evaluates whether a role is worth pursuing, selectively
            researches missing information, and turns strong opportunities into an
            evidence-backed application package.
          </p>
          <span className="builtwith">
            Built with Claude, Python, tool use, web research, and evals
          </span>

          <div className="facts">
            <div className="fact">
              <span className="k">Agentic decisions</span>
              <span className="v">Selective research and the fit recommendation</span>
            </div>
            <div className="fact">
              <span className="k">Controlled workflow</span>
              <span className="v">Evidence map → resume → factuality → strategy</span>
            </div>
            <div className="fact">
              <span className="k">Evaluation</span>
              <span className="v">Outcome and trajectory evals</span>
            </div>
          </div>
        </header>

        {/* ---------------- why an agent ---------------- */}
        <section className="section">
          <h2>Why an agent?</h2>
          <p className="lede">
            A normal workflow could simply search the company every time, before every decision.
            That is simpler, and for most postings it is wasted work — the answer is already in
            the text.
          </p>
          <p className="lede">
            This system lets the model decide instead: whether outside information is necessary
            at all, what to retrieve, whether a second retrieval is useful, and when it has
            enough. That dynamic path is the agentic part. Once the recommendation exists, the
            application-generation steps are predictable, so they stay deterministic.
          </p>
          <div className="card">
            <h4>Design principle</h4>
            <p style={{ margin: 0, color: "var(--text-2)" }}>
              Use agency where judgment creates value. Keep predictable execution deterministic.
            </p>
          </div>
        </section>

        {/* ---------------- the demo ---------------- */}
        <section className="section">
          <h2>Try it</h2>
          <p className="lede">
            Three prerecorded runs. Watch the trace before reading the documents — the decision
            path is the interesting part.
          </p>
          <Demo runs={DEMO_RUNS} liveEnabled={LIVE_ENABLED} />
        </section>

        {/* ---------------- boundaries ---------------- */}
        <section className="section">
          <h2>Agent boundaries</h2>
          <p className="lede">
            The split that makes this safe to run unattended. Neither side can overrule the
            other.
          </p>
          <div className="bounds">
            <div>
              <h4><span className="tag model">Model controls</span></h4>
              <ul>
                <li>Whether research is needed</li>
                <li>The search query</li>
                <li>Whether to search again</li>
                <li>The final fit judgment</li>
              </ul>
            </div>
            <div>
              <h4><span className="tag flow">Software controls</span></h4>
              <ul>
                <li>Maximum tool calls</li>
                <li>Loop termination</li>
                <li>Which tools exist at all</li>
                <li>Required application stages</li>
                <li>The factuality gate</li>
                <li>Secrets and credentials</li>
              </ul>
            </div>
          </div>
        </section>

        {/* ---------------- how it works ---------------- */}
        <section className="section">
          <h2>How it works</h2>
          <p className="lede">
            A hybrid. The first half is an agent because the model chooses its own path through
            it. The second half is a workflow because the steps are fixed and the order is
            enforced in code.
          </p>

          <details className="box" open>
            <summary>Phase 1 — the agentic loop</summary>
            <div className="inner">
              <div className="flow">
                <span className="n">JOB DESCRIPTION</span>
                <br /><span className="arrow">↓</span><br />
                <span className="n">MODEL</span> <span className="arrow">reads it against the candidate profile</span>
                <br /><span className="arrow">↓</span><br />
                <span className="split">ENOUGH INFORMATION TO DECIDE?</span>
                <br /><span className="arrow">↓ no</span><br />
                <span className="n">TOOL USE</span> <span className="arrow">— the model writes its own query</span>
                <br /><span className="arrow">↓</span><br />
                <span className="n">OBSERVATION</span>
                <br /><span className="arrow">↓</span><br />
                <span className="n">MODEL REASSESSES</span> <span className="arrow">— search again, or stop</span>
                <br /><span className="arrow">↓</span><br />
                <span className="n">APPLY / MAYBE / SKIP</span>
              </div>
              <p style={{ fontSize: "0.88rem", color: "var(--text-2)", marginTop: 16, marginBottom: 0 }}>
                The loop reads <code>stop_reason</code>. If it is{" "}
                <code>&quot;tool_use&quot;</code>, Python runs whatever the model asked for,
                appends the result, and calls again. Nothing in the code decides how many
                searches happen — but the ceiling is enforced there, so &ldquo;cannot search
                forever&rdquo; is a guarantee rather than an instruction.
              </p>
            </div>
          </details>

          <details className="box">
            <summary>Phase 2 — the deterministic workflow</summary>
            <div className="inner">
              <div className="flow">
                <span className="n">EVIDENCE MAP</span> <span className="arrow">requirement → evidence, before any prose</span>
                <br /><span className="arrow">↓</span><br />
                <span className="n">RESUME</span> <span className="arrow">drafted from the map</span>
                <br /><span className="arrow">↓</span><br />
                <span className="n">FACTUALITY CHECK</span> <span className="arrow">separate call, separate prompt</span>
                <br /><span className="arrow">↓</span><br />
                <span className="n">REVISION</span> <span className="arrow">forced by Python if anything failed</span>
                <br /><span className="arrow">↓</span><br />
                <span className="n">COVER LETTER</span>
                <br /><span className="arrow">↓</span><br />
                <span className="n">INTERVIEW STRATEGY</span>
              </div>
              <p style={{ fontSize: "0.88rem", color: "var(--text-2)", marginTop: 16, marginBottom: 0 }}>
                The evidence map comes first deliberately. Asking for a resume directly produces
                keyword stuffing; asking first which requirement each experience answers, and how
                strongly, forces the selection to be justified before a word gets written.
              </p>
            </div>
          </details>

          <details className="box">
            <summary>Why the factuality check is its own step</summary>
            <div className="inner">
              <p style={{ fontSize: "0.9rem", color: "var(--text-2)", marginTop: 0 }}>
                A model asked to check its own draft tends to approve it. So the review is a
                separate call with a separate system prompt telling it plainly that it did not
                write this resume and has no stake in it. It labels every claim{" "}
                <strong>SUPPORTED</strong>, <strong>PARTIALLY SUPPORTED</strong> or{" "}
                <strong>UNSUPPORTED</strong> against the experience bank.
              </p>
              <p style={{ fontSize: "0.9rem", color: "var(--text-2)", marginBottom: 0 }}>
                Then plain Python reads the verdict and decides whether a revision pass runs. The
                writer never signs off on itself. Every claim in the bank also carries a
                provenance label, and anything unconfirmed can never reach a document at all.
              </p>
            </div>
          </details>
        </section>

        {/* ---------------- evals ---------------- */}
        <section className="section">
          <h2>How I evaluated it</h2>
          <p className="lede">
            Two things get scored, because a right answer reached the wrong way is still a broken
            agent. <strong>Outcome:</strong> was the recommendation correct?{" "}
            <strong>Trajectory:</strong> did it use tools appropriately — necessary searches
            made, unnecessary ones skipped?
          </p>

          <h3>One iteration, start to finish</h3>
          <ul className="walk">
            <li>
              <span className="k">Initial behavior</span>
              <span className="v">The agent searched whenever information was missing.</span>
            </li>
            <li>
              <span className="k bad">Problem</span>
              <span className="v">Unnecessary searches increased cost and added noise to the reasoning.</span>
            </li>
            <li>
              <span className="k">Change</span>
              <span className="v">Search only when external information could materially change the recommendation.</span>
            </li>
            <li>
              <span className="k bad">Over-correction</span>
              <span className="v">
                An added instruction to &ldquo;prefer answering with no searches at all&rdquo;
                caused the agent to stop using the tool entirely. Every fixture returned zero
                tool calls.
              </span>
            </li>
            <li>
              <span className="k good">Eval caught it</span>
              <span className="v">
                Verdict accuracy never moved, so outcome scoring alone would have missed this
                completely. Only the trajectory column showed the regression. Removed the
                overly strong instruction.
              </span>
            </li>
            <li>
              <span className="k good">Result</span>
              <span className="v">
                Selective research: obvious cases skip tools entirely; uncertainty with
                actionable external context triggers a search.
              </span>
            </li>
          </ul>

          <h3>Example results</h3>
          <div className="tablewrap">
            <table>
              <thead>
                <tr>
                  <th>Fixture</th><th>Expected</th><th>Actual</th><th>Outcome</th>
                  <th>Searches</th><th>Research useful?</th><th>Trajectory</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Strong fit, onsite in another city</td>
                  <td>SKIP</td><td>SKIP</td><td><span className="pill STRONG">PASS</span></td>
                  <td>2</td><td>yes</td><td><span className="pill STRONG">PASS</span></td>
                </tr>
                <tr>
                  <td>Ambiguous stealth posting</td>
                  <td>SKIP</td><td>SKIP</td><td><span className="pill STRONG">PASS</span></td>
                  <td>0</td><td>no</td><td><span className="pill STRONG">PASS</span></td>
                </tr>
                <tr>
                  <td>Poor fit, stated red flags</td>
                  <td>SKIP</td><td>SKIP</td><td><span className="pill STRONG">PASS</span></td>
                  <td>0</td><td>no</td><td><span className="pill STRONG">PASS</span></td>
                </tr>
                <tr>
                  <td>Strong fit, company unknown</td>
                  <td>APPLY</td><td>APPLY</td><td><span className="pill STRONG">PASS</span></td>
                  <td>2</td><td>yes</td><td><span className="pill STRONG">PASS</span></td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="muted" style={{ marginTop: 12 }}>
            Four fixtures, run by hand. A personal project — not production-scale evaluation, and
            far too small a sample to claim accuracy. Its value was catching specific
            regressions.
          </p>
        </section>

        {/* ---------------- schema lesson ---------------- */}
        <section className="section">
          <h2>The lesson that wasn&rsquo;t about prompting</h2>
          <p className="lede">
            An early profile schema represented hard constraints and strong preferences
            identically — one flat list. The model then rationally over-weighted the
            preferences, letting a single soft mismatch reject an otherwise excellent role.
          </p>
          <p className="lede">
            The instinct was to prompt around it. The actual fix was to redesign the schema so
            the two are separate structures with different weight, which improved the reasoning
            more than any prompt edit had.
          </p>
          <div className="card">
            <p style={{ margin: 0, color: "var(--text)" }}>
              Agent failures are not always model failures. They can be context, schema, tool,
              prompt, or eval failures — and it is worth knowing which one you have before
              rewriting the prompt.
            </p>
          </div>
        </section>

        {/* ---------------- limitations ---------------- */}
        <section className="section">
          <h2>Limitations</h2>
          <div className="grid2">
            <div>
              <ul style={{ paddingLeft: 20, color: "var(--text-2)", fontSize: "0.91rem", margin: 0 }}>
                <li style={{ marginBottom: 8 }}>Demo runs on this page are cached, not live.</li>
                <li style={{ marginBottom: 8 }}>The eval set is small and synthetic.</li>
                <li style={{ marginBottom: 8 }}>Tool-use behavior can vary between identical runs.</li>
                <li style={{ marginBottom: 8 }}>The full private candidate profile is not exposed here — the demo reads a sanitized public subset.</li>
                <li style={{ marginBottom: 8 }}>Live mode would require proper distributed rate limiting.</li>
                <li>Factuality review still uses an LLM. It is a second opinion, not a proof system.</li>
              </ul>
            </div>
            <div>
              <h4 style={{ marginTop: 0, fontSize: "0.74rem", fontFamily: "var(--mono)", letterSpacing: "0.1em", textTransform: "uppercase", color: "var(--text-3)" }}>
                Next steps
              </h4>
              <ul style={{ paddingLeft: 20, color: "var(--text-2)", fontSize: "0.91rem", margin: 0 }}>
                <li style={{ marginBottom: 8 }}>Evaluate against real application history</li>
                <li style={{ marginBottom: 8 }}>Measure user overrides of the recommendation</li>
                <li style={{ marginBottom: 8 }}>Add repeated-run stability evals</li>
                <li style={{ marginBottom: 8 }}>Retrieve only relevant experience instead of passing the full bank</li>
                <li style={{ marginBottom: 8 }}>Production-grade live rate limiting</li>
                <li>Track cost and latency per run</li>
              </ul>
            </div>
          </div>
        </section>

        <footer>
          Example runs are prerecorded from real CLI runs and edited for length. Companies in the
          sample job descriptions are fictional. This page reads a sanitized profile containing
          public professional history only.
        </footer>
      </div>
    </main>
  );
}
