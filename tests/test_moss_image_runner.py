import json
import io
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from PIL import Image

from lib import comfy_client
from lib import moss_image_runner as moss


def fake_schema():
    info = {'CLIPLoader': {'input': {'required': {'type': [['moss_image']]}}}}
    for mode in moss.MODES:
        for node in moss.template(mode).values():
            kind = node['class_type']
            definition = info.setdefault(kind, {'input': {'required': {}}})
            key = moss.MODEL_INPUTS.get(kind)
            if key:
                definition['input']['required'].setdefault(key, [[]])[0].append(node['inputs'][key])
    return info


class MossValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.first = self.root / 'first.png'
        self.second = self.root / 'second.png'
        Image.new('RGB', (768, 768), 'blue').save(self.first)
        Image.new('RGB', (768, 768), 'red').save(self.second)
        self.layout = self.root / 'layout.json'
        self.layout.write_text(json.dumps({'width':768,'height':768,'prompt':'A poster',
            'boxes':[{'x':20,'y':20,'width':400,'height':100,'type':'text','text':'MOSS'}]}))

    def tearDown(self):
        self.tmp.cleanup()

    def options(self, mode):
        options = {'mode':mode,'prompt':'A clear test scene'}
        if mode == 'layout': options.update(layout=self.layout, prompt=None)
        if mode == 'edit': options['images']=[self.first]
        if mode == 'multi-edit': options['images']=[self.first,self.second]
        if mode in ('control','color'): options['color_map']=self.first
        if mode in ('control','depth'): options['depth_map']=self.second
        return options

    def test_all_presets_keep_mode_specific_sampling(self):
        for mode in moss.MODES:
            with self.subTest(mode=mode):
                graph, records, layout = moss.prepare(**self.options(mode))
                expected=('euler','normal',30,4.0) if mode in moss.EDIT_MODES else ('er_sde','simple',25,3.0 if mode in moss.CONTROL_MODES else 2.5)
                sampler=graph['7']['inputs']
                self.assertEqual(tuple(sampler[k] for k in ['sampler_name','scheduler','steps','cfg']),expected)
                self.assertNotIn('ModelSamplingSD3',[n['class_type'] for n in graph.values()])

    def test_zero_seed_empty_negative_and_overrides(self):
        graph,_,_=moss.prepare(mode='t2i',prompt='test',seed=0,negative='',width=512,height=768,steps=8,cfg=0)
        self.assertEqual(graph['7']['inputs']['seed'],0)
        self.assertEqual(graph['5']['inputs']['text'],'')
        self.assertEqual(graph['6']['inputs']['height'],768)

    def test_rejects_incompatible_inputs_and_counts(self):
        cases=[{'mode':'t2i','images':[self.first]}, {'mode':'edit'},
               {'mode':'edit','images':[self.first,self.second]}, {'mode':'multi-edit','images':[self.first]},
               {'mode':'multi-edit','images':[self.first,self.first]}, {'mode':'color','color_map':self.first,'depth_map':self.second},
               {'mode':'control','color_map':self.first}, {'mode':'depth','depth_map':self.second,'lora_strength':3},
               {'mode':'t2i','control_end':0.5}, {'mode':'t2i','reference_max_edge':512},
               {'mode':'t2i','lora_strength':1}, {'mode':'layout'}, {'mode':'t2i','layout':self.layout}]
        for options in cases:
            with self.subTest(options=options):
                with self.assertRaises(moss.MossImageError):moss.prepare(prompt='test',**options)

    def test_bad_dimensions_seed_and_nonfinite_values(self):
        cases=[{'width':512}, {'width':513,'height':512}, {'width':4096,'height':4096},
               {'seed':-1}, {'seed':2**64}, {'steps':0}, {'cfg':float('nan')}, {'cfg':float('inf')}]
        for options in cases:
            with self.subTest(options=options):
                with self.assertRaises(moss.MossImageError):moss.prepare(mode='t2i',prompt='test',**options)

    def test_layout_bounds_prompt_and_literal_array(self):
        graph,_,data=moss.prepare(mode='layout',prompt=None,layout=self.layout)
        self.assertEqual(graph['10']['inputs']['editor_state']['__value__'][0]['metadata']['text'],'MOSS')
        self.assertEqual(graph['11']['inputs']['prompt'],'A poster')
        self.assertEqual(graph['4']['inputs']['text'],['11',0])
        with self.assertRaises(moss.MossImageError):
            moss.prepare(mode='layout',prompt=None,layout=self.layout,width=512,height=512)
        bad=json.loads(self.layout.read_text());bad['boxes'][0]['x']=740
        self.layout.write_text(json.dumps(bad))
        with self.assertRaises(moss.MossImageError):moss.read_layout(self.layout)

    def test_control_maps_must_match_output(self):
        with self.assertRaises(moss.MossImageError):
            moss.prepare(mode='control',prompt='test',color_map=self.first,depth_map=self.second,width=512,height=512)
        Image.new('RGB',(512,512)).save(self.second)
        with self.assertRaises(moss.MossImageError):
            moss.prepare(mode='control',prompt='test',color_map=self.first,depth_map=self.second)

    def test_edit_preserves_reference_aspect_and_order_on_both_branches(self):
        Image.new('RGB',(1024,768)).save(self.first)
        graph,records,_=moss.prepare(mode='multi-edit',prompt='test',images=[self.first,self.second])
        self.assertEqual((records[0]['encoded_width'],records[0]['encoded_height']),(512,384))
        self.assertEqual(graph['4']['inputs']['images.image_0'],graph['5']['inputs']['images.image_0'])
        self.assertEqual(graph['4']['inputs']['images.image_1'],graph['5']['inputs']['images.image_1'])
        self.assertEqual(graph['4']['inputs']['edit_format'],'Moss-Image-Edit')
        self.assertAlmostEqual(graph['6']['inputs']['width']/graph['6']['inputs']['height'],4/3,delta=0.04)

    def test_missing_and_corrupt_images(self):
        with self.assertRaises(moss.MossImageError):moss.prepare(mode='edit',prompt='test',images=[self.root/'missing.png'])
        self.first.write_bytes(b'not a PNG')
        with self.assertRaises(moss.MossImageError):moss.prepare(mode='edit',prompt='test',images=[self.first])

    def test_local_only_without_credentials_or_query(self):
        self.assertEqual(moss.local_server('http://localhost:8188/'),'localhost:8188')
        self.assertEqual(moss.local_server('[::1]:8188'),'[::1]:8188')
        for server in ['https://127.0.0.1:8188','example.com:8188','http://user:secret@localhost:8188','http://localhost:8188/?token=secret','http://localhost:8188/api']:
            with self.subTest(server=server):
                with self.assertRaises(moss.MossImageError):moss.local_server(server)

    def test_dry_run_is_offline_and_does_not_create_png(self):
        output=self.root/'draft.png'
        with patch.object(moss,'api_get') as api, patch.object(comfy_client,'queue_prompt') as submit, patch.object(moss,'upload_image') as upload:
            result=moss.generate(**self.options('edit'),output=output,dry_run=True)
        api.assert_not_called();submit.assert_not_called();upload.assert_not_called()
        self.assertFalse(output.exists())
        self.assertTrue(output.with_suffix('.api.json').is_file())
        self.assertEqual(result['status'],'dry_run')
        self.assertEqual(json.loads(output.with_suffix('.result.json').read_text())['status'],'dry_run')
        self.assertFalse(output.with_suffix('.moss.lock').exists())

    def test_existing_files_and_inputs_never_silently_replace(self):
        for suffix in ['.png','.api.json','.result.json','.history.json']:
            output=self.root/'collision.png';existing=output.with_suffix(suffix);existing.write_bytes(b'old')
            with self.assertRaises(moss.MossImageError):moss.generate(mode='t2i',prompt='test',output=output,dry_run=True)
            self.assertEqual(existing.read_bytes(),b'old');existing.unlink()
        with self.assertRaises(moss.MossImageError):
            moss.generate(mode='edit',prompt='test',images=[self.first],output=self.first,dry_run=True,overwrite=True)

    def test_toolbox_output_is_blocked(self):
        with patch.dict('os.environ',{'AGENT_ALLOW_TOOLBOX_OUTPUT':'0'}):
            with self.assertRaises(ValueError) as error:
                moss.generate(mode='t2i',prompt='test',output=moss.ROOT/'dumps/test.png',dry_run=True)
        self.assertEqual(error.exception.exit_code,14)

    def test_explicit_overwrite_retains_previous_sidecars(self):
        output=self.root/'draft.png';prior=output.with_suffix('.result.json');prior.write_text('old')
        result=moss.generate(mode='t2i',prompt='test',output=output,dry_run=True,overwrite=True)
        saved=Path(result['previous_outputs'][str(prior)])
        self.assertEqual(saved.read_text(),'old')

    def test_busy_and_missing_requirements_do_not_submit(self):
        for busy in [True,False]:
            output=self.root/f'blocked{busy}.png'
            queue={'queue_running':[[]] if busy else [],'queue_pending':[]}
            with patch.object(comfy_client,'get_queue',return_value=queue), patch.object(moss,'api_get',return_value={}), patch.object(moss,'upload_image') as upload, patch.object(comfy_client,'queue_prompt') as submit:
                with self.assertRaises(moss.MossImageError) as exc:moss.generate(mode='t2i',prompt='test',output=output)
            self.assertEqual(exc.exception.exit_code,12 if busy else 11)
            upload.assert_not_called();submit.assert_not_called()

    def test_timeout_records_pending_prompt_and_does_not_cancel(self):
        output=self.root/'timeout.png'
        with patch.object(comfy_client,'get_queue',return_value={}), patch.object(moss,'api_get',return_value=fake_schema()), patch.object(comfy_client,'get_system_stats',return_value={}), patch.object(comfy_client,'queue_prompt',return_value='pending-id') as submit, patch.object(comfy_client,'wait_for_history',side_effect=TimeoutError), patch.object(moss,'job_lock',return_value=nullcontext()):
            with self.assertRaises(moss.MossImageError) as exc:moss.generate(mode='t2i',prompt='test',output=output)
        self.assertEqual(exc.exception.exit_code,124)
        record=json.loads(output.with_suffix('.result.json').read_text())
        self.assertEqual(record['status'],'timeout_pending');self.assertEqual(record['prompt_id'],'pending-id')
        self.assertTrue(record['server_job_may_still_be_running'])
        self.assertFalse(submit.call_args.kwargs['ensure']);self.assertFalse(submit.call_args.kwargs['retry_on_connection_error'])

    def test_success_download_decode_and_metadata(self):
        output=self.root/'result.png'
        history={'status':{'status_str':'success','messages':[['execution_start',{'timestamp':1000}],['execution_success',{'timestamp':2500}]]},'outputs':{'9':{'images':[{'filename':'image.png','subfolder':'agent_moss','type':'output'}]}}}
        def download(server,filename,subfolder,kind,target):Image.new('RGB',(1024,1024),'blue').save(target,format='PNG')
        with patch.object(comfy_client,'get_queue',return_value={}), patch.object(moss,'api_get',return_value=fake_schema()), patch.object(comfy_client,'get_system_stats',return_value={}), patch.object(comfy_client,'queue_prompt',return_value='completed-id'), patch.object(comfy_client,'wait_for_history',return_value=history), patch.object(comfy_client,'download_image',side_effect=download), patch.object(moss,'job_lock',return_value=nullcontext()):
            result=moss.generate(mode='t2i',prompt='test',output=output)
        self.assertTrue(output.is_file());self.assertEqual(result['server_execution_seconds'],1.5)
        record=json.loads(output.with_suffix('.result.json').read_text())
        self.assertEqual(record['actual_width'],1024);self.assertEqual(record['prompt'],'test')
        self.assertEqual(record['visual_qc'],'PENDING_VISUAL_REVIEW');self.assertEqual(record['status'],'execution_success')

    def test_uncertain_submit_records_client_id_and_never_waits(self):
        output=self.root/'uncertain.png'
        with patch.object(comfy_client,'get_queue',return_value={}), patch.object(moss,'api_get',return_value=fake_schema()), patch.object(comfy_client,'get_system_stats',return_value={}), patch.object(comfy_client,'queue_prompt',side_effect=comfy_client.PromptSubmissionUncertainError('lost response')), patch.object(comfy_client,'wait_for_history') as wait, patch.object(moss,'job_lock',return_value=nullcontext()):
            with self.assertRaises(moss.MossImageError) as exc:moss.generate(mode='t2i',prompt='test',output=output)
        self.assertEqual(exc.exception.exit_code,13);wait.assert_not_called()
        record=json.loads(output.with_suffix('.result.json').read_text())
        self.assertEqual(record['status'],'submission_uncertain')
        self.assertTrue(record['client_id'].startswith('agent_moss_'))
        self.assertTrue(record['server_job_may_still_be_running'])


class StrictSharedQueueTests(unittest.TestCase):
    def test_strict_submission_never_starts_or_retries(self):
        with patch.object(comfy_client,'ensure_comfy_running') as ensure, patch.object(comfy_client.urllib.request,'urlopen',side_effect=URLError('connection lost')) as request:
            with self.assertRaises(comfy_client.PromptSubmissionUncertainError):
                comfy_client.queue_prompt('127.0.0.1:8188',{},ensure=False,retry_on_connection_error=False,client_id='test-id')
        ensure.assert_not_called();self.assertEqual(request.call_count,1)

    def test_raw_socket_timeout_is_uncertain_without_start(self):
        with patch.object(comfy_client,'ensure_comfy_running') as ensure, patch.object(comfy_client.urllib.request,'urlopen',side_effect=TimeoutError('socket timed out')) as request:
            with self.assertRaises(comfy_client.PromptSubmissionUncertainError):
                comfy_client.queue_prompt('127.0.0.1:8188',{},ensure=False,retry_on_connection_error=False)
        ensure.assert_not_called();self.assertEqual(request.call_count,1)

    def test_legacy_defaults_still_ensure_and_submit_once(self):
        with patch.object(comfy_client,'ensure_comfy_running') as ensure, patch.object(comfy_client.urllib.request,'urlopen',return_value=io.BytesIO(b'{"prompt_id":"legacy-id"}')) as request:
            self.assertEqual(comfy_client.queue_prompt('127.0.0.1:8188',{}),'legacy-id')
        ensure.assert_called_once_with('127.0.0.1:8188')
        self.assertEqual(json.loads(request.call_args.args[0].data),{'prompt':{}})

    def test_legacy_connection_recovery_remains_available(self):
        with patch.object(comfy_client,'ensure_comfy_running') as ensure, patch.object(comfy_client.urllib.request,'urlopen',side_effect=[URLError('lost'),io.BytesIO(b'{"prompt_id":"recovered"}')]) as request:
            self.assertEqual(comfy_client.queue_prompt('127.0.0.1:8188',{}),'recovered')
        self.assertEqual(request.call_count,2)
        self.assertEqual(ensure.call_count,2)
        self.assertEqual(ensure.call_args.kwargs,{'force':True})


if __name__=='__main__':unittest.main()
