"""LTX-2.5 official-derived INT8 T2A / audio-conditioned A2V.

Example: python scripts/generate_ltx25_official.py --task a2v -a input.wav -p "A stream flows over rocks; static camera." -o D:/project/a2v.mp4
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bootstrap
import argparse
import hashlib
import json
import shutil
import time
import urllib.request

from lib.comfy_client import DEFAULT_SERVER, free_comfy_memory, get_comfy_input_dir, get_comfy_output_dir, queue_prompt, wait_for_history
from lib.ltx25_contract import find_completed_media
from lib.ltx25_official import build_task, build_ingredients


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=["t2a", "a2v", "ingredients"], required=True)
    parser.add_argument("-p", "--prompt", required=True)
    parser.add_argument("-a", "--audio")
    parser.add_argument("-i", "--image")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=None)
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--export-api", action="store_true", help="Write API envelope to --output without server mutation")
    parser.add_argument("--adapter-strength", type=float, default=1.0, help="Ingredients only; official default1; community1.4 is experimental")
    parser.add_argument("--sampler", choices=["euler_ancestral", "euler_ancestral_cfg_pp"], default="euler_ancestral", help="Ingredients only")
    args = parser.parse_args()
    ingredients = args.task == "ingredients"
    if args.seconds is None: args.seconds = 5.0 if ingredients else 2.0
    if args.width is None: args.width = 768 if ingredients else 384
    if args.height is None: args.height = 448 if ingredients else 256
    if not 0.0 < args.adapter_strength <= 2.0: parser.error("adapter-strength must be >0 and <=2")
    if not ingredients and (args.adapter_strength != 1.0 or args.sampler != "euler_ancestral"): parser.error("Adapter/sampler controls apply only to Ingredients")
    if args.output.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        parser.error("Output must be outside toolbox")
    names = {}
    for role, value in [("audio", args.audio), ("image", args.image)]:
        if not value:
            continue
        path = Path(value)
        if not path.is_file():
            parser.error(f"Missing {role}: {path}")
        name = "ltx25_" + hashlib.sha256(path.read_bytes()).hexdigest()[:12] + path.suffix.lower()
        names[role] = name
        if not args.export_api:
            target = Path(get_comfy_input_dir(server_address=args.server)) / name
            if not target.exists():
                shutil.copy2(path, target)
    builder = build_ingredients if args.task == "ingredients" else build_task
    task_args = {"adapter_strength": args.adapter_strength, "sampler_name": args.sampler} if args.task == "ingredients" else {"task": args.task, "audio_name": names.get("audio")}
    api, meta = builder(**task_args, prompt=args.prompt, seconds=args.seconds, width=args.width, height=args.height,
                       seed=args.seed, image_name=names.get("image"), prefix="ltx25_" + args.task)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    envelope = {"prompt": api, "metadata": meta}
    if args.export_api:
        args.output.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
        print("EXPORTED, NOT EXECUTED", args.output)
        return 0
    with urllib.request.urlopen(f"http://{args.server}/queue", timeout=10) as response:
        queue = json.load(response)
    if queue.get("queue_running") or queue.get("queue_pending"):
        raise RuntimeError("Shared server queue is busy; wait for resource coordination")
    args.output.with_suffix(args.output.suffix + ".api.json").write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    free_comfy_memory(server_address=args.server, unload_models=True, free_memory=True)
    started = time.time()
    pid = queue_prompt(args.server, api)
    print("Prompt ID:", pid, flush=True)
    history = wait_for_history(args.server, pid, timeout_sec=1800)
    source = find_completed_media(history, get_comfy_output_dir(server_address=args.server), audio_only=args.task == "t2a")
    shutil.copy2(source, args.output)
    evidence = {"prompt_id": pid, "metadata": meta, "status": history["status"], "elapsed_sec": time.time()-started,
                "execution": "completed", "quality_review": "not_run", "output": str(args.output.resolve())}
    args.output.with_suffix(args.output.suffix + ".history.json").write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output.with_suffix(args.output.suffix + ".run.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print("RENDER COMPLETE; QA REQUIRED", args.output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, RuntimeError, TimeoutError) as error:
        print("ERROR:", error, file=sys.stderr)
        raise SystemExit(1)
