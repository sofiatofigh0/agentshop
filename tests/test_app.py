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
                                  "markdown": RESUME}}, handle)
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


if __name__ == "__main__":
    unittest.main()
