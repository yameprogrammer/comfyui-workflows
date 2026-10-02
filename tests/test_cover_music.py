import argparse
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from lib import cover_music as c

class CoverMusicTests(unittest.TestCase):
    def test_toolbox_outputs_rejected(self):
        with self.assertRaises(ValueError): c.external(c.ROOT/'outputs'/'song')
    def test_segment_out_of_bounds_before_write(self):
        with tempfile.TemporaryDirectory() as t:
            r=Path(t)/'run'
            with patch.object(c,'probe',return_value={'format':{'duration':'20'}}):
                with self.assertRaises(ValueError): c.prepare(argparse.Namespace(run=r,audio='source.wav',start=19,seconds=10,server='localhost'))
            self.assertFalse(r.exists())
    def test_nonfinite_duration_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError): c.prepare(argparse.Namespace(run=t,audio='x',start=0,seconds=float('nan'),server='localhost'))
    def test_existing_run_not_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/'keep';f.write_text('unchanged')
            with self.assertRaises(ValueError): c.prepare(argparse.Namespace(run=t))
            self.assertEqual(f.read_text(),'unchanged')
    def test_duplicate_job_never_queued(self):
        with patch('lib.comfy_client.queue_prompt') as queue:
            with self.assertRaises(ValueError): c.submit(Path('.'),{'jobs':{'render':{'prompt_id':'existing'}}},'render',{})
            queue.assert_not_called()
    def test_timeout_retains_prompt_id_for_recovery(self):
        with tempfile.TemporaryDirectory() as t:
            r=Path(t);c.save_run(r,{'server':'localhost','jobs':{'render':{'prompt_id':'saved-id','state':'submitted'}}})
            with patch('lib.comfy_client.wait_for_history',side_effect=TimeoutError('test timeout')):
                with self.assertRaises(TimeoutError): c.collect(argparse.Namespace(run=t,stage='render',timeout=1))
            d=json.loads((r/'run.json').read_text());self.assertEqual(d['jobs']['render']['prompt_id'],'saved-id');self.assertEqual(d['jobs']['render']['state'],'submitted')
    def test_completed_collection_is_idempotent(self):
        with tempfile.TemporaryDirectory() as t:
            c.save_run(Path(t),{'jobs':{'render':{'prompt_id':'id','state':'complete'}}})
            with patch('lib.comfy_client.wait_for_history') as wait:
                self.assertEqual(c.collect(argparse.Namespace(run=t,stage='render',timeout=1))['state'],'complete');wait.assert_not_called()
    def test_caption_selection_preserves_uncertainty(self):
        with tempfile.TemporaryDirectory() as t:
            r=Path(t);c.save_run(r,{'segment':[10,20]})
            data={'events':[{'tStartMs':x*1000,'segs':[{'utf8':s}]} for x,s in [(1,'outside'),(12,'inside'),(13,'inside'),(15,'[Music]'),(20,'outside')]]}
            c.write_json(r/'captions.json',data)
            result=c.captions(argparse.Namespace(run=t,input=r/'captions.json'))
            self.assertEqual((r/'lyrics_auto.txt').read_text(),'[Verse]\ninside\n');self.assertEqual(result['status'],'automatic_unverified')
    def test_export_clipped_audio_does_not_encode(self):
        with tempfile.TemporaryDirectory() as t:
            with patch.object(c,'metrics',return_value={'non_silent':True,'clipped_samples':1}),patch.object(c,'call') as encode:
                with self.assertRaises(ValueError): c.export(argparse.Namespace(out=Path(t)/'export',audio='x.wav'))
                encode.assert_not_called()

if __name__=='__main__': unittest.main()
