import os
import tempfile
import unittest

from lib.edit_compile_ffmpeg import compile_ffmpeg
from lib.edit_look import compose_key, compose_look, look_filter
from lib.edit_timeline import from_clips


class TestEditLook(unittest.TestCase):
    def test_named_night_has_temperature(self):
        look = compose_look("night")
        self.assertEqual(look["name"], "night")
        self.assertLess(look["temperature"], 0)
        flt = look_filter(look)
        self.assertIn("eq=", flt)
        self.assertIn("colorbalance=", flt)

    def test_parts_override_shortcut(self):
        look = compose_look({"name": "punch", "saturation": 0.5, "temperature": 0.2})
        self.assertAlmostEqual(look["saturation"], 0.5)
        self.assertAlmostEqual(look["temperature"], 0.2)
        self.assertGreater(look["contrast"], 1.0)

    def test_none_is_identity_filter(self):
        self.assertEqual(look_filter(compose_look("none")), "")

    def test_key_green(self):
        k = compose_key({"color": "green", "similarity": 0.2})
        self.assertEqual(k["color"], "0x00FF00")
        self.assertAlmostEqual(k["similarity"], 0.2)

    def test_compile_look_and_key_in_graph(self):
        with tempfile.TemporaryDirectory() as td:
            a = os.path.join(td, "a.mp4")
            open(a, "wb").write(b"x")
            tl = from_clips([a], durations=[1.0], width=320, height=240)
            tl["look"] = {"name": "night", "saturation": 1.2}
            tl["clips"][0]["key"] = {"color": "green", "background": "#101018"}
            spec = compile_ffmpeg(tl, os.path.join(td, "out.mp4"))
        self.assertIn("colorbalance=", spec["graph"])
        self.assertIn("chromakey=0x00FF00", spec["graph"])
        self.assertIn("saturation=1.200", spec["graph"])


if __name__ == "__main__":
    unittest.main()
