"""Bounded DenoMix R2V 8+2 on an existing local ComfyUI server."""
from __future__ import annotations

import hashlib
import json
import math
import random
import re
import shutil
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from lib.comfy_client import (
    DEFAULT_SERVER, WORKSPACE_ROOT, _http_json, get_comfy_input_dir,
    get_comfy_output_dir, get_queue, get_system_stats, queue_prompt,
    utc_now_iso, wait_for_history, write_meta,
)
from lib.workflow_api_runner import apply_ports, resolve_preset
from lib.workflow_video_runner import extract_first_video

PRESET = 'minimax_h3_denomix'
DEFAULT_DURATION = 5.0
MAX_DURATION = 10.0
START_SIZE = (896, 512)


def aligned_frames(duration):
    if not isinstance(duration, (int, float)) or isinstance(duration, bool) or not math.isfinite(duration) or not 0 < duration <= MAX_DURATION:
        raise ValueError('Requested duration must be finite, greater than 0 and at most 10 seconds')
    frames = max(5, round(duration * 24))
    return frames + (5 - frames % 17) % 17


def local_server(server):
    parts = urlsplit('http://' + server)
    if parts.hostname not in ('127.0.0.1', 'localhost', '::1') or parts.username or parts.password or parts.path or parts.query or parts.fragment:
        raise ValueError('Use a loopback ComfyUI host:port; remote uploads are not supported')
    if parts.port is None:
        raise ValueError('ComfyUI server requires a port')
    return server


def build_prompt(*, prompt, image_names, duration=DEFAULT_DURATION, seed=42,
                 filename_prefix='video/h3_denomix'):
    frames = aligned_frames(duration)
    if not prompt.strip():
        raise ValueError('Prompt must not be empty')
    if not image_names:
        raise ValueError('At least one reference image is required')
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed < 2**64:
        raise ValueError('Seed must be an unsigned 64-bit integer')
    api_path, ports_path = resolve_preset(PRESET)
    api = json.loads(Path(api_path).read_text(encoding='utf-8'))
    ports = json.loads(Path(ports_path).read_text(encoding='utf-8'))
    apply_ports(api, ports, {'positive': prompt, 'reference_images': '\n'.join(image_names),
                           'duration': duration, 'seed': seed, 'filename_prefix': filename_prefix}, copy_images=False)
    return api, api_path, frames


def model_status(server=DEFAULT_SERVER, job_id=None):
    server = local_server(server)
    stats = get_system_stats(server, ensure=False)
    queue = get_queue(server, ensure=False)
    info = _http_json(server, '/object_info')
    api_path, _ = resolve_preset(PRESET)
    api = json.loads(Path(api_path).read_text(encoding='utf-8'))
    missing_nodes = sorted({n['class_type'] for n in api.values()} - set(info))
    missing_models = []
    for node, key in [('127', 'unet_name'), ('128', 'clip_name'), ('119', 'vae_name'), ('120', 'vae_name'),
                      ('192', 'lora_name'), ('199', 'lora_name'), ('216', 'lora_name'), ('197', 'model_name')]:
        entry = api[node]
        schema = info.get(entry['class_type'], {}).get('input', {}).get('required', {}).get(key)
        if schema:
            options = schema[0] if isinstance(schema[0], list) else schema[1].get('options', [])
            expected = entry['inputs'][key]
            if expected.replace('\\', '/') not in [str(v).replace('\\', '/') for v in options]:
                missing_models.append({'node': node, 'input': key, 'file': expected})
    result = {'tool': PRESET, 'available': not missing_nodes and not missing_models,
              'missing_nodes': missing_nodes, 'missing_models': missing_models,
              'running_ids': [r[1] for r in queue.get('queue_running', [])],
              'pending_ids': [r[1] for r in queue.get('queue_pending', [])],
              'default_requested_seconds': DEFAULT_DURATION, 'maximum_requested_seconds': MAX_DURATION,
              'ten_second_request': {'frames': 243, 'actual_seconds': 10.125},
              'system': stats.get('system'), 'devices': stats.get('devices')}
    if job_id:
        if not re.fullmatch(r'[0-9a-fA-F-]{36}', job_id):
            raise ValueError('Job ID must be a ComfyUI UUID')
        history = _http_json(server, '/history/' + job_id)
        record = history.get(job_id)
        result['job'] = {'prompt_id': job_id, 'status': record.get('status') if record else 'not_in_history',
                         'outputs': record.get('outputs') if record else None}
    return result


def generate(*, prompt, images, output_path, duration=DEFAULT_DURATION, seed=None,
             server=DEFAULT_SERVER, timeout=900.0, dry_run=False):
    # All request validation precedes server access, input staging and submission.
    frames = aligned_frames(duration)
    server = local_server(server)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('Timeout must be finite and positive')
    output = Path(output_path).expanduser().resolve()
    if output.is_relative_to(Path(WORKSPACE_ROOT).resolve()) or output.suffix.lower() != '.mp4':
        raise ValueError('Output must be an .mp4 in the caller project, outside the toolbox')
    graph = output.with_suffix('.api.json')
    meta_path = output.with_suffix('.meta.json')
    history_path = output.with_suffix('.history.json')
    if any(p.exists() for p in (output, graph, meta_path, history_path)):
        raise FileExistsError('Output or sidecar exists; select a new output name')
    sources = [Path(p).expanduser().resolve() for p in images]
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(source)
    seed = seed if seed is not None else random.randrange(2**63)
    run_id = uuid.uuid4().hex[:12]
    staged = [(p, f'h3_denomix_{run_id}_{i}{p.suffix.lower()}') for i, p in enumerate(sources)]
    api, preset_path, _ = build_prompt(prompt=prompt, image_names=[n for _, n in staged],
        duration=duration, seed=seed, filename_prefix=f'video/h3_denomix/{run_id}')
    meta = {'tool': PRESET, 'run_id': run_id, 'client_id': 'h3-denomix-' + run_id, 'status': 'dry_run' if dry_run else 'preflight',
            'requested_duration_sec': duration, 'frame_count': frames, 'fps': 24,
            'aligned_duration_sec': frames / 24, 'operational_max_requested_sec': MAX_DURATION,
            'start_size': list(START_SIZE), 'output_size': [1792, 1024], 'steps': [8, 2],
            'seed': seed, 'prompt': prompt, 'reference_images': [str(p) for p in sources],
            'reference_sha256': [hashlib.sha256(p.read_bytes()).hexdigest() for p in sources],
            'preset_path': preset_path, 'executed_api': str(graph), 'output_path': str(output),
            'history_path': str(history_path), 'created_at': utc_now_iso(),
            'quality': 'Human identity, audio listening and lip-sync review required'}
    output.parent.mkdir(parents=True, exist_ok=True)
    graph.write_text(json.dumps(api, ensure_ascii=False, indent=2), encoding='utf-8')
    write_meta(str(meta_path), meta)
    if dry_run:
        return meta
    started = time.monotonic()
    try:
        state = model_status(server)
        if not state['available']:
            raise RuntimeError(f'Missing nodes/models: {state["missing_nodes"]} {state["missing_models"]}')
        if state['running_ids'] or state['pending_ids']:
            raise RuntimeError('ComfyUI queue is occupied; no inputs staged or job submitted')
        input_dir = Path(get_comfy_input_dir(server))
        input_dir.mkdir(parents=True, exist_ok=True)
        for source, name in staged:
            shutil.copy2(source, input_dir / name)
        meta.update(status='submitting', server=server)
        write_meta(str(meta_path), meta)
        prompt_id = queue_prompt(server, api, ensure=False, retry_on_connection_error=False,
                                 client_id=meta['client_id'])
        meta.update(status='submitted', prompt_id=prompt_id, server=server)
        print(f'[denomix] queued {prompt_id}; timeout does not cancel the job', file=sys.stderr, flush=True)
        write_meta(str(meta_path), meta)
        history = wait_for_history(server, prompt_id, timeout_sec=timeout)
        write_meta(str(history_path), history)
        filename, subfolder, filetype = extract_first_video(history)
        if filetype != 'output':
            raise RuntimeError('Expected saved output video')
        root = Path(get_comfy_output_dir(server)).resolve()
        source = (root / subfolder / filename).resolve()
        if not source.is_relative_to(root):
            raise RuntimeError('Returned output path escapes ComfyUI output directory')
        shutil.copy2(source, output)
        meta.update(status='success', server_output=str(source), output_bytes=output.stat().st_size)
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        state = 'pending' if isinstance(exc, TimeoutError) else 'submission_unknown' if isinstance(exc, ConnectionError) and meta['status'] == 'submitting' else 'failed'
        meta.update(status=state, error=str(exc))
        if meta.get('prompt_id'):
            meta['job_lookup'] = f'--status --job-id {meta["prompt_id"]}'
        if meta.get('prompt_id') and not isinstance(exc, TimeoutError) and not history_path.exists():
            try:
                entry = _http_json(server, '/history/' + meta['prompt_id']).get(meta['prompt_id'])
                if entry:
                    write_meta(str(history_path), entry)
            except ConnectionError:
                pass
        raise
    finally:
        meta['elapsed_sec'] = round(time.monotonic() - started, 2)
        write_meta(str(meta_path), meta)
    return meta
