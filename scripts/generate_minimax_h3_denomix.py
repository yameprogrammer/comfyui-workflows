"""DenoMix H3 R2V 8+2. Default5s; maximum requested10s (243frames/10.125s).

python scripts/generate_minimax_h3_denomix.py --status
python scripts/generate_minimax_h3_denomix.py -i reference.png --prompt-file prompt.txt -o F:/my_project/clip.mp4 --duration 5
Guide: workflows/human/minimax_h3_denomix/AGENT_GUIDE.md
"""
import argparse
import json
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
from lib.minimax_h3_denomix_runner import generate, model_status


def main(argv=None):
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--status', action='store_true', help='Read-only existing local server; no auto-start or install')
    p.add_argument('--job-id', help='Inspect one previous prompt with --status')
    p.add_argument('-i', '--image', '--ref-image', action='append', default=[], dest='images')
    text = p.add_mutually_exclusive_group()
    text.add_argument('-p', '--prompt')
    text.add_argument('--prompt-file', type=Path)
    p.add_argument('-o', '--output')
    p.add_argument('--duration', type=float, default=5.0, help='Requested seconds:0<value<=10; default5')
    p.add_argument('--seed', type=int)
    p.add_argument('--server', default='127.0.0.1:8188')
    p.add_argument('--timeout', type=float, default=900)
    p.add_argument('--dry-run', action='store_true', help='Offline graph+metadata only; no server or image staging')
    a = p.parse_args(argv)
    try:
        if a.status:
            if a.images or a.prompt or a.prompt_file or a.output or a.dry_run or a.seed is not None or a.duration != 5.0:
                p.error('--status cannot be combined with generation inputs')
            result = model_status(a.server, a.job_id)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result['available'] else 1
        if a.job_id:
            p.error('--job-id requires --status')
        if not a.output or not (a.prompt or a.prompt_file):
            p.error('output and prompt/prompt-file are required')
        prompt = a.prompt_file.read_text(encoding='utf-8-sig') if a.prompt_file else a.prompt
        result = generate(prompt=prompt, images=a.images, output_path=a.output, duration=a.duration,
                          seed=a.seed, server=a.server, timeout=a.timeout, dry_run=a.dry_run)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        print(json.dumps({'tool': 'minimax_h3_denomix', 'status': 'error', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
