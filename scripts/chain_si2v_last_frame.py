#!/usr/bin/env python3
"""SI2V chain: each shot starts from the previous shot's last video frame.

One-take continuity (hard cuts, no crossfade):
  S_n last frame → keyframes/S_{n+1}.png → episode_s2v S_{n+1}
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import shutil
import subprocess
import sys

from lib.comfy_client import utc_now_iso
from lib.ffmpeg_util import find_ffmpeg, probe_duration, run_ffmpeg
from lib.story_package import StoryPackage

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_FAIL = 30


def extract_last_frame(video: str, png: str) -> dict:
    os.makedirs(os.path.dirname(png) or ".", exist_ok=True)
    # seek near end then take 1 frame — reliable for short clips
    r = run_ffmpeg(
        [
            "-sseof",
            "-0.08",
            "-i",
            video,
            "-frames:v",
            "1",
            "-q:v",
            "2",
            png,
        ],
        timeout_sec=120,
    )
    if r.get("ok") and os.path.isfile(png) and os.path.getsize(png) > 1000:
        return r
    # fallback: full decode last frame via select
    return run_ffmpeg(
        [
            "-i",
            video,
            "-vf",
            "select=eq(n\\,N-1)",
            "-vsync",
            "vfr",
            "-frames:v",
            "1",
            "-q:v",
            "2",
            png,
        ],
        timeout_sec=180,
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Chain SI2V using previous clip last frame")
    p.add_argument("--episode", "-e", required=True)
    p.add_argument(
        "--shots",
        default="S02,S03,S04,S05",
        help="Ordered dialogue chain (first shot uses existing keyframe)",
    )
    p.add_argument(
        "--backend",
        default="ltx23_aio",
        help="SI2V backend (default ltx23_aio; use infinitetalk for hero lips)",
    )
    p.add_argument("--timeout", type=int, default=2400)
    p.add_argument("--start-from", default=None, help="Skip until this shot id (inclusive)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--force-clip-gate",
        action="store_true",
        help=(
            "Allow chaining from previous shot without clip_status=approved "
            "(debug only; Rule 7.2)"
        ),
    )
    p.add_argument(
        "--pause-for-clip-approve",
        action="store_true",
        default=True,
        help=(
            "After each generated clip, stop so you can approve before next shot "
            "(default true). Use --no-pause-for-clip-approve for batch+force."
        ),
    )
    p.add_argument(
        "--no-pause-for-clip-approve",
        action="store_true",
        help="Generate entire chain without stopping (still checks prev clip_status unless --force-clip-gate)",
    )
    args = p.parse_args(argv)
    if args.no_pause_for_clip_approve:
        args.pause_for_clip_approve = False

    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] missing episode {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    chain = [s.strip() for s in args.shots.split(",") if s.strip()]
    if len(chain) < 1:
        print("[ERROR] need at least one shot", file=sys.stderr)
        return EXIT_USAGE

    # Import generate path used by episode_s2v
    from generate_s2v import generate_s2v
    from lib.audio_package import materialize_driving_audio
    from lib.story_package import resolve_work_size

    format_id = story.format_id()
    work_preset = story.doc.get("default_work_preset")
    try:
        width, height, _, _ = resolve_work_size(format_id, work_preset)
    except Exception:
        width, height = 544, 960

    # InfiniteTalk often uses long_edge 832 — match episode_s2v default non-square
    # Keep work size from episode for canvas consistency when possible
    long_edge = 832
    if height >= width:
        scale = long_edge / float(height)
        height = int(round(height * scale / 16) * 16)
        width = int(round(width * scale / 16) * 16)
    else:
        scale = long_edge / float(width)
        width = int(round(width * scale / 16) * 16)
        height = int(round(height * scale / 16) * 16)

    started = args.start_from is None
    prev_clip: str | None = None

    for i, sid in enumerate(chain):
        if not started:
            if sid == args.start_from:
                started = True
            else:
                # still track prev clip if exists
                cand = story.path("clips", "work", f"{sid}_s2v.mp4")
                if os.path.isfile(cand):
                    prev_clip = cand
                continue

        try:
            shot = story.get_shot(sid)
        except KeyError:
            print(f"[ERROR] shot {sid} not in shots.json", file=sys.stderr)
            return EXIT_MISSING

        # Chain keyframe from previous last frame (except first in chain)
        if i > 0 and prev_clip and os.path.isfile(prev_clip):
            prev_sid = chain[i - 1]
            # Rule 7.2: do not propagate a rejected/unreviewed last frame
            if not args.force_clip_gate:
                from lib.episode_status import CLIP_STATUS_OK, normalize_clip_status

                try:
                    prev_shot = story.get_shot(prev_sid)
                except KeyError:
                    prev_shot = {}
                pst = normalize_clip_status(prev_shot, work_ok=True)
                if pst not in CLIP_STATUS_OK:
                    print(
                        f"[ERROR] code=22 CLIP_NOT_APPROVED — cannot chain {prev_sid} → {sid}",
                        file=sys.stderr,
                    )
                    print(
                        f"  prev clip_status={pst or 'pending'!r}. Watch {prev_clip} then:\n"
                        f"    python scripts/shot_approve.py -e {args.episode} "
                        f"-s {prev_sid} --clip approved\n"
                        f"  Resume: python scripts/chain_si2v_last_frame.py -e {args.episode} "
                        f"--start-from {sid} ...\n"
                        f"  Debug-only: --force-clip-gate",
                        file=sys.stderr,
                    )
                    return EXIT_FAIL

            kf_path = story.path("keyframes", f"{sid}.png")
            print(f"\n>>> extract last frame {prev_clip} → {kf_path}")
            if args.dry_run:
                print("  [dry-run] skip extract")
            else:
                r = extract_last_frame(prev_clip, kf_path)
                if not r.get("ok") or not os.path.isfile(kf_path):
                    print(f"[ERROR] last frame extract failed: {r}", file=sys.stderr)
                    return EXIT_FAIL
                story.update_shot(
                    sid,
                    keyframe=f"keyframes/{sid}.png",
                    keyframe_status="approved",
                    continuity={
                        "chain": "last_frame",
                        "from_clip": os.path.relpath(prev_clip, story.root).replace("\\", "/"),
                        "match_from": chain[i - 1],
                    },
                    composed_at=utc_now_iso(),
                )
                print(f"  OK keyframe size={os.path.getsize(kf_path)}")
        else:
            kf_path = story.path(
                *str(shot.get("keyframe") or f"keyframes/{sid}.png").replace("\\", "/").split("/")
            )
            if not os.path.isfile(kf_path):
                print(f"[ERROR] first shot keyframe missing: {kf_path}", file=sys.stderr)
                return EXIT_MISSING
            story.update_shot(sid, keyframe_status="approved")
            print(f"\n>>> first of chain {sid} keyframe={kf_path}")

        # Refresh shot after update
        shot = story.get_shot(sid)
        kf_path = story.path(
            *str(shot.get("keyframe") or f"keyframes/{sid}.png").replace("\\", "/").split("/")
        )
        clip_rel = f"clips/work/{sid}_s2v.mp4"
        clip_path = story.path(*clip_rel.split("/"))
        os.makedirs(os.path.dirname(clip_path), exist_ok=True)

        audio_info = materialize_driving_audio(
            story.root, shot, prepare_mode="auto", force=True
        )
        if not audio_info.get("ok"):
            print(f"[ERROR] audio {sid}: {audio_info}", file=sys.stderr)
            return EXIT_FAIL
        audio_path = audio_info["path"]
        adur = probe_duration(audio_path)
        print(f"  driving={audio_path} dur={adur}")

        motion = (shot.get("motion_prompt") or "").strip()
        if not motion or "speak" not in motion.lower():
            motion = (
                "same person continuing to speak in the same seat and framing, "
                "natural lip sync with dialogue, subtle head motion only, "
                "locked camera, keep identity wardrobe and background fixed, cinematic"
            )

        print(f"  SI2V backend={args.backend} {width}x{height}")
        if args.dry_run:
            print("  [dry-run] skip generate_s2v")
            prev_clip = clip_path if os.path.isfile(clip_path) else prev_clip
            continue

        is_it = args.backend == "infinitetalk"
        is_aio = args.backend == "ltx23_aio"
        # LTX needs dims %32; chain previously used 832 long-edge for IT
        if not is_it:
            from lib.ltx_s2v import snap_ltx_dim

            # prefer shorts work size 544x960 when LTX
            width, height = snap_ltx_dim(544, 32), snap_ltx_dim(960, 32)
        result = generate_s2v(
            kf_path,
            audio_path,
            clip_path,
            backend=args.backend,
            prompt=motion,
            width=width,
            height=height,
            fps=16.0 if is_it else (24.0 if is_aio else 25.0),
            steps=10 if is_it else 20,
            cfg=None,
            audio_scale=1.35 if is_it else 1.5,
            seed=None,
            timeout_sec=args.timeout,
            meta_out=story.path("meta", f"{sid}_s2v.json"),
            dry_run=False,
            speed_lora=True,
            teacache=is_it,
        )
        if not result.get("ok"):
            print(f"[ERROR] s2v {sid}: {result}", file=sys.stderr)
            return EXIT_FAIL

        cdur = probe_duration(clip_path)
        print(f"  OK clip={clip_path} dur={cdur} (audio={adur})")
        if adur and cdur and cdur + 0.05 < adur:
            print(f"  [WARN] clip still shorter than audio by {adur - cdur:.3f}s")

        story.update_shot(
            sid,
            clip_work=clip_rel,
            clip_work_s2v=clip_rel,
            s2v_status="ok",
            s2v_backend=args.backend,
            s2v_driving_audio=os.path.relpath(audio_path, story.root).replace("\\", "/"),
            lip_status="pending",
            clip_status="pending",
            keyframe_status="approved",
        )
        prev_clip = clip_path
        print(
            f"  clip_status=pending — review then:\n"
            f"    python scripts/shot_approve.py -e {args.episode} -s {sid} --clip approved"
        )
        if args.pause_for_clip_approve and i < len(chain) - 1:
            print(
                f"\n[PAUSE] Approve {sid} before chaining next shot "
                f"(Rule 7.2). Then re-run with --start-from {chain[i + 1]}"
            )
            print("Done partial chain through", sid)
            return EXIT_OK

    print("\nDone chain:", " → ".join(chain))
    print(
        "Next: shot_approve --clip each shot (if pending), then hard-cut assemble "
        "(no crossfade) + yuv420p playable export"
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
