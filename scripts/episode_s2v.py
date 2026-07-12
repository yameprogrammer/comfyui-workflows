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


def _work_size(
    story: StoryPackage,
    shot: dict,
    long_edge: int,
    *,
    square: bool = False,
) -> tuple[int, int]:
    """
    SI2V generation size.

    Default: episode work aspect (format-consistent with I2V).
    Opt-in square=True for tight face CU when agent explicitly wants it.
    """
    long_edge = max(256, int(long_edge))
    if square:
        # Prefer even multiple of 32 for LTX; 16 for Wan/InfiniteTalk.
        side = long_edge if long_edge % 32 == 0 else (long_edge // 32) * 32
        side = max(256, side)
        return side, side

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
            w, h = 960, 544
    m = max(w, h)
    if m > long_edge:
        scale = long_edge / float(m)
        w = max(16, int(round(w * scale / 16) * 16))
        h = max(16, int(round(h * scale / 16) * 16))
    else:
        w = max(16, int(round(w / 16) * 16))
        h = max(16, int(round(h / 16) * 16))
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
        default="auto",
        help="Driving prep: auto(demucs→center_voicey)|copy|voicey|center|vocal_band|center_voicey|demucs",
    )
    parser.add_argument(
        "--square",
        dest="square",
        action="store_true",
        default=None,
        help="Force square face canvas (opt-in; default is episode work aspect)",
    )
    parser.add_argument(
        "--no-square",
        dest="square",
        action="store_false",
        help="Use episode work aspect (default)",
    )
    parser.set_defaults(square=False)
    parser.add_argument(
        "--long-edge",
        type=int,
        default=None,
        help="Cap long edge (default 960 LTX / 832 InfiniteTalk hero)",
    )
    parser.add_argument(
        "--force-audio",
        action="store_true",
        help="Rebuild cached prepared driving wavs",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=None,
        help="Frame rate (default 25 LTX / 16 InfiniteTalk hero)",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=None,
        help="Sampler steps (LTX unused schedule; IT default 12 without lightx2v)",
    )
    parser.add_argument("--cfg", type=float, default=1.0)
    parser.add_argument(
        "--audio-scale",
        type=float,
        default=None,
        help="InfiniteTalk audio_scale (default 1.5 LTX path / 2.0 IT)",
    )
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
        help="SI2V backend: infinitetalk (default) | ltx23_ia2v (preview)",
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

    # Backend-aware speed defaults (no Comfy graph edits).
    if backend == "infinitetalk":
        fps = float(args.fps if args.fps is not None else 16.0)
        steps = int(args.steps if args.steps is not None else 12)
        audio_scale = float(args.audio_scale if args.audio_scale is not None else 2.0)
        long_edge = int(args.long_edge if args.long_edge is not None else 832)
    else:
        fps = float(args.fps if args.fps is not None else 25.0)
        steps = int(args.steps if args.steps is not None else 20)
        audio_scale = float(args.audio_scale if args.audio_scale is not None else 1.5)
        long_edge = int(args.long_edge if args.long_edge is not None else 960)

    print(
        f"episode_s2v episode={args.episode} backend={backend} "
        f"shots={len(selected)} skipped={len(skipped)} "
        f"prepare={args.prepare_mode} fps={fps} steps={steps} "
        f"long_edge={long_edge} audio_scale={audio_scale}"
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

        motion = (shot.get("motion_prompt") or "").strip()
        # I2V-style still prompts suppress mouths; force speaking language for SI2V.
        low = motion.lower()
        anti_talk = any(
            k in low
            for k in (
                "micro facial",
                "natural blink",
                "do not change",
                "static",
                "still",
                "no new",
            )
        )
        if (not motion) or anti_talk or ("speak" not in low and "lip" not in low and "talk" not in low and "mouth" not in low):
            motion = (
                "person speaking clearly with natural lip sync, mouth opens and closes "
                "with the dialogue, jaw movement, subtle head motion, keep identity fixed, cinematic"
            )
            print(f"  [si2v] using speaking motion prompt (overrode non-talk I2V prompt)")
        width, height = _work_size(
            story, shot, long_edge, square=bool(args.square)
        )
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

        import time as _time

        t0 = _time.time()
        result = generate_s2v(
            kf_path,
            audio_path,
            clip_path,
            backend=backend,
            prompt=motion,
            width=width,
            height=height,
            fps=fps,
            steps=steps,
            cfg=args.cfg,
            audio_scale=audio_scale,
            seed=args.seed,
            timeout_sec=args.timeout,
            meta_out=meta_path,
            dry_run=False,
        )
        elapsed = _time.time() - t0

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
                s2v_elapsed_sec=round(elapsed, 2),
                s2v_size=f"{width}x{height}",
                s2v_fps=fps,
                s2v_steps=steps,
            )
            print(f"  OK {clip_path} elapsed={elapsed:.1f}s")
            # Patch meta with timing if present
            try:
                if meta_path and os.path.isfile(meta_path):
                    import json as _json

                    with open(meta_path, encoding="utf-8") as f:
                        meta = _json.load(f)
                    meta["elapsed_sec"] = round(elapsed, 2)
                    meta["width"] = width
                    meta["height"] = height
                    meta["fps"] = fps
                    meta["steps"] = steps
                    with open(meta_path, "w", encoding="utf-8") as f:
                        _json.dump(meta, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        else:
            fail += 1
            story.update_shot(
                sid,
                s2v_status="failed",
                s2v_error=result.get("error"),
                s2v_at=utc_now_iso(),
                s2v_elapsed_sec=round(elapsed, 2),
            )
            print(f"  FAIL {result.get('error')} {result.get('message')} elapsed={elapsed:.1f}s")
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
