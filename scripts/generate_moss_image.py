#!/usr/bin/env python3
"""Native local MOSS-Image: T2I, pixel-box Layout, Edit and Color/Depth Control.

python scripts/generate_moss_image.py --status
python scripts/generate_moss_image.py --mode t2i -p "Studio photograph of a blue teapot." -o F:/my_project/moss.png
Guide: workflows/human/moss_image/AGENT_GUIDE.md
"""
from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import sys
from pathlib import Path

from lib.moss_image_runner import MODES, MossImageError, generate, model_status


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--mode', choices=MODES, default='t2i')
    parser.add_argument('--status', action='store_true', help='Read-only node/model availability for all seven modes; no start/install')
    prompts = parser.add_mutually_exclusive_group()
    prompts.add_argument('-p', '--prompt')
    prompts.add_argument('--prompt-file', type=Path)
    parser.add_argument('--negative', default=None, help='Override preset negative prompt; empty string clears it')
    parser.add_argument('-i', '--image', action='append', type=Path, default=[], help='Edit source; repeat 2-4 times for multi-edit')
    parser.add_argument('--layout', type=Path, help='Pixel-box JSON; see workflows/human/moss_image/layout_example.json')
    parser.add_argument('--color-map', type=Path)
    parser.add_argument('--depth-map', type=Path)
    parser.add_argument('-o', '--output', type=Path, help='Project PNG outside this toolbox; existing PNG/sidecars are refused')
    parser.add_argument('--width', type=int)
    parser.add_argument('--height', type=int)
    parser.add_argument('--seed', type=int)
    parser.add_argument('--steps', type=int)
    parser.add_argument('--cfg', type=float)
    parser.add_argument('--reference-max-edge', type=int, default=None, help='Edit references only; default 512, aligned to 16, aspect preserved')
    parser.add_argument('--lora-strength', type=float, default=None, help='Edit/Control only; default 1')
    parser.add_argument('--control-strength', type=float, default=None, help='Control modes only; default 1')
    parser.add_argument('--control-end', type=float, default=None, help='Control modes only; default 0.5 for synthetic maps')
    parser.add_argument('--server', default='127.0.0.1:8188', help='Local HTTP only; no authentication or remote upload')
    parser.add_argument('--timeout', type=float, default=1800)
    parser.add_argument('--dry-run', action='store_true', help='Offline validation and API/result sidecars; no network/upload/generation')
    parser.add_argument('--overwrite', action='store_true', help='Explicitly replace the requested output and its sidecars')
    args = parser.parse_args(argv)
    try:
        if args.status:
            generation_values = [args.prompt, args.prompt_file, args.negative, args.image, args.layout,
                                 args.color_map, args.depth_map, args.output, args.width, args.height,
                                 args.seed, args.steps, args.cfg, args.reference_max_edge, args.lora_strength,
                                 args.control_strength, args.control_end, args.dry_run, args.overwrite]
            if any(value is not None and value is not False and value != [] for value in generation_values):
                raise MossImageError('--status cannot be combined with generation inputs', 2)
            result = model_status(args.server)
            print(json.dumps(result, ensure_ascii=False))
            return 0 if result['available_modes'][args.mode] else 11
        if not args.output:
            raise MossImageError('-o/--output is required for generation and dry-run', 2)
        prompt = args.prompt_file.read_text(encoding='utf-8-sig') if args.prompt_file else args.prompt
        result = generate(mode=args.mode, prompt=prompt, negative=args.negative, output=args.output,
                          images=args.image, layout=args.layout, color_map=args.color_map, depth_map=args.depth_map,
                          width=args.width, height=args.height, seed=args.seed, steps=args.steps, cfg=args.cfg,
                          reference_max_edge=args.reference_max_edge, lora_strength=args.lora_strength,
                          control_strength=args.control_strength, control_end=args.control_end,
                          server=args.server, timeout=args.timeout, dry_run=args.dry_run, overwrite=args.overwrite)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (MossImageError, ValueError, OSError) as exc:
        code = getattr(exc, 'exit_code', 2)
        print(json.dumps({'ok': False, 'tool': 'generate_moss_image', 'error': str(exc), 'exit_code': code}, ensure_ascii=False))
        print(f'[moss_image] {exc}', file=sys.stderr)
        return code


if __name__ == '__main__':
    raise SystemExit(main())
