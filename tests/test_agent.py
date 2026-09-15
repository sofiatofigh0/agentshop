"""The agent loop's cache marker and the search tool's usage accounting."""

import os
import threading
import unittest
from types import SimpleNamespace
from unittest import mock

import agent
import tools


class CacheMarker(unittest.TestCase):
    def test_first_turn_marks_the_posting(self):
        messages = [{"role": "user", "content": "the posting"}]
        agent.mark_cache(messages)
        self.assertEqual(messages[0]["content"],
                         [{"type": "text", "text": "the posting",
                           "cache_control": {"type": "ephemeral"}}])

    def test_marker_moves_to_the_newest_user_turn(self):
        messages = [{"role": "user", "content": "the posting"}]
        agent.mark_cache(messages)
        messages.append({"role": "assistant", "content": [SimpleNamespace(type="tool_use")]})
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "a", "content": "found"},
            {"type": "tool_result", "tool_use_id": "b", "content": "found more"},
        ]})
        agent.mark_cache(messages)
        self.assertNotIn("cache_control", messages[0]["content"][0])
        self.assertNotIn("cache_control", messages[2]["content"][0])
        self.assertEqual(messages[2]["content"][1]["cache_control"], {"type": "ephemeral"})
        # Assistant turns are SDK objects and are never touched.
        self.assertEqual(messages[1]["content"][0].type, "tool_use")


class SearchUsage(unittest.TestCase):
    def test_collect_without_begin_is_empty(self):
        tools._local.spend = None
        spend = tools.collect_usage()
        self.assertEqual(spend.calls, 0)

    def test_usage_is_per_thread(self):
        seen = {}

        def worker(name, tokens):
            tools.begin_usage()
            tools._local.spend.add("claude-opus-5", SimpleNamespace(
                input_tokens=tokens, output_tokens=0, cache_read_input_tokens=0,
                cache_creation_input_tokens=0, cache_creation=None, server_tool_use=None))
            seen[name] = tools.collect_usage().input_tokens

        threads = [threading.Thread(target=worker, args=("a", 100)),
                   threading.Thread(target=worker, args=("b", 200))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(seen, {"a": 100, "b": 200})

    def test_search_records_usage_and_uses_the_worker_model(self):
        captured = {}

        class Client:
            class messages:
                @staticmethod
                def create(**kwargs):
                    captured.update(kwargs)
                    return SimpleNamespace(
                        content=[SimpleNamespace(type="text", text="Facts [example.com]")],
                        usage=SimpleNamespace(input_tokens=5000, output_tokens=300,
                                              cache_read_input_tokens=0,
                                              cache_creation_input_tokens=0, cache_creation=None,
                                              server_tool_use=SimpleNamespace(web_search_requests=2)))

        with mock.patch.object(tools.anthropic, "Anthropic", lambda: Client()), \
             mock.patch.dict(os.environ, {"ANTHROPIC_MODEL": "claude-opus-5",
                                          "ANTHROPIC_WORKER_MODEL": "claude-sonnet-5"}):
            os.environ.pop("ANTHROPIC_EFFORT", None)
            tools.begin_usage()
            text = tools.search_web("who is acme")
            spend = tools.collect_usage()

        self.assertEqual(text, "Facts [example.com]")
        self.assertEqual(captured["model"], "claude-sonnet-5")
        self.assertEqual(captured["max_tokens"], 1500)
        self.assertEqual(captured["tools"][0]["max_uses"], tools.MAX_SEARCHES_PER_QUERY)
        self.assertEqual(captured["output_config"], {"effort": "low"})
        self.assertIn("who is acme", captured["messages"][0]["content"])
        self.assertEqual(spend.web_searches, 2)
        self.assertEqual(spend.input_tokens, 5000)
        self.assertAlmostEqual(spend.dollars(),
                               round((5000 * 2 + 300 * 10) / 1e6 + 0.02, 4))

    def test_failed_search_returns_text_not_exception(self):
        class Client:
            class messages:
                @staticmethod
                def create(**kwargs):
                    raise RuntimeError("network")

        with mock.patch.object(tools.anthropic, "Anthropic", lambda: Client()), \
             mock.patch.dict(os.environ, {"ANTHROPIC_MODEL": "claude-opus-5"}):
            self.assertIn("The search failed", tools.search_web("x"))


if __name__ == "__main__":
    unittest.main()
