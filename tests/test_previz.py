import subprocess
import sys
import unittest
from pathlib import Path

from lib.previz_blender import (
    PRESETS,
    ROLE_COLORS,
    evaluate_plate_qa,
    h3_r2v_prompt,
    list_presets,
    nearest_role,
)
from lib.tool_intent import search_intents

_ROOT = Path(__file__).resolve().parents[1]


def _ok_report() -> dict:
    return {
        "cameras": [
            {
                "name": "PrevizCam",
                "clip_start": 0.1,
                "constraints": [],
                "inside_meshes": [],
                "outside_corridor": False,
            }
        ],
        "active_camera": "PrevizCam",
        "meshes": [
            {"name": "Hero", "role": "hero", "color": list(ROLE_COLORS["hero"])},
            {"name": "Floor", "role": "floor", "color": list(ROLE_COLORS["floor"])},
            {"name": "Wall_L", "role": "set", "color": list(ROLE_COLORS["set"])},
            {"name": "Mark_Start", "role": "mark", "color": list(ROLE_COLORS["mark"])},
        ],
    }


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

    def test_role_colors_are_distinct(self):
        mapped = {name: nearest_role(col) for name, col in ROLE_COLORS.items()}
        self.assertEqual(mapped, {k: k for k in ROLE_COLORS})
        self.assertNotEqual(ROLE_COLORS["mark"], ROLE_COLORS["extra"])

    def test_qa_passes_stock_character_plate(self):
        qa = evaluate_plate_qa(_ok_report())
        self.assertTrue(qa["ok"], qa["errors"])

    def test_qa_fails_color_collision_on_set(self):
        report = _ok_report()
        report["meshes"].append(
            {"name": "Wall_R", "role": "hero", "color": list(ROLE_COLORS["hero"])}
        )
        qa = evaluate_plate_qa(report)
        self.assertFalse(qa["ok"])
        blob = " ".join(qa["errors"])
        self.assertIn("COLOR_COLLISION", blob)

    def test_qa_fails_camera_constrained_and_clip(self):
        report = _ok_report()
        report["cameras"][0]["constraints"] = ["TRACK_TO"]
        report["cameras"][0]["clip_start"] = 10.0
        qa = evaluate_plate_qa(report)
        blob = " ".join(qa["errors"])
        self.assertIn("CAMERA_CONSTRAINED", blob)
        self.assertIn("CLIP_START", blob)

    def test_qa_fails_camera_inside_geo(self):
        report = _ok_report()
        report["cameras"][0]["inside_meshes"] = ["Wall_L"]
        qa = evaluate_plate_qa(report)
        self.assertTrue(any("CAMERA_INSIDE_GEO" in e for e in qa["errors"]))

    def test_qa_fails_outside_corridor(self):
        report = _ok_report()
        report["cameras"][0]["outside_corridor"] = True
        qa = evaluate_plate_qa(report)
        self.assertTrue(any("CAMERA_OUTSIDE_SET" in e for e in qa["errors"]))

    def test_qa_required_camera_missing(self):
        qa = evaluate_plate_qa(_ok_report(), required_camera="Shot_B")
        self.assertTrue(any("CAMERA_MISSING" in e for e in qa["errors"]))

    def test_qa_object_plate_needs_prop(self):
        report = _ok_report()
        report["meshes"] = [
            {"name": "Floor", "role": "floor", "color": list(ROLE_COLORS["floor"])},
            {"name": "PropBall", "role": "prop", "color": list(ROLE_COLORS["prop"])},
        ]
        qa = evaluate_plate_qa(report, hero="object")
        self.assertTrue(qa["ok"], qa["errors"])
        qa_char = evaluate_plate_qa(report, hero="character")
        self.assertFalse(qa_char["ok"])

    def test_cli_help_lists_new_flags(self):
        r = subprocess.run(
            [sys.executable, str(_ROOT / "scripts" / "generate_previz.py"), "-h"],
            cwd=_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("--camera", r.stdout)
        self.assertIn("--save-blend", r.stdout)
        self.assertIn("--list-cameras", r.stdout)

    def test_cli_list_cameras_does_not_require_output(self):
        r = subprocess.run(
            [sys.executable, str(_ROOT / "scripts" / "generate_previz.py"), "--list-cameras"],
            cwd=_ROOT,
            capture_output=True,
            text=True,
        )
        combined = r.stderr + r.stdout
        self.assertNotIn("--output/-o required", combined)

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
