"""Tenure: computed from the bank's role dates, phrased as favourably as is true."""

import unittest
from datetime import datetime

import ats
import application_generator as gen

TODAY = datetime(2026, 11, 16)
BANK = {"roles": [
    {"company": "Bigbank", "title": "AI Product Manager, Senior Associate", "dates": "March 2026 - Present"},
    {"company": "Market", "title": "Product Manager", "dates": "October 2022 - November 2025"},
    {"company": "Streamco", "title": "Associate Consulting Engineer", "dates": "June 2021 - October 2022"},
]}


class Arithmetic(unittest.TestCase):
    def test_months_inclusive_gaps_not_counted(self):
        t = gen.tenure(BANK, TODAY)
        self.assertEqual(t["pm_months"], 9 + 38)
        # October 2022 is in two roles; it counts once.
        self.assertEqual(t["total_months"], 9 + 38 + 17 - 1)
        self.assertEqual(t["total_years_floor"], 5)

    def test_phrases_never_round_up(self):
        self.assertEqual(gen._years_phrase(63), "5+ years")
        self.assertEqual(gen._years_phrase(47), "nearly 4 years")
        self.assertEqual(gen._years_phrase(17), "nearly 1.5 years")
        self.assertEqual(gen._years_phrase(19), "1.5+ years")
        self.assertEqual(gen._years_phrase(48), "4 years")
        self.assertEqual(gen._years_phrase(8), "8 months")

    def test_the_block_gives_the_split(self):
        block = gen.tenure_block(BANK, TODAY)
        self.assertIn('total industry experience: 5 years 3 months (e.g. "5+ years")', block)
        self.assertIn('of which product management: 3 years 11 months (e.g. "nearly 4 years")', block)
        self.assertIn("Phrase them however", block)
        self.assertIn("nearly 1.5 years as Associate Consulting Engineer, Streamco", block)

    def test_the_block_is_in_every_writing_prompt(self):
        self.assertIn("TENURE —", gen.STABLE_PREFIX)


class Framing(unittest.TestCase):
    def test_ground_rules_teach_the_total_with_the_split(self):
        rules = " ".join(gen.GROUND_RULES.split())
        self.assertIn("HOW TO PHRASE A FACT IS YOUR JUDGEMENT", rules)
        self.assertIn("Whenever two phrasings are both true, choose the more favourable one", rules)
        self.assertIn("not templates to copy", rules)
        self.assertIn('"5+ years of PM experience" is false', rules)
        self.assertIn("The one limit is truth", rules)
        self.assertIn("You may never manufacture a number", rules)

    def test_the_rephrasing_pass_may_improve_framing(self):
        prompt = " ".join(gen.PHRASING_PROMPT.split())
        self.assertIn("its framing is also yours to judge", prompt)
        self.assertIn("change a fact", prompt)


class Offer(unittest.TestCase):
    def kw(self, term):
        return {"term": term, "category": "credential", "importance": "required", "aliases": []}

    def test_tenure_met_by_total_is_offered(self):
        offered = ats.rephrase_offer([], [], [self.kw("5+ years")], max_years=5)
        self.assertEqual([k["term"] for k in offered], ["5+ years"])
        block = ats.rephrase_block(offered)
        self.assertIn("your judgement", block)
        self.assertIn('"5+ years of PM experience" is not', block)

    def test_tenure_beyond_total_is_never_offered(self):
        self.assertEqual(ats.rephrase_offer([], [], [self.kw("7+ years")], max_years=5), [])

    def test_without_a_known_total_nothing_is_offered(self):
        self.assertEqual(ats.rephrase_offer([], [self.kw("5+ years")]), [])

    def test_the_resume_phrasing_scores(self):
        text = "Product manager with 5+ years of industry experience, nearly 4 in product management."
        self.assertEqual(ats.score([dict(self.kw("5+ years"))], text)["score"], 100)


if __name__ == "__main__":
    unittest.main()
