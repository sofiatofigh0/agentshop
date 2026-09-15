"""
Which model does what, how hard it thinks, and what a run costs.

Every model call in this project goes through one of three knobs defined here:

    main_model()      the model that judges and writes — set by ANTHROPIC_MODEL
    worker_model()    the model for extraction-shaped side jobs: summarizing a
                      web search, pulling keywords out of a posting, distilling
                      an edit into a lesson. Defaults to the main model; set
                      ANTHROPIC_WORKER_MODEL to a cheaper one to cut those
                      calls' cost without touching the documents themselves.
    request_options() the per-step effort. The writing steps do not need the
                      same depth of reasoning as the verdict or the factuality
                      review, and on current models effort is where most of a
                      call's cost goes.

Plus a price table, so the trace and the UI can say what a run actually cost
instead of "roughly $1".

Nothing here reads the environment at import time: .env is loaded by whichever
entry point runs first, and these helpers are called later.
"""

import os
import re
import threading

# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------

def main_model() -> str:
    return os.environ.get("ANTHROPIC_MODEL", "")


def worker_model() -> str:
    """The model for the side jobs. Falls back to the main model."""
    return os.environ.get("ANTHROPIC_WORKER_MODEL") or main_model()


# Models that accept output_config.effort. Matched by search rather than
# equality so provider-prefixed IDs (Bedrock's "anthropic.claude-opus-5",
# Vertex's "claude-opus-4-5@20251101") work too.
_EFFORT_CAPABLE = re.compile(r"claude-(?:opus-(?:4-[5-9]|5)|sonnet-(?:4-6|5)|fable|mythos)")

# Models that take the newer web_search tool variant. Older ones get the basic
# variant, which is the only one Haiku 4.5 and Sonnet 4.5 accept.
_NEW_WEB_SEARCH = re.compile(r"claude-(?:opus-(?:4-[6-9]|5)|sonnet-(?:4-6|5)|fable|mythos)")


def supports_effort(model: str) -> bool:
    return bool(_EFFORT_CAPABLE.search(model or ""))


def web_search_tool(model: str, max_uses: int) -> dict:
    """The server-side web search tool definition this model accepts."""
    kind = "web_search_20260209" if _NEW_WEB_SEARCH.search(model or "") else "web_search_20250305"
    return {"type": kind, "name": "web_search", "max_uses": max_uses}


# --------------------------------------------------------------------------
# Effort — the first cost lever that trades anything, applied per step
# --------------------------------------------------------------------------

# The steps where the model has to reason keep the default depth; the steps
# where it has to write, or do something mechanical, get less. A resume does
# not get better with more deliberation — the evidence map it is written from
# is where the thinking happens.
EFFORT = {
    "verdict":      "high",    # APPLY / MAYBE / SKIP — the judgement call
    "evidence_map": "high",    # the reasoning every document is built on
    "factuality":   "high",    # the guardrail
    "resume":       "medium",
    "cover_letter": "medium",
    "strategy":     "medium",
    "phrasing":     "medium",  # rewording for the posting's vocabulary
    "revision":     "low",     # apply the fixes the review listed
    "search":       "low",     # summarize what a web search returned
    "keywords":     "low",     # extract the terms a screener scans for
    "distill":      "low",     # one edit -> one sentence
}

_LEVELS = ("low", "medium", "high", "xhigh", "max")


def effort_for(step: str) -> str:
    """The effort for one step. ANTHROPIC_EFFORT forces every step to one
    level, which is how an eval sweep compares settings."""
    forced = os.environ.get("ANTHROPIC_EFFORT", "").strip().lower()
    if forced in _LEVELS:
        return forced
    return EFFORT[step]


def request_options(step: str, model: str = None) -> dict:
    """Keyword arguments to splat into messages.create() for one step.

    Empty on models that reject the effort field (Haiku 4.5, Sonnet 4.5 and
    older), so the same call site works whatever ANTHROPIC_MODEL is set to.
    """
    model = model if model is not None else main_model()
    if not supports_effort(model):
        return {}
    return {"output_config": {"effort": effort_for(step)}}


# --------------------------------------------------------------------------
# Cache lifetime
# --------------------------------------------------------------------------

def cache_control(long_lived: bool = False) -> dict:
    """The cache marker for one prompt block.

    The default 5-minute cache is right for the calls inside one run, which
    start well under five minutes apart. The blocks that are byte-identical
    across runs — the agent's instructions and the generation prefix with the
    whole experience bank in it — can outlive a run when PROMPT_CACHE_TTL=1h
    is set: a write then costs 2x instead of 1.25x, but every further run
    inside the hour reads the bank back at a tenth of the price instead of
    re-writing it. Worth it when several postings are run in one sitting;
    not when they are a day apart. Per-run blocks always stay at 5 minutes,
    and the API requires the longer-lived block to come first, which the
    callers here respect.
    """
    if long_lived and os.environ.get("PROMPT_CACHE_TTL", "").strip().lower() == "1h":
        return {"type": "ephemeral", "ttl": "1h"}
    return {"type": "ephemeral"}


# --------------------------------------------------------------------------
# Prices
# --------------------------------------------------------------------------

# Dollars per million tokens, (input, output), first-party API rates. Cache
# writes bill 1.25x input for the 5-minute TTL and 2x for the 1-hour one;
# cache reads bill 0.1x, except Claude Fable 5.1 at 0.025x. Longest names
# first so "claude-fable-5" cannot claim "claude-fable-5-1".
RATES = sorted([
    ("claude-fable-5-1", 10.0, 50.0), ("claude-mythos-5-1", 10.0, 50.0),
    ("claude-fable-5", 10.0, 50.0), ("claude-mythos-5", 10.0, 50.0),
    ("claude-opus-5", 5.0, 25.0), ("claude-opus-4-8", 5.0, 25.0),
    ("claude-opus-4-7", 5.0, 25.0), ("claude-opus-4-6", 5.0, 25.0),
    ("claude-opus-4-5", 5.0, 25.0),
    ("claude-sonnet-5", 2.0, 10.0), ("claude-sonnet-4-6", 3.0, 15.0),
    ("claude-sonnet-4-5", 3.0, 15.0),
    ("claude-haiku-4-5", 1.0, 5.0),
], key=lambda row: -len(row[0]))

WEB_SEARCH_USD = 0.01   # $10 per 1,000 searches, on top of the tokens


def rates(model: str):
    """(input, output) dollars per million tokens, or None for an unknown model."""
    for name, inp, out in RATES:
        if name in (model or ""):
            return inp, out
    return None


class Spend:
    """Token totals across calls, priced per model.

    One of these per phase; the threads in the generation stage all add to
    the same one, hence the lock. `dollars()` is None when any call ran on a
    model the price table does not know, rather than a number that is quietly
    wrong.
    """

    def __init__(self):
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_read = 0
        self.cache_write_5m = 0
        self.cache_write_1h = 0
        self.web_searches = 0
        self._usd = 0.0
        self._unpriced = False
        self._lock = threading.Lock()

    def add(self, model: str, usage) -> None:
        """Fold one response's usage block in."""
        inp = getattr(usage, "input_tokens", 0) or 0
        out = getattr(usage, "output_tokens", 0) or 0
        read = getattr(usage, "cache_read_input_tokens", 0) or 0
        written = getattr(usage, "cache_creation_input_tokens", 0) or 0
        breakdown = getattr(usage, "cache_creation", None)
        w1h = (getattr(breakdown, "ephemeral_1h_input_tokens", 0) or 0) if breakdown else 0
        w5m = (getattr(breakdown, "ephemeral_5m_input_tokens", None) if breakdown else None)
        if w5m is None:
            w5m = max(written - w1h, 0)
        server = getattr(usage, "server_tool_use", None)
        searches = (getattr(server, "web_search_requests", 0) or 0) if server else 0

        price = rates(model)
        with self._lock:
            self.calls += 1
            self.input_tokens += inp
            self.output_tokens += out
            self.cache_read += read
            self.cache_write_5m += w5m
            self.cache_write_1h += w1h
            self.web_searches += searches
            if price is None:
                self._unpriced = True
                return
            per_in, per_out = price
            read_rate = 0.025 if "fable-5-1" in model else 0.1
            self._usd += (
                inp * per_in
                + w5m * per_in * 1.25
                + w1h * per_in * 2.0
                + read * per_in * read_rate
                + out * per_out
            ) / 1_000_000 + searches * WEB_SEARCH_USD

    def absorb(self, other: "Spend") -> None:
        """Add another phase's totals to this one."""
        with self._lock:
            self.calls += other.calls
            self.input_tokens += other.input_tokens
            self.output_tokens += other.output_tokens
            self.cache_read += other.cache_read
            self.cache_write_5m += other.cache_write_5m
            self.cache_write_1h += other.cache_write_1h
            self.web_searches += other.web_searches
            self._usd += other._usd
            self._unpriced = self._unpriced or other._unpriced

    @property
    def cache_written(self) -> int:
        return self.cache_write_5m + self.cache_write_1h

    def dollars(self):
        return None if self._unpriced else round(self._usd, 4)

    def as_dict(self) -> dict:
        return {
            "calls": self.calls,
            "input": self.input_tokens,
            "output": self.output_tokens,
            "cache_read": self.cache_read,
            "cache_written": self.cache_written,
            "web_searches": self.web_searches,
            "usd": self.dollars(),
        }


def money(usd) -> str:
    """"$0.42", or a plain "n/a" when the model was not in the table."""
    return "n/a" if usd is None else f"${usd:.2f}"
