"""The ATS scorer is plain Python, so it is tested as plain Python.

Run with:  python -m unittest

No model is called anywhere in this file. The keyword lists are hand-written
in the shape extract_keywords() produces.
"""

import os
import tempfile
import unittest

import ats
from documents import fit_pdf


def kw(term, category="hard_skill", importance="required", aliases=()):
    return {"term": term, "category": category, "importance": importance,
            "aliases": list(aliases)}


KEYWORDS = [
    kw("product roadmap", aliases=["roadmap"]),
    kw("sql", "tool"),
    kw("llm evaluation", aliases=["llm evals"]),
    kw("a/b testing", importance="preferred", aliases=["a/b tests"]),
    kw("kubernetes", "tool", "mentioned"),
    kw("cross-functional collaboration", "soft_skill", "preferred",
       aliases=["cross functional"]),
    kw("api", "tool", "required"),
    kw("c++", "tool", "mentioned"),
]

RESUME = """# Jane Example
**Senior Product Manager**
New York · jane@example.com · 555-0100 · linkedin.com/in/example

## Profile
Product manager who owns the roadmap for an evaluation platform and ships with
engineering every week.

## Skills
- Product roadmaps
- LLM evals
- SQL
- A/B tests

## Experience
### Senior Product Manager — Acme | 2022 – Present
- Owned the product roadmap for the evaluation suite used by 40 teams.
- Ran A/B tests on onboarding; activation rose 12%.
- Built the LLM evaluation rubric and the SQL reporting behind it.

### Product Manager — Widgets | 2020 – 2022
- Shipped public API integrations with three partners.
- Rapid iteration with a cross functional team of 6.

## Education
**BS Computer Science**
State University · 2016 – 2020
"""


class Normalization(unittest.TestCase):
    def test_folds_punctuation_and_case(self):
        self.assertEqual(ats._norm("A/B-Testing & LLMs"), "a b testing and llms")

    def test_keeps_plus_and_hash(self):
        self.assertEqual(ats._norm("C++ and C#"), "c++ and c#")

    def test_unicode_dashes(self):
        self.assertEqual(ats._norm("cross–functional"), "cross functional")


class Matching(unittest.TestCase):
    def count(self, term, text, aliases=()):
        return ats._count(kw(term, aliases=aliases), ats._norm(text))

    def test_whole_phrase_only(self):
        self.assertEqual(self.count("api", "rapid growth"), 0)
        self.assertEqual(self.count("api", "public API integrations"), 1)

    def test_plural_and_singular(self):
        self.assertEqual(self.count("product roadmap", "owned product roadmaps"), 1)
        self.assertEqual(self.count("a/b testing", "ran A/B testing weekly"), 1)

    def test_alias_counts(self):
        self.assertEqual(self.count("llm evaluation", "LLM evals", aliases=["llm evals"]), 1)
        self.assertEqual(self.count("llm evaluation", "LLM evals"), 0)

    def test_special_characters(self):
        self.assertEqual(self.count("c++", "wrote C++ and C"), 1)
        self.assertEqual(self.count("c++", "wrote C and Go"), 0)

    def test_short_terms_do_not_swallow_longer_words(self):
        """A posting asking for Go must not match a resume that says "goes"."""
        for term, text in [("go", "when the feature goes live"),
                           ("us", "the team uses Jira"),
                           ("hr", "10 hrs per month"),
                           ("do", "what the model does")]:
            self.assertEqual(self.count(term, text), 0, (term, text))
        self.assertEqual(self.count("go", "shipped in Go and Python"), 1)

    def test_plus_and_hash_are_part_of_the_word(self):
        """Otherwise the term "c" matches C++, C# and CS."""
        for text in ("wrote C++ and Java", "fluent in C#", "a BS in CS"):
            self.assertEqual(self.count("c", text), 0, text)
        self.assertEqual(self.count("c", "wrote C and assembly"), 1)

    def test_plural_only_on_the_last_word(self):
        self.assertEqual(self.count("product roadmap", "owned product roadmaps"), 1)
        self.assertEqual(self.count("product roadmap", "products roadmap"), 0)

    def test_irregular_plurals(self):
        for term, text in [("strategy", "owned pricing strategies"),
                           ("analysis", "ran cohort analyses"),
                           ("priority", "set priorities"),
                           ("company", "three companies"),
                           ("process", "mapped the processes")]:
            self.assertEqual(self.count(term, text), 1, (term, text))

    def test_possessives(self):
        self.assertEqual(self.count("bachelor's degree", "Bachelors degree in CS"), 1)
        self.assertEqual(self.count("bachelors degree", "a Bachelor's degree"), 1)

    def test_arrow_spellings_are_one_term(self):
        """0->1, 0→1 and 0-to-1 are the same claim written three ways."""
        for text in ("0->1 product ownership", "0\u21921 ownership", "0-to-1 work"):
            self.assertEqual(self.count("0-to-1", text), 1, text)
        self.assertEqual(self.count("0->1", "took it 0-to-1"), 1)

    def test_overlapping_aliases_count_once(self):
        """"product roadmap" with alias "roadmap" must not count twice."""
        text = "Owned the product roadmap. The roadmap shipped."
        self.assertEqual(self.count("product roadmap", text, aliases=["roadmap"]), 2)


class Scoring(unittest.TestCase):
    def test_an_alias_that_is_another_keyword_is_dropped(self):
        parsed = ats.parse_keywords(
            '{"keywords": ['
            '{"term": "product roadmap", "aliases": ["roadmap"]},'
            '{"term": "roadmap"}]}')
        self.assertEqual(parsed["keywords"][0]["aliases"], [])
        scored = ats.score(parsed["keywords"], "I owned the roadmap.")
        self.assertEqual(scored["score"], 50)   # one of the two terms, not both

    def test_weighted_coverage(self):
        scored = ats.score(KEYWORDS, RESUME)
        matched = {m["term"] for m in scored["matched"]}
        self.assertEqual(matched, {"product roadmap", "sql", "llm evaluation", "api"})
        # The resume says "A/B tests" and "cross functional": the aliases, not
        # the posting's words. A search for the posting's term misses them.
        self.assertEqual({(v["term"], v["used"]) for v in scored["variants"]},
                         {("a/b testing", "a/b tests"),
                          ("cross-functional collaboration", "cross functional")})
        missing = [m["term"] for m in scored["missing"]]
        self.assertEqual(missing, ["c++", "kubernetes"])
        # weights: roadmap 3, sql 3, llm eval 3, a/b 2, k8s 1, soft 2*0.5=1, api 3, c++ 1
        # matched exactly: 3+3+3+3 = 12 of 17
        self.assertEqual(scored["score"], round(100 * 12 / 17))
        self.assertEqual(scored["by_category"]["soft_skill"], 0)
        self.assertEqual(scored["by_category"]["credential"], None)

    def test_an_alias_alone_is_a_variant_not_a_match(self):
        keyword = kw("llm evaluation", aliases=["llm evals"])
        scored = ats.score([keyword], "Ran LLM evals weekly.")
        self.assertEqual(scored["score"], 0)
        self.assertEqual(scored["variants"][0]["used"], "llm evals")
        self.assertEqual(scored["missing"], [])

    def test_the_exact_term_wins_over_an_alias(self):
        keyword = kw("llm evaluation", aliases=["llm evals"])
        scored = ats.score([keyword], "Ran LLM evals and owned LLM evaluation.")
        self.assertEqual(scored["score"], 100)
        self.assertEqual(scored["variants"], [])
        self.assertEqual(scored["matched"][0]["count"], 2)   # both forms still count as mentions

    def test_missing_sorted_by_weight(self):
        scored = ats.score(KEYWORDS, "nothing relevant here")
        weights = [m["weight"] for m in scored["missing"]]
        self.assertEqual(weights, sorted(weights, reverse=True))
        self.assertEqual(scored["score"], 0)

    def test_no_keywords(self):
        self.assertIsNone(ats.score([], RESUME)["score"])

    def test_stuffing_flag(self):
        text = "sql " * (ats.STUFFING_LIMIT + 1)
        scored = ats.score([kw("sql", "tool")], text)
        self.assertEqual([m["term"] for m in scored["stuffed"]], ["sql"])

    def test_overlapping_aliases_do_not_fake_a_stuffing_flag(self):
        """Three mentions counted twice each would read as repetition."""
        scored = ats.score(KEYWORDS, RESUME)
        roadmap = [m for m in scored["matched"] if m["term"] == "product roadmap"][0]
        self.assertEqual(roadmap["count"], 3)
        self.assertEqual(scored["stuffed"], [])

    def test_summary_shape(self):
        summary = ats.summary(ats.score(KEYWORDS, RESUME))
        self.assertEqual(set(summary), {"score", "matched", "variants", "missing"})


class Parsing(unittest.TestCase):
    def test_tolerates_fence_and_prose(self):
        text = ('Here you go:\n```json\n{"title": "Senior PM", "keywords": ['
                '{"term": "SQL", "category": "tool", "importance": "required", "aliases": ["sql"]},'
                '{"term": "sql", "category": "tool", "importance": "required"},'
                '{"term": "Roadmap", "category": "nonsense", "importance": "whatever", "aliases": 5},'
                '"junk"]}\n```')
        parsed = ats.parse_keywords(text)
        self.assertEqual(parsed["title"], "Senior PM")
        self.assertEqual([k["term"] for k in parsed["keywords"]], ["sql", "roadmap"])
        self.assertEqual(parsed["keywords"][0]["aliases"], [])          # same as the term
        self.assertEqual(parsed["keywords"][1]["category"], "domain")   # unknown -> domain
        self.assertEqual(parsed["keywords"][1]["importance"], "mentioned")

    def test_rejects_no_json(self):
        with self.assertRaises(ValueError):
            ats.parse_keywords("I could not find any keywords.")

    def test_caps_the_list(self):
        many = ",".join(f'{{"term": "term {i}"}}' for i in range(ats.MAX_KEYWORDS + 10))
        parsed = ats.parse_keywords('{"keywords": [' + many + "]}")
        self.assertEqual(len(parsed["keywords"]), ats.MAX_KEYWORDS)


class BankGate(unittest.TestCase):
    BANK = {
        "roles": [{"company": "Acme", "projects": [
            {"name": "Evals", "summary": "Built the LLM evaluation rubric",
             "label_rule": "Never describe this as production scale",
             "use_when": "cross-cultural communication matters",
             "metrics": [{"claim": "SQL reporting cut turnaround",
                          "source": "verified_resume", "type": "verified_metric",
                          "caveat": "Do not present it as a measured outcome"},
                         {"claim": "Kubernetes migration finished",
                          "source": "needs_validation"}]},
        ]}],
        "skills": {"tools": ["SQL"]},
        "identity": {"experience_length": "Never write '6 years of PM experience'",
                     "email": "someone@example.com"},
    }

    def test_prose_skips_unvalidated_and_keys(self):
        prose = ats.bank_prose(self.BANK)
        self.assertIn("llm evaluation rubric", prose)
        self.assertIn("sql reporting", prose)
        self.assertNotIn("kubernetes", prose)
        self.assertNotIn("metrics", prose)   # keys are vocabulary, not evidence

    def test_provenance_labels_are_not_evidence(self):
        """"supported_inference" must not make "inference" a supported term."""
        prose = ats.bank_prose(self.BANK)
        for label in ("verified", "inference", "verified metric"):
            self.assertEqual(ats._count(kw(label), prose), 0, label)

    def test_the_bank_s_own_prohibitions_are_not_evidence(self):
        """The rule forbidding a claim must never be read as making it."""
        prose = ats.bank_prose(self.BANK)
        for forbidden in ("production", "6 years", "measured outcome"):
            self.assertEqual(ats._count(kw(forbidden), prose), 0, forbidden)

    def test_guidance_about_when_to_use_a_claim_is_not_evidence(self):
        prose = ats.bank_prose(self.BANK)
        self.assertEqual(ats._count(kw("cross-cultural communication"), prose), 0)

    def test_contact_details_stay_out(self):
        self.assertNotIn("example.com", ats.bank_prose(self.BANK))

    def test_the_real_bank_does_not_leak_labels(self):
        import application_generator as gen
        for leak in ("inference", "verified", "6 years", "production"):
            self.assertEqual(ats._count(kw(leak), gen.BANK_PROSE), 0, leak)
        self.assertGreater(len(gen.BANK_PROSE), 5000)   # still full of real evidence

    def test_split(self):
        missing = ats.score(KEYWORDS, "")["missing"]
        candidates, gaps = ats.bank_supported(missing, ats.bank_prose(self.BANK))
        self.assertEqual({k["term"] for k in candidates}, {"sql", "llm evaluation"})
        self.assertIn("kubernetes", {k["term"] for k in gaps})


class PromptMaterial(unittest.TestCase):
    def test_empty_without_keywords(self):
        self.assertEqual(ats.prompt_block({"title": "x", "keywords": []}), "")
        self.assertEqual(ats.prompt_block(None), "")

    def test_groups_by_importance_and_forbids_stuffing(self):
        block = ats.prompt_block({"title": "Senior PM", "keywords": KEYWORDS})
        self.assertIn("required:", block)
        self.assertIn("preferred:", block)
        self.assertIn("mentioned:", block)
        self.assertIn('"Senior PM"', block)
        self.assertIn("Never add a term the experience bank does not earn", block)

    def test_rephrase_offer_puts_variants_first_and_caps(self):
        variants = [dict(kw(f"variant {i}"), used=f"v{i}") for i in range(3)]
        candidates = [kw(f"term {i}") for i in range(20)]
        offered = ats.rephrase_offer(variants, candidates)
        self.assertEqual(len(offered), ats.MAX_REPHRASE_TERMS)
        self.assertEqual([k["term"] for k in offered[:3]], ["variant 0", "variant 1", "variant 2"])

    def test_rephrase_block_names_the_form_to_replace(self):
        block = ats.rephrase_block([dict(kw("llm evaluation"), used="llm evals"),
                                    kw("sql", "tool")])
        self.assertIn('SAID IN A DIFFERENT FORM', block)
        self.assertIn('"llm evals" -> "llm evaluation"', block)
        self.assertIn("NOT YET USED, BUT THE BANK MENTIONS THE WORK", block)
        self.assertIn("- sql", block)

    def test_rephrase_block_omits_an_empty_group(self):
        self.assertNotIn("SAID IN A DIFFERENT FORM", ats.rephrase_block([kw("sql")]))


class Checks(unittest.TestCase):
    def test_title_line(self):
        self.assertEqual(ats.resume_title(RESUME), "Senior Product Manager")
        match = ats.title_match("Senior Product Manager, AI Platform", RESUME)
        self.assertEqual(match["shared"], ["senior", "product", "manager"])
        self.assertAlmostEqual(match["ratio"], 3 / 5)

    def test_title_match_without_posting_title(self):
        self.assertIsNone(ats.title_match("", RESUME)["ratio"])

    def test_format_checks_on_a_sound_resume(self):
        checks = {c["check"]: c for c in ats.format_checks(RESUME)}
        self.assertTrue(checks["Standard section headings"]["ok"])
        self.assertTrue(checks["Contact line under the name"]["ok"])
        self.assertTrue(checks["Dates on every role"]["ok"])
        self.assertTrue(checks["Bullets with a number in them"]["ok"])
        self.assertFalse(checks["Length for a one-page parse"]["ok"])  # this fixture is short

    def test_contact_check_does_not_count_the_profile_paragraph(self):
        """It can only pass on prose between the name and the first section."""
        no_contact = ("# Jane\n**Senior PM**\n\n## Profile\nA paragraph of prose.\n\n"
                      "## Skills\n- x\n\n## Experience\n### R — C | 2020\n- b\n\n"
                      "## Education\n**BS**\nU\n")
        checks = {c["check"]: c for c in ats.format_checks(no_contact)}
        self.assertFalse(checks["Contact line under the name"]["ok"])
        self.assertTrue({c["check"]: c for c in ats.format_checks(RESUME)}
                        ["Contact line under the name"]["ok"])

    def test_format_checks_catch_missing_dates_and_sections(self):
        text = "# A\n**T**\ncontact\n\n## Experience\n### Role — Co\n- did x\n"
        checks = {c["check"]: c for c in ats.format_checks(text)}
        self.assertFalse(checks["Standard section headings"]["ok"])
        self.assertIn("skills", checks["Standard section headings"]["detail"])
        self.assertFalse(checks["Dates on every role"]["ok"])

    def test_terms_survive_the_two_column_pdf(self):
        """A screener reads the PDF. The matched terms must come back out of it."""
        scored = ats.score(KEYWORDS, RESUME)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "resume.pdf")
            fit_pdf(RESUME, path, "resume")
            result = ats.pdf_text_check(path, scored["matched"])
        self.assertTrue(result["ok"], result)

    def test_pdf_check_on_unreadable_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "nope.pdf")
            with open(path, "w") as handle:
                handle.write("not a pdf")
            result = ats.pdf_text_check(path, [kw("sql")])
        self.assertFalse(result["ok"])
        self.assertEqual(result["lost"], ["sql"])


class ExactTitle(unittest.TestCase):
    """The posting's title, word for word, is what a recruiter's search finds."""

    def headline(self, title, summary="Product manager."):
        return f"# J\n**{title}**\nNYC\n\n## Summary\n{summary}\n"

    def test_core_title_drops_the_qualifier(self):
        self.assertEqual(ats.core_title("Senior Product Manager, AI Platform"),
                         "Senior Product Manager")
        self.assertEqual(ats.core_title("Product Manager - Payments (Remote)"), "Product Manager")
        self.assertEqual(ats.core_title("Staff PM"), "Staff PM")

    def test_the_full_title_is_exact(self):
        match = ats.title_match("Senior Product Manager, AI Platform",
                                self.headline("Senior Product Manager, AI Platform"))
        self.assertTrue(match["exact"])
        self.assertTrue(match["full"])

    def test_the_core_alone_is_still_exact(self):
        match = ats.title_match("Senior Product Manager, AI Platform",
                                self.headline("Senior Product Manager"))
        self.assertTrue(match["exact"])
        self.assertFalse(match["full"])

    def test_a_paraphrase_is_not(self):
        """"Product Lead" shares no search with "Senior Product Manager"."""
        for headline in ("Product Lead", "AI Product Manager", "Senior Product Lead"):
            match = ats.title_match("Senior Product Manager", self.headline(headline))
            self.assertFalse(match["exact"], headline)

    def test_the_summary_is_checked_too(self):
        yes = ats.title_match("Senior Product Manager", self.headline(
            "Senior Product Manager", "Senior Product Manager with four years of PM work."))
        no = ats.title_match("Senior Product Manager", self.headline("Senior Product Manager"))
        self.assertTrue(yes["in_summary"])
        self.assertFalse(no["in_summary"])

    def test_the_profile_heading_counts_as_a_summary(self):
        md = "# J\n**PM**\nNYC\n\n## Profile\nSenior Product Manager who ships.\n"
        self.assertTrue(ats.title_match("Senior Product Manager", md)["in_summary"])


class Headings(unittest.TestCase):
    def check(self, md):
        return {c["check"]: c for c in ats.format_checks(md)}["Standard section headings"]

    def test_standard_synonyms_pass(self):
        md = ("# J\n**T**\nNYC\n\n## Professional Summary\nx\n\n## Technical Skills\n- x\n\n"
              "## Experience\n### R — C | May 2020 - Present\n- b\n\n## Education\nx\n")
        self.assertTrue(self.check(md)["ok"], self.check(md))

    def test_a_creative_heading_is_flagged_by_name(self):
        md = RESUME.replace("## Skills", "## Toolkit")
        result = self.check(md)
        self.assertFalse(result["ok"])
        self.assertIn('non-standard: "toolkit"', result["detail"])
        self.assertIn("missing: skills", result["detail"])

    def test_my_journey_instead_of_experience(self):
        md = RESUME.replace("## Experience", "## My Journey")
        self.assertIn('"my journey"', self.check(md)["detail"])


class Dates(unittest.TestCase):
    def check(self, md):
        return {c["check"]: c for c in ats.format_checks(md)}["One date format throughout"]

    def test_date_format_names(self):
        cases = {"March 2026": "Month YYYY", "Mar 2026": "Mon YYYY", "Sept. 2020": "Mon YYYY",
                 "03/2026": "MM/YYYY", "2026-03": "YYYY-MM", "2020": "YYYY",
                 "January '19": "Mon 'YY", "Present": "present", "Spring 2020": "other"}
        for token, expected in cases.items():
            self.assertEqual(ats.date_format(token), expected, token)

    def test_one_format_passes(self):
        self.assertTrue(self.check(RESUME)["ok"])

    def test_mixed_formats_are_caught(self):
        """The post's example: "Jan 2019", "2019-01" and "January '19" in one resume."""
        md = RESUME.replace("2022 – Present", "Jan 2022 - Present").replace(
            "2020 – 2022", "2020-01 - January '22")
        result = self.check(md)
        self.assertFalse(result["ok"])
        self.assertIn("mixed", result["detail"])

    def test_a_bare_year_in_education_is_allowed(self):
        """No month is known for it, and education does not count toward tenure."""
        md = ("# J\n**T**\nNYC\n\n## Work Experience\n### R — C | March 2026 - Present\n- b\n\n"
              "## Education\n**Bootcamp**\nFlatiron School · 2020\n")
        self.assertTrue(self.check(md)["ok"], self.check(md))

    def test_a_different_month_style_in_education_is_not(self):
        md = ("# J\n**T**\nNYC\n\n## Work Experience\n### R — C | March 2026 - Present\n- b\n\n"
              "## Education\n**BA**\nColumbia · Sep 2015 - May 2019\n")
        self.assertFalse(self.check(md)["ok"])


class Glyphs(unittest.TestCase):
    def test_icons_and_emoji_are_found(self):
        for ch in ("\u260e", "\u2709", "\u2605", "\u2714", "\U0001F4E7", "\U0001F680"):
            self.assertEqual(ats.decorative_characters(f"call {ch} me"), [ch], hex(ord(ch)))

    def test_ordinary_punctuation_is_not(self):
        text = "NYC · a@b.com | 555 — Senior – PM • ~40% & A/B (x) 0->1 \"q\" 'q'"
        self.assertEqual(ats.decorative_characters(text), [])

    def test_the_check_names_the_code_point(self):
        md = RESUME.replace("555-0100", "\u260e 555-0100")
        check = {c["check"]: c for c in ats.format_checks(md)}["No icons or emoji"]
        self.assertFalse(check["ok"])
        self.assertEqual(check["detail"], "U+260E")


class Report(unittest.TestCase):
    def test_full_report(self):
        extracted = {"title": "Senior Product Manager", "keywords": KEYWORDS}
        resume = ats.score(KEYWORDS, RESUME)
        letter = ats.score(KEYWORDS, "I have owned a product roadmap.")
        candidates, gaps = [resume["missing"][0]], resume["missing"][1:]
        text = ats.report(
            extracted, resume, letter, 75, candidates, gaps, ats.format_checks(RESUME),
            ats.title_match(extracted["title"], RESUME),
            {"ok": True, "lost": [], "detail": "6 of 6 matched terms readable"},
            {"considered": 2, "before": 40, "after": 62, "kept": True},
        )
        self.assertIn(f"## Resume — {resume['score']} / 100", text)
        self.assertIn("## Cover letter — ", text)
        self.assertIn("Not in the experience bank", text)
        self.assertIn("40 → 62", text)
        self.assertIn("| Hard skills |", text)

    def test_report_does_not_claim_a_pass_that_never_ran(self):
        resume = ats.score(KEYWORDS, RESUME)
        text = ats.report({"title": "", "keywords": KEYWORDS}, resume, None, 75,
                          resume["missing"], [], [], ats.title_match("", RESUME),
                          {"ok": True, "lost": [], "detail": ""}, None)
        self.assertIn("No rephrasing pass ran", text)
        self.assertNotIn("could not work them in", text)

    def test_report_separates_offered_terms_from_unoffered_ones(self):
        resume = ats.score(KEYWORDS, "nothing here")
        candidates = resume["missing"]
        pass_info = {"considered": 1, "before": 0, "after": 0, "kept": True,
                     "terms": [candidates[0]["term"]]}
        text = ats.report({"title": "", "keywords": KEYWORDS}, resume, None, 75,
                          candidates, [], [], ats.title_match("", RESUME),
                          {"ok": True, "lost": [], "detail": ""}, pass_info)
        self.assertIn("could not work them in", text)
        self.assertIn("never offered to it", text)
        self.assertIn(candidates[1]["term"], text)

    def test_report_does_not_blame_a_discarded_pass_on_the_terms(self):
        resume = ats.score(KEYWORDS, "nothing here")
        pass_info = {"considered": 2, "before": 10, "after": 10, "kept": False,
                     "terms": [k["term"] for k in resume["missing"][:2]]}
        text = ats.report({"title": "", "keywords": KEYWORDS}, resume, None, 75,
                          resume["missing"][:2], [], [], ats.title_match("", RESUME),
                          {"ok": True, "lost": [], "detail": ""}, pass_info)
        self.assertIn("not known not to fit", text)

    def test_report_says_nothing_when_there_are_no_candidates(self):
        resume = ats.score(KEYWORDS, RESUME)
        text = ats.report({"title": "", "keywords": KEYWORDS}, resume, None, 75,
                          [], resume["missing"], [], ats.title_match("", RESUME),
                          {"ok": True, "lost": [], "detail": ""}, None)
        self.assertNotIn("No rephrasing pass ran", text)

    def test_report_shows_variants_and_counts_exact_terms(self):
        resume = ats.score(KEYWORDS, RESUME)
        text = ats.report({"title": "Senior Product Manager", "keywords": KEYWORDS},
                          resume, None, 75, [], resume["missing"], [],
                          ats.title_match("Senior Product Manager", RESUME),
                          {"ok": True, "lost": [], "detail": ""}, None)
        self.assertIn(f"Posting terms used in the posting's own words: 4 of {len(KEYWORDS)}.", text)
        self.assertIn('**Said in a different form (2):**', text)
        self.assertIn('"a/b tests" where the posting says **a/b testing**', text)
        self.assertIn("carries the posting's title word for word", text)

    def test_report_explains_the_designed_copy(self):
        resume = ats.score(KEYWORDS, RESUME)
        text = ats.report({"title": "", "keywords": KEYWORDS}, resume, None, 75, [], [], [],
                          ats.title_match("", RESUME), {"ok": True, "lost": [], "detail": ""},
                          None, order={"ok": True, "detail": "sections read back in order"},
                          designed={"ok": False, "detail": "3 printed line(s) join two blocks"})
        self.assertIn("Upload copy: sections read back in order.", text)
        self.assertIn("Designed copy (two columns)", text)
        self.assertIn("the one to upload", text)

    def test_report_without_keywords(self):
        text = ats.report({"title": "", "keywords": []}, None, None, 75, [], [], [], {}, {})
        self.assertIn("nothing was scored", text)

    def test_target_score_env(self):
        old = os.environ.get("ATS_TARGET_SCORE")
        try:
            os.environ["ATS_TARGET_SCORE"] = "60"
            self.assertEqual(ats.target_score(), 60)
            os.environ["ATS_TARGET_SCORE"] = "not a number"
            self.assertEqual(ats.target_score(), 75)
        finally:
            if old is None:
                os.environ.pop("ATS_TARGET_SCORE", None)
            else:
                os.environ["ATS_TARGET_SCORE"] = old


if __name__ == "__main__":
    unittest.main()
