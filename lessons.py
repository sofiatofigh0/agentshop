"""What the candidate's own edits teach the generator.

Editing a generated document is the most honest feedback available: it is the
candidate saying, in their own words, what should have been written. This module
turns those edits into short durable preferences and hands them to the next run.

One rule governs everything here, and it is the reason this file exists
separately from the experience bank:

    A lesson may change HOW something is said. It may never change WHAT is true.

The experience bank remains the only source of facts. If an edit introduces a
claim -- a number, an employer, a title, a scope -- that claim stays in the
document it was typed into. It does not become a lesson and it never reaches
another application. Learning style from an edit is useful; learning facts from
one would quietly turn a hand-written sentence into a source of truth, which is
exactly what the rest of this project is built to prevent.

Two files, both gitignored, both derived from private documents:

    feedback.jsonl  every edit as it happened, append-only, the raw record
    lessons.json    the distilled preferences, which is what generation reads
"""

import difflib
import json
import os
import re
from datetime import datetime

import anthropic

FEEDBACK_LOG = "feedback.jsonl"
LESSONS_FILE = "lessons.json"

# Bounds, so a year of editing cannot silently turn into a prompt nobody reads.
MAX_LESSONS = 40          # oldest fall off the end
MAX_DIFF_CHARS = 6000     # a diff longer than this is truncated before sending


DISTILL_PROMPT = """You turn one edit to a generated job-application document
into a single durable preference, or into nothing at all.

You are given the diff between what was generated and what the candidate changed
it to, sometimes with a note explaining why, plus the role it was written for.

Return ONLY a JSON object, no prose and no code fence:

  {"keep": true, "lesson": "<one imperative sentence>", "scope": "<when it applies>"}
  {"keep": false, "why": "<short reason>"}

`lesson` is an instruction to the writer of the next document, in the
imperative, under 25 words. Write the rule, not the incident:

  Good: "Open the cover letter on the problem the team is solving, not on a
         summary of the candidate's background."
  Good: "Keep resume bullets to one line; split a two-line bullet in two."
  Bad:  "The candidate changed the first paragraph."   (an observation, not a rule)
  Bad:  "Mention the 40% revenue increase."            (a fact, see below)

`scope` is either "always" or a short phrase naming the kind of posting it
applies to -- "partnerships and BD roles", "platform or API-heavy roles",
"roles at large regulated companies". Judge this from the role given, not from
the wording of the edit.

Return keep:false when the edit teaches nothing that generalises:

- a typo, a name, a date, a formatting slip
- a change specific to this one posting and no other
- a preference already covered by an existing lesson (they are listed below)
- anything you can only express as a fact

NEVER record a fact. Not a number, metric, employer, job title, date, team size,
technology or achievement -- not even one the candidate typed in themselves, and
not even to say it should be included. Facts live in the experience bank and
only ever come from there. If the entire edit was the candidate adding or
correcting a claim, that is keep:false: the claim belongs to that document
alone. Record only preferences about wording, emphasis, ordering, structure,
length, tone and what to lead with.
"""


def _path(name: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


def load() -> list:
    """Every lesson learned so far, oldest first."""
    try:
        with open(_path(LESSONS_FILE)) as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _store(lessons: list) -> None:
    with open(_path(LESSONS_FILE), "w") as handle:
        json.dump(lessons[-MAX_LESSONS:], handle, indent=2)


def forget(lesson_id: str) -> bool:
    """Drop one lesson. Returns whether it was there."""
    lessons = load()
    kept = [item for item in lessons if item.get("id") != lesson_id]
    if len(kept) == len(lessons):
        return False
    _store(kept)
    return True


def diff(before: str, after: str) -> str:
    """The edit itself, as a unified diff of the two versions."""
    text = "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile="generated", tofile="edited", n=2,
    ))
    if len(text) > MAX_DIFF_CHARS:
        text = text[:MAX_DIFF_CHARS] + "\n[diff truncated]"
    return text


def prompt_block() -> str:
    """The lessons, formatted for a writing prompt. Empty when there are none."""
    lessons = load()
    if not lessons:
        return ""

    lines = "\n".join(
        f"- {item['lesson']}  [applies to: {item.get('scope', 'always')}]"
        for item in lessons
    )
    return f"""

LEARNED FROM THE CANDIDATE'S OWN EDITS

Each line below is a preference inferred from a document this candidate rewrote
by hand, newest last. Follow the ones whose scope fits this posting and ignore
the rest -- a rule learned on a partnerships role is not automatically right for
a platform one.

{lines}

These govern wording, emphasis, ordering and structure ONLY. None of them is a
source of facts, whatever one appears to say: the experience bank remains the
only place a claim about this candidate may come from. Where a lesson pulls
against the truth of a claim, the bank wins and the lesson is dropped.
"""


def record(before: str, after: str, note: str, document: str,
           company: str = "", role: str = "", folder: str = "") -> dict:
    """Log one edit and try to learn from it.

    Returns {"lesson": <text>, "scope": ...} when something was learned, or
    {"lesson": None, "why": <reason>} when the edit taught nothing durable.
    Never raises: an edit that cannot be distilled is still an edit that saved
    correctly, and the save must not fail because a model call did.
    """
    note = (note or "").strip()
    patch = diff(before, after)
    if not patch and not note:
        return {"lesson": None, "why": "Nothing changed."}

    entry = {
        "at": datetime.now().isoformat(timespec="seconds"),
        "folder": folder, "document": document,
        "company": company, "role": role,
        "note": note, "diff": patch,
    }
    try:
        with open(_path(FEEDBACK_LOG), "a") as handle:
            handle.write(json.dumps(entry) + "\n")
    except OSError:
        pass  # the raw log is a convenience; losing a line must not fail a save

    try:
        return _distil(entry)
    except Exception as exc:
        return {"lesson": None, "why": f"Could not distil this edit: {exc}"}


def _distil(entry: dict) -> dict:
    """Ask the model for the rule behind one edit."""
    existing = load()
    known = "\n".join(f"- {item['lesson']}" for item in existing) or "(none yet)"

    user = (
        f"DOCUMENT: {entry['document']}\n"
        f"ROLE: {entry['role'] or 'unknown'} at {entry['company'] or 'unknown'}\n\n"
        f"EXISTING LESSONS (do not repeat these):\n{known}\n\n"
        f"THE CANDIDATE'S NOTE: {entry['note'] or '(none given)'}\n\n"
        f"THE EDIT:\n{entry['diff'] or '(no text change -- the note is the feedback)'}"
    )

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=os.environ["ANTHROPIC_MODEL"],
        max_tokens=400,
        system=DISTILL_PROMPT,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()

    verdict = json.loads(text)
    if not verdict.get("keep") or not verdict.get("lesson"):
        return {"lesson": None, "why": verdict.get("why", "Nothing generalisable here.")}

    lesson = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
        "lesson": str(verdict["lesson"]).strip(),
        "scope": str(verdict.get("scope", "always")).strip() or "always",
        "learned_at": entry["at"],
        "from": {"folder": entry["folder"], "document": entry["document"],
                 "role": entry["role"], "company": entry["company"]},
    }
    _store(existing + [lesson])
    return {"lesson": lesson["lesson"], "scope": lesson["scope"], "id": lesson["id"]}
