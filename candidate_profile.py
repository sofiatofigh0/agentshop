"""
What Sofia wants — preferences, goals, constraints, voice and tailoring rules.

Kept deliberately separate from experience_bank.py:

    candidate_profile.py  decides APPLY / MAYBE / SKIP, and governs how things
                          are written. It is preference, not evidence.
    experience_bank.py    is the only thing a resume or cover letter may draw
                          factual claims from.

Nothing in this file may become a factual claim about Sofia's work history.

Two key names are load-bearing: `hard_constraints` and `strong_preferences` are
referenced by name in agent.py's system prompt, which weighs them differently.
Renaming them silently changes how recommendations are made.
"""

CANDIDATE_PROFILE = {
    "name": "Sofia Tofigh",
    "location": "New York City",

    "positioning": (
        "AI Product Manager / Senior Product Manager with an unusually technical "
        "foundation, building LLM-powered products, evaluation systems, workflow "
        "automation, API integrations, marketplace products and data-informed user "
        "experiences."
    ),

    "career_narrative": (
        "Technical consulting/engineering -> marketplace Product Manager -> enterprise "
        "AI Product Manager. Worth using often: it explains why she moves comfortably "
        "between users, business problems, data, AI systems and engineering."
    ),

    "years_product_experience": (
        "Approximately 4 years of direct PM experience as of 2026, plus prior technical "
        "consulting/engineering. Never write '6 years of PM experience'."
    ),

    "domains_worked": [
        "technical consulting / engineering",
        "B2B SaaS",
        "marketplaces",
        "fintech / capital markets",
        "enterprise AI",
        "LLM product development",
    ],

    "product_strengths": [
        "ambiguous 0->1 product problems",
        "translating messy user problems into product requirements",
        "customer discovery",
        "workflow design",
        "marketplace products",
        "operational automation",
        "AI product development",
        "product analytics",
        "experimentation and measurement",
        "API / integration products",
        "cross-functional execution across Legal, Risk, Compliance, Design, Engineering, Data Science, Sales and Operations",
        "connecting technical and model performance to actual product outcomes",
    ],

    "desired_role_types": [
        "Senior Product Manager",
        "AI Product Manager",
        "Agent / agentic product roles",
        "Forward Deployed Product Manager",
        "Product Operations with significant AI/product ownership",
        "Founding / early product roles where appropriate",
        "Marketplace / platform roles",
        "Technical product roles",
    ],

    "career_goals": [
        "Grow into product leadership / Head of Product",
        "Eventually found a company",
        "Work closer to users",
        "Ship faster",
        "Own meaningful product outcomes",
        "Stay hands-on with AI rather than becoming purely programmatic or administrative",
    ],

    # -----------------------------------------------------------------------
    # NOTE — REVIEW THIS LIST.
    # The source material states nothing as an absolute dealbreaker; location is
    # phrased as "evaluate carefully rather than assuming flexibility", which is
    # a strong signal, not a refusal. So this list is empty by design rather
    # than by omission: an empty list means no single factor can justify SKIP on
    # its own, and everything is weighed holistically.
    #
    # If any of these are in fact absolute, move them up from
    # `strong_preferences` and recommendations will change accordingly:
    #   "Will not relocate outside New York City"
    #   "Will not accept compensation or seniority materially below current level"
    #   "Will not accept a role with no direct user access"
    # -----------------------------------------------------------------------
    "hard_constraints": [],

    "strong_preferences": [
        "New York preferred; remote is attractive. Relocation requirements must be examined explicitly, never assumed acceptable",
        "Fast-moving environment with meaningful ownership",
        "Direct access to users",
        "Strong engineering partnership and the ability to ship and iterate",
        "Measurable product outcomes and technically substantive work",
        "AI-native or genuinely technical product problems",
        "Companies where product is central rather than a support function",
        "Roles where ambiguity is a feature rather than an organizational failure",
        "Avoids highly bureaucratic environments",
        "Avoids roles where the PM has little user access",
        "Avoids vague scope without real ownership",
        "Avoids roles that are mostly project management",
        "Avoids companies where 'AI' is superficial positioning rather than a real product capability",
        "Avoids roles requiring the PM to substitute for an engineering team",
        "Avoids roles where compensation, seniority or ownership appear materially below her experience",
    ],

    # -----------------------------------------------------------------------
    # Voice. Used by the generation prompts, not by the recommendation.
    # -----------------------------------------------------------------------
    "voice": {
        "wanted": [
            "intelligent", "direct", "slightly conversational", "specific",
            "evidence-driven", "occasionally philosophical when the question warrants it",
            "confident without inflated corporate language", "concise",
            "willing to make an unusual but defensible observation",
        ],
        "banned_phrases": [
            "I am thrilled to apply",
            "I am passionate about",
            "dynamic team",
            "innovative company",
            "leveraging synergies",
        ],
        "banned_habits": [
            "generic statements that could apply to 100 companies",
            "excessive em dashes",
            "empty praise",
            "repeating the company's own About page back to them",
            "sounding corporate or AI-generated",
        ],
        "cover_letter_shape": (
            "Two to three strong paragraphs, not a five-paragraph letter. Must contain: "
            "(1) one genuinely specific reason this company or problem is interesting, "
            "(2) one or two unusually relevant pieces of Sofia's experience, "
            "(3) a coherent reason her trajectory leads naturally to this role."
        ),
        "cover_letter_questions_to_answer_first": [
            "What is genuinely unusual or interesting about this company?",
            "Why would someone with Sofia's exact trajectory care?",
            "Which one or two experiences create an unusually strong connection?",
            "Is there a more interesting opening than 'I am excited to apply'?",
        ],
        "opening_guidance": (
            "Good openings start from a product observation, an unusual connection "
            "between Sofia's experience and the company's problem, a tension in the "
            "industry, or why the problem itself is compelling. Never quirky for "
            "novelty. Specific over enthusiastic, evidence over adjectives, point of "
            "view over generic praise."
        ),
    },

    "resume_writing_rules": {
        "bullet_shape": "ACTION + DIFFICULTY/CONTEXT + RESULT",
        "good_example": (
            "Replaced a legacy ML classifier with an LLM + RAG pipeline processing "
            "400-500 monthly advisor submissions, cutting manual triage ~80%."
        ),
        "bad_example": "Responsible for implementing an AI feedback classification system.",
        "preferred_verbs": [
            "built", "shipped", "redesigned", "replaced", "launched", "led",
            "automated", "reduced", "increased", "designed", "evaluated",
        ],
        "use_sparingly": ["owned — keep it meaningful by using it rarely"],
        "avoid_verbs": [
            "collaborated", "supported", "helped — unless that genuinely reflects limited ownership",
        ],
        "no_responsibilities_only_bullets": True,
    },

    # Which evidence leads, by the kind of role. Pointers into the bank.
    "emphasis_by_role_family": {
        "ai_or_agent": [
            "JPM AI feedback classification",
            "JPM LLM evaluation framework",
            "JPM meeting summarization",
            "Axial AI-generated deal headlines",
            "Personal agent projects",
            "Confluent technical background",
        ],
        "marketplace": [
            "Axial partner API supply integrations",
            "Axial mobile redesign",
            "Axial NDA/CIM workflows",
            "Axial marketplace analytics",
            "Matching and funnel work",
        ],
        "technical_or_platform": [
            "Confluent",
            "Axial partner API integrations",
            "Axial notification infrastructure",
            "JPM RAG / AI systems",
            "Analytics and instrumentation work",
        ],
        "forward_deployed": [
            "Confluent enterprise consulting",
            "JPM advisor discovery",
            "JPM AI iterations",
            "Axial customer and workflow work",
        ],
        "startup_or_founding": [
            "Breadth across product surfaces",
            "Comfort with ambiguity",
            "Shipping record at Axial",
            "Hands-on AI and side projects",
            "Technical background",
            "Willingness to work across product / operations / engineering boundaries",
        ],
    },

    "personal_background_policy": (
        "Sofia grew up across New York and Tehran, completed a coding bootcamp around "
        "2020, and worked/bartended during college. Use these only where they genuinely "
        "fit — international perspective, cross-cultural communication, global "
        "operations, heterogeneous users, founder-type applications, grit questions, "
        "unconventional-path questions, or 'tell us something not on your resume'. "
        "Never insert them gratuitously."
    ),

    "tailoring_rule": (
        "There is no single best resume. The resume must change meaningfully by role: "
        "see emphasis_by_role_family."
    ),
}
