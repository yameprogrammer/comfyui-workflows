import unittest

from lib.midi_arrange import arrange, default_arrangement, validate_arrangement


def _skel():
    return {
        "schema": "music_skeleton.v1",
        "bpm": 96,
        "key": "C",
        "mode": "major",
        "time_signature": [4, 4],
        "chords": [
            {"start_sec": 0.0, "end_sec": 2.5, "bar": 1, "symbol": "Am", "root": "A", "quality": "min"},
            {"start_sec": 2.5, "end_sec": 5.0, "bar": 2, "symbol": "F", "root": "F", "quality": "maj"},
            {"start_sec": 5.0, "end_sec": 7.5, "bar": 3, "symbol": "C", "root": "C", "quality": "maj"},
            {"start_sec": 7.5, "end_sec": 10.0, "bar": 4, "symbol": "G", "root": "G", "quality": "maj"},
        ],
        "sections": [{"name": "A", "start_sec": 0.0, "end_sec": 10.0}],
        "melody_contour": [{"t": 0.0, "midi": 69, "dur": 0.5}],
    }


class TestArrange(unittest.TestCase):
    def test_unknown_genre(self):
        with self.assertRaises(ValueError):
            validate_arrangement({"genre": "smooth_jazz_xxx"})

    def test_harmony_only_has_no_lead_from_contour(self):
        arr = default_arrangement(genre="piano_pop", bpm=96, key="C", bars=4, keep="harmony_only")
        tracks = arrange(_skel(), arr)
        names = [t.name for t in tracks]
        self.assertNotIn("lead", names)
        pitches = [n.pitch for t in tracks for n in t.events]
        self.assertTrue(pitches)

    def test_lofi_has_drum_channel(self):
        arr = default_arrangement(genre="lofi_hiphop", bpm=90, key="C", bars=4)
        tracks = arrange(_skel(), arr)
        drums = [t for t in tracks if t.channel == 9]
        self.assertTrue(drums)
        self.assertTrue(drums[0].events)

    def test_transpose_changes_pitch(self):
        a = default_arrangement(genre="acoustic_ballad", bpm=80, key="C", bars=4)
        a["transpose"] = 0
        b = dict(a)
        b["transpose"] = 5
        pa = {n.pitch for t in arrange(_skel(), a) if t.channel != 9 for n in t.events}
        pb = {n.pitch for t in arrange(_skel(), b) if t.channel != 9 for n in t.events}
        self.assertNotEqual(pa, pb)


if __name__ == "__main__":
    unittest.main()
