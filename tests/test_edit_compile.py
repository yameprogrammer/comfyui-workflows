import os
import tempfile
import unittest

from lib.edit_compile_ffmpeg import compile_ffmpeg
from lib.edit_timeline import from_clips


class TestEditCompile(unittest.TestCase):
    def test_xfade_and_overlay_in_graph(self):
        with tempfile.TemporaryDirectory() as td:
            a = os.path.join(td, "a.mp4")
            b = os.path.join(td, "b.mp4")
            ov = os.path.join(td, "cap.png")
            for p in (a, b, ov):
                open(p, "wb").write(b"x")
            tl = from_clips([a, b], xfade=0.25, durations=[1.0, 1.0], width=320, height=240)
            tl["overlays"].append(
                {
                    "id": "t1",
                    "kind": "caption",
                    "text": "hi",
                    "path": ov,
                    "start": 0.2,
                    "end": 1.0,
                    "preset": "caption",
                }
            )
            spec = compile_ffmpeg(tl, os.path.join(td, "out.mp4"), timeline_path=os.path.join(td, "t.json"))
        self.assertIn("xfade", spec["graph"])
        self.assertIn("overlay", spec["graph"])
        self.assertGreater(spec["duration"], 1.5)


if __name__ == "__main__":
    unittest.main()
