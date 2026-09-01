"""
What Sofia wants — preferences, goals, voice and tailoring rules.

Kept deliberately separate from experience_bank.py:

    candidate_profile.py  decides APPLY / MAYBE / SKIP and governs how things
                          are written. Preference, not evidence.
    experience_bank.py    the only source of factual claims about her work.

Nothing here may become a factual claim about Sofia's work history.

Load-bearing key names: `hard_constraints` and `strong_preferences` are
referenced by name in agent.py's system prompt, which weighs them differently.
Renaming them silently changes how recommendations are made.
"""

CANDIDATE_PROFILE = {
    "name": "Sofia Tofigh",
    "location": "New York, NY",

    "positioning": (
        "AI Product Manager / Senior Product Manager with an unusually technical "
        "foundation. Builds LLM-powered products, evaluation systems, workflow "
        "automation, API integrations, marketplace products and data-informed user "
        "experiences."
    ),

    "career_narrative": (
        "Technical consulting/engineering -> marketplace Product Manager -> enterprise "
        "AI Product Manager. Worth using often: it explains why she moves comfortably "
        "between users, business problems, data, AI systems and engineering."
    ),

    # -----------------------------------------------------------------------
    # Tenure. Never inflate to satisfy a job description.
    # -----------------------------------------------------------------------
    "experience_length": {
        "direct_pm": "approximately 4 years of direct product management experience",
        "total_technical_and_product": (
            "approximately 5+ years total technical and product experience when "
            "Confluent is relevant to the role"
        ),
        "approved_phrasing": (
            "Product leader with ~4 years of PM experience and an earlier technical "
            "consulting engineering foundation."
        ),
        "never_write": (
            "Do not write '6 years of product management experience', and do not "
            "stretch tenure to match a job description's stated minimum."
        ),
    },

    # -----------------------------------------------------------------------
    # HARD CONSTRAINTS — absolute dealbreakers only.
    #
    # Empty by design, not by omission. Nothing in Sofia's source material is
    # stated as absolute: location is explicitly "a factor to investigate and
    # weigh", not a refusal. An empty list means no single factor can force a
    # SKIP on its own, and every role is weighed holistically.
    #
    # Only add an entry here if Sofia states it as non-negotiable.
    # -----------------------------------------------------------------------
    "hard_constraints": [],

    # -----------------------------------------------------------------------
    # STRONG PREFERENCES — what she is actively looking for. Positive signals.
    # Several violations together can justify SKIP; one on its own cannot.
    # -----------------------------------------------------------------------
    "strong_preferences": [
        "Fast-moving environment with meaningful ownership",
        "Direct access to users",
        "Strong engineering partnership and the ability to ship and iterate",
        "Measurable product outcomes and technically substantive work",
        "AI-native or genuinely technical product problems",
        "Companies where product is central rather than a support function",
        "Roles where ambiguity is a feature rather than an organizational failure",
    ],

    # -----------------------------------------------------------------------
    # LOCATION — a factor to weigh, never an automatic SKIP.
    # -----------------------------------------------------------------------
    "location_policy": {
        "based_in": "New York, NY",
        "preferred": "New York",
        "also_attractive": "Remote",
        "relocation": (
            "Do NOT assume Sofia categorically refuses relocation. Treat a relocation "
            "requirement as a factor to investigate and weigh — note it, ask what would "
            "make it worth it, and let the rest of the opportunity carry the decision. "
            "A relocation requirement alone is not grounds for SKIP."
        ),
        "worth_investigating": [
            "Whether the company will consider remote or an NYC arrangement",
            "Whether relocation support is offered",
            "How much onsite presence is genuinely required",
        ],
    },

    # -----------------------------------------------------------------------
    # ROLE PREFERENCES — what she is and is not targeting.
    # -----------------------------------------------------------------------
    "role_preferences": {
        "primary_targets": [
            "AI Product Manager",
            "Senior Product Manager",
            "Agent / agentic product roles",
            "Forward Deployed AI / Product roles",
            "Technical product roles",
            "High-ownership startup product roles",
            "Product Operations roles — selectively, only when they include real product/AI ownership",
        ],
        "not_targeting": [
            "Pure project management",
            "Purely administrative product operations",
            "Low-ownership coordination roles",
            "Roles substantially below her level",
        ],
    },

    # -----------------------------------------------------------------------
    # DIFFERENTIATORS — why she is an unusual candidate rather than a good one.
    # Use these to decide what leads an application.
    # -----------------------------------------------------------------------
    "differentiators": [
        "Real infrastructure background: Kafka and event-streaming consulting for Fortune 500 banks and insurers, which very few PMs have",
        "Shipped customer-facing generative AI in a marketplace before most PMs had touched it, with guardrails and a quality fallback rather than a demo",
        "Has actually built LLM evaluation: rubrics, LLM-as-judge, hard-fail thresholds, and the harder upstream work of defining what correct means",
        "Replaced a failing legacy ML system with LLM + RAG and measured the result in operational hours, not model metrics",
        "Owned a genuinely multi-sided marketplace end to end — supply, discovery, documents, funnel, mobile, notifications",
        "Ships AI agents by hand outside work, without a framework, including an eval harness",
        "Moves fluently between users, business problems, data, AI systems and engineers rather than specialising in one",
        "Trilingual, raised across New York and Tehran — use selectively, see personal_background_policy",
    ],

    # -----------------------------------------------------------------------
    # POTENTIAL CONCERNS — negative signals to weigh in a recommendation.
    # Distinct from strong_preferences: these are things to examine in a role,
    # not things she is seeking.
    # -----------------------------------------------------------------------
    "potential_concerns": [
        "Highly bureaucratic environments",
        "Roles where the PM has little or no user access",
        "Vague scope without real ownership",
        "Roles that are mostly project management",
        "Companies where 'AI' is superficial positioning rather than a real product capability",
        "Roles requiring the PM to substitute for an engineering team",
        "Compensation, seniority or ownership that appears materially below her experience",
    ],

    # -----------------------------------------------------------------------
    "career_goals": [
        "Grow into product leadership / Head of Product",
        "Eventually found a company",
        "Work closer to users",
        "Ship faster",
        "Own meaningful product outcomes",
        "Stay hands-on with AI rather than becoming purely programmatic or administrative",
    ],

    # -----------------------------------------------------------------------
    # WRITING VOICE — governs cover letters and any prose. Not the resume's
    # factual content, only its register.
    # -----------------------------------------------------------------------
    "writing_voice": {
        "should_feel": [
            "intelligent", "specific", "concise", "confident",
            "slightly unconventional", "human", "thoughtful", "evidence-driven",
            "capable of making a real observation about the company or industry",
        ],
        "banned_phrases": [
            "I am thrilled to apply",
            "I have always been passionate about",
            "I believe my skills make me an excellent fit",
            "I am excited to apply",
            "dynamic team",
            "innovative company",
            "leveraging synergies",
        ],
        "banned_habits": [
            "generic enthusiasm",
            "obvious AI phrasing",
            "unnecessary em dashes",
            "lists of adjectives",
            "corporate jargon",
            "repeating the job description back",
            "repeating the company's own About page back to them",
            "the generic three-paragraph cover-letter structure",
            "statements that could apply to a hundred other companies",
        ],
        "cover_letter_shape": (
            "Two to three strong paragraphs. It must contain: (1) one genuinely "
            "specific reason this company or problem is interesting, (2) one or two "
            "unusually relevant pieces of Sofia's experience, (3) a coherent reason "
            "her trajectory leads naturally to this role. It should read as though "
            "she had an actual reason to write to THIS company."
        ),
        "questions_to_answer_before_writing": [
            "What is genuinely unusual or interesting about this company?",
            "Why would someone with Sofia's exact trajectory care?",
            "Which one or two experiences create an unusually strong connection?",
            "Is there a more interesting opening than 'I am excited to apply'?",
        ],
        "opening_guidance": (
            "Good openings start from a product observation, an unusual connection "
            "between her experience and the company's problem, a tension in the "
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

    # Which evidence leads, by kind of role. Pointers into the experience bank.
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
            "Confluent — lead with this, expanded rather than compressed",
            "Axial partner API integrations",
            "Axial notification infrastructure",
            "JPM RAG / AI systems",
            "Analytics and instrumentation work",
        ],
        "forward_deployed": [
            "Confluent enterprise consulting — lead with this",
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
        "Personal background never appears in a resume by default. Use it only where "
        "it creates a genuinely relevant application narrative: international "
        "perspective, cross-cultural communication, global operations, heterogeneous "
        "users, founder-type applications, grit or unconventional-path questions, or "
        "'tell us something not on your resume'. See personal_background in the "
        "experience bank for what is available."
    ),

    "tailoring_rule": (
        "There is no single best resume. The resume must change meaningfully by role: "
        "see emphasis_by_role_family and the role_preferences targets."
    ),
}
