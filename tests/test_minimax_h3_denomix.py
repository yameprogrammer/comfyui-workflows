import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lib import minimax_h3_denomix_runner as runner
from lib.tool_intent import search_intents


class DenoMixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root / 'reference.png'
        self.image.write_bytes(b'unit-test-reference')

    def options(self, **extra):
        return dict(prompt='Validation prompt', images=[str(self.image)], output_path=str(self.root/'clip.mp4'), **extra)

    def test_alignment_is_operational_request_limit_not_aligned_time_cap(self):
        self.assertEqual(runner.aligned_frames(5), 124)
        self.assertEqual(runner.aligned_frames(10), 243)
        self.assertEqual(runner.aligned_frames(.2), 5)
        self.assertEqual(runner.aligned_frames(10)/24, 10.125)

    def test_bad_duration_fails_before_io_or_submission(self):
        with patch.object(runner, 'model_status') as status, patch.object(runner, 'queue_prompt') as submit:
            for seconds in [-1, 0, float('nan'), float('inf'), -float('inf'), 10.00001, 15]:
                with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                    runner.generate(**self.options(duration=seconds))
            status.assert_not_called()
            submit.assert_not_called()
            self.assertFalse((self.root/'clip.api.json').exists())

    def test_graph_preserves_eight_plus_two_and_frozen_audio(self):
        api, _, frames = runner.build_prompt(prompt='Validation', image_names=['a.png'], duration=10, seed=9)
        self.assertEqual(frames, 243)
        self.assertEqual(api['132']['inputs']['value'], 10)
        self.assertEqual(api['185']['inputs']['steps'], 8)
        self.assertEqual(api['194']['inputs']['step'], 6)
        self.assertEqual(api['125']['inputs']['sigmas'], ['185', 0])
        self.assertEqual(api['203']['inputs']['sigmas'], ['194', 1])
        self.assertEqual(api['218']['inputs']['mask'], ['217', 0])
        self.assertEqual(api['217']['inputs']['value'], 0)
        self.assertIn('rank_16', api['216']['inputs']['lora_name'])
        self.assertEqual(api['122']['inputs']['samples'], ['204', 0])
        self.assertEqual(api['121']['inputs']['samples'], ['204', 0])
        self.assertEqual(api['144']['inputs']['audio'], ['121', 0])

    def test_dry_run_is_offline_and_keeps_alignment_metadata(self):
        with patch.object(runner, 'model_status') as status, patch.object(runner, 'queue_prompt') as submit, patch.object(runner.shutil, 'copy2') as stage:
            result = runner.generate(**self.options(duration=10, seed=8, dry_run=True))
            self.assertEqual(result['frame_count'], 243)
            self.assertEqual(result['aligned_duration_sec'], 10.125)
            self.assertEqual(result['status'], 'dry_run')
            status.assert_not_called(); submit.assert_not_called(); stage.assert_not_called()

    def test_busy_queue_never_stages_or_submits(self):
        state = dict(available=True, running_ids=['user-job'], pending_ids=[])
        with patch.object(runner, 'model_status', return_value=state), patch.object(runner, 'queue_prompt') as submit, patch.object(runner.shutil, 'copy2') as copy:
            with self.assertRaisesRegex(RuntimeError, 'occupied'):
                runner.generate(**self.options())
            submit.assert_not_called(); copy.assert_not_called()
        self.assertEqual(json.loads((self.root/'clip.meta.json').read_text())['status'], 'failed')

    def test_timeout_preserves_prompt_id_and_leaves_job_running(self):
        state = dict(available=True, running_ids=[], pending_ids=[])
        with patch.object(runner, 'model_status', return_value=state), patch.object(runner, 'get_comfy_input_dir', return_value=str(self.root/'input')), patch.object(runner, 'queue_prompt', return_value='test-prompt') as submit, patch.object(runner, 'wait_for_history', side_effect=TimeoutError('still running')):
            with self.assertRaises(TimeoutError):
                runner.generate(**self.options())
            self.assertEqual(submit.call_args.kwargs['ensure'], False)
            self.assertEqual(submit.call_args.kwargs['retry_on_connection_error'], False)
        meta = json.loads((self.root/'clip.meta.json').read_text())
        self.assertEqual(meta['status'], 'pending')
        self.assertEqual(meta['prompt_id'], 'test-prompt')
        self.assertIn('--job-id test-prompt', meta['job_lookup'])

    def test_remote_server_and_output_collisions_are_rejected(self):
        with self.assertRaises(ValueError):
            runner.generate(**self.options(server='example.com:8188'))
        (self.root/'clip.mp4').touch()
        with self.assertRaises(FileExistsError):
            runner.generate(**self.options())

    def test_status_detects_missing_models_without_autostart(self):
        with patch.object(runner, 'get_system_stats', return_value={}) as stats, patch.object(runner, 'get_queue', return_value={}) as queue, patch.object(runner, '_http_json', return_value={}):
            state = runner.model_status()
            self.assertFalse(state['available'])
            self.assertIn('UNETLoader', state['missing_nodes'])
            stats.assert_called_once_with(runner.DEFAULT_SERVER, ensure=False)
            queue.assert_called_once_with(runner.DEFAULT_SERVER, ensure=False)

    def test_discovery_finds_new_tool(self):
        self.assertEqual(search_intents('denomix')[0]['id'], 'minimax_h3_denomix')


if __name__ == '__main__':
    unittest.main()
