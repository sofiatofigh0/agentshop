"""Education entries in the experience bank, and how inclusion is governed."""

import unittest

from experience_bank import EXPERIENCE_BANK, PERSONAL_BACKGROUND, missing_fields


def entry(institution):
    return next(e for e in EXPERIENCE_BANK["education"] if e["institution"] == institution)


class Education(unittest.TestCase):
    def test_every_entry_says_when_it_is_listed(self):
        for item in EXPERIENCE_BANK["education"]:
            self.assertIn(item["include"], ("always", "when_relevant"), item["institution"])
            if item["include"] == "when_relevant":
                self.assertTrue(item.get("use_when"), item["institution"])

    def test_flatiron_is_on_every_resume_with_the_year_only(self):
        flatiron = entry("Flatiron School")
        self.assertEqual(flatiron["include"], "always")
        self.assertEqual(flatiron["dates"], "2020")          # no invented month
        self.assertEqual(flatiron["source"], "candidate_provided")
        self.assertIn("Full-Stack", flatiron["credential"])

    def test_the_ib_is_listed_only_where_it_helps(self):
        ib = entry("Tehran International School")
        self.assertEqual(ib["include"], "when_relevant")
        self.assertEqual(ib["location"], "Tehran, Iran")
        self.assertEqual(ib["dates"], "")                    # none given, none invented
        self.assertIn("international", ib["use_when"])

    def test_columbia_is_unchanged(self):
        columbia = entry("Columbia University")
        self.assertEqual(columbia["dates"], "September 2015 - May 2019")
        self.assertEqual(columbia["source"], "verified_resume")
        self.assertEqual(columbia["include"], "always")

    def test_newest_first(self):
        self.assertEqual([e["institution"] for e in EXPERIENCE_BANK["education"]][:2],
                         ["Flatiron School", "Columbia University"])

    def test_the_personal_story_names_the_same_bootcamp(self):
        self.assertIn("Flatiron School", PERSONAL_BACKGROUND["transition_story"]["fact"])

    def test_no_placeholders(self):
        self.assertEqual(missing_fields(), [])


if __name__ == "__main__":
    unittest.main()
