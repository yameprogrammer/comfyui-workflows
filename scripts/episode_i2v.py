#!/usr/bin/env python3
"""Batch I2V for approved episode keyframes → clips/work/."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from generate_i2v import generate_i2v
from lib.audio_package import shot_motion_driver
from lib.comfy_client import utc_now_iso, write_meta
from lib.story_package import StoryPackage, validate_episode_id

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


def _filter_i2v_drivers(story: StoryPackage, selected: list[dict]) -> tuple[list[dict], list[dict]]:
    """Keep i2v + flf2v shots; return (run, skipped_other)."""
    run, skip = [], []
    for s in selected:
        d = shot_motion_driver(s, story.doc)
        if d in ("i2v", "flf2v"):
            run.append(s)
        elif d in (
            "still",
            "si2v",
            "v2v_camera",
            "v2v_motion",
            "v2v_style",
        ):
            skip.append(s)
        else:
            run.append(s)
    return run, skip


def _resolve_end_keyframe(story: StoryPackage, shot: dict, sid: str) -> str | None:
    """Return absolute path to keyframe_end / last still if present."""
    import os

    for key in ("keyframe_end", "keyframe_last", "end_keyframe"):
        rel = shot.get(key)
        if not rel:
            continue
        path = story.path(*str(rel).replace("\\", "/").split("/"))
        if path and os.path.isfile(path):
            return path
    # convention: keyframes/Sxx_end.png
    cand = story.path("keyframes", f"{sid}_end.png")
    if os.path.isfile(cand):
        return cand
    return None


def _frames_for_shot(duration_sec: float, fps: float) -> int:
    n = max(9, int(round(float(duration_sec) * float(fps))))
    # prefer odd counts common in video diffusion
    if n % 2 == 0:
        n += 1
    return n


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Run I2V for episode keyframes (approved by default)"
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
    parser.add_argument("--backend", default=None, help="I2V backend (default episode/wan22)")
    parser.add_argument("--fps", type=float, default=None, help="I2V frame rate (default 16)")
    parser.add_argument("--steps", type=int, default=6)
    parser.add_argument("--cfg", type=float, default=1.0)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Abort on first failed shot (default: continue)",
    )
    parser.add_argument(
        "--allow-freeze",
        action="store_true",
        help="Do not fail shots that look static/freeze-tailed (intentional still only)",
    )
    parser.add_argument(
        "--no-freeze-gate",
        action="store_true",
        help="Skip post-I2V freeze detection (debug; same as AGENT_FREEZE_GATE=0)",
    )
    from lib.workspace_export import add_export_workspace_args

    add_export_workspace_args(parser)
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
        # 'all' still filters to approved unless --allow-draft
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

    selected, skipped = _filter_i2v_drivers(story, selected)
    for s in skipped:
        print(
            f"[SKIP] {s.get('shot_id')} motion_driver={shot_motion_driver(s, story.doc)} "
            "(not i2v — use episode_s2v / still path when available)"
        )

    if not selected:
        print(
            "[ERROR] code=21 no i2v/flf2v shots to run "
            "(all selected use si2v/still/v2v)",
            file=sys.stderr,
        )
        return EXIT_NONE

    format_id = story.format_id()
    work_preset = story.doc.get("default_work_preset")
    backend = (
        args.backend
        or story.doc.get("default_backend_i2v")
        or "ltx23_aio_i2v"  # quality default (A/B 2026-07-17 vs Wan)
    )
    fps = float(args.fps if args.fps is not None else 16)

    print(
        f"episode_i2v episode={args.episode} format={format_id} "
        f"backend={backend} shots={len(selected)} skipped_other_drivers={len(skipped)} fps={fps}"
    )

    ok = 0
    fail = 0
    for shot in selected:
        sid = shot.get("shot_id")
        kf_rel = shot.get("keyframe") or f"keyframes/{sid}.png"
        kf_path = story.path(*kf_rel.replace("\\", "/").split("/"))
        clip_rel = shot.get("clip_work") or f"clips/work/{sid}.mp4"
        clip_path = story.path(*clip_rel.replace("\\", "/").split("/"))
        os.makedirs(os.path.dirname(clip_path), exist_ok=True)

        motion = (shot.get("motion_prompt") or "").strip() or "gentle natural motion"
        neg = (shot.get("negative_motion") or "").strip()
        duration = float(shot.get("duration_sec") or 4)
        frames = _frames_for_shot(duration, fps)
        meta_path = story.path("meta", f"{sid}_i2v.json")
        driver = shot_motion_driver(shot, story.doc)
        end_kf = _resolve_end_keyframe(story, shot, sid)
        use_flf = driver == "flf2v" or bool(end_kf)
        shot_backend = backend
        # Quality default FLF = LTX (A/B 2026-07-17 vs Wan). Explicit wan* keeps Wan.
        if use_flf:
            be_l = str(backend or "").lower()
            if not be_l or be_l in ("flf2v", "ltx23_aio_i2v", "ltx23", "ltx23_aio"):
                shot_backend = "ltx23_aio_flf"
            elif be_l in ("wan22", "wan22_flf2v"):
                shot_backend = "wan22_flf"

        print(f"\n=== {sid} status={shot.get('keyframe_status')} frames={frames} driver={driver} ===")
        print(f"  keyframe={kf_path}")
        if end_kf:
            print(f"  keyframe_end={end_kf}")
        elif use_flf:
            print("  WARN flf2v without keyframe_end — will fail FLF unless end frame exists")
        print(f"  out={clip_path}")
        print(f"  motion={motion[:100]}")

        if not os.path.isfile(kf_path):
            print(f"  FAIL keyframe file missing")
            fail += 1
            if args.stop_on_error:
                break
            continue

        if use_flf and not end_kf:
            print("  FAIL FLF requires keyframe_end (or keyframes/Sxx_end.png)")
            fail += 1
            if args.stop_on_error:
                break
            continue

        if args.dry_run:
            print("  [dry-run] skip generate_i2v")
            ok += 1
            continue

        result = generate_i2v(
            input_image_path=kf_path,
            end_image_path=end_kf,
            prompt_text=motion,
            negative_text=neg or "",
            output_filename=clip_path,
            num_frames=frames,
            frame_rate=int(fps) if fps == int(fps) else 16,
            steps=args.steps,
            cfg=args.cfg,
            backend=shot_backend,
            format_id=format_id,
            preset=work_preset,
            meta_out=meta_path,
            timeout_sec=args.timeout,
        )

        if result.get("ok"):
            # Post-gen freeze gate (default ON) — ban tpad/dead-tail work clips
            freeze_fail = False
            if not args.no_freeze_gate and os.path.isfile(clip_path):
                from lib.visual_qa import (
                    gate_work_clip_no_freeze,
                    shot_allows_still_freeze,
                )

                allow_still = args.allow_freeze or shot_allows_still_freeze(
                    shot, story.doc
                )
                sample = story.path("boards", "qa", f"{sid}_clip_frames")
                gate = gate_work_clip_no_freeze(
                    clip_path,
                    sample_dir=sample,
                    allow_still=allow_still,
                )
                if not gate.get("ok") and gate.get("error") == "FREEZE_PAD_SUSPECT":
                    freeze_fail = True
                    fail += 1
                    story.update_shot(
                        sid,
                        clip_work=clip_rel.replace("\\", "/"),
                        i2v_status="failed_freeze",
                        i2v_error="FREEZE_PAD_SUSPECT",
                        i2v_at=utc_now_iso(),
                        i2v_backend=backend,
                        i2v_frames=frames,
                        clip_status="rejected",
                        freeze_suspect=True,
                        freeze_kind=gate.get("kind"),
                    )
                    print(f"  FAIL FREEZE_PAD_SUSPECT kind={gate.get('kind')}")
                    print(f"  {gate.get('message')}")
                    print(
                        "  fix: match duration_sec to full I2V length / split shot; "
                        "never tpad clone. intentional still: --allow-freeze"
                    )
                    if args.stop_on_error:
                        break
                    continue
                if gate.get("report"):
                    try:
                        write_meta(
                            story.path("meta", f"{sid}_freeze_gate.json"),
                            {
                                "shot_id": sid,
                                "stage": "i2v_post",
                                **{k: v for k, v in gate.items() if k != "report"},
                                "report": gate.get("report"),
                            },
                        )
                    except Exception:
                        pass

            if not freeze_fail:
                ok += 1
                story.update_shot(
                    sid,
                    clip_work=clip_rel.replace("\\", "/"),
                    i2v_status="ok",
                    i2v_at=utc_now_iso(),
                    i2v_backend=backend,
                    i2v_frames=frames,
                    freeze_suspect=False,
                    # Human/vision gate — assemble requires clip_status=approved
                    clip_status="pending",
                )
                print(f"  OK {clip_path}")
                print(
                    f"  clip_status=pending → review clip then: "
                    f"python scripts/shot_qa_record.py -e {args.episode} -s {sid} "
                    f"--stage clip --verdict pass --pass-required --notes \"...\" "
                    f"&& python scripts/shot_approve.py -e {args.episode} -s {sid} --clip approved"
                )
        else:
            fail += 1
            story.update_shot(
                sid,
                i2v_status="failed",
                i2v_error=result.get("error"),
                i2v_at=utc_now_iso(),
            )
            print(f"  FAIL {result.get('error')} {result.get('message')}")
            if args.stop_on_error:
                break

    print(f"\nDone ok={ok} fail={fail} total={len(selected)}")

    # P0-3: copy to AGENT_WORKSPACE when configured / --export-workspace
    if ok > 0 and not args.dry_run:
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

    if ok == 0:
        return EXIT_PARTIAL if fail else EXIT_NONE
    if fail:
        return EXIT_PARTIAL
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
