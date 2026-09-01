"""
Fixture job descriptions to test the agent against.

Three examples, one per recommendation path:
    STRONG_FIT_AI_PRODUCT  well-specified, well-paid, clearly scoped
    AMBIGUOUS_ROLE         plausible, but too vague to judge as written
    POOR_FIT_RED_FLAGS     specific, and what it specifies is the problem
"""

STRONG_FIT_AI_PRODUCT = """
Senior Product Manager, AI Platform
Meridian Labs - San Francisco, CA (hybrid, 3 days onsite)

About the role

Meridian Labs builds developer infrastructure for teams shipping LLM-powered
features. Our AI Platform team owns the evaluation, observability, and prompt
management surfaces that ~4,000 engineering teams use in production. We're
hiring a senior PM to own the evaluation product end to end.

What you'll do

- Own the roadmap for our evaluation suite: offline eval runs, regression
  detection, and human review workflows
- Work directly with a team of 7 engineers and 1 designer; partner with our
  research team on what "quality" should mean for generative outputs
- Talk to customers weekly. We expect PMs here to write the problem statement
  before anyone writes a spec.
- Define success metrics and own them publicly in a monthly business review

What we're looking for

- 5+ years in product management, at least 2 of them on developer or
  infrastructure products
- Hands-on familiarity with LLM application development - you don't need to
  ship models, but you should have built something with an API and have
  opinions about why it broke
- Demonstrated experience taking an ambiguous 0-to-1 area to GA
- Strong written communication; we run on documents, not slide decks

Compensation and benefits

- Base salary: $185,000 - $230,000, depending on level and location
- Equity: 0.05% - 0.12%, 4-year vest with a 1-year cliff
- Full medical, dental, and vision; $3,000 annual learning budget
- 20 days PTO plus company holidays

Our process: a recruiter screen, a hiring manager conversation, a written
product exercise (we pay for your time on take-homes), and a final loop of four
interviews. We aim to go from first call to decision in three weeks.
"""

AMBIGUOUS_ROLE = """
Product Lead (AI)
Stealth startup - Remote-ish

We're a well-funded early stage team working on something big in the AI space.
We can't say too much publicly yet, but we're backed by top-tier investors and
moving fast.

We're looking for someone who can wear a lot of hats. You'll be involved in
product, obviously, but also a bit of everything else - GTM, design input,
maybe some hands-on work depending on your background. The right person is
scrappy and doesn't need a lot of direction.

You should be comfortable with ambiguity and excited to build from scratch.
Prior startup experience strongly preferred. AI/ML familiarity is a plus.

Location is flexible for the right candidate, though we do like to get the team
together regularly.

Compensation is competitive and includes meaningful equity. Happy to discuss
specifics once we connect.

Interested? Send us a note about something you've built.
"""

POOR_FIT_RED_FLAGS = """
Founding AI Product Engineer
Vantiq AI - Austin, TX (onsite, 6 days/week)

We are a pre-seed startup building the future of enterprise AI, and we are
looking for a founding team member who will treat this like their own company.
This is not a 9-to-5. We work Monday through Saturday in office because we
believe great products come from being in the room together. If you need
work-life balance this is not the role for you - we're a family here and we
expect that level of commitment.

Responsibilities

- Own product strategy, design, and roadmap
- Write and ship production backend and frontend code
- Fine-tune and deploy our models
- Run sales calls and close our first enterprise customers
- Handle customer support and onboarding
- Manage our hiring pipeline as we grow

Requirements

- 15+ years of machine learning experience
- Expert-level knowledge of modern LLM tooling and agent frameworks
- Prior founding experience with a successful exit strongly preferred
- Must be available on Slack outside working hours, including weekends

Compensation

Equity only for the first 6 months (0.25% - 0.5%, subject to board approval),
transitioning to a market-rate salary once we close our seed round, which we
expect to happen in Q1. You'll be getting in on the ground floor of something
enormous.

Process: after an initial call, finalists complete an unpaid two-week trial
project building a working prototype so we can see how you operate. Relocation
to Austin is required and is at the candidate's own expense.
"""

SAMPLES = [STRONG_FIT_AI_PRODUCT, AMBIGUOUS_ROLE, POOR_FIT_RED_FLAGS]
