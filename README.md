# Job Opportunity Agent

A small tool-using agent that decides whether a job is worth pursuing. You paste
in a job description; the agent reads it, pulls out the facts that matter —
company, role, location, compensation, requirements, responsibilities — and then
asks itself whether that is actually enough to judge the opportunity. Often it
isn't: the posting says "competitive salary", or names a company you've never
heard of. At that point the agent can reach for a research tool, look something
up, read the result, and decide whether it needs another lookup before it commits
to an answer.

It ends with one recommendation — **APPLY**, **MAYBE**, or **SKIP** — plus the
reasoning behind it, the strongest fit areas, the gaps and risks worth knowing
about, and what the candidate should emphasize if they do apply.

This is a learning project, so the point is the mechanics rather than the output.
Everything is plain Python and the Anthropic SDK — no LangChain, no CrewAI, no
agent framework — so that every part of the loop is visible and editable. Two
small files hold the whole system.

## The loop

The thing that makes this an agent rather than a prompt is that control flow is
decided by the model, not by us:

```
send the job description + tool definitions
  -> model replies
       -> did it ask for a tool?
            yes: run the tool, append the result, send again  ──┐
            no:  that reply is the final answer, stop           │
                                                    ◄───────────┘
```

We own the loop; the model owns the decisions inside it. How many lookups happen,
and whether any happen at all, is not something the code decides in advance.

## Structure

```
agent.py          the loop: messages, tool dispatch, final answer
tools.py          tool schemas + the Python functions behind them
requirements.txt  anthropic, python-dotenv
.env.example      copy to .env and add your API key
```

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then fill in ANTHROPIC_API_KEY and ANTHROPIC_MODEL
python agent.py
```

## Status

Scaffold only — `agent.py` and `tools.py` are placeholders. Nothing is
implemented yet.
