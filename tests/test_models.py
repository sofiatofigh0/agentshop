"""Model selection, effort gating, cache lifetime and the price table."""

import json
import os
import unittest
from types import SimpleNamespace
from unittest import mock

import models


class Effort(unittest.TestCase):
    def test_which_models_take_effort(self):
        yes = ["claude-opus-5", "claude-opus-4-8", "claude-opus-4-7", "claude-opus-4-6",
               "claude-opus-4-5", "claude-sonnet-5", "claude-sonnet-4-6", "claude-fable-5-1",
               "claude-mythos-5", "anthropic.claude-opus-5", "claude-opus-4-5@20251101"]
        no = ["claude-haiku-4-5", "claude-sonnet-4-5", "claude-opus-4-1", "", None]
        for model in yes:
            self.assertTrue(models.supports_effort(model), model)
        for model in no:
            self.assertFalse(models.supports_effort(model), model)

    def test_side_job_steps_set_effort_at_the_top_level(self):
        """Their calls share no cached prefix, so varying effort costs nothing."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_MODEL": "claude-opus-5"}, clear=False):
            os.environ.pop("ANTHROPIC_EFFORT", None)
            self.assertEqual(models.request_options("search"),
                             {"output_config": {"effort": "low"}})
            self.assertEqual(models.request_options("keywords"),
                             {"output_config": {"effort": "low"}})
            self.assertEqual(models.request_options("distill"),
                             {"output_config": {"effort": "low"}})
            self.assertEqual(models.request_options("search", "claude-haiku-4-5"), {})

    def test_generation_steps_never_vary_top_level_effort(self):
        """The regression guard for the bug this contract exists to prevent.

        These calls share one cached ~14k-token prefix. A top-level effort that
        differs between them rewrites that prefix instead of reading it, which
        costs far more than the effort saves.
        """
        with mock.patch.dict(os.environ, {"ANTHROPIC_MODEL": "claude-opus-5"}, clear=False):
            os.environ.pop("ANTHROPIC_EFFORT", None)
            sent = {json.dumps(models.request_options(step), sort_keys=True)
                    for step in models.GENERATION_STEPS}
            self.assertEqual(sent, {"{}"})

    def test_a_sweep_pins_every_step_from_the_top_level(self):
        """One level everywhere is constant, so it is still cache-safe."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_MODEL": "claude-opus-5",
                                          "ANTHROPIC_EFFORT": "LOW"}):
            self.assertEqual(models.effort_for("factuality"), "low")
            sent = {json.dumps(models.request_options(step), sort_keys=True)
                    for step in list(models.GENERATION_STEPS) + ["search", "verdict"]}
            self.assertEqual(sent, {'{"output_config": {"effort": "low"}}'})
            self.assertIsNone(models.effort_message("resume"))

    def test_unknown_forced_level_falls_back(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_MODEL": "claude-opus-5",
                                          "ANTHROPIC_EFFORT": "bogus"}):
            self.assertEqual(models.forced_effort(), "")
            self.assertEqual(models.effort_for("factuality"), "high")

    def test_every_step_has_a_level(self):
        for step, level in models.EFFORT.items():
            self.assertIn(level, models._LEVELS, step)

    def test_generation_steps_match_the_pipeline(self):
        import application_generator as gen
        self.assertTrue(models.GENERATION_STEPS <= set(models.EFFORT))
        self.assertEqual(models.GENERATION_STEPS,
                         set(models.EFFORT) - {"verdict", "search", "keywords", "distill"})
        self.assertIn("phrasing", models.GENERATION_STEPS)
        self.assertTrue(callable(gen._call))


class LevelClamping(unittest.TestCase):
    """A level the model rejects is a 400 on every call, not a degraded one."""

    def test_accepted_levels_per_family(self):
        self.assertEqual(models.accepted_levels("claude-opus-4-5"),
                         ("low", "medium", "high"))
        self.assertEqual(models.accepted_levels("claude-opus-4-6"),
                         ("low", "medium", "high", "max"))
        self.assertEqual(models.accepted_levels("claude-sonnet-4-6"),
                         ("low", "medium", "high", "max"))
        self.assertEqual(models.accepted_levels("claude-opus-5"), models._LEVELS)

    def test_xhigh_clamps_where_unsupported(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_EFFORT": "xhigh"}):
            self.assertEqual(models.effort_for("verdict", "claude-opus-4-5"), "high")
            self.assertEqual(models.effort_for("verdict", "claude-sonnet-4-6"), "high")
            self.assertEqual(models.effort_for("verdict", "claude-opus-5"), "xhigh")

    def test_max_is_accepted_on_4_6_but_not_4_5(self):
        """Not a ceiling: 4.6 takes max while rejecting the lower-ranked xhigh."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_EFFORT": "max"}):
            self.assertEqual(models.effort_for("verdict", "claude-sonnet-4-6"), "max")
            self.assertEqual(models.effort_for("verdict", "claude-opus-4-5"), "high")

    def test_clamping_uses_the_call_s_own_model(self):
        """The side jobs run on the worker model, which may be another family."""
        with mock.patch.dict(os.environ, {"ANTHROPIC_MODEL": "claude-opus-5",
                                          "ANTHROPIC_EFFORT": "xhigh"}):
            self.assertEqual(models.request_options("search", "claude-opus-4-5"),
                             {"output_config": {"effort": "high"}})
            self.assertEqual(models.request_options("verdict"),
                             {"output_config": {"effort": "xhigh"}})


class PerMessageEffort(unittest.TestCase):
    """Depth for the cached calls rides in messages, where the cache survives."""

    def setUp(self):
        models._per_message_effort_ok = True
        self.addCleanup(setattr, models, "_per_message_effort_ok", True)
        os.environ.pop("ANTHROPIC_EFFORT", None)

    def test_shape(self):
        message = models.effort_message("resume", "claude-opus-5")
        self.assertEqual(message, {"role": "system", "content": [],
                                   "output_config": {"effort": "medium"}})

    def test_default_depth_needs_no_message(self):
        """Sending the default is the same as omitting it."""
        self.assertIsNone(models.effort_message("factuality", "claude-opus-5"))
        self.assertEqual(models.EFFORT["factuality"], models.DEFAULT_EFFORT)

    def test_unsupported_models_get_nothing(self):
        for model in ("claude-opus-4-8", "claude-sonnet-5", "claude-fable-5",
                      "claude-haiku-4-5"):
            self.assertIsNone(models.effort_message("resume", model), model)
        for model in ("claude-opus-5", "claude-fable-5-1", "claude-mythos-5-1"):
            self.assertIsNotNone(models.effort_message("resume", model), model)

    def test_one_rejection_stops_it_for_the_process(self):
        self.assertIsNotNone(models.effort_message("resume", "claude-opus-5"))
        models.disable_per_message_effort()
        self.assertIsNone(models.effort_message("resume", "claude-opus-5"))

    def test_worker_model_falls_back(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_MODEL": "claude-opus-5"}):
            os.environ.pop("ANTHROPIC_WORKER_MODEL", None)
            self.assertEqual(models.worker_model(), "claude-opus-5")
        with mock.patch.dict(os.environ, {"ANTHROPIC_MODEL": "claude-opus-5",
                                          "ANTHROPIC_WORKER_MODEL": "claude-sonnet-5"}):
            self.assertEqual(models.worker_model(), "claude-sonnet-5")

    def test_web_search_variant(self):
        self.assertEqual(models.web_search_tool("claude-opus-5", 2)["type"], "web_search_20260209")
        self.assertEqual(models.web_search_tool("claude-haiku-4-5", 2)["type"], "web_search_20250305")
        self.assertEqual(models.web_search_tool("claude-opus-5", 2)["max_uses"], 2)


class CacheLifetime(unittest.TestCase):
    def test_default_is_five_minutes(self):
        os.environ.pop("PROMPT_CACHE_TTL", None)
        self.assertEqual(models.cache_control(long_lived=True), {"type": "ephemeral"})

    def test_one_hour_only_for_long_lived_blocks(self):
        with mock.patch.dict(os.environ, {"PROMPT_CACHE_TTL": "1h"}):
            self.assertEqual(models.cache_control(long_lived=True),
                             {"type": "ephemeral", "ttl": "1h"})
            self.assertEqual(models.cache_control(), {"type": "ephemeral"})


def usage(**fields):
    base = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0, "cache_creation": None, "server_tool_use": None}
    base.update(fields)
    return SimpleNamespace(**base)


class Prices(unittest.TestCase):
    def test_longest_name_wins(self):
        self.assertEqual(models.rates("claude-fable-5-1"), (10.0, 50.0))
        self.assertEqual(models.rates("claude-fable-5"), (10.0, 50.0))
        self.assertEqual(models.rates("anthropic.claude-opus-5"), (5.0, 25.0))
        self.assertEqual(models.rates("claude-sonnet-4-6"), (3.0, 15.0))
        self.assertIsNone(models.rates("claude-future-9"))

    def test_spend_arithmetic(self):
        spend = models.Spend()
        spend.add("claude-opus-5", usage(
            input_tokens=1000, output_tokens=2000, cache_read_input_tokens=10000,
            cache_creation_input_tokens=14000,
            cache_creation=SimpleNamespace(ephemeral_5m_input_tokens=4000,
                                           ephemeral_1h_input_tokens=10000),
            server_tool_use=SimpleNamespace(web_search_requests=2),
        ))
        expected = (1000 * 5 + 4000 * 5 * 1.25 + 10000 * 5 * 2.0 + 10000 * 5 * 0.1
                    + 2000 * 25) / 1_000_000 + 2 * models.WEB_SEARCH_USD
        self.assertAlmostEqual(spend.dollars(), round(expected, 4))
        self.assertEqual(spend.cache_written, 14000)
        self.assertEqual(spend.web_searches, 2)
        self.assertEqual(spend.calls, 1)

    def test_write_without_breakdown_counts_as_five_minute(self):
        spend = models.Spend()
        spend.add("claude-sonnet-5", usage(cache_creation_input_tokens=1000))
        self.assertEqual(spend.cache_write_5m, 1000)
        self.assertAlmostEqual(spend.dollars(), round(1000 * 2 * 1.25 / 1_000_000, 4))

    def test_fable_reads_are_cheaper(self):
        spend = models.Spend()
        spend.add("claude-fable-5-1", usage(cache_read_input_tokens=1_000_000))
        self.assertAlmostEqual(spend.dollars(), 0.25)

    def test_unknown_model_gives_no_number(self):
        spend = models.Spend()
        spend.add("claude-opus-5", usage(input_tokens=100))
        spend.add("claude-future-9", usage(input_tokens=100))
        self.assertIsNone(spend.dollars())
        self.assertEqual(spend.input_tokens, 200)  # tokens still counted

    def test_absorb(self):
        a, b = models.Spend(), models.Spend()
        a.add("claude-opus-5", usage(input_tokens=1_000_000))
        b.add("claude-opus-5", usage(output_tokens=1_000_000))
        a.absorb(b)
        self.assertAlmostEqual(a.dollars(), 30.0)
        self.assertEqual(a.calls, 2)
        self.assertEqual(a.as_dict()["usd"], 30.0)

    def test_money(self):
        self.assertEqual(models.money(None), "n/a")
        self.assertEqual(models.money(0.4167), "$0.42")


if __name__ == "__main__":
    unittest.main()
