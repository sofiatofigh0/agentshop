"""
Deterministic generation workflow, run after the agent decides a role is worth
pursuing.

Nothing in here is agentic. There is no loop and no tool use — Python calls the
model in a fixed order and writes files to fixed paths:

    evidence map  ->  resume draft  ->  factuality check  ->  final resume
                  ->  cover letter
                  ->  application strategy

The three branches after the evidence map depend on nothing but the map, so
they run concurrently. That is a wall-clock change only: same calls, same
prompts, same cost.

The evidence map comes first on purpose. Asking for a resume directly produces
keyword stuffing; asking first "which requirement does each experience actually
answer, and how strongly" forces the selection to be justified before any prose
gets written.

All model prompts for the generation stage live in this file.
"""

import copy
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import anthropic

from documents import fit_pdf, page_count, write_pdf

from candidate_profile import CANDIDATE_PROFILE
from experience_bank import EXPERIENCE_BANK, missing_fields

# Python owns the output paths. The model never chooses where anything is saved.
OUTPUT_DIR = "outputs"

def _generation_facts() -> str:
    """The bank as the generator sees it.

    Two things are removed, which saves tokens AND is safer:

    - `possible_metric_to_validate` blocks. Previously they were sent with an
      instruction not to use them. Not sending them at all is strictly better:
      the model cannot misuse a number it never saw.
    - `interview_stories`. Only the strategy document needs them, so they ride
      on that one call's user message instead of all six system prompts.
    """
    bank = copy.deepcopy(EXPERIENCE_BANK)
    for role in bank["roles"]:
        for project in role["projects"]:
            project.pop("possible_metric_to_validate", None)
    for project in bank["personal_projects"]:
        project.pop("possible_metric_to_validate", None)
    STORIES.extend(bank.pop("interview_stories", []))
    return json.dumps(bank, indent=2)


STORIES: list = []
FACTS = _generation_facts()
PROFILE = json.dumps(CANDIDATE_PROFILE, indent=2)

# The rule every writing prompt inherits. Stated once, repeated by reference.
GROUND_RULES = """The EXPERIENCE BANK below is the only source of facts about
this candidate. You may reword, reorder, shorten, expand, choose what to
emphasize, and mirror the job description's terminology where it is truthful.

You may NOT invent experience, metrics, technologies, tools, certifications, or
management responsibility. You may not change employers, official titles, or
dates, and you may not imply more seniority than the bank shows. If the job
asks for something the bank does not support, treat it as a gap and say so
plainly rather than writing around it.

Every claim in the bank carries a `source`. Three are usable:

  verified_resume     appears on the candidate's existing resume
  candidate_provided  stated directly by the candidate
  supported_inference a reading of verified work the candidate has approved

One is NOT usable, ever, in any document, however hedged:

  needs_validation    an open question, not an achievement

Claims also carry a `type` that governs how precisely you may state them:

  verified_metric               state it exactly as written
  approximate_supported_metric  a real measurement stated loosely. Keep the
                                approximation language ("~", "approximately",
                                "roughly", "more than"). Never sharpen it into a
                                precise figure.

Other fields:

  framing         approved interpretations. Safe to use.
  metric_variants separate measurements of ONE project. Choose exactly one per
                  bullet, guided by its `use_when`. Never combine, sum, or
                  present two as if they measure the same thing.
  metric_warning / caveat / note / label_rule / scale_caveat / positioning
                  restrictions on how something may be said. Obey them exactly.

You may improve framing aggressively. You may never manufacture a number.

Use the bank's own wording for tenure and seniority rather than computing your
own. Personal background never enters a resume by default — only where the
profile's policy says it creates a genuinely relevant narrative."""


# When the agent did not judge the role a clear fit, the candidate may still
# choose to apply. The materials then have to carry an argument the reader will
# not construct on their own. This block is appended to the step instructions —
# never to the cached prefix, which must stay byte-identical — so a stretch run
# costs a few hundred extra input tokens and nothing else.
STRETCH_BRIEF = """

STRETCH APPLICATION — the agent did not judge this role a clear fit, and the
candidate has read that judgement and is applying anyway.

The reader will not do the translating. If the application only lists what the
candidate has done, a reviewer scanning for the posting's own words will not
see the match, and the strongest evidence gets discarded for being described in
the wrong vocabulary. So argue from the SHAPE of the work rather than its label.

- Take each HIGH-priority requirement the candidate does not match head-on and
  find the closest thing they have actually done. Make the transfer explicit:
  what was structurally the same about the problem, the constraint, the users,
  the stakes or the scale.
- Lead with transferable substance, not domain. When the posting sits in an
  industry or function the candidate has not worked in, open on the problem
  they have solved before, not on the industry they have not.
- Where the bank genuinely supports the underlying capability, describe it in
  the posting's vocabulary rather than the candidate's. Reframing real work in
  the reader's language is the entire job here.

Three hard limits, because a stretch is exactly where applications start lying:

- Never invent domain experience, a tool, a title, a metric or a scope to close
  a gap. A gap closed by translation is persuasive; a gap closed by fabrication
  ends the application. Where nothing honestly transfers, say nothing — an
  unaddressed requirement costs far less than one answered with fiction.
- Reframing is not promotion. The underlying claim must stay exactly as true as
  the bank states it, at the same seniority, scope and precision.
- Never mention that this is a stretch. No apologising, no flagging thin
  experience, no "while I have not directly...". The documents an employer
  receives make the positive case and stop; the honest accounting of what is
  missing belongs in the evidence map and the strategy brief, which the
  employer never sees.
"""


# Everything below is byte-identical on all six generation calls, so it is sent
# once as a cached prefix and read back at a fraction of the cost on the other
# five. Prompt caching is prefix-matched, so the stable material must come first
# and the per-step instructions second — swapping the order caches nothing.
STABLE_PREFIX = f"""{GROUND_RULES}

EXPERIENCE BANK — the only source of facts about this candidate:
{FACTS}

CANDIDATE PREFERENCES — context for tone and motivation, never a source of facts:
{PROFILE}
"""


def _call(step_instructions: str, user: str, max_tokens: int = 8000) -> tuple:
    """One plain model call. Returns (text, usage).

    No tools here — this stage is a fixed pipeline, not an agent loop.
    """
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=os.environ["ANTHROPIC_MODEL"],
        max_tokens=max_tokens,
        system=[
            {"type": "text", "text": STABLE_PREFIX, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": step_instructions},
        ],
        messages=[{"role": "user", "content": user}],
    )
    text = "\n".join(b.text for b in response.content if b.type == "text").strip()
    if not text:
        # Malformed / empty response — fail loudly rather than write an empty file.
        raise RuntimeError(
            f"The model returned no text (stop_reason={response.stop_reason})."
        )
    return text, response.usage


# --------------------------------------------------------------------------
# Step 1: requirement -> evidence map
# --------------------------------------------------------------------------

EVIDENCE_MAP_PROMPT = """You map job requirements to concrete evidence.

Read the job description and produce a markdown table with one row per
important requirement, strongest first:

| Requirement | Priority | Evidence | Where it comes from | Metric | Strength | Gap |

- Priority is HIGH, MEDIUM or LOW — how much this requirement actually matters
  for the role, judged from how the posting treats it.
- Evidence is the specific thing the candidate did that answers it.
- Where it comes from names the exact role and project in the experience bank.
- Metric is a number from the bank, or "—" if there isn't one.
- Strength is STRONG, PARTIAL or NONE.
- Gap describes what is missing when strength is PARTIAL or NONE, otherwise "—".

Do not pad the table with weak rows to make the candidate look better. A NONE
row is more useful than a stretched one.

After the table, write two short sections: "Strongest angles" (the two or three
rows to build the whole application around) and "Real gaps" (what genuinely
isn't there).
"""

# Added to the evidence map only on a stretch run. The table above stays
# honest — PARTIAL and NONE keep their meaning — and this asks separately for
# the translation the resume and letter will be built on.
EVIDENCE_MAP_BRIDGES = """
Then add a third section, "Bridges". For each HIGH-priority requirement that
came out PARTIAL or NONE, give one row:

| Requirement | Closest real experience | Why it transfers |

"Why it transfers" is the actual argument — the structural similarity in the
problem, constraint, users or scale — not a restatement of the evidence. Write
"no honest bridge" where nothing in the bank genuinely transfers, and leave it
at that. A fabricated bridge is worse than an admitted gap, and this section is
what the resume and cover letter will be built on.
"""


def build_evidence_map(job_description: str, research: str = "", stretch: str = "") -> tuple:
    """Work out which experience answers which requirement, before writing prose."""
    user = f"JOB DESCRIPTION:\n{job_description}"
    if research:
        user += f"\n\nCOMPANY RESEARCH:\n{research}"
    prompt = EVIDENCE_MAP_PROMPT + (EVIDENCE_MAP_BRIDGES + stretch if stretch else "")
    return _call(prompt, user)


# --------------------------------------------------------------------------
# Step 2: resume draft
# --------------------------------------------------------------------------

RESUME_PROMPT = """You write tailored resumes in clean markdown.

Write a resume for this specific job, guided by the evidence map you are given.
Rows marked STRONG earn the most space and the highest position; rows marked
NONE must not be papered over.

Emit EXACTLY this structure. The renderer routes these sections into a
two-column template, so the headings and the order of the first three lines
matter:

# <full name>
**<professional title, aimed at this role — at most five words and 42
characters, e.g. "AI Product Manager" or "Platform Product Manager". It sits
beside the contact block and must not wrap.>**
<one contact line, items separated by " · ">

## Profile
<three or four lines of prose, aimed at this role>

## Skills
- <six to nine short skill phrases, most relevant first>

## Experience
### <Role> — <Company> | <dates>
<optional single line describing the employer or scope>
- <bullet>
- <bullet>

### <Role> — <Company> | <dates>
- <bullet>

## Selected Projects
- **<name>** — <one line>

## Education
**<credential>**
<institution> · <dates>

Rules for that structure:
- The contact line must include the portfolio URL and, when one is set, its
  password, since a gated link without the password is worse than no link.
- Roles go newest first UNLESS a less recent role is markedly more relevant to
  this job, in which case lead with that one.
- The pipe before the dates is required — it is how the renderer right-aligns
  them. Keep every date exactly as the bank states it.
- Profile, Skills and Education render in the narrow left column; Experience and
  Selected Projects render in the wide right column. Keep left-column content
  short so it does not outrun the right.
- Omit Selected Projects entirely if nothing there answers a requirement.
- No other top-level sections.

This is a document the candidate submits to an employer. It must contain ONLY
the resume. Never add a section assessing fit, listing gaps, weaknesses,
caveats, "honest notes", or anything else addressed to the candidate rather
than the employer — the gaps belong in the evidence map and the strategy
document, which the employer never sees. End after the last resume section.
"""


def write_resume(job_description: str, evidence_map: str, stretch: str = "") -> tuple:
    """Draft the resume from the evidence map."""
    user = (
        f"JOB DESCRIPTION:\n{job_description}\n\n"
        f"EVIDENCE MAP:\n{evidence_map}"
    )
    return _call(RESUME_PROMPT + stretch, user)


# --------------------------------------------------------------------------
# Step 3: factuality check — deliberately a separate call
# --------------------------------------------------------------------------

FACTUALITY_PROMPT = """You are a factuality reviewer. You did not write this
resume and you have no interest in it looking good.

Go through the draft claim by claim — every employer, title, date, metric,
technology, scope claim and seniority implication. For each one, decide whether
the experience bank supports it:

SUPPORTED           the bank states this, or it is a fair rewording, or it is
                    listed under that project's `framing`
PARTIALLY SUPPORTED the bank hints at it but the draft goes further
UNSUPPORTED         the bank does not contain this at all

Treat these as UNSUPPORTED even though the words appear in the bank:
- anything whose `source` is `needs_validation`
- an `approximate_supported_metric` restated as a precise figure, with its "~",
  "approximately" or "roughly" dropped
- two `metric_variants` from one project combined, summed, or used as if they
  measure the same thing
- any claim that breaks a `metric_warning`, `caveat`, `label_rule` or
  `scale_caveat`
- a metric restated without the timeframe the bank gives it
- an expected value presented as a measured outcome
- a personal project described as commercial, production-scale, or as having users
- any tenure claim that does not match the bank's own wording

Output a markdown table: | Claim | Verdict | Basis in the bank |

List SUPPORTED claims briefly; spend your attention on the other two. Then
write a section headed exactly "REQUIRED FIXES" listing each PARTIALLY
SUPPORTED or UNSUPPORTED claim and how to correct it — usually by cutting it or
weakening it to what the bank actually says. If everything checks out, write
"REQUIRED FIXES" followed by "None."
"""


def check_factuality(resume_draft: str) -> tuple:
    """Second opinion on the draft. Returns the review, not a verdict."""
    return _call(FACTUALITY_PROMPT, f"DRAFT RESUME:\n{resume_draft}")


REVISION_PROMPT = """You are correcting a resume that failed a factuality
review. Apply every fix the review asks for — cut or weaken the offending
claims — and change nothing else. Return the corrected resume in full, in
markdown, with no commentary.
"""


def revise_resume(resume_draft: str, review: str) -> tuple:
    """Rewrite the draft to remove unsupported claims."""
    user = f"DRAFT RESUME:\n{resume_draft}\n\nFACTUALITY REVIEW:\n{review}"
    return _call(REVISION_PROMPT, user)


def review_found_problems(review: str) -> bool:
    """Deterministic gate: does the review demand changes?

    Python decides whether a revision pass happens, by reading the review's
    verdict vocabulary. The model does not get to wave its own draft through.
    """
    upper = review.upper()
    if "UNSUPPORTED" in upper or "PARTIALLY SUPPORTED" in upper:
        # The words appear in the instructions' vocabulary too, so confirm the
        # review actually asked for fixes.
        after = upper.split("REQUIRED FIXES", 1)[-1]
        return "NONE." not in after[:40]
    return False


# --------------------------------------------------------------------------
# Step 4: cover letter
# --------------------------------------------------------------------------

COVER_LETTER_PROMPT = """You write short, specific cover letters.

Write a cover letter for this role. Under 330 words — it must fit on one
printed page with the letterhead, and shorter reads more confident anyway. Build it on the two or
three strongest rows of the evidence map — do not restate the resume bullet by
bullet. Be concrete about why this company and this role.

COMPANY RESEARCH IS UNVERIFIED. It came from a web search and nothing has
checked it. Use it for FRAMING ONLY — to decide which of the company's problems
to engage with and which angle to take. Never ASSERT it in the letter. Do not
name acquisitions, funding rounds, executives, launches, product names,
headcount, or quotes that came from research, and do not paraphrase them as
though they were established. Getting one of those wrong in a cover letter is
worse than omitting it, and the reader knows their own company better than the
search does.

  Good: research indicates an evaluation-tooling company, so the letter engages
        with what it takes to make generative output trustworthy at scale.
  Bad:  "your recent Series B", "post-Arcus", "as your CTO said last month".

Every concrete fact stated in the letter must come from either the job
description itself — which the reader wrote, so it is safe to reference — or the
candidate's own experience bank.

No "I am excited to apply", no "passionate about", no flattery the candidate
could not defend in a room. Open with the specific reason they are a fit, spend
the middle on evidence, and close with a plain statement of interest.

Format it as a letter. Begin with exactly these two lines, which become the
letterhead:

# <candidate name>
<location> · <email> · <phone> · <linkedin>

Then the greeting, the body paragraphs, and the candidate's name to sign off.
Take the contact details from the experience bank's identity block; omit any
that are empty rather than inventing them. If a portfolio URL is present and a
portfolio_password is set, always give them together — for example
"sofia-tofigh.netlify.app (password: xxxx)". A gated link without its password
is worse than no link at all.
"""


def write_cover_letter(job_description: str, evidence_map: str, research: str = "",
                      stretch: str = "") -> tuple:
    user = f"JOB DESCRIPTION:\n{job_description}\n\nEVIDENCE MAP:\n{evidence_map}"
    if research:
        user += f"\n\nCOMPANY RESEARCH:\n{research}"
    return _call(COVER_LETTER_PROMPT + stretch, user, max_tokens=4000)


# --------------------------------------------------------------------------
# Step 5: application strategy
# --------------------------------------------------------------------------

STRATEGY_PROMPT = """You brief candidates before they apply.

Write a strategy document in markdown with exactly these sections, in order:

## Recommendation
## Why
## Top 5 reasons this candidate fits
## Top 3 gaps or risks
## What to emphasize in the application
## Three experiences to emphasize in interviews
## Likely interview questions
## What NOT to emphasize
## Company-specific notes from research

Under "Likely interview questions", give each question its own line and name
the specific experience from the bank that should answer it. Under "Company-
specific notes from research", write "No research was gathered." if none was —
and where research is included, mark it as unverified and worth confirming,
since this document is the candidate's own briefing rather than something the
employer sees.

Be direct about the gaps. A brief that only flatters is useless.
"""


def write_strategy(
    job_description: str, evidence_map: str, recommendation: str,
    reasoning: str, research: str = "",
) -> tuple:
    user = (
        f"JOB DESCRIPTION:\n{job_description}\n\n"
        f"EVIDENCE MAP:\n{evidence_map}\n\n"
        f"THE AGENT'S VERDICT: {recommendation}\nITS REASONING: {reasoning}\n\n"
        f"PREPARED INTERVIEW STORIES:\n{json.dumps(STORIES, indent=2)}"
    )
    if research:
        user += f"\n\nCOMPANY RESEARCH:\n{research}"
    return _call(STRATEGY_PROMPT, user)


# --------------------------------------------------------------------------
# The pipeline
# --------------------------------------------------------------------------

def slugify(company: str, role: str) -> str:
    """A short, sortable folder name for one application.

    Company and role are trimmed separately. The model sometimes returns a role
    with trailing prose attached — "Partnerships Product Manager (reports
    directly to the Head of Product)" — so the role is cut at the first bracket
    or dash and then capped, which keeps the folder name readable.
    """
    def clean(value: str, words: int) -> str:
        value = re.split(r"[(\[|]|\s[-—–]\s", value)[0]
        return "-".join(re.sub(r"[^a-z0-9\s]+", " ", value.lower()).split()[:words])

    slug = "-".join(part for part in (clean(company, 3), clean(role, 5)) if part)
    return f"{datetime.now():%Y-%m-%d}-{slug or 'application'}"


def generate_application_package(
    job_description: str, recommendation: str, reasoning: str, research: str = "",
    company: str = "", role: str = "", progress=print,
) -> dict:
    """Run every generation step in order and write the files.

    Each run gets its own folder under outputs/, named by date, company and
    role, so a later run never overwrites an earlier one and the folder name
    says what the application was for. `progress` receives a line per stage,
    which is how the web UI shows what the run is doing.
    """
    gaps = missing_fields()
    if gaps:
        raise RuntimeError(
            "experience_bank.py still has "
            f"{len(gaps)} placeholder field(s) — for example {gaps[0]}.\n"
            "Fill them in before generating application materials: the agent "
            "will not invent experience to fill the space."
        )

    # Python owns file creation, not the model.
    run_dir = os.path.join(OUTPUT_DIR, slugify(company, role))
    os.makedirs(run_dir, exist_ok=True)

    # Usage is collected per call and totalled after every call has finished,
    # so the parallel steps below never race on a running total.
    usages = []

    def run(step):
        text, usage = step
        usages.append(usage)   # list.append is atomic, so threads may call this
        return text

    # Anything short of APPLY means the agent saw a real distance between this
    # candidate and this posting. The materials still get written when the
    # candidate asks for them, but they get written differently.
    stretch = STRETCH_BRIEF if recommendation.strip().upper() != "APPLY" else ""
    if stretch:
        progress(f"{recommendation} — writing for a stretch: bridging experience "
                 "to the posting's own requirements")

    progress("building requirement-to-evidence map...")
    evidence_map = run(build_evidence_map(job_description, research, stretch))

    # The evidence map is the only step the rest depends on. After it, the
    # resume chain, the cover letter and the strategy share no inputs, so they
    # run at the same time rather than one after another — the same six calls,
    # the same cost, roughly the time of three. The map's call has already
    # written the cached prefix, so these read it instead of each writing a
    # copy of their own, which is why the fan-out starts here and not earlier.
    def resume_chain():
        draft = run(write_resume(job_description, evidence_map, stretch))
        review = run(check_factuality(draft))
        if review_found_problems(review):
            progress("resume: unsupported claims found — revising...")
            return run(revise_resume(draft, review)), review
        progress("resume: all claims supported.")
        return draft, review

    def cover_letter_step():
        text = run(write_cover_letter(job_description, evidence_map, research, stretch))
        progress("cover letter written.")
        return text

    def strategy_step():
        text = run(
            write_strategy(job_description, evidence_map, recommendation, reasoning, research)
        )
        progress("application strategy written.")
        return text

    # These lines arrive interleaved, so each one names its own document.
    progress("writing resume, cover letter and strategy...")
    with ThreadPoolExecutor(max_workers=3) as pool:
        pending_resume = pool.submit(resume_chain)
        pending_letter = pool.submit(cover_letter_step)
        pending_strategy = pool.submit(strategy_step)
        resume, review = pending_resume.result()
        cover_letter = pending_letter.result()
        strategy = pending_strategy.result()

    calls = len(usages)
    input_tokens = sum(u.input_tokens for u in usages)
    output_tokens = sum(u.output_tokens for u in usages)
    cache_written = sum(getattr(u, "cache_creation_input_tokens", 0) or 0 for u in usages)
    # If cache_read stays at zero across a run, something is silently
    # invalidating the prefix and the saving is not happening.
    cache_read = sum(getattr(u, "cache_read_input_tokens", 0) or 0 for u in usages)

    # The model writes markdown; documents.py decides how each one looks. The
    # two documents an employer receives get document typography; the internal
    # working files get a denser report layout.
    outputs = (
        ("resume", "tailored_resume.pdf", resume, "resume"),
        ("cover_letter", "cover_letter.pdf", cover_letter, "letter"),
        ("evidence_map", "evidence_map.pdf", evidence_map, "report"),
        ("factuality_review", "factuality_review.pdf", review, "report"),
        ("strategy", "application_strategy.pdf", strategy, "report"),
    )
    files = {}
    for key, name, body, style in outputs:
        path = os.path.join(run_dir, name)
        if style in ("resume", "letter"):
            # One page, achieved by tightening the setting rather than by
            # deleting evidence. Nothing the model wrote is removed.
            pages, pt = fit_pdf(body, path, style)
            if pages > 1:
                progress(f"{name}: {pages} pages even at {pt}pt — too much content to fit")
            else:
                progress(f"{name}: fitted to one page at {pt}pt")
        else:
            write_pdf(body, path, style)

        files[key] = path

    # A record of what this application was, so months later the folder is not
    # a mystery. This is the thing that was missing when five identically named
    # PDFs sat in one directory.
    with open(os.path.join(run_dir, "run.json"), "w") as handle:
        json.dump({
            "company": company,
            "role": role,
            "recommendation": recommendation,
            "reasoning": reasoning,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "job_description": job_description,
            "research_performed": bool(research),
            "written_as_stretch": bool(stretch),
        }, handle, indent=2)

    return {
        "run_dir": run_dir,
        "files": files,
        "generation_calls": calls,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_written": cache_written,
        "cache_read": cache_read,
    }
