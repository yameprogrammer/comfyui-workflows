import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lib import moss_speech_launcher

ROOT = Path(__file__).resolve().parents[1]


class MossLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        py = self.root / '.venv/Scripts/python.exe'
        py.parent.mkdir(parents=True)
        py.touch()
        (self.root/'moss_speech_worker.py').touch()
        (self.root/'moss_worker.py').touch()

    def test_speech_uses_selected_isolated_root_without_inherited_pythonpath(self):
        argv = ['generate_moss_tts.py', '-t', '안녕하세요.', '-o', str(self.root/'output')]
        with patch.dict(os.environ, {'MOSS_SPEECH_ROOT': str(self.root), 'PYTHONPATH': 'untrusted-parent-path'}), patch.object(sys, 'argv', argv), patch.object(moss_speech_launcher.subprocess, 'call', return_value=0) as launch:
            self.assertEqual(moss_speech_launcher.run('tts'), 0)
        command = launch.call_args.args[0]
        self.assertEqual(command[0], str(self.root/'.venv/Scripts/python.exe'))
        self.assertIn('안녕하세요.', command)
        self.assertNotIn('PYTHONPATH', launch.call_args.kwargs['env'])
        self.assertEqual(launch.call_args.kwargs['env']['PYTHONNOUSERSITE'], '1')

    def test_blank_speech_is_rejected_without_worker_launch(self):
        with patch.object(sys, 'argv', ['tts', '-t', ' ', '-o', str(self.root/'out')]), patch.object(moss_speech_launcher.subprocess, 'call') as launch:
            with self.assertRaises(SystemExit) as error:
                moss_speech_launcher.run('tts')
            self.assertEqual(error.exception.code, 2)
            launch.assert_not_called()

    def test_transcriber_uses_selected_root_and_propagates_worker_result(self):
        spec = importlib.util.spec_from_file_location('transcribe_cli', ROOT/'scripts/transcribe_moss.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = self.root/'input.wav';source.touch()
        argv = ['transcribe_moss.py', '-i', str(source), '-o', str(self.root/'transcript')]
        with patch.dict(os.environ, {'MOSS_TRANSCRIBE_ROOT': str(self.root)}), patch.object(sys, 'argv', argv), patch.object(module.subprocess, 'call', return_value=2) as launch:
            self.assertEqual(module.main(), 2)
        self.assertEqual(launch.call_args.args[0][0], str(self.root/'.venv/Scripts/python.exe'))
        self.assertEqual(launch.call_args.kwargs['cwd'], self.root)


if __name__ == '__main__':
    unittest.main()
