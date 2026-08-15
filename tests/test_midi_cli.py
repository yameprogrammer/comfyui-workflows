import os
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


class TestMidiCli(unittest.TestCase):
    def test_extract_help(self):
        r = _run(["scripts/extract_music_skeleton.py", "--help"])
        self.assertEqual(r.returncode, 0)

    def test_arrange_from_chords(self):
        with tempfile.TemporaryDirectory() as td:
            mid = os.path.join(td, "bed.mid")
            r = _run(
                [
                    "scripts/generate_midi_arrangement.py",
                    "--chords",
                    "Am,F,C,G",
                    "--genre",
                    "piano_pop",
                    "--bpm",
                    "96",
                    "-o",
                    mid,
                ]
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(os.path.isfile(mid))
            self.assertTrue(open(mid, "rb").read().startswith(b"MThd"))

    def test_toolbox_write_refused(self):
        dest = os.path.join(ROOT, "dumps", "_midi_should_not_write.mid")
        r = _run(
            [
                "scripts/generate_midi_arrangement.py",
                "--chords",
                "C",
                "-o",
                dest,
            ],
            env={"AGENT_ALLOW_TOOLBOX_OUTPUT": ""},
        )
        self.assertEqual(r.returncode, 14)
        self.assertFalse(os.path.isfile(dest))

    def test_cover_bed_from_chords(self):
        with tempfile.TemporaryDirectory() as td:
            r = _run(
                [
                    "scripts/generate_midi_cover_bed.py",
                    "--chords",
                    "Am,F,C,G",
                    "--genre",
                    "piano_pop",
                    "--skip-render",
                    "-o",
                    td,
                ]
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(os.path.isfile(os.path.join(td, "skeleton.json")))
            self.assertTrue(os.path.isfile(os.path.join(td, "arrangement.mid")))
            src = os.path.join(td, "SOURCE.md")
            prompt = os.path.join(td, "cover_prompt.md")
            self.assertTrue(os.path.isfile(src))
            self.assertTrue(os.path.isfile(prompt))
            with open(src, encoding="utf-8") as f:
                body = f.read()
            self.assertIn("Do not send the source audio", body)

    def test_render_builtin_synth(self):
        with tempfile.TemporaryDirectory() as td:
            mid = os.path.join(td, "bed.mid")
            wav = os.path.join(td, "bed.wav")
            r = _run(
                [
                    "scripts/generate_midi_arrangement.py",
                    "--chords",
                    "C,G,Am,F",
                    "--genre",
                    "piano_pop",
                    "--bars",
                    "4",
                    "-o",
                    mid,
                ]
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            r2 = _run(
                [
                    "scripts/generate_midi_render.py",
                    "-i",
                    mid,
                    "-o",
                    wav,
                    "--engine",
                    "synth",
                ]
            )
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertTrue(os.path.isfile(wav))
            self.assertGreater(os.path.getsize(wav), 4000)


if __name__ == "__main__":
    unittest.main()

