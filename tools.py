"""
Tool definitions.

One tool: search_web. Two halves that must stay in sync — the schema Claude
sees, and the Python function we actually run.
"""

import threading

import anthropic

from models import Spend, request_options, web_search_tool, worker_model

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

# One query rarely needs more than two searches; three was the single most
# expensive default in the project, because each search's results are re-sent
# as input on the next one inside the same call.
MAX_SEARCHES_PER_QUERY = 2

# The summary is what the agent reads back into its own context, so its length
# is paid for twice: once to write it and again on every later turn of the
# loop. Facts with sources, no advice, and a hard stop at 200 words.
SEARCH_PROMPT = """Search the web for: {query}

Then report what you found in under 200 words: plain facts, most relevant
first, each with its source domain in brackets. No preamble, no advice, no
speculation about what it means for a candidate. If nothing relevant turns up,
say so in one line."""


# The agent loop runs the tool on its own thread, and the web UI can have more
# than one run going, so the usage of the nested calls is collected per thread
# and handed back to whichever evaluate() started it.
_local = threading.local()


def begin_usage() -> None:
    """Start collecting the cost of searches made on this thread."""
    _local.spend = Spend()


def collect_usage() -> Spend:
    """What the searches on this thread cost since begin_usage()."""
    spend = getattr(_local, "spend", None)
    _local.spend = None
    return spend or Spend()


def search_web(query: str) -> str:
    """Run one web search and return what it found as plain text.

    The search itself is done by asking the API with its built-in web_search
    tool switched on. That keeps setup to zero — no second provider, no second
    API key, no extra package — at the cost of one nested API call per search.
    That nested call is extraction, not judgement, so it runs on the worker
    model at low effort with a tight output shape. To swap in a dedicated
    search provider later (Tavily, Brave, SerpAPI), only this function body
    changes; the schema above and the loop in agent.py stay exactly as they are.
    """
    model = worker_model()
    client = anthropic.Anthropic()
    try:
        response = client.messages.create(
            model=model,
            max_tokens=1500,
            tools=[web_search_tool(model, MAX_SEARCHES_PER_QUERY)],
            messages=[{"role": "user", "content": SEARCH_PROMPT.format(query=query)}],
            **request_options("search", model),
        )
        spend = getattr(_local, "spend", None)
        if spend is not None:
            spend.add(model, response.usage)
        found = "\n".join(b.text for b in response.content if b.type == "text").strip()
        return found or "The search returned nothing useful."
    except Exception as exc:  # a failed tool must not crash the agent loop
        return f"The search failed: {exc}"


# Lets the loop dispatch by name without a growing if/elif chain.
TOOL_FUNCTIONS = {"search_web": search_web}
