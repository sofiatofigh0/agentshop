"""
ATS keyword scoring — reading a resume the way a screening system does.

Before a person sees an application, an applicant tracking system (Greenhouse,
Lever, Workday, and the tools layered on them) usually scores it against the
posting: does the resume contain the terms the posting was written in? Tools
like Simplify and Jobscan show candidates that score so they can close the gap
before submitting. This module does the same thing for the documents this
project generates, with one difference that matters:

    A keyword is only ever worked in by rephrasing something that is already
    true. It is never added to hit a number.

The pieces:

    extract_keywords()  one cheap model call: the terms a screener would be
                        configured to look for, each with its category, how
                        hard the posting requires it, and the equivalent
                        phrasings a screener would accept
    score()             plain Python: weighted coverage of those terms in a
                        document, matched and missing lists, over-repetition
    bank_supported()    plain Python: of the missing terms, which ones the
                        experience bank so much as mentions. Only those are
                        candidates for rephrasing; the rest are real gaps and
                        the report says so
    format_checks()     the structural things a parser trips on
    pdf_text_check()    whether the terms survive being read back out of the
                        finished PDF — a resume the parser cannot read scores
                        zero whatever the markdown says
    report()            the markdown behind ats_report.pdf

The scoring formula, so it can be read off the report rather than trusted:

    score = 100 x sum of weights of matched terms / sum of weights of all terms
    weight = importance (required 3, preferred 2, mentioned 1)
             x category (soft skills count half; everything else counts full)

A match is the term or any alias as a whole phrase, case-insensitive, plural
or singular, after punctuation is normalized — so "A/B testing" matches
"A/B tests" and "LLM eval" does not match "LLM evaluation" unless the extractor
listed it as an alias. Nothing fuzzier than that, because a screener is not
fuzzier than that either.
"""

import json
import os
import re

import anthropic
from pypdf import PdfReader

from models import request_options, worker_model

# --------------------------------------------------------------------------
# Weights
# --------------------------------------------------------------------------

CATEGORIES = ("hard_skill", "tool", "title", "credential", "domain", "soft_skill")
CATEGORY_LABEL = {
    "hard_skill": "Hard skills", "tool": "Tools & technologies", "title": "Title & level",
    "credential": "Credentials", "domain": "Domain", "soft_skill": "Soft skills",
}
CATEGORY_WEIGHT = {
    "hard_skill": 1.0, "tool": 1.0, "title": 1.0, "credential": 1.0, "domain": 1.0,
    "soft_skill": 0.5,
}
IMPORTANCE_WEIGHT = {"required": 3, "preferred": 2, "mentioned": 1}

MAX_KEYWORDS = 40
STUFFING_LIMIT = 4      # a term repeated more often than this reads as stuffing
MAX_REPHRASE_TERMS = 8  # the rephrasing pass looks at this many missing terms at most


def target_score() -> int:
    """The coverage below which a rephrasing pass is worth one more call.

    Jobscan's published guidance is a 75% match rate; the same number is used
    here as the default. It is a threshold for spending a call, not a goal the
    writer is told to hit.
    """
    try:
        return int(os.environ.get("ATS_TARGET_SCORE", "75"))
    except ValueError:
        return 75


# --------------------------------------------------------------------------
# Extraction — the one model call
# --------------------------------------------------------------------------

EXTRACT_PROMPT = """You extract the keywords an applicant tracking system would
be configured to scan for, from one job description.

Return ONLY a JSON object, no prose and no code fence:

{
  "title": "<the posting's job title, as written>",
  "keywords": [
    {"term": "<the posting's exact phrase>",
     "category": "hard_skill | tool | title | credential | domain | soft_skill",
     "importance": "required | preferred | mentioned",
     "aliases": ["<equivalent phrasings a screener would count as the same term>"]}
  ]
}

Rules:
- term is the posting's own wording, lower-case, singular, one to four words:
  "product roadmap", "sql", "a/b testing", "llm evaluation".
- category: hard_skill is a competency or method; tool is a named technology,
  product or language; title is the role's name or level ("senior product
  manager", "0-to-1"); credential is a degree, certification or years-of-
  experience requirement; domain is the industry or product area; soft_skill
  is a way of working ("cross-functional collaboration").
- importance: required when the posting says must, required, need, minimum,
  or lists it under requirements; preferred for nice-to-have, bonus, plus,
  ideally; mentioned for anything only described in passing.
- aliases: zero to four forms a screener would treat as the same term —
  abbreviations, expansions, spellings, the noun for a verb ("evaluate" ->
  "evaluation"). Do not list a different skill as an alias.
- Skip generic words ("experience", "team", "strong"), benefits, and the
  company's own name. Between 12 and 40 keywords, most important first; fewer
  for a thin posting.
"""


def extract_keywords(job_description: str) -> dict:
    """The posting's keywords, as ({"title": str, "keywords": [...]}, usage).

    Runs on the worker model at low effort: this is extraction, and the
    scoring that uses it is deterministic. Raises on a model or parse failure;
    the caller decides whether a run can go on without a score (it can).
    """
    model = worker_model()
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=3000,
        system=EXTRACT_PROMPT,
        messages=[{"role": "user", "content": f"JOB DESCRIPTION:\n{job_description}"}],
        **request_options("keywords", model),
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    return parse_keywords(text), response.usage


def parse_keywords(text: str) -> dict:
    """Turn the model's reply into a clean keyword list. Tolerates a code
    fence or stray prose around the JSON; rejects anything that is not a
    keyword object."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in the reply")
    data = json.loads(text[start:end + 1])

    seen, keywords = set(), []
    for entry in data.get("keywords") or []:
        if not isinstance(entry, dict):
            continue
        term = _norm(str(entry.get("term", "")))
        if not term or term in seen:
            continue
        seen.add(term)
        aliases = []
        listed = entry.get("aliases")
        for alias in (listed if isinstance(listed, list) else []):
            alias = _norm(str(alias))
            if alias and alias != term and alias not in aliases:
                aliases.append(alias)
        category = str(entry.get("category", "")).strip().lower()
        importance = str(entry.get("importance", "")).strip().lower()
        keywords.append({
            "term": term,
            "category": category if category in CATEGORIES else "domain",
            "importance": importance if importance in IMPORTANCE_WEIGHT else "mentioned",
            "aliases": aliases[:4],
        })
        if len(keywords) >= MAX_KEYWORDS:
            break

    return {"title": str(data.get("title", "")).strip(), "keywords": keywords}


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------

_DASHES = re.compile("[‐‑‒–—−]")
_STOP = {"a", "an", "and", "the", "of", "in", "for", "to", "with", "on", "at", "or"}


def _norm(text: str) -> str:
    """Lower-case, punctuation folded to spaces, whitespace collapsed.

    "+" and "#" survive so "C++" and "C#" stay distinct terms; every other
    non-alphanumeric character becomes a space, so "A/B-testing", "A/B
    testing" and "a b testing" are the same string.
    """
    text = _DASHES.sub("-", text.lower()).replace("&", " and ")
    text = re.sub(r"[^a-z0-9+# ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _pattern(phrase: str):
    """A whole-phrase, singular-or-plural regex for one phrase, normalized
    the same way as the text it will be searched in."""
    words = _norm(phrase).split()
    if not words:
        return None
    body = r"\s+".join(re.escape(w) + r"(?:s|es)?" for w in words)
    return re.compile(r"(?<![a-z0-9])" + body + r"(?![a-z0-9])")


def _count(keyword: dict, normalized_text: str) -> int:
    total = 0
    for phrase in [keyword["term"]] + list(keyword.get("aliases", [])):
        pattern = _pattern(phrase)
        if pattern:
            total += len(pattern.findall(normalized_text))
    return total


def weight(keyword: dict) -> float:
    return (IMPORTANCE_WEIGHT.get(keyword.get("importance"), 1)
            * CATEGORY_WEIGHT.get(keyword.get("category"), 1.0))


def score(keywords: list, text: str) -> dict:
    """Weighted keyword coverage of one document.

    Returns the score (0-100, or None when there are no keywords), the matched
    terms with how often each appears, the missing terms strongest first, the
    coverage per category, and any term repeated past STUFFING_LIMIT.
    """
    normalized = _norm(text)
    matched, missing = [], []
    got, total = 0.0, 0.0
    by_category = {cat: [0.0, 0.0] for cat in CATEGORIES}

    for keyword in keywords:
        w = weight(keyword)
        n = _count(keyword, normalized)
        total += w
        by_category[keyword["category"]][1] += w
        if n:
            got += w
            by_category[keyword["category"]][0] += w
            matched.append({**keyword, "count": n, "weight": w})
        else:
            missing.append({**keyword, "weight": w})

    missing.sort(key=lambda k: (-k["weight"], k["term"]))
    return {
        "score": round(100 * got / total) if total else None,
        "matched": matched,
        "missing": missing,
        "by_category": {
            cat: (round(100 * have / need) if need else None)
            for cat, (have, need) in by_category.items()
        },
        "stuffed": [m for m in matched if m["count"] > STUFFING_LIMIT],
        "keyword_count": len(keywords),
    }


def summary(scored: dict) -> dict:
    """The part of a score worth keeping in run.json."""
    return {
        "score": scored["score"],
        "matched": [m["term"] for m in scored["matched"]],
        "missing": [m["term"] for m in scored["missing"]],
    }


# --------------------------------------------------------------------------
# The bank as the gate
# --------------------------------------------------------------------------

def bank_prose(bank) -> str:
    """Every string in the bank, joined, with unusable claims left out.

    Keys are not included — "metrics" and "source" are bank vocabulary, not
    evidence — and any object whose source is needs_validation is skipped
    whole, so an unconfirmed claim cannot make a keyword look supported.
    """
    pieces = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("source") == "needs_validation":
                return
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str):
            pieces.append(node)

    walk(bank)
    return _norm("\n".join(pieces))


def bank_supported(missing: list, bank_text: str) -> tuple:
    """Split missing terms into (mentioned in the bank, not in the bank).

    Mention is a text match, not a judgement: it means the rephrasing pass
    may look at the term, not that the resume may claim it. The model decides
    whether the underlying work is truly there, and the factuality review
    checks what it decided.
    """
    candidates, gaps = [], []
    for keyword in missing:
        (candidates if _count(keyword, bank_text) else gaps).append(keyword)
    return candidates, gaps


# --------------------------------------------------------------------------
# Prompt material for the writers
# --------------------------------------------------------------------------

def prompt_block(extracted: dict, limit: int = 30) -> str:
    """The keyword list as a writing prompt carries it. Empty if none."""
    keywords = (extracted or {}).get("keywords") or []
    if not keywords:
        return ""

    ranked = sorted(keywords, key=lambda k: -weight(k))[:limit]
    groups = {"required": [], "preferred": [], "mentioned": []}
    for keyword in ranked:
        groups[keyword["importance"]].append(keyword["term"])
    listed = "\n".join(
        f"  {name + ':':11s}{', '.join(terms)}" for name, terms in groups.items() if terms
    )
    title = (extracted or {}).get("title") or ""
    title_line = f"\nThe posting's title is \"{title}\".\n" if title else ""

    return f"""

ATS KEYWORDS — the terms a screening system will scan this document for,
grouped by how firmly the posting asks for them:
{title_line}
{listed}

Use them the way a careful writer would, not the way a keyword stuffer would:
- Where a sentence already describes this work, say it in the posting's own
  term rather than a synonym. A screener does not know "LLM evals" and "LLM
  evaluation" are the same thing; a reader does not mind either.
- Never add a term the experience bank does not earn, never append a bare
  list of terms, and never repeat a term to raise a count. A term that does
  not fit is a gap, and the ATS report will say so — that is the correct
  outcome, not a failure.
"""


def rephrase_block(candidates: list) -> str:
    """The missing-but-mentioned terms, for the rephrasing pass."""
    lines = "\n".join(
        f"- {k['term']}  ({k['importance']}, {CATEGORY_LABEL[k['category']].lower()})"
        + (f"; also counts: {', '.join(k['aliases'])}" if k.get("aliases") else "")
        for k in candidates[:MAX_REPHRASE_TERMS]
    )
    return f"TERMS THE RESUME DOES NOT YET USE, WHICH THE BANK MENTIONS:\n{lines}"


# --------------------------------------------------------------------------
# Checks a parser cares about
# --------------------------------------------------------------------------

def resume_title(resume_md: str) -> str:
    """The bold title line under the name, before the first section."""
    for line in resume_md.splitlines():
        line = line.strip()
        if line.startswith("## "):
            break
        if line.startswith("**") and line.endswith("**") and len(line) > 4:
            return line.strip("*").strip()
    return ""


def title_match(posting_title: str, resume_md: str) -> dict:
    """How much of the posting's title the resume's title line shares."""
    resume = resume_title(resume_md)
    wanted = [w for w in _norm(posting_title).split() if w not in _STOP]
    have = set(_norm(resume).split())
    shared = [w for w in wanted if w in have]
    return {
        "posting": posting_title, "resume": resume, "shared": shared,
        "ratio": (len(shared) / len(wanted)) if wanted else None,
    }


REQUIRED_SECTIONS = ("experience", "skills", "education")


def format_checks(resume_md: str) -> list:
    """Structural checks, each {"check", "ok", "detail"}.

    These are the parser-facing properties of the document, not its content:
    the standard headings a parser routes by, dates on every role, a contact
    line, a length a one-page parse expects, and bullets that carry numbers.
    """
    lines = [l.strip() for l in resume_md.splitlines()]
    headings = {l[3:].strip().lower() for l in lines if l.startswith("## ")}
    jobs = [l for l in lines if l.startswith("### ")]
    bullets = [l for l in lines if l.startswith(("- ", "* "))]
    words = len(re.findall(r"[A-Za-z0-9]+", resume_md))
    quantified = sum(1 for b in bullets if re.search(r"\d", b))
    contact = next((l for l in lines[1:] if l and not l.startswith(("#", "**"))), "")

    missing = [s for s in REQUIRED_SECTIONS if s not in headings]
    undated = [j for j in jobs if "|" not in j]
    checks = [
        {"check": "Standard section headings", "ok": not missing,
         "detail": "Experience, Skills and Education all present" if not missing
                   else "missing: " + ", ".join(missing)},
        {"check": "Contact line under the name", "ok": bool(contact),
         "detail": "present" if contact else "none found"},
        {"check": "Dates on every role", "ok": bool(jobs) and not undated,
         "detail": f"{len(jobs)} role(s), all dated" if jobs and not undated
                   else ("no roles found" if not jobs else f"{len(undated)} undated")},
        {"check": "Length for a one-page parse", "ok": 300 <= words <= 900,
         "detail": f"{words} words (300-900 expected)"},
        {"check": "Bullets with a number in them", "ok": quantified >= 3,
         "detail": f"{quantified} of {len(bullets)} bullets"},
    ]
    return checks


def pdf_text_check(pdf_path: str, matched: list) -> dict:
    """Do the matched terms survive text extraction from the finished PDF?

    A screener reads the PDF, not the markdown. If a term that is in the
    markdown cannot be found in the extracted text, the layout is losing it.
    """
    try:
        text = "\n".join(page.extract_text() or "" for page in PdfReader(pdf_path).pages)
    except Exception as exc:  # an unreadable PDF is itself the finding
        return {"ok": False, "lost": [m["term"] for m in matched],
                "detail": f"could not read the PDF: {exc}"}
    normalized = _norm(text)
    lost = [m["term"] for m in matched if not _count(m, normalized)]
    return {"ok": not lost, "lost": lost,
            "detail": f"{len(matched) - len(lost)} of {len(matched)} matched terms readable"}


# --------------------------------------------------------------------------
# The report
# --------------------------------------------------------------------------

def _terms(items: list, with_counts: bool = False) -> str:
    if not items:
        return "_none_"
    out = []
    for k in items:
        label = f"**{k['term']}**"
        if with_counts and k.get("count", 1) > 1:
            label += f" ×{k['count']}"
        out.append(f"{label} ({k['importance']})")
    return ", ".join(out)


def report(extracted: dict, resume: dict, letter: dict, target: int,
           candidates: list, gaps: list, checks: list, title: dict,
           pdf: dict, pass_info: dict = None) -> str:
    """The markdown behind ats_report.pdf."""
    keywords = extracted.get("keywords") or []
    if not keywords:
        return ("# ATS keyword report\n\nNo keywords were extracted from this posting, so "
                "nothing was scored. The documents were written without an ATS pass.\n")

    lines = [
        "# ATS keyword report",
        "",
        f"Scored against {len(keywords)} terms extracted from the posting"
        + (f' for "{extracted.get("title")}"' if extracted.get("title") else "")
        + f". Target for a rephrasing pass: {target}.",
        "",
        "Score = weighted share of the posting's terms the document contains. Weight is "
        "importance (required 3, preferred 2, mentioned 1) times category (soft skills "
        "count half). A match is the exact term or a listed alias, singular or plural. "
        "No fuzzier than that, because a screener is not fuzzier than that either.",
        "",
        f"## Resume — {resume['score']} / 100",
        "",
        "| Category | Coverage |",
        "|---|---|",
    ]
    for cat in CATEGORIES:
        pct = resume["by_category"].get(cat)
        if pct is not None:
            lines.append(f"| {CATEGORY_LABEL[cat]} | {pct}% |")
    lines += [
        "",
        f"**Matched ({len(resume['matched'])}):** {_terms(resume['matched'], with_counts=True)}",
        "",
        f"**Not used, but the bank mentions the work ({len(candidates)}):** {_terms(candidates)}",
        "",
        "These did not fit by rephrasing what is already there. They are the only terms a "
        "further edit could honestly pick up — and only where a sentence already says it.",
        "",
        f"**Not in the experience bank ({len(gaps)}):** {_terms(gaps)}",
        "",
        "Real gaps. Do not add these; a screener may miss them, but an interviewer will not.",
        "",
    ]
    if resume["stuffed"]:
        lines += [
            "**Repeated past the point of use:** "
            + ", ".join(f"{m['term']} ×{m['count']}" for m in resume["stuffed"])
            + ". Screeners flag repetition; trim to where it reads naturally.",
            "",
        ]
    if pass_info:
        lines += [
            "**Rephrasing pass:** "
            + (f"ran on {pass_info['considered']} term(s); the score moved "
               f"{pass_info['before']} → {pass_info['after']}"
               + (", and the reworded draft was kept." if pass_info["kept"]
                  else ", so the original draft was kept.")),
            "",
        ]

    ratio = title["ratio"]
    lines += [
        "### Title line",
        "",
        (f'Posting: "{title["posting"]}" · Resume: "{title["resume"] or "(none)"}" · '
         + (f"{len(title['shared'])} shared word(s)" if ratio is not None else "no posting title")),
        "",
    ]
    if ratio is not None and ratio < 0.5:
        lines += ["A screener often filters on the title first. If the bank supports the "
                  "posting's title honestly, use its words on the title line.", ""]

    lines += ["### Formatting", "", "| Check | Result | Detail |", "|---|---|---|"]
    for check in checks:
        lines.append(f"| {check['check']} | {'pass' if check['ok'] else 'look'} | {check['detail']} |")
    lines += [
        "",
        "### Machine readability",
        "",
        ("Every matched term can be read back out of the rendered PDF." if pdf["ok"]
         else "Terms lost between the markdown and the PDF's extracted text: "
              + ", ".join(pdf["lost"]) + ". The layout is hiding them from a parser."),
        f" ({pdf['detail']})",
        "",
    ]

    if letter and letter.get("score") is not None:
        lines += [
            f"## Cover letter — {letter['score']} / 100",
            "",
            "A letter is read by people more than by parsers, so this is context rather "
            "than a target: 330 words cannot and should not carry every term.",
            "",
            f"**Matched ({len(letter['matched'])}):** {_terms(letter['matched'])}",
            "",
            f"**Strongest terms it does not use:** {_terms(letter['missing'][:10])}",
            "",
        ]
    return "\n".join(lines)
