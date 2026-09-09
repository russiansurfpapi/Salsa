import unittest
from unittest.mock import patch

from ingest.youtube_tutorials import rank_candidates_with_llm
from server.techniques import video_key_for_technique


class ExactTutorialKeyTests(unittest.TestCase):
    def test_half_step_does_not_fall_back_to_basic_step(self):
        self.assertEqual(video_key_for_technique("half_step"), "half_step")

    def test_around_the_world_does_not_fall_back_to_basic_step(self):
        self.assertEqual(
            video_key_for_technique("around_the_world"),
            "around_the_world",
        )

    @patch(
        "ingest.youtube_tutorials._llm_json",
        return_value={
            "selected": [
                {
                    "youtube_id": "half-turn-id",
                    "why": "It explicitly teaches On2 half turns.",
                }
            ]
        },
    )
    def test_candidate_selection_comes_from_llm_result(self, mocked_llm):
        candidates = [
            {
                "youtube_id": "basic-id",
                "title": "Salsa Basic Step",
                "url": "https://www.youtube.com/watch?v=basic-id",
                "channel": "Basic Channel",
                "description": "A generic basic step.",
                "duration_seconds": 60,
                "view_count": 100000,
            },
            {
                "youtube_id": "half-turn-id",
                "title": "Salsa On2 Half Turns",
                "url": "https://www.youtube.com/watch?v=half-turn-id",
                "channel": "Half Turn Channel",
                "description": "A half-turn footwork lesson.",
                "duration_seconds": 90,
                "view_count": 100,
            },
        ]

        selected = rank_candidates_with_llm(
            {"slug": "half_step", "name": "Half Step"},
            candidates,
        )

        mocked_llm.assert_called_once()
        self.assertEqual([video["title"] for video in selected], ["Salsa On2 Half Turns"])
        self.assertEqual(selected[0]["match_method"], "llm")


if __name__ == "__main__":
    unittest.main()
