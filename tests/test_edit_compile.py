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

    def test_audio_fade_and_overlay_fade_in_graph(self):
        with tempfile.TemporaryDirectory() as td:
            a = os.path.join(td, "a.mp4")
            wav = os.path.join(td, "bed.wav")
            ov = os.path.join(td, "cap.png")
            for p in (a, wav, ov):
                open(p, "wb").write(b"x")
            tl = from_clips([a], durations=[2.0], width=320, height=240)
            tl["overlays"].append(
                {
                    "id": "t1",
                    "kind": "caption",
                    "path": ov,
                    "start": 0.2,
                    "end": 1.4,
                    "fade_in": 0.12,
                    "fade_out": 0.12,
                }
            )
            tl["audio"].append(
                {
                    "id": "bgm",
                    "path": wav,
                    "start": 0.0,
                    "in": 0.0,
                    "out": 2.0,
                    "volume": 1.0,
                    "role": "master",
                    "fade_in": 0.2,
                    "fade_out": 0.35,
                    "duck": 0.28,
                }
            )
            spec = compile_ffmpeg(tl, os.path.join(td, "out.mp4"))
        self.assertIn("afade=t=in", spec["graph"])
        self.assertIn("afade=t=out", spec["graph"])
        self.assertIn("fade=t=in", spec["graph"])
        self.assertIn("alpha=1", spec["graph"])

    def test_overlay_pop_motion_in_graph(self):
        with tempfile.TemporaryDirectory() as td:
            a = os.path.join(td, "a.mp4")
            ov = os.path.join(td, "cap.png")
            for p in (a, ov):
                open(p, "wb").write(b"x")
            tl = from_clips([a], durations=[2.0], width=320, height=240)
            tl["overlays"].append(
                {
                    "id": "t1",
                    "kind": "caption",
                    "path": ov,
                    "start": 0.3,
                    "end": 1.6,
                    "motion": "pop",
                }
            )
            spec = compile_ffmpeg(tl, os.path.join(td, "out.mp4"))
        self.assertIn("eval=frame", spec["graph"])
        self.assertIn("fade=t=in:st=0.3000", spec["graph"])
        self.assertIn("overlay=", spec["graph"])

    def test_unknown_motion_downgraded(self):
        with tempfile.TemporaryDirectory() as td:
            a = os.path.join(td, "a.mp4")
            ov = os.path.join(td, "cap.png")
            for p in (a, ov):
                open(p, "wb").write(b"x")
            tl = from_clips([a], durations=[1.0], width=320, height=240)
            tl["overlays"].append(
                {
                    "id": "t1",
                    "kind": "caption",
                    "path": ov,
                    "start": 0.0,
                    "end": 0.8,
                    "motion": "explode",
                }
            )
            spec = compile_ffmpeg(tl, os.path.join(td, "out.mp4"))
        self.assertEqual(tl["overlays"][0]["motion"], "fade")
        self.assertIn("fade=t=in", spec["graph"])

    def test_compose_direction_and_scale_parts(self):
        from lib.edit_motion import compose_motion

        m = compose_motion(
            {
                "start": 0.2,
                "end": 2.0,
                "direction": "left",
                "distance": 120,
                "scale_from": 0.7,
                "scale_to": 1.05,
                "move": 0.25,
                "fade_in": 0.08,
            },
            width=1080,
            height=1920,
        )
        self.assertEqual(m["name"], "custom")
        self.assertEqual(m["dx"], 120)
        self.assertEqual(m["dy"], 0)
        self.assertAlmostEqual(m["scale_from"], 0.7)
        self.assertAlmostEqual(m["fade_in"], 0.08)

        with tempfile.TemporaryDirectory() as td:
            a = os.path.join(td, "a.mp4")
            ov = os.path.join(td, "cap.png")
            for p in (a, ov):
                open(p, "wb").write(b"x")
            tl = from_clips([a], durations=[2.0], width=320, height=240)
            tl["overlays"].append(
                {
                    "id": "t1",
                    "kind": "caption",
                    "path": ov,
                    "start": 0.2,
                    "end": 1.8,
                    "direction": "left",
                    "distance": 80,
                    "scale_from": 0.75,
                    "move": 0.2,
                    "fade_in": 0.08,
                }
            )
            spec = compile_ffmpeg(tl, os.path.join(td, "out.mp4"))
        self.assertIn("80.00", spec["graph"])
        self.assertIn("0.7500", spec["graph"])
        self.assertIn("eval=frame", spec["graph"])


if __name__ == "__main__":
    unittest.main()
