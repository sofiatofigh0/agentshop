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

A match is the posting's own term as a whole phrase, case-insensitive, plural
or singular, after punctuation is normalized — so "product roadmaps" matches
"product roadmap", and "0->1" matches "0-to-1". Those are the forms a search
engine folds together.

An alias — an abbreviation, an expansion, another phrasing — does NOT count
toward the score. A recruiter searches the tracking system for the posting's
words, and "LLM evals" is simply not found by a search for "LLM evaluation".
A document that says the thing in a different form is listed separately, as
a variant: the claim is already on the page in other words, which makes it the
safest rewording there is.
"""

import json
import os
import re
import unicodedata

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

    # An alias that is also some other keyword's term would score the same
    # words twice, once under each. The standalone term keeps it.
    terms = {keyword["term"] for keyword in keywords}
    for keyword in keywords:
        keyword["aliases"] = [alias for alias in keyword["aliases"]
                              if alias not in terms - {keyword["term"]}]

    return {"title": str(data.get("title", "")).strip(), "keywords": keywords}


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------

_DASHES = re.compile("[‐‑‒–—−]")
# "0->1", "0→1" and "0-to-1" are the same claim written three ways, and a
# posting and a resume rarely pick the same one.
_ARROWS = re.compile(r"\s*(?:-+>|→|-to-)\s*")
_POSSESSIVE = re.compile(r"['’]s\b")
_STOP = {"a", "an", "and", "the", "of", "in", "for", "to", "with", "on", "at", "or"}


def _norm(text: str) -> str:
    """Lower-case, punctuation folded to spaces, whitespace collapsed.

    "+" and "#" survive so "C++" and "C#" stay distinct terms; every other
    non-alphanumeric character becomes a space, so "A/B-testing", "A/B
    testing" and "a b testing" are the same string. Arrow spellings collapse
    to "to", and a possessive loses its apostrophe rather than splitting the
    word in two, so "bachelor's degree" and "Bachelors degree" match.
    """
    text = _DASHES.sub("-", text.lower()).replace("&", " and ")
    text = _ARROWS.sub(" to ", text)
    text = _POSSESSIVE.sub("s", text)
    text = re.sub(r"[^a-z0-9+# ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _word(word: str, last: bool) -> str:
    """One word of a phrase, as a regex.

    Only the last word takes a plural, because that is where English puts it —
    "product roadmaps", not "products roadmap". Words of one or two letters
    never take one: without that rule "go" matches "goes", "us" matches
    "uses" and a posting asking for Go is scored against a resume that never
    mentions it.
    """
    if not last or len(word) <= 2 or not word[-1].isalpha():
        return re.escape(word)
    if word.endswith("y") and len(word) > 3 and word[-2] not in "aeiou":
        return re.escape(word[:-1]) + r"(?:y|ies)"       # strategy / strategies
    if word.endswith("is") and len(word) > 3:
        return re.escape(word[:-2]) + r"(?:is|es)"       # analysis / analyses
    if word.endswith(("s", "x", "z", "ch", "sh")):
        return re.escape(word) + r"(?:es)?"              # process / processes
    return re.escape(word) + r"(?:s)?"                   # roadmap / roadmaps


def _pattern(phrase: str):
    """A whole-phrase regex for one phrase, normalized the same way as the
    text it will be searched in.

    "+" and "#" count as part of a word in the boundaries, so the term "c"
    does not match "C++" or "C#".
    """
    words = _norm(phrase).split()
    if not words:
        return None
    body = r"\s+".join(_word(w, i == len(words) - 1) for i, w in enumerate(words))
    return re.compile(r"(?<![a-z0-9+#])" + body + r"(?![a-z0-9+#])")


def _spans(keyword: dict, normalized_text: str) -> list:
    """Where this keyword appears, counting overlapping forms once.

    A term and its aliases often overlap — "product roadmap" with the alias
    "roadmap" matches the same words twice. Counting both would inflate the
    count and trip the repetition flag on a resume that says it three times.
    """
    found = []
    for phrase in [keyword["term"]] + list(keyword.get("aliases", [])):
        pattern = _pattern(phrase)
        if pattern:
            found.extend(match.span() for match in pattern.finditer(normalized_text))

    merged = []
    for start, end in sorted(found):
        if merged and start < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _count(keyword: dict, normalized_text: str) -> int:
    return len(_spans(keyword, normalized_text))


def weight(keyword: dict) -> float:
    return (IMPORTANCE_WEIGHT.get(keyword.get("importance"), 1)
            * CATEGORY_WEIGHT.get(keyword.get("category"), 1.0))


def _exact(term: str, normalized_text: str) -> int:
    """How often one phrase appears, with no aliases considered."""
    return _count({"term": term, "aliases": []}, normalized_text)


def score(keywords: list, text: str) -> dict:
    """Weighted keyword coverage of one document.

    Returns the score (0-100, or None when there are no keywords), the matched
    terms with how often each appears, the variants — terms the document says
    only in another form, with the form it used — the missing terms strongest
    first, the coverage per category, and any term repeated past
    STUFFING_LIMIT. Only an exact match counts toward the score.
    """
    normalized = _norm(text)
    matched, variants, missing = [], [], []
    got, total = 0.0, 0.0
    by_category = {cat: [0.0, 0.0] for cat in CATEGORIES}

    for keyword in keywords:
        w = weight(keyword)
        total += w
        by_category[keyword["category"]][1] += w
        if _exact(keyword["term"], normalized):
            got += w
            by_category[keyword["category"]][0] += w
            # The count covers every form, since repetition is about how often
            # the idea recurs, whatever words carry it.
            matched.append({**keyword, "count": _count(keyword, normalized), "weight": w})
            continue
        used = next((a for a in keyword.get("aliases", []) if _exact(a, normalized)), None)
        if used:
            variants.append({**keyword, "weight": w, "used": used})
        else:
            missing.append({**keyword, "weight": w})

    variants.sort(key=lambda k: (-k["weight"], k["term"]))
    missing.sort(key=lambda k: (-k["weight"], k["term"]))
    return {
        "score": round(100 * got / total) if total else None,
        "matched": matched,
        "variants": variants,
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
        "variants": [m["term"] for m in scored.get("variants", [])],
        "missing": [m["term"] for m in scored["missing"]],
    }


# --------------------------------------------------------------------------
# The bank as the gate
# --------------------------------------------------------------------------

# The bank's fields that describe what the candidate actually did. Everything
# else in it is bookkeeping — provenance labels, guidance about when a claim
# may be used, and outright prohibitions — and none of that is evidence.
#
# This is a whitelist rather than a list of fields to skip, because the
# failure it prevents runs one way. Reading `source: "supported_inference"` as
# evidence puts "inference" in front of the writer as a term the bank
# supports; reading the rule "Never write '6 years of PM experience'" as
# evidence offers the candidate "6 years" as an honest edit, which is the
# exact claim the bank forbids. A field nobody has classified yet should
# default to "not evidence", and a whitelist is what makes that the default.
EVIDENCE_FIELDS = frozenset({
    # what was done
    "claim", "claims", "actions", "results", "problem", "summary", "story",
    "lessons", "fact", "career_narrative",
    # what it was done with
    "skills", "keywords", "technologies", "tools", "technical", "ai",
    "product", "domain", "domains", "collaboration", "items",
    # how it is characterised
    "primary_strengths", "additional_themes", "narrative_themes",
    "use_as_evidence_of",
    # where and when
    "name", "title", "company", "team", "dates", "location", "level",
    "language", "credential", "institution",
})


def bank_prose(bank) -> str:
    """The bank's evidence, as one string, for deciding what a term may touch.

    Only the fields named above are read, and any object whose source is
    needs_validation is skipped whole, so neither an unconfirmed claim nor a
    label nor a restriction can make a keyword look supported.
    """
    pieces = []

    def walk(node, field=None):
        if isinstance(node, dict):
            if node.get("source") == "needs_validation":
                return
            for key, value in node.items():
                walk(value, key)
        elif isinstance(node, list):
            for value in node:
                walk(value, field)
        elif isinstance(node, str) and field in EVIDENCE_FIELDS:
            pieces.append(node)

    walk(bank)
    return _norm("\n".join(pieces))


def bank_supported(missing: list, bank_text: str) -> tuple:
    """Split missing terms into (mentioned in the bank, not in the bank).

    Mention is a text match, not a judgement: it means a writer may look at
    the term, not that the resume may claim it. The model decides whether the
    underlying work is truly there, and nothing re-checks that decision.
    """
    candidates, gaps = [], []
    for keyword in missing:
        (candidates if _count(keyword, bank_text) else gaps).append(keyword)
    return candidates, gaps


# --------------------------------------------------------------------------
# Prompt material for the writers
# --------------------------------------------------------------------------

def _grouped(keywords: list) -> str:
    """Terms listed under required / preferred / mentioned, strongest first."""
    groups = {"required": [], "preferred": [], "mentioned": []}
    for keyword in sorted(keywords, key=lambda k: -weight(k)):
        groups[keyword["importance"]].append(keyword["term"])
    return "\n".join(f"  {name + ':':11s}{', '.join(terms)}"
                     for name, terms in groups.items() if terms)


def prompt_block(extracted: dict, bank_text: str = None, limit: int = 30) -> str:
    """The keyword list as a writing prompt carries it. Empty if none.

    Given the bank's text, the terms are split by whether the bank uses them.
    That is the same plain-Python check the rephrasing gate runs after the
    draft, moved in front of it: a writer who knows which of the posting's
    words the bank already contains uses them on the first pass, so the draft
    lands nearer the target and the second, full-resume rephrasing call is
    needed less often. It also names, before a word is written, the terms the
    bank never uses — the ones most likely to be reached for dishonestly.
    """
    keywords = (extracted or {}).get("keywords") or []
    if not keywords:
        return ""

    ranked = sorted(keywords, key=lambda k: -weight(k))[:limit]
    title = (extracted or {}).get("title") or ""
    title_line = (f"\nThe posting's exact title is \"{title}\". Wherever a document names "
                  "the role, it uses this title verbatim.\n" if title else "")

    if bank_text is None:
        listing = ("grouped by how firmly the posting asks for them:\n"
                   f"{title_line}\n{_grouped(ranked)}")
    else:
        used = [k for k in ranked if _count(k, bank_text)]
        unused = [k for k in ranked if not _count(k, bank_text)]
        listing = f"split by whether the experience bank uses them:\n{title_line}"
        if used:
            listing += ("\nTHE BANK USES THESE WORDS. Where a sentence describes this work, "
                        "write the posting's exact term:\n" + _grouped(used) + "\n")
        if unused:
            listing += ("\nTHE BANK NEVER USES THESE WORDS. Use one only where the bank "
                        "clearly describes that exact work in other words; otherwise leave "
                        "it out — it is a gap, not a target:\n" + _grouped(unused) + "\n")

    return f"""

ATS KEYWORDS — the terms a screening system will scan this document for,
{listing}
Use them the way a careful writer would, not the way a keyword stuffer would:
- Where a sentence already describes this work, say it in the posting's own
  term rather than a synonym. A screener does not know "LLM evals" and "LLM
  evaluation" are the same thing; a reader does not mind either.
- Match the posting's exact form, not just its meaning. "Adobe Creative Cloud"
  and "Adobe Creative Suite" are different strings to a parser. Abbreviate only
  where the posting abbreviates, and spell out what it spells out.
- Never add a term the experience bank does not earn, never append a bare
  list of terms, and never repeat a term to raise a count. A term that does
  not fit is a gap, and the ATS report will say so — that is the correct
  outcome, not a failure.
"""


def rephrase_offer(variants: list, candidates: list) -> list:
    """What the rephrasing pass is given, most valuable first, capped.

    Variants lead: the document already says each of them in another form, so
    rewording one to the posting's exact words adds no claim at all. Then the
    missing terms the bank mentions, strongest first.
    """
    return (list(variants) + list(candidates))[:MAX_REPHRASE_TERMS]


def rephrase_block(offered: list) -> str:
    """The terms for the rephrasing pass, split by what each one needs."""
    variants = [k for k in offered if k.get("used")]
    missing = [k for k in offered if not k.get("used")]
    parts = []
    if variants:
        parts.append(
            "SAID IN A DIFFERENT FORM — the resume already says these, but not in the "
            "posting's words, so a search for the posting's term does not find them. "
            "Reword each to the posting's exact term:\n"
            + "\n".join(f'- "{k["used"]}" -> "{k["term"]}"  ({k["importance"]})' for k in variants))
    if missing:
        parts.append(
            "NOT YET USED, BUT THE BANK MENTIONS THE WORK:\n"
            + "\n".join(f"- {k['term']}  ({k['importance']}, "
                        f"{CATEGORY_LABEL[k['category']].lower()})" for k in missing))
    return "\n\n".join(parts)


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


def core_title(title: str) -> str:
    """The title before its qualifier: "Senior Product Manager, AI Platform"
    -> "Senior Product Manager". The part a recruiter actually searches for."""
    return re.split(r"\s*[,(\[|]|\s[-\u2013\u2014]\s", title or "")[0].strip()


def section_text(resume_md: str, kind: str) -> str:
    """The text under the first heading of this kind, e.g. "summary"."""
    names = HEADING_KINDS.get(kind, ())
    out, inside = [], False
    for line in resume_md.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            if inside:
                break
            inside = stripped[3:].strip().lower() in names
            continue
        if inside:
            out.append(stripped)
    return "\n".join(out)


def title_match(posting_title: str, resume_md: str) -> dict:
    """Does the resume carry the posting's job title, in the posting's words?

    `exact` is true when the title line contains the posting's full title or
    its core, word for word — the match a recruiter's title search makes.
    `in_summary` asks the same of the Summary. `shared` and `ratio` keep the
    looser word-overlap view for context.
    """
    resume = resume_title(resume_md)
    core = core_title(posting_title)
    headline = _norm(resume)
    full = bool(posting_title) and _exact(posting_title, headline) > 0
    exact = full or (bool(core) and _exact(core, headline) > 0)
    in_summary = bool(core) and _exact(core, _norm(section_text(resume_md, "summary"))) > 0
    wanted = [w for w in _norm(posting_title).split() if w not in _STOP]
    have = set(headline.split())
    shared = [w for w in wanted if w in have]
    return {
        "posting": posting_title, "core": core, "resume": resume,
        "exact": exact, "full": full, "in_summary": in_summary, "shared": shared,
        "ratio": (len(shared) / len(wanted)) if wanted else None,
    }


# The headings parsers file sections by, grouped by what they mean. A heading
# outside every group is one a parser has to guess at, and a guess is often a
# miscellaneous field nobody searches.
HEADING_KINDS = {
    "summary": ("summary", "professional summary", "profile", "professional profile",
                "career summary"),
    "skills": ("skills", "technical skills", "core skills", "key skills",
               "core competencies"),
    "experience": ("work experience", "experience", "professional experience",
                   "employment history", "work history", "employment"),
    "projects": ("projects", "selected projects", "personal projects", "key projects"),
    "education": ("education", "education and training"),
    "certifications": ("certifications", "certificates", "licenses and certifications"),
    "other": ("awards", "honors", "languages", "publications", "volunteer experience",
              "leadership"),
}
REQUIRED_KINDS = ("experience", "skills", "education")

_MONTHS = ("january|february|march|april|may|june|july|august|september|october|"
           "november|december")
_MON = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
_RANGE = re.compile(r"\s+(?:-|\u2013|\u2014|to)\s+")


def date_format(token: str) -> str:
    """Name the format of one date, e.g. "Month YYYY" for "March 2026"."""
    t = token.strip().lower().rstrip(".")
    if t in ("present", "current", "now"):
        return "present"
    if re.fullmatch(rf"(?:{_MONTHS}) \d{{4}}", t):
        return "Month YYYY"
    if re.fullmatch(rf"(?:{_MON})\.? \d{{4}}", t):
        return "Mon YYYY"
    if re.fullmatch(r"\d{1,2}/\d{4}", t):
        return "MM/YYYY"
    if re.fullmatch(r"\d{4}-\d{2}", t):
        return "YYYY-MM"
    if re.fullmatch(r"\d{4}", t):
        return "YYYY"
    if re.fullmatch(rf"(?:{_MONTHS}|{_MON}) '\d{{2}}", t):
        return "Mon 'YY"
    return "other"


def _formats(date_range: str) -> set:
    return {date_format(part) for part in _RANGE.split(date_range.strip()) if part.strip()}


def decorative_characters(text: str) -> list:
    """Icons, emoji and other pictographs — the characters a parser drops or
    garbles. Ordinary punctuation (· — – • |) is not among them."""
    found = set()
    for ch in text:
        if (unicodedata.category(ch) in ("So", "Co", "Cs")
                or 0x1F000 <= ord(ch) <= 0x1FAFF or ch == "\ufe0f"):
            found.add(ch)
    return sorted(found)


def format_checks(resume_md: str) -> list:
    """Structural checks, each {"check", "ok", "detail"}.

    These are the parser-facing properties of the document, not its content:
    the standard headings a parser routes by, dates on every role, a contact
    line, a length a one-page parse expects, and bullets that carry numbers.
    """
    lines = [l.strip() for l in resume_md.splitlines()]
    headings = [l[3:].strip().lower() for l in lines if l.startswith("## ")]
    kinds = {kind for heading in headings
             for kind, names in HEADING_KINDS.items() if heading in names}
    unknown = [h for h in headings
               if not any(h in names for names in HEADING_KINDS.values())]
    jobs = [l for l in lines if l.startswith("### ")]
    bullets = [l for l in lines if l.startswith(("- ", "* "))]
    words = len(re.findall(r"[A-Za-z0-9]+", resume_md))
    quantified = sum(1 for b in bullets if re.search(r"\d", b))

    # The contact line is the prose between the name and the first section.
    # Looking past that heading would find the Profile paragraph and call any
    # resume contactable, including one a parser has no way to reach anyone by.
    header = []
    for line in lines[1:]:
        if line.startswith("## "):
            break
        header.append(line)
    contact = next((l for l in header
                    if l and not l.startswith(("#", "**", "- ", "* "))), "")

    missing = [k for k in REQUIRED_KINDS if k not in kinds]
    undated = [j for j in jobs if "|" not in j]

    # Every role's range in one format, since that is what experience is
    # computed from. Education may give a bare year where no month is known;
    # anything else there has to match the roles too.
    role_formats = set().union(*[_formats(j.rpartition("|")[2]) for j in jobs if "|" in j]) \
        if jobs else set()
    role_formats.discard("present")
    education_formats = set().union(*[_formats(l.rpartition("\u00b7")[2])
                                       for l in section_text(resume_md, "education").splitlines()
                                       if "\u00b7" in l]) if "## " in resume_md else set()
    education_formats -= {"present", "YYYY", "other"}
    one_format = (len(role_formats) <= 1 and "other" not in role_formats
                  and (not role_formats or education_formats <= role_formats))
    glyphs = decorative_characters(resume_md)

    problems = []
    if missing:
        problems.append("missing: " + ", ".join(missing))
    if unknown:
        problems.append("non-standard: " + ", ".join(f'"{h}"' for h in unknown))
    checks = [
        {"check": "Standard section headings", "ok": not problems,
         "detail": "; ".join(problems) if problems
                   else "all recognised: " + ", ".join(h.title() for h in headings)},
        {"check": "Contact line under the name", "ok": bool(contact),
         "detail": "present" if contact else "none found"},
        {"check": "Dates on every role", "ok": bool(jobs) and not undated,
         "detail": f"{len(jobs)} role(s), all dated" if jobs and not undated
                   else ("no roles found" if not jobs else f"{len(undated)} undated")},
        {"check": "One date format throughout", "ok": one_format,
         "detail": (f"{next(iter(role_formats))} on every role" if one_format and role_formats
                    else "no dated roles" if one_format
                    else "mixed: " + ", ".join(sorted(role_formats | education_formats)))},
        {"check": "No icons or emoji", "ok": not glyphs,
         "detail": "none found" if not glyphs
                   else ", ".join(f"U+{ord(c):04X}" for c in glyphs)},
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


_DATE_CELL = re.compile(rf"^(?:(?:{_MONTHS}|{_MON})\.? )?\d{{4}}"
                        rf"(?:\s*(?:-|\u2013|\u2014|to)\s*(?:(?:(?:{_MONTHS}|{_MON})\.? )?\d{{4}}"
                        r"|present|current))?$", re.I)


def reading_order(pdf_path: str, resume_md: str) -> dict:
    """Does the PDF read back as one stream, in the order it was written?

    Two tests, because parsers read a page in two ways. Some follow the order
    the text was drawn in: there, the section headings have to come back in
    the order the markdown gives them. Others rebuild the page row by row:
    there, no printed row may hold two blocks of text side by side, because a
    row-reader fuses them into one line. Two columns fail both — the sidebar's
    sections jump ahead, and each row joins a line from one column to a line
    from the other. A right-aligned date on a role's own line is not counted
    as a second block.
    """
    headings = [l.strip()[3:].strip() for l in resume_md.splitlines()
                if l.strip().startswith("## ")]
    try:
        pages = PdfReader(pdf_path).pages
        stream = "\n".join(page.extract_text() or "" for page in pages)
        layout = "\n".join(page.extract_text(extraction_mode="layout") or "" for page in pages)
    except Exception as exc:
        return {"ok": False, "in_order": False, "fused_rows": 0,
                "detail": f"could not read the PDF: {exc}"}

    lines = [_norm(line) for line in stream.splitlines()]
    positions = [next((i for i, line in enumerate(lines) if line == _norm(h)), None)
                 for h in headings]
    in_order = all(p is not None for p in positions) and positions == sorted(positions)

    fused = 0
    for row in layout.splitlines():
        cells = [c for c in re.split(r"\s{3,}", row.strip()) if c]
        if len(cells) > 1 and not (len(cells) == 2 and _DATE_CELL.match(cells[1].strip())):
            fused += 1

    ok = in_order and fused == 0
    if ok:
        detail = "sections read back in order, one block per line"
    else:
        parts = []
        if not in_order:
            parts.append("sections read back out of order")
        if fused:
            parts.append(f"{fused} printed line(s) join two blocks side by side")
        detail = "; ".join(parts)
    return {"ok": ok, "in_order": in_order, "fused_rows": fused, "detail": detail}


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


def _rephrasing_note(candidates: list, pass_info: dict, target: int) -> str:
    """What actually happened to the bank-mentioned terms the resume misses.

    Three different things can leave a term here, and telling the candidate it
    "did not fit" when nothing ever tried to fit it would be the report
    inventing an outcome. So each case says what it is.
    """
    if not pass_info:
        return (f"No rephrasing pass ran — the draft was already at or above the target "
                f"({target}) — so these were not tried. A further edit could pick them up "
                "where a sentence already says the thing, and nowhere else.")

    tried = set(pass_info.get("terms") or [])
    untried = [k for k in candidates if k["term"] not in tried]
    if not pass_info.get("kept"):
        note = ("A rephrasing pass was tried and its result scored no higher, so the "
                "original draft was kept. These terms are not known not to fit.")
    else:
        note = ("The rephrasing pass looked at these and could not work them in without "
                "claiming something the bank does not say.")
    if untried:
        note += (f" {len(untried)} of them were never offered to it: the pass looks at "
                 f"at most {MAX_REPHRASE_TERMS} terms, strongest first "
                 f"({', '.join(k['term'] for k in untried)}).")
    return note + (" Either way, a further edit could only pick one up where a sentence "
                   "already says the thing.")


def report(extracted: dict, resume: dict, letter: dict, target: int,
           candidates: list, gaps: list, checks: list, title: dict,
           pdf: dict, pass_info: dict = None, order: dict = None,
           designed: dict = None) -> str:
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
        "Score = weighted share of the posting's terms the document contains, in the "
        "posting's own words. Weight is importance (required 3, preferred 2, mentioned 1) "
        "times category (soft skills count half). A match is the exact term, singular or "
        "plural. Saying the same thing another way does not count, because a recruiter "
        "searches for the posting's words and a synonym is not found.",
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
    variants = resume.get("variants", [])
    used = len(resume["matched"])
    lines += [
        "",
        f"Posting terms used in the posting's own words: {used} of {len(keywords)}.",
        "",
        f"**Matched ({used}):** {_terms(resume['matched'], with_counts=True)}",
        "",
    ]
    if variants:
        lines += [
            f"**Said in a different form ({len(variants)}):** "
            + ", ".join(f'"{k["used"]}" where the posting says **{k["term"]}** '
                        f'({k["importance"]})' for k in variants),
            "",
            "The resume already says these, so a search for the posting's term is all that "
            "misses them. Rewording each to the posting's exact words adds no claim — these "
            "are the safest edits in this report.",
            "",
        ]
    lines += [
        f"**Not used, but the bank mentions the work ({len(candidates)}):** {_terms(candidates)}",
        "",
    ]
    if candidates:
        lines += [_rephrasing_note(candidates, pass_info, target), ""]
    lines += [
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

    lines += ["### Title line", ""]
    if not title.get("posting"):
        lines += ["No posting title was extracted, so the title line was not checked.", ""]
    else:
        lines += [
            f'Posting: "{title["posting"]}" · Resume: "{title.get("resume") or "(none)"}"',
            "",
            ("The title line carries the posting's title word for word"
             + (" (in full)." if title.get("full") else f' (its core, "{title.get("core")}").')
             if title.get("exact") else
             "The title line does not carry the posting's title word for word. Recruiters "
             "find candidates by searching for the title, and that search is literal: if "
             "the bank supports the title honestly, use it exactly."),
            "",
            ("The Summary repeats it." if title.get("in_summary")
             else "The Summary does not repeat it; its first sentence is the place to."),
            "",
        ]

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
    if order:
        lines += [
            ("Upload copy: " + order["detail"] + "." if order["ok"]
             else f"Upload copy: {order['detail']}. A parser would read this page "
                  "scrambled; check the layout before uploading it."),
            "",
        ]
    if designed:
        lines += [
            ("Designed copy: " + designed["detail"] + "." if designed["ok"]
             else f"Designed copy (two columns): {designed['detail']}. That is what a "
                  "parser makes of two columns, which is why this copy is for people — "
                  "email, referrals, print — and the single-column PDF or the .docx is "
                  "the one to upload."),
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
