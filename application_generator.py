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

import json
import os

import anthropic

from candidate_profile import CANDIDATE_PROFILE
from experience_bank import EXPERIENCE_BANK, missing_fields

# Python owns the output paths. The model never chooses where anything is saved.
OUTPUT_DIR = "outputs"

FACTS = json.dumps(EXPERIENCE_BANK, indent=2)
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

The bank's fields carry different permissions. Respect them exactly:

  metrics       Safe to state as written.
  framing       Interpretations of the verified work that the candidate has
                already approved. Safe to use.
  metric_variants
                Real numbers from DIFFERENT analyses of the same project. Choose
                exactly ONE per bullet, guided by its `use_when`. Never combine
                two, never sum them, never present two as if they measure the
                same thing. Obey any `metric_warning` on the project.
  possible_metric_to_validate
                UNVERIFIED. These are open questions, not achievements. Never
                put one in a resume, cover letter or strategy document in any
                form, however hedged.
  scale_caveat  A restriction on how a project may be described. Obey it.

Where a project records years of experience or a seniority note, use the
bank's wording rather than computing your own."""


def _call(system: str, user: str, max_tokens: int = 8000) -> tuple:
    """One plain model call. Returns (text, usage).

    No tools here — this stage is a fixed pipeline, not an agent loop.
    """
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=os.environ["ANTHROPIC_MODEL"],
        max_tokens=max_tokens,
        system=system,
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

EVIDENCE_MAP_PROMPT = f"""You map job requirements to concrete evidence.

{GROUND_RULES}

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

EXPERIENCE BANK:
{FACTS}

CANDIDATE PREFERENCES (context for tone and motivation, not a source of facts):
{PROFILE}
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

RESUME_PROMPT = f"""You write tailored resumes in clean markdown.

{GROUND_RULES}

Write a resume for this specific job, guided by the evidence map you are given.
Rows marked STRONG earn the most space and the highest position; rows marked
NONE must not be papered over.

Structure: name placeholder, a three-line professional summary aimed at this
role, then Experience (most relevant first, with the strongest bullets first
within each role), then Skills, then Education, then anything else that helps.

Keep every employer, title and date exactly as the bank states them. Prefer
bullets that carry a defensible number. Aim for one page of content.

EXPERIENCE BANK:
{FACTS}
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

FACTUALITY_PROMPT = f"""You are a factuality reviewer. You did not write this
resume and you have no interest in it looking good.

Go through the draft claim by claim — every employer, title, date, metric,
technology, scope claim and seniority implication. For each one, decide whether
the experience bank supports it:

SUPPORTED           the bank states this, or it is a fair rewording, or it is
                    listed under that project's `framing`
PARTIALLY SUPPORTED the bank hints at it but the draft goes further
UNSUPPORTED         the bank does not contain this at all

Treat these as UNSUPPORTED even though the words appear in the bank:
- any number drawn from `possible_metric_to_validate`
- two `metric_variants` from one project combined, summed, or used as if they
  measure the same thing
- any claim that breaks a project's `metric_warning` or `scale_caveat`
- a metric restated without the timeframe the bank gives it

Output a markdown table: | Claim | Verdict | Basis in the bank |

List SUPPORTED claims briefly; spend your attention on the other two. Then
write a section headed exactly "REQUIRED FIXES" listing each PARTIALLY
SUPPORTED or UNSUPPORTED claim and how to correct it — usually by cutting it or
weakening it to what the bank actually says. If everything checks out, write
"REQUIRED FIXES" followed by "None."

EXPERIENCE BANK:
{FACTS}
"""


def check_factuality(resume_draft: str) -> tuple:
    """Second opinion on the draft. Returns the review, not a verdict."""
    return _call(FACTUALITY_PROMPT, f"DRAFT RESUME:\n{resume_draft}")


REVISION_PROMPT = f"""You are correcting a resume that failed a factuality
review. Apply every fix the review asks for — cut or weaken the offending
claims — and change nothing else. Return the corrected resume in full, in
markdown, with no commentary.

{GROUND_RULES}

EXPERIENCE BANK:
{FACTS}
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

COVER_LETTER_PROMPT = f"""You write short, specific cover letters.

{GROUND_RULES}

Write a cover letter for this role. Under 400 words. Build it on the two or
three strongest rows of the evidence map — do not restate the resume bullet by
bullet. Be concrete about why this company and this role, using the research if
any was gathered and skipping that angle entirely if it would be generic.

No "I am excited to apply", no "passionate about", no flattery the candidate
could not defend in a room. Open with the specific reason they are a fit, spend
the middle on evidence, and close with a plain statement of interest.

EXPERIENCE BANK:
{FACTS}

CANDIDATE PREFERENCES (what genuinely motivates them):
{PROFILE}
"""


def write_cover_letter(job_description: str, evidence_map: str, research: str = "") -> tuple:
    user = f"JOB DESCRIPTION:\n{job_description}\n\nEVIDENCE MAP:\n{evidence_map}"
    if research:
        user += f"\n\nCOMPANY RESEARCH:\n{research}"
    return _call(COVER_LETTER_PROMPT, user, max_tokens=4000)


# --------------------------------------------------------------------------
# Step 5: application strategy
# --------------------------------------------------------------------------

STRATEGY_PROMPT = f"""You brief candidates before they apply.

{GROUND_RULES}

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
specific notes from research", write "No research was gathered." if none was.

Be direct about the gaps. A brief that only flatters is useless.

EXPERIENCE BANK:
{FACTS}

CANDIDATE PREFERENCES:
{PROFILE}
"""


def write_strategy(
    job_description: str, evidence_map: str, recommendation: str,
    reasoning: str, research: str = "",
) -> tuple:
    user = (
        f"JOB DESCRIPTION:\n{job_description}\n\n"
        f"EVIDENCE MAP:\n{evidence_map}\n\n"
        f"THE AGENT'S VERDICT: {recommendation}\nITS REASONING: {reasoning}"
    )
    if research:
        user += f"\n\nCOMPANY RESEARCH:\n{research}"
    return _call(STRATEGY_PROMPT, user)


# --------------------------------------------------------------------------
# The pipeline
# --------------------------------------------------------------------------

def generate_application_package(
    job_description: str, recommendation: str, reasoning: str, research: str = "",
) -> dict:
    """Run every generation step in order and write the files.

    Returns the paths written plus call and token counts for the trace.
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
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    calls = 0
    input_tokens = 0
    output_tokens = 0

    def run(step):
        nonlocal calls, input_tokens, output_tokens
        text, usage = step
        calls += 1
        input_tokens += usage.input_tokens
        output_tokens += usage.output_tokens
        return text

    print("  building requirement-to-evidence map...")
    evidence_map = run(build_evidence_map(job_description, research))

    print("  drafting resume...")
    draft = run(write_resume(job_description, evidence_map))

    print("  checking every claim against the experience bank...")
    review = run(check_factuality(draft))

    if review_found_problems(review):
        print("  unsupported claims found — revising...")
        resume = run(revise_resume(draft, review))
    else:
        print("  all claims supported.")
        resume = draft

    print("  writing cover letter...")
    cover_letter = run(write_cover_letter(job_description, evidence_map, research))

    print("  writing application strategy...")
    strategy = run(
        write_strategy(job_description, evidence_map, recommendation, reasoning, research)
    )

    files = {
        "evidence_map": f"{OUTPUT_DIR}/evidence_map.md",
        "factuality_review": f"{OUTPUT_DIR}/factuality_review.md",
        "resume": f"{OUTPUT_DIR}/tailored_resume.md",
        "cover_letter": f"{OUTPUT_DIR}/cover_letter.md",
        "strategy": f"{OUTPUT_DIR}/application_strategy.md",
    }
    for key, body in (
        ("evidence_map", evidence_map),
        ("factuality_review", review),
        ("resume", resume),
        ("cover_letter", cover_letter),
        ("strategy", strategy),
    ):
        with open(files[key], "w") as handle:
            handle.write(body + "\n")

    return {
        "files": files,
        "generation_calls": calls,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
