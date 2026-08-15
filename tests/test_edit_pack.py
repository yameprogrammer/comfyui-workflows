import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from lib.edit_pack import (
    attach_mix,
    build_pack,
    build_title_overlays,
    default_title_window,
    refuse_frozen_clips,
    resolve_title_window,
    sidecar_paths,
    title_kind,
    title_windows,
)
from lib.edit_timeline import timeline_duration

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _run(args, env=None):
    e = os.environ.copy()
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=e,
    )


class TestEditPackLib(unittest.TestCase):
    def test_sidecar_paths(self):
        paths = sidecar_paths(r"D:\proj\edits\s01\master.mp4")
        self.assertTrue(paths["timeline"].endswith(os.path.join("s01", "timeline.json")))
        self.assertTrue(paths["title"].endswith(os.path.join("titles", "t1.png")))
        self.assertTrue(paths["qa"].endswith(os.path.join("s01", "qa")))

    def test_title_window_defaults(self):
        start, end = default_title_window(8.0)
        self.assertAlmostEqual(start, 0.4, places=3)
        self.assertGreater(end, start)
        self.assertLessEqual(end, 3.4)
        s2, e2 = resolve_title_window(8.0, start=1.0, end=2.5)
        self.assertAlmostEqual(s2, 1.0)
        self.assertAlmostEqual(e2, 2.5)
        with self.assertRaises(ValueError):
            resolve_title_window(4.0, start=2.0, end=1.0)

    def test_title_windows_sequential(self):
        wins = title_windows(8.0, 2)
        self.assertEqual(len(wins), 2)
        self.assertLess(wins[0][1], wins[1][0] + 0.01)
        self.assertLessEqual(wins[1][1], 8.0)
        self.assertEqual(title_windows(8.0, 1), [default_title_window(8.0)])

    def test_title_kind(self):
        self.assertEqual(title_kind("yeonung"), "caption")
        self.assertEqual(title_kind("lower_third"), "lower_third")
        self.assertEqual(title_kind("card"), "card")

    def test_build_pack_xfade_and_look(self):
        tl = build_pack(
            ["a.mp4", "b.mp4"],
            xfade=0.25,
            durations=[2.0, 2.0],
            width=1080,
            height=1920,
            look="night",
            saturation=1.2,
        )
        self.assertEqual(len(tl["clips"]), 2)
        self.assertEqual(len(tl["transitions"]), 1)
        self.assertAlmostEqual(timeline_duration(tl), 3.75, places=3)
        self.assertEqual(tl["look"]["name"], "night")
        self.assertGreater(tl["look"]["saturation"], 1.0)

    def test_single_overlay_and_stagger(self):
        ovs = build_title_overlays(
            path="cap.png",
            text="포기하지 마",
            start=0.4,
            end=3.2,
            motion="pop",
        )
        self.assertEqual(len(ovs), 1)
        self.assertEqual(ovs[0]["id"], "t1")
        self.assertEqual(ovs[0]["motion"], "pop")

        glyphs = {
            "glyphs": [
                {"path": "g1.png", "ch": "포", "x": 10, "y": 20, "w": 30, "h": 40},
                {"path": "g2.png", "ch": "기", "x": 40, "y": 20, "w": 30, "h": 40},
            ]
        }
        stag = build_title_overlays(
            path="cap.png",
            text="포기",
            start=0.4,
            end=3.2,
            motion="pop",
            stagger=0.06,
            glyphs=glyphs,
        )
        self.assertEqual(len(stag), 2)
        self.assertAlmostEqual(stag[0]["start"], 0.4)
        self.assertAlmostEqual(stag[1]["start"], 0.46)
        self.assertEqual(stag[0]["ox"], 10)

    def test_attach_mix_ducks_bed_under_vo(self):
        tl = build_pack(["a.mp4"], durations=[4.0], width=320, height=240)
        tl = attach_mix(tl, audio="bed.wav", vo="line.wav")
        roles = {a["id"]: a for a in tl["audio"]}
        self.assertEqual(roles["bed"]["role"], "master")
        self.assertAlmostEqual(roles["bed"]["duck"], 0.28)
        self.assertAlmostEqual(roles["bed"]["fade_in"], 0.2)
        self.assertEqual(roles["vo"]["role"], "vo")
        only_bed = attach_mix(
            build_pack(["a.mp4"], durations=[2.0]),
            audio="bed.wav",
        )
        self.assertNotIn("duck", only_bed["audio"][0])

    def test_allow_freeze_skips_gate(self):
        tl = build_pack(["missing.mp4"], durations=[2.0])
        out = refuse_frozen_clips(tl, allow_freeze=True)
        self.assertTrue(out["ok"])
        self.assertTrue(out.get("allowed"))

    def test_stagger_requires_glyphs(self):
        with self.assertRaises(ValueError):
            build_title_overlays(
                path="cap.png",
                text="헐",
                start=0.4,
                end=2.0,
                stagger=0.06,
            )


class TestEditPackCli(unittest.TestCase):
    def test_help(self):
        r = _run(["scripts/edit_pack.py", "-h"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("xfade", r.stdout)
        self.assertIn("stagger", r.stdout)
        self.assertIn("audio", r.stdout)
        self.assertIn("allow-freeze", r.stdout)
        self.assertIn("no-qa", r.stdout)

    def test_toolbox_write_refused(self):
        dest = os.path.join(ROOT, "stories", "_nope_master.mp4")
        r = _run(["scripts/edit_pack.py", "-i", "a.mp4", "-o", dest])
        self.assertEqual(r.returncode, 14, r.stderr + r.stdout)

    def test_render_clips_and_title(self):
        if not shutil.which("ffmpeg"):
            self.skipTest("ffmpeg not on PATH")
        with tempfile.TemporaryDirectory() as td:
            a = os.path.join(td, "a.mp4")
            b = os.path.join(td, "b.mp4")
            for path, color in ((a, "red"), (b, "blue")):
                subprocess.run(
                    [
                        shutil.which("ffmpeg"),
                        "-y",
                        "-f",
                        "lavfi",
                        "-i",
                        f"color=c={color}:s=320x240:r=24:d=1",
                        "-pix_fmt",
                        "yuv420p",
                        path,
                    ],
                    check=True,
                    capture_output=True,
                )
            master = os.path.join(td, "master.mp4")
            r = _run(
                [
                    "scripts/edit_pack.py",
                    "-i",
                    a,
                    "-i",
                    b,
                    "--xfade",
                    "0.25",
                    "--width",
                    "320",
                    "--height",
                    "240",
                    "--text",
                    "헐",
                    "--font",
                    "gothic",
                    "--motion",
                    "pop",
                    "--look",
                    "night",
                    "--allow-freeze",
                    "-o",
                    master,
                    "--json",
                ]
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertTrue(os.path.isfile(master))
            self.assertTrue(os.path.isfile(os.path.join(td, "timeline.json")))
            self.assertTrue(os.path.isfile(os.path.join(td, "titles", "t1.png")))
            self.assertTrue(os.path.isfile(os.path.join(td, "qa", "qa_pack.json")))

    def test_mix_timeline_and_freeze_refuse(self):
        if not shutil.which("ffmpeg"):
            self.skipTest("ffmpeg not on PATH")
        ff = shutil.which("ffmpeg")
        with tempfile.TemporaryDirectory() as td:
            clip = os.path.join(td, "still.mp4")
            bed = os.path.join(td, "bed.wav")
            vo = os.path.join(td, "vo.wav")
            subprocess.run(
                [
                    ff, "-y", "-f", "lavfi", "-i", "color=c=red:s=320x240:r=24:d=1.2",
                    "-pix_fmt", "yuv420p", clip,
                ],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [ff, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1.2", "-ar", "48000", bed],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [ff, "-y", "-f", "lavfi", "-i", "sine=frequency=880:duration=0.8", "-ar", "48000", vo],
                check=True,
                capture_output=True,
            )
            master = os.path.join(td, "master.mp4")
            r_mix = _run(
                [
                    "scripts/edit_pack.py",
                    "-i", clip,
                    "--width", "320",
                    "--height", "240",
                    "--audio", bed,
                    "--vo", vo,
                    "--timeline-only",
                    "-o", master,
                    "--json",
                ]
            )
            self.assertEqual(r_mix.returncode, 0, r_mix.stderr + r_mix.stdout)
            import json

            tl_path = os.path.join(td, "timeline.json")
            with open(tl_path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(len(data["audio"]), 2)
            self.assertAlmostEqual(data["audio"][0]["duck"], 0.28)
            self.assertEqual(data["audio"][1]["role"], "vo")

            r_fr = _run(
                [
                    "scripts/edit_pack.py",
                    "-i", clip,
                    "--width", "320",
                    "--height", "240",
                    "-o", master,
                    "--json",
                ]
            )
            self.assertNotEqual(r_fr.returncode, 0, r_fr.stdout + r_fr.stderr)
            blob = r_fr.stdout + r_fr.stderr
            self.assertIn("FREEZE_PAD_SUSPECT", blob)

    def test_multi_text_timeline(self):
        if not shutil.which("ffmpeg"):
            self.skipTest("ffmpeg not on PATH")
        with tempfile.TemporaryDirectory() as td:
            clip = os.path.join(td, "a.mp4")
            subprocess.run(
                [
                    shutil.which("ffmpeg"),
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=navy:s=320x240:r=24:d=4",
                    "-pix_fmt",
                    "yuv420p",
                    clip,
                ],
                check=True,
                capture_output=True,
            )
            master = os.path.join(td, "master.mp4")
            r = _run(
                [
                    "scripts/edit_pack.py",
                    "-i",
                    clip,
                    "--width",
                    "320",
                    "--height",
                    "240",
                    "--text",
                    "잠깐",
                    "--text",
                    "가자",
                    "--font",
                    "gothic",
                    "--timeline-only",
                    "-o",
                    master,
                    "--json",
                ]
            )
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertTrue(os.path.isfile(os.path.join(td, "titles", "t1.png")))
            self.assertTrue(os.path.isfile(os.path.join(td, "titles", "t2.png")))
            import json

            with open(os.path.join(td, "timeline.json"), encoding="utf-8") as f:
                data = json.load(f)
            texts = [o.get("text") for o in data["overlays"]]
            self.assertIn("잠깐", texts)
            self.assertIn("가자", texts)
            self.assertLess(data["overlays"][0]["end"], data["overlays"][-1]["start"] + 0.05)

    def test_assemble_warns_edit_pack(self):
        r = _run(["scripts/assemble_video.py", "-e", "ZZ_NOT_AN_EP"])
        self.assertIn("edit_pack", r.stderr)
        self.assertIn("debug concat", r.stderr.lower() + r.stderr)


if __name__ == "__main__":
    unittest.main()
