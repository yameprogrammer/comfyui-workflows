import unittest

from lib.music_theory import parse_chord, transpose_symbol, voicing_midis


class TestParseChord(unittest.TestCase):
    def test_major_triad(self):
        c = parse_chord("C")
        self.assertEqual(c["root"], "C")
        self.assertEqual(c["quality"], "maj")

    def test_minor_and_seventh(self):
        self.assertEqual(parse_chord("Am")["quality"], "min")
        self.assertEqual(parse_chord("G7")["quality"], "7")
        self.assertEqual(parse_chord("Fmaj7")["quality"], "maj7")
        self.assertEqual(parse_chord("C/E")["bass"], "E")

    def test_transpose_roundtrip(self):
        self.assertEqual(transpose_symbol("Am", 3), "Cm")
        self.assertEqual(transpose_symbol("F#m", -1), "Fm")

    def test_voicing_c_major(self):
        midis = voicing_midis("C", octave=4)
        self.assertEqual(midis, [60, 64, 67])


if __name__ == "__main__":
    unittest.main()
