import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.minimax_h3_runner import build_api_prompt


class DecodeBarrierTests(unittest.TestCase):
    def test_decoders_wait_for_final_sampler_and_model_release(self):
        for task in ('t2v', 'i2v', 'flf', 'r2v'):
            for scale in (1.0, 2.0):
                with self.subTest(task=task, scale=scale):
                    api = build_api_prompt(task=task, prompt='Validation', seed=42,
                        duration=8, megapixels=0.5625, steps=20,
                        first_frame_name='first.png', last_frame_name='last.png',
                        ref_image_names=['first.png'], latent_upscale=scale)
                    barrier = api['144']
                    self.assertEqual(barrier['class_type'], 'VRAM_Debug')
                    self.assertEqual(barrier['inputs']['any_input'],
                                     ['125' if scale == 1 else '138', 0])
                    for flag in ('empty_cache', 'gc_collect', 'unload_all_models'):
                        self.assertTrue(barrier['inputs'][flag])
                    for decoder in ('121', '122'):
                        self.assertEqual(api[decoder]['inputs']['samples'], ['144', 0])
                    samplers = [n for n in api.values()
                                if n['class_type'] == 'SamplerCustomAdvanced']
                    self.assertEqual(len(samplers), 1 if scale == 1 else 2)


    def test_sampling_waits_for_encoder_cleanup(self):
        for task in ('t2v', 'i2v', 'flf', 'r2v', 'a2v'):
            with self.subTest(task=task):
                api = build_api_prompt(task=task, prompt='Validation', seed=42,
                    duration=8, megapixels=0.4, steps=20,
                    first_frame_name='first.png', last_frame_name='last.png',
                    ref_image_names=['first.png'], ref_audio_name='voice.wav')
                def ancestors(node):
                    found = set()
                    for value in api[node]['inputs'].values():
                        if isinstance(value, list) and len(value) == 2 and str(value[0]) in api:
                            parent = str(value[0])
                            found.add(parent)
                            found.update(ancestors(parent))
                    return found
                cleanup = api['145']
                self.assertEqual(cleanup['class_type'], 'VRAM_Debug')
                self.assertTrue(cleanup['inputs']['unload_all_models'])
                self.assertEqual(api['125']['inputs']['latent_image'], ['145', 0])
                self.assertIn('131', ancestors('145'))
                self.assertIn('145', ancestors('125'))
                encoders = {node for node, value in api.items()
                            if value['class_type'] in ('MiniMaxH3ImageToVideo', 'MiniMaxH3ReferenceToVideo')}
                self.assertTrue(encoders <= ancestors('145'))
                self.assertEqual(api['126']['inputs']['conditioning'], ['131', 0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
