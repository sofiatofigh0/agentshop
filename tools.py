"""
Tool definitions.

PLACEHOLDER — nothing is implemented yet.

Eventual purpose: give the agent a way to find out what the job description
doesn't say, so it can stop guessing about salary bands, company reputation, or
an unfamiliar tech stack.

Each tool is two halves that must stay in sync:

    TOOLS     a list of JSON schemas the model sees (name, description,
              input_schema). This is the only thing the model knows about a
              tool, so the description is the real interface — it is what the
              model reads when deciding whether this tool is worth calling.

    a Python  the code we actually run when the model asks for that tool, plus a
    function  dict mapping tool name -> function so the loop can dispatch
              without a growing if/elif chain.

Candidate tools for V1 (start with one — the loop is the same shape for ten):

    search_web(query)              general lookup: company, role, reputation
    lookup_salary_range(role,      typical comp for this title and location
                        location)
"""

# TODO: TOOLS = [ ... ]
# TODO: def search_web(query: str) -> str
# TODO: TOOL_FUNCTIONS = {"search_web": search_web, ...}
