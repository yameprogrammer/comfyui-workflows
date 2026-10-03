"""Run memory-managed H3 modes; reuse the existing verified R2V 7+1 preset."""

from __future__ import annotations

import json
import math
import random
import shutil
import time
import uuid
from pathlib import Path

from lib.comfy_client import (
    DEFAULT_SERVER, WORKSPACE_ROOT, get_comfy_input_dir, get_comfy_output_dir,
    queue_prompt, utc_now_iso, wait_for_history, write_meta,
)
from lib.comfy_engine_session import FAMILY_MINIMAX_H3, ensure_engine
from lib.workflow_api_runner import apply_ports, resolve_preset
from lib.workflow_video_runner import extract_first_video

TASKS = ('t2v', 'i2v', 'flf', 'r2v', 'v2v', 'ai2v')
PROFILES = {'draft': (512, 288), 'work': (672, 384), '1080': (960, 544)}


def canvas(profile, aspect, width=None, height=None):
    if profile not in PROFILES or aspect not in ('16:9', '9:16'):
        raise ValueError('Unsupported profile or aspect')
    if (width is None) != (height is None):
        raise ValueError('Specify both --width and --height (first-pass pixels)')
    if width is None:
        width, height = PROFILES[profile]
        if aspect == '9:16':
            width, height = height, width
    if any(not isinstance(x, int) or x < 32 or x % 32 for x in (width, height)):
        raise ValueError('First-pass width and height must be positive multiples of 32')
    if max(width, height) > 8192:
        raise ValueError('First-pass dimensions exceed the resolution node limit')
    return width, height


def build_prompt(*, task, prompt, image_names=None, video_name=None, audio_name=None,
                 profile='work', aspect='16:9', width=None, height=None, duration=5.0,
                 seed=42, attention='dense', ref_image_size='match', audio_start=0.0,
                 filename_prefix='video/h3_optimized'):
    if task not in TASKS:
        raise ValueError('Unsupported H3 task')
    if not prompt.strip():
        raise ValueError('Prompt must not be empty')
    if not math.isfinite(duration) or duration <= 0 or duration > 150:
        raise ValueError('Duration must be finite, positive and at most 150 seconds')
    if not isinstance(seed, int) or not 0 <= seed < 2**64:
        raise ValueError('Seed must be an unsigned 64-bit integer')
    if ref_image_size not in ('match', 'max'):
        raise ValueError('Unsupported reference image size')
    if attention not in ('dense', 'sol') or (attention == 'sol' and task != 'r2v'):
        raise ValueError('Sol is supported only by the existing R2V preset')
    if not math.isfinite(audio_start) or audio_start < 0:
        raise ValueError('Audio start must be finite and nonnegative')
    images = list(image_names or [])
    if len(images) > 9:
        raise ValueError('H3 supports at most nine reference images')
    if task in ('i2v', 'r2v', 'ai2v') and not images:
        raise ValueError(f'{task} requires an image')
    if task == 'flf' and len(images) != 2:
        raise ValueError('flf requires exactly a first and a last image')
    if task == 'i2v' and len(images) != 1:
        raise ValueError('i2v requires exactly one first image')
    if task in ('t2v', 'v2v') and images:
        raise ValueError(f'{task} does not accept image inputs; use r2v/ai2v or the specialized legacy tool')
    if task == 'v2v' and not video_name:
        raise ValueError('v2v requires --ref-video')
    if video_name and task != 'v2v':
        raise ValueError('Use --task v2v for a video reference')
    if task == 'ai2v' and not audio_name:
        raise ValueError('ai2v requires --audio')
    if audio_name and task != 'ai2v':
        raise ValueError('Use --task ai2v for an audio reference')
    w, h = canvas(profile, aspect, width, height)
    alias = ('minimax_h3_7plus1' + ('_sol' if attention == 'sol' else '')) if task == 'r2v' else f'minimax_h3_optimized_{task}'
    api_path, ports_path = resolve_preset(alias)
    api = json.loads(Path(api_path).read_text(encoding='utf-8'))
    ports = json.loads(Path(ports_path).read_text(encoding='utf-8'))
    values = {'positive': prompt, 'width': w, 'height': h, 'duration': duration,
              'seed': seed, 'filename_prefix': filename_prefix}
    if task in ('r2v', 'ai2v'):
        values['reference_images'] = '\n'.join(images)
    if task in ('i2v', 'flf'):
        values['first_frame'] = images[0]
    if task == 'flf':
        values['last_frame'] = images[1]
    if task == 'v2v':
        values['reference_video'] = video_name
    if task == 'ai2v':
        values.update(reference_audio=audio_name, audio_start=audio_start)
    if 'ref_image_size' in ports['ports']:
        values['ref_image_size'] = ref_image_size
    apply_ports(api, ports, values, copy_images=False)
    if 'ref_image_size' in api['141']['inputs']:
        api['141']['inputs']['ref_image_size'] = ref_image_size
    # Manual Input owns the dimensions; keep the visible ratio label consistent.
    api['145']['inputs']['ratio_preset'] = '9:16' if w < h else '16:9'
    return api, api_path, (w, h)


def generate(*, task, prompt, images=None, video=None, audio=None, output_path,
             profile='work', aspect='16:9', width=None, height=None, duration=5.0,
             seed=None, attention='dense', ref_image_size='match', audio_start=0.0,
             server=DEFAULT_SERVER, timeout=900.0, dry_run=False):
    output = Path(output_path).expanduser().resolve()
    if output.is_relative_to(Path(WORKSPACE_ROOT).resolve()):
        raise ValueError('Output must be in the caller project, outside the toolbox')
    if output.suffix.lower() != '.mp4':
        raise ValueError('Output must have an .mp4 extension')
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('Timeout must be finite and positive')
    image_paths = [Path(p).expanduser().resolve() for p in (images or [])]
    video_path = Path(video).expanduser().resolve() if video else None
    audio_path = Path(audio).expanduser().resolve() if audio else None
    for source in [*image_paths, *([video_path] if video_path else []), *([audio_path] if audio_path else [])]:
        if not source.is_file():
            raise FileNotFoundError(source)
    seed = seed if seed is not None else random.randint(0, 2**63 - 1)
    run_id = uuid.uuid4().hex[:12]
    staged = [(p, f'h3_opt_{run_id}_image{i}{p.suffix.lower()}') for i, p in enumerate(image_paths)]
    if video_path:
        staged.append((video_path, f'h3_opt_{run_id}_video{video_path.suffix.lower()}'))
    if audio_path:
        staged.append((audio_path, f'h3_opt_{run_id}_audio{audio_path.suffix.lower()}'))
    image_names = [name for _, name in staged[:len(image_paths)]]
    video_name = next((name for path, name in staged if path == video_path), None) if video_path else None
    audio_name = next((name for path, name in staged if path == audio_path), None) if audio_path else None
    api, preset_path, size = build_prompt(
        task=task, prompt=prompt, image_names=image_names, video_name=video_name, audio_name=audio_name,
        profile=profile, aspect=aspect, width=width, height=height, duration=duration, seed=seed,
        attention=attention, ref_image_size=ref_image_size, audio_start=audio_start,
        filename_prefix=f'video/h3_optimized/{task}/{run_id}')
    output.parent.mkdir(parents=True, exist_ok=True)
    graph_path = output.with_suffix('.api.json')
    graph_path.write_text(json.dumps(api, ensure_ascii=False, indent=2), encoding='utf-8')
    if dry_run:
        return {'dry_run': True, 'task': task, 'api_path': str(graph_path), 'preset_path': preset_path,
                'start_size': list(size), 'output_size': [n * 2 for n in size], 'seed': seed,
                'note': 'No server request or media staging; generated input names are placeholders'}
    session = ensure_engine(FAMILY_MINIMAX_H3, server_address=server, caller='minimax_h3_optimized')
    if not session.get('ok', False):
        raise RuntimeError(session.get('message') or session.get('error') or 'Comfy memory gate failed')
    input_dir = Path(get_comfy_input_dir(server))
    input_dir.mkdir(parents=True, exist_ok=True)
    for source, name in staged:
        shutil.copy2(source, input_dir / name)
    started = time.monotonic()
    prompt_id = queue_prompt(server, api)
    history = wait_for_history(server, prompt_id, timeout_sec=timeout)
    filename, subfolder, filetype = extract_first_video(history)
    if filetype != 'output':
        raise RuntimeError(f'Expected saved video output, received {filetype}')
    source = Path(get_comfy_output_dir(server)) / subfolder / filename
    shutil.copy2(source, output)
    meta = {'tool': 'minimax_h3_optimized', 'task': task, 'profile': profile, 'aspect': aspect,
            'start_size': list(size), 'output_size': [n * 2 for n in size], 'seed': seed,
            'requested_duration_sec': duration, 'attention': attention, 'ref_image_size': ref_image_size,
            'audio_start': audio_start, 'reference_images': [str(p) for p in image_paths],
            'reference_video': str(video_path) if video_path else None,
            'reference_audio': str(audio_path) if audio_path else None,
            'steps': api['185']['inputs']['steps'], 'split_steps': api['194']['inputs']['step'],
            'prompt': prompt, 'preset_path': preset_path, 'executed_api': str(graph_path),
            'output_path': str(output), 'prompt_id': prompt_id,
            'elapsed_sec': round(time.monotonic() - started, 2), 'created_at': utc_now_iso(),
            'models': {'diffusion': api['127']['inputs']['unet_name'],
                       'text_encoder': api['128']['inputs']['clip_name']}}
    write_meta(str(output.with_suffix('.meta.json')), meta)
    return meta
