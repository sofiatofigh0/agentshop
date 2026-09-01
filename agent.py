"""
Job Opportunity Agent — orchestration and the agent loop.

Run it with:  python agent.py

Paste a job description, and the agent evaluates it against your profile,
researches the company if that could change the answer, and returns
APPLY / MAYBE / SKIP. If the role is worth pursuing it hands off to
application_generator.py for the resume, cover letter and strategy.

The split this file exists to demonstrate:

  THE MODEL DECIDES   whether to search, what to search for, whether one result
                      was enough, which uncertainties matter, which experience
                      is relevant.

  PYTHON DECIDES      how many searches are allowed, when the loop stops, where
                      files are written, whether unsupported claims survive,
                      and how credentials are handled.

Neither can overrule the other. That boundary is the architecture.
"""

import json
import os
import sys

import anthropic
from dotenv import load_dotenv

from candidate_profile import CANDIDATE_PROFILE
from application_generator import generate_application_package
from tools import TOOLS, TOOL_FUNCTIONS

# Reads the .env file next to this script and copies its values into the
# environment. After this, ANTHROPIC_API_KEY and ANTHROPIC_MODEL are readable
# with os.environ, and the SDK can find the key on its own.
load_dotenv()

MODEL = os.environ.get("ANTHROPIC_MODEL")

# A hard ceiling we enforce in Python. The model cannot talk its way past this.
MAX_TOOL_CALLS = 3

# The system prompt is the standing instruction: who the model is and what shape
# its answer must take. It is the same on every request and says nothing about
# any particular job - that keeps the job description separate from the data, so
# editing the prompt is how you tune behavior for every input at once.
BASE_PROMPT = """You are a Job Opportunity assistant.

A candidate will paste in the text of a job description. Read it the way an
experienced recruiter would and help them decide whether the role is worth
pursuing — for this candidate specifically, whose profile is at the end of these
instructions.

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
- Strongest Fit Areas is where this candidate's profile lines up with what the
  role rewards. Main Gaps or Risks is where the role conflicts with their
  profile, plus anything stated that is unfavorable or a warning sign.
- Use the search_web tool only when a search could materially change the
  recommendation for this candidate. Missing information is NOT by itself a
  reason to search: if the gap is something only the employer can answer — their
  comp band, their team structure, who the founders are — record it under
  Missing Information and move on.
- Recommendation must be exactly one of: APPLY, MAYBE, SKIP
- Recommendation is about fit between this candidate and this role, not how
  attractive the role is in the abstract.
- Weigh the profile's two lists differently. Violating a hard_constraint can
  justify SKIP on its own. Violating a strong_preference lowers fit but never
  forces SKIP by itself; several strong_preference violations together can.
  Otherwise weigh the whole opportunity holistically rather than scanning for
  disqualifiers.
- Reasoning is two or three sentences explaining that recommendation.
- What to Emphasize if Applying is the one or two things from this candidate's
  own background that this posting most clearly rewards, phrased as advice.
"""

# The profile is standing context, so it belongs in the system prompt next to
# the instructions rather than being pasted into each job description. Same on
# every call; only the user message changes.
SYSTEM_PROMPT = (
    BASE_PROMPT
    + "\n\nCANDIDATE PROFILE:\n"
    + json.dumps(CANDIDATE_PROFILE, indent=2)
)


def evaluate(job_description: str) -> dict:
    """Run the agent loop on one job description.

    Returns the final response plus a little metadata about how the run went:
    how many searches it took and what it cost. Token counts are summed across
    every call the loop made, not just the last one. They do not include the
    nested API calls that search_web itself makes.
    """
    client = anthropic.Anthropic()

    # The conversation. Unlike the baseline, this grows: every tool request and
    # every tool result gets appended, and the whole history is resent each turn.
    # That history is the agent's only memory.
    messages = [{"role": "user", "content": job_description}]
    research_notes = []  # kept so the generation stage can reuse what was found
    searches_used = 0
    search_queries = []
    input_tokens = 0
    output_tokens = 0

    # At most MAX_TOOL_CALLS rounds of searching, one round to tell the model its
    # budget is gone, and one round for it to write the final answer. Bounding
    # the loop in Python is what makes "cannot search forever" a guarantee
    # rather than a request.
    for _ in range(MAX_TOOL_CALLS + 2):
        response = client.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,  # the schemas from tools.py, sent on every turn
            messages=messages,
        )
        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens

        # HOW CLAUDE ASKS FOR A TOOL: it does not call anything itself. It ends
        # its turn with stop_reason == "tool_use" and puts one or more tool_use
        # blocks in its content, each with a name, an id, and the arguments it
        # chose. Any other stop_reason means it is done and this is the answer.
        if response.stop_reason != "tool_use":
            return {
                "response": response,
                "search_count": searches_used,
                "search_queries": search_queries,
                "research": "\n\n".join(research_notes),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }

        # The assistant turn must go into the history verbatim, tool_use blocks
        # and all, or the next request will not line up with the tool results.
        messages.append({"role": "assistant", "content": response.content})

        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            # HOW PYTHON EXECUTES THE TOOL: we look the name up in the dispatch
            # dict and call it with the arguments Claude chose. This is ordinary
            # Python — the model has no access to the machine, it can only ask.
            if searches_used < MAX_TOOL_CALLS:
                print(f'  [tool call {searches_used + 1}] search_web(query="{block.input["query"]}")')
                output = TOOL_FUNCTIONS[block.name](**block.input)
                search_queries.append(block.input["query"])
                research_notes.append(output)
                searches_used += 1
            else:
                print("  [budget spent] refusing further searches")
                output = "Search budget exhausted. Answer using what you already have."

            # HOW THE RESULT GETS BACK: as a user turn containing a tool_result
            # block whose tool_use_id matches the request. Every tool_use needs
            # exactly one matching tool_result, in one single user message.
            results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": output}
            )

        messages.append({"role": "user", "content": results})

    # Only reachable if the model asked for tools every single round.
    return {
        "response": response,
        "search_count": searches_used,
        "search_queries": search_queries,
        "research": "\n\n".join(research_notes),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def report_text(response: anthropic.types.Message) -> str:
    """Join the readable text blocks of a response into one printable report."""
    return "\n".join(block.text for block in response.content if block.type == "text")


def parse_field(report: str, field: str) -> str:
    """Pull one labelled field out of the report. Empty string if absent."""
    for line in report.splitlines():
        if line.strip().startswith(f"{field}:"):
            return line.split(":", 1)[1].strip()
    return ""


def parse_recommendation(report: str) -> str:
    """Pull APPLY / MAYBE / SKIP out of the report."""
    line = parse_field(report, "Recommendation")
    for verdict in ("APPLY", "MAYBE", "SKIP"):
        if verdict in line:
            return verdict
    return "UNPARSED"


def read_job_description() -> str:
    """Read a pasted, multi-line job description from the terminal.

    Terminated by a line containing only END, or by end-of-input (ctrl-D), so
    the script also works when a file is piped in.
    """
    print("Paste job description below.")
    print("When finished, type END on a new line.\n")
    lines = []
    for line in sys.stdin:
        if line.strip() == "END":
            break
        lines.append(line)
    return "".join(lines).strip()


def main() -> None:
    """The interactive runtime. Evals bypass this and call evaluate() directly."""
    # Python owns credential handling — checked once, before anything costs money.
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in.")
    if not MODEL:
        raise SystemExit("ANTHROPIC_MODEL is not set. Copy .env.example to .env and fill it in.")

    job_description = read_job_description()
    if not job_description:
        raise SystemExit("No job description given — nothing to evaluate.")

    print("\nEvaluating...\n")
    result = evaluate(job_description)
    report = report_text(result["response"])

    recommendation = parse_recommendation(report)
    reasoning = parse_field(report, "Reasoning")

    if recommendation == "UNPARSED":
        # Malformed response: show the whole thing rather than guessing.
        print("Could not find a recommendation in the response. Full output:\n")
        print(report)
        return

    print(f"Recommendation: {recommendation}")
    print(f"{reasoning}\n")

    # Python owns this branch, not the model.
    generate = recommendation in ("APPLY", "MAYBE")
    if not generate:
        answer = input("This looks like a SKIP. Generate application materials anyway? [y/N] ")
        generate = answer.strip().lower().startswith("y")

    package = None
    if generate:
        print("\nGenerating application package...")
        try:
            package = generate_application_package(
                job_description, recommendation, reasoning, result["research"]
            )
        except RuntimeError as exc:
            print(f"\nCould not generate: {exc}")

    if package:
        print("\nWrote:")
        for path in package["files"].values():
            print(f"  {path}")

    # --- trace ------------------------------------------------------------
    # Deliberately does not echo the candidate profile or the job description.
    print("\n--- trace ---")
    print(f"Recommendation:            {recommendation}")
    print(f"Searches used:             {result['search_count']}")
    for query in result["search_queries"]:
        print(f"  query:                   {query}")
    print(f"Main agent input tokens:   {result['input_tokens']}")
    print(f"Main agent output tokens:  {result['output_tokens']}")
    print(f"Generation calls:          {package['generation_calls'] if package else 0}")
    if package:
        print(f"Generation input tokens:   {package['input_tokens']}")
        print(f"Generation output tokens:  {package['output_tokens']}")


if __name__ == "__main__":
    main()
