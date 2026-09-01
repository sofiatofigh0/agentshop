"""
The factual source of truth for everything the agent writes about you.

Every claim in a generated resume or cover letter must trace back to something
in this file. The factuality check in application_generator.py compares the
draft against this dictionary and strips anything it cannot find here — so an
empty or half-filled bank produces a thin resume, never an invented one.

Keep this file honest and boring. It is not marketing copy; it is evidence.
Write what actually happened, including the numbers you can defend in an
interview. The model is allowed to reword and reorder this material. It is not
allowed to add to it.

FILL THIS IN BEFORE GENERATING ANYTHING. Every "TODO" below is a blank left
deliberately — the agent refuses to generate application materials while any of
them remain, because it will not invent facts on your behalf.
"""

EXPERIENCE_BANK = {
    "roles": [
        {
            "company": "TODO: employer name",
            "title": "TODO: your official job title, exactly as it appears",
            "dates": "TODO: e.g. Mar 2022 - present",
            "summary": "TODO: one or two sentences on the scope you owned",
            "projects": [
                {
                    "name": "TODO: short project name",
                    "problem": "TODO: what was actually wrong or needed",
                    "actions": [
                        "TODO: something you personally did",
                    ],
                    "results": [
                        "TODO: what changed as a result",
                    ],
                    "metrics": [
                        "TODO: a number you can defend, with its baseline",
                    ],
                    "skills": ["TODO"],
                    "technologies": ["TODO: only tools you actually used"],
                    "keywords": ["TODO: terms a recruiter might search for"],
                },
            ],
        },
    ],
    "education": [
        {
            "institution": "TODO",
            "credential": "TODO: degree and field",
            "dates": "TODO",
            "notes": "TODO: optional — honors, relevant coursework, or leave blank",
        },
    ],
    "skills": [
        "TODO: list skills you would be comfortable being tested on",
    ],
    "other": [
        "TODO: certifications, publications, talks, open source, volunteering",
    ],
}


# Not part of the bank — just here to show the shape of a filled-in project.
# Delete it or leave it; it is never read by the agent.
EXAMPLE_PROJECT = {
    "name": "Example: checkout latency reduction",
    "problem": "Checkout p95 latency was 4.2s and cart abandonment was rising.",
    "actions": [
        "Profiled the request path and found three redundant pricing calls",
        "Led a two-sprint effort with 4 engineers to consolidate them",
    ],
    "results": ["Latency dropped and abandonment recovered to prior levels"],
    "metrics": ["p95 checkout latency 4.2s -> 1.1s", "cart abandonment -6pp"],
    "skills": ["performance analysis", "cross-team coordination"],
    "technologies": ["Python", "Datadog"],
    "keywords": ["latency", "checkout", "performance"],
}


def missing_fields() -> list:
    """Return the TODO placeholders still left in the bank.

    Deterministic Python check, not a model judgement: we simply look for the
    marker string. Used to refuse generation rather than produce a resume built
    on placeholders.
    """
    found = []

    def walk(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{path}.{key}" if path else key)
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f"{path}[{i}]")
        elif isinstance(node, str) and node.strip().startswith("TODO"):
            found.append(path)

    walk(EXPERIENCE_BANK, "")
    return found


def is_populated() -> bool:
    """True when the bank has no TODO placeholders left."""
    return not missing_fields()
