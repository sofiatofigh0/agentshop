"""
Tool definitions.

PLACEHOLDER — nothing is implemented yet.

Each tool is two halves that must stay in sync:

    TOOLS     a list of JSON schemas the model sees (name, description,
              input_schema). This is the only thing the model knows about a
              tool, so the description is the real interface.

    a Python  the actual code we run when the model asks for that tool, plus a
    function  dict mapping tool name -> function so the loop in agent.py can
              dispatch without a big if/elif chain.

Candidate tools for V1 (start with one or two, not all of them):

    lookup_brand(brand_name)          what do we know about this brand?
    check_rate_benchmark(deliverable) is the offered pay in a normal range?
    parse_deadline(text)              turn "end of next week" into a real date
    flag_contract_terms(text)         scan for exclusivity, usage rights, perpetuity
"""

# TODO: TOOLS = [ ... ]
# TODO: def lookup_brand(brand_name: str) -> str
# TODO: TOOL_FUNCTIONS = {"lookup_brand": lookup_brand, ...}
