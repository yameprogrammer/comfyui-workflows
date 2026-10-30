"""Local MOSS transcription/diarization in its isolated Python 3.12 environment.

Example: python scripts/transcribe_moss.py -i F:/my_project/speech.wav -o F:/my_project/moss_take01
"""
from pathlib import Path
import argparse
import os
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-i', '--input', required=True, type=Path)
    parser.add_argument('-o', '--output', required=True, type=Path, help='New or empty directory in caller project')
    parser.add_argument('--max-new-tokens', type=int, default=4096)
    parser.add_argument('--prompt', help='Complete transcription/speaker/timestamp instruction')
    args = parser.parse_args()
    root = Path(os.environ.get('MOSS_TRANSCRIBE_ROOT', 'F:/MOSS-Transcribe-Diarize')).expanduser().resolve()
    python = root/'.venv/Scripts/python.exe'
    worker = root/'moss_worker.py'
    if not python.is_file() or not worker.is_file():
        parser.error('MOSS installation missing; see workflows/human/moss_transcribe/AGENT_GUIDE.md')
    cmd = [str(python), '-s', str(worker), '-i', str(args.input.expanduser().resolve()), '-o', str(args.output.expanduser().resolve()), '--max-new-tokens', str(args.max_new_tokens)]
    if args.prompt:
        cmd += ['--prompt',args.prompt]
    env = os.environ.copy()
    env.pop('PYTHONPATH',None)
    env['PYTHONNOUSERSITE']='1'
    env['PYTHONUTF8']='1'
    env['AGENT_MEDIA_TOOLS_ROOT']=str(Path(__file__).resolve().parents[1])
    return subprocess.call(cmd,env=env,cwd=root)

if __name__=='__main__':
    raise SystemExit(main())
