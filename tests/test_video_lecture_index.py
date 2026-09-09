import json
import unittest
from pathlib import Path

from server.app import list_video_lectures
from server.video_lectures import (
    TECHNIQUE_NAMES,
    build_video_lecture_library,
    tag_video_breakdowns,
)


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


class VideoLectureTagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.breakdowns = json.loads((DATA / "technique_breakdowns.json").read_text())
        cls.notes = json.loads((DATA / "class_notes.json").read_text())
        cls.guides = json.loads((DATA / "study_guides.json").read_text())

    def test_every_saved_video_part_has_canonical_technique_tags(self):
        tagged = tag_video_breakdowns(self.breakdowns, self.notes)
        seen = 0
        for entry in tagged.values():
            lecture = entry.get("video_breakdown") if isinstance(entry, dict) else None
            if not lecture:
                continue
            for part in lecture["steps"]:
                seen += 1
                self.assertTrue(part["techniques"])
                self.assertIn(part["technique"], part["techniques"])
                self.assertNotIn("general", part["techniques"])
                self.assertTrue(part["technique_label"])
                for technique in part["techniques"]:
                    self.assertIn(technique, TECHNIQUE_NAMES)
        self.assertGreater(seen, 100)

    def test_compound_breakdown_part_keeps_multiple_technique_tags(self):
        tagged = tag_video_breakdowns(self.breakdowns, self.notes)
        parts = tagged["class_20260526_combo"]["video_breakdown"]["steps"]
        transition = next(
            part
            for part in parts
            if part["technique_label"] == "basic_step_into_prep_step"
        )

        self.assertTrue(
            {"basic_step", "prep_step"}.issubset(transition["techniques"])
        )

    def test_central_index_contains_every_saved_breakdown_part(self):
        library = build_video_lecture_library(
            self.breakdowns,
            self.guides,
            self.notes,
        )
        source_count = sum(
            len(entry["video_breakdown"].get("steps", []))
            for entry in self.breakdowns.values()
            if isinstance(entry, dict) and entry.get("video_breakdown")
        )

        self.assertEqual(library["part_count"], source_count)
        # Derived, not pinned: every new class video adds a lecture, so a
        # literal here goes stale on the next ingest.
        self.assertEqual(
            library["lecture_count"],
            sum(
                1
                for entry in self.breakdowns.values()
                if isinstance(entry, dict) and entry.get("video_breakdown")
            ),
        )
        self.assertIn(
            "half_step",
            {item["slug"] for item in library["techniques"]},
        )
        self.assertIn(
            "side_to_side",
            {item["slug"] for item in library["techniques"]},
        )

    def test_api_filter_returns_only_parts_tagged_for_technique(self):
        result = list_video_lectures(technique="half_step")

        self.assertGreater(result["part_count"], 0)
        for lecture in result["lectures"]:
            for part in lecture["parts"]:
                self.assertIn("half_step", part["techniques"])

    def test_centralized_video_page_exposes_tag_filters(self):
        page = (ROOT / "server" / "web" / "video-lectures.html").read_text()

        self.assertIn("/api/video-lectures", page)
        self.assertIn("canonical technique tags", page)
        self.assertIn("Original breakdown label", page)


if __name__ == "__main__":
    unittest.main()
