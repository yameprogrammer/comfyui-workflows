import os
import tempfile
import unittest

from lib.midi_smf import MidiNote, MidiTrack, write_smf


class TestWriteSmf(unittest.TestCase):
    def test_writes_mthd(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "t.mid")
            write_smf(
                path,
                [MidiTrack("piano", 0, 0, [MidiNote(60, 0, 480, 80)])],
                bpm=120,
            )
            data = open(path, "rb").read()
            self.assertTrue(data.startswith(b"MThd"))
            self.assertIn(b"MTrk", data)
            self.assertGreater(os.path.getsize(path), 20)


if __name__ == "__main__":
    unittest.main()
