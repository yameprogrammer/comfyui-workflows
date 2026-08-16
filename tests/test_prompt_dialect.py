"""prompt_dialect picker — no Comfy."""

from __future__ import annotations

import unittest

from lib.prompt_dialect import DIALECTS, get_dialect, search_dialects


class TestPromptDialect(unittest.TestCase):
    def test_all_still_families_present(self):
        ids = {d["id"] for d in DIALECTS}
        self.assertGreaterEqual(
            ids,
            {
                "krea",
                "zimage",
                "illustrious",
                "anima",
                "flux1",
                "flux_fill",
                "flux2_klein",
                "sdxl",
                "qwen_edit",
                "ideogram",
            },
        )

    def test_aliases(self):
        self.assertEqual(get_dialect("generate_krea")["id"], "krea")
        self.assertEqual(get_dialect("flux")["id"], "flux1")
        self.assertEqual(get_dialect("klein")["id"], "flux2_klein")
        self.assertEqual(get_dialect("juggernaut")["id"], "sdxl")
        self.assertIsNone(get_dialect("not-a-model"))

    def test_pick_cinematic_ranks_krea(self):
        hits = search_dialects("시네 키프레임", limit=3)
        self.assertEqual(hits[0]["id"], "krea")

    def test_pick_flux_fill(self):
        hits = search_dialects("flux fill mask", limit=3)
        self.assertEqual(hits[0]["id"], "flux_fill")

    def test_cards_have_official_and_template(self):
        for d in DIALECTS:
            self.assertTrue(d["official"], d["id"])
            self.assertTrue(d["template"], d["id"])
            self.assertTrue(d["ref"].endswith(".md"), d["id"])


if __name__ == "__main__":
    unittest.main()
