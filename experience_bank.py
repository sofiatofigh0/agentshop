"""
The factual source of truth for everything the agent writes about Sofia Tofigh.

Every claim in a generated resume or cover letter must trace back to something
in this file. The factuality check in application_generator.py compares each
draft against this dictionary and strips anything it cannot find here.

HOW TO READ THE EVIDENCE LEVELS
-------------------------------
Each project carries its facts in fields with different permissions:

  verified            Level 1. Stated directly by Sofia. Use freely.
  framing             Level 2. Reasonable interpretations of the verified work
                      (cross-functional leadership, 0->1 ownership, AI product
                      management). Safe to use because the underlying facts hold.
  metrics             Level 1 numbers that are safe to state as written.
  metric_variants     Real numbers from DIFFERENT analyses of the same project.
                      Pick exactly one per bullet. Never combine or sum them.
  possible_metric_to_validate
                      Level 3. Plausible but unconfirmed. NEVER put these in a
                      resume, cover letter, or strategy document. They exist so
                      Sofia can check them and promote them to metrics.

Never invent employers, dates, degrees, titles, direct reports, technologies,
certifications, revenue ownership, customers, promotions, funding events, or
projects. If a job requires something absent here, it is a gap — say so.
"""

# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

IDENTITY = {
    "name": "Sofia Tofigh",
    "location": "New York City",
    # Not supplied yet. Left blank rather than marked TODO so it does not block
    # generation — a resume will simply omit the header line until filled in.
    "email": "",
    "phone": "",
    "linkedin": "",
    "portfolio": "",
    "languages": [
        {"language": "English", "level": "native/fluent"},
        {"language": "Persian (Farsi)", "level": "fluent"},
        {"language": "German", "level": "intermediate"},
    ],
    "years_pm_experience": (
        "Approximately 4 years of direct product management experience as of 2026, "
        "plus prior technical consulting/engineering experience at Confluent. "
        "Do not write '6 years of PM experience'."
    ),
    "career_narrative": (
        "Technical consulting/engineering (Confluent) -> marketplace Product Manager "
        "(Axial) -> enterprise AI Product Manager (JPMorgan Chase). The through-line "
        "is comfort moving between users, business problems, data, AI systems and "
        "engineering."
    ),
}


# ---------------------------------------------------------------------------
# Roles, newest first
# ---------------------------------------------------------------------------

EXPERIENCE_BANK = {
    "identity": IDENTITY,
    "roles": [
        {
            "company": "JPMorgan Chase",
            "title": "AI Product Manager, Senior Associate",
            "dates": "March 2026 - Present",
            "team": "Product Accelerator Garage",
            "location": "New York",
            "domain": "Financial services / private wealth / enterprise AI",
            "summary": (
                "Builds AI products for financial advisors in a highly regulated "
                "environment — the part of AI product work that demos leave out: "
                "evaluation, reliability, compliance, user trust, legal constraints, "
                "rollout governance and model failure cases."
            ),
            "projects": [
                {
                    "name": "AI meeting summarization for financial advisors",
                    "problem": (
                        "Financial advisors spend meaningful time documenting meetings "
                        "and turning conversations into compliant notes and summaries."
                    ),
                    "actions": [
                        "Led end-to-end product delivery of an AI meeting summarization product for financial advisors",
                        "Conducted and translated research from 6+ advisor interviews",
                        "Identified useful summary structures and turned that research into 3 LLM-powered summarization templates",
                        "Worked through client-consent design and redaction requirements",
                        "Partnered with Legal, Risk and Compliance",
                        "Defined the rollout approach and participated in quality and evaluation design",
                    ],
                    "results": [
                        "Phased rollout targeting approximately 5,000 advisors",
                        "Expected user value of approximately 30 minutes of documentation time saved per meeting",
                    ],
                    "metrics": [
                        "Phased rollout targeting ~5,000 advisors",
                        "~30 minutes of documentation time saved per meeting (expected)",
                    ],
                    "metric_variants": [],
                    "possible_metric_to_validate": [
                        "Advisor adoption rate during the phased rollout",
                        "Measured (rather than expected) time saved per meeting post-launch",
                    ],
                    "framing": [
                        "0->1 product ownership: discovery through delivery",
                        "AI product management in a regulated environment",
                        "Cross-functional leadership across Legal, Risk, Compliance and Engineering",
                        "Enterprise rollout at scale",
                    ],
                    "skills": [
                        "AI product management", "LLMs", "user research", "regulated AI",
                        "compliance", "product discovery", "prompt/product design",
                        "enterprise rollout", "stakeholder management",
                        "human workflow automation",
                    ],
                    "technologies": ["LLMs"],
                    "keywords": [
                        "meeting summarization", "financial advisors", "compliance",
                        "consent", "redaction", "enterprise AI", "rollout",
                    ],
                },
                {
                    "name": "LLM evaluation framework",
                    "problem": (
                        "A meeting-summary product cannot be judged on whether output "
                        "sounds good. It has to meet factual, compliance, quality and "
                        "tone requirements."
                    ),
                    "actions": [
                        "Designed and executed an LLM evaluation framework for AI-generated meeting summaries",
                        "Built an evaluation set of 36 scenarios scored against 12 criteria including factual accuracy, compliance and tone",
                        "Used LLM-as-judge with explicit quality criteria and hard-fail thresholds",
                        "Derived quality standards from advisor expectations rather than assuming them",
                        "Ran iterative prompt refinement against the evaluation set",
                    ],
                    "results": [
                        "Approximately 80% first-run pass rate",
                    ],
                    "metrics": [
                        "36 evaluation scenarios across 12 criteria",
                        "~80% first-run pass rate",
                    ],
                    "metric_variants": [],
                    "possible_metric_to_validate": [
                        "Pass-rate improvement from first version of the rubric to current",
                        "Reduction in advisor-reported summary corrections",
                    ],
                    "framing": [
                        "The hard part was not improving a prompt — it was defining what "
                        "'correct' meant and turning subjective advisor expectations into "
                        "repeatable evaluation criteria",
                        "AI quality and reliability ownership",
                    ],
                    "skills": [
                        "evals", "LLM-as-judge", "AI quality", "model evaluation",
                        "prompt iteration", "rubric design", "failure analysis",
                        "regulated AI", "product metrics",
                    ],
                    "technologies": ["LLMs", "LLM-as-judge"],
                    "keywords": [
                        "evaluation", "eval harness", "rubric", "hard-fail thresholds",
                        "factual accuracy", "model quality",
                    ],
                },
                {
                    "name": "AI feedback classification (LLM + RAG)",
                    "problem": (
                        "An existing machine-learning classification system ran at "
                        "roughly 30-60% error rates and required significant manual triage "
                        "of approximately 400-500 advisor feedback submissions per month."
                    ),
                    "actions": [
                        "Reframed the problem rather than treating it as 'improve the model'",
                        "Established which categories actually mattered and what correct classification meant",
                        "Analyzed where the existing system failed and how humans reviewed errors",
                        "Replaced/redesigned the approach using an LLM + RAG pipeline",
                        "Connected model performance to operational time saved",
                    ],
                    "results": [
                        "Manual triage fell from approximately 50 hours/month to approximately 10 hours/month",
                    ],
                    "metrics": [
                        "Legacy system error rate ~30-60%",
                        "~400-500 advisor feedback submissions processed per month",
                        "Manual triage ~50 hours/month -> ~10 hours/month (~80% reduction)",
                    ],
                    "metric_variants": [],
                    "possible_metric_to_validate": [
                        "Post-migration classification accuracy of the LLM + RAG pipeline",
                        "Dollar value of the operational hours recovered",
                    ],
                    "framing": [
                        "Recognizing the problem was taxonomy and definition, not model quality",
                        "Human-in-the-loop system design",
                        "Translating technical work into operational business impact",
                    ],
                    "skills": [
                        "LLMs", "RAG", "classification", "workflow automation",
                        "AI evaluation", "operations", "human-in-the-loop", "ambiguity",
                        "taxonomy design", "measurable productivity",
                    ],
                    "technologies": ["LLMs", "RAG"],
                    "keywords": [
                        "classification", "triage", "legacy ML replacement", "RAG",
                        "operational leverage",
                    ],
                },
            ],
        },
        {
            "company": "Axial",
            "title": "Product Manager",
            "title_history": "Associate Product Manager initially, later Product Manager",
            "dates": "October 2022 - November 2025",
            "location": "New York",
            "domain": "B2B M&A marketplace / fintech / capital markets",
            "summary": (
                "Owned marketplace and workflow surfaces across a three-sided market of "
                "buyers, sellers and advisors/intermediaries: deal discovery, onboarding, "
                "partner supply, documents, notifications, analytics, mobile, AI-generated "
                "content and down-funnel transaction workflows. This is the role that "
                "demonstrates shipping speed and volume."
            ),
            "projects": [
                {
                    "name": "Partner / supply API integrations (Transworld, Sunbelt)",
                    "problem": (
                        "Important deal supply arrived through partner workflows that "
                        "relied on manual and legacy ingestion."
                    ),
                    "actions": [
                        "Shipped API integrations with Axial's two largest broker partners, Transworld and Sunbelt",
                        "Automated ingestion that had previously been manual",
                        "Coordinated across partners and internal GTM",
                    ],
                    "results": [
                        "Automated ingestion for more than 60% of platform deal flow",
                        "Eliminated approximately 10+ hours/week of manual effort",
                    ],
                    "metrics": [
                        "API integrations became responsible for 60%+ of incoming deal flow",
                        "~10+ hours/week of manual effort eliminated",
                        "Partner/supply integrations represented roughly one-third of closures in prior analysis",
                    ],
                    "metric_variants": [],
                    "possible_metric_to_validate": [
                        "Deal volume increase attributable to the integrations",
                        "Time-to-list improvement for partner-sourced deals",
                    ],
                    "framing": [
                        "Marketplace supply and liquidity ownership",
                        "Technical/API product management",
                        "Multi-sided marketplace work",
                    ],
                    "skills": [
                        "APIs", "integrations", "marketplace liquidity", "supply",
                        "B2B SaaS", "partner products", "technical PM",
                        "workflow automation", "GTM coordination",
                    ],
                    "technologies": ["REST APIs"],
                    "keywords": ["API integration", "partner supply", "deal flow", "ingestion"],
                },
                {
                    "name": "Mobile product redesign",
                    "problem": "Axial's buyer experience was poorly optimized for mobile usage.",
                    "actions": [
                        "Led a responsive redesign of deal discovery, navigation and mobile workflows",
                        "Worked across approximately 2 designers and 7 engineers",
                    ],
                    "results": [
                        "Substantial increase in mobile engagement at launch, with sustained lift afterwards",
                    ],
                    "metrics": [],
                    # THREE numbers from THREE different analyses. Use exactly one.
                    "metric_variants": [
                        {
                            "claim": "~+127% mobile engagement/usage at launch",
                            "basis": "launch analysis",
                            "use_when": "the role rewards launch impact and visible step-changes",
                        },
                        {
                            "claim": "~+15% sustained mobile usage",
                            "basis": "longer-term analysis",
                            "use_when": "the role rewards durable outcomes over launch spikes",
                        },
                        {
                            "claim": "~18% improvement in mobile buyer retention",
                            "basis": "current resume framing; retention definition",
                            "use_when": "the role is retention- or engagement-metric oriented",
                        },
                    ],
                    "metric_warning": (
                        "These three come from different analyses with different metric "
                        "definitions. Use exactly ONE per bullet. Never combine them, "
                        "never sum them, never present two as if they measure the same thing."
                    ),
                    "possible_metric_to_validate": [
                        "Which of the three definitions Sofia most wants to defend in interviews",
                    ],
                    "framing": [
                        "End-to-end PM ownership of a redesign",
                        "Cross-functional leadership across design and engineering",
                    ],
                    "skills": [
                        "mobile", "product redesign", "UX", "discovery", "analytics",
                        "cross-functional leadership", "marketplace", "engagement",
                        "retention",
                    ],
                    "technologies": [],
                    "keywords": ["mobile", "responsive", "deal discovery", "navigation"],
                },
                {
                    "name": "NDA / CIM confidential document workflows",
                    "problem": (
                        "M&A marketplace participants need to share sensitive information "
                        "only after the appropriate confidentiality steps."
                    ),
                    "actions": [
                        "Built NDA workflow and CIM/document sharing",
                        "Shipped multi-document upload and rule-based distribution",
                        "Automated the confidentiality workflow",
                        "Worked on watermarking and controlled document handling in related iterations",
                    ],
                    "results": [
                        "7-day CIM sharing improved from approximately 16% to 37%",
                    ],
                    "metrics": [
                        "7-day CIM sharing improved from ~16% to ~37%",
                    ],
                    "metric_variants": [
                        {
                            "claim": "7-day CIM sharing improved from ~16% to ~37%",
                            "basis": "funnel conversion measurement",
                            "use_when": "transaction workflow, funnel or conversion roles — the strongest version",
                        },
                        {
                            "claim": "~16% improvement in document access rate",
                            "basis": "current resume framing; likely a different measurement",
                            "use_when": "only if Sofia confirms which measurement this is",
                        },
                    ],
                    "metric_warning": (
                        "The 16%->37% figure and the '~16% document access rate' figure may "
                        "describe different measurements. Do not combine them and do not "
                        "present the second without validation."
                    ),
                    "possible_metric_to_validate": [
                        "Whether the '~16% document access rate' is a distinct metric or a restatement",
                        "Downstream deal-progression impact of faster CIM sharing",
                    ],
                    "framing": [
                        "Transaction workflow and funnel conversion ownership",
                        "Trust and permissioning design in a regulated-adjacent context",
                    ],
                    "skills": [
                        "workflow design", "fintech", "M&A", "documents", "permissioning",
                        "funnel conversion", "automation", "trust",
                    ],
                    "technologies": ["e-signature workflows"],
                    "keywords": ["NDA", "CIM", "confidentiality", "document sharing", "watermarking"],
                },
                {
                    "name": "Notification infrastructure migration",
                    "problem": "Email notification infrastructure was unreliable and hard to maintain.",
                    "actions": [
                        "Migrated approximately 15 email notification types to Courier",
                        "Resolved email threading issues",
                        "Documented the notification architecture",
                    ],
                    "results": [
                        "Improved reliability and maintainability; fewer support tickets",
                    ],
                    "metrics": [
                        "~15 email notification types migrated to Courier",
                        "Email-related support tickets reduced ~44%",
                    ],
                    "metric_variants": [],
                    "possible_metric_to_validate": [
                        "Deliverability or open-rate change after the migration",
                    ],
                    "framing": [
                        "Platform/infrastructure product ownership",
                        "Lifecycle engagement surface",
                    ],
                    "skills": [
                        "infrastructure product", "notifications", "platform", "migration",
                        "customer support reduction", "lifecycle engagement",
                    ],
                    "technologies": ["Courier"],
                    "keywords": ["notifications", "email", "migration", "infrastructure"],
                },
                {
                    "name": "AI-generated deal headlines",
                    "problem": "Marketplace listings were inconsistent and often unclear to buyers.",
                    "actions": [
                        "Launched AI-written/AI-assisted deal headlines in a customer-facing marketplace",
                        "Built QA and rubric-based audits covering factuality and salience",
                        "Designed guardrails with fallback to the original content when model quality was uncertain",
                    ],
                    "results": [
                        "Approximately +15% buyer engagement",
                    ],
                    "metrics": [
                        "~+15% buyer engagement",
                    ],
                    "metric_variants": [],
                    "possible_metric_to_validate": [
                        "Share of listings where the AI headline was kept over the original",
                        "Rubric audit pass rate",
                    ],
                    "framing": [
                        "Shipping customer-facing generative AI before the JPM AI work",
                        "The product optimized for safe improvement rather than generation rate: "
                        "when output quality was uncertain, preserve the original copy",
                        "Evaluation and guardrail design",
                    ],
                    "skills": [
                        "generative AI", "evaluation", "guardrails", "marketplace",
                        "content generation", "buyer engagement",
                    ],
                    "technologies": ["LLMs"],
                    "keywords": ["generative AI", "guardrails", "fallback", "content quality"],
                },
                {
                    "name": "Analytics instrumentation",
                    "problem": "Product decisions needed behavioral evidence across web and mobile.",
                    "actions": [
                        "Integrated GA4 and FullStory across web and mobile",
                        "Used the instrumentation for roadmap prioritization, post-launch monitoring and rapid iteration",
                    ],
                    "results": ["Behavioral data available for prioritization and post-launch monitoring"],
                    "metrics": [],
                    "metric_variants": [],
                    "possible_metric_to_validate": [
                        "Number of shipped decisions attributable to the instrumentation",
                    ],
                    "framing": ["Data-informed product practice", "Quantitative and qualitative behavior analysis"],
                    "skills": [
                        "product analytics", "instrumentation", "roadmap prioritization",
                    ],
                    "technologies": ["GA4", "FullStory"],
                    "keywords": ["analytics", "instrumentation", "behavioral data"],
                },
                {
                    "name": "Down-funnel / transaction reporting",
                    "problem": "Down-funnel transaction activity was under-measured.",
                    "actions": ["Built down-funnel and transaction reporting"],
                    "results": ["Increased visibility into down-funnel and LOI activity"],
                    "metrics": [
                        "Down-funnel reporting activity ~+238% YoY",
                        "LOI-related activity ~+18% MoM",
                    ],
                    "metric_warning": (
                        "Keep the original timeframe with each number: YoY for the 238%, "
                        "MoM for the 18%. Do not restate either without its timeframe."
                    ),
                    "metric_variants": [],
                    "possible_metric_to_validate": [
                        "Whether the +238% reflects reporting coverage or genuine activity growth",
                    ],
                    "framing": ["Marketplace funnel and transaction analytics"],
                    "skills": ["analytics", "B2B SaaS funnels", "transaction products"],
                    "technologies": [],
                    "keywords": ["down-funnel", "LOI", "transaction reporting"],
                },
            ],
            "additional_themes": [
                "onboarding",
                "buyer/seller marketplace matching",
                "anonymized matching",
                "NDA e-sign / confidentiality workflows",
                "CIM watermarking",
                "buyside digest",
                "deal discovery",
                "transaction funnel",
                "customer feedback and behavior analysis",
            ],
        },
        {
            "company": "Confluent",
            "title": "Associate Consulting Engineer",
            "dates": "June 2021 - October 2022",
            "location": "New York",
            "domain": "Enterprise data infrastructure / event streaming",
            "summary": (
                "Technical consulting and engineering for Fortune 500 banking and "
                "insurance clients on Apache Kafka and event-streaming systems. This "
                "role is the reason Sofia should not be framed as a non-technical PM."
            ),
            "projects": [
                {
                    "name": "Enterprise Kafka adoption and modernization",
                    "problem": (
                        "Fortune 500 banking and insurance organizations needed to "
                        "modernize toward real-time, event-driven data infrastructure."
                    ),
                    "actions": [
                        "Helped clients design Kafka adoption strategies",
                        "Worked on multi-year modernization approaches",
                        "Addressed security and compliance requirements",
                        "Translated technical systems into enterprise implementation plans",
                    ],
                    "results": [
                        "Clients equipped with adoption strategies and implementation plans for event-driven infrastructure",
                    ],
                    "metrics": [],
                    "metric_variants": [],
                    "possible_metric_to_validate": [
                        "Number of enterprise clients advised",
                        "Scale of any specific deployment (throughput, cluster size)",
                        "Named industries or deal sizes that can be disclosed",
                    ],
                    "framing": [
                        "Customer-embedded / forward-deployed technical work",
                        "Credible technical foundation in APIs, streaming data, infrastructure and enterprise architecture",
                        "Direct collaboration with engineering teams",
                    ],
                    "skills": [
                        "Apache Kafka", "event streaming", "distributed systems",
                        "enterprise architecture", "technical consulting", "security and compliance",
                        "client communication",
                    ],
                    "technologies": ["Apache Kafka", "event streaming", "distributed/real-time data systems"],
                    "keywords": [
                        "Kafka", "event-driven", "real-time data", "enterprise", "modernization",
                        "forward deployed",
                    ],
                },
            ],
        },
    ],

    # -----------------------------------------------------------------------
    # Independent work — real, but do not inflate to production scale
    # -----------------------------------------------------------------------
    "personal_projects": [
        {
            "name": "AI Daily Brief",
            "type": "Personal AI product / builder project",
            "problem": "Wanted a personalized intelligence and content briefing workflow.",
            "actions": [
                "Built a pipeline covering podcast ingestion, transcription and retrieval",
                "Added web context and AI-generated summaries",
                "Added background functions/automation with human review",
            ],
            "results": ["A working personal briefing workflow"],
            "metrics": [],
            "scale_caveat": (
                "Primarily a personal project. Do not describe it as production, "
                "do not imply users beyond Sofia, do not invent scale."
            ),
            "framing": ["Hands-on AI building", "RAG and retrieval thinking", "Pipeline and workflow design"],
            "skills": ["RAG", "retrieval", "pipelines", "workflow design", "transcription"],
            "technologies": ["LLMs", "transcription", "retrieval"],
            "keywords": ["RAG", "ingestion", "summarization", "automation"],
        },
        {
            "name": "Personal Job Opportunity Agent",
            "type": "Personal learning / AI-agent project",
            "problem": "Wanted to understand agent architecture directly rather than through a framework.",
            "actions": [
                "Built a Python agent on the Anthropic API with tool use and web search, deliberately without LangChain or CrewAI",
                "Started from a non-agentic single-call baseline before adding tools, to have a control to measure against",
                "Gave the model discretion over whether research is necessary, what to query, and whether another search is warranted",
                "Kept tool execution, maximum search count, loop termination and message-state handling in deterministic Python",
                "Built an evaluation harness tracking both recommendation accuracy and tool-use behavior",
            ],
            "results": [
                "Agent takes a job description, compares it against a structured candidate profile, and returns APPLY / MAYBE / SKIP",
                "Distinguishes hard constraints from strong preferences",
                "Decides whether external research could materially change the recommendation and searches selectively",
                "Refines a follow-up search based on prior results",
            ],
            "metrics": [],
            "scale_caveat": "A personal learning project. Do not describe it as a shipped product or imply users.",
            "lessons": [
                "Evaluate both outcomes and trajectories",
                "Tool-use behavior can vary across runs while recommendations stay stable",
                "Poor fixtures create misleading eval results",
                "Profile and schema design strongly affect model reasoning",
            ],
            "framing": [
                "Agent product thinking",
                "Eval design and prompt iteration",
                "State representation, cost and latency awareness",
                "Building without an agent framework",
            ],
            "skills": [
                "agent architecture", "tool use", "eval design", "prompt iteration",
                "state design", "Python",
            ],
            "technologies": ["Python", "Anthropic API", "tool use", "web search"],
            "keywords": ["agent", "tool use", "evals", "APPLY/MAYBE/SKIP", "no framework"],
        },
    ],

    # -----------------------------------------------------------------------
    "education": [
        {
            "institution": "Columbia University",
            "credential": "BA, Economics",
            "dates": "2015 - 2019",
            "notes": "",
            "framing": (
                "Economics plus technical consulting plus product creates business "
                "intuition, systems thinking, quantitative reasoning and product judgement."
            ),
        },
    ],

    # -----------------------------------------------------------------------
    "skills": {
        "product": [
            "Product management", "AI product management", "customer discovery",
            "0->1 product development", "workflow design", "marketplace products",
            "product analytics", "experimentation and measurement",
            "stakeholder management", "cross-functional execution",
        ],
        "ai": [
            "LLM-powered products", "RAG", "LLM evaluation", "LLM-as-judge",
            "prompt design and iteration", "rubric design", "AI failure-mode analysis",
            "human-in-the-loop systems", "guardrail design",
        ],
        "technical": [
            "API integrations", "Apache Kafka", "event streaming", "SQL",
            "analytics instrumentation", "enterprise technical architecture",
        ],
        "tools": ["GA4", "FullStory", "Figma", "Courier", "Python", "Anthropic API"],
        "domains": [
            "B2B SaaS", "marketplaces", "fintech / capital markets", "M&A",
            "enterprise AI", "private wealth",
        ],
        "collaboration": [
            "Legal / Risk / Compliance collaboration", "Design", "Engineering",
            "Data Science", "Sales", "Operations",
        ],
        "positioning_caveat": (
            "Do not claim expert-level hands-on software engineering. Sofia is "
            "technically fluent with an engineering/consulting foundation, but "
            "positioning stays product-first unless the role specifically rewards "
            "technical implementation."
        ),
    },

    # -----------------------------------------------------------------------
    "other": [
        {
            "item": "Coding bootcamp, around 2020",
            "use": (
                "Not a default resume entry. Useful for founder-type applications, "
                "questions about grit, unconventional paths, or 'tell us something "
                "not on your resume'."
            ),
        },
        {
            "item": "Worked/bartended during college",
            "use": "Not a default resume entry. Same uses as above.",
        },
        {
            "item": "Grew up across New York and Tehran",
            "use": (
                "Use selectively — only where international perspective, cross-cultural "
                "communication, global operations or heterogeneous users genuinely "
                "matter, or where the application asks for unusual background. Never "
                "insert gratuitously."
            ),
        },
    ],

    # -----------------------------------------------------------------------
    # Prepared evidence packages. Each points at projects above; they add no
    # new facts, they just say which evidence answers which kind of question.
    # -----------------------------------------------------------------------
    "interview_stories": [
        {
            "id": 1,
            "title": "Ambiguous AI / eval problem",
            "source": "JPMorgan Chase — LLM evaluation framework",
            "story": "The hard problem was not 'make the model better'. The first challenge was defining what correct meant.",
            "use_for": ["ambiguous product problems", "AI evals", "product quality", "0->1 AI", "working without a playbook", "model reliability"],
        },
        {
            "id": 2,
            "title": "Broken system -> AI redesign",
            "source": "JPMorgan Chase — AI feedback classification",
            "story": "A legacy ML system ran at 30-60% errors. Reframed the problem, shipped an LLM + RAG pipeline, cut manual triage ~80%.",
            "use_for": ["replacing legacy ML", "measurable AI impact", "operational leverage", "human-in-the-loop systems"],
        },
        {
            "id": 3,
            "title": "User discovery plus regulated shipping",
            "source": "JPMorgan Chase — AI meeting summarization",
            "story": "6+ advisor interviews turned into 3 summarization templates, shipped through Legal, Risk and Compliance to ~5,000 advisors.",
            "use_for": ["customer discovery", "regulated environments", "Legal/Risk/Compliance", "AI trust", "enterprise rollout"],
        },
        {
            "id": 4,
            "title": "Shipping / marketplace impact",
            "source": "Axial — mobile product redesign",
            "story": "Led a responsive redesign across 2 designers and 7 engineers, with a large measured lift at launch.",
            "use_for": ["end-to-end PM ownership", "cross-functional leadership", "measurable launch results", "customer experience", "mobile"],
        },
        {
            "id": 5,
            "title": "Technical / platform product",
            "source": "Axial — partner API integrations, plus Confluent",
            "story": "Shipped API integrations covering 60%+ of deal flow, on a foundation of Kafka and event-streaming consulting for Fortune 500 clients.",
            "use_for": ["technical PM", "APIs", "integrations", "platform", "infrastructure", "data"],
        },
        {
            "id": 6,
            "title": "Workflow / funnel optimization",
            "source": "Axial — NDA/CIM workflows",
            "story": "Rebuilt the confidentiality workflow and moved 7-day CIM sharing from ~16% to ~37%.",
            "use_for": ["funnels", "marketplace transaction workflows", "conversion", "user friction", "operational automation"],
        },
        {
            "id": 7,
            "title": "Early generative-AI product",
            "source": "Axial — AI-generated deal headlines",
            "story": "Shipped customer-facing generative AI with rubric audits and a fallback to original copy when quality was uncertain — optimizing for safe improvement, not generation rate.",
            "use_for": ["GenAI", "guardrails", "evaluation", "product metrics", "model uncertainty"],
        },
        {
            "id": 8,
            "title": "Builder / agent story",
            "source": "Personal Job Opportunity Agent and AI Daily Brief",
            "story": "Built an agent with tool use and an eval harness from scratch, without a framework, starting from a non-agentic baseline as a control.",
            "use_for": ["agents", "hands-on AI", "side projects", "building without a framework", "learning quickly", "product and technical fluency"],
        },
    ],
}


# ---------------------------------------------------------------------------
# Placeholder detection — deterministic Python, not a model judgement.
# ---------------------------------------------------------------------------

def missing_fields() -> list:
    """Return the TODO placeholders still left in the bank."""
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


def unvalidated_metrics() -> list:
    """Every possible_metric_to_validate in the bank, with its source.

    These must never reach a generated document. Surfacing them here lets Sofia
    check them and promote the ones that hold into `metrics`.
    """
    out = []
    for role in EXPERIENCE_BANK["roles"]:
        for project in role["projects"]:
            for metric in project.get("possible_metric_to_validate", []):
                out.append((role["company"], project["name"], metric))
    return out
