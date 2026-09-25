"""
Which model does what, how hard it thinks, and what a run costs.

Every model call in this project goes through one of three knobs defined here:

    main_model()      the model that judges and writes — set by ANTHROPIC_MODEL
    worker_model()    the model for extraction-shaped side jobs: summarizing a
                      web search, pulling keywords out of a posting, distilling
                      an edit into a lesson. Defaults to the main model; set
                      ANTHROPIC_WORKER_MODEL to a cheaper one to cut those
                      calls' cost without touching the documents themselves.
    request_options() the per-step effort, as top-level request arguments.
    effort_message()  the per-step effort for the calls that share a cached
                      prefix, carried inside `messages` instead.

The split between those last two is the whole subtlety of this file, and it
exists because the two cheapest levers in this project pull against each other.

Effort is where most of a call's cost goes, and the writing steps do not need
the same depth of reasoning as the verdict or the evidence map. But a
top-level effort value is rendered into the prompt itself, so changing it
between calls starts a new cache prefix — on models that render it ahead of
the system prompt it invalidates the system cache too. The generation
calls share a ~14k-token cached prefix holding the whole experience bank. Vary
their effort and each one rewrites that prefix instead of reading it, which
costs far more than the effort ever saved.

So: for those calls the top-level effort is pinned (left at the model's
default, which is the same thing as omitting it), and per-step depth rides in
a `role: "system"` message with empty content and its own output_config —
message content never invalidates the system cache, so the prefix survives.
That mechanism is beta and model-gated; where it is unavailable the generation
calls simply all run at the default depth, because the cache is worth more
than the difference. Steps whose calls share no cached prefix — the search
summary, keyword extraction, lesson distillation — set effort the plain way.

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

# Models that can carry an effort change inside `messages` instead of at the
# top level, which is what lets a step change depth without resetting the
# cached prefix. Beta, and first-party API only. "opus-5" also covers
# Claude Opus 5.5, which takes it too.
_PER_MESSAGE_EFFORT = re.compile(r"claude-(?:opus-5|fable-5-1|mythos-5-1)")
PER_MESSAGE_EFFORT_BETA = "mid-conversation-output-config-2026-07-01"

# Not every effort-capable model takes every level, and the exceptions are not
# a simple ceiling: Opus 4.6 and Sonnet 4.6 accept "max" but not "xhigh",
# which arrived with Opus 4.7. So this is a membership test, not a rank
# comparison. Anything effort-capable and unlisted takes all five.
_ACCEPTED_LEVELS = [
    (re.compile(r"claude-opus-4-5"), ("low", "medium", "high")),
    (re.compile(r"claude-(?:opus-4-6|sonnet-4-6)"), ("low", "medium", "high", "max")),
]


def supports_effort(model: str) -> bool:
    return bool(_EFFORT_CAPABLE.search(model or ""))


def supports_per_message_effort(model: str) -> bool:
    return bool(_PER_MESSAGE_EFFORT.search(model or ""))


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
    "resume":       "medium",
    "cover_letter": "medium",
    "strategy":     "medium",
    "phrasing":     "medium",  # rewording for the posting's vocabulary
    "search":       "low",     # summarize what a web search returned
    "keywords":     "low",     # extract the terms a screener scans for
    "distill":      "low",     # one edit -> one sentence
}

# The steps whose calls share the generation stage's cached prefix. Their
# top-level effort must be identical or the prefix is rewritten instead of
# read — see this module's docstring.
GENERATION_STEPS = frozenset({
    "evidence_map", "resume", "phrasing", "cover_letter", "strategy",
})

_LEVELS = ("low", "medium", "high", "xhigh", "max")

# The level a model runs at when no effort is sent. Sending it explicitly is
# the same as omitting the field, so it is what the generation calls pin to.
# Most models default to "high"; Claude Opus 5.5 defaults one level lower, and
# assuming "high" there would quietly run the evidence map at "medium".
DEFAULT_EFFORT = "high"
_DEFAULT_EFFORT = [
    (re.compile(r"claude-opus-5-5"), "medium"),
]


def default_effort(model: str) -> str:
    """The effort this model runs at when the field is omitted."""
    for pattern, level in _DEFAULT_EFFORT:
        if pattern.search(model or ""):
            return level
    return DEFAULT_EFFORT


def accepted_levels(model: str) -> tuple:
    """The effort levels this model actually takes."""
    for pattern, levels in _ACCEPTED_LEVELS:
        if pattern.search(model or ""):
            return levels
    return _LEVELS


def _clamp(level: str, model: str) -> str:
    """The nearest level at or below `level` that this model accepts.

    A level the model rejects is a 400 on every call of the run, so a forced
    ANTHROPIC_EFFORT of "xhigh" on Opus 4.5 becomes "high" rather than
    breaking the sweep it was set for.
    """
    accepted = accepted_levels(model)
    if level in accepted:
        return level
    for candidate in reversed(_LEVELS[:_LEVELS.index(level)]):
        if candidate in accepted:
            return candidate
    return accepted[0]


def forced_effort() -> str:
    """The level ANTHROPIC_EFFORT pins every step to, or "" when unset.

    An eval sweep sets this to compare one setting against another. It applies
    to every step, including the cached generation calls — one level
    everywhere is constant, so it is cache-safe.
    """
    forced = os.environ.get("ANTHROPIC_EFFORT", "").strip().lower()
    return forced if forced in _LEVELS else ""


def effort_for(step: str, model: str = None) -> str:
    """The effort for one step, clamped to what this model accepts."""
    model = model if model is not None else main_model()
    return _clamp(forced_effort() or EFFORT[step], model)


def request_options(step: str, model: str = None) -> dict:
    """Keyword arguments to splat into messages.create() for one step.

    Empty when the model rejects the effort field (Haiku 4.5, Sonnet 4.5 and
    older), and empty for the generation steps unless a sweep is forcing one
    level: their depth is carried by effort_message() instead, so that the
    cached prefix they share is not reset between them.
    """
    model = model if model is not None else main_model()
    if not supports_effort(model):
        return {}
    if step in GENERATION_STEPS and not forced_effort():
        return {}
    return {"output_config": {"effort": effort_for(step, model)}}


# Set to False for the rest of the process the first time the API rejects the
# beta, so an account without it pays for one failed call rather than one per
# call. The fallback is simply the default depth, which is correct, just less
# thrifty.
_per_message_effort_ok = True


def disable_per_message_effort() -> None:
    global _per_message_effort_ok
    _per_message_effort_ok = False


def effort_message(step: str, model: str = None):
    """The `messages` entry that sets this step's depth, or None.

    None means "run this step at the model's default depth" — either because
    that is what the step asks for, because a sweep is pinning every step from
    the top level, or because this model cannot change effort without
    resetting the cache, in which case the cache wins.
    """
    model = model if model is not None else main_model()
    if (not _per_message_effort_ok or forced_effort()
            or not supports_effort(model) or not supports_per_message_effort(model)):
        return None
    level = effort_for(step, model)
    if level == default_effort(model):
        return None  # identical to omitting it, so do not spend a message on it
    return {"role": "system", "content": [], "output_config": {"effort": level}}


# --------------------------------------------------------------------------
# Cache lifetime
# --------------------------------------------------------------------------

def long_lived_ttl() -> str:
    """"1h" or "5m": the lifetime of the blocks that outlive a run."""
    chosen = os.environ.get("PROMPT_CACHE_TTL", "").strip().lower()
    return "5m" if chosen == "5m" else "1h"


def cache_control(long_lived: bool = False) -> dict:
    """The cache marker for one prompt block.

    The per-run blocks keep the default 5-minute cache: the calls inside one
    run start well under five minutes apart, and every read refreshes it.

    The blocks that are byte-identical across runs — the agent's instructions
    and the generation prefix holding the whole experience bank — get an hour.
    Postings run one after another are further apart than five minutes, so on
    the 5-minute cache each run re-wrote the bank at 1.25x and never read it
    again. On the hour cache the first run of a sitting writes it at 2x and
    every later run inside the hour reads it at a tenth of the price or less:
    the hour pays for itself from the second run. A run on its own pays the
    difference, 0.75x on the prefix; PROMPT_CACHE_TTL=5m turns it off for
    anyone who only ever runs one posting at a time. The API requires the
    longer-lived block to come first, which the callers here respect.
    """
    if long_lived and long_lived_ttl() == "1h":
        return {"type": "ephemeral", "ttl": "1h"}
    return {"type": "ephemeral"}


# --------------------------------------------------------------------------
# Prices
# --------------------------------------------------------------------------

# Dollars per million tokens, (input, output), first-party API rates. Cache
# writes bill 1.25x input for the 5-minute TTL and 2x for the 1-hour one;
# cache reads are priced by cache_read_rate() below. Longest names first so
# "claude-opus-5" cannot claim "claude-opus-5-5".
RATES = sorted([
    ("claude-fable-5-1", 10.0, 50.0), ("claude-mythos-5-1", 10.0, 50.0),
    ("claude-fable-5", 10.0, 50.0), ("claude-mythos-5", 10.0, 50.0),
    ("claude-opus-5-5", 4.0, 20.0),
    ("claude-opus-5", 5.0, 25.0), ("claude-opus-4-8", 5.0, 25.0),
    ("claude-opus-4-7", 5.0, 25.0), ("claude-opus-4-6", 5.0, 25.0),
    ("claude-opus-4-5", 5.0, 25.0),
    ("claude-sonnet-5", 2.0, 10.0), ("claude-sonnet-4-6", 3.0, 15.0),
    ("claude-sonnet-4-5", 3.0, 15.0),
    ("claude-haiku-4-5", 1.0, 5.0),
], key=lambda row: -len(row[0]))

WEB_SEARCH_USD = 0.01   # $10 per 1,000 searches, on top of the tokens


# Cache reads as a fraction of the input price. 0.1x on most models; the
# newest price them lower, which moves every caching break-even with them.
_CACHE_READ_RATES = [
    (re.compile(r"claude-(?:fable|mythos)-5-1"), 0.025),
    (re.compile(r"claude-opus-5-5"), 0.05),
]


def cache_read_rate(model: str) -> float:
    for pattern, rate in _CACHE_READ_RATES:
        if pattern.search(model or ""):
            return rate
    return 0.1


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
            read_rate = cache_read_rate(model)
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
