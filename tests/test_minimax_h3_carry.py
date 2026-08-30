"""Carry-look tail extract: last N frames, never the first N. No Comfy."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from lib.minimax_h3_runner import extract_carry_tail, _ffmpeg_bin


def _ffmpeg() -> str | None:
    return _ffmpeg_bin()


def _write_red_then_blue(ffmpeg: str, dest: str, *, head_frames: int = 25, tail_frames: int = 5) -> None:
    """24fps clip: red head, then blue tail (yuv420p)."""
    td = Path(dest).parent
    red = str(td / "head_red.mp4")
    blue = str(td / "tail_blue.mp4")
    for path, color, n in ((red, "0xFF0000", head_frames), (blue, "0x0000FF", tail_frames)):
        subprocess.check_call(
            [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"color=c={color}:s=64x64:r=24:d={n / 24:.6f}",
                "-pix_fmt",
                "yuv420p",
                path,
            ]
        )
    lst = str(td / "concat.txt")
    Path(lst).write_text(f"file '{Path(red).name}'\nfile '{Path(blue).name}'\n", encoding="utf-8")
    subprocess.check_call(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            lst,
            "-c",
            "copy",
            dest,
        ],
        cwd=str(td),
    )


def _first_frame_rgb(ffmpeg: str, video: str, png: str) -> tuple[float, float, float]:
    subprocess.check_call(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            video,
            "-frames:v",
            "1",
            png,
        ]
    )
    px = list(Image.open(png).convert("RGB").getdata())
    n = max(1, len(px))
    r = sum(p[0] for p in px) / n
    g = sum(p[1] for p in px) / n
    b = sum(p[2] for p in px) / n
    return r, g, b


class TestExtractCarryTail(unittest.TestCase):
    def setUp(self):
        self.ffmpeg = _ffmpeg()
        if not self.ffmpeg:
            self.skipTest("ffmpeg (PATH or imageio-ffmpeg) not available")

    def _assert_blue_not_red(self, rgb: tuple[float, float, float]) -> None:
        r, _g, b = rgb
        self.assertGreater(b, r, f"expected blue tail, got rgb={rgb}")
        self.assertGreater(b, 80)

    def test_last_frames_not_first(self):
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "plate.mp4")
            _write_red_then_blue(self.ffmpeg, src)
            first = _first_frame_rgb(self.ffmpeg, src, os.path.join(td, "src_first.png"))
            self.assertGreater(first[0], first[2], f"fixture head should be red, got {first}")

            out = extract_carry_tail(src, Path(td) / "carry", frames=5)
            self.assertTrue(os.path.isfile(out))
            rgb = _first_frame_rgb(self.ffmpeg, out, os.path.join(td, "tail_first.png"))
            self._assert_blue_not_red(rgb)
            self.assertLess(os.path.getsize(out), os.path.getsize(src))

    def test_path_ffmpeg_missing_uses_bundled(self):
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "plate.mp4")
            _write_red_then_blue(self.ffmpeg, src)
            with patch.dict(os.environ, {"FFMPEG_PATH": "", "FFMPEG": ""}, clear=False):
                with patch("lib.minimax_h3_runner.shutil.which", return_value=None):
                    out = extract_carry_tail(src, Path(td) / "carry", frames=5)
            rgb = _first_frame_rgb(self.ffmpeg, out, os.path.join(td, "tail_first.png"))
            self._assert_blue_not_red(rgb)

    def test_no_ffmpeg_raises_does_not_copy(self):
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "plate.mp4")
            Path(src).write_bytes(b"not-a-video")
            dest_dir = Path(td) / "carry"
            dest_dir.mkdir()
            with patch("lib.minimax_h3_runner._ffmpeg_bin", return_value=None):
                with self.assertRaises(RuntimeError) as ctx:
                    extract_carry_tail(src, dest_dir, frames=5)
            self.assertIn("last N frames", str(ctx.exception))
            self.assertFalse(list(dest_dir.glob("mmh3carry_*.mp4")))

    def test_bad_frame_count(self):
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "x.mp4")
            Path(src).write_bytes(b"x")
            with self.assertRaises(ValueError):
                extract_carry_tail(src, Path(td), frames=10)

    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):
                extract_carry_tail(os.path.join(td, "nope.mp4"), Path(td), frames=5)


if __name__ == "__main__":
    unittest.main()
