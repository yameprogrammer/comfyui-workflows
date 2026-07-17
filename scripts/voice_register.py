#!/usr/bin/env python3
"""
Register a voice sample for Qwen3-TTS clone mode (you or talent).

Stores under voices/<id>/:
  ref.wav (or original ext)
  voice.json  { id, display, ref_audio, ref_text, language, notes }

Usage:
  python scripts/voice_register.py --id my_voice_v1 --name "Me" \\
    --ref path/to/clean_8s.wav \\
    --ref-text "레퍼런스에서 말한 문장을 그대로" \\
    --language Korean

  python scripts/generate_qwen3_tts.py --voice-id my_voice_v1 \\
    --text "이제 이 목소리로 새 대사를 읽습니다." \\
    -o out.mp3
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import re
import shutil
import sys

from lib.comfy_client import utc_now_iso

VOICES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "voices"
)
ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")

EXIT_OK = 0
EXIT_USAGE = 2


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Register voice sample for TTS clone")
    p.add_argument("--id", default=None, help="voice_id snake_case")
    p.add_argument("--name", default=None, help="Display name")
    p.add_argument(
        "--ref",
        default=None,
        help="Reference wav/mp3 (ideal 5–15s, max ~30s for clone)",
    )
    p.add_argument(
        "--ref-text",
        default="",
        help="Exact transcript of the reference audio (strongly recommended)",
    )
    p.add_argument("--language", default="Korean")
    p.add_argument(
        "--instruct",
        default="",
        help="Optional default emotion instruct when generating",
    )
    p.add_argument("--notes", default="")
    p.add_argument("--force", action="store_true")
    p.add_argument("--list", action="store_true", help="List registered voices")
    args = p.parse_args(argv)

    if args.list:
        if not os.path.isdir(VOICES_DIR):
            print("(no voices/ yet)")
            return EXIT_OK
        for name in sorted(os.listdir(VOICES_DIR)):
            vj = os.path.join(VOICES_DIR, name, "voice.json")
            if os.path.isfile(vj):
                with open(vj, "r", encoding="utf-8") as f:
                    d = json.load(f)
                print(f"  {name}: {d.get('display_name')} ref={d.get('ref_audio')}")
        return EXIT_OK

    if not args.id or not args.ref:
        print("[ERROR] --id and --ref required (or pass --list)", file=sys.stderr)
        return EXIT_USAGE
    if not ID_RE.match(args.id):
        print("[ERROR] bad voice id", file=sys.stderr)
        return EXIT_USAGE
    if not os.path.isfile(args.ref):
        print(f"[ERROR] ref missing: {args.ref}", file=sys.stderr)
        return EXIT_USAGE

    # Duration guard (same policy as generate_qwen3_tts clone)
    try:
        from generate_qwen3_tts import validate_ref_audio, REF_MAX_SECONDS

        chk = validate_ref_audio(args.ref, max_sec=REF_MAX_SECONDS)
        for w in chk.get("warnings") or []:
            print(f"[WARN] {w}")
        if not chk.get("ok"):
            print(f"[ERROR] {chk.get('error')}", file=sys.stderr)
            print("  Trim ref to ≤30s (ideal 5–15s) then re-register.", file=sys.stderr)
            return EXIT_USAGE
        if chk.get("duration_sec") is not None:
            print(f"  ref_duration_sec={chk['duration_sec']:.1f}")
    except Exception as e:
        print(f"[WARN] duration probe skipped: {e}")

    dest = os.path.join(VOICES_DIR, args.id)
    if os.path.isdir(dest) and not args.force:
        print(f"[ERROR] exists: {dest} (use --force)", file=sys.stderr)
        return EXIT_USAGE
    os.makedirs(dest, exist_ok=True)

    ext = os.path.splitext(args.ref)[1].lower() or ".wav"
    if ext not in (".wav", ".mp3", ".flac", ".ogg", ".m4a"):
        print(f"[WARN] unusual audio ext {ext}")
    ref_name = f"ref{ext}"
    shutil.copy2(args.ref, os.path.join(dest, ref_name))

    doc = {
        "id": args.id,
        "display_name": args.name or args.id,
        "ref_audio": ref_name,
        "ref_text": (args.ref_text or "").strip(),
        "language": args.language,
        "default_instruct": (args.instruct or "").strip(),
        "notes": args.notes,
        "engine": "qwen3_tts_clone",
        "created_at": utc_now_iso(),
        "tips": [
            "Use 5–15 seconds of clean solo speech",
            "ref_text should match the reference audio exactly",
            "Avoid music bed / heavy reverb on the sample",
        ],
    }
    with open(os.path.join(dest, "voice.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"OK voice={args.id}")
    print(f"  path={dest}")
    print(f"  ref_text_set={bool(doc['ref_text'])}")
    print(
        f"  next: python scripts/generate_qwen3_tts.py --voice-id {args.id} "
        f"--text \"...\" -o out.mp3"
    )
    if not doc["ref_text"]:
        print(
            "  [tip] add --ref-text for much better clone quality",
            file=sys.stderr,
        )
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
