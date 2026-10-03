import json
import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import minimax_h3_optimized_runner as runner

_temporary = tempfile.TemporaryDirectory(prefix='h3_tool_validation_')
WORK = Path(_temporary.name)


class H3OptimizedToolTests(unittest.TestCase):
    def options(self, task):
        kw = dict(task=task, prompt='Workflow validation', aspect='9:16', duration=7, seed=42)
        if task in ('i2v', 'r2v', 'ai2v'):
            kw['image_names'] = ['first.png']
        if task == 'flf':
            kw['image_names'] = ['first.png', 'last.png']
        if task == 'v2v':
            kw['video_name'] = 'plate.mp4'
        if task == 'ai2v':
            kw['audio_name'] = 'voice.wav'
        return kw

    def test_all_tasks_preserve_model_family_and_memory_barriers(self):
        for task in runner.TASKS:
            with self.subTest(task=task):
                api, source, size = runner.build_prompt(**self.options(task))
                self.assertEqual(size, (384, 672))
                self.assertEqual(api['132']['inputs']['value'], 7)
                self.assertEqual(api['204']['inputs']['unload_all_models'], True)
                self.assertEqual(api['122']['inputs']['samples'], ['204', 0])
                self.assertEqual(api['121']['inputs']['samples'], ['204', 0])
                self.assertEqual(api['195']['class_type'], 'DenoTextEncoderUnload')
                native = task in ('t2v', 'i2v', 'flf')
                self.assertEqual(api['185']['inputs']['steps'], 20 if native else 8)
                self.assertEqual(api['194']['inputs']['step'], 15 if native else 7)
                if native:
                    self.assertIn('fl2va', api['127']['inputs']['unet_name'])
                    self.assertNotIn('192', api)
                else:
                    self.assertIn('ref2va', api['127']['inputs']['unet_name'])
                if task == 'r2v':
                    self.assertTrue(source.endswith('minimax_h3_7plus1.api.json'))

    def test_keyframes_are_rebuilt_for_second_pass(self):
        for task in ('i2v', 'flf'):
            api, _, _ = runner.build_prompt(**self.options(task))
            self.assertEqual(api['202']['inputs']['conditioning'], ['217', 0])
            self.assertEqual(api['217']['inputs']['positive_conditioning'], ['214', 0])
            self.assertEqual(api['214']['inputs']['width'], ['215', 1])
            self.assertEqual(api['215']['inputs']['expression'], 'a * 2')
            self.assertEqual(api['214']['inputs']['first_frame'], ['210', 0])
            if task == 'flf':
                self.assertEqual(api['214']['inputs']['last_frame'], ['211', 0])

    def test_reference_inputs_use_generated_audio_and_bounded_audio(self):
        api, _, _ = runner.build_prompt(**self.options('ai2v'))
        self.assertEqual(api['141']['inputs']['ref_audios.ref_audio_0'], ['212', 0])
        self.assertEqual(api['212']['inputs']['duration'], ['132', 0])
        self.assertEqual(api['144']['inputs']['audio'], ['121', 0])
        api, _, _ = runner.build_prompt(**self.options('v2v'))
        self.assertEqual(api['210']['inputs']['force_rate'], 24)
        self.assertEqual(api['210']['inputs']['frame_load_cap'], ['131', 1])

    def test_dry_run_has_no_server_or_staging_side_effects(self):
        image = WORK/'source.png'
        video = WORK/'source.mp4'
        audio = WORK/'source.wav'
        for file in (image, video, audio):
            file.touch()
        with patch.object(runner, 'ensure_engine') as engine, patch.object(runner, 'queue_prompt') as queue, patch.object(runner.shutil, 'copy2') as copy:
            for task in runner.TASKS:
                images = [str(image)] if task in ('i2v','r2v','ai2v') else [str(image),str(image)] if task=='flf' else []
                result = runner.generate(task=task, prompt='Validation', images=images,
                    video=str(video) if task=='v2v' else None,
                    audio=str(audio) if task=='ai2v' else None,
                    output_path=str(WORK/f'{task}.mp4'), aspect='9:16', seed=42, dry_run=True)
                self.assertTrue(result['dry_run'])
                self.assertEqual(result['output_size'], [768,1344])
                self.assertTrue(Path(result['api_path']).is_file())
            engine.assert_not_called()
            queue.assert_not_called()
            copy.assert_not_called()

    def test_invalid_combinations_fail_before_queueing(self):
        for options in [dict(task='r2v',image_names=[]),dict(task='i2v',image_names=['a','b']),
                        dict(task='flf',image_names=['a']),dict(task='v2v',video_name='a',attention='sol'),
                        dict(task='ai2v',image_names=['a']),dict(task='t2v',width=145,height=256)]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                runner.build_prompt(prompt='Validation', **options)


if __name__ == '__main__':
    unittest.main(verbosity=2)
