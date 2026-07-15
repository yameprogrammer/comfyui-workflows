#!/usr/bin/env python3
"""Assemble episode clips toward a continuous 'single-take' feel.

Improvements over plain concat:
  - short video/audio crossfades between dialogue shots
  - normalize all clips to episode work canvas (e.g. 544x960)
  - pad each clip so video never ends before its audio (no chopped dialogue)
  - outro freeze hold after the last dialogue shot (breathing room after speech)

Does not replace FLF2V (planned). Complements continuous keyframe chains + SI2V.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import subprocess
import sys
import tempfile

from lib.ffmpeg_util import find_ffmpeg, probe_duration, probe_has_audio, run_ffmpeg
from lib.story_package import StoryPackage, resolve_work_size

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_FFMPEG = 30


def _ffprobe_bin() -> str:
    import shutil

    return shutil.which("ffprobe") or "ffprobe"


def _stream_size(path: str) -> tuple[int, int] | None:
    try:
        out = subprocess.check_output(
            [
                _ffprobe_bin(),
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "json",
                path,
            ],
            text=True,
            timeout=30,
        )
        st = json.loads(out)["streams"][0]
        return int(st["width"]), int(st["height"])
    except Exception:
        return None


def _resolve_clip(story: StoryPackage, shot: dict) -> str | None:
    """Prefer SI2V work clip, then I2V work, then deliver."""
    sid = shot["shot_id"]
    candidates = [
        shot.get("clip_work"),
        f"clips/work/{sid}_s2v.mp4",
        f"clips/work/{sid}.mp4",
        shot.get("clip_deliver"),
        f"clips/deliver/{sid}.mp4",
    ]
    for rel in candidates:
        if not rel:
            continue
        path = story.path(*str(rel).replace("\\", "/").split("/"))
        if os.path.isfile(path):
            return path
    return None


def _normalize_clip(
    src: str,
    dest: str,
    *,
    width: int,
    height: int,
    fps: float,
    ensure_audio: bool,
    min_duration: float | None,
    outro_hold: float,
    allow_freeze_pad: bool = False,
) -> dict:
    """Scale to canvas, force fps. Length-fill via tpad clone is BANNED by default.

    Rule 7.3: do not freeze-pad work clips to match audio — regen longer motion.
    Optional outro_hold (editorial breath) is allowed as explicit short freeze only.
    min_duration > video requires --allow-freeze-pad (debug/emergency).
    """
    has_a = probe_has_audio(src)
    vd = probe_duration(src) or 0.0

    # Audio longer than video → must not silently tpad (freeze pad ban)
    audio_gap = 0.0
    if min_duration and min_duration > vd + 0.05:
        audio_gap = float(min_duration) - vd
        if not allow_freeze_pad:
            return {
                "ok": False,
                "error": "FREEZE_PAD_BANNED",
                "message": (
                    f"video {vd:.2f}s < min_duration/audio {min_duration:.2f}s "
                    f"(gap {audio_gap:.2f}s). Refusing tpad=clone freeze pad. "
                    "Regen longer SI2V/I2V or split dialogue. "
                    "Emergency only: --allow-freeze-pad"
                ),
                "video_sec": vd,
                "min_duration": min_duration,
            }

    target = vd
    if allow_freeze_pad and min_duration and min_duration > target + 0.05:
        target = min_duration
    # Intentional editorial outro hold (last shot breath) — not duration faking mid-cut
    if outro_hold > 0:
        target = target + outro_hold

    # video: scale+pad to exact size; tpad only for allowed outro / emergency pad
    v_filters = [
        f"scale={width}:{height}:force_original_aspect_ratio=decrease",
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black",
        f"fps={fps}",
        "format=yuv420p",
        "setsar=1",
    ]
    pad_v = max(0.0, target - vd)
    if pad_v > 0.05:
        # Only outro_hold (and emergency allow_freeze_pad) should reach here for length
        v_filters.append(f"tpad=stop_mode=clone:stop_duration={pad_v:.3f}")

    vf = ",".join(v_filters)
    # Windows/browser players reject High 4:4:4 / yuv444p — force 420 + high profile
    x264 = ["-c:v", "libx264", "-profile:v", "high", "-level", "4.0", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "18"]

    if has_a:
        # apad to target length
        a_filters = [
            "aformat=sample_rates=48000:channel_layouts=stereo",
            f"apad=whole_dur={target:.3f}",
        ]
        af = ",".join(a_filters)
        args = [
            "-i",
            src,
            "-vf",
            vf,
            "-af",
            af,
            *x264,
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            dest,
        ]
    elif ensure_audio:
        # silent stereo for establishing shots
        args = [
            "-i",
            src,
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=channel_layout=stereo:sample_rate=48000",
            "-vf",
            vf,
            *x264,
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-t",
            f"{target:.3f}",
            "-movflags",
            "+faststart",
            dest,
        ]
    else:
        args = [
            "-i",
            src,
            "-vf",
            vf,
            "-an",
            *x264,
            "-t",
            f"{target:.3f}",
            "-movflags",
            "+faststart",
            dest,
        ]

    r = run_ffmpeg(args, timeout_sec=600)
    if not r.get("ok"):
        return r
    return {"ok": True, "path": dest, "duration": probe_duration(dest)}


def _xfade_chain(
    paths: list[str],
    dest: str,
    *,
    xfade: float,
    fps: float,
) -> dict:
    """Crossfade-join clips for continuous feel. xfade=0 falls back to concat demuxer."""
    if not paths:
        return {"ok": False, "error": "EMPTY", "message": "no clips"}
    if len(paths) == 1 or xfade <= 0.001:
        # concat demuxer
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            for p in paths:
                f.write(f"file '{p.replace(chr(39), chr(39)+chr(39))}'\n")
            list_path = f.name
        try:
            return run_ffmpeg(
                [
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    list_path,
                    "-c",
                    "copy",
                    dest,
                ],
                timeout_sec=600,
            )
        finally:
            try:
                os.unlink(list_path)
            except OSError:
                pass

    durs = [probe_duration(p) or 0.0 for p in paths]
    n = len(paths)
    inputs: list[str] = []
    for p in paths:
        inputs.extend(["-i", p])

    # offset_i = sum(d[0:i]) - i * xfade  (standard multi-xfade chain)
    v_parts: list[str] = []
    a_parts: list[str] = []
    v_label = "[0:v]"
    a_label = "[0:a]"
    for i in range(1, n):
        offset = sum(durs[:i]) - i * xfade
        if offset < 0.05:
            offset = max(0.05, sum(durs[:i]) * 0.5)
        out_v = f"[vx{i}]"
        out_a = f"[ax{i}]"
        v_parts.append(
            f"{v_label}[{i}:v]xfade=transition=fade:duration={xfade:.3f}:offset={offset:.3f}{out_v}"
        )
        a_parts.append(
            f"{a_label}[{i}:a]acrossfade=d={xfade:.3f}:c1=tri:c2=tri{out_a}"
        )
        v_label = out_v
        a_label = out_a

    fc = ";".join(v_parts + a_parts)
    args = [
        *inputs,
        "-filter_complex",
        fc,
        "-map",
        v_label,
        "-map",
        a_label,
        "-c:v",
        "libx264",
        "-profile:v",
        "high",
        "-level",
        "4.0",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-r",
        str(fps),
        "-movflags",
        "+faststart",
        dest,
    ]
    return run_ffmpeg(args, timeout_sec=900)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Single-take style assemble with xfade + outro hold")
    p.add_argument("--episode", "-e", required=True)
    p.add_argument(
        "--xfade",
        type=float,
        default=0.22,
        help="Crossfade seconds between dialogue clips (0=hard cut)",
    )
    p.add_argument(
        "--outro-hold",
        type=float,
        default=1.4,
        help="Freeze last frame + silence after final dialogue (seconds)",
    )
    p.add_argument(
        "--pre-hold",
        type=float,
        default=0.12,
        help="Tiny freeze at end of non-final dialogue clips before xfade (reduces pop)",
    )
    p.add_argument(
        "--allow-freeze-pad",
        action="store_true",
        help=(
            "Emergency: allow tpad=clone when video shorter than TTS/audio. "
            "Default refuses (regen longer clip instead — Rule 7.3)"
        ),
    )
    p.add_argument("--fps", type=float, default=24.0)
    p.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output mp4 (default exports/final/<ep>_single_take.mp4)",
    )
    p.add_argument("--establishing-fade", type=float, default=0.35, help="Fade S01 into body")
    args = p.parse_args(argv)

    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] episode missing: {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    format_id = story.format_id()
    work_preset = story.doc.get("default_work_preset")
    try:
        width, height, _, _ = resolve_work_size(format_id, work_preset)
    except Exception:
        width, height = 544, 960

    shots = sorted(story.shots(), key=lambda s: s.get("order", 0))
    if not shots:
        print("[ERROR] no shots", file=sys.stderr)
        return EXIT_USAGE

    work_dir = story.path("clips", "work", "_single_take")
    os.makedirs(work_dir, exist_ok=True)

    norm_paths: list[str] = []
    meta_shots: list[dict] = []

    for i, shot in enumerate(shots):
        sid = shot["shot_id"]
        src = _resolve_clip(story, shot)
        if not src:
            print(f"[ERROR] missing clip for {sid}", file=sys.stderr)
            return EXIT_MISSING

        # TTS duration for dialogue pad
        min_dur = None
        for tts_rel in (
            f"audio/dialogue/{sid}_qwen3tts.mp3",
            f"audio/dialogue/{sid}.mp3",
            f"audio/dialogue/{sid}.wav",
        ):
            tts_path = story.path(*tts_rel.split("/"))
            if os.path.isfile(tts_path):
                min_dur = probe_duration(tts_path)
                break
        # driving wav as fallback length
        if min_dur is None:
            drive = shot.get("audio_refs") or {}
            dpath = drive.get("driving")
            if dpath:
                dp = story.path(*str(dpath).replace("\\", "/").split("/"))
                if os.path.isfile(dp):
                    min_dur = probe_duration(dp)

        is_last = i == len(shots) - 1
        is_first = i == 0
        # Outro hold only on last shot; small pre-hold on dialogue middles helps continuity
        outro = float(args.outro_hold) if is_last else float(args.pre_hold)
        # Establishing (no dialogue): no min_dur stretch unless short
        dialogue = (shot.get("dialogue") or "").strip()
        if not dialogue:
            min_dur = None
            if not is_last:
                outro = 0.0

        dest = os.path.join(work_dir, f"{sid}_norm.mp4")
        print(
            f"normalize {sid}: src={os.path.basename(src)} "
            f"min_audio={min_dur} outro_hold={outro:.2f}s → {width}x{height}"
        )
        r = _normalize_clip(
            src,
            dest,
            width=width,
            height=height,
            fps=args.fps,
            ensure_audio=True,
            min_duration=min_dur,
            outro_hold=outro,
            allow_freeze_pad=bool(args.allow_freeze_pad),
        )
        if not r.get("ok"):
            print(
                f"[ERROR] normalize {sid}: {r.get('error')} {r.get('message')}",
                file=sys.stderr,
            )
            return EXIT_FFMPEG
        print(f"  OK dur={r.get('duration')}")
        norm_paths.append(dest)
        meta_shots.append(
            {
                "shot_id": sid,
                "src": src,
                "norm": dest,
                "min_audio": min_dur,
                "outro_hold": outro,
                "duration": r.get("duration"),
            }
        )

    out = args.output or story.path(
        "exports", "final", f"{args.episode}_single_take.mp4"
    )
    os.makedirs(os.path.dirname(out), exist_ok=True)

    # Strategy: S01 (establishing) hard/short-fade join, then xfade among rest if multi
    body = norm_paths
    if len(norm_paths) >= 2 and args.establishing_fade > 0 and not (
        shots[0].get("dialogue") or ""
    ).strip():
        # xfade only among dialogue body if first is establishing
        head = norm_paths[0]
        tail = norm_paths[1:]
        body_out = os.path.join(work_dir, "body_xfade.mp4")
        print(f"xfade body n={len(tail)} d={args.xfade}s")
        r = _xfade_chain(tail, body_out, xfade=args.xfade, fps=args.fps)
        if not r.get("ok"):
            print(f"[ERROR] xfade body: {r.get('error')} {r.get('message')}", file=sys.stderr)
            return EXIT_FFMPEG
        # join head + body with short xfade
        print(f"join establishing fade={args.establishing_fade}s")
        r2 = _xfade_chain(
            [head, body_out],
            out,
            xfade=float(args.establishing_fade),
            fps=args.fps,
        )
        if not r2.get("ok"):
            print(f"[ERROR] join head: {r2.get('error')} {r2.get('message')}", file=sys.stderr)
            return EXIT_FFMPEG
    else:
        print(f"xfade all n={len(body)} d={args.xfade}s")
        r = _xfade_chain(body, out, xfade=args.xfade, fps=args.fps)
        if not r.get("ok"):
            print(f"[ERROR] xfade: {r.get('error')} {r.get('message')}", file=sys.stderr)
            return EXIT_FFMPEG

    final_dur = probe_duration(out)
    meta = {
        "tool": "assemble_single_take",
        "episode_id": args.episode,
        "output": os.path.abspath(out),
        "width": width,
        "height": height,
        "fps": args.fps,
        "xfade": args.xfade,
        "outro_hold": args.outro_hold,
        "pre_hold": args.pre_hold,
        "establishing_fade": args.establishing_fade,
        "final_duration": final_dur,
        "shots": meta_shots,
        "notes": [
            "Crossfades improve continuous seating feel; not a substitute for FLF2V.",
            "Outro freeze hold prevents dialogue-end = hard video cut.",
            "Audio pad to TTS length prevents chopped last syllables.",
        ],
    }
    meta_path = story.path("meta", f"{args.episode}_single_take.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # also copy as main final for convenience
    main_final = story.path("exports", "final", f"{args.episode}_final.mp4")
    try:
        import shutil

        shutil.copy2(out, main_final)
    except Exception as e:
        print(f"[WARN] copy main final failed: {e}")

    print(f"OK single_take={out}")
    print(f"  duration={final_dur}s canvas={width}x{height}")
    print(f"  meta={meta_path}")
    print(f"  also={main_final}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
