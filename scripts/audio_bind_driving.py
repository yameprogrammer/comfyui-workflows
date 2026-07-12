#!/usr/bin/env python3
"""
Bind music-master (or any) audio to a shot as SI2V driving.

Typical music_video vocal cut:
  slice master [t0,t1) → prepare center_voicey → set motion_driver=si2v + audio_refs.driving
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.ffmpeg_util import DRIVING_PREP_MODES, prepare_driving_audio, slice_audio
from lib.story_package import StoryPackage, validate_episode_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_FAIL = 30


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Slice/prepare audio and bind as shot SI2V driving (music_video vocal / dialogue)"
    )
    p.add_argument("--episode", "-e", required=True)
    p.add_argument("--shot", "-s", required=True, help="Shot id e.g. S02")
    p.add_argument(
        "--input",
        "-i",
        default=None,
        help="Source audio (default: episode audio.master / masters first file)",
    )
    p.add_argument("--start", type=float, default=0.0, help="Slice start sec on source")
    p.add_argument("--end", type=float, default=None, help="Slice end sec (exclusive)")
    p.add_argument("--duration", type=float, default=None, help="Slice duration (alt to --end)")
    p.add_argument(
        "--prepare-mode",
        "-m",
        default="center_voicey",
        choices=list(DRIVING_PREP_MODES),
        help="Driving prep (default center_voicey; use copy for clean VO)",
    )
    p.add_argument(
        "--role",
        default="vocal",
        help="audio_refs.driving.role tag (vocal|dialogue|…)",
    )
    p.add_argument(
        "--no-set-si2v",
        action="store_true",
        help="Do not force motion_driver=si2v (only bind audio_refs)",
    )
    p.add_argument(
        "--motion",
        default=None,
        help="Optional motion_prompt override for singing/speech",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan only",
    )
    args = p.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] bad episode id", file=sys.stderr)
        return EXIT_USAGE
    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] episode missing: {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    try:
        shot = story.get_shot(args.shot)
    except KeyError:
        print(f"[ERROR] unknown shot {args.shot}", file=sys.stderr)
        return EXIT_USAGE

    src = args.input
    if not src:
        from lib.audio_package import find_master_music

        src = find_master_music(story.root, story.doc)
    if not src or not os.path.isfile(src):
        print(
            "[ERROR] no source audio; pass --input or set audio.master / masters/",
            file=sys.stderr,
        )
        return EXIT_USAGE

    if args.end is None and args.duration is None:
        # full file
        end = None
        start = float(args.start or 0.0)
        need_slice = start > 0.001
    else:
        start = float(args.start or 0.0)
        if args.end is not None:
            end = float(args.end)
        else:
            end = start + float(args.duration)
        need_slice = True

    sid = args.shot
    out_dir = story.path("audio", "exports", "s2v_drive")
    os.makedirs(out_dir, exist_ok=True)
    raw_name = f"{sid}_slice_raw.wav"
    prep_name = f"{sid}_drive_{args.prepare_mode}.wav"
    raw_path = os.path.join(out_dir, raw_name)
    drive_path = os.path.join(out_dir, prep_name)

    print(f"audio_bind_driving episode={args.episode} shot={sid}")
    print(f"  source={src}")
    print(f"  slice start={start} end={end} prepare={args.prepare_mode}")
    print(f"  out={drive_path}")

    if args.dry_run:
        print("  [dry-run] skip write/bind")
        return EXIT_OK

    work_src = src
    if need_slice:
        if end is None:
            # start-only: remaining duration via probe
            import json
            import subprocess

            try:
                out = subprocess.check_output(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-show_entries",
                        "format=duration",
                        "-of",
                        "json",
                        src,
                    ],
                    text=True,
                    timeout=30,
                )
                dur = float(json.loads(out)["format"]["duration"])
            except Exception as e:
                print(f"[ERROR] probe failed: {e}", file=sys.stderr)
                return EXIT_FAIL
            sr = slice_audio(src, raw_path, start_sec=start, duration_sec=max(0.05, dur - start))
        else:
            sr = slice_audio(src, raw_path, start_sec=start, end_sec=end)
        if not sr.get("ok"):
            print(f"[ERROR] slice {sr.get('error')}: {sr.get('message')}", file=sys.stderr)
            return EXIT_FAIL
        work_src = raw_path
        print(f"  sliced → {raw_path}")

    pr = prepare_driving_audio(work_src, drive_path, mode=args.prepare_mode)
    if not pr.get("ok"):
        print(f"[ERROR] prepare {pr.get('error')}: {pr.get('message')}", file=sys.stderr)
        return EXIT_FAIL
    print(f"  prepared → {drive_path}")

    rel = os.path.relpath(drive_path, story.root).replace("\\", "/")
    refs = dict(shot.get("audio_refs") or {}) if isinstance(shot.get("audio_refs"), dict) else {}
    refs["driving"] = {
        "path": rel,
        "start_sec": 0,
        "end_sec": None,
        "at_sec": 0,
        "role": args.role,
    }

    fields: dict = {"audio_refs": refs}
    if not args.no_set_si2v:
        fields["motion_driver"] = "si2v"
    if args.motion:
        fields["motion_prompt"] = args.motion
    # duration from slice if known
    if need_slice and end is not None:
        fields["duration_sec"] = max(0.1, float(end) - float(start))

    story.update_shot(sid, **fields)
    print(f"OK bound {sid} driving={rel} motion_driver={fields.get('motion_driver', shot.get('motion_driver'))}")
    print(f"  next: python scripts/episode_s2v.py -e {args.episode} --shots {sid}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
