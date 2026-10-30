"""Validated native MOSS presets; local API only, no installation or server lifecycle changes."""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

from lib import comfy_client
from lib.output_policy import assert_outside_toolbox

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / 'workflows' / 'agent' / 'moss_image'
MODES = ('t2i', 'layout', 'edit', 'multi-edit', 'control', 'color', 'depth')
EDIT_MODES = ('edit', 'multi-edit')
CONTROL_MODES = ('control', 'color', 'depth')
FILES = {'multi-edit': 'multi_edit.api.json'}
MODEL_INPUTS = {'UNETLoader': 'unet_name', 'CLIPLoader': 'clip_name', 'VAELoader': 'vae_name',
                'LoraLoaderModelOnly': 'lora_name'}
SIDE_SUFFIXES = ('.api.json', '.result.json', '.history.json')


class MossImageError(RuntimeError):
    def __init__(self, message, exit_code=1):
        super().__init__(message)
        self.exit_code = exit_code


def local_server(value):
    raw = str(value).strip()
    parsed = urlparse(raw if '://' in raw else 'http://' + raw)
    try:
        port = parsed.port or 8188
    except ValueError:
        raise MossImageError('Invalid local ComfyUI port', 2) from None
    if (parsed.scheme != 'http' or parsed.hostname not in ('localhost', '127.0.0.1', '::1')
            or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment
            or not 1 <= port <= 65535):
        raise MossImageError('Use local unauthenticated HTTP ComfyUI only (127.0.0.1:8188)', 2)
    host = '[::1]' if parsed.hostname == '::1' else parsed.hostname
    return f'{host}:{port}'


def api_get(server, route, timeout=15):
    try:
        with urlopen(f'http://{server}{route}', timeout=timeout) as response:
            return json.load(response)
    except (URLError, OSError, ValueError) as exc:
        raise MossImageError(f'ComfyUI read failed at {server}: {exc}. Start/check it manually; no restart attempted.', 10) from exc


def template(mode, workflow_dir=None):
    if mode not in MODES:
        raise MossImageError(f'Unsupported MOSS mode: {mode}', 2)
    path = Path(workflow_dir or WORKFLOWS) / FILES.get(mode, mode + '.api.json')
    return json.loads(path.read_text(encoding='utf-8-sig'))


def choices(info, node, name):
    fields = info.get(node, {}).get('input', {})
    spec = fields.get('required', {}).get(name, fields.get('optional', {}).get(name, []))
    if spec and isinstance(spec[0], list):
        return spec[0]
    return spec[1].get('options', []) if len(spec) > 1 and isinstance(spec[1], dict) else []


def missing_requirements(graph, info):
    missing = []
    for node in graph.values():
        kind, inputs = node['class_type'], node['inputs']
        if kind not in info:
            missing.append('node:' + kind)
        field = MODEL_INPUTS.get(kind)
        if field and inputs[field] not in choices(info, kind, field):
            missing.append(f'model:{inputs[field]}')
    if 'moss_image' not in choices(info, 'CLIPLoader', 'type'):
        missing.append('CLIPLoader:type=moss_image')
    return sorted(set(missing))


def model_status(server='127.0.0.1:8188'):
    server = local_server(server)
    try:
        stats = comfy_client.get_system_stats(server, ensure=False)
        queue = comfy_client.get_queue(server, ensure=False)
    except ConnectionError as exc:
        raise MossImageError(f'ComfyUI is unavailable: {exc}. No server start attempted.', 10) from exc
    info = api_get(server, '/object_info', 30)
    required = {mode: missing_requirements(template(mode), info) for mode in MODES}
    return {'ok': True, 'tool': 'generate_moss_image', 'status': 'availability_only', 'server': server,
            'comfyui_version': stats.get('system', {}).get('comfyui_version'),
            'available_modes': {mode: not absent for mode, absent in required.items()},
            'missing': required, 'queue_running': len(queue.get('queue_running', [])),
            'queue_pending': len(queue.get('queue_pending', [])),
            'note': 'Loader listings only, not checksum or quality verification. Missing models are never downloaded.'}


def dimensions(width, height):
    for name, value in [('width', width), ('height', height)]:
        if type(value) is not int or value < 16 or value > 4096 or value % 16:
            raise MossImageError(f'{name} must be a positive multiple of 16 between 16 and 4096', 2)
    if width * height > 4 * 1024 * 1024:
        raise MossImageError('This local profile is limited to 4 megapixels and batch 1', 2)
    return width, height


def image_info(value, role):
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise MossImageError(f'{role} image not found: {path}', 2)
    if path.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp'):
        raise MossImageError(f'{role} must be a PNG, JPEG or WebP still image', 2)
    try:
        with Image.open(path) as im:
            if getattr(im, 'n_frames', 1) != 1:
                raise ValueError('Animated inputs are not supported')
            im.load()
            width, height = ImageOps.exif_transpose(im).size
    except (OSError, ValueError) as exc:
        raise MossImageError(f'Cannot decode {role}: {path}: {exc}', 2) from exc
    return {'path': str(path), 'role': role, 'width': width, 'height': height,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def read_layout(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        raise MossImageError(f'Cannot read layout JSON: {exc}', 2) from exc
    if not isinstance(data, dict) or set(data) - {'width', 'height', 'prompt', 'boxes'}:
        raise MossImageError('Layout JSON needs width, height, prompt and boxes; unknown keys are rejected', 2)
    width, height = dimensions(data.get('width'), data.get('height'))
    boxes = data.get('boxes')
    if not isinstance(boxes, list) or not 1 <= len(boxes) <= 32:
        raise MossImageError('Layout requires 1-32 pixel boxes', 2)
    normalized, characters = [], []
    for index, box in enumerate(boxes):
        if not isinstance(box, dict):
            raise MossImageError('Each layout box must be an object', 2)
        x, y, w, h = (box.get(k) for k in ('x', 'y', 'width', 'height'))
        if (any(type(v) is not int for v in (x, y, w, h)) or min(x, y) < 0 or min(w, h) <= 0
                or x + w > width or y + h > height):
            raise MossImageError(f'Layout box {index + 1} is outside the canvas or has invalid integer pixel dimensions', 2)
        meta = box.get('metadata', box)
        if not isinstance(meta, dict):
            raise MossImageError('Box metadata must be an object', 2)
        kind = meta.get('type', 'obj')
        if kind not in ('text', 'obj', 'object', 'character'):
            raise MossImageError('Box type must be text, object/obj, or character', 2)
        text = meta.get('text', '')
        desc = meta.get('description', meta.get('desc', ''))
        if not isinstance(text, str) or not isinstance(desc, str) or not (text.strip() if kind == 'text' else desc.strip()):
            raise MossImageError('Text boxes need text; object/character boxes need a description', 2)
        if kind == 'character':
            characters.append(str(index + 1))
        normalized.append({'x': x, 'y': y, 'width': w, 'height': h,
                           'metadata': {'type': 'text' if kind == 'text' else 'obj', 'text': text, 'desc': desc, 'palette': []}})
    if 'prompt' in data and not isinstance(data['prompt'], str):
        raise MossImageError('Layout prompt must be text', 2)
    return {'width': width, 'height': height, 'prompt': data.get('prompt', ''), 'boxes': normalized,
            'character_boxes': ','.join(characters)}


def finite_number(value, name, lower, upper):
    if not isinstance(value, (float, int)) or isinstance(value, bool) or not math.isfinite(value) or not lower <= value <= upper:
        raise MossImageError(f'{name} must be finite and between {lower} and {upper}', 2)
    return value


def prepare(*, mode, prompt, negative=None, images=(), layout=None, color_map=None, depth_map=None,
            width=None, height=None, seed=None, steps=None, cfg=None, reference_max_edge=None,
            lora_strength=None, control_strength=None, control_end=None, workflow_dir=None):
    graph = template(mode, workflow_dir)
    if bool(width is not None) != bool(height is not None):
        raise MossImageError('Provide --width and --height together', 2)
    if mode not in EDIT_MODES and (images or reference_max_edge is not None):
        raise MossImageError('Image references and --reference-max-edge belong to edit/multi-edit only', 2)
    if mode in EDIT_MODES and (len(images) != 1 if mode == 'edit' else not 2 <= len(images) <= 4):
        raise MossImageError('edit needs exactly one image; multi-edit needs 2-4 ordered references', 2)
    if (mode == 'layout') != bool(layout):
        raise MossImageError('--layout is required only in layout mode', 2)
    expected_maps = {'control': (True, True), 'color': (True, False), 'depth': (False, True)}.get(mode, (False, False))
    if (bool(color_map), bool(depth_map)) != expected_maps:
        raise MossImageError('control needs both maps; color only --color-map; depth only --depth-map; other modes forbid maps', 2)
    if mode not in EDIT_MODES + CONTROL_MODES and lora_strength is not None:
        raise MossImageError('--lora-strength belongs to Edit/Control only', 2)
    if mode not in CONTROL_MODES and (control_strength is not None or control_end is not None):
        raise MossImageError('Control strength/end belong to Control modes only', 2)
    records = [image_info(value, f'reference_{i + 1}') for i, value in enumerate(images)]
    if len({r['path'] for r in records}) != len(records):
        raise MossImageError('Use distinct files for multiple references', 2)
    for value, role in [(color_map, 'color_map'), (depth_map, 'depth_map')]:
        if value:
            records.append(image_info(value, role))
    layout_data = read_layout(layout) if layout else None
    if layout_data:
        if width is not None and (width, height) != (layout_data['width'], layout_data['height']):
            raise MossImageError('Layout JSON dimensions must match output; edit its pixel boxes instead of implicit rescaling', 2)
        width, height = layout_data['width'], layout_data['height']
        prompt = prompt if prompt is not None else layout_data['prompt']
        graph['10']['inputs'].update(width=width, height=height, editor_state={'__value__': layout_data['boxes']})
        graph['11']['inputs'].update(prompt=prompt, width=width, height=height, character_boxes=layout_data['character_boxes'])
    if not isinstance(prompt, str) or not prompt.strip():
        raise MossImageError('A nonempty --prompt/--prompt-file is required (or layout JSON prompt)', 2)
    if negative is not None and not isinstance(negative, str):
        raise MossImageError('Negative prompt must be text', 2)
    if width is None:
        if mode in CONTROL_MODES:
            width, height = records[0]['width'], records[0]['height']
        elif mode in EDIT_MODES:
            area = graph['6']['inputs']['width'] * graph['6']['inputs']['height']
            scale = math.sqrt(area / (records[0]['width'] * records[0]['height']))
            width = max(16, round(records[0]['width'] * scale / 16) * 16)
            height = max(16, round(records[0]['height'] * scale / 16) * 16)
        else:
            width, height = graph['6']['inputs']['width'], graph['6']['inputs']['height']
    dimensions(width, height)
    graph['6']['inputs'].update(width=width, height=height)
    if mode != 'layout':
        graph['4']['inputs']['prompt' if mode in EDIT_MODES else 'text'] = prompt
    if negative is not None:
        graph['5']['inputs']['prompt' if mode in EDIT_MODES else 'text'] = negative
    sampler = graph['7']['inputs']
    if seed is not None:
        if type(seed) is not int or not 0 <= seed < 2**64:
            raise MossImageError('Seed must be an unsigned 64-bit integer', 2)
        sampler['seed'] = seed
    if steps is not None:
        if type(steps) is not int or not 1 <= steps <= 150:
            raise MossImageError('Steps must be an integer between 1 and 150', 2)
        sampler['steps'] = steps
    if cfg is not None:
        sampler['cfg'] = finite_number(cfg, 'CFG', 0, 20)
    if mode in EDIT_MODES:
        edge = 512 if reference_max_edge is None else reference_max_edge
        if type(edge) is not int or not 256 <= edge <= 1024 or edge % 16:
            raise MossImageError('Reference max edge must be a multiple of 16 between 256 and 1024', 2)
        for i, record in enumerate(records):
            scale = min(1.0, edge / max(record['width'], record['height']))
            rw = max(16, round(record['width'] * scale / 16) * 16)
            rh = max(16, round(record['height'] * scale / 16) * 16)
            loader, resize = str(100 + 2*i), str(101 + 2*i)
            graph[loader] = {'class_type': 'LoadImage', 'inputs': {'image': Path(record['path']).name}}
            graph[resize] = {'class_type': 'ImageScale', 'inputs': {'image': [loader, 0], 'upscale_method': 'lanczos', 'width': rw, 'height': rh, 'crop': 'disabled'}}
            record.update(loader_node=loader, encoded_width=rw, encoded_height=rh)
        for node_id in ('4', '5'):
            inputs = graph[node_id]['inputs']
            for key in list(inputs):
                if key.startswith('images.'):
                    del inputs[key]
            for i in range(len(records)):
                inputs[f'images.image_{i}'] = [str(101 + 2*i), 0]
        for node_id in ('10', '11', '14', '15'):
            graph.pop(node_id, None)
    if mode in CONTROL_MODES:
        for record in records:
            if (record['width'], record['height']) != (width, height):
                raise MossImageError('All control maps must match output dimensions; no implicit map resize', 2)
            loader = '13' if record['role'] == 'color_map' else '14'
            graph[loader]['inputs']['image'] = Path(record['path']).name
            record['loader_node'] = loader
        graph['15']['inputs']['strength'] = finite_number(1 if control_strength is None else control_strength, 'Control strength', 0, 10)
        graph['15']['inputs']['end_percent'] = finite_number(0.5 if control_end is None else control_end, 'Control end', 0, 1)
    if mode in EDIT_MODES + CONTROL_MODES:
        graph['12']['inputs']['strength_model'] = finite_number(1 if lora_strength is None else lora_strength, 'LoRA strength', 0, 2)
    return graph, records, layout_data


def upload_image(server, record, run_id):
    path = Path(record['path'])
    boundary = 'moss-' + uuid.uuid4().hex
    name = record['sha256'][:24] + path.suffix.lower()
    folder = 'agent_moss/' + run_id
    pieces = []
    for key, value in [('type', 'input'), ('subfolder', folder), ('overwrite', 'false')]:
        pieces.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    pieces.extend([f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode(), path.read_bytes(), f'\r\n--{boundary}--\r\n'.encode()])
    request = Request(f'http://{server}/upload/image', data=b''.join(pieces), headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    try:
        with urlopen(request, timeout=60) as response:
            item = json.load(response)
    except (URLError, OSError, ValueError) as exc:
        raise MossImageError(f'Local image upload failed: {exc}', 10) from exc
    result = '/'.join(filter(None, [item.get('subfolder', ''), item['name']]))
    if PurePosixPath(result).is_absolute() or '..' in PurePosixPath(result).parts:
        raise MossImageError('Unexpected upload path from ComfyUI', 10)
    return result


@contextmanager
def job_lock():
    path = ROOT / '.agent_cache' / 'moss_image_job.lock'
    path.parent.mkdir(exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise MossImageError(f'Another MOSS CLI owns {path}; inspect its job before removing a stale lock', 12) from None
    os.write(fd, f'pid={os.getpid()}\n'.encode()); os.close(fd)
    try:
        yield
    finally:
        path.unlink()


def ensure_idle(server):
    queue = comfy_client.get_queue(server, ensure=False)
    if queue.get('queue_running') or queue.get('queue_pending'):
        raise MossImageError('ComfyUI queue is busy; nothing submitted or cancelled. Wait and retry.', 12)


def generate(*, mode, prompt, output, server='127.0.0.1:8188', timeout=1800, dry_run=False, overwrite=False, **options):
    server = local_server(server)
    finite_number(timeout, 'Timeout seconds', 1, 86400)
    output = Path(assert_outside_toolbox(str(Path(output).expanduser().resolve())))
    if output.suffix.lower() != '.png':
        raise MossImageError('Output must have a .png extension', 2)
    paths = [output] + [output.with_suffix(suffix) for suffix in SIDE_SUFFIXES]
    if not overwrite and any(path.exists() for path in paths):
        raise MossImageError('Output or sidecar already exists; choose a new name or explicitly use --overwrite', 2)
    graph, records, layout_data = prepare(mode=mode, prompt=prompt, **options)
    source_paths = {Path(r['path']) for r in records}
    if options.get('layout'):
        source_paths.add(Path(options['layout']).resolve())
    if source_paths.intersection(paths):
        raise MossImageError('Output/sidecars cannot replace an input file, even with --overwrite', 2)
    run_id = uuid.uuid4().hex
    graph['9']['inputs']['filename_prefix'] = f'agent_moss/{run_id}/{mode.replace("-", "_")}'
    output.parent.mkdir(parents=True, exist_ok=True)
    sampler = graph['7']['inputs']
    record = {'ok': False, 'tool': 'generate_moss_image', 'task': 'moss_image', 'mode': mode, 'run_id': run_id,
              'status': 'prepared', 'server': server, 'prompt': prompt if not layout_data else graph['11']['inputs']['prompt'],
              'negative': graph['5']['inputs'].get('prompt', graph['5']['inputs'].get('text')),
              'seed': sampler['seed'], 'width': graph['6']['inputs']['width'], 'height': graph['6']['inputs']['height'],
              'steps': sampler['steps'], 'cfg': sampler['cfg'], 'sampler': sampler['sampler_name'], 'scheduler': sampler['scheduler'],
              'models': {n['class_type']: n['inputs'][MODEL_INPUTS[n['class_type']]] for n in graph.values() if n['class_type'] in MODEL_INPUTS},
              'inputs': records, 'layout': layout_data, 'requested_output': str(output),
              'api_path': str(output.with_suffix('.api.json')), 'meta_path': str(output.with_suffix('.result.json')),
              'started_utc': comfy_client.utc_now_iso(), 'visual_qc': 'PENDING_VISUAL_REVIEW',
              'community_extension': mode in EDIT_MODES + CONTROL_MODES,
              'license_note': 'Edit weights: original license not separately stated; commercial review required.' if mode in EDIT_MODES else ('Control: author Apache-2.0; base native MOSS: Apache-2.0.' if mode in CONTROL_MODES else 'Base native MOSS: Apache-2.0.')}
    start = time.monotonic()
    temp = output.with_name(output.name + '.' + run_id + '.partial')
    # Reserve the output name as well as the family GPU slot. Never clear another caller's lock.
    reservation = output.with_suffix('.moss.lock')
    try:
        fd = os.open(reservation, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.close(fd)
    except FileExistsError:
        raise MossImageError('This output is reserved by another caller; inspect it before retrying', 12) from None
    if not overwrite and any(path.exists() for path in paths):
        reservation.unlink()
        raise MossImageError('Output appeared during preparation; existing files were preserved', 2)
    try:
        if overwrite:
            previous = {}
            for path in paths:
                if path.exists() and (not dry_run or path.suffixes[-2:] in [['.api', '.json'], ['.result', '.json']]):
                    saved = path.with_name(path.name + '.previous.' + run_id)
                    path.replace(saved)
                    previous[str(path)] = str(saved)
            record['previous_outputs'] = previous
        if dry_run:
            for r in records:
                graph[r['loader_node']]['inputs']['image'] = f'agent_moss/DRY_RUN/{r["sha256"][:24]}{Path(r["path"]).suffix.lower()}'
            comfy_client.write_meta(str(output.with_suffix('.api.json')), graph)
            record.update(ok=True, status='dry_run', network_used=False)
            return record
        with job_lock():
            ensure_idle(server)
            info = api_get(server, '/object_info', 30)
            missing = missing_requirements(graph, info)
            if missing:
                raise MossImageError('Missing native MOSS requirements: ' + ', '.join(missing) + '. See workflows/human/moss_image/AGENT_GUIDE.md; no install/download attempted.', 11)
            record['comfyui_version'] = comfy_client.get_system_stats(server, ensure=False).get('system', {}).get('comfyui_version')
            for r in records:
                r['server_input'] = upload_image(server, r, run_id)
                graph[r['loader_node']]['inputs']['image'] = r['server_input']
            ensure_idle(server)
            comfy_client.write_meta(str(output.with_suffix('.api.json')), graph)
            record['client_id'] = 'agent_moss_' + run_id
            record['status'] = 'submitting'
            comfy_client.write_meta(str(output.with_suffix('.result.json')), record)
            record['prompt_id'] = comfy_client.queue_prompt(server, graph, ensure=False,
                                                          retry_on_connection_error=False, client_id=record['client_id'])
            record['status'] = 'queued'
            comfy_client.write_meta(str(output.with_suffix('.result.json')), record)
            print(f'[moss_image] queued {record["prompt_id"]}; timeout does not cancel the server job', file=sys.stderr, flush=True)
            history = comfy_client.wait_for_history(server, record['prompt_id'], timeout_sec=timeout, poll_interval=0.5)
            comfy_client.write_meta(str(output.with_suffix('.history.json')), history)
            images = history.get('outputs', {}).get('9', {}).get('images', [])
            if not images:
                raise MossImageError('Successful history has no expected SaveImage node 9 output', 1)
            image = images[0]
            comfy_client.download_image(server, image['filename'], image.get('subfolder', ''), image.get('type', 'output'), str(temp))
            with Image.open(temp) as im:
                im.load()
                if im.format != 'PNG' or im.size != (record['width'], record['height']):
                    raise MossImageError('Decoded output is not the requested PNG size', 1)
                record['actual_width'], record['actual_height'] = im.size
            with output.open('wb' if overwrite else 'xb') as target:
                target.write(temp.read_bytes())
            messages = {m[0]: m[1].get('timestamp') for m in history.get('status', {}).get('messages', []) if len(m) > 1 and isinstance(m[1], dict)}
            if messages.get('execution_start') and messages.get('execution_success'):
                record['server_execution_seconds'] = (messages['execution_success'] - messages['execution_start']) / 1000
            record.update(ok=True, status='execution_success', output_path=str(output), server_output=image,
                          output_sha256=hashlib.sha256(output.read_bytes()).hexdigest())
            return record
    except comfy_client.PromptSubmissionUncertainError as exc:
        record.update(status='submission_uncertain', server_job_may_still_be_running=True, error=str(exc))
        raise MossImageError('Submission outcome is uncertain; inspect queue/history using the recorded client_id before retrying', 13) from exc
    except TimeoutError as exc:
        record.update(status='timeout_pending', server_job_may_still_be_running=True, error=str(exc))
        raise MossImageError('Timed out; server job was not cancelled. Inspect recorded prompt_id and queue/history before retrying.', 124) from exc
    except Exception as exc:
        record.update(status='failed', error=str(exc))
        if isinstance(exc, MossImageError):
            raise
        raise MossImageError(str(exc), 10 if isinstance(exc, ConnectionError) else 1) from exc
    finally:
        if record.get('prompt_id') and not output.with_suffix('.history.json').exists():
            try:
                history = api_get(server, '/history/' + record['prompt_id'], 5).get(record['prompt_id'])
                if history:
                    comfy_client.write_meta(str(output.with_suffix('.history.json')), history)
            except MossImageError:
                pass
        record.update(wall_seconds=round(time.monotonic() - start, 3), ended_utc=comfy_client.utc_now_iso())
        comfy_client.write_meta(str(output.with_suffix('.result.json')), record)
        if temp.exists():
            temp.unlink()
        reservation.unlink()
