"""MiniMax Music 3 graph knobs. No Comfy / no GPU."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.minimax_music_runner import (
    DEFAULT_CFG,
    DEFAULT_ENCODE_CFG,
    DEFAULT_STEPS,
    TILED_OVERLAP,
    TILED_TILE_SIZE,
    build_music3_api_prompt,
    clamp_duration,
    default_duration,
    resolve_tiled_decode,
)


def _run(args):
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


class TestMusic3Defaults(unittest.TestCase):
    def test_official_sampler_defaults(self):
        self.assertEqual(DEFAULT_STEPS, 30)
        self.assertEqual(DEFAULT_CFG, 1.7)
        self.assertEqual(DEFAULT_ENCODE_CFG, 1.7)

    def test_duration_ceiling_by_mode(self):
        self.assertEqual(default_duration("song"), 180.0)
        self.assertEqual(default_duration("bgm"), 60.0)
        self.assertEqual(default_duration("instrumental"), 60.0)
        self.assertEqual(clamp_duration(1.0), 4.0)
        self.assertEqual(clamp_duration(400.0), 300.0)

    def test_tiled_auto_at_four_minutes(self):
        self.assertFalse(resolve_tiled_decode(None, 180.0))
        self.assertTrue(resolve_tiled_decode(None, 240.0))
        self.assertTrue(resolve_tiled_decode(None, 300.0))
        self.assertFalse(resolve_tiled_decode(False, 300.0))
        self.assertTrue(resolve_tiled_decode(True, 60.0))

    def test_song_graph_plain_decode(self):
        g = build_music3_api_prompt(duration=180.0, seed=7, tiled_decode=False)
        self.assertEqual(g["4"]["inputs"]["max_duration"], 180.0)
        self.assertEqual(g["4"]["inputs"]["cfg_scale"], 1.7)
        self.assertEqual(g["7"]["inputs"]["steps"], 30)
        self.assertEqual(g["7"]["inputs"]["cfg"], 1.7)
        self.assertEqual(g["7"]["inputs"]["sampler_name"], "euler")
        self.assertEqual(g["7"]["inputs"]["scheduler"], "simple")
        self.assertEqual(g["8"]["class_type"], "VAEDecodeAudio")

    def test_long_song_tiled_decode_node(self):
        g = build_music3_api_prompt(duration=300.0, seed=7, tiled_decode=True)
        self.assertEqual(g["8"]["class_type"], "VAEDecodeAudioTiled")
        self.assertEqual(g["8"]["inputs"]["tile_size"], TILED_TILE_SIZE)
        self.assertEqual(g["8"]["inputs"]["overlap"], TILED_OVERLAP)
        self.assertEqual(g["4"]["inputs"]["max_duration"], 300.0)
        self.assertEqual(g["9"]["inputs"]["audio"], ["8", 0])

    def test_cli_help_mentions_ceiling(self):
        r = _run(["scripts/generate_minimax_music.py", "--help"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ceiling", r.stdout.lower())
        self.assertIn("--tiled-decode", r.stdout)
        self.assertIn("1.7", r.stdout)
        self.assertIn("180", r.stdout)


if __name__ == "__main__":
    unittest.main()
