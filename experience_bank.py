"""
The factual source of truth for everything the agent writes about Sofia Tofigh.

Every claim in a generated resume or cover letter must trace back to this file.

METRIC TYPES
------------
  verified_metric              An exact figure. State it as written.
  approximate_supported_metric A real measurement Sofia has stated with
                               approximation. Use ONLY with approximation
                               language: "~", "approximately", "roughly",
                               "more than". Never sharpen it into an exact number.
  possible_metric_to_validate  An open question, not an achievement. NEVER
                               appears in a generated document in any form.

PROVENANCE (the "source" field)
-------------------------------
  verified_resume     Appears on Sofia's existing resume.
  candidate_provided  Stated directly by Sofia.
  supported_inference A reasonable reading of verified work that she approved.
  needs_validation    Unconfirmed. The generator MUST NOT use these.

The first three are usable. `needs_validation` is not, until Sofia promotes it.
The system may improve framing aggressively. It may never manufacture a number.

Never invent employers, dates, degrees, titles, direct reports, technologies,
certifications, revenue ownership, customers, promotions, funding events, or
projects. If a job requires something absent here, it is a gap — say so.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Identity. Email and phone come only from Sofia's existing resume/profile
# configuration and are never printed to logs or traces.
# ---------------------------------------------------------------------------

IDENTITY = {
    # All contact fields below are verified_resume: they appear on Sofia's
    # current resume and MAY appear in generated resumes and cover letters.
    # They must NEVER appear in debugging logs, eval output, API trace
    # summaries, or terminal diagnostics. Nothing in this project prints them.
    "name": "Sofia Tofigh",
    "location": "New York, NY",
    "linkedin": "linkedin.com/in/sofia-tofigh/",
    # Read from the environment, never committed — this repo is public.
    # Set CANDIDATE_EMAIL and CANDIDATE_PHONE in .env (gitignored).
    "email": os.environ.get("CANDIDATE_EMAIL", ""),
    "phone": os.environ.get("CANDIDATE_PHONE", ""),
    "portfolio": "",
    "contact_source": "verified_resume",
    "contact_logging_policy": "never log, trace, or print these fields",
    "experience_length": (
        "~4 years direct product management experience; ~5+ years total technical "
        "and product experience including Confluent. Never write '6 years of PM "
        "experience' and never stretch tenure to match a job description."
    ),
    "career_narrative": (
        "Technical consulting/engineering (Confluent) -> marketplace Product Manager "
        "(Axial) -> enterprise AI Product Manager (JPMorgan Chase)."
    ),
    "resume_summary_claims": {
        "source": "verified_resume",
        "claims": [
            "Over three years of product management experience",
            "End-to-end ownership across a fintech B2B SaaS marketplace serving the capital markets ecosystem",
            "Shipped full-stack product transformations that expanded deal-sourcing supply through partner API integrations, improved onboarding, and modernized mobile workflows for M&A teams",
            "Worked cross-functionally with data science, sales and UX design teams to interpret customer needs, translate user behavior into actionable insights, and refine machine-learning-driven recommendations",
        ],
        "conflict": (
            "The resume says 'over three years'; Sofia has since said ~4 years direct "
            "PM experience. Use Sofia's ~4 years figure — the resume line is the older "
            "of the two — but never write '6 years'."
        ),
    },
}


# ---------------------------------------------------------------------------
# Personal background. NOT professional evidence. Never appears in a resume by
# default. Informs voice and storytelling only, and only when genuinely relevant.
# ---------------------------------------------------------------------------

PERSONAL_BACKGROUND = {
    "origin": {
        "fact": "Grew up across New York and Tehran",
        "source": "candidate_provided",
        "use_when": (
            "international perspective, cross-cultural communication, global "
            "operations, or heterogeneous users genuinely matter, or the "
            "application asks for unusual background"
        ),
    },
    "languages": [
        {"language": "English", "level": "native/fluent", "source": "candidate_provided"},
        {"language": "Persian (Farsi)", "level": "fluent", "source": "candidate_provided"},
        {"language": "German", "level": "intermediate", "source": "candidate_provided"},
    ],
    "transition_story": {
        "fact": "Completed a coding bootcamp around 2020 while transitioning deeper into technology",
        "source": "candidate_provided",
        "use_when": "founder-type applications, grit questions, unconventional-path questions, 'tell us something not on your resume'",
    },
    "college_work": {
        "fact": "Worked and bartended during college",
        "source": "candidate_provided",
        "use_when": "same as transition_story",
    },
    "education_angle": {
        "fact": "Economics plus technical consulting plus product",
        "source": "supported_inference",
        "use_when": "explaining the combination of business intuition, systems thinking, quantitative reasoning and product judgement",
    },
}


# ---------------------------------------------------------------------------

EXPERIENCE_BANK = {
    "identity": IDENTITY,
    "personal_background": PERSONAL_BACKGROUND,

    "roles": [
        {
            "company": "JPMorgan Chase",
            "employment_source": "verified_resume",
            "title": "AI Product Manager, Senior Associate",
            "dates": "March 2026 - Present",
            "team": "Product Accelerator Garage",
            "location": "New York",
            "domain": "Financial services / private wealth / enterprise AI",
            "summary": (
                "Builds AI products for financial advisors in a highly regulated "
                "environment — the part of AI product work demos leave out: evaluation, "
                "reliability, compliance, user trust, legal constraints, rollout "
                "governance and model failure cases."
            ),
            "positioning": (
                "Three genuinely distinct AI stories, not one AI project. Pick the one "
                "that matches the role rather than blending them."
            ),
            "projects": [
                {
                    "name": "AI meeting summarization for financial advisors",
                    "story_id": "A",
                    "primary_strengths": [
                        "user discovery", "enterprise AI", "regulated deployment",
                        "Legal/Risk/Compliance", "workflow automation",
                    ],
                    "problem": (
                        "Financial advisors spend meaningful time documenting meetings "
                        "and turning conversations into compliant notes and summaries."
                    ),
                    "actions": [
                        "Led end-to-end product delivery of an AI meeting summarization product for financial advisors",
                        "Conducted and translated research from 6+ advisor interviews",
                        "Turned that research into 3 LLM-powered summarization templates",
                        "Worked through client-consent design and redaction requirements",
                        "Partnered with Legal, Risk and Compliance",
                        "Defined the rollout approach and participated in quality and evaluation design",
                    ],
                    "results": [
                        "Phased rollout targeting approximately 5,000 advisors",
                        "Expected user value of approximately 30 minutes of documentation time saved per meeting",
                    ],
                    "metrics": [
                        {"claim": "6+ advisor interviews conducted and translated into product requirements",
                         "type": "verified_metric", "source": "verified_resume"},
                        {"claim": "3 LLM-powered summarization templates",
                         "type": "verified_metric", "source": "verified_resume"},
                        {"claim": "phased rollout targeting ~5,000 advisors",
                         "type": "verified_metric", "source": "verified_resume"},
                        {"claim": "~30 minutes of documentation time saved per meeting (expected, not yet measured)",
                         "type": "approximate_supported_metric", "source": "verified_resume",
                         "caveat": "This is an expected value. Do not present it as a measured outcome."},
                    ],
                    "metric_variants": [],
                    "possible_metric_to_validate": [
                        {"claim": "Advisor adoption rate during the phased rollout", "source": "needs_validation"},
                        {"claim": "Measured (rather than expected) time saved per meeting post-launch", "source": "needs_validation"},
                        {"claim": "Number of engineers/designers on the team", "source": "needs_validation"},
                    ],
                    "framing": [
                        {"claim": "0->1 product ownership from discovery through delivery", "source": "supported_inference"},
                        {"claim": "AI product management in a regulated environment", "source": "supported_inference"},
                        {"claim": "Cross-functional leadership across Legal, Risk, Compliance and Engineering", "source": "supported_inference"},
                        {"claim": "Enterprise rollout at scale", "source": "supported_inference"},
                    ],
                    "skills": [
                        "AI product management", "LLMs", "user research", "regulated AI",
                        "compliance", "product discovery", "prompt/product design",
                        "enterprise rollout", "stakeholder management", "human workflow automation",
                    ],
                    "technologies": ["LLMs"],
                    "keywords": ["meeting summarization", "financial advisors", "compliance",
                                 "consent", "redaction", "enterprise AI", "rollout"],
                },
                {
                    "name": "LLM evaluation framework",
                    "story_id": "B",
                    "primary_strengths": [
                        "eval design", "defining correctness", "LLM-as-judge",
                        "rubric design", "prompt iteration", "quality thresholds",
                    ],
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
                    "results": ["Approximately 80% first-run pass rate"],
                    "metrics": [
                        {"claim": "36 evaluation scenarios", "type": "verified_metric", "source": "verified_resume"},
                        {"claim": "12 evaluation criteria including factual accuracy, compliance and tone",
                         "type": "verified_metric", "source": "verified_resume"},
                        {"claim": "~80% first-run pass rate", "type": "verified_metric",
                         "source": "verified_resume"},
                    ],
                    "metric_variants": [],
                    "possible_metric_to_validate": [
                        {"claim": "Pass-rate improvement from the first rubric version to current", "source": "needs_validation"},
                        {"claim": "Reduction in advisor-reported summary corrections", "source": "needs_validation"},
                    ],
                    "framing": [
                        {"claim": "The hard part was not improving a prompt — it was defining what 'correct' meant and turning subjective advisor expectations into repeatable evaluation criteria",
                         "source": "supported_inference"},
                        {"claim": "Ownership of AI quality and reliability", "source": "supported_inference"},
                    ],
                    "skills": ["evals", "LLM-as-judge", "AI quality", "model evaluation",
                               "prompt iteration", "rubric design", "failure analysis",
                               "regulated AI", "product metrics"],
                    "technologies": ["LLMs", "LLM-as-judge"],
                    "keywords": ["evaluation", "eval harness", "rubric", "hard-fail thresholds",
                                 "factual accuracy", "model quality"],
                },
                {
                    "name": "AI feedback classification (LLM + RAG)",
                    "story_id": "C",
                    "primary_strengths": [
                        "LLM + RAG", "replacing poor legacy ML", "operational automation",
                        "human-in-the-loop thinking", "measurable efficiency",
                    ],
                    "problem": (
                        "An existing machine-learning classification system ran at roughly "
                        "30-60% error rates and required significant manual triage of "
                        "approximately 400-500 advisor feedback submissions per month."
                    ),
                    "actions": [
                        "Reframed the problem rather than treating it as 'improve the model'",
                        "Established which categories actually mattered and what correct classification meant",
                        "Analyzed where the existing system failed and how humans reviewed errors",
                        "Replaced the approach with an LLM + RAG pipeline",
                        "Connected model performance to operational time saved",
                    ],
                    "results": ["Manual triage fell from approximately 50 hours/month to approximately 10 hours/month"],
                    "metrics": [
                        {"claim": "legacy ML classification tool had 30-60% error rates", "type": "verified_metric",
                         "source": "verified_resume"},
                        {"claim": "400-500 monthly advisor feedback submissions categorized",
                         "type": "verified_metric", "source": "verified_resume"},
                        {"claim": "manual triage reduced from ~50 hours/month to ~10 hours/month",
                         "type": "verified_metric", "source": "verified_resume"},
                        {"claim": "80% reduction in manual triage", "type": "verified_metric",
                         "source": "verified_resume",
                         "caveat": "Same measurement as the 50->10 hours figure. Use one or the other, not both."},
                    ],
                    "metric_variants": [],
                    "possible_metric_to_validate": [
                        {"claim": "Post-migration classification accuracy of the LLM + RAG pipeline", "source": "needs_validation"},
                        {"claim": "Dollar value of the operational hours recovered", "source": "needs_validation"},
                    ],
                    "framing": [
                        {"claim": "Recognized the problem was taxonomy and definition, not model quality", "source": "supported_inference"},
                        {"claim": "Human-in-the-loop system design", "source": "supported_inference"},
                        {"claim": "Translating technical work into operational business impact", "source": "supported_inference"},
                    ],
                    "skills": ["LLMs", "RAG", "classification", "workflow automation", "AI evaluation",
                               "operations", "human-in-the-loop", "ambiguity", "taxonomy design",
                               "measurable productivity"],
                    "technologies": ["LLMs", "RAG"],
                    "keywords": ["classification", "triage", "legacy ML replacement", "RAG", "operational leverage"],
                },
            ],
        },

        {
            "company": "Axial",
            "employment_source": "verified_resume",
            "title": "Product Manager",
            "dates": "October 2022 - November 2025",
            "title_history": [
                {"title": "Associate Product Manager", "dates": "October 2022 - December 2023",
                 "source": "candidate_provided"},
                {"title": "Product Manager", "dates": "January 2024 - November 2025",
                 "source": "candidate_provided"},
            ],
            "title_history_source": "candidate_provided — the resume supports the overall October 2022 - November 2025 span, not the split",
            "title_note": (
                "May be compressed to a single 'Product Manager, October 2022 - November 2025' "
                "entry when space requires. The promotion is real and must never be "
                "misstated if shown."
            ),
            "location": "New York",
            "domain": "B2B M&A marketplace / fintech / capital markets",
            "summary": (
                "Owned marketplace and workflow surfaces across a three-sided market of "
                "buyers, sellers and advisors/intermediaries. This is the role that "
                "demonstrates shipping speed and breadth."
            ),
            # Higher-level themes so Axial reads as a coherent story, not a feature list.
            "narrative_themes": [
                "multi-sided B2B marketplace",
                "end-to-end PM ownership",
                "marketplace liquidity and supply",
                "transaction funnel optimization",
                "workflow automation",
                "customer-facing shipping velocity",
                "API / platform work",
                "data-driven iteration",
                "early generative-AI product work",
            ],
            "projects": [
                {
                    "name": "Partner / supply API integrations (Transworld, Sunbelt)",
                    "problem": "Important deal supply arrived through partner workflows that relied on manual and legacy ingestion.",
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
                        {"claim": "API integrations became responsible for 60% of platform deal flow",
                         "type": "verified_metric", "source": "verified_resume",
                         "note": "The resume states 60%. Do not restate it as '60%+'."},
                        {"claim": "10+ hours/week of manual effort eliminated",
                         "type": "verified_metric", "source": "verified_resume"},
                        {"claim": "partner/supply integrations represented roughly one-third of closures in prior analysis",
                         "type": "approximate_supported_metric", "source": "candidate_provided"},
                    ],
                    "metric_variants": [],
                    "possible_metric_to_validate": [
                        {"claim": "Deal volume increase attributable to the integrations", "source": "needs_validation"},
                        {"claim": "Time-to-list improvement for partner-sourced deals", "source": "needs_validation"},
                    ],
                    "framing": [
                        {"claim": "Marketplace supply and liquidity ownership", "source": "supported_inference"},
                        {"claim": "Technical / API product management", "source": "supported_inference"},
                    ],
                    "skills": ["APIs", "integrations", "marketplace liquidity", "supply", "B2B SaaS",
                               "partner products", "technical PM", "workflow automation", "GTM coordination"],
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
                    "results": ["Substantial increase in mobile engagement at launch, with sustained lift afterwards"],
                    "metrics": [
                        {"claim": "led the initiative across 2 designers and 7 engineers",
                         "type": "verified_metric", "source": "candidate_provided"},
                    ],
                    # THREE SEPARATE MEASUREMENTS. Choose one. Never combine.
                    "metric_variants": [
                        {"claim": "lifted mobile engagement 127% at launch",
                         "type": "verified_metric", "source": "verified_resume",
                         "basis": "launch measurement",
                         "use_when": "the role rewards launch impact and visible step-changes"},
                        {"claim": "~15% sustained mobile usage lift",
                         "type": "approximate_supported_metric", "source": "candidate_provided",
                         "basis": "longer-term measurement",
                         "use_when": "the role rewards durable outcomes over launch spikes"},
                        {"claim": "~18% mobile buyer retention improvement",
                         "type": "approximate_supported_metric", "source": "verified_resume",
                         "basis": "retention measurement, as stated on the current resume",
                         "use_when": "the role is retention-oriented"},
                    ],
                    "metric_warning": (
                        "These are three separate measurements of the same project. Use exactly "
                        "ONE per bullet. Never combine them, never sum them, never present two "
                        "as if they measure the same thing."
                    ),
                    "possible_metric_to_validate": [
                        {"claim": "Which of the three definitions Sofia most wants to defend in interviews", "source": "needs_validation"},
                    ],
                    "framing": [
                        {"claim": "End-to-end PM ownership of a redesign", "source": "supported_inference"},
                        {"claim": "Cross-functional leadership across design and engineering", "source": "supported_inference"},
                    ],
                    "skills": ["mobile", "product redesign", "UX", "discovery", "analytics",
                               "cross-functional leadership", "marketplace", "engagement", "retention"],
                    "technologies": [],
                    "keywords": ["mobile", "responsive", "deal discovery", "navigation"],
                },
                {
                    "name": "NDA / CIM confidential document workflows",
                    "problem": "M&A marketplace participants need to share sensitive information only after the appropriate confidentiality steps.",
                    "actions": [
                        "Built NDA workflow and CIM/document sharing",
                        "Shipped multi-document upload and rule-based distribution",
                        "Automated the confidentiality workflow",
                        "Worked on watermarking and controlled document handling in related iterations",
                    ],
                    "results": ["7-day CIM sharing improved from approximately 16% to 37%"],
                    "metrics": [
                        {"claim": "7-day CIM sharing improved from ~16% to ~37%",
                         "type": "approximate_supported_metric", "source": "candidate_provided",
                         "note": "The strongest version for transaction workflow, funnel or conversion roles."},
                    ],
                    "metric_variants": [
                        {"claim": "improved document access rate by 16%, reducing turnaround time",
                         "type": "verified_metric", "source": "verified_resume",
                         "basis": "the resume's own measurement of the redesigned document workflow",
                         "use_when": "the default choice — it is the resume-backed figure"},
                    ],
                    "metric_warning": (
                        "The 16%->37% figure and the '~16% document access rate' figure may describe "
                        "different measurements. Never combine them and never present both."
                    ),
                    "possible_metric_to_validate": [
                        {"claim": "Whether the '~16% document access rate' is distinct from the 16%->37% figure or a restatement", "source": "needs_validation"},
                        {"claim": "Downstream deal-progression impact of faster CIM sharing", "source": "needs_validation"},
                    ],
                    "framing": [
                        {"claim": "Transaction workflow and funnel conversion ownership", "source": "supported_inference"},
                        {"claim": "Trust and permissioning design in a regulated-adjacent context", "source": "supported_inference"},
                    ],
                    "skills": ["workflow design", "fintech", "M&A", "documents", "permissioning",
                               "funnel conversion", "automation", "trust"],
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
                    "results": ["Improved reliability and maintainability; fewer support tickets"],
                    "metrics": [
                        {"claim": "15 email notification types migrated to Courier",
                         "type": "verified_metric", "source": "verified_resume"},
                        {"claim": "email-related support tickets reduced 44%",
                         "type": "verified_metric", "source": "verified_resume"},
                    ],
                    "metric_variants": [],
                    "possible_metric_to_validate": [
                        {"claim": "Deliverability or open-rate change after the migration", "source": "needs_validation"},
                    ],
                    "framing": [
                        {"claim": "Platform / infrastructure product ownership", "source": "supported_inference"},
                    ],
                    "skills": ["infrastructure product", "notifications", "platform", "migration",
                               "customer support reduction", "lifecycle engagement"],
                    "technologies": ["Courier"],
                    "keywords": ["notifications", "email", "migration", "infrastructure"],
                },
                {
                    "name": "AI-generated deal headlines",
                    "problem": "Marketplace listings were inconsistent and often unclear to buyers.",
                    "actions": [
                        "Launched AI-written/AI-assisted deal headlines in a customer-facing marketplace",
                        "Built QA and rubric-based audits covering factuality and salience",
                        "Designed guardrails with fallback to original content when model quality was uncertain",
                    ],
                    "results": ["Approximately +15% buyer engagement"],
                    "metrics": [
                        {"claim": "+15% buyer engagement", "type": "verified_metric",
                         "source": "verified_resume"},
                    ],
                    "metric_variants": [],
                    "possible_metric_to_validate": [
                        {"claim": "Share of listings where the AI headline was kept over the original", "source": "needs_validation"},
                        {"claim": "Rubric audit pass rate", "source": "needs_validation"},
                    ],
                    "framing": [
                        {"claim": "Shipped customer-facing generative AI before the JPM AI work", "source": "supported_inference"},
                        {"claim": "The product optimized for safe improvement rather than generation rate: when output quality was uncertain, preserve the original copy",
                         "source": "supported_inference"},
                        {"claim": "Evaluation and guardrail design", "source": "supported_inference"},
                    ],
                    "skills": ["generative AI", "evaluation", "guardrails", "marketplace",
                               "content generation", "buyer engagement"],
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
                        {"claim": "Number of shipped decisions attributable to the instrumentation", "source": "needs_validation"},
                    ],
                    "framing": [
                        {"claim": "Data-driven iteration as a working practice, not a one-off", "source": "supported_inference"},
                    ],
                    "skills": ["product analytics", "instrumentation", "roadmap prioritization"],
                    "technologies": ["GA4", "FullStory"],
                    "keywords": ["analytics", "instrumentation", "behavioral data"],
                },
                {
                    "name": "Down-funnel / transaction reporting",
                    "problem": "Down-funnel transaction activity was under-measured.",
                    "actions": ["Built down-funnel and transaction reporting"],
                    "results": ["Increased visibility into down-funnel and LOI activity"],
                    "metrics": [
                        {"claim": "down-funnel reporting activity ~+238% year over year",
                         "type": "approximate_supported_metric", "source": "candidate_provided",
                         "caveat": "Always keep the YoY timeframe attached."},
                        {"claim": "LOI-related activity ~+18% month over month",
                         "type": "approximate_supported_metric", "source": "candidate_provided",
                         "caveat": "Always keep the MoM timeframe attached."},
                    ],
                    "metric_warning": "Never restate either number without its original timeframe.",
                    "metric_variants": [],
                    "possible_metric_to_validate": [
                        {"claim": "Whether the +238% reflects reporting coverage or genuine activity growth", "source": "needs_validation"},
                    ],
                    "framing": [
                        {"claim": "Marketplace funnel and transaction analytics", "source": "supported_inference"},
                    ],
                    "skills": ["analytics", "B2B SaaS funnels", "transaction products"],
                    "technologies": [],
                    "keywords": ["down-funnel", "LOI", "transaction reporting"],
                },
            ],
            "resume_claims_without_detail": [
                {"claim": "improved onboarding", "source": "verified_resume",
                 "gap": "No project detail, actions or metrics supplied. Cannot be expanded beyond this phrase."},
                {"claim": "refined machine-learning-driven recommendations, working with data science",
                 "source": "verified_resume",
                 "gap": "No project detail, actions or metrics supplied. Cannot be expanded beyond this phrase."},
            ],
            "additional_themes": [
                "onboarding", "buyer/seller marketplace matching", "anonymized matching",
                "NDA e-sign / confidentiality workflows", "CIM watermarking", "buyside digest",
                "deal discovery", "transaction funnel", "customer feedback and behavior analysis",
            ],
        },

        {
            "company": "Confluent",
            "employment_source": "verified_resume",
            "title": "Associate Consulting Engineer",
            "dates": "June 2021 - October 2022",
            "location": "Remote",
            "domain": "Enterprise data infrastructure / event streaming",
            "summary": (
                "Technical consulting and engineering for Fortune 500 banking and "
                "insurance clients on Apache Kafka and event-streaming systems."
            ),
            "positioning": (
                "This role carries no metrics and none should be manufactured for it. "
                "Its value is qualitative: a genuine technical foundation, enterprise "
                "customers, Kafka and event-driven architecture, infrastructure, "
                "translating technical requirements into customer solutions, regulated "
                "banking and insurance exposure, and the ability to hold a conversation "
                "with deeply technical engineers and customers. "
                "Compress it on general PM resumes. Make it prominent — expanded, near "
                "the top — for technical PM, AI infrastructure, platform, forward-deployed "
                "and developer-product roles. It is the reason Sofia is not a "
                "non-technical PM."
            ),
            "projects": [
                {
                    "name": "Enterprise Kafka adoption and modernization",
                    "problem": (
                        "Fortune 500 banking and insurance organizations needed to modernize "
                        "toward real-time, event-driven data infrastructure."
                    ),
                    "actions": [
                        "Helped Fortune 500 banking and insurance clients design Kafka adoption strategies",
                        "Worked on multi-year modernization approaches",
                        "Addressed security and compliance requirements",
                        "Translated technical systems into enterprise implementation plans",
                    ],
                    "results": [
                        "Modernized event-streaming infrastructure to reduce data latency and meet security and compliance requirements",
                        "Clients equipped with multi-year Kafka adoption strategies",
                    ],
                    "results_source": "verified_resume",
                    "metrics": [],
                    "metric_variants": [],
                    "possible_metric_to_validate": [
                        {"claim": "Number of enterprise clients advised", "source": "needs_validation"},
                        {"claim": "Scale of any specific deployment (throughput, cluster size)", "source": "needs_validation"},
                        {"claim": "Named industries or deal sizes that can be disclosed", "source": "needs_validation"},
                    ],
                    "framing": [
                        {"claim": "Customer-embedded / forward-deployed technical work", "source": "supported_inference"},
                        {"claim": "Credible technical foundation in APIs, streaming data, infrastructure and enterprise architecture", "source": "supported_inference"},
                        {"claim": "Direct collaboration with deeply technical engineers and customers", "source": "supported_inference"},
                        {"claim": "Regulated-industry exposure in banking and insurance", "source": "supported_inference"},
                    ],
                    "skills": ["Apache Kafka", "event streaming", "distributed systems",
                               "enterprise architecture", "technical consulting",
                               "security and compliance", "client communication"],
                    "technologies": ["Apache Kafka", "event streaming", "distributed/real-time data systems"],
                    "keywords": ["Kafka", "event-driven", "real-time data", "enterprise",
                                 "modernization", "forward deployed"],
                },
            ],
        },
    ],

    # -----------------------------------------------------------------------
    # Personal / builder projects. Real work, no commercial scale.
    # -----------------------------------------------------------------------
    "personal_projects": [
        {
            "name": "AI Daily Brief",
            "type": "Personal / builder project",
            "label_rule": (
                "Always label as a personal project. Never imply it was a commercial "
                "product, had external users, or ran at production scale."
            ),
            "problem": "Wanted a personalized intelligence and content briefing workflow.",
            "actions": [
                "Built a pipeline covering podcast ingestion, transcription and retrieval",
                "Added web context and AI-generated summaries",
                "Added background functions and automation with human review",
            ],
            "results": ["A working personal briefing workflow"],
            "metrics": [],
            "possible_metric_to_validate": [
                {"claim": "How long it has run and whether it is used daily", "source": "needs_validation"},
            ],
            "use_as_evidence_of": [
                "hands-on experimentation", "RAG / retrieval", "pipelines",
                "LLM APIs", "workflow design", "building outside formal job responsibilities",
            ],
            "skills": ["RAG", "retrieval", "pipelines", "workflow design", "transcription"],
            "technologies": ["LLMs", "transcription", "retrieval"],
            "keywords": ["RAG", "ingestion", "summarization", "automation"],
        },
        {
            "name": "Job Opportunity Agent",
            "type": "Personal / builder project",
            "label_rule": (
                "Always label as a personal learning project. Never imply users, "
                "customers or production scale."
            ),
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
            "possible_metric_to_validate": [],
            "lessons": [
                "Evaluate both outcomes and trajectories",
                "Tool-use behavior can vary across runs while recommendations stay stable",
                "Poor fixtures create misleading eval results",
                "Profile and schema design strongly affect model reasoning",
            ],
            "use_as_evidence_of": [
                "agent architecture", "tool calling", "LLM APIs", "evals", "Python",
                "prompt iteration", "state representation", "cost and latency awareness",
                "building outside formal job responsibilities",
            ],
            "skills": ["agent architecture", "tool use", "eval design", "prompt iteration",
                       "state design", "Python"],
            "technologies": ["Python", "Anthropic API", "tool use", "web search"],
            "keywords": ["agent", "tool use", "evals", "APPLY/MAYBE/SKIP", "no framework"],
        },
    ],

    "education": [
        {
            "institution": "Columbia University",
            "credential": "BA, Economics",
            "dates": "September 2015 - May 2019",
            "source": "verified_resume",
            "notes": "",
        },
    ],

    "skills": {
        "product": ["Product management", "AI product management", "customer discovery",
                    "0->1 product development", "workflow design", "marketplace products",
                    "product analytics", "experimentation and measurement",
                    "stakeholder management", "cross-functional execution"],
        "ai": ["LLM-powered products", "RAG", "LLM evaluation", "LLM-as-judge",
               "prompt design and iteration", "rubric design", "AI failure-mode analysis",
               "human-in-the-loop systems", "guardrail design"],
        "technical": ["API integrations", "Apache Kafka", "event streaming", "SQL",
                      "analytics instrumentation", "enterprise technical architecture"],
        "tools": ["GA4", "FullStory", "Figma", "Courier", "Python", "Anthropic API"],
        "domains": ["B2B SaaS", "marketplaces", "fintech / capital markets", "M&A",
                    "enterprise AI", "private wealth"],
        "collaboration": ["Legal / Risk / Compliance", "Design", "Engineering",
                          "Data Science", "Sales", "Operations"],
        "on_resume": {
            "source": "verified_resume",
            "items": ["Apache Kafka", "API integrations", "Figma", "FullStory",
                      "Google Analytics", "LLM-powered products", "SQL",
                      "German", "Persian/Farsi"],
            "note": "Everything else in this skills section is candidate_provided.",
        },
        "positioning_caveat": (
            "Do not claim expert-level hands-on software engineering. Sofia is "
            "technically fluent with an engineering/consulting foundation, but "
            "positioning stays product-first unless the role specifically rewards "
            "technical implementation."
        ),
    },

    "interview_stories": [
        {"id": 1, "title": "Ambiguous AI / eval problem",
         "source": "JPMorgan Chase — LLM evaluation framework",
         "story": "The hard problem was not 'make the model better'. The first challenge was defining what correct meant.",
         "use_for": ["ambiguous product problems", "AI evals", "product quality", "0->1 AI",
                     "working without a playbook", "model reliability"]},
        {"id": 2, "title": "Broken system -> AI redesign",
         "source": "JPMorgan Chase — AI feedback classification",
         "story": "A legacy ML system ran at 30-60% errors. Reframed the problem, shipped an LLM + RAG pipeline, cut manual triage ~80%.",
         "use_for": ["replacing legacy ML", "measurable AI impact", "operational leverage", "human-in-the-loop systems"]},
        {"id": 3, "title": "User discovery plus regulated shipping",
         "source": "JPMorgan Chase — AI meeting summarization",
         "story": "6+ advisor interviews turned into 3 summarization templates, shipped through Legal, Risk and Compliance to ~5,000 advisors.",
         "use_for": ["customer discovery", "regulated environments", "Legal/Risk/Compliance", "AI trust", "enterprise rollout"]},
        {"id": 4, "title": "Shipping / marketplace impact",
         "source": "Axial — mobile product redesign",
         "story": "Led a responsive redesign across ~2 designers and ~7 engineers, with a large measured lift at launch.",
         "use_for": ["end-to-end PM ownership", "cross-functional leadership", "measurable launch results",
                     "customer experience", "mobile"]},
        {"id": 5, "title": "Technical / platform product",
         "source": "Axial — partner API integrations, plus Confluent",
         "story": "Shipped API integrations covering more than 60% of deal flow, on a foundation of Kafka and event-streaming consulting for Fortune 500 clients.",
         "use_for": ["technical PM", "APIs", "integrations", "platform", "infrastructure", "data"]},
        {"id": 6, "title": "Workflow / funnel optimization",
         "source": "Axial — NDA/CIM workflows",
         "story": "Rebuilt the confidentiality workflow and moved 7-day CIM sharing from ~16% to ~37%.",
         "use_for": ["funnels", "marketplace transaction workflows", "conversion", "user friction",
                     "operational automation"]},
        {"id": 7, "title": "Early generative-AI product",
         "source": "Axial — AI-generated deal headlines",
         "story": "Shipped customer-facing generative AI with rubric audits and a fallback to original copy when quality was uncertain — optimizing for safe improvement, not generation rate.",
         "use_for": ["GenAI", "guardrails", "evaluation", "product metrics", "model uncertainty"]},
        {"id": 8, "title": "Builder / agent story",
         "source": "Personal — Job Opportunity Agent and AI Daily Brief",
         "story": "Built an agent with tool use and an eval harness from scratch, without a framework, starting from a non-agentic baseline as a control.",
         "use_for": ["agents", "hands-on AI", "side projects", "building without a framework",
                     "learning quickly", "product and technical fluency"]},
    ],
}


# ---------------------------------------------------------------------------
# Deterministic helpers. Plain Python, no model judgement.
# ---------------------------------------------------------------------------

USABLE_SOURCES = {"verified_resume", "candidate_provided", "supported_inference"}
BLOCKED_SOURCE = "needs_validation"


def _walk_projects():
    for role in EXPERIENCE_BANK["roles"]:
        for project in role["projects"]:
            yield role["company"], project
    for project in EXPERIENCE_BANK["personal_projects"]:
        yield "Personal", project


def missing_fields() -> list:
    """TODO placeholders still left in the bank."""
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
    return not missing_fields()


def blocked_claims() -> list:
    """Every needs_validation claim. These must never reach a document."""
    out = []
    for company, project in _walk_projects():
        for entry in project.get("possible_metric_to_validate", []):
            out.append((company, project["name"], entry["claim"]))
    return out


def provenance_counts() -> dict:
    """Count every sourced claim in the bank by provenance label."""
    counts = {"verified_resume": 0, "candidate_provided": 0,
              "supported_inference": 0, "needs_validation": 0}

    def walk(node):
        if isinstance(node, dict):
            src = node.get("source")
            if isinstance(src, str) and src in counts:
                counts[src] += 1
            for key, value in node.items():
                if key != "source":
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(EXPERIENCE_BANK)
    return counts


def usable_metrics() -> list:
    """Every metric the generator is allowed to state, with its type and source."""
    out = []
    for company, project in _walk_projects():
        for entry in project.get("metrics", []) + project.get("metric_variants", []):
            if entry.get("source") in USABLE_SOURCES:
                out.append((company, project["name"], entry["type"], entry["source"], entry["claim"]))
    return out
