"""
The agent loop.

PLACEHOLDER — nothing is implemented yet.

The plan for V1:

    1. Build a system prompt describing the triage job.
    2. Send the creator's pasted opportunity text as the first user message.
    3. Call the Messages API with the tool schemas from tools.py.
    4. If the response contains tool_use blocks:
           - run the matching Python function
           - append the assistant turn, then a user turn of tool_result blocks
           - loop back to step 3
       Otherwise: we have the final answer, so stop.
    5. Print the triage report.

The report should contain:

    1.  One-sentence summary
    2.  Brand
    3.  Compensation (if mentioned)
    4.  Deliverables
    5.  Deadline
    6.  Important missing information
    7.  Potential concerns / red flags
    8.  Recommendation: ACCEPT | INVESTIGATE | DECLINE
    9.  Reasoning behind the recommendation
    10. Best next action for the creator
"""

# TODO: load ANTHROPIC_API_KEY from .env
# TODO: SYSTEM_PROMPT = "..."
# TODO: def run_agent(opportunity_text: str) -> str
# TODO: if __name__ == "__main__": run against a sample from sample_opportunities.py
