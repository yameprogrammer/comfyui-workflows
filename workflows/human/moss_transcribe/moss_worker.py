"""Strict local-only MOSS HF inference. Run with the dedicated installation Python."""
from pathlib import Path
import argparse
import gc
import hashlib
import json
import os
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent
for key, value in {
    'HF_HOME': str(ROOT / '.cache/huggingface'),
    'HF_MODULES_CACHE': str(ROOT / '.cache/huggingface/modules'),
    'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
    'HF_HUB_DISABLE_TELEMETRY': '1', 'DO_NOT_TRACK': '1',
    'NUMBA_CACHE_DIR': str(ROOT / '.cache/numba'),
}.items():
    os.environ[key] = value


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('-i', '--input', required=True, type=Path)
    p.add_argument('-o', '--output', required=True, type=Path, help='New or empty project output directory')
    p.add_argument('--max-new-tokens', type=int, default=4096)
    p.add_argument('--prompt', default=None, help='Full transcription/timestamp/speaker instruction; replaces default')
    a = p.parse_args()
    source, out = a.input.expanduser().resolve(), a.output.expanduser().resolve()
    toolbox = Path(os.environ.get('AGENT_MEDIA_TOOLS_ROOT', str(ROOT.parent/'Agent_media_tools'))).resolve()
    if not source.is_file():
        p.error('Input must be an existing local file; URLs are unsupported')
    if out == toolbox or toolbox in out.parents or out == ROOT or ROOT in out.parents:
        p.error('Output must be in the caller project, outside toolbox and installation')
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        p.error('Output must be new or empty; existing subtitles are never overwritten')
    if a.max_new_tokens < 1:
        p.error('--max-new-tokens must be positive')
    out.mkdir(parents=True, exist_ok=True)
    summary = {'input': str(source), 'output': str(out), 'status': 'failed', 'warnings': []}
    started = time.perf_counter()
    model = processor = None
    torch = None
    lock = None
    try:
        import msvcrt
        lock = (ROOT / '.inference.lock').open('a+b')
        lock.seek(0)
        if not lock.read(1):
            lock.write(b'0'); lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        import numpy as np
        import torch
        import transformers
        from transformers import AutoModelForCausalLM, AutoProcessor
        from moss_transcribe_diarize.inference_utils import DEFAULT_PROMPT, build_transcription_messages, generate_transcription, load_audio_item
        from moss_transcribe_diarize.subtitle import export_ass, export_json, export_srt, subtitle_segments_from_transcript
        model_dir = ROOT / 'model'
        manifest = json.loads((ROOT / 'audit/code-review.json').read_text(encoding='utf-8-sig'))
        for name, expected in manifest['sha256'].items():
            actual = hashlib.sha256((model_dir / name).read_bytes()).hexdigest()
            if actual != expected:
                raise RuntimeError(f'Reviewed model source changed: {name}; review before executing')
        summary.update(python=sys.version, torch=torch.__version__, transformers=transformers.__version__, model_revision=manifest['model_revision'], source_commit=manifest['source_commit'])
        audio = load_audio_item(str(source), sampling_rate=16000)
        summary.update(audio_seconds=len(audio)/16000, audio_peak=float(np.max(np.abs(audio))) if len(audio) else 0)
        if not len(audio):
            raise ValueError('Audio contains no samples')
        if not np.isfinite(audio).all():
            raise ValueError('Audio contains nonfinite values')
        prompt = a.prompt or DEFAULT_PROMPT
        summary['prompt'] = prompt
        if summary['audio_peak'] == 0:
            result = {'text': '', 'generated_tokens': 0, 'prompt_len': 0}
            summary['status'] = 'silent_zero_signal'
            summary['warnings'].append('Exactly zero waveform: skipped inference; no speech segments. Nonzero music/noise is not VAD filtered.')
        else:
            if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
                raise RuntimeError('CUDA/BF16 unavailable; CPU or eager fallback is prohibited')
            device, dtype = torch.device('cuda:0'), torch.bfloat16
            torch.cuda.reset_peak_memory_stats(device)
            summary['free_vram_before_bytes'] = torch.cuda.mem_get_info(device)[0]
            model = AutoModelForCausalLM.from_pretrained(str(model_dir), trust_remote_code=True, local_files_only=True, dtype=dtype, attn_implementation='sdpa').to(device).eval()
            processor = AutoProcessor.from_pretrained(str(model_dir), trust_remote_code=True, local_files_only=True)
            devices = sorted({str(v.device) for v in model.parameters()})
            dtypes = sorted({str(v.dtype) for v in model.parameters() if v.is_floating_point()})
            attentions = {n: getattr(c, '_attn_implementation', None) for n,c in [('model',model.config),('text',model.config.text_config),('audio',model.config.audio_config)]}
            summary.update(devices=devices, dtypes=dtypes, attention=attentions, gpu=torch.cuda.get_device_name(device))
            if devices != ['cuda:0'] or dtypes != ['torch.bfloat16'] or any(x != 'sdpa' for x in attentions.values()):
                raise RuntimeError(f'Unexpected execution placement/attention: {devices} {dtypes} {attentions}')
            print(json.dumps({'loaded': {k:summary[k] for k in ('devices','dtypes','attention','gpu')} }), flush=True)
            inference_start = time.perf_counter()
            result = generate_transcription(model, processor, build_transcription_messages(source,prompt), device=device, dtype=dtype, max_new_tokens=a.max_new_tokens, do_sample=False)
            torch.cuda.synchronize(device)
            summary['inference_seconds'] = time.perf_counter()-inference_start
            summary['status'] = 'completed'
            summary.update(peak_allocated_bytes=torch.cuda.max_memory_allocated(device),peak_reserved_bytes=torch.cuda.max_memory_reserved(device))
        (out/'raw_transcript.txt').write_text(result['text'],encoding='utf-8')
        summary.update({k:v for k,v in result.items() if k!='text'})
        segments = subtitle_segments_from_transcript(result['text'], postprocess=False)
        (out/'segments.json').write_text(export_json(segments),encoding='utf-8')
        (out/'subtitle.srt').write_text(export_srt(segments,show_speaker=True),encoding='utf-8-sig')
        (out/'subtitle.ass').write_text(export_ass(segments),encoding='utf-8-sig')
        summary['segments'] = len(segments)
        if result['generated_tokens'] >= a.max_new_tokens:
            summary['warnings'].append('Token limit reached: transcript may be truncated; raw output retained')
        if summary['status'] != 'silent_zero_signal' and not segments:
            summary['warnings'].append('No parsed segments: could be no speech or malformed model output; inspect raw transcript')
        invalid = [s.to_dict() for s in segments if not (0 <= s.start < s.end <= summary['audio_seconds']+1)]
        if invalid:
            summary['warnings'].append('Invalid/out-of-range timestamps detected; inspect segments before using subtitles')
        summary['last_segment_end'] = max((s.end for s in segments),default=None)
        if summary['warnings'] and summary['status']=='completed':
            summary['status']='needs_review'
    except Exception as exc:
        summary['error'] = f'{type(exc).__name__}: {exc}'
        import traceback
        traceback.print_exc()
    finally:
        model = processor = None
        gc.collect()
        if torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()
            summary['allocated_after_cleanup_bytes'] = torch.cuda.memory_allocated()
        if lock is not None:
            lock.close()
        summary['total_seconds'] = time.perf_counter()-started
        (out/'run_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    return 1 if summary['status']=='failed' else 2 if summary['status']=='needs_review' else 0

if __name__=='__main__':
    raise SystemExit(main())
