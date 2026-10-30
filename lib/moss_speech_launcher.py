"""Launch the isolated local MOSS speech family; no shared ML imports."""
from pathlib import Path
import argparse
import os
import subprocess


def run(task):
    p=argparse.ArgumentParser(description={'tts':'MOSS-TTS v1.5: Korean/multilingual speech and local voice references','dialogue':'MOSS-TTSD v1.0: [S1]/[S2] dialogue continuation from two local voice references','design':'MOSS-VoiceGenerator: English/Chinese voice design from natural-language instruction'}[task])
    text=p.add_mutually_exclusive_group(required=True)
    text.add_argument('-t','--text')
    text.add_argument('--text-file',type=Path)
    p.add_argument('-o','--output',type=Path,required=True,help='New or empty project output directory (WAV + raw codes + summary)')
    p.add_argument('--language',default='English' if task=='design' else 'Korean')
    p.add_argument('--seed',type=int,default=20261019)
    p.add_argument('--max-new-tokens',type=int,default=512)
    p.add_argument('--gpu-memory-gib',type=int,default=14,help='HF weight placement budget; runtime needs additional VRAM')
    if task=='tts':p.add_argument('--ref-audio',type=Path)
    if task=='dialogue':
        p.add_argument('--ref-audio',type=Path,action='append',required=True,help='Repeat twice in S1,S2 order')
        p.add_argument('--ref-text',action='append',required=True,help='Repeat twice, exact reference speech, without added tags')
    if task=='design':p.add_argument('--instruction',required=True,help='Voice, emotion, pitch and speed description; English/Chinese only')
    a=p.parse_args()
    content=a.text_file.read_text(encoding='utf-8-sig') if a.text_file else a.text
    if not content.strip():p.error('Text is empty')
    root=Path(os.environ.get('MOSS_SPEECH_ROOT', 'F:/MOSS-TTS')).expanduser().resolve()
    py=root/'.venv/Scripts/python.exe';worker=root/'moss_speech_worker.py'
    if not py.is_file() or not worker.is_file():p.error('MOSS speech installation missing; read workflows/human/moss_speech/AGENT_GUIDE.md')
    cmd=[str(py),'-s',str(worker),'--task',task,'--text',content,'--language',a.language,'-o',str(a.output.expanduser().resolve()),'--seed',str(a.seed),'--max-new-tokens',str(a.max_new_tokens),'--gpu-memory-gib',str(a.gpu_memory_gib)]
    refs=getattr(a,'ref_audio',None)
    for ref in refs if isinstance(refs,list) else [refs] if refs else []:
        cmd+=['--reference',str(ref.expanduser().resolve())]
    for line in getattr(a,'ref_text',[]) or []:cmd+=['--reference-text',line]
    if task=='design':cmd+=['--instruction',a.instruction]
    env=os.environ.copy();env.pop('PYTHONPATH',None);env['PYTHONNOUSERSITE']='1';env['PYTHONUTF8']='1';env['AGENT_MEDIA_TOOLS_ROOT']=str(Path(__file__).resolve().parents[1])
    return subprocess.call(cmd,cwd=root,env=env)
