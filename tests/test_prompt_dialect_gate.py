import unittest

from lib.prompt_dialect_gate import check_anima_prompt, check_motion_prompt, check_music_caption


class TestPromptDialectGate(unittest.TestCase):
    def test_anima_soup_refused(self):
        self.assertFalse(check_anima_prompt("").get("ok"))
        self.assertFalse(
            check_anima_prompt(
                "1girl, anime masterpiece, exquisite face, detailed lighting, rich colors, studio quality, 8k render"
            ).get("ok")
        )
        self.assertTrue(
            check_anima_prompt(
                "masterpiece, best quality, anime illustration, 1girl, solo, black hair, standing in rain, cel shading"
            ).get("ok")
        )

    def test_music_visual_refused(self):
        self.assertFalse(check_music_caption("a woman stands in rain, photoreal, 8k").get("ok"))
        self.assertTrue(check_music_caption("K-Pop ballad, female vocal, piano, 90 BPM").get("ok"))
        three = (
            "Global Metadata: K-pop ballad, 84 BPM\n\n"
            "Vocal Details: Korean female lead\n\n"
            "Arrangement: guitar verse, drums on chorus"
        )
        self.assertTrue(check_music_caption(three).get("ok"))

    def test_i2v_look_essay_not_ok(self):
        self.assertFalse(
            check_motion_prompt("beautiful face, wearing a black dress, masterpiece 8k").get("ok")
        )
        self.assertTrue(
            check_motion_prompt("slow push-in, subtle breathing, locked medium frame, continuous").get("ok")
        )


if __name__ == "__main__":
    unittest.main()
