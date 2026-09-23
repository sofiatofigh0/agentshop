"""The generation pipeline with the model calls faked.

What is under test is the wiring: which steps run in which order, when the
rephrasing pass fires and when it does not, which draft is kept, and what
lands on disk. The PDFs are really rendered.
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
# Only "the roadmap": the alias of "product roadmap", so a variant. Exact score 0.
DRAFT = HEAD + "- Owned the roadmap for the evaluation suite used by 40 teams.\n" + TAIL
# No exact term and no variant either — not even "Roadmaps" in the Skills list.
BARE = (HEAD.replace("- Roadmaps\n", "- Planning\n")
        + "- Owned the evaluation suite used by 40 teams.\n" + TAIL)
# roadmap + sql + llm evaluation: 9 of 12 = 75
REWORDED = HEAD + ("- Owned the product roadmap for the LLM evaluation suite used by 40 teams.\n"
                   "- Built the SQL reporting behind it.\n") + TAIL
# everything: 100
FULL = HEAD + ("- Owned the product roadmap for the LLM evaluation suite used by 40 teams.\n"
               "- Built the SQL reporting and A/B testing behind it, on Kubernetes.\n") + TAIL

EVIDENCE = "| Requirement | Priority | Evidence | Where | Metric | Strength | Gap |\n|-|-|-|-|-|-|-|\n| roadmap | HIGH | owned it | Acme | — | STRONG | — |\n"
LETTER = "# Jane Example\nNew York · jane@example.com\n\nDear team,\n\nI owned the product roadmap.\n\nJane"
STRATEGY = "## Recommendation\nAPPLY\n## Why\nFit.\n"


def fake_usage():
    return SimpleNamespace(input_tokens=1000, output_tokens=500, cache_read_input_tokens=0,
                           cache_creation_input_tokens=0, cache_creation=None,
                           server_tool_use=None)


class Fake:
    """Stand-in for _call: canned text per step, and a log of the steps run."""

    def __init__(self, resume=DRAFT, reworded=REWORDED):
        self.texts = {"evidence_map": EVIDENCE, "resume": resume, "phrasing": reworded,
                      "cover_letter": LETTER, "strategy": STRATEGY}
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

        chain = [s for s in fake.steps if s in ("resume", "phrasing")]
        self.assertEqual(chain, ["resume", "phrasing"])
        # Only the terms the bank mentions were offered to the pass.
        offered = fake.inputs["phrasing"][1]
        self.assertIn("- sql", offered)
        self.assertIn("- llm evaluation", offered)
        self.assertNotIn("kubernetes", offered)
        self.assertNotIn("a/b testing", offered)

        self.assertEqual(package["ats"]["resume"], 75)
        self.assertEqual(package["ats"]["target"], 75)
        self.assertEqual(package["generation_calls"], 6)  # 5 main + keywords
        self.assertAlmostEqual(package["cost_usd"], round(6 * (1000 * 5 + 500 * 25) / 1e6, 4))

        run_dir = package["run_dir"]
        self.assertEqual(sorted(f for f in os.listdir(run_dir) if f.endswith(".pdf")),
                         ["application_strategy.pdf", "ats_report.pdf", "cover_letter.pdf",
                          "evidence_map.pdf", "resume_designed.pdf", "tailored_resume.pdf"])
        for name in (gen.ATS_FILE, gen.SOURCES_FILE, "run.json"):
            self.assertTrue(os.path.isfile(os.path.join(run_dir, name)), name)
        self.assertEqual(set(package["files"]),
                         {"resume", "resume_designed", "cover_letter", "evidence_map",
                          "strategy", "ats_report"})
        # sources.json names the upload copy only; the designed copy derives
        # from it. The kept draft is the reworded one.
        with open(os.path.join(run_dir, gen.SOURCES_FILE)) as handle:
            sources = json.load(handle)
        self.assertEqual(sources["resume"]["file"], "tailored_resume.pdf")
        self.assertIn("SQL reporting", sources["resume"]["markdown"])
        with open(os.path.join(run_dir, gen.ATS_FILE)) as handle:
            data = json.load(handle)
        # The variant leads: the draft already says "roadmap", so rewording it
        # to "product roadmap" adds no claim. Then the bank-mentioned terms.
        self.assertEqual(data["rephrasing_pass"],
                         {"considered": 3, "before": 0, "after": 75, "kept": True,
                          "terms": ["product roadmap", "llm evaluation", "sql"]})
        self.assertEqual(data["resume"]["score"], 75)
        self.assertEqual(len(data["keywords"]), 5)
        with open(os.path.join(run_dir, "run.json")) as handle:
            meta = json.load(handle)
        self.assertEqual(meta["ats"]["resume"], 75)
        self.assertIsNotNone(meta["generation_usd"])
        with open(os.path.join(run_dir, gen.SOURCES_FILE)) as handle:
            self.assertNotIn("ats_report", json.load(handle))

    def test_no_second_model_reads_the_resume(self):
        """No review and no revision: the resume costs one call, two at most."""
        fake = Fake()
        package = self.run_pipeline(fake)
        self.assertEqual(sorted(set(fake.steps)),
                         ["cover_letter", "evidence_map", "phrasing", "resume", "strategy"])
        self.assertFalse(os.path.exists(os.path.join(package["run_dir"], "factuality_review.pdf")))

    def test_a_failed_designed_copy_never_costs_the_run(self):
        """The designed copy is rendered after every model call has been paid
        for, so a failure there must leave the rest of the run intact."""
        real_fit = gen.fit_pdf

        def fit(markdown_text, path, style, **kwargs):
            if style == "resume_designed":
                raise RuntimeError("layout broke")
            return real_fit(markdown_text, path, style, **kwargs)

        with mock.patch.object(gen, "fit_pdf", fit):
            package = self.run_pipeline(Fake())
        run_dir = package["run_dir"]
        self.assertFalse(os.path.exists(os.path.join(run_dir, "resume_designed.pdf")))
        for name in ("tailored_resume.pdf", "cover_letter.pdf", "ats_report.pdf",
                     "run.json", gen.SOURCES_FILE):
            self.assertTrue(os.path.isfile(os.path.join(run_dir, name)), name)
        self.assertNotIn("resume_designed", package["files"])
        self.assertTrue(any("resume_designed.pdf could not be written" in line
                            for line in self.progress))

    def test_no_rephrasing_when_already_at_target(self):
        fake = Fake(resume=FULL)
        package = self.run_pipeline(fake)
        self.assertNotIn("phrasing", fake.steps)
        self.assertEqual(package["ats"]["resume"], 100)
        self.assertEqual(package["generation_calls"], 5)

    def test_no_rephrasing_when_there_is_nothing_honest_to_offer(self):
        """No variant on the page and nothing in the bank: no call is spent."""
        fake = Fake(resume=BARE)
        with mock.patch.object(gen, "BANK_PROSE", "unrelated work entirely"):
            package = self.run_pipeline(fake)
        self.assertNotIn("phrasing", fake.steps)
        self.assertEqual(package["ats"]["resume"], 0)

    def test_a_variant_alone_justifies_the_pass(self):
        """A variant is already claimed on the page, so it needs no bank check."""
        fake = Fake()
        with mock.patch.object(gen, "BANK_PROSE", "unrelated work entirely"):
            self.run_pipeline(fake)
        self.assertIn("phrasing", fake.steps)
        self.assertIn('"roadmap" -> "product roadmap"', fake.inputs["phrasing"][1])
        self.assertNotIn("NOT YET USED", fake.inputs["phrasing"][1])

    def test_reworded_draft_dropped_when_it_does_not_score_higher(self):
        fake = Fake(reworded=DRAFT)
        package = self.run_pipeline(fake)
        self.assertIn("phrasing", fake.steps)
        with open(os.path.join(package["run_dir"], gen.SOURCES_FILE)) as handle:
            kept = json.load(handle)["resume"]["markdown"]
        self.assertIn("Owned the roadmap for the evaluation suite", kept)
        self.assertEqual(package["ats"]["resume"], 0)

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
        """The posting rides in the cached run context, not the user turn."""
        fake = Fake(resume=FULL)
        self.run_pipeline(fake)
        instructions, user, context = fake.inputs["resume"]
        self.assertIn("JD text", context)
        self.assertIn("Acme raised money", context)
        self.assertNotIn("JD text", user)
        self.assertIn("ATS KEYWORDS", instructions)
        self.assertIn("ATS KEYWORDS", fake.inputs["cover_letter"][0])
        self.assertNotIn("ATS KEYWORDS", fake.inputs["strategy"][0])

    def test_writers_are_told_up_front_which_terms_the_bank_uses(self):
        """Fewer rephrasing calls: the first draft already knows the easy wins."""
        fake = Fake(resume=FULL)
        self.run_pipeline(fake)
        for step in ("resume", "cover_letter"):
            instructions = fake.inputs[step][0]
            self.assertIn("THE BANK USES THESE WORDS", instructions, step)
            self.assertIn("THE BANK NEVER USES THESE WORDS", instructions, step)
        used = fake.inputs["resume"][0].split("THE BANK NEVER USES")[0]
        self.assertIn("sql", used)
        self.assertNotIn("kubernetes", used)

    def test_the_documents_everything_waits_on_are_bounded(self):
        """Output tokens are the slow, expensive ones, and the evidence map is
        on every run's critical path."""
        flat = lambda text: " ".join(text.split())
        self.assertIn("At most 12 rows", flat(gen.EVIDENCE_MAP_PROMPT))
        self.assertIn("Every cell is a phrase, not a sentence", flat(gen.EVIDENCE_MAP_PROMPT))
        self.assertIn("give six", flat(gen.STRATEGY_PROMPT))
        self.assertIn("about 700 words in all", flat(gen.STRATEGY_PROMPT))

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
        client, _ = self.call("resume", model="claude-haiku-4-5", context="")
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
        client, _ = self.call("evidence_map")
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
            for step in ("evidence_map", "resume", "strategy"):
                client, _ = self.call(step)
                call = client.calls[-1]
                self.assertFalse(call["beta"])
                sent.append(call["output_config"])
        self.assertEqual(sent, [{"effort": "low"}] * 3)


if __name__ == "__main__":
    unittest.main()
