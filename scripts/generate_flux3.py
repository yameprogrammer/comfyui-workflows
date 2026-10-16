from pathlib import Path
import argparse
import json
import sys

if (Path(__file__).parent/'_bootstrap.py').is_file():
    import _bootstrap
    from lib.flux3_runner import generate, MODES
    WORKFLOWS=Path(_bootstrap.REPO_ROOT)/'workflows'/'agent'/'flux3'
else:
    from flux3_runner import generate, MODES
    WORKFLOWS=Path(__file__).parent/'workflows'/'agent'

def main():
    parser=argparse.ArgumentParser(description='FLUX3 distilled INT8; local production/isolated profiles, full scene captions')
    parser.add_argument('--mode',choices=MODES,default='t2i')
    parser.add_argument('--profile',choices=['flux3-production','flux3-isolated'],default='flux3-production')
    prompts=parser.add_mutually_exclusive_group(required=True)
    prompts.add_argument('-p','--prompt')
    prompts.add_argument('--prompt-file',type=Path)
    parser.add_argument('-i','--image',action='append',default=[])
    parser.add_argument('-o','--output',required=True)
    parser.add_argument('--width',type=int,default=None,help='Default: workflow preset width')
    parser.add_argument('--height',type=int,default=None,help='Default: workflow preset height')
    parser.add_argument('--seed',type=int,default=None,help='Default: workflow preset fixed seed')
    parser.add_argument('--steps',type=int,default=16)
    parser.add_argument('--ref-megapixels',type=float,default=None,help='Default: workflow preset reference resolution')
    parser.add_argument('--server',default=None)
    parser.add_argument('--timeout',type=int,default=1800)
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    prompt=args.prompt_file.read_text(encoding='utf-8-sig') if args.prompt_file else args.prompt
    try:
        server=args.server or ('http://127.0.0.1:8188' if args.profile=='flux3-production' else 'http://127.0.0.1:8193')
        result=generate(workflow_dir=WORKFLOWS,mode=args.mode,prompt=prompt,output=args.output,images=args.image,width=args.width,height=args.height,seed=args.seed,steps=args.steps,ref_megapixels=args.ref_megapixels,server=server,timeout=args.timeout,dry_run=args.dry_run)
    except Exception as exc:
        print(f'{type(exc).__name__}: {exc}',file=sys.stderr)
        return 1
    print(json.dumps(result,ensure_ascii=False))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
