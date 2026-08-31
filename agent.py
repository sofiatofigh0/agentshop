"""
Creator Opportunity Triage - BASELINE.

This is the simple version on purpose: one system prompt, one user message, one
API call, one printed report. No tools, no loop, no framework. It exists so that
once the tool-using agent is built, there is something honest to compare it to.
"""

import os

import anthropic
from dotenv import load_dotenv

from sample_opportunities import SAMPLES

# Reads the .env file next to this script and copies its values into the
# environment. After this, ANTHROPIC_API_KEY and ANTHROPIC_MODEL are readable
# with os.environ, and the SDK can find the key on its own.
load_dotenv()

MODEL = os.environ.get("ANTHROPIC_MODEL")

# The system prompt is the standing instruction: who the model is and what shape
# its answer must take. It is the same on every request and says nothing about
# any particular opportunity - that keeps the job description separate from the
# data, so changing the prompt is how you tune behavior for every input at once.
SYSTEM_PROMPT = """You are a Creator Opportunity Triage assistant.

A creator will paste in the raw text of a brand opportunity - a campaign
invitation, a gifting offer, or a brand DM. Read it the way an experienced
talent manager would and help the creator decide what to do about it.

Reply with exactly these fields, each on its own line, in this order, with no
extra commentary before or after:

Summary:
Brand:
Compensation:
Deliverables:
Deadline:
Missing Information:
Potential Concerns:
Recommendation:
Reasoning:
Next Action:

Rules:
- Summary is one sentence.
- Report only what the message actually says. If a field is not stated, write
  "Not specified" rather than guessing or inferring a plausible value.
- Missing Information is what the creator would need before committing - unstated
  pay, vague deliverables, no timeline, undefined usage rights, and so on.
- Potential Concerns is for terms that are stated but unfavorable or risky.
- Recommendation must be exactly one of: ACCEPT, INVESTIGATE, DECLINE
- Reasoning is two or three sentences explaining that recommendation.
- Next Action is the single most useful thing the creator should do next.
"""


def triage(opportunity_text: str) -> str:
    """Send one opportunity to the model and return the report as text."""
    client = anthropic.Anthropic()  # picks up ANTHROPIC_API_KEY from the environment

    # The user message is the data: just the pasted opportunity, nothing else.
    # The instructions live in the system prompt, so this stays swappable.
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": opportunity_text}],
    )

    # The call returns a Message object. The interesting part is response.content,
    # which is a *list* of content blocks rather than a single string - a block
    # has a .type, and only blocks of type "text" carry readable output. Joining
    # the text blocks is what turns the response back into a printable report.
    # (response.usage has the token counts, and response.stop_reason says why the
    # model stopped, if you want to look at those later.)
    return "\n".join(block.text for block in response.content if block.type == "text")


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in.")
    if not MODEL:
        raise SystemExit("ANTHROPIC_MODEL is not set. Copy .env.example to .env and fill it in.")

    opportunity = SAMPLES[0]  # change the index to try the other samples
    print(triage(opportunity))
