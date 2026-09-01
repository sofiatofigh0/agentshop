"""
The agent loop.

PLACEHOLDER — nothing is implemented yet.

Eventual purpose: take a pasted job description and drive the agent loop until
the model stops asking for tools, then print the verdict.

The plan for V1:

    1. Build a system prompt describing the evaluation job.
    2. Start the conversation with the job description as the first user message.
    3. Call the Messages API with the tool schemas from tools.py.
    4. Look at stop_reason:
         "tool_use"  -> run each requested tool, append the assistant turn and a
                        user turn of tool_result blocks, then go back to step 3
         anything else -> this reply is the final answer, so stop
    5. Print it.

Step 4 is the whole lesson: we never decide how many lookups happen. The model
does, by either asking for another tool or not.

The final answer should contain:

    - Recommendation: APPLY | MAYBE | SKIP
    - Why
    - Strongest fit areas
    - Gaps and risks
    - What to emphasize when applying
"""

# TODO: load ANTHROPIC_API_KEY and ANTHROPIC_MODEL from .env
# TODO: SYSTEM_PROMPT = "..."
# TODO: def run_agent(job_description: str) -> str   # the loop
# TODO: if __name__ == "__main__": read a job description and print the verdict
