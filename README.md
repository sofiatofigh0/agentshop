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
ats.py                    keyword extraction and scoring, the way a screener does it
models.py                 which model runs each step, at what effort, at what price
lessons.py                what the candidate's own edits teach later runs
documents.py              markdown -> PDF, including the one-page fit
sample_jobs.py            fixtures for the eval suite
evals.py                  the eval harness
tests/                    unit tests; no model is called
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
evidence map  -> resume draft -> [rephrasing pass]
+ ATS keywords
              -> cover letter -> application strategy
              -> ATS report (plain Python, no model)
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

An earlier version had a second model read every resume against the experience
bank and force a revision when a claim went too far. It was removed to make
runs cheaper and faster. What remains all works upstream of the writing:

1. A requirement-to-evidence map, written before any prose, so the selection is
   justified before a word gets written
2. The same ground rules in every writing prompt: the experience bank is the
   only source of facts — no invented experience, metrics, titles or seniority
3. Claims marked `needs_validation` stripped from the bank before any model
   sees it, so they cannot be used however a prompt is read
4. Each writer told, before it starts, which of the posting's terms the bank
   never uses — the ones most likely to be reached for dishonestly

These are instructions and omissions, not a check. Nothing reads the finished
resume back against the bank, so read it before you send it.

The bank also tags every claim with provenance — `verified_resume`,
`candidate_provided`, `supported_inference`, or `needs_validation`. The last is
never usable in a document, however hedged.

## How a resume bullet is shaped

Every Work Experience bullet opens with the project it is about, in two or three
bold words, then the achievement:

```
- **Advisor summarization** — Shipped an LLM pipeline that cut meeting prep by ~40%.
- **Eval framework** — Built the rubric and the reporting behind it.
```

A reviewer scans the left edge of the bullets before reading a full sentence.
Those labels are what tell them, in a couple of seconds, what kinds of problems
this candidate has actually worked on.

The label is the experience bank's own name for that project, shortened. It is
never invented, never a place to park a keyword, and it names the project
rather than the candidate's role in it.

Bullets that are not about one discrete project stay plain sentences — ongoing
responsibilities, ways of working, and advisory or consulting engagements
described as a kind of work rather than a thing that shipped. A label on those
is padding, and it tells the reviewer nothing.

## ATS scoring

Before a person reads an application, a screening system usually scores it
against the posting: does the resume contain the terms the posting was written
in? Tools like Simplify and Jobscan show candidates that score so they can
close the gap before submitting. This project does the same thing, with one
rule the borrowed idea does not have:

> A keyword is only ever worked in by rephrasing something that is already
> true. It is never added to hit a number.

How it works, in order:

1. **Extract.** One cheap call on the worker model reads the posting and
   returns the terms a screener would be configured to scan for — each with a
   category (hard skill, tool, title, credential, domain, soft skill), how
   firmly the posting asks for it (required, preferred, mentioned), and the
   equivalent phrasings a screener would count ("LLM evals" for "LLM
   evaluation"). This runs alongside the evidence map; it needs only the
   posting.
2. **Write with the terms in view.** The resume and cover-letter prompts get
   the weighted list, split by whether the experience bank uses each term.
   Where a sentence already describes the work, say it in the posting's own
   term rather than a synonym. A term the bank never uses is a gap unless the
   bank clearly describes that exact work in other words. Never append lists,
   never repeat for effect.
3. **Score.** Plain Python. `score = 100 × weight of matched terms / weight of
   all terms`, where weight is importance (required 3, preferred 2, mentioned
   1) times category (soft skills count half). A match is the posting's own
   term as a whole phrase, singular or plural. An alias — "LLM evals" for "LLM
   evaluation", an abbreviation, another phrasing — does not count: a
   recruiter searches for the posting's words, and a synonym is not found.
   Such a term is listed as *said in a different form* instead.
4. **Rephrase — sometimes.** If the draft is below the target (75, Jobscan's
   published guidance) and there is something honest to offer, one more call
   rewords sentences that already say the thing, in the posting's words,
   changing sentence structure where it has to. Terms said in a different
   form go first — the claim is already on the page, so rewording it adds
   nothing. Then missing terms the experience bank at least mentions. It may
   not add a bullet, a skill, or a claim; a term the bank never mentions is a
   gap, and no call is spent on it. The reworded draft is kept only if it
   scores higher.
5. **Report.** `ats_report.pdf` gives the score per document and per category,
   how many of the posting's terms appear in its own words, what matched, what
   was said in a different form, what the bank mentions but the resume does
   not yet use, and what is not in the bank at all (the real gaps, marked *do
   not add*). Then whether the title line carries the posting's title word for
   word and the Summary repeats it; the parser-facing checks — standard
   headings, one date format, no icons, a contact line; and whether each copy
   reads back in order when a parser extracts it.

The score is a proxy for one filter, not a measure of quality. It is shown
beside the verdict so a low number can be understood, not so it can be chased.
Editing a resume or letter in the UI re-scores it on the spot, with no model
call, so the effect of a change is visible immediately.

## What a screening system actually reads

A widely shared write-up on applicant tracking systems (Workday, Greenhouse,
Lever, iCIMS, Taleo) makes a set of claims about what gets a resume found. Some
of them are checkable against this project's own output, and were checked
before anything changed. Here is what was adopted and what was not.

**Adopted:**

| Claim | What changed |
|---|---|
| Two columns get scrambled | Measured, not assumed: this project's own two-column PDF reads back with Education ahead of Experience, and with each row fusing a line from the sidebar to a line from the main column. The upload copy is now one column, and `tests/test_documents.py` keeps both results as a regression guard. |
| Match the exact job title | The title line is the posting's own title, word for word, or its core when the full title will not fit. The Summary's first sentence repeats it. It never overstates seniority: a "Director of Product" posting gets "Senior Product Manager". |
| Exact words, not synonyms | Scoring now counts only the posting's own term. A resume that says it another way is shown the exact rewording, and those rewordings go to the rephrasing pass first. |
| Standard headings | Summary, Skills, Work Experience, Projects, Education. The report flags any heading a parser would have to guess at. |
| Contact details in the body | They always were: nothing uses the page margins. |
| One date format | The bank already used Month Year throughout. The prompt now says why it must stay that way, and the report checks every role. |
| No icons | Checked by Unicode category; ordinary punctuation passes. |

**Not adopted:**

- **A 25–35 keyword "sweet spot."** No mechanism is given, and the right number
  depends on the posting — a thin one might have twelve real terms. A floor
  would push the writer to pad, which the no-forcing rule exists to prevent.
  The report shows "posting terms used in the posting's own words: N of M"
  instead, which is the thing a recruiter's search actually sees.
- **A stuffing detector that trips above 35.** No threshold like that is
  documented for any of these systems. What is defensible is already here:
  a flag when one term repeats past the point of use, and no hidden text, ever.
- **A .docx copy.** An earlier version wrote one; it was removed to keep a
  single upload format. The PDF is text-based and tested to read back in order,
  which the write-up itself says modern systems handle.

### The two resume copies

| File | Layout | Use it for |
|---|---|---|
| `tailored_resume.pdf` | one column | uploading |
| `resume_designed.pdf` | two columns | people — a referral, an email to a hiring manager, print |

Both come from one markdown source, and an edit in the UI rebuilds both.

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

## What a run costs

Each run makes six to twelve model calls: one to four in the agent loop, up to
three nested web-search summaries, and five or six in generation — the
keyword extraction, the evidence map, the resume, the cover letter and the
strategy, plus the rephrasing pass when the draft needs it. A run used to cost
more than a dollar; most of that was reasoning depth spent on steps that do
not need it, search results re-billed on every turn, and a review pass on the
resume. The levers, in the order they were applied:

| Lever | What changed | Costs quality? |
|---|---|---|
| Per-step effort | Verdict and evidence map keep the default depth. Resume, letter, strategy and the rephrasing pass run at `medium`; search summaries, keyword extraction and lesson distillation at `low`. See `EFFORT` in `models.py`, and "Effort against caching" below for how that is delivered. | Not measurably for writing and extraction steps; the reasoning steps are untouched |
| Search sub-calls | Two searches per query instead of three, a 200-word summary shape, `low` effort, and a 1,500-token cap. Their usage is now counted in the trace. | No — the agent reads a summary either way |
| Run context cached | The posting and research sit in the system prompt behind a second cache marker, written once by the evidence-map call and read back by every later call, instead of travelling in the user turn at full price six times. | No |
| Loop caching | The agent loop moves a cache marker to the newest user turn, so each turn reads the history it already sent. | No |
| Priced trace | `models.py` carries the price table; the trace and the UI show dollars per run instead of "roughly $1". | No |
| No review pass | The factuality review and the revision it could trigger are gone. The review ran at the default depth after the resume was written, so it was the costliest call after the evidence map, and it sat on the longest branch of the run. | Yes — see "Factual guardrails" |
| Bank-aware first draft | The writers are told up front which of the posting's terms the bank uses, the same plain-Python check the rephrasing gate runs afterwards. A first draft that uses them lands nearer the target, so the second, full-resume rephrasing call fires less often. | No |
| Bounded outputs | Output tokens cost five times input and set the pace. Every document waits for the evidence map, which is now at most 12 rows of short phrases. The strategy brief is bullets, about 700 words, with six interview questions. | Slightly: shorter internal documents, same facts |

### Effort against caching

These two levers pull against each other, and the conflict is not obvious.

A top-level effort value is rendered into the prompt itself, so changing it
between calls starts a new cache prefix — and on models that render it ahead of
the system prompt, it invalidates the system cache too. The generation calls
share a cached prefix of roughly fourteen thousand tokens, most of it the
experience bank. Giving each of them its own effort would make most of them
rewrite that prefix instead of reading it, which costs several times what the
effort saves. With a one-hour cache it would cost more than not caching at all.

So the generation calls pin their top-level effort, and a step that wants less
depth asks for it in a `messages` entry instead — a `role: "system"` message
with empty content and its own `output_config`. Message content never
invalidates the system cache, so the prefix survives and each step still gets
its own depth. That mechanism is in beta and only on some models; where it is
unavailable the whole stage simply runs at the default depth, because the cache
is worth more than the difference. If the API rejects the beta, the first call
falls back and the rest of the process stops asking.

The steps whose calls share no cached prefix — the search summary, keyword
extraction, lesson distillation — set effort the ordinary way, because there is
nothing for them to invalidate.

`tests/test_models.py` asserts that every generation step sends an identical
top-level effort. That test is the regression guard: the first version of this
change did vary it, and would have quietly spent more than it saved.

Three optional settings in `.env` go further:

- `ANTHROPIC_WORKER_MODEL` — a cheaper model (say `claude-sonnet-5`) for the
  extraction-shaped side jobs only: search summaries, keyword extraction,
  lesson distillation. The verdict and every document still come from
  `ANTHROPIC_MODEL`.
- `PROMPT_CACHE_TTL=1h` — keeps the experience bank in the prompt cache for an
  hour rather than five minutes. A write then costs 2× instead of 1.25×, but
  every further run in the hour reads it at a tenth of the price. Worth it
  when several postings are run in one sitting.
- `ANTHROPIC_EFFORT` — forces one effort on every step, for comparing settings
  with `evals.py` one change at a time. One level everywhere is constant, so it
  is still cache-safe. A level the chosen model does not accept is clamped down
  to the nearest one it does, rather than failing every call in the run.

Estimated from the code rather than measured — nothing in this repo spends
money on a benchmark — a no-search run on Opus 5 went from roughly $1.20 to
roughly $0.70–0.80 with the first five levers, and removing the review and
bounding the outputs takes about another $0.15–0.20 off, to roughly
$0.55–0.60. The same removal takes the review off the run's longest branch,
which by the same estimate saves about a minute of wall-clock per run.
`ANTHROPIC_WORKER_MODEL=claude-sonnet-5` takes a further ten to fifteen cents
off a searching run. Most of what remains is the verdict and the evidence map,
the two steps that keep the default depth. The trace prints the real number
for every run, which is the figure to trust.

## Limitations

- Four eval fixtures. Enough to catch regressions, not to measure quality.
- The ATS score measures one filter — exact-term coverage — and nothing about
  whether a person will like the document. Treat a low score as a prompt to
  read the report, not as a target.
- Tool-use behavior varies between runs on identical input.
- Nothing checks a generated resume against the experience bank. The ground
  rules are instructions, not a verifier; read a resume before sending it.
- One search tool, one candidate. A personal workflow, not a product.

## Running the CLI

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # fill in ANTHROPIC_API_KEY and ANTHROPIC_MODEL
```

After pulling changes, run `pip install -r requirements.txt` again: new
dependencies are not picked up by an existing virtualenv.

Fill in `experience_bank.py` with real experience — the agent refuses to generate
application materials while placeholders remain, because it will not invent facts
to fill gaps. Then:

```bash
python app.py             # web UI at http://localhost:8000  ← easiest
python agent.py           # or the terminal: paste a JD, end with END on its own line
python evals.py           # run the fixture suite instead
python -m unittest        # the unit tests; no model is called
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
chose to make, the ATS score of the resume and the cover letter, what the run
cost, and links to every document — the resume two ways, the cover letter,
and three internal reports. Past applications stay listed down the
right-hand side with company, role, date, verdict and score, so months later
you can tell what each set of documents was for.

Each run writes to its own folder — `outputs/2026-09-02-addepar-partnerships-product-manager/` —
alongside a `run.json` recording the company, role, verdict, reasoning and the
original posting. Nothing is overwritten.

This is not the portfolio demo. It runs the real agent against your real key and
your private experience bank, so **every run costs money** — the amount is
shown when it finishes, and "What a run costs" above says where it goes. The
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

Two things worth knowing. Nothing checks an edit against the experience bank,
so anything added by hand is on you — the ATS score does re-run, in plain
Python, so the effect of a wording change is visible at once. And packages generated before this existed
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

Output lands in `outputs/`, which is gitignored because generated applications
contain personal information. The resume comes two ways — see "The two
resume copies" above — and the cover letter as a finished PDF. The evidence
map, strategy and ATS report render as denser internal reports.

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
