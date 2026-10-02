#!/usr/bin/env python3
"""Worker launched by cover_music voice under the audio Python runtime."""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ['source','reference','out','repo']: p.add_argument('--'+flag,required=True)
    a=p.parse_args();out=Path(a.out).resolve();repo=Path(a.repo).resolve()
    if out.exists(): raise ValueError('Refusing to overwrite a voice candidate')
    if Path(__file__).resolve().parents[1] in out.parents: raise ValueError('Output must be in the project')
    import numpy as np
    import soundfile as sf
    import torch
    import torchaudio
    from demucs.pretrained import get_model
    from demucs.apply import apply_model
    source=Path(a.source).resolve();reference=Path(a.reference).resolve()
    ref,rs=sf.read(reference,always_2d=True)
    if not 1<=len(ref)/rs<=30: raise ValueError('Reference must contain 1..30 seconds of clean audio')
    if not np.isfinite(ref).all() or np.sqrt(np.mean(ref*ref))<1e-5: raise ValueError('Silent/nonfinite voice reference')
    out.mkdir(parents=True)
    torch.hub.set_dir(str(repo.parent/'torch-cache'))
    audio,sr=sf.read(source,always_2d=True,dtype='float32')
    if not np.isfinite(audio).all() or np.sqrt(np.mean(audio*audio))<1e-5: raise ValueError('Silent/nonfinite source')
    if audio.shape[1]==1: audio=np.repeat(audio,2,axis=1)
    if audio.shape[1]!=2: raise ValueError('Mono or stereo source required')
    wave=torch.from_numpy(audio.T.copy()); model=get_model('htdemucs').to('cuda').eval()
    wave=torchaudio.functional.resample(wave,sr,model.samplerate)
    mean=wave.mean(0).mean(); std=wave.mean(0).std()
    if std<1e-8: raise ValueError('Degenerate waveform')
    with torch.inference_mode():
        stems=apply_model(model,((wave-mean)/std)[None].to('cuda'),shifts=1,split=True,overlap=.25,progress=True)[0].cpu()*std+mean
    v=stems[model.sources.index('vocals')];bed=stems.sum(0)-v;rate=model.samplerate
    sf.write(out/'vocals.wav',v.T.numpy(),rate,subtype='PCM_24');sf.write(out/'instrumental.wav',bed.T.numpy(),rate,subtype='PCM_24')
    del model,stems,wave;torch.cuda.empty_cache()
    os.chdir(repo);sys.path.insert(0,str(repo));os.environ['HF_HOME']=str(repo.parent/'huggingface')
    import inference
    args=argparse.Namespace(source=str(out/'vocals.wav'),target=str(reference),output=str(out/'converted'),diffusion_steps=30,length_adjust=1.,inference_cfg_rate=.7,f0_condition=True,auto_f0_adjust=False,semi_tone_shift=0,checkpoint=None,config=None,fp16=True)
    inference.main(args)
    candidates=list((out/'converted').glob('*.wav'))
    if len(candidates)!=1: raise ValueError('Expected exactly one converted vocal')
    vc,sr=sf.read(candidates[0],always_2d=True);backing,sb=sf.read(out/'instrumental.wav',always_2d=True);original,sv=sf.read(out/'vocals.wav',always_2d=True)
    if sr!=sb or sr!=sv: raise ValueError('Unexpected sample-rate mismatch')
    delta=(len(vc)-len(backing))/sr
    if abs(delta)>.1: raise ValueError('Converted duration differs >100ms; align and inspect before mixing')
    if not np.isfinite(vc).all() or np.sqrt(np.mean(vc*vc))<1e-5: raise ValueError('Invalid converted vocal')
    vc=np.pad(vc,((0,max(0,len(backing)-len(vc))),(0,0)))[:len(backing)]
    gain=float(np.sqrt(np.mean(original*original))/np.sqrt(np.mean(vc*vc)))
    mix=backing+vc*gain;normalization=min(1.,.89125/max(float(np.max(np.abs(mix))),1e-8));mix*=normalization
    sf.write(out/'mix.wav',mix,sr,subtype='PCM_24')
    record={'duration':len(mix)/sr,'sample_rate':sr,'tail_adjustment_sec':-delta,'vocal_gain':gain,'mix_gain':normalization,'peak':float(np.max(np.abs(mix))),'clipped_samples':int(np.sum(np.abs(mix)>=.99999)),'review':'listening_pending','f0_condition':True,'pitch_shift':0,'steps':30,'reference':str(reference)}
    (out/'voice.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record))

if __name__=='__main__': main()
