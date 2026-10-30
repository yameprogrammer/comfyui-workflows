"""Isolated local MOSS speech generation, staged GPU tokenizer + HF CPU offload."""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import os
import sys
import time

ROOT=Path(__file__).resolve().parent
for key,value in {'HF_HOME':str(ROOT/'.cache/huggingface'),'HF_MODULES_CACHE':str(ROOT/'.cache/huggingface/modules'),'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','DO_NOT_TRACK':'1','NUMBA_CACHE_DIR':str(ROOT/'.cache/numba'),'TOKENIZERS_PARALLELISM':'false'}.items():
    os.environ[key]=value
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task',choices=['tts','dialogue','design'],required=True)
    p.add_argument('--text',required=True)
    p.add_argument('--language',default='Korean')
    p.add_argument('--reference',type=Path,action='append',default=[])
    p.add_argument('--reference-text',action='append',default=[])
    p.add_argument('--instruction')
    p.add_argument('-o','--output',required=True,type=Path,help='New/empty output directory')
    p.add_argument('--max-new-tokens',type=int,default=512)
    p.add_argument('--seed',type=int,default=20261019)
    p.add_argument('--gpu-memory-gib',type=int,default=14)
    a=p.parse_args()
    if a.task=='design' and (a.language not in ['English','Chinese'] or not a.instruction):
        p.error('VoiceGenerator requires English/Chinese text and --instruction')
    if a.task!='design' and a.instruction:
        p.error('No validated free-form emotion/instruction control for this TTS/TTSD profile; use design task')
    if a.task=='dialogue' and (len(a.reference)!=2 or len(a.reference_text)!=2):
        p.error('Dialogue requires two ordered references and their exact transcripts; [S1]/[S2] tag the target script')
    if a.task=='tts' and len(a.reference)>1:
        p.error('Single-speaker TTS accepts one reference')
    if a.task=='design' and a.reference:
        p.error('VoiceGenerator uses instructions, no reference')
    if not 1 <= a.max_new_tokens <= 4096 or not 4 <= a.gpu_memory_gib <= 16:
        p.error('Token limit1..4096 and GPU weight budget4..16GiB required')
    for r in a.reference:
        if not r.is_file():p.error('Reference must be an existing local audio file')
    out=a.output.expanduser().resolve()
    toolbox=Path(os.environ.get('AGENT_MEDIA_TOOLS_ROOT', str(ROOT.parent/'Agent_media_tools'))).resolve()
    if out==toolbox or toolbox in out.parents:
        p.error('Outputs belong in caller project, outside toolbox')
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        p.error('Output must be new/empty; no overwrite')
    out.mkdir(parents=True,exist_ok=True)
    summary={'status':'failed','task':a.task,'text':a.text,'language':a.language,'instruction':a.instruction,'seed':a.seed,'max_new_tokens':a.max_new_tokens,'references':[str(x.resolve()) for x in a.reference],'warnings':[]}
    started=time.perf_counter()
    model=processor=outputs=batch=None
    lock=None
    torch=None
    try:
        import msvcrt
        lock=(ROOT/'.speech_inference.lock').open('a+b')
        lock.seek(0)
        if not lock.read(1):lock.write(b'0');lock.flush()
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        import numpy as np
        import soundfile as sf
        import torch
        import torchaudio
        import transformers
        from transformers import AutoModel,AutoProcessor
        torch.set_num_threads(8)
        torch.manual_seed(a.seed)
        if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
            raise RuntimeError('CUDA/BF16 required; no silent CPU-only fallback')
        torch.backends.cuda.enable_cudnn_sdp(False)
        torch.backends.cuda.enable_flash_sdp(True)
        torch.backends.cuda.enable_mem_efficient_sdp(True)
        torch.backends.cuda.enable_math_sdp(True)
        torch.cuda.reset_peak_memory_stats()
        selected={'tts':'MOSS-TTS-v1.5','dialogue':'MOSS-TTSD-v1.0','design':'MOSS-VoiceGenerator'}[a.task]
        info=json.loads((ROOT/'audit/model_revisions.json').read_text(encoding='utf-8'))
        for name in (selected,'MOSS-Audio-Tokenizer'):
            for file,expected in info[name]['sha256_review_files'].items():
                if file.endswith('.py'):
                    actual=hashlib.sha256((ROOT/'models'/name/file).read_bytes()).hexdigest()
                    if actual!=expected:raise RuntimeError('Reviewed source changed: '+name+'/'+file)
        summary.update(model=selected,model_revision=info[selected]['revision'],codec_revision=info['MOSS-Audio-Tokenizer']['revision'],torch=torch.__version__,transformers=transformers.__version__,python=sys.version,gpu=torch.cuda.get_device_name(0),gpu_weight_budget_gib=a.gpu_memory_gib,codec_policy='float32 CPU storage; GPU encode/decode only outside generator residency')
        print('Loading local processor and audio tokenizer on CPU',flush=True)
        # Official processor forwards unknown kwargs into its constructor.
        # Offline env + absolute model/codec paths enforce locality here.
        processor_options={'normalize_inputs':True} if a.task=='design' else {}
        processor=AutoProcessor.from_pretrained(str(ROOT/'models'/selected),trust_remote_code=True,codec_path=str(ROOT/'models/MOSS-Audio-Tokenizer'),**processor_options)
        processor.audio_tokenizer.eval()
        sr=int(processor.model_config.sampling_rate)
        waves=[]
        summary['reference_provenance']=[]
        for ref in a.reference:
            audio,rate=sf.read(str(ref),dtype='float32',always_2d=True)
            if not len(audio) or not np.isfinite(audio).all():raise ValueError('Empty/nonfinite reference')
            if len(audio)/rate>30:raise ValueError('Reference exceeds30s; choose a short caller-prepared excerpt')
            wave=torch.from_numpy(audio.T.copy()).mean(dim=0,keepdim=True)
            if rate!=sr:wave=torchaudio.functional.resample(wave,rate,sr)
            waves.append(wave)
            summary['reference_provenance'].append({'path':str(ref.resolve()),'sha256':hashlib.sha256(ref.read_bytes()).hexdigest(),'seconds':len(audio)/rate})
        encoded=[]
        encode_start=time.perf_counter()
        if waves:
            print('Stage1: GPU encode references; generator not loaded',flush=True)
            processor.audio_tokenizer.to('cuda:0')
            with torch.inference_mode():
                encoded=processor.encode_audios_from_wav(waves,sampling_rate=sr)
                prompt_codes=processor.encode_audios_from_wav([torch.cat(waves,dim=-1)],sampling_rate=sr)[0] if a.task=='dialogue' else None
            processor.audio_tokenizer.to('cpu')
            gc.collect();torch.cuda.empty_cache()
        summary['reference_encode_seconds']=time.perf_counter()-encode_start
        if a.task=='dialogue':
            full_text=' '.join(f'[S{i+1}] {text}' for i,text in enumerate(a.reference_text))+' '+a.text
            conv=[processor.build_user_message(text=full_text,reference=encoded),processor.build_assistant_message(audio_codes_list=[prompt_codes])]
            batch=processor([conv],mode='continuation')
        else:
            kwargs={'text':a.text,'language':a.language}
            if encoded:kwargs['reference']=encoded
            if a.task=='design':kwargs['instruction']=a.instruction
            batch=processor([[processor.build_user_message(**kwargs)]],mode='generation')
        print('Stage2: HF generator BF16 SDPA with bounded GPU weights / CPU offload',flush=True)
        load_start=time.perf_counter()
        model=AutoModel.from_pretrained(str(ROOT/'models'/selected),trust_remote_code=True,local_files_only=True,dtype=torch.bfloat16,attn_implementation='sdpa',device_map='auto',max_memory={0:f'{a.gpu_memory_gib}GiB','cpu':'24GiB'},offload_folder=str(ROOT/'.cache/offload'/a.task),offload_state_dict=True,low_cpu_mem_usage=True).eval()
        summary['model_load_seconds']=time.perf_counter()-load_start
        placement=getattr(model,'hf_device_map',None)
        if placement is None:
            placement={'':str(next(model.parameters()).device)}
        summary['device_map']={k:str(v) for k,v in placement.items()}
        summary['actual_parameter_devices']=sorted({str(x.device) for x in model.parameters()})
        summary['actual_floating_dtypes']=sorted({str(x.dtype) for x in model.parameters() if x.is_floating_point()})
        summary['attention']={'model':model.config._attn_implementation,'language':model.config.language_config._attn_implementation}
        if any(v!='sdpa' for v in summary['attention'].values()):raise RuntimeError('SDPA config not honored')
        if not any(v in ('0','cuda:0') for v in summary['device_map'].values()):raise RuntimeError('No generator modules dispatched to CUDA')
        input_ids=batch['input_ids'].to('cuda:0');mask=batch['attention_mask'].to('cuda:0')
        summary['prompt_frames']=int(input_ids.shape[1])
        generation_start=time.perf_counter()
        sampling={'audio_temperature':1.5,'audio_top_p':0.6,'audio_top_k':50,'audio_repetition_penalty':1.1} if a.task=='design' else {}
        with torch.inference_mode():
            outputs=model.generate(input_ids=input_ids,attention_mask=mask,max_new_tokens=a.max_new_tokens,**sampling)
        torch.cuda.synchronize()
        summary['generation_seconds']=time.perf_counter()-generation_start
        outputs=[(int(start),codes.detach().cpu()) for start,codes in outputs]
        summary['generated_steps']=[int(codes.shape[0])-start for start,codes in outputs]
        summary['eos_observed']=[bool((codes[:,0]==model.config.im_end_token_id).any()) for _,codes in outputs]
        for i,(start,codes) in enumerate(outputs):np.save(out/f'raw_generation_{i}.npy',codes.numpy())
        if max(summary['generated_steps'],default=0)>=a.max_new_tokens or not all(summary['eos_observed']):summary['warnings'].append('Generation may be truncated: token cap or no end-of-message token; raw codes preserved')
        model=None;input_ids=mask=batch=None
        gc.collect();torch.cuda.empty_cache()
        summary['allocated_before_decode_bytes']=torch.cuda.memory_allocated()
        if summary['allocated_before_decode_bytes']>512*1024**2:
            raise RuntimeError('Generator GPU allocations remain after unload; refusing overlapping codec decode')
        print('Stage3: generator released; GPU audio decode',flush=True)
        processor.audio_tokenizer.to('cuda:0')
        decode_start=time.perf_counter()
        with torch.inference_mode():messages=processor.decode(outputs)
        torch.cuda.synchronize()
        summary['audio_decode_seconds']=time.perf_counter()-decode_start
        summary['files']=[]
        for i,message in enumerate(messages):
            if message is None:continue
            for j,audio in enumerate(message.audio_codes_list):
                values=audio.detach().float().cpu().numpy().reshape(-1)
                if not len(values) or not np.isfinite(values).all():raise RuntimeError('Empty/nonfinite generated audio')
                path=out/f'speech_{i}_{j}.wav'
                raw_peak=float(np.max(np.abs(values)))
                raw_path=out/f'raw_float_{i}_{j}.wav'
                sf.write(str(raw_path),values,sr,subtype='FLOAT')
                gain=min(1.0,0.98/raw_peak) if raw_peak else 1.0
                export_values=values*gain
                sf.write(str(path),export_values,sr,subtype='PCM_16')
                summary['files'].append({'path':str(path),'raw_float_path':str(raw_path),'seconds':len(values)/sr,'sample_rate':sr,'raw_peak':raw_peak,'pcm_gain':gain,'peak':float(np.max(np.abs(export_values))),'rms':float(np.sqrt(np.mean(export_values**2))),'samples_at_or_above_1':int(np.sum(np.abs(export_values)>=1))})
                if raw_peak>=1:summary['warnings'].append('Raw waveform exceeded PCM range; raw FLOAT WAV retained and PCM attenuated to peak0.98. Inspect output before use.')
        if not summary['files']:raise RuntimeError('No output waveform generated')
        if any(f['peak']<0.001 for f in summary['files']):summary['warnings'].append('Near-silent output')
        if any(f['samples_at_or_above_1'] for f in summary['files']):summary['warnings'].append('Waveform exceeds PCM range; inspect clipping')
        summary['peak_allocated_bytes']=torch.cuda.max_memory_allocated()
        summary['peak_reserved_bytes']=torch.cuda.max_memory_reserved()
        summary['status']='needs_review' if summary['warnings'] else 'generated_unreviewed'
        summary['quality_status']='Pronunciation/timbre/emotion require separate review; exit0 is not perceptual approval'
    except Exception as exc:
        summary['error']=f'{type(exc).__name__}: {exc}'
        import traceback
        traceback.print_exc()
    finally:
        model=processor=outputs=batch=None
        gc.collect()
        if torch is not None and torch.cuda.is_available():
            summary['peak_allocated_bytes']=torch.cuda.max_memory_allocated()
            summary['peak_reserved_bytes']=torch.cuda.max_memory_reserved()
            torch.cuda.empty_cache()
            summary['allocated_after_cleanup_bytes']=torch.cuda.memory_allocated()
        if lock is not None:lock.close()
        summary['total_seconds']=time.perf_counter()-started
        (out/'run_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    return 1 if summary['status']=='failed' else 2 if summary['status']=='needs_review' else 0

if __name__=='__main__':raise SystemExit(main())
