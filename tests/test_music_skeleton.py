import os
import tempfile
import unittest

from lib.music_skeleton import load_skeleton, save_skeleton, skeleton_from_symbols


class TestSkeletonFromSymbols(unittest.TestCase):
    def test_four_chords(self):
        sk = skeleton_from_symbols(["Am", "F", "C", "G"], bpm=96, key="C")
        self.assertEqual(sk["schema"], "music_skeleton.v1")
        self.assertEqual(len(sk["chords"]), 4)
        self.assertEqual(sk["chords"][0]["symbol"], "Am")
        self.assertEqual(sk["bpm"], 96)
        self.assertGreater(sk["chords"][-1]["end_sec"], 0)

    def test_roundtrip_json(self):
        sk = skeleton_from_symbols(["C"], bpm=120, key="C")
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "s.json")
            save_skeleton(sk, path)
            back = load_skeleton(path)
        self.assertEqual(back["chords"][0]["symbol"], "C")


if __name__ == "__main__":
    unittest.main()
