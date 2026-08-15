import os
import tempfile
import unittest

from lib.edit_fonts import known_font_names, list_fonts, resolve_font
from lib.edit_title import render_title


class TestEditFonts(unittest.TestCase):
    def test_aliases_listed(self):
        names = known_font_names()
        for n in ("yeonung", "hook", "soft", "display", "gothic", "gothic_bold"):
            self.assertIn(n, names)

    def test_gothic_resolves_on_this_machine(self):
        path = resolve_font("gothic")
        self.assertTrue(path, "expected a system Hangul gothic")
        self.assertTrue(os.path.isfile(path))

    def test_unknown_alias_returns_none(self):
        self.assertIsNone(resolve_font("not_a_real_font_zzz"))

    def test_path_still_works(self):
        hit = resolve_font("gothic")
        self.assertEqual(resolve_font(hit), os.path.abspath(hit))

    def test_render_with_alias(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "f.png")
            r = render_title("포기하지 마", path, font="gothic_bold", width=320, height=240)
            self.assertTrue(r.get("ok"), r)
            self.assertGreater(os.path.getsize(path), 200)

    def test_list_fonts_ready_flag(self):
        rows = {r["name"]: r for r in list_fonts()}
        self.assertTrue(rows["gothic"]["ready"])


if __name__ == "__main__":
    unittest.main()
