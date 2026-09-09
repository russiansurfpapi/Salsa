import json
import unittest
from pathlib import Path
from unittest.mock import patch

from server.app import PracticeGenerateReq, generate_practice
from server.practice_llm import PRACTICE_SYSTEM_PROMPT, _normalize_plan
from server.salsa_context import SALSA_STYLE_NAME, salsa_style_context


ROOT = Path(__file__).resolve().parent.parent


def latest_class_note():
    """Newest class in the notes, so these tests survive a new class ingest."""
    notes = json.loads((ROOT / "data" / "class_notes.json").read_text())
    return max(notes, key=lambda note: note["class_date"])


class NewYorkSalsaContextTests(unittest.TestCase):
    def test_canonical_context_is_an_explicit_on2_constraint(self):
        context = salsa_style_context()

        self.assertIn("New York-style salsa", context)
        self.assertIn("NY On2", context)
        self.assertIn("hard constraint", context)
        self.assertIn("Never silently substitute On1", context)

    def test_practice_prompt_uses_canonical_context(self):
        self.assertIn(SALSA_STYLE_NAME, PRACTICE_SYSTEM_PROMPT)
        self.assertIn("NY On2", PRACTICE_SYSTEM_PROMPT)
        self.assertIn("class evidence", PRACTICE_SYSTEM_PROMPT)
        self.assertIn("Do not invent angles", PRACTICE_SYSTEM_PROMPT)

    def test_normalized_llm_plan_is_labeled_with_canonical_style(self):
        plan = _normalize_plan({"title": "Half Step practice"}, 25)

        self.assertEqual(plan["style"], SALSA_STYLE_NAME)
        self.assertEqual(plan["total_minutes"], 25)


class PracticeEndpointTests(unittest.TestCase):
    @patch("server.app.generate_practice_plan")
    def test_endpoint_passes_latest_class_evidence_to_llm(self, generate_mock):
        generate_mock.return_value = (
            {
                "title": "Half Step and right turns",
                "total_minutes": 25,
                "style": SALSA_STYLE_NAME,
            },
            "test-llm",
        )
        request = PracticeGenerateReq(
            prompt="Practice Side to Side, not Basic Step.",
            minutes=25,
        )

        response = generate_practice(request)

        student_prompt, minutes, evidence = generate_mock.call_args.args
        self.assertEqual(student_prompt, request.prompt)
        self.assertEqual(minutes, 25)
        latest = latest_class_note()
        self.assertEqual(evidence["latest_class"]["date"], latest["class_date"])
        self.assertEqual(
            evidence["latest_class"]["techniques"],
            latest["techniques_covered"],
        )
        self.assertEqual(response["generated_by"], "test-llm")
        self.assertEqual(response["style"], SALSA_STYLE_NAME)

    def test_practice_page_exposes_premade_class_library(self):
        page = (ROOT / "server" / "web" / "practice.html").read_text()

        self.assertIn("/api/practices", page)
        self.assertIn("Premade technique practices", page)
        self.assertIn("NY SALSA ON2", page)
        self.assertIn("Tagged class-video parts", page)


if __name__ == "__main__":
    unittest.main()
