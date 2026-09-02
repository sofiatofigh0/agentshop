# Portfolio copy — Job Opportunity Agent

Reusable descriptions for a personal site, LinkedIn project section, or a résumé
line. Written to be pasted as-is.

---

## Short description (~25 words)

A personal AI agent that decides whether a job is worth pursuing, researches the
company only when it would change the answer, and drafts an evidence-backed
application.

---

## Medium description (~75 words)

A personal AI agent that evaluates job postings against a structured candidate
profile and returns APPLY, MAYBE or SKIP. The model decides whether external
research would change the recommendation, writes its own search queries, and
stops when it has enough — the agentic half. Once a role is worth pursuing, a
deterministic workflow maps requirements to evidence, drafts a tailored resume,
runs a separate factuality review against a source-of-truth experience bank, and
produces a cover letter and interview strategy. Built in Python with the
Anthropic API and no agent framework.

---

## Case study description (~150 words)

Most of evaluating a job posting is mechanical: extract the facts, check them
against what you want, notice what is missing. One part is not — knowing when
missing information matters enough to go find out. That single decision is why
this system is an agent rather than a prompt.

The model controls judgment: whether to research, what to query, whether one
result was enough. Python controls the execution envelope: the tool ceiling, loop
termination, which stages must run, and whether an unsupported resume claim
survives. Generated documents can only draw on a provenance-tagged experience
bank, and a separate factuality call — which the writer never gets to overrule —
gates what reaches the page.

Evaluation scores both outcome and trajectory. That mattered: an instruction that
suppressed tool use entirely left verdict accuracy untouched, and only the
trajectory metric caught it.

---

## Technologies

Python · Anthropic API (Claude) · tool use / function calling · web search ·
retrieval-augmented generation · LLM-as-judge evaluation · Next.js · TypeScript ·
React. No LangChain, CrewAI, or agent framework — the loop is hand-written.

---

## Key product concepts

- **Hybrid agent and workflow** — agency where judgment creates value,
  determinism where execution is predictable
- **Selective tool use** — research only when it could materially change the
  decision, not whenever information is missing
- **Outcome and trajectory evaluation** — a correct answer reached through
  unnecessary searches is still poor agent behavior
- **Provenance-tagged source of truth** — every generated claim traces to a
  labelled fact; unconfirmed figures are structurally unusable
- **Separated factuality gate** — the model that writes never approves its own
  work; software reads the verdict
- **Schema design as agent design** — representing hard constraints and
  preferences identically caused a reasoning failure that no prompt edit fixed

---

## One-line interview description

I built a personal job-application agent where the model decides whether it needs
to research a company, and software decides everything else — then evaluated it
on whether it used tools appropriately, not just whether the answer was right.
