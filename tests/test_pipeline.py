"""The generation pipeline with the model calls faked.

What is under test is the wiring: which steps run in which order, when the
rephrasing pass fires and when it does not, that the factuality review reads
the reworded draft, and what lands on disk. The PDFs are really rendered.
"""

import json
import os
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest import mock

import anthropic

import application_generator as gen
import ats

KEYWORDS = [
    {"term": "product roadmap", "category": "hard_skill", "importance": "required", "aliases": ["roadmap"]},
    {"term": "sql", "category": "tool", "importance": "required", "aliases": []},
    {"term": "llm evaluation", "category": "hard_skill", "importance": "required", "aliases": ["llm evals"]},
    {"term": "a/b testing", "category": "hard_skill", "importance": "preferred", "aliases": []},
    {"term": "kubernetes", "category": "tool", "importance": "mentioned", "aliases": []},
]
EXTRACTED = {"title": "Senior Product Manager", "keywords": KEYWORDS}

# The bank, as running text, for the gate: it mentions SQL and LLM evaluation
# but neither A/B testing nor Kubernetes.
BANK_PROSE = ats._norm("Owned the roadmap. Built the LLM evaluation rubric. Wrote SQL reports.")

HEAD = """# Jane Example
**Senior Product Manager**
New York · jane@example.com · 555-0100

## Profile
Product manager for an evaluation platform.

## Skills
- Roadmaps
- Analytics

## Experience
### Senior Product Manager — Acme | 2022 – Present
"""
TAIL = """
## Education
**BS Computer Science**
State University · 2016 – 2020
"""
# roadmap only: 3 of 12 weight = 25
DRAFT = HEAD + "- Owned the roadmap for the evaluation suite used by 40 teams.\n" + TAIL
# roadmap + sql + llm evaluation: 9 of 12 = 75
REWORDED = HEAD + ("- Owned the product roadmap for the LLM evaluation suite used by 40 teams.\n"
                   "- Built the SQL reporting behind it.\n") + TAIL
# everything: 100
FULL = HEAD + ("- Owned the product roadmap for the LLM evaluation suite used by 40 teams.\n"
               "- Built the SQL reporting and A/B testing behind it, on Kubernetes.\n") + TAIL

EVIDENCE = "| Requirement | Priority | Evidence | Where | Metric | Strength | Gap |\n|-|-|-|-|-|-|-|\n| roadmap | HIGH | owned it | Acme | — | STRONG | — |\n"
LETTER = "# Jane Example\nNew York · jane@example.com\n\nDear team,\n\nI owned the product roadmap.\n\nJane"
STRATEGY = "## Recommendation\nAPPLY\n## Why\nFit.\n"
CLEAN_REVIEW = "| Claim | Verdict | Basis |\n|-|-|-|\n| roadmap | SUPPORTED | bank |\n\nREQUIRED FIXES\nNone.\n"
DIRTY_REVIEW = "| Claim | Verdict | Basis |\n|-|-|-|\n| 40 teams | UNSUPPORTED | not in bank |\n\nREQUIRED FIXES\n- cut 40 teams\n"


def fake_usage():
    return SimpleNamespace(input_tokens=1000, output_tokens=500, cache_read_input_tokens=0,
                           cache_creation_input_tokens=0, cache_creation=None,
                           server_tool_use=None)


class Fake:
    """Stand-in for _call: canned text per step, and a log of the steps run."""

    def __init__(self, resume=DRAFT, reworded=REWORDED, review=CLEAN_REVIEW):
        self.texts = {"evidence_map": EVIDENCE, "resume": resume, "phrasing": reworded,
                      "factuality": review, "revision": FULL, "cover_letter": LETTER,
                      "strategy": STRATEGY}
        self.steps = []
        self.inputs = {}
        self.lock = threading.Lock()

    def __call__(self, step, instructions, user, context="", max_tokens=8000):
        with self.lock:
            self.steps.append(step)
            self.inputs[step] = (instructions, user, context)
        return self.texts[step], fake_usage()


class Pipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patches = [
            mock.patch.object(gen, "OUTPUT_DIR", self.tmp.name),
            mock.patch.object(gen, "BANK_PROSE", BANK_PROSE),
            mock.patch.object(gen, "missing_fields", lambda: []),
            mock.patch.object(gen.lessons, "prompt_block", lambda: ""),
            mock.patch.dict(os.environ, {"ANTHROPIC_MODEL": "claude-opus-5",
                                         "ATS_TARGET_SCORE": "75"}),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        os.environ.pop("ANTHROPIC_WORKER_MODEL", None)
        self.progress = []

    def tearDown(self):
        self.tmp.cleanup()

    def run_pipeline(self, fake, extract=None):
        extract = extract or (lambda jd: (EXTRACTED, fake_usage()))
        with mock.patch.object(gen, "_call", fake), \
             mock.patch.object(ats, "extract_keywords", extract):
            return gen.generate_application_package(
                "JD text", "APPLY", "fits", research="Acme raised money",
                company="Acme", role="Senior PM", progress=self.progress.append)

    def test_rephrasing_runs_when_below_target_and_bank_mentions_terms(self):
        fake = Fake()
        package = self.run_pipeline(fake)

        chain = [s for s in fake.steps if s in ("resume", "phrasing", "factuality", "revision")]
        self.assertEqual(chain, ["resume", "phrasing", "factuality"])
        # The review read the reworded draft, not the original.
        self.assertIn("SQL reporting", fake.inputs["factuality"][1])
        # Only the terms the bank mentions were offered to the pass.
        offered = fake.inputs["phrasing"][1]
        self.assertIn("- sql", offered)
        self.assertIn("- llm evaluation", offered)
        self.assertNotIn("kubernetes", offered)
        self.assertNotIn("a/b testing", offered)

        self.assertEqual(package["ats"]["resume"], 75)
        self.assertEqual(package["ats"]["target"], 75)
        self.assertEqual(package["generation_calls"], 7)  # 6 main + keywords
        self.assertAlmostEqual(package["cost_usd"], round(7 * (1000 * 5 + 500 * 25) / 1e6, 4))

        run_dir = package["run_dir"]
        for name in ("tailored_resume.pdf", "cover_letter.pdf", "evidence_map.pdf",
                     "factuality_review.pdf", "application_strategy.pdf", "ats_report.pdf",
                     gen.ATS_FILE, gen.SOURCES_FILE, "run.json"):
            self.assertTrue(os.path.isfile(os.path.join(run_dir, name)), name)
        with open(os.path.join(run_dir, gen.ATS_FILE)) as handle:
            data = json.load(handle)
        self.assertEqual(data["rephrasing_pass"],
                         {"considered": 2, "before": 25, "after": 75, "kept": True,
                          "terms": ["llm evaluation", "sql"]})
        self.assertEqual(data["resume"]["score"], 75)
        self.assertEqual(len(data["keywords"]), 5)
        with open(os.path.join(run_dir, "run.json")) as handle:
            meta = json.load(handle)
        self.assertEqual(meta["ats"]["resume"], 75)
        self.assertIsNotNone(meta["generation_usd"])
        with open(os.path.join(run_dir, gen.SOURCES_FILE)) as handle:
            self.assertNotIn("ats_report", json.load(handle))

    def test_no_rephrasing_when_already_at_target(self):
        fake = Fake(resume=FULL)
        package = self.run_pipeline(fake)
        self.assertNotIn("phrasing", fake.steps)
        self.assertEqual(package["ats"]["resume"], 100)
        self.assertEqual(package["generation_calls"], 6)

    def test_no_rephrasing_when_bank_mentions_nothing(self):
        fake = Fake()
        with mock.patch.object(gen, "BANK_PROSE", "unrelated work entirely"):
            package = self.run_pipeline(fake)
        self.assertNotIn("phrasing", fake.steps)
        self.assertEqual(package["ats"]["resume"], 25)

    def test_reworded_draft_dropped_when_it_does_not_score_higher(self):
        fake = Fake(reworded=DRAFT)
        package = self.run_pipeline(fake)
        self.assertIn("phrasing", fake.steps)
        self.assertIn("Owned the roadmap for the evaluation suite", fake.inputs["factuality"][1])
        self.assertEqual(package["ats"]["resume"], 25)

    def test_revision_follows_a_failed_review(self):
        fake = Fake(review=DIRTY_REVIEW)
        package = self.run_pipeline(fake)
        chain = [s for s in fake.steps if s in ("resume", "phrasing", "factuality", "revision")]
        self.assertEqual(chain, ["resume", "phrasing", "factuality", "revision"])
        self.assertEqual(package["ats"]["resume"], 100)  # scored on the final text

    def test_keyword_failure_does_not_stop_the_run(self):
        fake = Fake()

        def broken(jd):
            raise RuntimeError("model down")

        package = self.run_pipeline(fake, extract=broken)
        self.assertNotIn("phrasing", fake.steps)
        self.assertEqual(package["ats"], {"resume": None, "cover_letter": None, "target": 75})
        self.assertTrue(os.path.isfile(os.path.join(package["run_dir"], "ats_report.pdf")))
        self.assertTrue(any("keyword extraction failed" in line for line in self.progress))
        self.assertNotIn("ATS KEYWORDS", fake.inputs["resume"][0])

    def test_context_block_placement(self):
        """The posting rides in the cached run context, not the user turn; the
        factuality review gets neither."""
        fake = Fake(resume=FULL)
        self.run_pipeline(fake)
        instructions, user, context = fake.inputs["resume"]
        self.assertIn("JD text", context)
        self.assertIn("Acme raised money", context)
        self.assertNotIn("JD text", user)
        self.assertIn("ATS KEYWORDS", instructions)
        self.assertEqual(fake.inputs["factuality"][2], "")
        self.assertIn("ATS KEYWORDS", fake.inputs["cover_letter"][0])
        self.assertNotIn("ATS KEYWORDS", fake.inputs["strategy"][0])

    def test_stretch_brief_rides_on_instructions(self):
        fake = Fake(resume=FULL)
        with mock.patch.object(gen, "_call", fake), \
             mock.patch.object(ats, "extract_keywords", lambda jd: (EXTRACTED, fake_usage())):
            gen.generate_application_package("JD text", "MAYBE", "close", company="Acme",
                                             role="PM", progress=self.progress.append)
        self.assertIn("STRETCH APPLICATION", fake.inputs["resume"][0])
        self.assertIn("Bridges", fake.inputs["evidence_map"][0])
        self.assertNotIn("STRETCH APPLICATION", fake.inputs["evidence_map"][2])


class Recorder:
    """A fake Anthropic client that records both transport paths."""

    def __init__(self, fail_beta=False):
        self.calls = []
        self.fail_beta = fail_beta
        outer = self

        def make(beta):
            def create(**kwargs):
                outer.calls.append({"beta": beta, **kwargs})
                if beta and outer.fail_beta:
                    raise anthropic.BadRequestError(
                        "unknown beta", response=SimpleNamespace(status_code=400,
                                                                 headers={}, request=None),
                        body=None)
                return SimpleNamespace(content=[SimpleNamespace(type="text", text="ok")],
                                       usage=fake_usage(), stop_reason="end_turn")
            return SimpleNamespace(create=create)

        self.messages = make(False)
        self.beta = SimpleNamespace(messages=make(True))


class CallShape(unittest.TestCase):
    """_call builds the system prompt in cache order: stable, run, step."""

    def setUp(self):
        gen.models._per_message_effort_ok = True
        self.addCleanup(setattr, gen.models, "_per_message_effort_ok", True)
        os.environ.pop("ANTHROPIC_EFFORT", None)
        os.environ.pop("PROMPT_CACHE_TTL", None)

    def call(self, step, model="claude-opus-5", context="RUN CONTEXT", fail_beta=False):
        client = Recorder(fail_beta=fail_beta)
        with mock.patch.object(gen.anthropic, "Anthropic", lambda: client), \
             mock.patch.dict(os.environ, {"ANTHROPIC_MODEL": model}):
            text, usage = gen._call(step, "STEP", "USER", context)
        return client, text

    def test_system_blocks(self):
        client, text = self.call("resume")
        self.assertEqual(text, "ok")
        system = client.calls[-1]["system"]
        self.assertEqual([b["text"][:12] for b in system],
                         [gen.STABLE_PREFIX[:12], "RUN CONTEXT", "STEP"])
        self.assertIn("cache_control", system[0])
        self.assertIn("cache_control", system[1])
        self.assertNotIn("cache_control", system[2])

    def test_no_context_means_two_blocks(self):
        client, _ = self.call("factuality", model="claude-haiku-4-5", context="")
        self.assertEqual(len(client.calls[-1]["system"]), 2)
        self.assertNotIn("output_config", client.calls[-1])

    def test_depth_rides_in_messages_never_at_the_top_level(self):
        """The cached prefix must not see a different effort per step."""
        client, _ = self.call("resume")
        call = client.calls[-1]
        self.assertTrue(call["beta"])
        self.assertNotIn("output_config", call)
        self.assertEqual(call["messages"][0],
                         {"role": "system", "content": [],
                          "output_config": {"effort": "medium"}})
        self.assertEqual(call["messages"][1], {"role": "user", "content": "USER"})
        self.assertEqual(call["betas"], [gen.models.PER_MESSAGE_EFFORT_BETA])

    def test_default_depth_takes_the_plain_path(self):
        client, _ = self.call("factuality")
        self.assertEqual([c["beta"] for c in client.calls], [False])
        self.assertEqual(client.calls[0]["messages"],
                         [{"role": "user", "content": "USER"}])

    def test_a_rejected_beta_falls_back_and_is_not_retried(self):
        client = Recorder(fail_beta=True)
        with mock.patch.object(gen.anthropic, "Anthropic", lambda: client), \
             mock.patch.dict(os.environ, {"ANTHROPIC_MODEL": "claude-opus-5"}):
            gen._call("resume", "STEP", "USER", "CTX")
            gen._call("cover_letter", "STEP", "USER", "CTX")
        # first step tries the beta, falls back; the second never tries again
        self.assertEqual([c["beta"] for c in client.calls], [True, False, False])
        self.assertFalse(gen.models._per_message_effort_ok)

    def test_a_sweep_pins_effort_at_the_top_level_for_every_step(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_EFFORT": "low"}):
            sent = []
            for step in ("evidence_map", "resume", "factuality"):
                client, _ = self.call(step)
                call = client.calls[-1]
                self.assertFalse(call["beta"])
                sent.append(call["output_config"])
        self.assertEqual(sent, [{"effort": "low"}] * 3)


if __name__ == "__main__":
    unittest.main()
