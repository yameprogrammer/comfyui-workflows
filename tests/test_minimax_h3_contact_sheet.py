"""H3 contact-sheet dialect helper. No Comfy."""

from __future__ import annotations

import unittest

from lib.minimax_h3_runner import build_contact_sheet_prompt

_REQUIRED = (
    "subject_definitions",
    "summary",
    "retention_analysis",
    "detailed_description",
    "overall_soundscape",
    "non_diegetic_music",
)


class TestContactSheetPrompt(unittest.TestCase):
    def test_six_fields_and_roles(self):
        p = build_contact_sheet_prompt()
        for name in _REQUIRED:
            self.assertIn(name + ":", p)
        self.assertIn("<Picture 1>", p)
        self.assertIn("<Picture 2>", p)
        self.assertIn("outfit only", p.lower())
        self.assertIn("not a video", p.lower())
        self.assertIn("Photo 1:", p)
        self.assertIn("Photo 2:", p)
        self.assertIn("Photo 3:", p)
        self.assertIn("non_diegetic_music: N/A", p)
        self.assertNotIn("USER DIRECTION", p)

    def test_extra_is_priority_not_role_swap(self):
        p = build_contact_sheet_prompt(extra="slim adult, narrow shoulders")
        self.assertIn("USER DIRECTION — HIGHEST PRIORITY", p)
        self.assertIn("slim adult, narrow shoulders", p)
        self.assertIn("keep Picture 1 identity and Picture 2 outfit roles", p)


if __name__ == "__main__":
    unittest.main()
