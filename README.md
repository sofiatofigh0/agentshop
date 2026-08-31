# Creator Opportunity Triage Agent

A tiny AI agent that helps creators triage inbound brand opportunities. A creator
pastes in the raw text of a campaign invitation, gifting offer, or brand DM, and the
agent reads it the way an experienced talent manager would. It returns a one-sentence
summary, the brand, the compensation, the deliverables, and the deadline — pulling out
only what the message actually says. Just as importantly, it names what is *missing*:
unstated usage rights, vague pay, no timeline, or an exclusivity clause hiding in the
fine print. It then flags potential concerns and gives a recommendation of **ACCEPT**,
**INVESTIGATE**, or **DECLINE**, along with the reasoning behind it and the single best
next action the creator should take.

This is a learning project, so the architecture is deliberately transparent: plain
Python, the Anthropic SDK, and no agent framework. V1 is a real tool-using agent loop —
the model decides which tools to call, we run them, we feed the results back, and we
repeat until it produces a final answer. Everything lives in four small files so you can
read the entire system in one sitting.

## Structure

```
agent.py                 the agent loop: messages, tool dispatch, final answer
tools.py                 tool schemas + the Python functions behind them
sample_opportunities.py  fixture brand messages to test against
requirements.txt         anthropic, python-dotenv
.env.example             copy to .env and add your API key
```

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then paste in your ANTHROPIC_API_KEY
python agent.py
```

## Status

Scaffold only — the files are placeholders. Nothing is implemented yet.
