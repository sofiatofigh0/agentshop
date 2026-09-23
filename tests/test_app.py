"""The web server's edit path: save, re-render, re-score."""

import json
import os
import tempfile
import unittest
from unittest import mock

import app as server

RESUME = """# Jane Example
**Senior Product Manager**
New York · jane@example.com

## Profile
Product manager for an evaluation platform.

## Skills
- Roadmaps

## Experience
### Senior Product Manager — Acme | 2022 – Present
- Owned the roadmap for the evaluation suite.

## Education
**BS Computer Science**
State University · 2016 – 2020
"""

LETTER = """# Jane Example
New York

Dear team,

I owned the roadmap.

Jane
"""

KEYWORDS = [
    {"term": "product roadmap", "category": "hard_skill", "importance": "required", "aliases": ["roadmap"]},
    {"term": "sql", "category": "tool", "importance": "required", "aliases": []},
]


class EditRescores(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = "2026-01-01-acme-pm"
        run_dir = os.path.join(self.tmp.name, self.folder)
        os.makedirs(run_dir)
        with open(os.path.join(run_dir, "run.json"), "w") as handle:
            json.dump({"company": "Acme", "role": "PM", "recommendation": "APPLY",
                       "ats": {"resume": 50, "cover_letter": 0, "target": 75}}, handle)
        with open(os.path.join(run_dir, server.SOURCES_FILE), "w") as handle:
            json.dump({"resume": {"file": "tailored_resume.pdf", "style": "resume",
                                  "markdown": RESUME},
                       "cover_letter": {"file": "cover_letter.pdf", "style": "letter",
                                        "markdown": LETTER}}, handle)
        with open(os.path.join(run_dir, server.ATS_FILE), "w") as handle:
            json.dump({"title": "PM", "keywords": KEYWORDS, "target": 75,
                       "resume": {"score": 50, "matched": [], "missing": []}}, handle)
        self.run_dir = run_dir
        patches = [
            mock.patch.object(server, "OUTPUT_DIR", self.tmp.name),
            mock.patch.object(server.lessons, "record",
                              lambda *a, **k: {"lesson": None, "why": "test"}),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.client = server.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_history_carries_the_score(self):
        rows = self.client.get("/api/history").get_json()
        self.assertEqual(rows[0]["ats"]["resume"], 50)
        self.assertTrue(rows[0]["editable"])

    def _report_text(self):
        from pypdf import PdfReader
        path = os.path.join(self.run_dir, "ats_report.pdf")
        return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)

    def test_edit_rebuilds_the_report_so_it_cannot_contradict_the_score(self):
        """The chip and the report the UI links must tell one story."""
        edited = RESUME.replace("Owned the roadmap",
                                "Owned the product roadmap and the SQL reporting")
        response = self.client.put(f"/api/document/{self.folder}/resume",
                                   json={"markdown": edited, "note": ""})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["ats"], 100)
        text = self._report_text()
        self.assertIn("100 / 100", text)
        self.assertIn("sql", text.lower())

    def test_edit_rescored_and_persisted(self):
        edited = RESUME.replace("Owned the roadmap", "Owned the product roadmap and the SQL reporting")
        response = self.client.put(f"/api/document/{self.folder}/resume",
                                   json={"markdown": edited, "note": ""})
        self.assertEqual(response.status_code, 200, response.get_json())
        body = response.get_json()
        self.assertEqual(body["ats"], 100)
        self.assertTrue(body["fitted"])
        self.assertTrue(os.path.isfile(os.path.join(self.run_dir, "tailored_resume.pdf")))

        with open(os.path.join(self.run_dir, "run.json")) as handle:
            self.assertEqual(json.load(handle)["ats"]["resume"], 100)
        with open(os.path.join(self.run_dir, server.ATS_FILE)) as handle:
            data = json.load(handle)
        self.assertEqual(data["resume"]["score"], 100)
        self.assertEqual(sorted(data["resume"]["matched"]), ["product roadmap", "sql"])

    def test_edit_without_keywords_has_no_score(self):
        with open(os.path.join(self.run_dir, server.ATS_FILE), "w") as handle:
            json.dump({"title": "", "keywords": [], "target": 75}, handle)
        response = self.client.put(f"/api/document/{self.folder}/resume",
                                   json={"markdown": RESUME + "\n", "note": ""})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.get_json()["ats"])

    def test_bad_folder_rejected(self):
        response = self.client.put("/api/document/../etc/resume", json={"markdown": "x"})
        self.assertIn(response.status_code, (400, 404))

    def test_a_resume_edit_rebuilds_the_designed_copy(self):
        """Two copies from one text: neither may describe the resume as it was."""
        from pypdf import PdfReader
        edited = RESUME.replace("Owned the roadmap", "Owned the product roadmap")
        response = self.client.put(f"/api/document/{self.folder}/resume",
                                   json={"markdown": edited, "note": ""})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertIsNone(response.get_json()["warning"])
        designed = os.path.join(self.run_dir, "resume_designed.pdf")
        text = " ".join((p.extract_text() or "") for p in PdfReader(designed).pages)
        self.assertIn("product roadmap", " ".join(text.split()))
        self.assertFalse(os.path.exists(os.path.join(self.run_dir, "tailored_resume.docx")))

    def test_a_companion_failure_is_a_warning_not_a_failed_save(self):
        with mock.patch.object(server, "render_resume_companions",
                               side_effect=RuntimeError("layout broke")):
            response = self.client.put(f"/api/document/{self.folder}/resume",
                                       json={"markdown": RESUME + "\n", "note": ""})
        self.assertEqual(response.status_code, 200)
        self.assertIn("could not be rebuilt", response.get_json()["warning"])

    def test_history_lists_the_designed_copy_and_only_pdfs(self):
        self.client.put(f"/api/document/{self.folder}/resume",
                        json={"markdown": RESUME + "\n", "note": ""})
        files = self.client.get("/api/history").get_json()[0]["files"]
        self.assertIn("resume_designed.pdf", files)
        self.assertTrue(all(f.endswith(".pdf") for f in files), files)

    def test_a_saved_edit_is_never_reported_as_a_failed_one(self):
        """The save happens before the scoring; only the score can be lost."""
        edited = RESUME.replace("Owned the roadmap", "Owned the product roadmap")
        with mock.patch.object(server, "_rescore", side_effect=RuntimeError("bad ats.json")):
            response = self.client.put(f"/api/document/{self.folder}/resume",
                                       json={"markdown": edited, "note": ""})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.get_json()["ats"])
        with open(os.path.join(self.run_dir, server.SOURCES_FILE)) as handle:
            self.assertIn("product roadmap", json.load(handle)["resume"]["markdown"])

    def test_the_cover_letter_is_scored_too(self):
        """Both documents are re-scored, so neither goes stale behind the other."""
        response = self.client.put(f"/api/document/{self.folder}/cover_letter",
                                   json={"markdown": LETTER + "\nI write SQL.\n", "note": ""})
        self.assertEqual(response.status_code, 200, response.get_json())
        # "sql" is used exactly; "the roadmap" is only the alias of "product
        # roadmap", which is a variant and does not count toward the score.
        self.assertEqual(response.get_json()["ats"], 50)
        with open(os.path.join(self.run_dir, "run.json")) as handle:
            meta = json.load(handle)
        self.assertEqual(meta["ats"]["cover_letter"], 50)
        self.assertEqual(meta["ats"]["resume"], 0)   # unedited, re-scored: a variant only


if __name__ == "__main__":
    unittest.main()
