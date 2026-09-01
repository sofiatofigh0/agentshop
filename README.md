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
agent.py                  orchestration, the agent loop, interactive input
tools.py                  the search_web tool: schema + implementation
candidate_profile.py      what you want — preferences, goals, constraints
experience_bank.py        what you have done — the factual source of truth
application_generator.py  deterministic resume / letter / strategy pipeline
sample_jobs.py            fixtures for the eval suite
evals.py                  the eval harness
outputs/                  generated materials (gitignored)
```

Two files hold facts about you and they are deliberately separate.
`candidate_profile.py` is preference — it decides APPLY / MAYBE / SKIP.
`experience_bank.py` is evidence — it is the only thing generated materials may
draw on. Nothing written into a resume can come from the profile.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then fill in ANTHROPIC_API_KEY and ANTHROPIC_MODEL
```

Fill in `experience_bank.py` with your real experience — the agent refuses to
generate application materials while placeholders remain, because it will not
invent facts to fill the gaps. Then:

```bash
python agent.py           # paste a job description, end with END on its own line
python evals.py           # run the fixture suite instead
```

If the verdict is APPLY or MAYBE the package is generated automatically; on a
SKIP you are asked, and the default is no. Everything lands in `outputs/`,
which is gitignored because generated applications contain personal
information.

## Factual guardrails

Generated materials go through a fixed pipeline, and the model does not get to
approve its own work:

1. a requirement-to-evidence map, written before any prose, so selection has to
   be justified rather than keyword-matched
2. a resume drafted from that map
3. a separate factuality call that reads the draft against the experience bank
   and labels every claim SUPPORTED / PARTIALLY SUPPORTED / UNSUPPORTED
4. Python reads that verdict and forces a revision pass if anything failed
5. only then is the file written

## Status

Working. The eval suite covers the evaluation half; the generation half is
exercised by running it.
