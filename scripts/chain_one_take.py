#!/usr/bin/env python3
"""Full-episode one-take chain: each shot starts from the previous clip's last frame.

Supports mixed motion drivers in shot order (i2v + si2v).
  S_n last frame → keyframes/S_{n+1}.png → generate I2V or SI2V

Example:
  python scripts/chain_one_take.py -e cafe_gomin_ep01 --backend-s2v infinitetalk \\
    --prepare-mode center_voicey --no-pause --force-clip-gate
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import math
import os
import sys

from lib.comfy_client import utc_now_iso
from lib.ffmpeg_util import probe_duration, run_ffmpeg
from lib.story_package import StoryPackage, resolve_work_size

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_FAIL = 30


def extract_last_frame(video: str, png: str) -> dict:
    os.makedirs(os.path.dirname(png) or ".", exist_ok=True)
    r = run_ffmpeg(
        ["-y", "-sseof", "-0.08", "-i", video, "-frames:v", "1", "-q:v", "2", png],
        timeout_sec=120,
    )
    if r.get("ok") and os.path.isfile(png) and os.path.getsize(png) > 1000:
        return r
    return run_ffmpeg(
        [
            "-y",
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


def fit_png(src: str, dst: str, w: int, h: int) -> None:
    """Cover-crop resize last frame to episode work canvas."""
    from PIL import Image

    im = Image.open(src).convert("RGB")
    sw, sh = im.size
    scale = max(w / sw, h / sh)
    nw, nh = max(1, int(round(sw * scale))), max(1, int(round(sh * scale)))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    im.crop((left, top, left + w, top + h)).save(dst)


def work_clip_path(story: StoryPackage, shot: dict, sid: str) -> str:
    drv = (shot.get("motion_driver") or "i2v").lower()
    if drv in ("si2v", "s2v"):
        rel = shot.get("clip_work_s2v") or f"clips/work/{sid}_s2v.mp4"
    else:
        rel = shot.get("clip_work") or f"clips/work/{sid}.mp4"
    return story.path(*str(rel).replace("\\", "/").split("/"))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="One-take chain all shots (i2v+si2v)")
    p.add_argument("--episode", "-e", required=True)
    p.add_argument("--shots", default=None, help="Comma list (default: all shots in order)")
    p.add_argument("--backend-s2v", default="infinitetalk")
    p.add_argument("--backend-i2v", default="wan22")
    p.add_argument("--prepare-mode", default="center_voicey")
    p.add_argument("--fps", type=float, default=24.0)
    p.add_argument("--audio-scale", type=float, default=1.25)
    p.add_argument("--s2v-steps", type=int, default=12)
    p.add_argument("--timeout", type=int, default=2400)
    p.add_argument("--start-from", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--force-clip-gate",
        action="store_true",
        help="Allow chain without prev clip_status=approved",
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
        want = {s.strip() for s in args.shots.split(",") if s.strip()}
        chain = [s for s in shots if s.get("shot_id") in want]
        # preserve user order if given
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

    # IT dims %16
    width = int(round(width / 16) * 16)
    height = int(round(height / 16) * 16)

    from generate_i2v import generate_i2v
    from generate_s2v import generate_s2v
    from lib.audio_package import materialize_driving_audio
    from lib.episode_status import CLIP_STATUS_OK, normalize_clip_status

    started = args.start_from is None
    prev_clip: str | None = None

    print(
        f"chain_one_take episode={args.episode} shots={[s.get('shot_id') for s in chain]} "
        f"canvas={width}x{height} fps={args.fps} s2v={args.backend_s2v} i2v={args.backend_i2v}"
    )

    for i, shot in enumerate(chain):
        sid = shot.get("shot_id")
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
        kf_path = story.path("keyframes", f"{sid}.png")
        clip_path = work_clip_path(story, shot, sid)
        os.makedirs(os.path.dirname(clip_path), exist_ok=True)

        # --- seed keyframe ---
        if i == 0 and args.keep_first_clip and os.path.isfile(clip_path):
            print(f"\n>>> {sid} keep existing first clip {clip_path}")
            prev_clip = clip_path
            story.update_shot(sid, keyframe_status="approved", clip_status="pending")
            if not args.no_pause and i < len(chain) - 1:
                print(f"[PAUSE] approve {sid} then --start-from {chain[i+1].get('shot_id')}")
                return EXIT_OK
            continue

        if i > 0:
            if not prev_clip or not os.path.isfile(prev_clip):
                print(f"[ERROR] no previous clip for {sid}", file=sys.stderr)
                return EXIT_FAIL
            prev_sid = chain[i - 1].get("shot_id")
            if not args.force_clip_gate:
                prev_shot = chain[i - 1]
                pst = normalize_clip_status(prev_shot, work_ok=True)
                if pst not in CLIP_STATUS_OK:
                    print(
                        f"[ERROR] code=22 cannot chain {prev_sid}→{sid} "
                        f"clip_status={pst!r}",
                        file=sys.stderr,
                    )
                    print(
                        f"  python scripts/shot_approve.py -e {args.episode} "
                        f"-s {prev_sid} --clip approved"
                    )
                    return EXIT_FAIL
            print(f"\n>>> {sid} last_frame of {prev_sid} → {kf_path}")
            if not args.dry_run:
                tmp = kf_path + ".tmp.png"
                r = extract_last_frame(prev_clip, tmp)
                if not r.get("ok"):
                    print(f"[ERROR] extract failed {r}", file=sys.stderr)
                    return EXIT_FAIL
                fit_png(tmp, kf_path, width, height)
                try:
                    os.remove(tmp)
                except OSError:
                    pass
                story.update_shot(
                    sid,
                    keyframe=f"keyframes/{sid}.png",
                    keyframe_status="approved",
                    continuity={
                        "style": "one_take",
                        "chain": "last_frame",
                        "match_from": prev_sid,
                        "from_clip": os.path.relpath(prev_clip, story.root).replace("\\", "/"),
                    },
                    composed_at=utc_now_iso(),
                )
        else:
            # first shot: use existing keyframe
            krel = shot.get("keyframe") or f"keyframes/{sid}.png"
            kf_path = story.path(*str(krel).replace("\\", "/").split("/"))
            if not os.path.isfile(kf_path):
                print(f"[ERROR] first keyframe missing {kf_path}", file=sys.stderr)
                return EXIT_MISSING
            print(f"\n>>> {sid} first keyframe {kf_path}")
            story.update_shot(sid, keyframe_status="approved")

        motion = (shot.get("motion_prompt") or "").strip()
        if is_s2v:
            low = motion.lower()
            if "lip" not in low and "speak" not in low and "talk" not in low:
                motion = (
                    "same person continuing in the same seat, natural lip sync with dialogue, "
                    "minimal upper body motion matching speech tone, locked camera, "
                    "keep identity wardrobe background fixed, one-take continuity"
                )
            audio_info = materialize_driving_audio(
                story.root, shot, prepare_mode=args.prepare_mode, force=True
            )
            if not audio_info.get("ok"):
                print(f"[ERROR] audio {sid}: {audio_info}", file=sys.stderr)
                return EXIT_FAIL
            audio_path = audio_info["path"]
            adur = probe_duration(audio_path)
            print(f"  SI2V audio={audio_path} dur={adur}")
            if args.dry_run:
                print("  [dry-run] skip s2v")
                prev_clip = clip_path if os.path.isfile(clip_path) else prev_clip
                continue
            result = generate_s2v(
                kf_path,
                audio_path,
                clip_path,
                backend=args.backend_s2v,
                prompt=motion,
                width=width,
                height=height,
                fps=float(args.fps),
                steps=int(args.s2v_steps),
                audio_scale=float(args.audio_scale),
                timeout_sec=args.timeout,
                meta_out=story.path("meta", f"{sid}_s2v.json"),
                speed_lora=True,
                teacache=False,
            )
            if not result.get("ok"):
                print(f"[ERROR] s2v {sid}: {result}", file=sys.stderr)
                return EXIT_FAIL
            story.update_shot(
                sid,
                clip_work_s2v=f"clips/work/{sid}_s2v.mp4",
                s2v_status="ok",
                s2v_backend=args.backend_s2v,
                clip_status="pending",
                lip_status="pending",
            )
        else:
            # I2V
            if not motion:
                motion = (
                    "subtle natural motion, locked camera or very slow push-in, "
                    "keep identity wardrobe seat fixed, one-take continuity"
                )
            dur = float(shot.get("duration_sec") or 3.5)
            frames = int(math.ceil(dur * float(args.fps) - 1e-9))
            # wan often wants 4n+1 style — generate_i2v may snap
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
                f"  python scripts/chain_one_take.py -e {args.episode} --start-from {nxt} --no-pause ..."
            )
            return EXIT_OK

    print("\nDone one-take chain:", " → ".join(s.get("shot_id") for s in chain))
    print("Next: approve clips, hard-cut assemble (no xfade preferred for true one-take)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
