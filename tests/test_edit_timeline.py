import os
import tempfile
import unittest

from lib.edit_timeline import from_clips, save_timeline, timeline_duration, validate_timeline


class TestEditTimeline(unittest.TestCase):
    def test_from_clips_duration(self):
        tl = from_clips(
            ["a.mp4", "b.mp4", "c.mp4"],
            xfade=0.25,
            durations=[2.0, 2.0, 2.0],
            width=1080,
            height=1920,
        )
        self.assertEqual(len(tl["clips"]), 3)
        self.assertEqual(len(tl["transitions"]), 2)
        # 2+2+2 - 0.25 - 0.25
        self.assertAlmostEqual(timeline_duration(tl), 5.5, places=3)

    def test_bad_transition_id(self):
        tl = from_clips(["a.mp4", "b.mp4"], durations=[1.0, 1.0])
        tl["transitions"].append({"id": "bad", "from": "c1", "to": "nope", "type": "cut"})
        with self.assertRaises(ValueError):
            validate_timeline(tl)

    def test_roundtrip(self):
        tl = from_clips(["a.mp4"], durations=[1.5], width=640, height=360)
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "t.json")
            save_timeline(tl, path)
            from lib.edit_timeline import load_timeline

            back = load_timeline(path)
        self.assertEqual(back["width"], 640)
        self.assertAlmostEqual(timeline_duration(back), 1.5)


if __name__ == "__main__":
    unittest.main()
