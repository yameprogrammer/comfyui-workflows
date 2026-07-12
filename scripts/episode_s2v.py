#!/usr/bin/env python3
"""Batch SI2V for motion_driver=si2v shots → clips/work/*_s2v.mp4.

Use for:
  - story: on-screen dialogue (driving = dialogue/TTS wav)
  - music_video: on-camera vocal / singing cuts (driving = master slice ± vocal prep)
Not story-only — any shot where the mouth must track audio.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from generate_s2v import generate_s2v
from lib.audio_package import materialize_driving_audio, shot_motion_driver
from lib.comfy_client import utc_now_iso
from lib.story_package import StoryPackage, validate_episode_id
from lib.video_backends import get_preset, load_video_backends, resolve_s2v_backend

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_NONE = 21
EXIT_PARTIAL = 31


def _select_shots(story: StoryPackage, shots_arg: str, require_approved: bool) -> list[dict]:
    all_shots = sorted(story.shots(), key=lambda s: s.get("order", 0))
    if shots_arg in ("all", "all_approved", "*"):
        selected = all_shots
    else:
        want = {x.strip() for x in shots_arg.split(",") if x.strip()}
        selected = [s for s in all_shots if s.get("shot_id") in want]
        missing = want - {s.get("shot_id") for s in selected}
        if missing:
            raise KeyError(f"unknown shots: {sorted(missing)}")

    if require_approved or shots_arg == "all_approved":
        selected = [s for s in selected if s.get("keyframe_status") == "approved"]
    return selected


def _filter_si2v(story: StoryPackage, selected: list[dict]) -> tuple[list[dict], list[dict]]:
    run, skip = [], []
    for s in selected:
        d = shot_motion_driver(s, story.doc)
        if d == "si2v":
            run.append(s)
        else:
            skip.append(s)
    return run, skip


def _work_size(story: StoryPackage, shot: dict, long_edge: int) -> tuple[int, int]:
    """Prefer episode work preset; cap long edge for InfiniteTalk VRAM; snap later in runner."""
    ws = shot.get("work_size") or {}
    w = int(ws.get("width") or 0)
    h = int(ws.get("height") or 0)
    if w <= 0 or h <= 0:
        preset_id = story.doc.get("default_work_preset")
        try:
            cfg = load_video_backends()
            pr = get_preset(str(preset_id or cfg.get("default_work_preset")), cfg)
            w, h = int(pr["width"]), int(pr["height"])
        except Exception:
            w, h = 640, 640
    # Talking-head smokes used 640²; keep aspect but cap long edge.
    long_edge = max(256, int(long_edge))
    m = max(w, h)
    if m > long_edge:
        scale = long_edge / float(m)
        w = max(16, int(round(w * scale)))
        h = max(16, int(round(h * scale)))
    return w, h


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Run SI2V for episode shots with motion_driver=si2v"
    )
    parser.add_argument("--episode", "-e", required=True)
    parser.add_argument(
        "--shots",
        default="all_approved",
        help="all_approved | all | S01,S02,... (default all_approved)",
    )
    parser.add_argument(
        "--allow-draft",
        action="store_true",
        help="Include non-approved keyframes when selecting by id/all",
    )
    parser.add_argument(
        "--prepare-mode",
        default="center_voicey",
        help="Driving audio prep: copy|voicey|center|vocal_band|center_voicey",
    )
    parser.add_argument(
        "--force-audio",
        action="store_true",
        help="Rebuild cached prepared driving wavs",
    )
    parser.add_argument("--fps", type=float, default=25.0)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--cfg", type=float, default=1.0)
    parser.add_argument("--audio-scale", type=float, default=1.5)
    parser.add_argument("--long-edge", type=int, default=640, help="Cap work long edge (default 640)")
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Abort on first failed shot (default: continue)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional fixed seed for all shots (default random per shot)",
    )
    parser.add_argument(
        "--backend",
        default=None,
        help="SI2V backend: infinitetalk | ltx23_ia2v (default episode default_backend_s2v / infinitetalk)",
    )
    args = parser.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] code=2 invalid episode id", file=sys.stderr)
        return EXIT_USAGE

    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] code=11 episode missing: {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    require_approved = not args.allow_draft
    if args.shots == "all" and not args.allow_draft:
        require_approved = True

    try:
        selected = _select_shots(story, args.shots, require_approved=require_approved)
    except KeyError as e:
        print(f"[ERROR] code=2 {e}", file=sys.stderr)
        return EXIT_USAGE

    if not selected:
        print(
            "[ERROR] code=21 no shots to run "
            "(need keyframe_status=approved, or pass --allow-draft / explicit ids)",
            file=sys.stderr,
        )
        return EXIT_NONE

    selected, skipped = _filter_si2v(story, selected)
    for s in skipped:
        print(
            f"[SKIP] {s.get('shot_id')} motion_driver={shot_motion_driver(s, story.doc)} "
            "(not si2v — use episode_i2v / still path)"
        )

    if not selected:
        print(
            "[ERROR] code=21 no si2v shots to run "
            "(set motion_driver=si2v and audio_refs.driving)",
            file=sys.stderr,
        )
        return EXIT_NONE

    try:
        backend = resolve_s2v_backend(args.backend, episode_doc=story.doc)
    except (KeyError, ValueError, RuntimeError) as e:
        print(f"[ERROR] code=2 s2v backend: {e}", file=sys.stderr)
        return EXIT_USAGE
    print(
        f"episode_s2v episode={args.episode} backend={backend} "
        f"shots={len(selected)} skipped={len(skipped)} "
        f"prepare={args.prepare_mode} fps={args.fps} steps={args.steps}"
    )

    ok = 0
    fail = 0
    for shot in selected:
        sid = shot.get("shot_id")
        kf_rel = shot.get("keyframe") or f"keyframes/{sid}.png"
        kf_path = story.path(*kf_rel.replace("\\", "/").split("/"))
        # Dedicated s2v path so i2v work clips are not clobbered when mixed drivers exist.
        clip_rel = shot.get("clip_work_s2v") or f"clips/work/{sid}_s2v.mp4"
        clip_path = story.path(*str(clip_rel).replace("\\", "/").split("/"))
        os.makedirs(os.path.dirname(clip_path), exist_ok=True)

        motion = (shot.get("motion_prompt") or "").strip() or (
            "a person speaking naturally, subtle head motion, natural lip motion, cinematic"
        )
        width, height = _work_size(story, shot, args.long_edge)
        meta_path = story.path("meta", f"{sid}_s2v.json")

        print(f"\n=== {sid} status={shot.get('keyframe_status')} size={width}x{height} ===")
        print(f"  keyframe={kf_path}")
        print(f"  out={clip_path}")

        if not os.path.isfile(kf_path):
            print("  FAIL keyframe file missing")
            fail += 1
            if args.stop_on_error:
                break
            continue

        audio_info = materialize_driving_audio(
            story.root,
            shot,
            prepare_mode=args.prepare_mode,
            force=args.force_audio,
        )
        if not audio_info.get("ok"):
            print(f"  FAIL audio {audio_info.get('error')}: {audio_info.get('message')}")
            fail += 1
            story.update_shot(
                sid,
                s2v_status="failed",
                s2v_error=audio_info.get("error"),
                s2v_at=utc_now_iso(),
            )
            if args.stop_on_error:
                break
            continue

        audio_path = audio_info["path"]
        print(f"  audio={audio_path} prep={audio_info.get('prepare_mode')} cached={audio_info.get('cached')}")

        if args.dry_run:
            print("  [dry-run] skip generate_s2v")
            ok += 1
            continue

        result = generate_s2v(
            kf_path,
            audio_path,
            clip_path,
            backend=backend,
            prompt=motion,
            width=width,
            height=height,
            fps=args.fps,
            steps=args.steps,
            cfg=args.cfg,
            audio_scale=args.audio_scale,
            seed=args.seed,
            timeout_sec=args.timeout,
            meta_out=meta_path,
            dry_run=False,
        )

        if result.get("ok"):
            ok += 1
            story.update_shot(
                sid,
                clip_work=str(clip_rel).replace("\\", "/"),
                clip_work_s2v=str(clip_rel).replace("\\", "/"),
                s2v_status="ok",
                s2v_at=utc_now_iso(),
                s2v_backend=backend,
                s2v_prepare_mode=args.prepare_mode,
                s2v_driving_audio=os.path.relpath(audio_path, story.root).replace("\\", "/"),
            )
            print(f"  OK {clip_path}")
        else:
            fail += 1
            story.update_shot(
                sid,
                s2v_status="failed",
                s2v_error=result.get("error"),
                s2v_at=utc_now_iso(),
            )
            print(f"  FAIL {result.get('error')} {result.get('message')}")
            if args.stop_on_error:
                break

    print(f"\nDone ok={ok} fail={fail} total={len(selected)}")
    if ok == 0:
        return EXIT_PARTIAL if fail else EXIT_NONE
    if fail:
        return EXIT_PARTIAL
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
