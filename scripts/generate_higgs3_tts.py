"""Higgs TTS 3 through original local ComfyUI, with a private Transformers 5 worker.

Example: python scripts/generate_higgs3_tts.py -t "Hello there." --emotion elation -o D:/my_project/voice.wav
Guide: workflows/human/higgs3_tts/AGENT_GUIDE.md
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import uuid
import urllib.parse
import urllib.request
from pathlib import Path

if (Path(__file__).parent / '_bootstrap.py').is_file():
    import _bootstrap
else:
    sys.path.insert(0, r'F:\Agent_media_tools')

from lib.comfy_client import (get_comfy_input_dir, queue_prompt, wait_for_history,
                              extract_first_audio, download_audio)
from lib.comfy_engine_session import ensure_engine


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    text = parser.add_mutually_exclusive_group(required=True)
    text.add_argument('-t', '--text')
    text.add_argument('--text-file', type=Path)
    parser.add_argument('-o', '--output', required=True, type=Path)
    parser.add_argument('--emotion', choices=['neutral', 'elation', 'sadness', 'anger', 'contentment', 'enthusiasm', 'fear'], default='neutral')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--max-new-tokens', type=int, default=512)
    parser.add_argument('--temperature', type=float, default=0.8)
    parser.add_argument('--ref-audio', type=Path)
    parser.add_argument('--ref-text', default='')
    parser.add_argument('--ref-text-file', type=Path)
    parser.add_argument('--server', default='127.0.0.1:8188')
    parser.add_argument('--timeout', type=float, default=1800)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    server = args.server.removeprefix('http://').rstrip('/')
    if urllib.parse.urlparse('http://' + server).hostname not in {'localhost', '127.0.0.1'}:
        parser.error('This tool uses local ComfyUI only')
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    value = args.text_file.read_text(encoding='utf-8-sig') if args.text_file else args.text
    ref_text = args.ref_text_file.read_text(encoding='utf-8-sig') if args.ref_text_file else args.ref_text
    graph = {
        '1': {'class_type': 'Higgs3IsolatedTTS', 'inputs': {
            'text': value, 'emotion': args.emotion, 'seed': args.seed,
            'max_new_tokens': args.max_new_tokens, 'temperature': args.temperature,
            'reference_text': ref_text}},
        '2': {'class_type': 'SaveAudio', 'inputs': {
            'audio': ['1', 0], 'filename_prefix': 'higgs3/voice'}}}
    ref_copy = None
    started = time.perf_counter()
    result = {'tool': 'generate_higgs3_tts', 'server': server, 'output_path': str(output),
              'emotion': args.emotion, 'seed': args.seed, 'status': 'prepared',
              'listening_qc': 'not_performed'}
    try:
        if not args.dry_run:
            with urllib.request.urlopen('http://' + server + '/queue', timeout=10) as response:
                queue = json.load(response)
            if queue.get('queue_running') or queue.get('queue_pending'):
                raise RuntimeError('ComfyUI queue is busy; nothing was submitted')
            result['engine_session'] = ensure_engine('higgs3_tts', server, caller='generate_higgs3_tts')
            if not result['engine_session'].get('ok'):
                raise RuntimeError('Factory memory gate failed')
        if args.ref_audio:
            if not args.ref_audio.is_file():
                raise FileNotFoundError(args.ref_audio)
            ref_name = 'higgs3_ref_' + uuid.uuid4().hex + args.ref_audio.suffix.lower()
            if not args.dry_run:
                ref_copy = Path(get_comfy_input_dir(server)) / ref_name
                shutil.copy2(args.ref_audio, ref_copy)
            graph['3'] = {'class_type': 'LoadAudio', 'inputs': {'audio': ref_name}}
            graph['1']['inputs']['reference_audio'] = ['3', 0]
        output.with_suffix('.api.json').write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding='utf-8')
        if args.dry_run:
            result['status'] = 'dry_run'
        else:
            prompt_id = queue_prompt(server, graph)
            result['prompt_id'] = prompt_id
            history = wait_for_history(server, prompt_id, timeout_sec=args.timeout, poll_interval=0.5)
            output.with_suffix('.history.json').write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding='utf-8')
            filename, subfolder, kind = extract_first_audio(history)
            downloaded = output.with_name(output.stem + '.comfy.flac')
            download_audio(server, filename, subfolder, kind, str(downloaded))
            import soundfile as sf
            wav, sr = sf.read(downloaded, dtype='float32')
            sf.write(output, wav, sr)
            downloaded.unlink()
            result['metrics'] = json.loads(history['outputs']['1']['text'][0])
            result['status'] = 'execution_success'
    except Exception as exc:
        result.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        result['wall_seconds'] = time.perf_counter() - started
        output.with_suffix('.result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        # Reference filenames remain reproducible while a timed-out server job might still need them.
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
