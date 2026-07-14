#!/usr/bin/env python3
"""Full-episode one-take chain: each shot starts from the previous clip's last frame.

Supports mixed motion drivers in shot order (i2v + si2v).
  S_n last frame → keyframes/S_{n+1}.png → generate I2V or SI2V

Rule 7.2: previous clip_status=approved required (use --force-clip-gate only for debug).

Example:
  python scripts/chain_one_take.py -e cafe_gomin_ep01 --backend-s2v infinitetalk \\
    --prepare-mode center_voicey --no-pause
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import math
import os
import sys

from lib.comfy_client import utc_now_iso
from lib.ffmpeg_util import probe_duration
from lib.one_take import check_prev_clip_gate, keyframe_from_prev_clip, work_clip_path
from lib.story_package import StoryPackage, resolve_work_size

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_CLIP_GATE = 22
EXIT_FAIL = 30


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="One-take chain all shots (i2v+si2v)")
    p.add_argument("--episode", "-e", required=True)
    p.add_argument("--shots", default=None, help="Comma list (default: all shots in order)")
    p.add_argument("--backend-s2v", default="infinitetalk")
    p.add_argument("--backend-i2v", default="wan22")
    p.add_argument("--prepare-mode", default="center_voicey")
    p.add_argument("--fps", type=float, default=24.0)
    p.add_argument(
        "--audio-scale",
        type=float,
        default=None,
        help="Override SI2V audio_scale (default: performance profile)",
    )
    p.add_argument("--s2v-steps", type=int, default=12)
    p.add_argument("--timeout", type=int, default=2400)
    p.add_argument("--start-from", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--performance",
        default=None,
        help="Default performance profile for SI2V shots (or per-shot.performance)",
    )
    p.add_argument(
        "--force-clip-gate",
        action="store_true",
        help="Allow chain without prev clip_status=approved (debug only)",
    )
    p.add_argument(
        "--no-pause",
        action="store_true",
        help="Do not pause after each shot for approve",
    )
    p.add_argument(
        "--keep-first-clip",
        action="store_true",
        help="If first shot work clip exists, do not regenerate it",
    )
    from lib.workspace_export import add_export_workspace_args

    add_export_workspace_args(p)
    args = p.parse_args(argv)

    os.environ.setdefault("AGENT_IT_MAX_FRAMES", "257")
    os.environ.setdefault("AGENT_S2V_TAIL_SEC", "0.25")

    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] missing episode {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    shots = sorted(story.shots(), key=lambda s: s.get("order", 0))
    if args.shots:
        order = [x.strip() for x in args.shots.split(",") if x.strip()]
        by_id = {s.get("shot_id"): s for s in shots}
        chain = [by_id[i] for i in order if i in by_id]
    else:
        chain = shots

    if not chain:
        print("[ERROR] no shots", file=sys.stderr)
        return EXIT_USAGE

    format_id = story.format_id()
    work_preset = story.doc.get("default_work_preset")
    try:
        width, height, _, _ = resolve_work_size(format_id, work_preset)
    except Exception:
        width, height = 544, 960

    width = int(round(width / 16) * 16)
    height = int(round(height / 16) * 16)

    from generate_i2v import generate_i2v
    from generate_s2v import generate_s2v
    from lib.audio_package import materialize_driving_audio
    from lib.ltx_s2v import is_ltx_backend, snap_ltx_frames
    from lib.performance_profiles import resolve_si2v_motion_prompt
    from lib.s2v_length_contract import validate_pre_generate
    from generate_s2v import _snap_frames

    started = args.start_from is None
    prev_clip: str | None = None

    print(
        f"chain_one_take episode={args.episode} shots={[s.get('shot_id') for s in chain]} "
        f"canvas={width}x{height} fps={args.fps} s2v={args.backend_s2v} i2v={args.backend_i2v}"
    )

    for i, shot in enumerate(chain):
        sid = shot.get("shot_id")
        # re-load shot for fresh status
        try:
            shot = story.get_shot(sid)
        except KeyError:
            pass

        if not started:
            if sid == args.start_from:
                started = True
            else:
                cand = work_clip_path(story, shot, sid)
                if os.path.isfile(cand):
                    prev_clip = cand
                continue

        drv = (shot.get("motion_driver") or "i2v").lower()
        is_s2v = drv in ("si2v", "s2v")
        clip_path = work_clip_path(story, shot, sid)
        os.makedirs(os.path.dirname(clip_path), exist_ok=True)

        # --- seed keyframe ---
        if i == 0 and args.keep_first_clip and os.path.isfile(clip_path):
            print(f"\n>>> {sid} keep existing first clip {clip_path}")
            prev_clip = clip_path
            story.update_shot(sid, keyframe_status="approved", clip_status="pending")
            if not args.no_pause and i < len(chain) - 1:
                print(
                    f"[PAUSE] approve {sid} then:\n"
                    f"  python scripts/shot_approve.py -e {args.episode} -s {sid} --clip approved\n"
                    f"  python scripts/chain_one_take.py -e {args.episode} "
                    f"--start-from {chain[i+1].get('shot_id')} --keep-first-clip ..."
                )
                return EXIT_OK
            continue

        if i > 0:
            prev_sid = chain[i - 1].get("shot_id")
            try:
                prev_shot = story.get_shot(prev_sid)
            except KeyError:
                prev_shot = chain[i - 1]
            if prev_clip is None:
                prev_clip = work_clip_path(story, prev_shot, prev_sid)

            gate = check_prev_clip_gate(
                story, prev_shot, force=bool(args.force_clip_gate)
            )
            if not gate.get("ok"):
                print(f"[ERROR] code={gate.get('exit_code') or 30} {gate.get('message')}", file=sys.stderr)
                return int(gate.get("exit_code") or EXIT_FAIL)

            prev_clip = gate["prev_clip"]
            print(f"\n>>> {sid} last_frame of {prev_sid} → keyframes/{sid}.png")
            if not args.dry_run:
                kr = keyframe_from_prev_clip(
                    story,
                    sid,
                    width=width,
                    height=height,
                    force_clip_gate=True,  # already gated above
                    prev_shot_id=prev_sid,
                )
                if not kr.get("ok"):
                    print(f"[ERROR] keyframe {kr}", file=sys.stderr)
                    return EXIT_FAIL
                kf_path = kr["keyframe_path"]
                story.update_shot(
                    sid,
                    keyframe=kr["keyframe_rel"],
                    keyframe_status="approved",
                    continuity={
                        "style": "one_take",
                        "chain": "last_frame",
                        "match_from": prev_sid,
                        "from_clip": os.path.relpath(prev_clip, story.root).replace(
                            "\\", "/"
                        ),
                    },
                    composed_at=utc_now_iso(),
                )
            else:
                kf_path = story.path("keyframes", f"{sid}.png")
        else:
            krel = shot.get("keyframe") or f"keyframes/{sid}.png"
            kf_path = story.path(*str(krel).replace("\\", "/").split("/"))
            if not os.path.isfile(kf_path):
                print(f"[ERROR] first keyframe missing {kf_path}", file=sys.stderr)
                return EXIT_MISSING
            print(f"\n>>> {sid} first keyframe {kf_path}")
            story.update_shot(sid, keyframe_status="approved")

        if is_s2v:
            perf = resolve_si2v_motion_prompt(shot, performance=args.performance)
            motion = perf["motion_prompt"]
            # one-take continuity suffix
            if "one-take" not in motion.lower() and "one take" not in motion.lower():
                motion = motion.rstrip(".") + ", one-take continuity, locked camera"
            scale = (
                float(args.audio_scale)
                if args.audio_scale is not None
                else float(perf["audio_scale"])
            )
            print(
                f"  performance={perf['performance']} "
                f"motion_src={perf['source']} audio_scale={scale}"
            )

            audio_info = materialize_driving_audio(
                story.root, shot, prepare_mode=args.prepare_mode, force=False
            )
            if not audio_info.get("ok"):
                print(f"[ERROR] audio {sid}: {audio_info}", file=sys.stderr)
                return EXIT_FAIL
            audio_path = audio_info["path"]

            snap = (
                snap_ltx_frames
                if is_ltx_backend(args.backend_s2v)
                else _snap_frames
            )
            pre = validate_pre_generate(
                backend=args.backend_s2v,
                fps=float(args.fps),
                drive_path=audio_path,
                snap_fn=snap,
            )
            if not pre.get("ok"):
                print(
                    f"[ERROR] length {pre.get('error')}: {pre.get('message')}",
                    file=sys.stderr,
                )
                return EXIT_FAIL
            print(
                f"  SI2V audio={audio_path} drive={pre.get('drive_sec')}s "
                f"frames={pre.get('num_frames')}"
            )
            if args.dry_run:
                print("  [dry-run] skip s2v")
                prev_clip = clip_path if os.path.isfile(clip_path) else prev_clip
                continue

            s2v_kw = dict(
                backend=args.backend_s2v,
                prompt=motion,
                width=width,
                height=height,
                fps=float(args.fps),
                steps=int(args.s2v_steps),
                audio_scale=scale,
                num_frames=int(pre["num_frames"]) if pre.get("num_frames") else None,
                timeout_sec=args.timeout,
                meta_out=story.path("meta", f"{sid}_s2v.json"),
                speed_lora=True,
                teacache=False,
            )
            if perf.get("negative_motion"):
                s2v_kw["negative"] = perf["negative_motion"]
            result = generate_s2v(kf_path, audio_path, clip_path, **s2v_kw)
            if not result.get("ok"):
                print(f"[ERROR] s2v {sid}: {result}", file=sys.stderr)
                return EXIT_FAIL
            story.update_shot(
                sid,
                clip_work_s2v=f"clips/work/{sid}_s2v.mp4",
                s2v_status="ok",
                s2v_backend=args.backend_s2v,
                s2v_performance=perf.get("performance"),
                performance=perf.get("performance"),
                s2v_driving_audio=os.path.relpath(audio_path, story.root).replace(
                    "\\", "/"
                ),
                clip_status="pending",
                lip_status="pending",
            )
        else:
            motion = (shot.get("motion_prompt") or "").strip()
            if not motion:
                motion = (
                    "subtle natural motion, locked camera or very slow push-in, "
                    "keep identity wardrobe seat fixed, one-take continuity"
                )
            dur = float(shot.get("duration_sec") or 3.5)
            frames = int(math.ceil(dur * float(args.fps) - 1e-9))
            print(f"  I2V backend={args.backend_i2v} frames~{frames} motion={motion[:80]}")
            if args.dry_run:
                print("  [dry-run] skip i2v")
                prev_clip = clip_path if os.path.isfile(clip_path) else prev_clip
                continue
            result = generate_i2v(
                input_image_path=kf_path,
                prompt_text=motion,
                output_filename=clip_path,
                backend=args.backend_i2v,
                width=width,
                height=height,
                frame_rate=int(args.fps),
                num_frames=frames,
                timeout_sec=args.timeout,
                meta_out=story.path("meta", f"{sid}_i2v.json"),
                profile="deliver",
                cache="none",
                apply_profile_long_edge=False,
            )
            if not result.get("ok"):
                print(f"[ERROR] i2v {sid}: {result}", file=sys.stderr)
                return EXIT_FAIL
            story.update_shot(
                sid,
                clip_work=f"clips/work/{sid}.mp4",
                i2v_status="ok",
                clip_status="pending",
            )

        cdur = probe_duration(clip_path) if os.path.isfile(clip_path) else None
        print(f"  OK {sid} → {clip_path} dur={cdur}")
        prev_clip = clip_path

        if not args.no_pause and i < len(chain) - 1:
            nxt = chain[i + 1].get("shot_id")
            print(
                f"\n[PAUSE] Review {sid}, then:\n"
                f"  python scripts/shot_approve.py -e {args.episode} -s {sid} --clip approved\n"
                f"  python scripts/chain_one_take.py -e {args.episode} --start-from {nxt} ..."
            )
            return EXIT_OK

    print("\nDone one-take chain:", " → ".join(s.get("shot_id") for s in chain))
    print("Next: hard-cut assemble (no xfade preferred for true one-take)")

    if not args.dry_run:
        from lib.workspace_export import (
            CLIP_PARTS,
            export_flag_from_args,
            maybe_export_episode,
        )

        ex = maybe_export_episode(
            args.episode,
            export_flag=export_flag_from_args(args),
            dest=getattr(args, "export_dest", None),
            parts=list(CLIP_PARTS),
        )
        if not ex.get("skipped") and not ex.get("ok"):
            print(f"[WARN] export-workspace: {ex.get('error')}: {ex.get('message')}")

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
