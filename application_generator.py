"""
Deterministic generation workflow, run after the agent decides a role is worth
pursuing.

Nothing in here is agentic. There is no loop and no tool use — Python calls the
model in a fixed order and writes files to fixed paths:

    evidence map  ->  resume draft  ->  [rephrasing pass]  ->  factuality check
    + ATS keywords                  ->  final resume
                  ->  cover letter
                  ->  application strategy
                  ->  ATS report (plain Python, no model)

The three branches after the evidence map depend on nothing but the map, so
they run concurrently. That is a wall-clock change only: same calls, same
prompts, same cost.

The evidence map comes first on purpose. Asking for a resume directly produces
keyword stuffing; asking first "which requirement does each experience actually
answer, and how strongly" forces the selection to be justified before any prose
gets written.

The ATS pass runs the other way round from the tools it borrows the idea from.
Simplify and Jobscan score a resume against the posting's terms and tell the
candidate what to add. Here the score is computed the same way, but a missing
term is only ever picked up by rewording a sentence that already says the
thing — and only if the experience bank so much as mentions it. Everything
else is reported as a gap. The factuality review runs after the rewording,
not before, so nothing the pass does escapes it.

All model prompts for the generation stage live in this file.
"""

import copy
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import anthropic

from documents import INSTALL_HINT, fit_pdf, page_count, write_pdf, write_resume_docx

import ats
import lessons
import models

from candidate_profile import CANDIDATE_PROFILE
from experience_bank import EXPERIENCE_BANK, missing_fields
from models import Spend, cache_control, main_model, request_options, worker_model

# Python owns the output paths. The model never chooses where anything is saved.
OUTPUT_DIR = "outputs"

# The markdown each PDF was rendered from, kept beside it. The folder still
# contains only PDFs as far as anything that lists it is concerned, but the
# source survives, which is what makes a generated document editable after the
# fact: an edit re-renders from markdown rather than trying to rewrite a PDF.
SOURCES_FILE = "sources.json"

# The posting's keywords and each document's score, kept beside the PDFs so an
# edit can be re-scored without another model call.
ATS_FILE = "ats.json"
ATS_REPORT = "ats_report.pdf"

# The resume is one markdown source rendered three ways (see documents.py).
# tailored_resume.pdf is the single-column upload copy and the one sources.json
# names; the other two are always rebuilt from the same text beside it.
RESUME_PDF = "tailored_resume.pdf"
RESUME_DOCX = "tailored_resume.docx"
RESUME_DESIGNED = "resume_designed.pdf"


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
    BANK_FOR_MATCHING.update(bank)
    return json.dumps(bank, indent=2)


STORIES: list = []
BANK_FOR_MATCHING: dict = {}
FACTS = _generation_facts()
PROFILE = json.dumps(CANDIDATE_PROFILE, indent=2)

# The bank as running text, for deciding which missing keywords are even worth
# a look. Built from the same trimmed copy the model sees, so an unconfirmed
# claim cannot make a keyword look supported.
BANK_PROSE = ats.bank_prose(BANK_FOR_MATCHING)

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


# Everything below is byte-identical on every generation call of every run, so
# it is written to the cache once and read back at a fraction of the cost on
# the rest. Prompt caching is prefix-matched, so the stable material must come
# first, the per-run material second, and the per-step instructions last —
# swapping the order caches nothing.
STABLE_PREFIX = f"""{GROUND_RULES}

EXPERIENCE BANK — the only source of facts about this candidate:
{FACTS}

CANDIDATE PREFERENCES — context for tone and motivation, never a source of facts:
{PROFILE}
"""


def run_context(job_description: str, research: str = "") -> str:
    """The per-run material every step reads: the posting and any research.

    It sits in the system prompt behind its own cache marker, after the stable
    prefix and before the step instructions. The evidence-map call writes it;
    every later call of the run reads it back instead of re-sending it in the
    user message, which is where it used to travel at full price six times.
    """
    context = f"JOB DESCRIPTION — the posting these documents are for:\n{job_description}\n"
    if research:
        context += f"\nCOMPANY RESEARCH — from a web search, unverified:\n{research}\n"
    return context


def _call(step: str, instructions: str, user: str, context: str = "",
          max_tokens: int = 8000) -> tuple:
    """One plain model call. Returns (text, usage).

    No tools here — this stage is a fixed pipeline, not an agent loop. `step`
    names the effort the call runs at; `context` is the per-run block, left out
    of the calls that must not be looking at the posting (the factuality
    review judges the draft against the bank and nothing else).

    Every call here sends the same two cached system blocks, so the top-level
    effort has to stay identical between them — a change there would rewrite
    the prefix rather than read it. A step that wants less depth says so in a
    `messages` entry instead, which the system cache survives. An account
    without that beta gets one rejected call, after which the stage runs at
    the default depth for the rest of the process.
    """
    system = [{"type": "text", "text": STABLE_PREFIX,
               "cache_control": cache_control(long_lived=True)}]
    if context:
        system.append({"type": "text", "text": context, "cache_control": cache_control()})
    system.append({"type": "text", "text": instructions})

    model = main_model()
    client = anthropic.Anthropic()
    kwargs = dict(model=model, max_tokens=max_tokens, system=system,
                  **request_options(step, model))
    turn = {"role": "user", "content": user}

    depth = models.effort_message(step, model)
    response = None
    if depth is not None:
        try:
            response = client.beta.messages.create(
                betas=[models.PER_MESSAGE_EFFORT_BETA],
                messages=[depth, turn], **kwargs,
            )
        except anthropic.BadRequestError:
            # The beta is not available here. Stop trying, and run this step
            # at the default depth like the rest of the stage.
            models.disable_per_message_effort()
    if response is None:
        response = client.messages.create(messages=[turn], **kwargs)

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


def build_evidence_map(context: str, guidance: str = "", stretch: str = "") -> tuple:
    """Work out which experience answers which requirement, before writing prose."""
    prompt = EVIDENCE_MAP_PROMPT + (EVIDENCE_MAP_BRIDGES if stretch else "") + guidance
    return _call("evidence_map", prompt,
                 "Build the evidence map for the JOB DESCRIPTION given above.", context)


# --------------------------------------------------------------------------
# Step 2: resume draft
# --------------------------------------------------------------------------

RESUME_PROMPT = """You write tailored resumes in clean markdown.

Write a resume for this specific job, guided by the evidence map you are given.
Rows marked STRONG earn the most space and the highest position; rows marked
NONE must not be papered over.

Emit EXACTLY this structure. It is set in one column, in this order, as the
copy uploaded to applicant tracking systems — a screening system reads the page
as one stream of text and files each section by its heading, so the headings,
their order and the first three lines all matter. The same text is also set as
a two-column designed copy for people.

# <full name>
**<the posting's exact job title — see "The title line" below>**
<one contact line, items separated by " · ">

## Summary
<three or four lines of prose, aimed at this role; the first sentence uses the
title line's title, verbatim>

## Skills
- <six to nine short skill phrases, most relevant first>

## Work Experience
### <Role> — <Company> | <dates>
<optional single line describing the employer or scope>
- **<project, two or three words>** — <what was done, and what came of it>
- **<project, two or three words>** — <what was done, and what came of it>

### <Role> — <Company> | <dates>
- <a plain bullet, where the work was not one discrete project>

## Projects
- **<name>** — <one line>

## Education
**<credential>**
<institution> · <dates>

The title line:
- It is the posting's own job title, word for word. If the posting says
  "Senior Product Manager", the line says "Senior Product Manager" — not
  "Product Lead", not "AI Product Manager", not a creative variant. Recruiters
  find candidates by searching the tracking system for the title, and that
  match is literal: a synonym is simply not found.
- It fits on one line at 42 characters. When the full title is longer, keep
  its core — the words before the first comma, dash or bracket — exactly as
  the posting writes them ("Senior Product Manager, Generative AI Platform
  Experiences" becomes "Senior Product Manager"). Shorten; never paraphrase.
- It names the role applied for, not a past title, so it may match no title
  in the bank. It may still not overstate seniority. If the posting's title
  claims a level the bank and the candidate's positioning do not support —
  Director, Head of, VP, Principal, Staff, Group, or a Lead who manages other
  PMs — replace only that level with the highest one they do support and keep
  the posting's other words ("Director of Product, Payments" becomes "Senior
  Product Manager, Payments").
- The Summary's first sentence repeats the same title in a true sentence,
  because some systems weight the summary as heavily as the headline.

Rules for that structure:
- The contact line must include the portfolio URL and, when one is set, its
  password, since a gated link without the password is worse than no link.
  Write every URL as plain text (sofia-tofigh.netlify.app), never as a
  markdown link: a parser stores the text it can read, not the link behind a
  label.
- Use exactly the section headings shown — Summary, Skills, Work Experience,
  Projects, Education. A parser files each section by its heading; one it does
  not recognise lands in a field nobody searches.
- No icons, emoji, symbols or decorative characters anywhere — no phone or
  envelope glyphs, stars, checkmarks or arrows. To a parser they are noise,
  and next to contact details they can garble the details themselves.
- Open each Experience bullet with the project it is about, in two or three
  words, bold, then an em dash: "**Advisor summarization** — Shipped an LLM
  pipeline that...". A reviewer scans the left edge of the bullets before
  reading a single full sentence, and those labels are what tell them the
  kinds of problems this candidate has worked on.
    - The label names the project, not the candidate's role in it, and it is
      the experience bank's own name for that project, shortened. Never invent
      a project, a product name or a codename to have something to put there.
    - Two or three words. A label long enough to wrap is a headline, not a
      signpost, and it costs the line the evidence needs.
    - Label and sentence stay on one line together wherever the content
      allows it.
- Do NOT label a bullet that is not about one discrete project. Ongoing
  responsibilities, ways of working, and advisory or consulting engagements
  described as a kind of work rather than a thing that shipped all stay plain
  sentences — the Confluent consulting work is the clear case. A label on work
  that was not a project reads as padding and tells the reviewer nothing.
- Roles go newest first UNLESS a less recent role is markedly more relevant to
  this job, in which case lead with that one.
- The pipe before the dates is required — it is how the renderer places
  them. Keep every date exactly as the bank states it, which gives one format
  throughout: Month Year - Month Year. Never mix formats ("Jan 2020",
  "2020-01", "January '20") — screening systems compute total experience from
  these ranges, and mixed formats make them miscount.
- In Education, list every entry the bank marks `include: "always"`, and an
  entry marked `include: "when_relevant"` only when its `use_when` genuinely
  fits this posting. Newest first. Where the bank gives only a year, write
  only the year; never invent a month.
- Keep Summary and Skills short: the designed copy sets Summary, Skills and
  Education in a narrow column that must not outrun the one beside it.
- Omit Projects entirely if nothing there answers a requirement.
- No other top-level sections.

This is a document the candidate submits to an employer. It must contain ONLY
the resume. Never add a section assessing fit, listing gaps, weaknesses,
caveats, "honest notes", or anything else addressed to the candidate rather
than the employer — the gaps belong in the evidence map and the strategy
document, which the employer never sees. End after the last resume section.
"""


def write_resume(context: str, evidence_map: str, guidance: str = "") -> tuple:
    """Draft the resume from the evidence map."""
    return _call("resume", RESUME_PROMPT + guidance, f"EVIDENCE MAP:\n{evidence_map}", context)


# --------------------------------------------------------------------------
# Step 2b: rephrasing for the posting's vocabulary — conditional
# --------------------------------------------------------------------------

PHRASING_PROMPT = """You are rewording a finished resume so that, where it
already describes work the posting asks for, it describes it in the posting's
own terms. A screening system matches exact terms; to it, a synonym scores
zero. To the reader, the posting's word is usually the clearer one anyway.

You are given the resume and a short list of the posting's terms, in two
groups. Terms SAID IN A DIFFERENT FORM are already on the page in other words
— the list names the words used — so reword that spot to the posting's exact
term. For terms NOT YET USED, look for a sentence, bullet, summary line or
skills entry that already says this thing in other words, and reword it to use
the term — changing the sentence's structure if that is what it takes to read
naturally.

What you may change: the wording and structure of sentences that are there.

What you may not do:
- add a bullet, a skills entry, a project, or a claim of any kind
- attach a term to a sentence that does not already mean it
- use a term the experience bank does not support, whatever the list says —
  the list came from a text search, not from judgement, and the judgement is
  yours
- repeat a term for effect, or bolt one onto the end of a sentence
- change any employer, title, date, metric, scope, or the document's structure
- treat a bullet's bold project label as a slot for a keyword. It names the
  project and stays two or three words; reword it only if the new wording is
  still that project's name. A bullet that has no label was left plain on
  purpose — the work was not one discrete project — so do not add one.

If a term cannot be worked in by rewording something that is already true,
leave it out. That is the expected outcome for part of the list; the report
will record it as a gap, which is the right answer.

Return the full resume in markdown, in exactly the structure you received, with
no commentary.
"""


def rephrase_resume(context: str, draft: str, offered: list) -> tuple:
    """Reword the draft toward the posting's terms — never add to it."""
    user = f"DRAFT RESUME:\n{draft}\n\n{ats.rephrase_block(offered)}"
    return _call("phrasing", PHRASING_PROMPT, user, context)


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

Two kinds of title appear, and they are judged differently:
- The bold line directly under the name is the title of the role being applied
  for, and the Summary's first sentence may repeat it. It is not a claim about
  any past position, so do not require it to match a title in the bank. Judge
  it on one thing: whether it implies more seniority than the bank supports
  (Director, Head of, VP, Principal, Staff, Group, or managing other PMs). If
  it does not, it is SUPPORTED.
- The title in each Work Experience role line is a claim about that job, and
  must match the bank's official title for it exactly.

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

Give the SUPPORTED claims one line each, at most; spend your attention on the
other two. Then write a section headed exactly "REQUIRED FIXES" listing each
PARTIALLY SUPPORTED or UNSUPPORTED claim and how to correct it — usually by
cutting it or weakening it to what the bank actually says. If everything
checks out, write "REQUIRED FIXES" followed by "None."
"""


def check_factuality(resume_draft: str) -> tuple:
    """Second opinion on the draft. Returns the review, not a verdict.

    Deliberately gets no job description: the question is whether the bank
    supports each claim, and the posting has no say in that.
    """
    return _call("factuality", FACTUALITY_PROMPT, f"DRAFT RESUME:\n{resume_draft}")


REVISION_PROMPT = """You are correcting a resume that failed a factuality
review. Apply every fix the review asks for — cut or weaken the offending
claims — and change nothing else. Return the corrected resume in full, in
markdown, with no commentary.
"""


def revise_resume(resume_draft: str, review: str) -> tuple:
    """Rewrite the draft to remove unsupported claims."""
    user = f"DRAFT RESUME:\n{resume_draft}\n\nFACTUALITY REVIEW:\n{review}"
    return _call("revision", REVISION_PROMPT, user)


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


def write_cover_letter(context: str, evidence_map: str, guidance: str = "") -> tuple:
    return _call("cover_letter", COVER_LETTER_PROMPT + guidance,
                 f"EVIDENCE MAP:\n{evidence_map}", context, max_tokens=4000)


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


def write_strategy(context: str, evidence_map: str, recommendation: str,
                   reasoning: str) -> tuple:
    user = (
        f"EVIDENCE MAP:\n{evidence_map}\n\n"
        f"THE AGENT'S VERDICT: {recommendation}\nITS REASONING: {reasoning}\n\n"
        f"PREPARED INTERVIEW STORIES:\n{json.dumps(STORIES, indent=2)}"
    )
    return _call("strategy", STRATEGY_PROMPT, user, context)


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


def _atomic(path: str, render) -> None:
    """Render to a scratch file and move it into place only once it exists, so
    a render that fails leaves the previous file intact."""
    draft = path + ".rendering"
    try:
        render(draft)
        os.replace(draft, path)
    finally:
        if os.path.exists(draft):
            os.remove(draft)


def render_resume_companions(markdown_text: str, run_dir: str, pt: float) -> dict:
    """Write the Word copy and the two-column designed copy of a resume.

    Called wherever the upload PDF is rendered — at generation and after every
    edit — so the copies can never describe different resumes. `pt` is the
    size the upload PDF fitted at, which the Word copy reuses.

    Neither copy is allowed to fail the caller. At generation this runs after
    every model call has been paid for, and an export that cannot be written
    must not throw away the run — the upload PDF, the letter and the reports
    still land. Each copy is attempted separately and whatever went wrong is
    returned, in words the candidate can act on.

    Returns {"written": [file, ...], "problems": [line, ...],
    "designed_pages": n or None, "designed_pt": pt or None}.
    """
    result = {"written": [], "problems": [], "designed_pages": None, "designed_pt": None}

    try:
        _atomic(os.path.join(run_dir, RESUME_DOCX),
                lambda draft: write_resume_docx(markdown_text, draft, pt or 10.0))
        result["written"].append(RESUME_DOCX)
    except ImportError:
        result["problems"].append(
            f"{RESUME_DOCX} skipped: python-docx is not installed. Run "
            f"`{INSTALL_HINT}` in this project's virtualenv, then re-run or edit "
            "the resume to get the Word copy.")
    except Exception as exc:
        result["problems"].append(
            f"{RESUME_DOCX} could not be written ({type(exc).__name__}: {exc}).")

    def designed(draft):
        result["designed_pages"], result["designed_pt"] = fit_pdf(
            markdown_text, draft, "resume_designed")

    try:
        _atomic(os.path.join(run_dir, RESUME_DESIGNED), designed)
        result["written"].append(RESUME_DESIGNED)
    except Exception as exc:
        result["problems"].append(
            f"{RESUME_DESIGNED} could not be written ({type(exc).__name__}: {exc}).")
    return result


def render_document(markdown_text: str, path: str, style: str) -> tuple:
    """Render one document to its final PDF. Returns (pages, body_pt).

    The only place a PDF is produced, so a document re-rendered after an edit
    gets exactly the typography it was generated with — including the one-page
    fit, which is why an edit cannot be applied to the PDF directly.
    """
    if style in ("resume", "letter"):
        return fit_pdf(markdown_text, path, style)
    write_pdf(markdown_text, path, style)
    return page_count(path), None


def write_ats_report(run_dir: str, data: dict, resume_md: str, letter_md: str) -> dict:
    """Score both documents, write ats_report.pdf and ats.json, return the scores.

    Every input is already on disk and nothing here calls a model, so this runs
    again after an edit — which is the only way the score the UI shows and the
    report it links can stay the same story. `data` is the ats.json payload:
    the posting's title, its keywords, the target, and what the rephrasing pass
    did, all of which belong to the run rather than to one document.
    """
    keywords = data.get("keywords") or []
    scores = {"resume": None, "cover_letter": None, "target": data.get("target")}

    if keywords:
        resume_scored = ats.score(keywords, resume_md)
        letter_scored = ats.score(keywords, letter_md) if letter_md else None
        candidates, real_gaps = ats.bank_supported(resume_scored["missing"], BANK_PROSE)
        report = ats.report(
            data, resume_scored, letter_scored, data.get("target"),
            candidates, real_gaps, ats.format_checks(resume_md),
            ats.title_match(data.get("title", ""), resume_md),
            ats.pdf_text_check(os.path.join(run_dir, RESUME_PDF), resume_scored["matched"]),
            data.get("rephrasing_pass"),
            order=ats.reading_order(os.path.join(run_dir, RESUME_PDF), resume_md),
            designed=(ats.reading_order(os.path.join(run_dir, RESUME_DESIGNED), resume_md)
                      if os.path.isfile(os.path.join(run_dir, RESUME_DESIGNED)) else None),
        )
        scores["resume"] = resume_scored["score"]
        scores["cover_letter"] = letter_scored["score"] if letter_scored else None
        data = dict(data, resume=ats.summary(resume_scored),
                    cover_letter=ats.summary(letter_scored) if letter_scored else None)
    else:
        report = ats.report(data, None, None, data.get("target"), [], [], [], {}, {})
        data = dict(data, resume=None, cover_letter=None)

    write_pdf(report, os.path.join(run_dir, ATS_REPORT), "report")
    _write_json(os.path.join(run_dir, ATS_FILE), data)
    return scores


def _write_json(path: str, payload) -> None:
    """Write one JSON file so a failure cannot leave it half-written.

    ats.json is read back on every later edit, so a truncated write would not
    fail once — it would fail every edit of that application afterwards.
    """
    draft = path + ".writing"
    with open(draft, "w") as handle:
        json.dump(payload, handle, indent=2)
    os.replace(draft, path)


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

    # Every call's usage lands here, priced as it arrives. The parallel steps
    # below all add to it; it locks internally.
    spend = Spend()

    def run(step):
        text, usage = step
        spend.add(main_model(), usage)
        return text

    # Anything short of APPLY means the agent saw a real distance between this
    # candidate and this posting. The materials still get written when the
    # candidate asks for them, but they get written differently.
    stretch = STRETCH_BRIEF if recommendation.strip().upper() != "APPLY" else ""
    if stretch:
        progress(f"{recommendation} — writing for a stretch: bridging experience "
                 "to the posting's own requirements")

    # What past edits taught, read now rather than at import: an edit made
    # earlier in this same session has to reach this run. Like the stretch
    # brief it rides on the step instructions, never the cached prefix.
    learned = lessons.prompt_block()
    if learned:
        progress(f"applying {len(lessons.load())} preference(s) learned from your edits")
    guidance = stretch + learned

    # The posting and the research, cached once for the whole run.
    context = run_context(job_description, research)
    target = ats.target_score()

    def keyword_step():
        """The posting's terms, on the worker model. A failure here costs the
        run its score, not its documents."""
        try:
            extracted, usage = ats.extract_keywords(job_description)
            spend.add(worker_model(), usage)
            progress(f"ATS: {len(extracted['keywords'])} terms extracted from the posting")
            return extracted
        except Exception as exc:
            progress(f"ATS: keyword extraction failed ({type(exc).__name__}) — "
                     "the documents will be written without a score")
            return {"title": "", "keywords": []}

    # The evidence map and the keyword extraction both need only the posting,
    # and share no prompt prefix, so they run side by side. The map's call is
    # the one that writes the cached prefix and the run context; everything
    # after it reads them.
    progress("building requirement-to-evidence map, extracting ATS keywords...")
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending_map = pool.submit(lambda: run(build_evidence_map(context, guidance, stretch)))
        pending_keywords = pool.submit(keyword_step)
        evidence_map = pending_map.result()
        extracted = pending_keywords.result()

    keywords = extracted["keywords"]
    keyword_block = ats.prompt_block(extracted)

    # The evidence map is the only step the rest depends on. After it, the
    # resume chain, the cover letter and the strategy share no inputs, so they
    # run at the same time rather than one after another — the same calls, the
    # same cost, roughly the time of three.
    def resume_chain():
        draft = run(write_resume(context, evidence_map, guidance + keyword_block))
        pass_info = None

        # One more call, only when it can honestly buy something: the draft
        # is below the target AND some missing term is at least mentioned in
        # the bank. A term the bank never mentions is a gap, and no call is
        # spent trying to close it.
        if keywords:
            scored = ats.score(keywords, draft)
            candidates, _ = ats.bank_supported(scored["missing"], BANK_PROSE)
            offered = ats.rephrase_offer(scored["variants"], candidates)
            if scored["score"] < target and offered:
                progress(f"ATS: draft resume scores {scored['score']}/100 — rewording for "
                         f"{len(offered)} term(s): {len(scored['variants'])} said in another "
                         "form, the rest mentioned in the bank...")
                reworded = run(rephrase_resume(context, draft, offered))
                rescored = ats.score(keywords, reworded)
                kept = rescored["score"] > scored["score"]
                # Which terms were put to it, not just how many: the report
                # says something different about a term the pass never saw.
                pass_info = {"considered": len(offered), "before": scored["score"],
                             "after": rescored["score"], "kept": kept,
                             "terms": [k["term"] for k in offered]}
                if kept:
                    draft = reworded
                progress(f"ATS: resume now {rescored['score'] if kept else scored['score']}/100")

        # The review reads whatever the rewording produced, so nothing that
        # pass did is outside the guardrail.
        review = run(check_factuality(draft))
        if review_found_problems(review):
            progress("resume: unsupported claims found — revising...")
            return run(revise_resume(draft, review)), review, pass_info
        progress("resume: all claims supported.")
        return draft, review, pass_info

    def cover_letter_step():
        text = run(write_cover_letter(context, evidence_map, guidance + keyword_block))
        progress("cover letter written.")
        return text

    def strategy_step():
        text = run(write_strategy(context, evidence_map, recommendation, reasoning))
        progress("application strategy written.")
        return text

    # These lines arrive interleaved, so each one names its own document.
    progress("writing resume, cover letter and strategy...")
    with ThreadPoolExecutor(max_workers=3) as pool:
        pending_resume = pool.submit(resume_chain)
        pending_letter = pool.submit(cover_letter_step)
        pending_strategy = pool.submit(strategy_step)
        resume, review, pass_info = pending_resume.result()
        cover_letter = pending_letter.result()
        strategy = pending_strategy.result()

    # The model writes markdown; documents.py decides how each one looks. The
    # two documents an employer receives get document typography; the internal
    # working files get a denser report layout.
    outputs = [
        ("resume", RESUME_PDF, resume, "resume"),
        ("cover_letter", "cover_letter.pdf", cover_letter, "letter"),
        ("evidence_map", "evidence_map.pdf", evidence_map, "report"),
        ("factuality_review", "factuality_review.pdf", review, "report"),
        ("strategy", "application_strategy.pdf", strategy, "report"),
    ]
    files = {}
    for key, name, body, style in outputs:
        path = os.path.join(run_dir, name)
        # One page, achieved by tightening the setting rather than by deleting
        # evidence. Nothing the model wrote is removed.
        pages, pt = render_document(body, path, style)
        if style in ("resume", "letter"):
            if pages > 1:
                progress(f"{name}: {pages} pages even at {pt}pt — too much content to fit")
            else:
                progress(f"{name}: fitted to one page at {pt}pt")
        if style == "resume":
            extra = render_resume_companions(body, run_dir, pt)
            if RESUME_DOCX in extra["written"]:
                files["resume_docx"] = os.path.join(run_dir, RESUME_DOCX)
                progress(f"{RESUME_DOCX}: written at {pt}pt")
            if RESUME_DESIGNED in extra["written"]:
                files["resume_designed"] = os.path.join(run_dir, RESUME_DESIGNED)
                progress(f"{RESUME_DESIGNED}: {extra['designed_pages']} page(s) "
                         f"at {extra['designed_pt']}pt")
            for problem in extra["problems"]:
                progress(problem)
        files[key] = path

    # The ATS report: scores on the final text, the checks a parser cares
    # about, and whether the finished PDF still reads. Plain Python, no model,
    # which is what lets an edit rebuild the whole thing later.
    ats_scores = write_ats_report(run_dir, {
        "title": extracted["title"], "keywords": keywords, "target": target,
        "rephrasing_pass": pass_info,
    }, resume, cover_letter)
    files["ats_report"] = os.path.join(run_dir, ATS_REPORT)
    if ats_scores["resume"] is not None:
        progress(f"ATS: resume {ats_scores['resume']}/100, "
                 f"cover letter {ats_scores['cover_letter']}/100 (target {target})")

    # The markdown behind each PDF, so it can be edited and re-rendered later.
    # `file` and `style` live here too: an edit then names a document by key and
    # the server looks up where it goes, rather than taking a path from a caller.
    # The ATS report is not here: it is derived, and re-derived on every edit.
    _write_json(os.path.join(run_dir, SOURCES_FILE),
                {key: {"file": name, "style": style, "markdown": body}
                 for key, name, body, style in outputs})

    # A record of what this application was, so months later the folder is not
    # a mystery. This is the thing that was missing when five identically named
    # PDFs sat in one directory.
    _write_json(os.path.join(run_dir, "run.json"), {
        "company": company,
        "role": role,
        "recommendation": recommendation,
        "reasoning": reasoning,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "job_description": job_description,
        "research_performed": bool(research),
        "written_as_stretch": bool(stretch),
        "ats": ats_scores,
        "generation_usd": spend.dollars(),
    })

    return {
        "run_dir": run_dir,
        "files": files,
        "ats": ats_scores,
        "generation_calls": spend.calls,
        "input_tokens": spend.input_tokens,
        "output_tokens": spend.output_tokens,
        # If cache_read stays at zero across a run, something is silently
        # invalidating the prefix and the saving is not happening.
        "cache_written": spend.cache_written,
        "cache_read": spend.cache_read,
        "cost_usd": spend.dollars(),
    }
