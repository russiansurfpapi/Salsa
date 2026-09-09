import unittest

from ingest.video_study import _parse_model_json, _validate_guide_shape


class VideoStudyJsonTests(unittest.TestCase):
    def test_repairs_common_model_json_punctuation(self):
        broken = """```json
        {
          "techniques": [{"slug": "side_to_side",}],
          "choreography": {"phases": [{"name": "Walk-through"}]},
          "practice": {"sections": [{"name": "Isolation"}]},
          "key_frames": [{"frame": "frame_001.jpg"}]
        }
        ```"""

        guide = _parse_model_json(broken)
        _validate_guide_shape(guide)

        self.assertEqual(guide["techniques"][0]["slug"], "side_to_side")

    def test_rejects_incomplete_guide_before_save(self):
        guide = {
            "techniques": [{"slug": "side_to_side"}],
            "choreography": {"phases": []},
            "practice": {"sections": []},
            "key_frames": [],
        }

        with self.assertRaisesRegex(ValueError, "incomplete"):
            _validate_guide_shape(guide)


if __name__ == "__main__":
    unittest.main()
