"""The contact block a tracking system reads its phone, email and LinkedIn from.

It is written in code from the identity block, not by the model, because the
model dropped fields it judged inessential. Every value here is made up.
"""

import os
import tempfile
import unittest

from pypdf import PdfReader

import ats
import documents
import application_generator as gen

IDENTITY = {"name": "Jane Example", "location": "New York, NY",
            "linkedin": "https://www.linkedin.com/in/jane-example/",
            "portfolio": "jane-example.netlify.app", "portfolio_password": "open-sesame",
            "email": "jane.fiona@example.com", "phone": "(555) 010-0199"}

DRAFT = """# Jane Example
**Senior Product Manager**
New York, NY · linkedin.com/in/jane-example/

## Summary
Senior Product Manager who ships.

## Work Experience
### Product Manager — Acme | March 2022 - Present
- **Eval framework** — Built the rubric.

## Education
**BA Economics**
State University · 2019

## Skills
- SQL
"""


class ContactBlock(unittest.TestCase):
    def test_one_line_in_the_original_order(self):
        self.assertEqual(gen.contact_lines(IDENTITY), [
            "New York, NY · jane.fiona@example.com · (555) 010-0199 · "
            "linkedin.com/in/jane-example · jane-example.netlify.app (password: open-sesame)",
        ])

    def test_blank_fields_are_left_out_not_invented(self):
        sparse = dict(IDENTITY, phone="", email="", portfolio_password="")
        self.assertEqual(gen.contact_lines(sparse), [
            "New York, NY · linkedin.com/in/jane-example · jane-example.netlify.app"])
        self.assertEqual(gen.missing_contact(sparse), ["CANDIDATE_EMAIL", "CANDIDATE_PHONE"])
        self.assertEqual(gen.missing_contact(IDENTITY), [])

    def test_the_model_s_contact_line_is_replaced(self):
        fixed = gen.with_contact(DRAFT, IDENTITY)
        head = fixed.split("## Summary")[0]
        self.assertIn("**Senior Product Manager**", head)
        self.assertIn("jane.fiona@example.com", head)
        self.assertIn("(555) 010-0199", head)
        self.assertEqual(len([l for l in head.splitlines() if "·" in l]), 1)
        self.assertEqual(fixed.split("## Summary")[1], DRAFT.split("## Summary")[1])

    def test_replacing_is_idempotent(self):
        once = gen.with_contact(DRAFT, IDENTITY)
        self.assertEqual(gen.with_contact(once, IDENTITY), once)

    def test_the_prompt_no_longer_owns_the_contact_line(self):
        self.assertIn("rewritten in code from the identity block", gen.RESUME_PROMPT)


class InThePdf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = os.path.join(cls.tmp.name, "resume.pdf")
        cls.md = gen.with_contact(DRAFT, IDENTITY)
        documents.fit_pdf(cls.md, cls.path, "resume")
        cls.page = PdfReader(cls.path).pages[0]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_contact_item_reaches_the_page_whole(self):
        text = " ".join(self.page.extract_text().split())
        for item in ("New York, NY", "jane.fiona@example.com", "(555) 010-0199",
                     "linkedin.com/in/jane-example", "jane-example.netlify.app (password: open-sesame)"):
            self.assertIn(item, text)
        for line in self.page.extract_text().splitlines():
            self.assertFalse(line.rstrip().endswith("(password:"), line)

    def test_each_field_is_also_a_real_link(self):
        uris = [a.get_object()["/A"]["/URI"] for a in self.page.get("/Annots", [])]
        self.assertIn("mailto:jane.fiona@example.com", uris)
        self.assertIn("tel:5550100199", uris)
        self.assertIn("https://linkedin.com/in/jane-example", uris)

    def test_the_pdf_check_passes(self):
        self.assertTrue(ats.pdf_contact_check(self.path)["ok"])

    def test_ligatures_are_off(self):
        self.assertIn('"liga" 0', documents.ATS_CSS(9.6, "0.5in"))


class WholePage(unittest.TestCase):
    """Every word, not only the posting's keywords, has to extract."""

    def test_every_word_of_a_full_resume_extracts(self):
        md = gen.with_contact(DRAFT, IDENTITY)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "resume.pdf")
            documents.fit_pdf(md, path, "resume")
            result = ats.pdf_full_text_check(path, md)
        self.assertTrue(result["ok"], result)

    def test_a_word_missing_from_the_pdf_is_named(self):
        md = gen.with_contact(DRAFT, IDENTITY)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "resume.pdf")
            documents.fit_pdf(md, path, "resume")
            result = ats.pdf_full_text_check(path, md + "\n- Zanzibarian quokka wrangling\n")
        self.assertFalse(result["ok"])
        self.assertIn("zanzibarian", result["detail"])

    def test_a_ligature_counts_as_broken(self):
        self.assertTrue(ats._BROKEN.search("o\ufb03ce"))
        self.assertFalse(ats._BROKEN.search("office · résumé — “quoted”"))


class Checks(unittest.TestCase):
    def test_header_check_names_what_is_missing(self):
        check = {c["check"]: c for c in ats.format_checks(DRAFT)}[
            "Email, phone and LinkedIn under the name"]
        self.assertFalse(check["ok"])
        self.assertEqual(check["detail"], "missing: email, phone")

    def test_header_check_passes_on_the_rebuilt_block(self):
        check = {c["check"]: c for c in ats.format_checks(gen.with_contact(DRAFT, IDENTITY))}[
            "Email, phone and LinkedIn under the name"]
        self.assertTrue(check["ok"])

    def test_a_date_range_is_not_a_phone_number(self):
        self.assertFalse(ats.contact_fields("2019 - 2022")["phone"])
        self.assertTrue(ats.contact_fields("+1 555 010 0199")["phone"])

    def test_unreadable_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.pdf")
            with open(path, "w") as handle:
                handle.write("not a pdf")
            self.assertFalse(ats.pdf_contact_check(path)["ok"])


if __name__ == "__main__":
    unittest.main()
