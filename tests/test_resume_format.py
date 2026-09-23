"""The shape of an Experience bullet.

Each bullet opens with the project it is about, in two or three bold words, so
a reviewer scanning the left edge learns what kinds of problems this candidate
has worked on before reading a sentence. Bullets that are not about one
discrete project — ongoing responsibilities, consulting engagements — stay
plain, because a label on those is padding.

The label is a writing instruction, so what can be tested without a model is
everything around it: that the instruction is in the prompt, that the renderer
sets it, that it survives into the PDF, and that it does not disturb scoring.
"""

import os
import re
import tempfile
import unittest

import ats
import documents
from application_generator import PHRASING_PROMPT, RESUME_PROMPT

LABELLED = """# Jane Example
**AI Product Manager**
New York · jane@example.com · 555-0100

## Profile
Product manager for an evaluation platform.

## Skills
- LLM evaluation
- SQL

## Experience
### AI Product Manager — Acme | 2024 – Present
- **Advisor summarization** — Shipped an LLM pipeline that cut meeting prep by ~40%.
- **Eval framework** — Built the rubric and the SQL reporting behind it.

### Consulting Engineer — Streamly | 2021 – 2022
- Advised enterprise banking clients on event-streaming architecture and compliance.

## Education
**BS Computer Science**
State University · 2016 – 2020
"""


class PromptContract(unittest.TestCase):
    """Guards the instruction itself, which nothing else in the suite covers."""

    def test_the_template_shows_a_labelled_bullet(self):
        self.assertIn("- **<project, two or three words>** — ", RESUME_PROMPT)

    def test_the_label_is_two_or_three_words_from_the_bank(self):
        self.assertIn("two or three", RESUME_PROMPT)
        self.assertIn("Never invent", RESUME_PROMPT)

    def test_non_project_bullets_are_exempt(self):
        self.assertIn("Do NOT label a bullet that is not about one discrete project",
                      RESUME_PROMPT)
        self.assertIn("Confluent", RESUME_PROMPT)

    def test_the_rephrasing_pass_may_not_use_a_label_as_a_keyword_slot(self):
        self.assertIn("slot for a keyword", PHRASING_PROMPT)
        self.assertIn("do not add one", PHRASING_PROMPT)


def flat(text):
    """Whitespace-insensitive, so re-wrapping a prompt does not break its contract."""
    return " ".join(text.split())


RESUME = flat(RESUME_PROMPT)


class AtsRules(unittest.TestCase):
    """The parser-facing rules the resume prompt now carries."""

    def test_standard_headings_in_the_template(self):
        for heading in ("## Summary", "## Skills", "## Work Experience", "## Projects",
                        "## Education"):
            self.assertIn(heading, RESUME_PROMPT)
        for retired in ("## Profile", "## Experience\n", "## Selected Projects"):
            self.assertNotIn(retired, RESUME_PROMPT)

    def test_the_title_line_is_the_posting_s_exact_title(self):
        self.assertIn("**<the posting's exact job title", RESUME)
        self.assertIn("word for word", RESUME)
        self.assertIn("Shorten; never paraphrase", RESUME)

    def test_the_title_may_not_overstate_seniority(self):
        self.assertIn("may still not overstate seniority", RESUME)
        self.assertIn('"Director of Product, Payments" becomes "Senior Product Manager, Payments"',
                      RESUME)

    def test_the_summary_repeats_the_title(self):
        self.assertIn("The Summary's first sentence repeats the same title", RESUME)

    def test_dates_icons_urls_and_education_flags(self):
        self.assertIn("Month Year - Month Year", RESUME)
        self.assertIn("No icons, emoji, symbols or decorative characters", RESUME)
        self.assertIn("never as a markdown link", RESUME)
        self.assertIn('include: "always"', RESUME)
        self.assertIn('include: "when_relevant"', RESUME)
        self.assertIn("never invent a month", RESUME)


class Rendering(unittest.TestCase):
    def setUp(self):
        self.html = documents.render_resume_html(LABELLED)
        self.items = re.findall(r"<li>(.*?)</li>", self.html)

    def test_a_label_becomes_bold_inside_the_bullet(self):
        experience = [i for i in self.items if "—" in i]
        self.assertEqual(len(experience), 2)
        for item in experience:
            self.assertRegex(item, r"^<strong>[^<]+</strong> — ")

    def test_an_unlabelled_bullet_renders_plain(self):
        plain = [i for i in self.items if i.startswith("Advised enterprise")]
        self.assertEqual(len(plain), 1)
        self.assertNotIn("<strong>", plain[0])

    def test_labelled_bullets_still_fit_one_page_and_stay_readable(self):
        """A screener reads the PDF, so the label has to survive the render."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "resume.pdf")
            pages, pt = documents.fit_pdf(LABELLED, path, "resume")
            self.assertEqual(pages, 1)
            check = ats.pdf_text_check(path, [{"term": "advisor summarization", "aliases": []},
                                              {"term": "eval framework", "aliases": []}])
        self.assertTrue(check["ok"], check)


class ScoringIsUnaffected(unittest.TestCase):
    def test_the_markup_does_not_break_matching(self):
        """`**` folds to whitespace, so a label reads as ordinary words."""
        bullet = "- **Eval framework** — Built the rubric behind it."
        self.assertEqual(ats._norm(bullet), "eval framework built the rubric behind it")

    def test_a_term_in_a_label_counts_like_a_term_anywhere_else(self):
        keyword = {"term": "llm evaluation", "category": "hard_skill",
                   "importance": "required", "aliases": ["llm eval"]}
        scored = ats.score([keyword], LABELLED)
        self.assertEqual(scored["score"], 100)

    def test_a_label_does_not_invent_coverage(self):
        """Labels name real projects; they cannot make an absent term match."""
        keyword = {"term": "kubernetes", "category": "tool",
                   "importance": "required", "aliases": []}
        self.assertEqual(ats.score([keyword], LABELLED)["score"], 0)


if __name__ == "__main__":
    unittest.main()
