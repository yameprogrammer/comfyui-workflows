"""TRELLIS 2 mesh graph builder. No Comfy."""

from __future__ import annotations

import unittest

from lib.trellis2_mesh_runner import PROFILES, build_trellis2_prompt, list_profiles


class TestTrellis2Prompt(unittest.TestCase):
    def test_draft_is_geometry_only(self):
        g = build_trellis2_prompt(
            "in.png",
            seed=1,
            resolution="512",
            ss_steps=8,
            shape_steps=8,
            tex_steps=0,
            texture=False,
            max_tokens=32768,
            target_faces=40000,
            texture_size=1024,
            prefix="agent_trellis2_1",
        )
        types = {n["class_type"] for n in g.values()}
        self.assertIn("LoadTrellis2Models", types)
        self.assertIn("Trellis2RemoveBackground", types)
        self.assertIn("Trellis2ImageToShape", types)
        self.assertIn("Trellis2ExportTrimesh", types)
        self.assertNotIn("Trellis2ShapeToTexturedMesh", types)
        self.assertNotIn("Trellis2RasterizePBR", types)
        self.assertEqual(g["3"]["inputs"]["resolution"], "512")
        self.assertEqual(g["9"]["inputs"]["filename_prefix"], "agent_trellis2_1")

    def test_work_pbr_chain(self):
        g = build_trellis2_prompt(
            "in.png",
            seed=42,
            resolution="1024_cascade",
            ss_steps=12,
            shape_steps=12,
            tex_steps=12,
            texture=True,
            max_tokens=49152,
            target_faces=80000,
            texture_size=2048,
            prefix="agent_trellis2_42",
        )
        self.assertEqual(g["6"]["class_type"], "Trellis2ShapeToTexturedMesh")
        self.assertEqual(g["7"]["class_type"], "Trellis2ProcessMesh")
        self.assertEqual(g["8"]["class_type"], "Trellis2RasterizePBR")
        self.assertEqual(g["9"]["inputs"]["trimesh"], ["8", 0])
        self.assertEqual(g["8"]["inputs"]["original_mesh"], ["5", 0])
        self.assertEqual(g["7"]["inputs"]["target_face_count"], 80000)
        self.assertEqual(g["5"]["inputs"]["seed"], 42)

    def test_profiles_exist(self):
        p = list_profiles()
        self.assertEqual(set(p), {"draft", "work", "hero"})
        self.assertFalse(PROFILES["draft"]["texture"])
        self.assertTrue(PROFILES["work"]["texture"])
        self.assertEqual(PROFILES["work"]["resolution"], "1024_cascade")

    def test_bad_resolution_raises(self):
        with self.assertRaises(ValueError):
            build_trellis2_prompt(
                "in.png",
                seed=1,
                resolution="999",
                ss_steps=8,
                shape_steps=8,
                tex_steps=0,
                texture=False,
                max_tokens=1,
                target_faces=1,
                texture_size=512,
                prefix="x",
            )


if __name__ == "__main__":
    unittest.main()
