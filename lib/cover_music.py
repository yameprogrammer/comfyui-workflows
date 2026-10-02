"""Project-owned, staged YuE2 cover jobs. No hidden dependency installation."""
from __future__ import annotations
import argparse
import array
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
AUDIO_PYTHON = r'F:\ComfyUI_windows_portable\python_embeded\python.exe'
SEED_REPO = r'F:\model\tools\seed-vc'
YT_PACKAGES = r'F:\model\tools\cover-youtube'

def external(path):
    p = Path(path).expanduser().resolve()
    if p == ROOT or ROOT in p.parents:
        raise ValueError('Output must be outside the media toolbox')
    return p

def write_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def call(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)

def probe(path):
    return json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
        'format=duration:stream=sample_rate,channels', '-of', 'json', str(path)]))

def metrics(path):
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'f32le', '-acodec', 'pcm_f32le', '-'])
    data = array.array('f'); data.frombytes(raw)
    if sys.byteorder != 'little': data.byteswap()
    if not data or any(not math.isfinite(x) for x in data): raise ValueError('Empty/nonfinite audio')
    peak = max(abs(x) for x in data)
    rms = math.sqrt(sum(x*x for x in data)/len(data))
    return {'probe': probe(path), 'peak': peak, 'rms_dbfs':20*math.log10(max(rms, 1e-12)),
        'clipped_samples':sum(abs(x)>=0.99999 for x in data), 'non_silent':rms>1e-5}

def read_run(path):
    p = external(path)
    return p, json.loads((p/'run.json').read_text(encoding='utf-8'))

def save_run(path, data): write_json(path/'run.json', data)

def prepare(a):
    r = external(a.run)
    if r.exists() and any(r.iterdir()): raise ValueError('Use a new empty run directory')
    if not math.isfinite(a.start) or not math.isfinite(a.seconds) or a.start<0 or not 4<=a.seconds<=60:
        raise ValueError('Smoke requires start >= 0 and 4..60 seconds')
    src = Path(a.audio).resolve()
    info = probe(src)
    if a.start+a.seconds>float(info['format']['duration'])+0.05: raise ValueError('Segment exceeds source duration')
    r.mkdir(parents=True, exist_ok=True)
    call(['ffmpeg','-v','error','-n','-ss',a.start,'-i',src,'-t',a.seconds,'-ar','48000','-ac','2',r/'source.wav'])
    data={'version':1,'state':'prepared','source':str(src),'source_sha256':sha(src),'segment':[a.start,a.start+a.seconds],
        'segment_sha256':sha(r/'source.wav'),'server':a.server,'mode':'melody','jobs':{},'voice_reference_applied':False,'quality':'listening_pending'}
    save_run(r,data)
    return data

def download(a):
    dest=external(a.out)
    if dest.exists() and any(dest.iterdir()): raise ValueError('Use a new empty download directory')
    dest.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy(); env['PYTHONIOENCODING']='utf-8'
    package=Path(a.yt_packages)
    if package.is_dir(): env['PYTHONPATH']=str(package)+os.pathsep+env.get('PYTHONPATH','')
    cmd=[sys.executable,'-m','yt_dlp','--js-runtimes','node','--no-playlist','--write-info-json','-f','ba','-x','--audio-format','wav','-o',str(dest/'source.%(ext)s')]
    if a.caption_language: cmd+=['--write-auto-subs','--sub-langs',a.caption_language,'--sub-format','json3']
    call(cmd+[a.url],env=env)
    if not (dest/'source.wav').is_file(): raise ValueError('No source audio downloaded')
    return {'audio':str(dest/'source.wav'),'note':'Automatic captions require verification'}

def captions(a):
    r,d=read_run(a.run); target=r/'lyrics_auto.txt'
    if target.exists(): raise ValueError('lyrics_auto.txt already exists')
    start,end=d['segment']; lines=[]
    for e in json.loads(Path(a.input).read_text(encoding='utf-8'))['events']:
        t=e.get('tStartMs',0)/1000; text=''.join(s.get('utf8','') for s in e.get('segs',[])).strip()
        if start<=t<end and text and not text.startswith('[') and (not lines or lines[-1]!=text): lines.append(text)
    if not lines: raise ValueError('No captions in chosen segment')
    target.write_text('[Verse]\n'+'\n'.join(lines)+'\n',encoding='utf-8')
    d['lyrics_status']='automatic_unverified';save_run(r,d)
    return {'lyrics':str(target),'status':d['lyrics_status']}

def submit(r,d,stage,graph):
    from lib.comfy_client import queue_prompt
    if stage in d['jobs']: raise ValueError('Job already submitted; use collect, or create a new run')
    write_json(r/(stage+'.workflow.json'),graph)
    pid=queue_prompt(d['server'],graph)
    d['jobs'][stage]={'prompt_id':pid,'state':'submitted'};save_run(r,d)
    return pid

def collect(a):
    from lib.comfy_client import wait_for_history,extract_preview_text,extract_first_audio,download_audio
    r,d=read_run(a.run); job=d['jobs'][a.stage]
    if job['state']=='complete': return job
    try:
        history=wait_for_history(d['server'],job['prompt_id'],timeout_sec=a.timeout)
        write_json(r/(a.stage+'.history.json'),history)
        if a.stage=='transcribe':
            text=extract_preview_text(history)
            if not text.strip(): raise ValueError('Empty score')
            (r/'source_melody.abc').write_text(text,encoding='utf-8')
        else:
            f,s,t=extract_first_audio(history); download_audio(d['server'],f,s,t,str(r/'base.flac'))
            result=metrics(r/'base.flac');write_json(r/'base.metrics.json',result)
            if not result['non_silent']: raise ValueError('Rendered audio is silent')
        job['state']='complete'; d['state']=a.stage+'_complete';job.pop('error',None)
    except Exception as e:
        job['error']=str(e);save_run(r,d);raise
    save_run(r,d);return job

def transcribe(a):
    from lib.comfy_client import get_comfy_input_dir
    r,d=read_run(a.run)
    if 'transcribe' in d['jobs']: return collect(argparse.Namespace(run=a.run,stage='transcribe',timeout=a.timeout))
    filename='cover_'+sha(r/'source.wav')[:20]+'.wav'
    target=Path(get_comfy_input_dir(d['server']))/filename;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(r/'source.wav',target)
    graph={'1':{'class_type':'AudioEncoderLoader','inputs':{'audio_encoder_name':a.encoder}},
        '2':{'class_type':'LoadAudio','inputs':{'audio':filename}},
        '3':{'class_type':'SheetSage2AudioToABC','inputs':{'audio_encoder':['1',0],'audio':['2',0],'mode':'melody'}},
        '4':{'class_type':'PreviewAny','inputs':{'source':['3',0]}}}
    d['encoder']=a.encoder;submit(r,d,'transcribe',graph)
    return collect(argparse.Namespace(run=a.run,stage='transcribe',timeout=a.timeout))

def render(a):
    from lib.yue2_music_runner import build_yue2_text2music_prompt
    r,d=read_run(a.run)
    if 'render' in d['jobs']: raise ValueError('Render exists. Use collect to recover; new run for a new candidate')
    if not math.isfinite(a.ceiling) or not 4<=a.ceiling<=90: raise ValueError('Smoke ceiling must be 4..90 seconds')
    score=Path(a.abc) if a.abc else r/'source_melody.abc'
    abc=score.read_text(encoding='utf-8-sig'); lyrics=Path(a.lyrics).read_text(encoding='utf-8-sig');style=Path(a.style).read_text(encoding='utf-8-sig')
    if not all(x.strip() for x in [abc,lyrics,style]): raise ValueError('ABC, lyrics and style must be explicit and nonempty')
    for name,text in [('render.abc',abc),('lyrics.txt',lyrics),('style.txt',style)]: (r/name).write_text(text,encoding='utf-8')
    d['render_settings']={'seed':a.seed,'ceiling':a.ceiling,'steps':32,'checkpoint':a.checkpoint,'lyrics_status':a.lyrics_status,'abc_sha256':sha(r/'render.abc'),'lyrics_sha256':sha(r/'lyrics.txt'),'style_sha256':sha(r/'style.txt')}
    g=build_yue2_text2music_prompt(style=style,lyrics=lyrics,abc_text=abc,abc_mode='melody',duration=a.ceiling,seed=a.seed,ckpt_name=a.checkpoint,filename_prefix='audio/Cover_'+uuid.uuid4().hex[:10])
    submit(r,d,'render',g)
    return collect(argparse.Namespace(run=a.run,stage='render',timeout=a.timeout))

def export(a):
    out=external(a.out);out.mkdir(parents=True,exist_ok=True)
    if any((out/n).exists() for n in ['cover.wav','cover.mp3','export.json']): raise ValueError('Use a new export directory')
    src=Path(a.audio).resolve(); m=metrics(src)
    if not m['non_silent'] or m['clipped_samples']: raise ValueError('Silent or clipped input: inspect before export')
    call(['ffmpeg','-v','error','-n','-i',src,'-c:a','pcm_s24le',out/'cover.wav'])
    call(['ffmpeg','-v','error','-n','-i',src,'-c:a','libmp3lame','-b:a','192k',out/'cover.mp3'])
    result={'source':str(src),'source_sha256':sha(src),'wav':str(out/'cover.wav'),'mp3':str(out/'cover.mp3'),'metrics':m,'perceptual_review':'pending'}
    write_json(out/'export.json',result)
    call([sys.executable,ROOT/'scripts/review_media.py','pack','-i',out/'cover.wav','--intent','Short music cover preview; perceptual review pending','-o',out/'review'])
    return result

def voice(a):
    r,d=read_run(a.run);out=r/'reference_voice'
    if out.exists(): raise ValueError('Voice output exists; use a fresh candidate directory')
    if not Path(a.reference).is_file(): raise ValueError('Reference file not found')
    if not Path(a.seed_vc_repo,'inference.py').is_file(): raise ValueError('Seed-VC not installed; see skill setup')
    call([a.audio_python,ROOT/'scripts/cover_music_voice.py','--source',r/'base.flac','--reference',Path(a.reference).resolve(),'--out',out,'--repo',Path(a.seed_vc_repo).resolve()])
    d['reference_variant']={'path':str(out/'mix.wav'),'reference':str(Path(a.reference).resolve()),'reference_sha256':sha(a.reference),'quality':'listening_pending'}
    save_run(r,d);return d['reference_variant']

def doctor(a):
    from lib.yue2_music_runner import DEFAULT_CKPT,DEFAULT_AUDIO_ENCODER
    d={'ffmpeg':shutil.which('ffmpeg'),'ffprobe':shutil.which('ffprobe'),'node':shutil.which('node'),'audio_python':Path(a.audio_python).is_file(),'seed_vc_repo':Path(a.seed_vc_repo,'inference.py').is_file(),'yt_packages':Path(a.yt_packages,'yt_dlp').is_dir()}
    try:
        nodes=json.load(urllib.request.urlopen('http://'+a.server+'/object_info',timeout=10))
        required=['SheetSage2AudioToABC','YuE2GenerateMusic','CheckpointLoaderSimple','AudioEncoderLoader','PreviewAny','SaveAudio']
        d['missing_nodes']=[n for n in required if n not in nodes]
        d['checkpoint_available']=DEFAULT_CKPT in json.dumps(nodes.get('CheckpointLoaderSimple',{}))
        d['encoder_available']=DEFAULT_AUDIO_ENCODER in json.dumps(nodes.get('AudioEncoderLoader',{}))
    except Exception as e: d['server_error']=str(e)
    d['base_ready']=all(d[k] for k in ['ffmpeg','ffprobe']) and not d.get('server_error') and not d.get('missing_nodes') and d.get('checkpoint_available',False) and d.get('encoder_available',False)
    return d

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    x=sub.add_parser('doctor');x.add_argument('--server',default='127.0.0.1:8188');x.add_argument('--audio-python',default=AUDIO_PYTHON);x.add_argument('--seed-vc-repo',default=SEED_REPO);x.add_argument('--yt-packages',default=YT_PACKAGES)
    x=sub.add_parser('download');x.add_argument('--url',required=True);x.add_argument('--out',required=True);x.add_argument('--yt-packages',default=YT_PACKAGES);x.add_argument('--caption-language')
    x=sub.add_parser('prepare');x.add_argument('--audio',required=True);x.add_argument('--run',required=True);x.add_argument('--start',type=float,required=True);x.add_argument('--seconds',type=float,default=30);x.add_argument('--server',default='127.0.0.1:8188')
    x=sub.add_parser('captions');x.add_argument('--run',required=True);x.add_argument('--input',required=True)
    for cmd in ['transcribe','render','collect']:
        x=sub.add_parser(cmd);x.add_argument('--run',required=True);x.add_argument('--timeout',type=float,default=900)
        if cmd=='transcribe': x.add_argument('--encoder',default='sheetsage2_bf16.safetensors')
        if cmd=='collect': x.add_argument('--stage',choices=['transcribe','render'],required=True)
        if cmd=='render':
            x.add_argument('--style',required=True);x.add_argument('--lyrics',required=True);x.add_argument('--abc');x.add_argument('--seed',type=int,default=42);x.add_argument('--ceiling',type=float,default=45);x.add_argument('--checkpoint',default='yue2_3b_int8_convrot.safetensors');x.add_argument('--lyrics-status',choices=['verified','automatic_unverified','user_supplied'],default='user_supplied')
    x=sub.add_parser('voice');x.add_argument('--run',required=True);x.add_argument('--reference',required=True);x.add_argument('--audio-python',default=AUDIO_PYTHON);x.add_argument('--seed-vc-repo',default=SEED_REPO)
    x=sub.add_parser('export');x.add_argument('--audio',required=True);x.add_argument('--out',required=True)
    a=p.parse_args(argv)
    try:
        result=globals()[a.command](a); print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except Exception as e:
        print(json.dumps({'ok':False,'error':str(e)},ensure_ascii=False),file=sys.stderr);return 1
