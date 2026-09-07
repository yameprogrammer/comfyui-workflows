import subprocess
import sys
import unittest
from pathlib import Path

from lib.previz_blender import PRESETS, h3_r2v_prompt, list_presets
from lib.tool_intent import search_intents

_ROOT = Path(__file__).resolve().parents[1]


class TestPreviz(unittest.TestCase):
    def test_presets_include_corridor_follow(self):
        names = list_presets()
        self.assertIn("corridor_follow", names)
        self.assertEqual(set(names), set(PRESETS))

    def test_intent_previz_korean_ranks_first(self):
        hits = search_intents("블렌더 프리비즈 카메라 경로", limit=5)
        self.assertTrue(hits)
        self.assertEqual(hits[0]["id"], "camera_previz")

    def test_intent_playblast_english(self):
        hits = search_intents("previz playblast blender camera lock", limit=5)
        ids = [h["id"] for h in hits]
        self.assertIn("camera_previz", ids)
        self.assertEqual(ids[0], "camera_previz")

    def test_intent_custom_scene_words(self):
        hits = search_intents("커스텀 장면 급카메라 from-scene", limit=5)
        self.assertEqual(hits[0]["id"], "camera_previz")

    def test_object_prompt_is_not_a_person(self):
        obj = h3_r2v_prompt("object")
        self.assertIn("<Picture 1>", obj)
        self.assertIn("object", obj.lower())
        self.assertNotIn("person in <Picture 1>", obj)

    def test_cli_rejects_mode_collision(self):
        r = subprocess.run(
            [
                sys.executable,
                str(_ROOT / "scripts" / "generate_previz.py"),
                "--preset",
                "orbit",
                "--from-scene",
                "-o",
                "x.mp4",
            ],
            cwd=_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("only one", (r.stderr + r.stdout).lower())


if __name__ == "__main__":
    unittest.main()
