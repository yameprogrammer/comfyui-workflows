#!/usr/bin/env python3
"""Assemble episode clips (and optional BGM) into a final mp4 via FFmpeg."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys

from lib.comfy_client import utc_now_iso, write_meta
from lib.ffmpeg_util import concat_videos, find_ffmpeg, mux_bgm
from lib.story_package import StoryPackage, validate_episode_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_NONE = 21
EXIT_FFMPEG = 40


def _clip_path(story: StoryPackage, shot: dict, stage: str) -> str | None:
    """Resolve best clip path for stage: deliver | work | auto."""
    sid = shot.get("shot_id")
    deliver_rel = shot.get("clip_deliver") or f"clips/deliver/{sid}.mp4"
    work_rel = shot.get("clip_work") or f"clips/work/{sid}.mp4"
    deliver = story.path(*deliver_rel.replace("\\", "/").split("/"))
    work = story.path(*work_rel.replace("\\", "/").split("/"))

    if stage == "deliver":
        return deliver if os.path.isfile(deliver) else None
    if stage == "work":
        return work if os.path.isfile(work) else None
    # auto: prefer deliver
    if os.path.isfile(deliver):
        return deliver
    if os.path.isfile(work):
        return work
    return None


def _default_bgm(story: StoryPackage) -> str | None:
    music_dir = story.path("audio", "music")
    if not os.path.isdir(music_dir):
        return None
    for name in sorted(os.listdir(music_dir)):
        low = name.lower()
        if low.endswith((".mp3", ".wav", ".m4a", ".aac", ".flac")):
            return os.path.join(music_dir, name)
    return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="FFmpeg-assemble episode clips into exports/final/"
    )
    parser.add_argument("--episode", "-e", required=True)
    parser.add_argument(
        "--shots",
        default="all",
        help="all | S01,S02,... (order follows shots.json order)",
    )
    parser.add_argument(
        "--stage",
        choices=["auto", "deliver", "work"],
        default="auto",
        help="Which clips to use (auto prefers deliver)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output mp4 (default stories/<ep>/exports/final/<ep>_final.mp4)",
    )
    parser.add_argument(
        "--bgm",
        default=None,
        help="Background music path (default: first file in audio/music/)",
    )
    parser.add_argument("--no-bgm", action="store_true", help="Video only, no BGM mux")
    parser.add_argument(
        "--bgm-volume",
        type=float,
        default=0.35,
        help="BGM volume multiplier (default 0.35)",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Try stream copy concat (faster; may fail if codecs differ)",
    )
    parser.add_argument("--fps", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--meta-out", default=None)
    args = parser.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] code=2 invalid episode id", file=sys.stderr)
        return EXIT_USAGE

    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] code=11 episode missing: {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    try:
        ff = find_ffmpeg()
    except FileNotFoundError as e:
        print(f"[ERROR] code=40 {e}", file=sys.stderr)
        return EXIT_FFMPEG

    all_shots = sorted(story.shots(), key=lambda s: s.get("order", 0))
    if args.shots in ("all", "*"):
        selected = all_shots
    else:
        want = {x.strip() for x in args.shots.split(",") if x.strip()}
        selected = [s for s in all_shots if s.get("shot_id") in want]
        missing = want - {s.get("shot_id") for s in selected}
        if missing:
            print(f"[ERROR] code=2 unknown shots: {sorted(missing)}", file=sys.stderr)
            return EXIT_USAGE

    clips: list[tuple[str, str]] = []  # (shot_id, path)
    for s in selected:
        path = _clip_path(story, s, args.stage)
        if path:
            clips.append((s.get("shot_id") or "?", path))
        else:
            print(f"[WARN] skip {s.get('shot_id')}: no {args.stage} clip")

    if not clips:
        print("[ERROR] code=21 no clips to assemble", file=sys.stderr)
        return EXIT_NONE

    out = args.output or story.path(
        "exports", "final", f"{args.episode}_final.mp4"
    )
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)

    bgm = None
    if not args.no_bgm:
        bgm = args.bgm or _default_bgm(story)

    print(f"assemble_video episode={args.episode} stage={args.stage}")
    print(f"  ffmpeg={ff}")
    print(f"  clips={len(clips)}")
    for sid, p in clips:
        print(f"    {sid}: {p}")
    print(f"  out={out}")
    print(f"  bgm={bgm or '(none)'}")

    if args.dry_run:
        print("[dry-run] skip ffmpeg")
        return EXIT_OK

    # Intermediate video without BGM if mux needed
    if bgm:
        import tempfile

        fd, tmp_video = tempfile.mkstemp(suffix=".mp4", prefix="assemble_vid_")
        os.close(fd)
        try:
            r1 = concat_videos(
                [p for _, p in clips],
                tmp_video,
                reencode=not args.copy,
                fps=args.fps,
                timeout_sec=args.timeout,
            )
            if not r1.get("ok"):
                print(f"[ERROR] concat {r1.get('error')}: {r1.get('message')}", file=sys.stderr)
                return EXIT_FFMPEG
            r2 = mux_bgm(
                tmp_video,
                bgm,
                out,
                audio_volume=args.bgm_volume,
                timeout_sec=args.timeout,
            )
            if not r2.get("ok"):
                print(f"[ERROR] bgm {r2.get('error')}: {r2.get('message')}", file=sys.stderr)
                return EXIT_FFMPEG
        finally:
            try:
                os.remove(tmp_video)
            except OSError:
                pass
    else:
        r1 = concat_videos(
            [p for _, p in clips],
            out,
            reencode=not args.copy,
            fps=args.fps,
            timeout_sec=args.timeout,
        )
        if not r1.get("ok"):
            print(f"[ERROR] concat {r1.get('error')}: {r1.get('message')}", file=sys.stderr)
            return EXIT_FFMPEG

    meta = {
        "mode": "assemble_video",
        "episode_id": args.episode,
        "stage": args.stage,
        "clips": [{"shot_id": sid, "path": os.path.abspath(p)} for sid, p in clips],
        "bgm": os.path.abspath(bgm) if bgm else None,
        "bgm_volume": args.bgm_volume if bgm else None,
        "output_path": os.path.abspath(out),
        "reencode": not args.copy,
        "created_at": utc_now_iso(),
    }
    meta_path = args.meta_out or story.path("meta", f"{args.episode}_assemble.json")
    write_meta(meta_path, meta)

    # stamp episode doc lightly
    story.doc["final_export"] = {
        "path": os.path.relpath(out, story.root).replace("\\", "/"),
        "assembled_at": utc_now_iso(),
        "clip_count": len(clips),
    }
    story.save()

    print(f"OK final={out}")
    print(f"  meta={meta_path}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
