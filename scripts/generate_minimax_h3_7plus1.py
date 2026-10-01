"""Singularity H3 R2V: 7 low-resolution steps + x2 latent upscale + 1 refine.

Run from the toolbox root, with outputs in your project:
  python scripts/generate_minimax_h3_7plus1.py -i hero.png --prompt-file prompt.txt -o F:/my_project/clips/shot.mp4
  python scripts/generate_minimax_h3_7plus1.py -i hero.png --prompt-file prompt.txt --profile 1080 -o F:/my_project/clips/hero.mp4
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Portable embedded Python does not add the script directory to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bootstrap  # noqa: E402,F401

from lib.minimax_h3_7plus1_runner import PROFILES, generate


def main(argv=None) -> int:
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-i', '--image', '--ref-image', action='append', dest='images', help='Ordered R2V reference; repeat for <Picture 1>, <Picture 2>, ...')
    prompt = parser.add_mutually_exclusive_group()
    prompt.add_argument('-p', '--prompt')
    prompt.add_argument('--prompt-file')
    parser.add_argument('-o', '--output', help='Caller project MP4 path, outside the toolbox')
    parser.add_argument('--profile', choices=PROFILES, default='work')
    parser.add_argument('--attention', choices=['dense', 'sol'], default='dense', help='Sol applies only to the last high-resolution step')
    parser.add_argument('--duration', type=float, default=5.0, help='Requested seconds; native 17k+5 frame grid at 24fps')
    parser.add_argument('--seed', type=int)
    parser.add_argument('--ref-image-size', choices=['match', 'max'], default='match')
    parser.add_argument('--server', default='127.0.0.1:8188')
    parser.add_argument('--timeout', type=float, default=900)
    parser.add_argument('--dry-run', action='store_true', help='Write patched API JSON in the project without staging images or calling Comfy')
    parser.add_argument('--list-profiles', action='store_true')
    args = parser.parse_args(argv)
    if args.list_profiles:
        for name, (width, height) in PROFILES.items():
            print(f'{name}: {width}x{height} -> {width*2}x{height*2}; 7+1 steps; default 5s; dense attention')
        return 0
    if not args.images or not args.output or not (args.prompt or args.prompt_file):
        parser.error('reference image, prompt or prompt-file, and output are required')
    text = Path(args.prompt_file).read_text(encoding='utf-8-sig').strip() if args.prompt_file else args.prompt.strip()
    if not text:
        parser.error('prompt must not be empty')
    if args.duration > 5:
        print('Note: this preset was measured at 5s; longer clips require separate quality and memory review.', file=sys.stderr)
    try:
        result = generate(prompt=text, images=args.images, output_path=args.output,
                          profile=args.profile, attention=args.attention, duration=args.duration,
                          seed=args.seed, ref_image_size=args.ref_image_size, server=args.server,
                          timeout=args.timeout, dry_run=args.dry_run)
    except (OSError, ValueError, RuntimeError, TimeoutError) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
