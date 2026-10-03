"""Preferred memory-managed H3 T2V/I2V/FLF/R2V/V2V/AI2V tool.

  python scripts/generate_minimax_h3_optimized.py --task r2v -i hero.png --aspect 9:16 --prompt-file prompt.txt -o F:/my_project/clip.mp4
  python scripts/generate_minimax_h3_optimized.py --task v2v --ref-video plate.mp4 -p "Use <Video 1> as the reference" -o F:/my_project/clip.mp4
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bootstrap  # noqa: E402,F401
from lib.minimax_h3_optimized_runner import PROFILES, TASKS, generate


def main(argv=None):
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', choices=TASKS, default='r2v')
    parser.add_argument('-i', '--image', '--ref-image', action='append', dest='images')
    parser.add_argument('--last', '--last-frame', dest='last')
    parser.add_argument('--ref-video')
    parser.add_argument('-a', '--audio')
    text = parser.add_mutually_exclusive_group()
    text.add_argument('-p', '--prompt')
    text.add_argument('--prompt-file')
    parser.add_argument('-o', '--output')
    parser.add_argument('--profile', choices=PROFILES, default='work')
    parser.add_argument('--aspect', choices=['16:9', '9:16'], default='16:9')
    parser.add_argument('--width', type=int, help='First-pass pixels; output width is x2')
    parser.add_argument('--height', type=int, help='First-pass pixels; output height is x2')
    parser.add_argument('--duration', type=float, default=5.0)
    parser.add_argument('--seed', type=int)
    parser.add_argument('--attention', choices=['dense', 'sol'], default='dense')
    parser.add_argument('--ref-image-size', choices=['match', 'max'], default='match')
    parser.add_argument('--audio-start', type=float, default=0.0)
    parser.add_argument('--server', default='127.0.0.1:8188')
    parser.add_argument('--timeout', type=float, default=900.0)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--list-profiles', action='store_true')
    args = parser.parse_args(argv)
    if args.list_profiles:
        for name, (w, h) in PROFILES.items():
            print(f'{name}: {w}x{h} -> {w*2}x{h*2}; --aspect 9:16 swaps axes; default 5s')
        return 0
    if not args.output or not (args.prompt or args.prompt_file):
        parser.error('output and prompt or prompt-file are required')
    if args.last and args.task != 'flf':
        parser.error('--last is only used by --task flf')
    images = list(args.images or [])
    if args.last:
        images.append(args.last)
    try:
        prompt = Path(args.prompt_file).read_text(encoding='utf-8-sig').strip() if args.prompt_file else args.prompt.strip()
        if args.duration > 8:
            print('Note: clips longer than 8s need separate memory and quality validation.', file=sys.stderr)
        result = generate(task=args.task, prompt=prompt, images=images, video=args.ref_video, audio=args.audio,
                          output_path=args.output, profile=args.profile, aspect=args.aspect,
                          width=args.width, height=args.height, duration=args.duration, seed=args.seed,
                          attention=args.attention, ref_image_size=args.ref_image_size, audio_start=args.audio_start,
                          server=args.server, timeout=args.timeout, dry_run=args.dry_run)
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
