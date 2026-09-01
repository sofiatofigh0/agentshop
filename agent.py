"""
Job Opportunity Agent - BASELINE.

This is the simple version on purpose: one system prompt, one user message, one
API call, one printed report. No tools, no loop, no framework. It exists so that
once the tool-using agent is built, there is something honest to compare it to.
"""

import os

import anthropic
from dotenv import load_dotenv

from sample_jobs import SAMPLES

# Reads the .env file next to this script and copies its values into the
# environment. After this, ANTHROPIC_API_KEY and ANTHROPIC_MODEL are readable
# with os.environ, and the SDK can find the key on its own.
load_dotenv()

MODEL = os.environ.get("ANTHROPIC_MODEL")

# The system prompt is the standing instruction: who the model is and what shape
# its answer must take. It is the same on every request and says nothing about
# any particular job - that keeps the job description separate from the data, so
# editing the prompt is how you tune behavior for every input at once.
SYSTEM_PROMPT = """You are a Job Opportunity assistant.

A candidate will paste in the text of a job description. Read it the way an
experienced recruiter would and help them decide whether the role is worth
pursuing.

Reply with exactly these fields, each on its own line, in this order, with no
extra commentary before or after:

Company:
Role:
Location:
Compensation:
Key Responsibilities:
Key Requirements:
Missing Information:
Strongest Fit Areas:
Main Gaps or Risks:
Recommendation:
Reasoning:
What to Emphasize if Applying:

Rules:
- Report only what the posting actually says. If a field is not stated, write
  "Not specified" rather than guessing or inferring a plausible value.
- Missing Information is what a candidate would need before applying - unstated
  pay, vague scope, no team size, unclear seniority, and so on.
- You are not given the candidate's resume, so judge fit from the posting alone:
  Strongest Fit Areas is what the role offers and the kind of background it
  rewards; Main Gaps or Risks is what is stated but unfavorable, contradictory,
  or a warning sign.
- Recommendation must be exactly one of: APPLY, MAYBE, SKIP
- Reasoning is two or three sentences explaining that recommendation.
- What to Emphasize if Applying is the one or two things this posting most
  clearly rewards, phrased as advice.
"""


def evaluate(job_description: str) -> anthropic.types.Message:
    """Send one job description to the model and return the whole response."""
    client = anthropic.Anthropic()  # picks up ANTHROPIC_API_KEY from the environment

    # The user message is the data: just the pasted job description, nothing
    # else. The instructions live in the system prompt, so this stays swappable.
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": job_description}],
    )

    # The call returns a Message object. The interesting part is response.content,
    # which is a *list* of content blocks rather than a single string - a block
    # has a .type, and only blocks of type "text" carry readable output. Joining
    # the text blocks is what turns the response back into a printable report.
    # We return the whole Message rather than just the text, because the caller
    # also wants response.usage (the token counts) and response.stop_reason (why
    # the model stopped - that one becomes important once tools are added,
    # because "tool_use" is the signal to run a tool and call again).
    return response


def report_text(response: anthropic.types.Message) -> str:
    """Join the readable text blocks of a response into one printable report."""
    return "\n".join(block.text for block in response.content if block.type == "text")


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in.")
    if not MODEL:
        raise SystemExit("ANTHROPIC_MODEL is not set. Copy .env.example to .env and fill it in.")

    # One independent API call per sample. Nothing is shared between them - no
    # conversation history, no tools, no second pass. Three separate baselines.
    for name, job in SAMPLES.items():
        print("=" * 78)
        print(name)
        print("=" * 78)

        response = evaluate(job)

        print(report_text(response))
        print()
        print(f"input tokens:  {response.usage.input_tokens}")
        print(f"output tokens: {response.usage.output_tokens}")
        print(f"stop_reason:   {response.stop_reason}")
        print()
