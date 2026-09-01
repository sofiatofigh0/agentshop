"""
Tool definitions.

One tool: search_web. Two halves that must stay in sync — the schema Claude
sees, and the Python function we actually run.
"""

import os

import anthropic

# This is the ONLY thing Claude knows about the tool. It never sees the Python
# below. So the description is the real interface: it is what Claude reads when
# deciding whether calling this is worth a turn, and the input_schema is the
# contract it must fill in. Vague description, bad tool use.
TOOLS = [
    {
        "name": "search_web",
        "description": (
            "Search the web for current external information about a company, role, or "
            "job opportunity. Use this when the job description leaves out something you "
            "need in order to judge the opportunity — who the company is, whether it is "
            "credible, how it is funded, what the role typically pays."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for, phrased as a search query.",
                }
            },
            "required": ["query"],
        },
    }
]


def search_web(query: str) -> str:
    """Run one web search and return what it found as plain text.

    The search itself is done by asking the API with its built-in web_search
    tool switched on. That keeps setup to zero — no second provider, no second
    API key, no extra package — at the cost of one nested API call per search.
    To swap in a dedicated search provider later (Tavily, Brave, SerpAPI), only
    this function body changes; the schema above and the loop in agent.py stay
    exactly as they are.
    """
    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model=os.environ["ANTHROPIC_MODEL"],
            max_tokens=4000,
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 3}],
            messages=[
                {
                    "role": "user",
                    "content": f"Search the web and summarize what you find about: {query}",
                }
            ],
        )
        found = "\n".join(b.text for b in response.content if b.type == "text")
        return found or "The search returned nothing useful."
    except Exception as exc:  # a failed tool must not crash the agent loop
        return f"The search failed: {exc}"


# Lets the loop dispatch by name without a growing if/elif chain.
TOOL_FUNCTIONS = {"search_web": search_web}
