"""
Who we are evaluating jobs for.

Standing context, not per-job data: this is the same on every evaluation. Edit
the values freely — the agent reads whatever is here, so changing a preference
changes the recommendations without touching any other file.
"""

CANDIDATE_PROFILE = {
    "years_product_experience": 6,
    "ai_product_experience": (
        "2 years as PM on LLM-powered features. Shipped an internal evaluation "
        "tool and a RAG-based customer support assistant."
    ),
    "technical_background": (
        "CS degree. Reads Python comfortably and builds prototypes against APIs, "
        "but is not a production engineer and does not want to be."
    ),
    "preferred_location": "Remote, or hybrid in New York City",
    "desired_role_types": [
        "Senior PM on AI/ML developer tools or infrastructure",
        "Product lead at a Series A to Series C company",
        "0-to-1 ownership with a dedicated engineering team",
    ],
    "career_goals": [
        "Grow into a Director of Product role within about three years",
        "Deepen technical credibility in AI evaluation and infrastructure",
        "Work directly with engineers rather than through layers of management",
    ],
    # Non-negotiable. A role that violates one of these can be ruled out on that
    # basis alone.
    "hard_constraints": [
        "Will not relocate from New York City",
        "Will not work without a salary — no equity-only arrangements",
        "Will not accept a six-day work week or an always-on / on-call culture",
    ],
    # Real dislikes that lower fit. Any one of them is survivable if the rest of
    # the opportunity is strong; several together are not.
    "strong_preferences": [
        "Wants a clearly defined scope with a named owner",
        "Wants a disclosed compensation band before investing time",
        "Wants a dedicated engineering team rather than to substitute for one",
        "Prefers Series A to Series C over pre-seed or late-stage",
        "Prefers working directly with engineers rather than through layers",
    ],
}
