import Demo from "@/components/Demo";
import { DEMO_RUNS, LIVE_ENABLED } from "@/lib/runs";

export default function Page() {
  return (
    <main>
      <div className="wrap">
        <header className="hero">
          <h1>Job Opportunity Agent</h1>
          <p className="sub">
            An agent that evaluates whether a role is worth pursuing, selectively researches
            missing information, and turns the candidate&rsquo;s experience into a tailored
            application package.
          </p>
          <span className="builtwith">
            Built with Claude, Python, tool use, web research, and evals
          </span>
        </header>

        <section className="section">
          <div className="grid2">
            <div>
              <h3 style={{ marginTop: 0 }}>Project goal</h3>
              <p className="lede" style={{ marginBottom: 0 }}>
                Explore how selective model autonomy can improve a real personal workflow.
              </p>
            </div>
            <div>
              <h3 style={{ marginTop: 0 }}>Design principle</h3>
              <p className="lede" style={{ marginBottom: 0 }}>
                Use agency only where dynamic judgment creates value; keep predictable steps
                deterministic.
              </p>
            </div>
          </div>
          <div className="card" style={{ marginTop: 22 }}>
            <h4>Key lesson</h4>
            <p style={{ margin: 0, color: "var(--text-2)" }}>
              The model should control judgment. Software should control the execution envelope.
            </p>
          </div>
        </section>

        <section className="section">
          <Demo runs={DEMO_RUNS} liveEnabled={LIVE_ENABLED} />
        </section>

        <section className="section">
          <h2>How it works</h2>
          <p className="lede">
            A hybrid of two different things. The first half is an agent because the model
            chooses its own path through it. The second half is a workflow because the steps are
            fixed and the order is enforced in code.
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
                <span className="n">TOOL USE</span> <span className="arrow">— model writes its own query</span>
                <br /><span className="arrow">↓</span><br />
                <span className="n">OBSERVATION</span>
                <br /><span className="arrow">↓</span><br />
                <span className="n">MODEL REASSESSES</span> <span className="arrow">— search again, or stop</span>
                <br /><span className="arrow">↓</span><br />
                <span className="n">APPLY / MAYBE / SKIP</span>
              </div>
              <p style={{ fontSize: "0.88rem", color: "var(--text-2)", marginTop: 16, marginBottom: 0 }}>
                Nothing in the code decides how many searches happen. The loop reads{" "}
                <code>stop_reason == &quot;tool_use&quot;</code>, runs whatever the model asked
                for, appends the result, and calls again. What Python does own is the ceiling:
                the loop is bounded, so &ldquo;cannot search forever&rdquo; is a guarantee rather
                than an instruction.
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
                separate call with a separate system prompt that tells it plainly that it did not
                write this resume and has no stake in it. It labels every claim{" "}
                <strong>SUPPORTED</strong>, <strong>PARTIALLY SUPPORTED</strong> or{" "}
                <strong>UNSUPPORTED</strong> against the experience bank.
              </p>
              <p style={{ fontSize: "0.9rem", color: "var(--text-2)", marginBottom: 0 }}>
                Then plain Python reads the verdict and decides whether a revision pass runs. The
                writer never signs off on itself. The bank also tags every claim with a
                provenance label, and anything marked <code>needs_validation</code> — a number
                that sounds plausible but has not been confirmed — can never reach a document at
                all.
              </p>
            </div>
          </details>
        </section>

        <section className="section">
          <h2>How I evaluated it</h2>
          <p className="lede">
            A small eval harness over four fixture job descriptions. It scores two different
            things, because a right answer reached the wrong way is still a broken agent.
          </p>

          <div className="grid2">
            <div className="card">
              <h4><span className="tag eval">Outcome quality</span></h4>
              <p style={{ fontSize: "0.89rem", color: "var(--text-2)", margin: "10px 0 0" }}>
                Did the agent return the right APPLY / MAYBE / SKIP for this candidate?
              </p>
            </div>
            <div className="card">
              <h4><span className="tag eval">Trajectory quality</span></h4>
              <p style={{ fontSize: "0.89rem", color: "var(--text-2)", margin: "10px 0 0" }}>
                Was research actually useful when it happened? Were there unnecessary searches?
                How many tool calls, how many tokens, and is the behavior stable across runs?
              </p>
            </div>
          </div>

          <h3>Example results</h3>
          <div className="tablewrap">
            <table>
              <thead>
                <tr>
                  <th>Fixture</th>
                  <th>Expected</th>
                  <th>Actual</th>
                  <th>Outcome</th>
                  <th>Searches</th>
                  <th>Research useful?</th>
                  <th>Trajectory</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Strong fit, onsite in another city</td>
                  <td>SKIP</td><td>SKIP</td>
                  <td><span className="pill STRONG">PASS</span></td>
                  <td>2</td><td>yes</td>
                  <td><span className="pill STRONG">PASS</span></td>
                </tr>
                <tr>
                  <td>Ambiguous stealth posting</td>
                  <td>SKIP</td><td>SKIP</td>
                  <td><span className="pill STRONG">PASS</span></td>
                  <td>0</td><td>no</td>
                  <td><span className="pill STRONG">PASS</span></td>
                </tr>
                <tr>
                  <td>Poor fit, stated red flags</td>
                  <td>SKIP</td><td>SKIP</td>
                  <td><span className="pill STRONG">PASS</span></td>
                  <td>0</td><td>no</td>
                  <td><span className="pill STRONG">PASS</span></td>
                </tr>
                <tr>
                  <td>Strong fit, company unknown</td>
                  <td>APPLY</td><td>APPLY</td>
                  <td><span className="pill STRONG">PASS</span></td>
                  <td>2</td><td>yes</td>
                  <td><span className="pill STRONG">PASS</span></td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="muted" style={{ marginTop: 12 }}>
            Four fixtures, run by hand. This is a personal project — it is not production-scale
            evaluation, and the sample is far too small to make claims about accuracy. Its value
            was catching specific regressions, not measuring quality.
          </p>

          <div className="card" style={{ marginTop: 18 }}>
            <h4>The insight that shaped the harness</h4>
            <p style={{ margin: 0, color: "var(--text-2)" }}>
              A correct final answer reached through unnecessary searches is still poor agent
              behavior. Scoring only the verdict would have hidden every problem below.
            </p>
          </div>
        </section>

        <section className="section">
          <h2>What I learned</h2>
          <p className="lede">
            The useful parts of this project were the failures, and most of them were not where I
            expected.
          </p>
          <ul className="iter">
            <li>
              <div className="lab">V1</div>
              <div className="txt">A single LLM call. One prompt in, one verdict out — a control to measure everything else against.</div>
            </li>
            <li>
              <div className="lab">V2</div>
              <div className="txt">Added a web search tool and the loop around it. The model could now choose to research.</div>
            </li>
            <li className="prob">
              <div className="lab">Problem</div>
              <div className="txt">It searched far too eagerly — looking things up whenever information was missing, whether or not the answer could change.</div>
            </li>
            <li>
              <div className="lab">Change</div>
              <div className="txt">Rewrote the rule: search only when external information could materially affect the recommendation.</div>
            </li>
            <li className="prob">
              <div className="lab">Problem</div>
              <div className="txt">One sentence in that rule — &ldquo;prefer answering with no searches at all&rdquo; — over-corrected and suppressed searching entirely. Every fixture returned zero tool calls.</div>
            </li>
            <li>
              <div className="lab">The eval caught it</div>
              <div className="txt">Verdict accuracy never moved, so outcome scoring alone would have missed it completely. The trajectory column was the only thing that showed the regression.</div>
            </li>
            <li className="win">
              <div className="lab">Result</div>
              <div className="txt">Removing that one sentence restored selective search: the fixture with an unknown company searches twice, the three with nothing worth looking up still search zero times.</div>
            </li>
            <li className="win">
              <div className="lab">The deeper one</div>
              <div className="txt">
                Another failure initially looked like a prompting problem, but the real issue was
                the candidate schema: hard constraints and preferences were represented
                identically, so a single soft mismatch could reject an otherwise excellent role.
                Separating them improved reasoning more than any prompt edit did.
              </div>
            </li>
          </ul>
        </section>

        <section className="section">
          <h2>Limitations</h2>
          <ul style={{ paddingLeft: 20, color: "var(--text-2)", fontSize: "0.92rem", maxWidth: "72ch" }}>
            <li style={{ marginBottom: 8 }}>Four eval fixtures is a small sample. It catches regressions; it does not measure quality.</li>
            <li style={{ marginBottom: 8 }}>Tool-use behavior varies between runs on identical input, so a single clean pass is a snapshot rather than a guarantee.</li>
            <li style={{ marginBottom: 8 }}>The factuality check is a second model call, not a formal verifier. Provenance tagging in the experience bank is the deterministic half of that defence.</li>
            <li style={{ marginBottom: 8 }}>Token counts reported by the agent exclude the nested calls made inside the search tool, so a searching run costs more than the trace shows.</li>
            <li>One search tool, one candidate. This is a personal workflow, not a product.</li>
          </ul>
        </section>

        <footer>
          Example runs are prerecorded from real CLI runs and edited for length. Companies in the
          sample job descriptions are fictional. The public demo reads a sanitized profile
          containing public professional history only.
        </footer>
      </div>
    </main>
  );
}
