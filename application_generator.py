"""
Deterministic generation workflow, run after the agent decides a role is worth
pursuing.

Nothing in here is agentic. There is no loop and no tool use — Python calls the
model in a fixed order and writes files to fixed paths:

    evidence map  ->  resume draft  ->  factuality check  ->  final resume
                  ->  cover letter
                  ->  application strategy

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


def build_evidence_map(job_description: str, research: str = "") -> tuple:
    """Work out which experience answers which requirement, before writing prose."""
    user = f"JOB DESCRIPTION:\n{job_description}"
    if research:
        user += f"\n\nCOMPANY RESEARCH:\n{research}"
    return _call(EVIDENCE_MAP_PROMPT, user)


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


def write_resume(job_description: str, evidence_map: str) -> tuple:
    """Draft the resume from the evidence map."""
    user = (
        f"JOB DESCRIPTION:\n{job_description}\n\n"
        f"EVIDENCE MAP:\n{evidence_map}"
    )
    return _call(RESUME_PROMPT, user)


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


def write_cover_letter(job_description: str, evidence_map: str, research: str = "") -> tuple:
    user = f"JOB DESCRIPTION:\n{job_description}\n\nEVIDENCE MAP:\n{evidence_map}"
    if research:
        user += f"\n\nCOMPANY RESEARCH:\n{research}"
    return _call(COVER_LETTER_PROMPT, user, max_tokens=4000)


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

    calls = 0
    input_tokens = 0
    output_tokens = 0
    cache_written = 0
    cache_read = 0

    def run(step):
        nonlocal calls, input_tokens, output_tokens, cache_written, cache_read
        text, usage = step
        calls += 1
        input_tokens += usage.input_tokens
        output_tokens += usage.output_tokens
        # If cache_read stays at zero across a run, something is silently
        # invalidating the prefix and the saving is not happening.
        cache_written += getattr(usage, "cache_creation_input_tokens", 0) or 0
        cache_read += getattr(usage, "cache_read_input_tokens", 0) or 0
        return text

    progress("  building requirement-to-evidence map...".strip())
    evidence_map = run(build_evidence_map(job_description, research))

    progress("  drafting resume...".strip())
    draft = run(write_resume(job_description, evidence_map))

    progress("  checking every claim against the experience bank...".strip())
    review = run(check_factuality(draft))

    if review_found_problems(review):
        progress("  unsupported claims found — revising...".strip())
        resume = run(revise_resume(draft, review))
    else:
        progress("  all claims supported.".strip())
        resume = draft

    progress("  writing cover letter...".strip())
    cover_letter = run(write_cover_letter(job_description, evidence_map, research))

    progress("  writing application strategy...".strip())
    strategy = run(
        write_strategy(job_description, evidence_map, recommendation, reasoning, research)
    )

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
