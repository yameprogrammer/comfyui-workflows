import os
import tempfile
import unittest

from lib.edit_title import compose_style, parse_color, render_title


class TestEditTitle(unittest.TestCase):
    def test_parse_hex_and_name(self):
        self.assertEqual(parse_color("#ff0")[:3], (255, 255, 0))
        self.assertEqual(parse_color("yellow")[:3], (255, 225, 74))
        self.assertIsNone(parse_color("none"))

    def test_yeonung_writes_png(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "y.png")
            r = render_title("진짜요?", path, preset="yeonung", width=320, height=240, subtext="ㅋㅋ")
            self.assertTrue(r.get("ok"), r)
            self.assertGreater(os.path.getsize(path), 200)

    def test_portrait_caption_defaults_y_low(self):
        from lib.edit_title import compose_style

        # y is applied at render; compose leaves y unset
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "c.png")
            r = render_title("테스트", path, layout="caption", width=320, height=568)
            self.assertTrue(r.get("ok"), r)
            self.assertAlmostEqual(float((r.get("composed") or {}).get("y") or 0), 0.82)

    def test_yt_hook_writes_png(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "h.png")
            r = render_title("포기하지 마", path, preset="yt_hook", width=320, height=240)
            self.assertTrue(r.get("ok"), r)
            self.assertTrue(os.path.isfile(path))
            self.assertGreater(os.path.getsize(path), 200)

    def test_compose_without_preset(self):
        s = compose_style(
            layout="caption",
            color="cyan",
            size="xl",
            bubble="yellow",
            tilt=-4,
            y=0.82,
        )
        self.assertIsNone(s.get("_preset"))
        self.assertEqual(s["layout"], "caption")
        self.assertEqual(s["color"], "cyan")
        self.assertEqual(s["bubble"], "yellow")
        self.assertEqual(s["tilt"], -4.0)
        self.assertEqual(s["y"], 0.82)
        self.assertNotIn("box", s)

    def test_compose_overrides_preset_chrome(self):
        s = compose_style(preset="yt_box", bubble="#FFF8C8", box="none", tilt=3, layout="yeonung")
        self.assertEqual(s["layout"], "yeonung")
        self.assertEqual(s["bubble"], "#FFF8C8")
        self.assertNotIn("box", s)
        self.assertEqual(s["tilt"], 3.0)

    def test_agent_invented_look_writes_png(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "mix.png")
            r = render_title(
                "조금만 더",
                path,
                layout="caption",
                color="cyan",
                size="xl",
                bubble="yellow",
                tilt=-4,
                y=0.82,
                subtext="헐",
                width=320,
                height=568,
            )
            self.assertTrue(r.get("ok"), r)
            self.assertIsNone(r.get("preset"))
            self.assertEqual(r.get("layout"), "caption")
            self.assertGreater(os.path.getsize(path), 200)

    def test_split_glyphs_writes_letters(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "line.png")
            r = render_title(
                "가 나",
                path,
                layout="caption",
                width=320,
                height=240,
                split="glyphs",
            )
            self.assertTrue(r.get("ok"), r)
            self.assertEqual(r.get("glyph_count"), 2)
            man = r.get("glyphs")
            self.assertTrue(man and os.path.isfile(man))
            import json

            data = json.load(open(man, encoding="utf-8"))
            self.assertEqual(len(data["glyphs"]), 2)
            for g in data["glyphs"]:
                self.assertTrue(os.path.isfile(g["path"]))
                self.assertGreater(os.path.getsize(g["path"]), 50)

    def test_bad_place_rejected(self):
        with self.assertRaises(ValueError):
            compose_style(y=1.4)


if __name__ == "__main__":
    unittest.main()
