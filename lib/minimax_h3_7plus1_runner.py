"""Run the verified Singularity R2V 7+1 API presets; patch exposed ports only."""

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

PROFILES = {'work': (672, 384), '1080': (960, 544)}


def project_output(path: str) -> Path:
    output = Path(path).expanduser().resolve()
    if output.is_relative_to(Path(WORKSPACE_ROOT).resolve()):
        raise ValueError('Output must be outside the toolbox, in the caller project')
    return output


def build_prompt(*, prompt: str, image_names: list[str], profile: str = 'work',
                 attention: str = 'dense', duration: float = 5.0, seed: int = 42,
                 ref_image_size: str = 'match', filename_prefix: str = 'video/h3_7plus1') -> tuple[dict, str]:
    alias = 'minimax_h3_7plus1' + ('_sol' if attention == 'sol' else '')
    api_path, ports_path = resolve_preset(alias)
    with open(api_path, encoding='utf-8') as stream:
        api = json.load(stream)
    with open(ports_path, encoding='utf-8') as stream:
        ports = json.load(stream)
    width, height = PROFILES[profile]
    apply_ports(api, ports, {'positive': prompt, 'reference_images': '\n'.join(image_names),
                           'width': width, 'height': height, 'duration': duration,
                           'seed': seed, 'ref_image_size': ref_image_size,
                           'filename_prefix': filename_prefix}, copy_images=False)
    return api, api_path


def generate(*, prompt: str, images: list[str], output_path: str, profile: str = 'work',
             attention: str = 'dense', duration: float = 5.0, seed: int | None = None,
             ref_image_size: str = 'match', server: str = DEFAULT_SERVER,
             timeout: float = 900.0, dry_run: bool = False) -> dict:
    output = project_output(output_path)
    if output.suffix.lower() != '.mp4':
        raise ValueError('Output must have an .mp4 extension')
    if not images or not prompt.strip():
        raise ValueError('Reference images and a non-empty prompt are required')
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Duration must be finite and greater than zero')
    if profile not in PROFILES or attention not in ('dense', 'sol'):
        raise ValueError('Unsupported profile or attention mode')
    if seed is not None and not 0 <= seed < 2**64:
        raise ValueError('Seed must be an unsigned 64-bit integer')
    sources = [Path(path).expanduser().resolve() for path in images]
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(source)
    seed = seed if seed is not None else random.randint(0, 2**63 - 1)
    run_id = uuid.uuid4().hex[:12]
    names = [f'h3_71_{run_id}_{i}{source.suffix.lower()}' for i, source in enumerate(sources)]
    api, api_path = build_prompt(prompt=prompt, image_names=names, profile=profile,
                                attention=attention, duration=duration, seed=seed,
                                ref_image_size=ref_image_size, filename_prefix=f'video/h3_7plus1/{run_id}')
    output.parent.mkdir(parents=True, exist_ok=True)
    graph_path = output.with_suffix('.api.json')
    graph_path.write_text(json.dumps(api, ensure_ascii=False, indent=2), encoding='utf-8')
    if dry_run:
        return {'dry_run': True, 'api_path': str(graph_path), 'seed': seed,
                'reference_images': [str(source) for source in sources],
                'note': 'No files staged and no Comfy request sent; image names are placeholders until a real run'}
    session = ensure_engine(FAMILY_MINIMAX_H3, server_address=server, caller='minimax_h3_7plus1')
    if not session.get('ok', False):
        raise RuntimeError(session.get('message') or session.get('error') or 'Comfy engine memory gate failed')
    input_dir = Path(get_comfy_input_dir(server))
    input_dir.mkdir(parents=True, exist_ok=True)
    for source, name in zip(sources, names):
        shutil.copy2(source, input_dir / name)
    started = time.monotonic()
    prompt_id = queue_prompt(server, api)
    history = wait_for_history(server, prompt_id, timeout_sec=timeout)
    filename, subfolder, filetype = extract_first_video(history)
    if filetype != 'output':
        raise RuntimeError(f'Expected saved video output, received {filetype}')
    source = Path(get_comfy_output_dir(server)) / subfolder / filename
    shutil.copy2(source, output)
    width, height = PROFILES[profile]
    meta = {'tool': 'minimax_h3_7plus1', 'task': 'r2v', 'profile': profile,
            'attention': attention, 'seed': seed, 'requested_duration_sec': duration,
            'start_size': [width, height], 'output_size': [width * 2, height * 2],
            'steps': 8, 'split_steps': 7, 'latent_upscale': 2,
            'ref_image_size': ref_image_size, 'reference_images': [str(p) for p in sources],
            'prompt': prompt, 'preset_path': api_path, 'executed_api': str(graph_path),
            'models': {'diffusion': api['127']['inputs']['unet_name'],
                       'lora': api['192']['inputs']['lora_name'],
                       'text_encoder': api['128']['inputs']['clip_name']},
            'output_path': str(output), 'prompt_id': prompt_id,
            'elapsed_sec': round(time.monotonic() - started, 2), 'created_at': utc_now_iso()}
    write_meta(str(output.with_suffix('.meta.json')), meta)
    return meta
