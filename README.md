# Job Opportunity Agent

An agent that evaluates whether a role is worth pursuing, selectively researches
missing information, and turns a candidate's experience into a tailored
application package.

Two things live in this repo: a **Python CLI** that does the real work, and a
**Next.js portfolio demo** in `web/` that explains the architecture to a visitor
in a couple of minutes. The CLI is the product; the demo is the exhibit. Neither
depends on the other.

## The problem

Reading a job posting and deciding whether to apply is a judgement call made
dozens of times, badly, under time pressure. Most of it is mechanical — extract
the facts, check them against what you want, notice what's missing. The part
that isn't mechanical is knowing when the missing information actually matters
enough to go find out.

## Why an agent

Most of this could be a single prompt. One part could not: deciding whether to
research the company, what to ask, and whether the answer was enough. That
decision depends on what the posting turned out to say, which is unknowable when
you write the code. So the model owns it.

Everything else — how many searches are allowed, when the loop stops, which
documents get produced, whether an unsupported claim survives — is fixed, so
Python owns it.

**The model controls judgment. Software controls the execution envelope.**

## Architecture

```
agent.py                  orchestration, the agent loop, interactive input
tools.py                  the search_web tool: schema + implementation
candidate_profile.py      what Sofia wants — preferences, goals, constraints
experience_bank.py        what Sofia has done — the factual source of truth
application_generator.py  deterministic resume / letter / strategy pipeline
sample_jobs.py            fixtures for the eval suite
evals.py                  the eval harness
outputs/                  generated materials (gitignored)
web/                      the portfolio demo (see web section below)
```

Two files hold facts and they are deliberately separate. `candidate_profile.py`
is *preference* — it decides APPLY / MAYBE / SKIP. `experience_bank.py` is
*evidence* — it is the only thing generated materials may draw on. Nothing
written into a resume can come from the profile.

### Agent vs workflow

**Phase 1 is an agent.** The model reads the posting against the profile,
decides whether external information could change the answer, writes its own
query if so, reads the result, and decides whether to search again.

```
send the job description + tool definitions
  -> model replies
       -> did it ask for a tool?
            yes: run the tool, append the result, send again  ──┐
            no:  that reply is the final answer, stop           │
                                                    ◄───────────┘
```

**Phase 2 is a workflow.** Once a role is worth pursuing, the steps are fixed:

```
evidence map -> resume draft -> factuality review -> forced revision if needed
             -> cover letter -> application strategy
```

The evidence map comes first deliberately. Asking for a resume directly produces
keyword stuffing; asking first which requirement each experience answers, and
how strongly, forces the selection to be justified before a word gets written.

### The tool-use loop

The loop reads `stop_reason`. If it is `"tool_use"`, it runs the requested tool,
appends the assistant turn verbatim plus matching `tool_result` blocks, and calls
again. Anything else means the model is done.

The number of searches is not something the code decides — but the ceiling is.
`MAX_TOOL_CALLS = 3` is enforced in Python, so "cannot search forever" is a
guarantee rather than an instruction in a prompt.

### Factual guardrails

The writer never signs off on its own work:

1. A requirement-to-evidence map, written before any prose
2. A resume drafted from that map
3. A **separate** model call, with its own system prompt, that reads the draft
   against the experience bank and labels every claim SUPPORTED / PARTIALLY
   SUPPORTED / UNSUPPORTED
4. Plain Python reads that verdict and forces a revision pass if anything failed
5. Only the survivor is written to disk

The bank also tags every claim with provenance — `verified_resume`,
`candidate_provided`, `supported_inference`, or `needs_validation`. The last is
never usable in a document, however hedged.

## Eval design

`evals.py` runs four fixture postings and scores two different things:

- **Outcome quality** — was the APPLY / MAYBE / SKIP correct?
- **Trajectory quality** — was research useful when it happened? Were there
  unnecessary searches? How many tool calls, how many tokens, and is behavior
  stable across runs?

A correct final answer reached through unnecessary searches is still poor agent
behavior. Scoring only the verdict hides that.

## Key iterations

1. **V1** — a single LLM call, as a control.
2. **V2** — added the search tool and the loop. It searched far too eagerly.
3. **Fix** — search only when external information could materially change the
   recommendation.
4. **Regression** — one sentence in that rule ("prefer answering with no
   searches at all") suppressed searching entirely. Verdict accuracy never
   moved, so outcome scoring alone would have missed it. The trajectory column
   caught it.
5. **Fix** — removed that sentence. Selective search returned.
6. **The deeper one** — a failure that looked like a prompting problem was
   actually the candidate schema: hard constraints and preferences were
   represented identically, so one soft mismatch could reject an excellent role.
   Separating them improved reasoning more than any prompt edit.

## Limitations

- Four eval fixtures. Enough to catch regressions, not to measure quality.
- Tool-use behavior varies between runs on identical input.
- The factuality check is a second model call, not a formal verifier.
- Reported token counts exclude the nested calls inside `search_web`, so a
  searching run costs more than the trace shows.
- One search tool, one candidate. A personal workflow, not a product.

## Running the CLI

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # fill in ANTHROPIC_API_KEY and ANTHROPIC_MODEL
```

Fill in `experience_bank.py` with real experience — the agent refuses to generate
application materials while placeholders remain, because it will not invent facts
to fill gaps. Then:

```bash
python app.py             # web UI at http://localhost:8000  ← easiest
python agent.py           # or the terminal: paste a JD, end with END on its own line
python evals.py           # run the fixture suite instead
```

### The local UI

`python app.py` serves a small page on `localhost:8000`, or on `PORT` if that
is set. If a server from earlier is still running there it says so and points
at it rather than starting a second one; if something unrelated holds the port
it moves to the next free one and prints the address. Paste a job
description, press Run, and watch the stages tick past — a run takes several
minutes, so the work happens on a background thread and the page polls for
progress rather than holding an HTTP request open.

When it finishes you get the verdict, the reasoning, any searches the agent
chose to make, and links to the five PDFs. Past applications stay listed down
the right-hand side with company, role, date and verdict, so months later you
can tell what each set of documents was for.

Each run writes to its own folder — `outputs/2026-09-02-addepar-partnerships-product-manager/` —
alongside a `run.json` recording the company, role, verdict, reasoning and the
original posting. Nothing is overwritten.

This is not the portfolio demo. It runs the real agent against your real key and
your private experience bank, so **every run costs money** (roughly $1). The
server binds to `127.0.0.1` deliberately; it is not built to face the internet.

### Editing a document after it is generated

Every listed document has a small **edit** link beside it, in the history on the
right and in the results panel after a run. It opens the markdown the PDF was
rendered from; `Save & re-render` rebuilds the PDF and reports what it came to
("one page at 9.6pt"), or says so and stays open if the edit no longer fits.

The PDF itself is not the editable artifact. Fitting a resume to one page is a
typographic result — `documents.py` walks a density ladder until the page holds
— so an edit has to go back through the same renderer to keep it. Each run
therefore writes a `sources.json` holding the markdown behind every PDF, and an
edit re-renders through the same entry point generation uses.

Two things worth knowing. The factuality check does not re-run on an edit, so
anything added by hand is unguarded. And packages generated before this existed
kept no markdown; those rows say so and can only be made editable by re-running
the posting.

A run can also be deleted from its row in the history — the folder and its PDFs
go with it, after a confirmation, with no undo.

### Learning from those edits

An edit is the most direct feedback there is: it is the candidate saying, in
their own words, what should have been written. Saving one sends the diff — and
an optional note explaining why — to a small model call that tries to state the
rule behind it in one sentence, tagged with the kind of posting it applies to.
The editor shows what was drawn ("Learned: open on the team's problem, not on a
background summary"), and the lessons are listed under the history where any of
them can be deleted. Nothing inferred this way is permanent.

Later runs receive those lessons in the resume, cover letter and evidence-map
prompts, with their scopes, so a rule learned on a partnerships role is applied
to a platform one only if it genuinely fits.

One rule governs the whole loop:

> A lesson may change **how** something is said. It may never change **what is
> true.**

The distiller is instructed to record preferences about wording, emphasis,
ordering, structure, length and tone, and to record no fact at all — no metric,
employer, title, date, team size or achievement, not even one typed in by hand.
An edit that only adds a claim teaches nothing and is dropped. Learning style
from an edit is useful; learning facts from one would quietly promote a
hand-written sentence into a source of truth, which is what the provenance
rules exist to prevent.

Two files hold this, both gitignored because both derive from private
documents: `feedback.jsonl` is the append-only record of every edit as it
happened, and `lessons.json` holds the distilled preferences that generation
actually reads. The learning is best-effort — a failed or unparseable
distillation is swallowed, because an edit that cannot be learned from is still
an edit that saved correctly.

Output lands in `outputs/` as PDFs, which is gitignored because generated
applications contain personal information. The resume and cover letter are
typeset as finished documents; the evidence map, factuality review and strategy
render as denser internal reports.

PDF rendering uses WeasyPrint. On Linux it installs from pip alone; on macOS it
also needs its native text stack:

```bash
brew install pango libffi
```

## The web demo

```bash
cd web
npm install
npm run dev               # http://localhost:3000
```

### Demo mode (the default)

Demo mode makes **zero API calls**. It needs no key at all. Three prerecorded
runs — APPLY, MAYBE and SKIP — are imported at build time and replayed, so a
portfolio visitor can explore the whole system without anyone spending credits.
Companies in the sample postings are fictional.

The demo reads `web/data/portfolio_profile.json`, a sanitized public profile
containing professional history only. The private `candidate_profile.py` and
`experience_bank.py` are never imported, bundled, or served.

### Enabling live mode

Live mode is off unless the server env var is exactly `true`:

```bash
# web/.env.local — server-side only, never NEXT_PUBLIC_
ENABLE_LIVE_DEMO=true
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-opus-5
MAX_JD_CHARS=12000
MAX_SEARCHES=2
```

The guards in `web/app/api/run/route.ts` are implemented: the live flag, JD
length cap, per-IP throttle, and error handling. **The agent loop itself is not
yet ported to the web backend** — the route fails closed with a clear message
rather than pretending. Porting it means either reimplementing the loop with
`@anthropic-ai/sdk` against the sanitized profile, or deploying the Python side
as a service and proxying to it.

Before exposing live mode publicly, replace the in-memory rate limiter with a
durable store (Vercel KV, Upstash). It resets on cold start and is not shared
between instances — it slows casual abuse and nothing more.

### Deploying

The `web/` directory is a self-contained Next.js app.

**Vercel** — import the repo, set the root directory to `web`, deploy. Demo mode
needs no environment variables. Add the live-mode variables only if you want it.

**Netlify** — same, with base directory `web`, build `npm run build`, and the
Next.js plugin.

Visitor job descriptions are used for the request and dropped. Nothing writes
them to disk, a database, or a log.

## Screenshots

TODO — add screenshots of the execution timeline, evidence map and resume tabs.
