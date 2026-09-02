"""
Export the demo as ONE self-contained HTML file.

The Next.js app in this directory is the maintained version and is what live
mode will eventually run on. But a Next app needs hosting, and the portfolio it
is linked from is a plain static Netlify site — so this script flattens the same
content into a single file that can be dropped next to index.html and deploys
with the rest of the site.

Content is read from the same sources the Next app uses (globals.css and the
three run JSONs), so the two cannot drift apart. Re-run after editing either.

    python3 build_static.py > job-agent.html
"""

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
CSS = (HERE / "app" / "globals.css").read_text()
RUNS = [json.loads((HERE / "data" / f"run-{name}.json").read_text())
        for name in ("apply", "maybe", "skip")]

EXTRA_CSS = """
/* static-export additions */
.hidden { display: none !important; }
.backlink { display: inline-block; margin-bottom: 26px; font-size: 0.85rem; color: var(--text-2); text-decoration: none; }
.backlink:hover { color: var(--text); }
.doc-head button, .controls button { font-family: var(--sans); }
"""

BODY = """
<div class="wrap">
  <a class="backlink" href="/#projects">&larr; Back to projects</a>

  <header class="hero" style="padding-top:0">
    <h1>Job Opportunity Agent</h1>
    <p class="sub">A personalized agent that evaluates whether a role is worth pursuing,
    selectively researches missing information, and turns strong opportunities into an
    evidence-backed application package.</p>
    <span class="builtwith">Built with Claude, Python, tool use, web research, and evals</span>
    <div class="facts">
      <div class="fact"><span class="k">Agentic decisions</span><span class="v">Selective research and the fit recommendation</span></div>
      <div class="fact"><span class="k">Controlled workflow</span><span class="v">Evidence map &rarr; resume &rarr; factuality &rarr; strategy</span></div>
      <div class="fact"><span class="k">Evaluation</span><span class="v">Outcome and trajectory evals</span></div>
    </div>
  </header>

  <section class="section">
    <h2>Why an agent?</h2>
    <p class="lede">A normal workflow could simply search the company every time, before every
    decision. That is simpler, and for most postings it is wasted work &mdash; the answer is
    already in the text.</p>
    <p class="lede">This system lets the model decide instead: whether outside information is
    necessary at all, what to retrieve, whether a second retrieval is useful, and when it has
    enough. That dynamic path is the agentic part. Once the recommendation exists, the
    application-generation steps are predictable, so they stay deterministic.</p>
    <div class="card"><h4>Design principle</h4>
      <p style="margin:0;color:var(--text-2)">Use agency where judgment creates value. Keep
      predictable execution deterministic.</p></div>
  </section>

  <section class="section">
    <h2>Try it</h2>
    <p class="lede">Three prerecorded runs. Watch the trace before reading the documents &mdash;
    the decision path is the interesting part.</p>

    <label for="jd" style="display:block;margin-bottom:8px;font-size:0.9rem">Paste a job description</label>
    <textarea id="jd" class="jd" spellcheck="false" placeholder="Paste the full job description here&hellip;"></textarea>
    <div class="controls">
      <button class="primary" id="runbtn">Run Agent</button>
      <span class="muted" style="margin-right:4px">Try a sample:</span>
      <span id="samples"></span>
    </div>
    <div class="notice" id="note"><strong>Demo mode.</strong> The example runs are prerecorded
    from real CLI runs and make zero API calls, so anyone can explore the system without
    spending credits. Employers in the sample job descriptions are fictional.</div>

    <div id="runout"></div>
  </section>

  <section class="section">
    <h2>Agent boundaries</h2>
    <p class="lede">The split that makes this safe to run unattended. Neither side can overrule
    the other.</p>
    <div class="bounds">
      <div><h4><span class="tag model">Model controls</span></h4>
        <ul><li>Whether research is needed</li><li>The search query</li>
        <li>Whether to search again</li><li>The final fit judgment</li></ul></div>
      <div><h4><span class="tag flow">Software controls</span></h4>
        <ul><li>Maximum tool calls</li><li>Loop termination</li><li>Which tools exist at all</li>
        <li>Required application stages</li><li>The factuality gate</li>
        <li>Secrets and credentials</li></ul></div>
    </div>
  </section>

  <section class="section">
    <h2>How it works</h2>
    <p class="lede">A hybrid. The first half is an agent because the model chooses its own path
    through it. The second half is a workflow because the steps are fixed and the order is
    enforced in code.</p>

    <details class="box" open><summary>Phase 1 &mdash; the agentic loop</summary><div class="inner">
      <div class="flow"><span class="n">JOB DESCRIPTION</span><br><span class="arrow">&darr;</span><br>
      <span class="n">MODEL</span> <span class="arrow">reads it against the candidate profile</span><br>
      <span class="arrow">&darr;</span><br><span class="split">ENOUGH INFORMATION TO DECIDE?</span><br>
      <span class="arrow">&darr; no</span><br><span class="n">TOOL USE</span>
      <span class="arrow">&mdash; the model writes its own query</span><br><span class="arrow">&darr;</span><br>
      <span class="n">OBSERVATION</span><br><span class="arrow">&darr;</span><br>
      <span class="n">MODEL REASSESSES</span> <span class="arrow">&mdash; search again, or stop</span><br>
      <span class="arrow">&darr;</span><br><span class="n">APPLY / MAYBE / SKIP</span></div>
      <p style="font-size:0.88rem;color:var(--text-2);margin:16px 0 0">The loop reads
      <code>stop_reason</code>. If it is <code>"tool_use"</code>, Python runs whatever the model
      asked for, appends the result, and calls again. Nothing in the code decides how many
      searches happen &mdash; but the ceiling is enforced there, so &ldquo;cannot search
      forever&rdquo; is a guarantee rather than an instruction.</p>
    </div></details>

    <details class="box"><summary>Phase 2 &mdash; the deterministic workflow</summary><div class="inner">
      <div class="flow"><span class="n">EVIDENCE MAP</span>
      <span class="arrow">requirement &rarr; evidence, before any prose</span><br><span class="arrow">&darr;</span><br>
      <span class="n">RESUME</span> <span class="arrow">drafted from the map</span><br><span class="arrow">&darr;</span><br>
      <span class="n">FACTUALITY CHECK</span> <span class="arrow">separate call, separate prompt</span><br>
      <span class="arrow">&darr;</span><br><span class="n">REVISION</span>
      <span class="arrow">forced by Python if anything failed</span><br><span class="arrow">&darr;</span><br>
      <span class="n">COVER LETTER</span><br><span class="arrow">&darr;</span><br>
      <span class="n">INTERVIEW STRATEGY</span></div>
      <p style="font-size:0.88rem;color:var(--text-2);margin:16px 0 0">The evidence map comes
      first deliberately. Asking for a resume directly produces keyword stuffing; asking first
      which requirement each experience answers, and how strongly, forces the selection to be
      justified before a word gets written.</p>
    </div></details>

    <details class="box"><summary>Why the factuality check is its own step</summary><div class="inner">
      <p style="font-size:0.9rem;color:var(--text-2);margin-top:0">A model asked to check its own
      draft tends to approve it. So the review is a separate call with a separate system prompt
      telling it plainly that it did not write this resume and has no stake in it. It labels every
      claim <strong>SUPPORTED</strong>, <strong>PARTIALLY SUPPORTED</strong> or
      <strong>UNSUPPORTED</strong> against the experience bank.</p>
      <p style="font-size:0.9rem;color:var(--text-2);margin-bottom:0">Then plain Python reads the
      verdict and decides whether a revision pass runs. The writer never signs off on itself.
      Every claim in the bank also carries a provenance label, and anything unconfirmed can never
      reach a document at all.</p>
    </div></details>
  </section>

  <section class="section">
    <h2>How I evaluated it</h2>
    <p class="lede">Two things get scored, because a right answer reached the wrong way is still a
    broken agent. <strong>Outcome:</strong> was the recommendation correct?
    <strong>Trajectory:</strong> did it use tools appropriately &mdash; necessary searches made,
    unnecessary ones skipped?</p>

    <h3>One iteration, start to finish</h3>
    <ul class="walk">
      <li><span class="k">Initial behavior</span><span class="v">The agent searched whenever information was missing.</span></li>
      <li><span class="k bad">Problem</span><span class="v">Unnecessary searches increased cost and added noise to the reasoning.</span></li>
      <li><span class="k">Change</span><span class="v">Search only when external information could materially change the recommendation.</span></li>
      <li><span class="k bad">Over-correction</span><span class="v">An added instruction to &ldquo;prefer answering with no searches at all&rdquo; caused the agent to stop using the tool entirely. Every fixture returned zero tool calls.</span></li>
      <li><span class="k good">Eval caught it</span><span class="v">Verdict accuracy never moved, so outcome scoring alone would have missed this completely. Only the trajectory column showed the regression. Removed the overly strong instruction.</span></li>
      <li><span class="k good">Result</span><span class="v">Selective research: obvious cases skip tools entirely; uncertainty with actionable external context triggers a search.</span></li>
    </ul>

    <h3>Example results</h3>
    <div class="tablewrap"><table>
      <thead><tr><th>Fixture</th><th>Expected</th><th>Actual</th><th>Outcome</th><th>Searches</th><th>Research useful?</th><th>Trajectory</th></tr></thead>
      <tbody>
        <tr><td>Strong fit, onsite in another city</td><td>SKIP</td><td>SKIP</td><td><span class="pill STRONG">PASS</span></td><td>2</td><td>yes</td><td><span class="pill STRONG">PASS</span></td></tr>
        <tr><td>Ambiguous stealth posting</td><td>SKIP</td><td>SKIP</td><td><span class="pill STRONG">PASS</span></td><td>0</td><td>no</td><td><span class="pill STRONG">PASS</span></td></tr>
        <tr><td>Poor fit, stated red flags</td><td>SKIP</td><td>SKIP</td><td><span class="pill STRONG">PASS</span></td><td>0</td><td>no</td><td><span class="pill STRONG">PASS</span></td></tr>
        <tr><td>Strong fit, company unknown</td><td>APPLY</td><td>APPLY</td><td><span class="pill STRONG">PASS</span></td><td>2</td><td>yes</td><td><span class="pill STRONG">PASS</span></td></tr>
      </tbody></table></div>
    <p class="muted" style="margin-top:12px">Four fixtures, run by hand. A personal project &mdash;
    not production-scale evaluation, and far too small a sample to claim accuracy. Its value was
    catching specific regressions.</p>
  </section>

  <section class="section">
    <h2>The lesson that wasn&rsquo;t about prompting</h2>
    <p class="lede">An early profile schema represented hard constraints and strong preferences
    identically &mdash; one flat list. The model then rationally over-weighted the preferences,
    letting a single soft mismatch reject an otherwise excellent role.</p>
    <p class="lede">The instinct was to prompt around it. The actual fix was to redesign the schema
    so the two are separate structures with different weight, which improved the reasoning more
    than any prompt edit had.</p>
    <div class="card"><p style="margin:0;color:var(--text)">Agent failures are not always model
    failures. They can be context, schema, tool, prompt, or eval failures &mdash; and it is worth
    knowing which one you have before rewriting the prompt.</p></div>
  </section>

  <section class="section">
    <h2>Limitations</h2>
    <div class="grid2">
      <div><ul style="padding-left:20px;color:var(--text-2);font-size:0.91rem;margin:0">
        <li style="margin-bottom:8px">Demo runs on this page are cached, not live.</li>
        <li style="margin-bottom:8px">The eval set is small and synthetic.</li>
        <li style="margin-bottom:8px">Tool-use behavior can vary between identical runs.</li>
        <li style="margin-bottom:8px">The full private candidate profile is not exposed here &mdash; the demo reads a sanitized public subset.</li>
        <li style="margin-bottom:8px">Live mode would require proper distributed rate limiting.</li>
        <li>Factuality review still uses an LLM. It is a second opinion, not a proof system.</li>
      </ul></div>
      <div><h4 style="margin-top:0;font-size:0.74rem;font-family:var(--mono);letter-spacing:0.1em;text-transform:uppercase;color:var(--text-3)">Next steps</h4>
      <ul style="padding-left:20px;color:var(--text-2);font-size:0.91rem;margin:0">
        <li style="margin-bottom:8px">Evaluate against real application history</li>
        <li style="margin-bottom:8px">Measure user overrides of the recommendation</li>
        <li style="margin-bottom:8px">Add repeated-run stability evals</li>
        <li style="margin-bottom:8px">Retrieve only relevant experience instead of passing the full bank</li>
        <li style="margin-bottom:8px">Production-grade live rate limiting</li>
        <li>Track cost and latency per run</li>
      </ul></div>
    </div>
  </section>

  <footer>Example runs are prerecorded from real CLI runs and edited for length. Companies in the
  sample job descriptions are fictional. This page reads a sanitized profile containing public
  professional history only. &nbsp;&middot;&nbsp;
  <a href="https://github.com/sofiatofigh0/agentshop">Source on GitHub</a></footer>
</div>
"""

SCRIPT = r"""
const RUNS = __RUNS__;
const REVEAL_MS = 380;
let timer = null;

const esc = (s) => String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
const $ = (sel) => document.querySelector(sel);

function md(src) {
  const lines = esc(src).split("\n"); const out = []; let ul = false;
  const close = () => { if (ul) { out.push("</ul>"); ul = false; } };
  for (const raw of lines) {
    const t = raw.trim();
    if (!t) { close(); continue; }
    const line = t.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    if (t.startsWith("## ")) { close(); out.push("<h2>" + line.slice(3) + "</h2>"); }
    else if (t.startsWith("# ")) { close(); out.push("<h1>" + line.slice(2) + "</h1>"); }
    else if (t.startsWith("- ")) { if (!ul) { out.push("<ul>"); ul = true; } out.push("<li>" + line.slice(2) + "</li>"); }
    else if (/^[A-Za-z].*·/.test(t) && t.length < 90) { close(); out.push('<p class="meta">' + line + "</p>"); }
    else { close(); out.push("<p>" + line + "</p>"); }
  }
  close(); return out.join("\n");
}

function stepHtml(s) {
  if (s.type === "model_decision")
    return '<li class="step is-model"><span class="tag model">Model decision</span><div class="body">' + esc(s.message) + "</div></li>";
  if (s.type === "tool_call")
    return '<li class="step is-tool"><span class="tag tool">Tool call</span><code class="q">' + esc(s.tool) + "( " + esc(s.input.query) + " )</code></li>";
  if (s.type === "tool_result")
    return '<li class="step is-obs"><span class="tag obs">Observation</span><div class="body">' + esc(s.summary) + "</div></li>";
  return '<li class="step is-flow"><span class="tag flow">Recommendation</span><div class="verdict-row"><span class="verdict ' + esc(s.message) + '">' + esc(s.message) + "</span></div></li>";
}

function stageHtml(s) {
  return '<li class="step is-flow"><span class="tag flow">Workflow</span><div class="body"><strong style="color:var(--text)">' +
    esc(s.stage) + "</strong> &mdash; " + esc(s.detail) + "</div></li>";
}

function list(items) {
  return '<ul style="margin:0;padding-left:20px">' + items.map(i =>
    '<li style="margin-bottom:6px;color:var(--text-2);font-size:0.9rem">' + esc(i) + "</li>").join("") + "</ul>";
}

function notGenerated(v) {
  return '<div class="notice">No application materials were generated for this run. The verdict was <strong>' +
    esc(v) + "</strong>, and on a SKIP the CLI asks before generating anything &mdash; defaulting to no. " +
    "Spending six model calls on a role the agent just advised against would be the wrong default.</div>";
}

function tabsHtml(run) {
  const names = ["Recommendation","Evidence Map","Tailored Resume","Cover Letter","Interview Strategy","Agent Trace"];
  return '<div class="results"><div class="tabs" role="tablist">' +
    names.map((n,i) => '<button class="tab" role="tab" data-tab="' + i + '" aria-selected="' + (i===0) + '">' + n + "</button>").join("") +
    '</div><div class="panel" id="panel"></div></div>';
}

function panelHtml(run, i) {
  if (i === 0) {
    let h = '<div class="verdict-row" style="margin-bottom:18px"><span class="verdict ' + run.recommendation + '">' + run.recommendation +
      '</span><span class="muted">' + run.metrics.searches + " search" + (run.metrics.searches===1?"":"es") + " &middot; " +
      run.metrics.agent_turns + " agent turn" + (run.metrics.agent_turns===1?"":"s") + "</span></div>" +
      '<p style="max-width:72ch;color:var(--text-2)">' + esc(run.reasoning) + "</p>";
    if (run.recommendation_note) h += '<div class="notice">' + esc(run.recommendation_note) + "</div>";
    h += '<div class="grid2" style="margin-top:22px"><div class="card"><h4>Top strengths</h4>' + list(run.strengths) +
      '</div><div class="card"><h4>Main concerns</h4>' + list(run.concerns) + "</div></div>" +
      '<div class="card"><h4>Research performed</h4><p style="margin:0;font-size:0.9rem;color:var(--text-2)">' +
      esc(run.research_summary) + "</p></div>";
    return h;
  }
  if (i === 1) {
    return '<p class="lede">Built before any prose is written. Asking for a resume directly produces keyword stuffing; ' +
      'asking first which requirement each experience answers, and how strongly, forces the selection to be justified.</p>' +
      '<div class="tablewrap"><table><thead><tr><th>Requirement</th><th>Priority</th><th>Evidence</th><th>Source</th>' +
      "<th>Metric</th><th>Strength</th><th>Gap</th></tr></thead><tbody>" +
      run.evidence_map.map(r => "<tr><td style='font-weight:500'>" + esc(r.requirement) + '</td><td><span class="pill ' + r.priority + '">' +
        r.priority + "</span></td><td style='color:var(--text-2)'>" + esc(r.evidence) +
        "</td><td style='color:var(--text-3);font-size:0.8rem'>" + esc(r.source) +
        "</td><td style='color:var(--text-2);font-size:0.8rem'>" + esc(r.metric) +
        '</td><td><span class="pill ' + r.strength + '">' + r.strength + "</span></td>" +
        "<td style='color:var(--text-3);font-size:0.8rem'>" + esc(r.gap) + "</td></tr>").join("") +
      "</tbody></table></div>";
  }
  if (i === 2) {
    if (!run.resume) return notGenerated(run.recommendation);
    let h = '<div class="doc-head"><span class="muted">Generated for this role. Every claim traced to the experience bank.</span>' +
      '<button data-copy="resume">Copy</button></div><div class="doc">' + md(run.resume) + "</div>";
    const f = run.factuality_review;
    if (f) {
      h += '<div class="card" style="margin-top:18px"><h4><span class="tag eval">Factuality gate</span> <span style="margin-left:8px">' +
        f.claims_checked + ' claims checked</span></h4><p style="font-size:0.87rem;color:var(--text-2);margin:8px 0 12px">' +
        f.supported + " supported &middot; " + f.partially_supported + " partially supported &middot; " + f.unsupported +
        " unsupported. A separate model call reviews the draft against the experience bank; Python &mdash; not the model &mdash; " +
        "reads the verdict and forces a revision pass if anything failed.</p>";
      h += f.required_fixes.length
        ? f.required_fixes.map(x => '<div class="card" style="background:var(--surface-2)"><div style="font-size:0.87rem;margin-bottom:6px">' +
            '<span class="pill PARTIAL">' + esc(x.verdict) + '</span> <span style="margin-left:6px">' + esc(x.claim) +
            '</span></div><div class="muted">' + esc(x.basis) + '</div><div style="font-size:0.85rem;color:var(--apply);margin-top:6px">' +
            esc(x.action) + "</div></div>").join("")
        : '<div class="muted">No fixes required &mdash; every claim was supported.</div>';
      h += "</div>";
    }
    return h;
  }
  if (i === 3) {
    if (!run.cover_letter) return notGenerated(run.recommendation);
    return '<div class="doc-head"><span class="muted">Under 400 words. No generic enthusiasm.</span>' +
      '<button data-copy="cover">Copy</button></div><div class="doc">' +
      run.cover_letter.split("\n\n").map(p => "<p>" + esc(p) + "</p>").join("") + "</div>";
  }
  if (i === 4) {
    if (!run.strategy) return notGenerated(run.recommendation);
    const s = run.strategy;
    return '<div class="grid2"><div class="card"><h4>Strongest fit areas</h4>' + list(s.fit_areas) +
      '</div><div class="card"><h4>Gaps</h4>' + list(s.gaps) +
      '</div><div class="card"><h4>What to emphasize</h4>' + list(s.emphasize) +
      '</div><div class="card"><h4>What not to emphasize</h4>' + list(s.avoid) + "</div></div>" +
      "<h3>Likely questions, and the story to answer with</h3>" +
      '<div class="tablewrap"><table><thead><tr><th>Likely question</th><th>Best experience to use</th></tr></thead><tbody>' +
      s.questions.map(q => "<tr><td style='font-weight:500'>" + esc(q.question) + "</td><td style='color:var(--text-2)'>" +
        esc(q.story) + "</td></tr>").join("") + "</tbody></table></div>";
  }
  const modelSide = ["Whether external research was needed at all","Which query to issue",
    "Whether the first result was enough or another search was warranted",
    "Which uncertainties actually matter to the decision","The final APPLY / MAYBE / SKIP judgement"];
  const swSide = ["Maximum number of searches (hard ceiling of 3 in the CLI)",
    "Loop termination — bounded in Python, not requested in the prompt",
    "Which output stages must run, and in what order","The factuality gate: whether a revision pass is forced",
    "API credential handling — server-side only","Error handling and graceful failure"];
  let seq = [], turn = 1;
  for (const st of run.agent_trace) {
    if (st.type === "tool_call") { seq.push("Agent turn " + turn + "\n  → requested " + st.tool + '("' + st.input.query + '")'); turn++; }
    else if (st.type === "tool_result") { seq.push("Tool result\n  → " + st.summary.slice(0,120) + (st.summary.length>120?"…":"")); }
    else if (st.type === "recommendation") { seq.push("Agent turn " + turn + "\n  → end_turn (" + st.message + ")"); }
  }
  if (seq.length === 1) seq.unshift("No tool calls. The model judged that research could not change the answer.");
  const m = run.metrics;
  return '<div class="grid2"><div class="card"><h4><span class="tag model">Model controlled</span></h4>' + list(modelSide) +
    '</div><div class="card"><h4><span class="tag flow">Software controlled</span></h4>' + list(swSide) + "</div></div>" +
    "<h3>Tool-call sequence from this run</h3><div class=\"card\" style=\"font-family:var(--mono);font-size:0.82rem\">" +
    seq.map(l => '<div style="white-space:pre-wrap;margin-bottom:10px;color:var(--text-2)">' + esc(l) + "</div>").join("") +
    '</div><h3>Run metrics</h3><dl class="kv">' +
    "<dt>Searches</dt><dd>" + m.searches + "</dd><dt>Tool calls</dt><dd>" + m.tool_calls +
    "</dd><dt>Agent turns</dt><dd>" + m.agent_turns + "</dd><dt>Agent input</dt><dd>" + m.agent_input_tokens.toLocaleString() +
    " tokens</dd><dt>Agent output</dt><dd>" + m.agent_output_tokens.toLocaleString() +
    " tokens</dd><dt>Generation calls</dt><dd>" + m.generation_calls + "</dd></dl>";
}

function wireTabs(run) {
  const panel = $("#panel");
  panel.innerHTML = panelHtml(run, 0);
  document.querySelectorAll(".tab").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach(b => b.setAttribute("aria-selected", "false"));
      btn.setAttribute("aria-selected", "true");
      panel.innerHTML = panelHtml(run, Number(btn.dataset.tab));
      wireCopy(run);
    });
  });
  wireCopy(run);
}

function wireCopy(run) {
  document.querySelectorAll("[data-copy]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const text = btn.dataset.copy === "resume" ? run.resume : run.cover_letter;
      try { await navigator.clipboard.writeText(text); btn.textContent = "Copied";
        setTimeout(() => (btn.textContent = "Copy"), 1600); } catch (e) {}
    });
  });
}

function play(run) {
  if (timer) clearInterval(timer);
  $("#jd").value = run.job.text;
  const total = run.agent_trace.length + run.workflow_trace.length;
  const out = $("#runout");
  out.innerHTML =
    '<div style="margin-top:30px"><div class="phase-head" style="margin-top:0">' +
    '<span class="tag eval">' + esc(run.label) + '</span><span class="d">' + esc(run.job.title) + " &middot; " +
    esc(run.job.company) + " &middot; " + esc(run.job.location) + "</span></div>" +
    '<div class="trace-panel"><div class="trace-title">Execution trace</div>' +
    '<p class="cap">Every step below the first heading was the model&rsquo;s choice. Every step below the second was fixed in code before the run started.</p>' +
    '<div class="phase-head"><span class="t">Agentic phase</span><span class="d">the model chooses the path</span></div>' +
    '<ul class="timeline" id="tl-agent"></ul><div id="wf-wrap"></div></div><div id="tabs-slot"></div></div>';

  let n = 0;
  const tick = () => {
    if (n >= total) {
      clearInterval(timer); timer = null;
      $("#tabs-slot").innerHTML = tabsHtml(run);
      wireTabs(run);
      return;
    }
    if (n < run.agent_trace.length) {
      $("#tl-agent").insertAdjacentHTML("beforeend", stepHtml(run.agent_trace[n]));
    } else {
      const k = n - run.agent_trace.length;
      if (k === 0 && run.workflow_trace.length) {
        $("#wf-wrap").innerHTML =
          '<div class="phase-head"><span class="t">Deterministic workflow</span><span class="d">fixed order, enforced in Python</span></div>' +
          '<ul class="timeline" id="tl-wf"></ul>';
      }
      if (run.workflow_trace[k]) $("#tl-wf").insertAdjacentHTML("beforeend", stageHtml(run.workflow_trace[k]));
    }
    n++;
  };
  tick();
  timer = setInterval(tick, REVEAL_MS);
}

$("#samples").innerHTML = RUNS.map((r, i) =>
  '<button class="chip" data-run="' + i + '">' + r.recommendation + " &mdash; " + esc(r.job.company) + "</button>").join(" ");
document.querySelectorAll("[data-run]").forEach(b =>
  b.addEventListener("click", () => play(RUNS[Number(b.dataset.run)])));

$("#runbtn").addEventListener("click", () => {
  $("#note").innerHTML = "<strong>This page is a static demo.</strong> It ships three prerecorded runs and " +
    "makes no API calls, so it costs nothing to explore and cannot leak a key. Running the agent on your own " +
    "job description means cloning the repo and running the Python CLI &mdash; the link is in the footer.";
});
"""


def main() -> None:
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Job Opportunity Agent — Sofia Tofigh</title>
<meta name="description" content="An agent that evaluates whether a role is worth pursuing, selectively researches missing information, and turns strong opportunities into an evidence-backed application package.">
<style>
{CSS}
{EXTRA_CSS}
</style>
</head>
<body>
{BODY}
<script>
{SCRIPT.replace("__RUNS__", json.dumps(RUNS, ensure_ascii=False))}
</script>
</body>
</html>
"""
    sys.stdout.write(html)


if __name__ == "__main__":
    main()
