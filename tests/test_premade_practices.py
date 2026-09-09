import json
import unittest
from pathlib import Path

from server.practice_library import build_practice_library
from server.video_lectures import build_video_lecture_library


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


class PremadePracticeLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.class_notes = json.loads((DATA / "class_notes.json").read_text())
        cls.techniques = json.loads((DATA / "techniques.json").read_text())
        cls.breakdowns = json.loads((DATA / "technique_breakdowns.json").read_text())
        cls.study_guides = json.loads((DATA / "study_guides.json").read_text())
        cls.lecture_library = build_video_lecture_library(
            cls.breakdowns,
            cls.study_guides,
            cls.class_notes,
        )
        cls.library = build_practice_library(
            cls.class_notes,
            cls.techniques,
            cls.lecture_library,
        )

    def test_every_identified_class_technique_has_one_premade_practice(self):
        identified = {
            technique
            for note in self.class_notes
            for technique in note.get("techniques_covered", [])
        }
        practices = {
            practice["technique"]
            for practice in self.library["practices"]
        }

        self.assertEqual(practices, identified)
        self.assertEqual(self.library["count"], len(identified))

    def test_every_practice_has_class_sources_and_balanced_minutes(self):
        for practice in self.library["practices"]:
            self.assertTrue(practice["class_sources"], practice["technique"])
            scheduled = (
                practice["warmup"]["minutes"]
                + sum(drill["minutes"] for drill in practice["drills"])
                + practice["music_round"]["minutes"]
            )
            self.assertEqual(practice["total_minutes"], scheduled)

    def test_displayed_cues_are_exact_class_teaching_points(self):
        source_cues = {
            (
                point.get("technique"),
                point.get("tip"),
                note.get("class_date"),
            )
            for note in self.class_notes
            for point in note.get("teaching_points", [])
        }
        for practice in self.library["practices"]:
            for cue in practice["class_cues"]:
                self.assertIn(
                    (
                        practice["technique"],
                        cue["tip"],
                        cue["class_date"],
                    ),
                    source_cues,
                )

    def test_latest_class_techniques_come_first(self):
        latest = self.library["latest_class"]
        leading = [
            practice["technique"]
            for practice in self.library["practices"][:len(latest["techniques"])]
        ]

        self.assertEqual(leading, latest["techniques"])
        # Derived from the notes rather than pinned to a date, so ingesting a
        # new class does not turn this into a false failure.
        self.assertEqual(
            latest["date"],
            max(note["class_date"] for note in self.class_notes),
        )

    def test_latest_side_to_side_practice_is_curated_and_video_linked(self):
        side_to_side = next(
            practice
            for practice in self.library["practices"]
            if practice["technique"] == "side_to_side"
        )

        self.assertTrue(side_to_side["is_curated"])
        self.assertEqual(
            side_to_side["latest_class"]["date"],
            max(
                note["class_date"]
                for note in self.class_notes
                if "side_to_side" in note.get("techniques_covered", [])
            ),
        )
        self.assertTrue(side_to_side["video_parts"])
        for part in side_to_side["video_parts"]:
            self.assertIn("side_to_side", part["techniques"])

    def test_practices_include_centralized_video_parts_when_available(self):
        practices = {
            practice["technique"]: practice
            for practice in self.library["practices"]
        }

        self.assertTrue(practices["half_step"]["video_parts"])
        for part in practices["half_step"]["video_parts"]:
            self.assertIn("half_step", part["techniques"])


if __name__ == "__main__":
    unittest.main()
