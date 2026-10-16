"""Local FLUX3 production/isolated API runner. No model downloading or credential access."""
from __future__ import annotations

import hashlib
import json
import os
import struct
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

if __package__ == 'lib':
    from lib.comfy_engine_session import ensure_engine
else:
    ensure_engine = None

DEFAULT_SERVER = 'http://127.0.0.1:8188'
SANDBOX = Path(r'F:\Agent_media_sandboxes\flux3')
MODES = ('t2i', 'single_edit', 'multi_reference', 'character_consistency', 'style_consistency', 'box_layout')

def api_request(server, route, payload=None, timeout=30):
    data = None if payload is None else json.dumps(payload).encode('utf-8')
    req = Request(server + route, data=data, headers={'Content-Type':'application/json'})
    try:
        with urlopen(req, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f'ComfyUI HTTP {exc.code}: {exc.read().decode("utf-8",errors="replace")}') from None

def upload(server, path):
    boundary='flux3-' + uuid.uuid4().hex
    name=hashlib.sha256(path.read_bytes()).hexdigest()[:16] + path.suffix.lower()
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()
          + path.read_bytes() + f'\r\n--{boundary}--\r\n'.encode())
    req=Request(server+'/upload/image', data=body, headers={'Content-Type':f'multipart/form-data; boundary={boundary}'})
    with urlopen(req, timeout=60) as response:
        item=json.load(response)
    return (item.get('subfolder','')+'/' if item.get('subfolder') else '') + item['name']

def sample_vram(stop, samples):
    while not stop.is_set():
        try:
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
            result=subprocess.run(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5,creationflags=creationflags)
            values=result.stdout.strip().splitlines()[0].split(',')
            samples.append({'elapsed':time.monotonic(),'memory_mib':int(values[0]),'util_percent':int(values[1])})
        except (OSError,ValueError,IndexError,subprocess.TimeoutExpired):
            pass
        stop.wait(0.5)

def build_graph(workflow_dir, mode, prompt, images, width, height, seed, steps, ref_megapixels, prefix):
    graph=json.loads((Path(workflow_dir)/f'{mode}.api.json').read_text(encoding='utf-8-sig'))
    graph['4']['inputs']['text']=prompt
    if width is not None: graph['6']['inputs']['width']=width
    if height is not None: graph['6']['inputs']['height']=height
    if seed is not None: graph['7']['inputs']['seed']=seed
    graph['7']['inputs']['steps']=steps
    graph['9']['inputs']['filename_prefix']=prefix
    if images:
        for key in list(graph):
            if graph[key]['class_type']=='LoadImage': del graph[key]
        refs=graph['17']['inputs']
        for key in list(refs):
            if key.startswith('images.'): del refs[key]
        if ref_megapixels is not None: refs['resolution.megapixels']=ref_megapixels
        for index,name in enumerate(images):
            key=str(100+index)
            graph[key]={'class_type':'LoadImage','inputs':{'image':name}}
            refs[f'images.image{index}']=[key,0]
    return graph

def generate(*, workflow_dir, mode, prompt, output, images=(), width=None,height=None,seed=None,steps=16,ref_megapixels=None,server=DEFAULT_SERVER,timeout=1800,dry_run=False):
    url=urlparse(server)
    if url.scheme!='http' or url.hostname not in ('127.0.0.1','localhost','::1'):
        raise ValueError('This profile sends references only to a local HTTP ComfyUI server')
    output=Path(output).resolve()
    toolbox=Path(r'F:\Agent_media_tools').resolve()
    if output.is_relative_to(toolbox): raise ValueError('Output must be outside Agent_media_tools')
    required=0 if mode in ('t2i','box_layout') else 2 if mode in ('multi_reference','style_consistency') else 1
    if len(images)<required or len(images)>10: raise ValueError(f'{mode} needs {required} to 10 references')
    if required==0 and images: raise ValueError('Choose a reference mode for image inputs')
    for path in images:
        if not Path(path).is_file(): raise FileNotFoundError(path)
    output.parent.mkdir(parents=True,exist_ok=True)
    names=[str(Path(path).name) for path in images]
    graph=build_graph(workflow_dir,mode,prompt,names,width,height,seed,steps,ref_megapixels,'flux3/'+output.stem)
    width,height=graph['6']['inputs']['width'],graph['6']['inputs']['height']
    seed=graph['7']['inputs']['seed']
    if dry_run:
        output.with_suffix('.api.json').write_text(json.dumps(graph,indent=2),encoding='utf-8')
        return {'status':'dry_run','api_path':str(output.with_suffix('.api.json'))}
    # A shared lock serializes FLUX3 callers, and production queue is checked before submitting.
    lock=SANDBOX/'gpu-job.lock'
    descriptor=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    os.close(descriptor)
    stop=threading.Event()
    samples=[]
    monitor=None
    record={'status':'started','mode':mode,'server':server,'seed':seed,'steps':steps,'cfg':1,'sampler':'euler','scheduler':'simple','width':width,'height':height,
            'reference_megapixels':graph.get('17',{}).get('inputs',{}).get('resolution.megapixels'),
            'started_utc':datetime.now(timezone.utc).isoformat(),'references':[{'path':str(p),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in images]}
    start=time.monotonic()
    try:
        for base in {server, 'http://127.0.0.1:8188', 'http://127.0.0.1:8193'}:
            try: queue=api_request(base,'/queue',timeout=3)
            except URLError:
                if base==server: raise
                continue
            if queue.get('queue_running') or queue.get('queue_pending'):
                raise RuntimeError(f'GPU queue is occupied at {base}; no job submitted')
        if ensure_engine is not None:
            engine=ensure_engine('flux3_klein',url.netloc,caller='generate_flux3')
            record['engine_session']=engine
            if not engine.get('ok'): raise RuntimeError('Factory engine memory gate failed: '+str(engine.get('message')))
        names=[upload(server,Path(p)) for p in images]
        graph=build_graph(workflow_dir,mode,prompt,names,width,height,seed,steps,ref_megapixels,'flux3/'+output.stem)
        output.with_suffix('.api.json').write_text(json.dumps(graph,indent=2),encoding='utf-8')
        monitor=threading.Thread(target=sample_vram,args=(stop,samples),daemon=True)
        monitor.start()
        queued=api_request(server,'/prompt',{'prompt':graph,'client_id':str(uuid.uuid4())})
        prompt_id=queued['prompt_id']
        record['prompt_id']=prompt_id
        while time.monotonic()-start<timeout:
            history=api_request(server,'/history/'+prompt_id)
            if prompt_id in history:
                item=history[prompt_id]
                output.with_suffix('.history.json').write_text(json.dumps(item,indent=2),encoding='utf-8')
                if item.get('status',{}).get('status_str')=='error':
                    raise RuntimeError('Inference failed; see .history.json execution_error')
                files=item.get('outputs',{}).get('9',{}).get('images',[])
                if not files: raise RuntimeError('Job ended without SaveImage output')
                query=urlencode(files[0])
                with urlopen(server+'/view?'+query,timeout=60) as response:
                    pixels=response.read()
                output.write_bytes(pixels)
                actual_width,actual_height=struct.unpack('>II',pixels[16:24])
                record.update(status='success',output=str(output),output_sha256=hashlib.sha256(pixels).hexdigest(),actual_width=actual_width,actual_height=actual_height,server_output=files[0],qc='PENDING_VISUAL_REVIEW')
                return record
            time.sleep(0.5)
        raise TimeoutError('Caller timed out. Server job may still be running; inspect queue/history before another call')
    except Exception as exc:
        record.update(status='failed',error=str(exc))
        raise
    finally:
        stop.set()
        if monitor: monitor.join(timeout=6)
        record.update(wall_seconds=round(time.monotonic()-start,3),ended_utc=datetime.now(timezone.utc).isoformat(),sampled_total_gpu_peak_mib=max((s['memory_mib'] for s in samples),default=None),vram_sample_count=len(samples),vram_method='nvidia-smi total GPU memory, sampled about every 0.5s; includes other apps, not exact CUDA peak')
        output.with_suffix('.result.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        lock.unlink()
