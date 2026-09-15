"""Model selection, effort gating, cache lifetime and the price table."""

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

    def test_request_options_per_step(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_MODEL": "claude-opus-5"}, clear=False):
            os.environ.pop("ANTHROPIC_EFFORT", None)
            self.assertEqual(models.request_options("resume"),
                             {"output_config": {"effort": "medium"}})
            self.assertEqual(models.request_options("factuality"),
                             {"output_config": {"effort": "high"}})
            self.assertEqual(models.request_options("search", "claude-haiku-4-5"), {})

    def test_forced_effort(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_MODEL": "claude-opus-5",
                                          "ANTHROPIC_EFFORT": "LOW"}):
            self.assertEqual(models.effort_for("factuality"), "low")
        with mock.patch.dict(os.environ, {"ANTHROPIC_MODEL": "claude-opus-5",
                                          "ANTHROPIC_EFFORT": "bogus"}):
            self.assertEqual(models.effort_for("factuality"), "high")

    def test_every_step_has_a_level(self):
        for step, level in models.EFFORT.items():
            self.assertIn(level, models._LEVELS, step)

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
