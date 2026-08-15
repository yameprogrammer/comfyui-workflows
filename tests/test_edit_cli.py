import os
import shutil
import subprocess
import sys
import tempfile
import unittest

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


def _ffmpeg():
    return shutil.which("ffmpeg")


class TestEditCli(unittest.TestCase):
    def test_timeline_help(self):
        r = _run(["scripts/edit_timeline.py", "-h"])
        self.assertEqual(r.returncode, 0)

    def test_list_looks(self):
        r = _run(["scripts/comp_shot.py", "--list-looks"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("night", r.stdout)
        r2 = _run(["scripts/edit_timeline.py", "list-looks"])
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn("punch", r2.stdout)

    def test_list_motions(self):
        r = _run(["scripts/edit_timeline.py", "list-motions"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("direction", r.stdout)
        self.assertIn("scale_from", r.stdout)

    def test_title_list_fonts(self):
        r = _run(["scripts/render_title.py", "--list-fonts"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("yeonung", r.stdout)
        self.assertIn("gothic", r.stdout)

    def test_title_list_parts_and_compose(self):
        r = _run(["scripts/render_title.py", "--list-parts"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("layouts", r.stdout)
        self.assertIn("yeonung", r.stdout)
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "mix.png")
            r2 = _run(
                [
                    "scripts/render_title.py",
                    "--text",
                    "조금만 더",
                    "--layout",
                    "caption",
                    "--color",
                    "cyan",
                    "--bubble",
                    "yellow",
                    "--tilt",
                    "-4",
                    "--y",
                    "0.82",
                    "--width",
                    "320",
                    "--height",
                    "240",
                    "-o",
                    out,
                ]
            )
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            self.assertTrue(os.path.isfile(out))
            self.assertGreater(os.path.getsize(out), 200)

    def test_render_two_colors_xfade(self):
        if not _ffmpeg():
            self.skipTest("ffmpeg not on PATH")
        with tempfile.TemporaryDirectory() as td:
            a = os.path.join(td, "a.mp4")
            b = os.path.join(td, "b.mp4")
            for path, color in ((a, "red"), (b, "blue")):
                subprocess.run(
                    [
                        _ffmpeg(),
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
            tl = os.path.join(td, "timeline.json")
            r = _run(
                [
                    "scripts/edit_timeline.py",
                    "from-clips",
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
                    "-o",
                    tl,
                ]
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            master = os.path.join(td, "master.mp4")
            r2 = _run(["scripts/render_edit.py", "--timeline", tl, "-o", master, "--allow-freeze"])
            self.assertEqual(r2.returncode, 0, r2.stderr + r2.stdout)
            self.assertTrue(os.path.isfile(master))
            self.assertGreater(os.path.getsize(master), 1000)
            qa = os.path.join(td, "qa")
            r3 = _run(["scripts/edit_qa_pack.py", "-i", master, "-o", qa])
            self.assertEqual(r3.returncode, 0, r3.stderr)
            self.assertTrue(os.path.isfile(os.path.join(qa, "qa_pack.json")))


if __name__ == "__main__":
    unittest.main()
