#!/usr/bin/env python3
"""Assemble episode clips (and audio stems per mix_policy) into a final mp4 via FFmpeg."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys
import tempfile

import shutil

from lib.audio_package import (
    audio_readiness,
    audio_section,
    collect_simple_stems,
    collect_timeline_events,
    ensure_audio_dirs,
    normalize_production_mode,
    resolve_mix_policy,
    shot_motion_driver,
)
from lib.comfy_client import utc_now_iso, write_meta
from lib.ffmpeg_util import (
    concat_videos,
    find_ffmpeg,
    mix_audio_under_video,
    mix_bgm_keep_video_audio,
    mix_timeline_under_video,
    normalize_clip,
    probe_duration,
    probe_has_audio,
)
from lib.story_package import StoryPackage, validate_episode_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_NONE = 21
EXIT_CLIP_GATE = 22
EXIT_FFMPEG = 40
EXIT_AUDIO = 41


def _clip_path(story: StoryPackage, shot: dict, stage: str) -> str | None:
    """Resolve best clip path for stage: deliver | work | auto."""
    sid = shot.get("shot_id")
    deliver_rel = shot.get("clip_deliver") or f"clips/deliver/{sid}.mp4"
    deliver = story.path(*deliver_rel.replace("\\", "/").split("/"))

    work_candidates: list[str] = []
    for rel in (
        shot.get("clip_work_s2v"),
        shot.get("clip_work"),
        f"clips/work/{sid}_s2v.mp4",
        f"clips/work/{sid}.mp4",
    ):
        if not rel:
            continue
        p = story.path(*str(rel).replace("\\", "/").split("/"))
        if p not in work_candidates:
            work_candidates.append(p)
    work = next((p for p in work_candidates if os.path.isfile(p)), None)

    if stage == "deliver":
        return deliver if os.path.isfile(deliver) else None
    if stage == "work":
        return work
    if os.path.isfile(deliver):
        return deliver
    return work


def _default_bgm(story: StoryPackage) -> str | None:
    music_dir = story.path("audio", "music")
    if not os.path.isdir(music_dir):
        return None
    for name in sorted(os.listdir(music_dir)):
        low = name.lower()
        if low.endswith((".mp3", ".wav", ".m4a", ".aac", ".flac")):
            return os.path.join(music_dir, name)
    return None


def _probe_duration(path: str) -> float | None:
    try:
        import json
        import subprocess

        out = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                path,
            ],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=30,
        )
        return float(json.loads(out)["format"]["duration"])
    except Exception:
        return None


def _tracks_for_policy(
    policy: str,
    stems: dict,
    *,
    force_bgm: str | None,
    bgm_volume: float | None,
) -> tuple[list[dict], str]:
    """Return flat tracks (no timeline). Empty → try timeline or video only."""
    vols = stems.get("volumes") or {}
    bv = float(bgm_volume if bgm_volume is not None else vols.get("bgm") or 0.35)

    if policy == "video_only":
        return [], "video_only"

    if policy in ("music_locked", "bgm_under"):
        path = force_bgm or stems.get("master") or stems.get("bgm")
        if not path:
            return [], f"{policy}: no master/bgm found"
        vol = 1.0 if policy == "music_locked" else bv
        role = "master" if policy == "music_locked" else "bgm"
        return [{"path": path, "volume": vol, "role": role}], policy

    if policy == "dialogue_sfx_first_bgm_late":
        tracks: list[dict] = []
        for p in stems.get("dialogue") or []:
            tracks.append(
                {"path": p, "volume": float(vols.get("dialogue") or 1.0), "role": "dialogue"}
            )
        for p in stems.get("vo") or []:
            tracks.append({"path": p, "volume": float(vols.get("vo") or 1.0), "role": "vo"})
        for p in stems.get("sfx") or []:
            tracks.append({"path": p, "volume": float(vols.get("sfx") or 0.85), "role": "sfx"})
        bgm = force_bgm or stems.get("bgm")
        if bgm:
            tracks.append({"path": bgm, "volume": bv, "role": "bgm"})
        if not tracks:
            return [], f"{policy}: no flat stems — try timeline/refs"
        return tracks, policy

    if policy == "layered":
        return [], "layered_uses_timeline"

    path = force_bgm or stems.get("bgm") or stems.get("master")
    if path:
        return [{"path": path, "volume": bv, "role": "bgm"}], "fallback_bgm"
    return [], "unknown_policy_video_only"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="FFmpeg-assemble episode clips + audio stems (mix_policy)"
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
        "--mix-policy",
        default=None,
        help="Override episode mix_policy (video_only|music_locked|bgm_under|dialogue_sfx_first_bgm_late|layered)",
    )
    parser.add_argument(
        "--bgm",
        default=None,
        help="Force music/BGM path (also used as master for music_locked)",
    )
    parser.add_argument(
        "--no-audio",
        action="store_true",
        help="Force video_only (alias of --mix-policy video_only)",
    )
    parser.add_argument(
        "--no-bgm",
        action="store_true",
        help="Deprecated alias for --no-audio",
    )
    parser.add_argument(
        "--bgm-volume",
        type=float,
        default=None,
        help="BGM/master volume override",
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
    parser.add_argument(
        "--require-audio",
        action="store_true",
        help="Fail if mix_policy needs audio but stems missing",
    )
    parser.add_argument(
        "--subs",
        action="store_true",
        help="After assemble: write SRT and soft-burn to <final>_subs.mp4 (P2-2)",
    )
    parser.add_argument(
        "--force-clip-gate",
        action="store_true",
        help=(
            "Skip clip_status hard gate (debug/preview only). "
            "Deliver path must NOT use this — Rule 7.2"
        ),
    )
    args = parser.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] code=2 invalid episode id", file=sys.stderr)
        return EXIT_USAGE

    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] code=11 episode missing", file=sys.stderr)
        return EXIT_MISSING

    ensure_audio_dirs(story.root)

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

    clips: list[tuple[str, str]] = []
    selected_with_clip: list[dict] = []
    for s in selected:
        path = _clip_path(story, s, args.stage)
        if path:
            clips.append((s.get("shot_id") or "?", path))
            selected_with_clip.append(s)
        else:
            print(f"[WARN] skip {s.get('shot_id')}: no {args.stage} clip")

    if not clips:
        print("[ERROR] code=21 no clips to assemble", file=sys.stderr)
        return EXIT_NONE

    # Rule 7.2: hard gate — every clip in the assemble list must be clip_status approved
    if not args.force_clip_gate:
        from lib.episode_status import CLIP_STATUS_OK, normalize_clip_status

        gate_fail: list[str] = []
        for s in selected_with_clip:
            sid = s.get("shot_id") or "?"
            st = normalize_clip_status(s, work_ok=True)
            if st not in CLIP_STATUS_OK:
                gate_fail.append(f"{sid}:clip_status={st or 'pending'}")
        if gate_fail:
            print(
                "[ERROR] code=22 CLIP_NOT_APPROVED — assemble blocked until per-cut review",
                file=sys.stderr,
            )
            for line in gate_fail:
                print(f"  - {line}", file=sys.stderr)
            print(
                "  Fix: watch each clips/work clip, then:\n"
                "    python scripts/shot_approve.py -e "
                f"{args.episode} -s <SHOT> --clip approved\n"
                "  Debug-only bypass: --force-clip-gate (forbidden on deliver path)",
                file=sys.stderr,
            )
            return EXIT_CLIP_GATE
    else:
        print(
            "[WARN] --force-clip-gate: skipping clip_status check (not for deliver)"
        )

    out = args.output or story.path("exports", "final", f"{args.episode}_final.mp4")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)

    if args.no_audio or args.no_bgm:
        policy = "video_only"
    elif args.mix_policy:
        policy = args.mix_policy.strip()
    else:
        policy = resolve_mix_policy(story.doc)

    mode = normalize_production_mode(story.doc.get("production_mode"))

    # Resolve stems without permanently mutating shots.json
    doc_for_audio = dict(story.doc)
    if args.bgm:
        audio_ov = dict(doc_for_audio.get("audio") or {})
        audio_ov["master"] = args.bgm
        audio_ov["bgm"] = args.bgm
        doc_for_audio["audio"] = audio_ov
    if args.mix_policy:
        doc_for_audio["mix_policy"] = policy

    stems = collect_simple_stems(story.root, doc_for_audio)
    readiness = audio_readiness(story.root, doc_for_audio)

    sec = audio_section(doc_for_audio)
    bgm_vol = args.bgm_volume if args.bgm_volume is not None else float(sec.get("bgm_volume") or 0.35)
    if policy == "music_locked" and args.bgm_volume is None:
        bgm_vol = float(sec.get("master_volume") if sec.get("master_volume") is not None else 1.0)

    # actual clip durations for timeline offsets
    shot_durs: dict[str, float] = {}
    for sid, p in clips:
        d = _probe_duration(p)
        if d:
            shot_durs[sid] = d

    tracks, track_note = _tracks_for_policy(
        policy,
        stems,
        force_bgm=args.bgm,
        bgm_volume=bgm_vol,
    )

    timeline_events: list[dict] = []
    use_timeline = policy == "layered"
    if policy == "dialogue_sfx_first_bgm_late" and not tracks:
        use_timeline = True
    if use_timeline:
        timeline_events = collect_timeline_events(
            story.root,
            doc_for_audio,
            shot_durations=shot_durs or None,
            include_episode_bgm=True,
        )
        if args.bgm and not any(e.get("role") in ("master", "bgm") for e in timeline_events):
            timeline_events.insert(
                0,
                {
                    "path": args.bgm,
                    "timeline_start_sec": 0.0,
                    "source_start_sec": 0.0,
                    "source_end_sec": None,
                    "volume": bgm_vol,
                    "role": "bgm",
                    "shot_id": None,
                },
            )
        track_note = f"layered events={len(timeline_events)}"

    has_audio = bool(tracks) or bool(timeline_events)
    if args.require_audio and policy != "video_only" and not has_audio:
        print(
            f"[ERROR] code=41 audio required for mix_policy={policy}: {track_note}",
            file=sys.stderr,
        )
        return EXIT_AUDIO

    print(f"assemble_video episode={args.episode} stage={args.stage}")
    print(f"  production_mode={mode} mix_policy={policy}")
    print(f"  ffmpeg={ff}")
    print(f"  clips={len(clips)}")
    for sid, p in clips:
        print(f"    {sid}: {p} dur={shot_durs.get(sid, '?')}")
    print(f"  out={out}")
    print(f"  audio_note={track_note}")
    if timeline_events:
        for e in timeline_events:
            print(
                f"    event t={e.get('timeline_start_sec')} role={e.get('role')} "
                f"vol={e.get('volume')} {e.get('path')}"
            )
    elif tracks:
        for t in tracks:
            print(f"    track role={t['role']} vol={t['volume']} {t['path']}")
    else:
        print("  audio=(none — video only)")
    if readiness.get("missing"):
        print(f"  [WARN] readiness: {readiness['missing']}")

    if args.dry_run:
        print("[dry-run] skip ffmpeg")
        return EXIT_OK

    # Prefer per-shot audio bake when SI2V clips exist or layered story mix:
    # - keep lip-synced audio embedded in *_s2v.mp4
    # - VO/dialogue stems only for shots without clip audio, clipped to shot length
    # - never stack full stems from t=0 (that caused VO/dialogue overlap)
    # - BGM mixed under final while preserving speech
    use_bake = policy != "video_only" and (
        policy in ("layered", "dialogue_sfx_first_bgm_late")
        or any(shot_motion_driver(s, story.doc) == "si2v" for s in selected)
        or any(probe_has_audio(p) for _, p in clips)
    )

    if use_bake and not args.copy:
        tmp_dir = tempfile.mkdtemp(prefix="assemble_bake_")
        baked: list[str] = []
        tmp_video = None
        try:
            target_fps = float(args.fps or 25)
            tw, th = 960, 544
            for s in selected:
                ws = s.get("work_size") or {}
                if ws.get("width") and ws.get("height"):
                    tw, th = int(ws["width"]), int(ws["height"])
                    break

            for s in selected:
                sid = s.get("shot_id") or "?"
                src = _clip_path(story, s, args.stage)
                if not src:
                    continue
                dst = os.path.join(tmp_dir, f"{sid}.mp4")
                driver = shot_motion_driver(s, story.doc)
                refs = s.get("audio_refs") if isinstance(s.get("audio_refs"), dict) else {}
                clip_dur = probe_duration(src) or float(s.get("duration_sec") or 4.0)

                ext_audio = None
                keep_va = False
                # Per-shot stems only (never stack all dialogue from t=0).
                # SI2V: prefer driving (prep used at gen) then dialogue TTS; never VO.
                # Non-SI2V: vo then dialogue; never driving.
                stem_order = (
                    ("driving", "dialogue")
                    if driver == "si2v"
                    else ("vo", "dialogue")
                )
                for key in stem_order:
                    item = refs.get(key)
                    if isinstance(item, dict) and item.get("path"):
                        cand = story.path(
                            *str(item["path"]).replace("\\", "/").split("/")
                        )
                        if os.path.isfile(cand):
                            ext_audio = cand
                            print(
                                f"  bake {sid}: stem {key} "
                                f"(trim≤{clip_dur:.2f}s; "
                                f"{'lip-matched' if driver == 'si2v' else 'no spill'})"
                            )
                            break
                if ext_audio is None and probe_has_audio(src):
                    keep_va = True
                    print(f"  bake {sid}: keep existing clip audio (fallback)")
                elif ext_audio is None:
                    print(f"  bake {sid}: silence")

                r_n = normalize_clip(
                    src,
                    dst,
                    width=tw,
                    height=th,
                    fps=target_fps,
                    audio_path=ext_audio,
                    audio_volume=1.0,
                    keep_video_audio=keep_va,
                    max_audio_sec=clip_dur if ext_audio else None,
                    timeout_sec=args.timeout,
                )
                if not r_n.get("ok"):
                    print(
                        f"[ERROR] bake {sid} {r_n.get('error')}: {r_n.get('message')}",
                        file=sys.stderr,
                    )
                    return EXIT_FFMPEG
                baked.append(dst)

            if not baked:
                print("[ERROR] code=21 no clips to bake", file=sys.stderr)
                return EXIT_NONE

            bgm_path = args.bgm or stems.get("bgm") or stems.get("master")
            need_bgm = bool(
                policy != "video_only"
                and bgm_path
                and os.path.isfile(str(bgm_path))
            )
            fd, tmp_video = tempfile.mkstemp(suffix=".mp4", prefix="assemble_vid_")
            os.close(fd)

            # Always re-encode concat of baked clips — stream-copy concat of
            # per-shot AAC can drop/mute later segments' dialogue on some builds.
            r1 = concat_videos(
                baked,
                tmp_video,
                reencode=True,
                fps=int(target_fps),
                width=tw,
                height=th,
                timeout_sec=args.timeout,
            )
            if not r1.get("ok"):
                print(
                    f"[ERROR] concat {r1.get('error')}: {r1.get('message')}",
                    file=sys.stderr,
                )
                return EXIT_FFMPEG

            if need_bgm:
                r2 = mix_bgm_keep_video_audio(
                    tmp_video,
                    str(bgm_path),
                    out,
                    bgm_volume=bgm_vol,
                    video_audio_volume=1.0,
                    timeout_sec=args.timeout,
                )
                if not r2.get("ok"):
                    print(
                        f"[ERROR] bgm mix {r2.get('error')}: {r2.get('message')}",
                        file=sys.stderr,
                    )
                    return EXIT_FFMPEG
                track_note = f"bake+bgm keep_speech vol={bgm_vol}"
            else:
                shutil.copy2(tmp_video, out)
                track_note = "bake speech only (no bgm)"
            print(f"  audio_note={track_note}")
        finally:
            if tmp_video:
                try:
                    os.remove(tmp_video)
                except OSError:
                    pass
            shutil.rmtree(tmp_dir, ignore_errors=True)

    elif has_audio:
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
            if timeline_events:
                r2 = mix_timeline_under_video(
                    tmp_video,
                    out,
                    events=timeline_events,
                    timeout_sec=args.timeout,
                )
            else:
                r2 = mix_audio_under_video(
                    tmp_video,
                    out,
                    tracks=tracks,
                    timeout_sec=args.timeout,
                )
            if not r2.get("ok"):
                print(f"[ERROR] mix {r2.get('error')}: {r2.get('message')}", file=sys.stderr)
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
        "production_mode": mode,
        "mix_policy": policy,
        "clips": [{"shot_id": sid, "path": os.path.abspath(p)} for sid, p in clips],
        "tracks": [
            {
                "role": t["role"],
                "volume": t["volume"],
                "path": os.path.abspath(t["path"]),
            }
            for t in tracks
        ],
        "timeline_events": [
            {
                "role": e.get("role"),
                "timeline_start_sec": e.get("timeline_start_sec"),
                "source_start_sec": e.get("source_start_sec"),
                "source_end_sec": e.get("source_end_sec"),
                "volume": e.get("volume"),
                "path": os.path.abspath(e["path"]) if e.get("path") else None,
                "shot_id": e.get("shot_id"),
            }
            for e in timeline_events
        ],
        "audio_note": track_note,
        "output_path": os.path.abspath(out),
        "reencode": not args.copy,
        "created_at": utc_now_iso(),
    }
    meta_path = args.meta_out or story.path("meta", f"{args.episode}_assemble.json")
    write_meta(meta_path, meta)

    story.doc["final_export"] = {
        "path": os.path.relpath(out, story.root).replace("\\", "/"),
        "assembled_at": utc_now_iso(),
        "clip_count": len(clips),
        "mix_policy": policy,
        "production_mode": mode,
        "has_audio": has_audio,
    }
    story.save()

    print(f"OK final={out}")
    print(f"  meta={meta_path}")
    print(f"  has_audio={has_audio}")

    if args.subs and not args.dry_run:
        try:
            from lib.subtitles import burn_subtitles, write_episode_srt

            srt_r = write_episode_srt(story)
            print(f"  srt={srt_r.get('path')} cues={srt_r.get('cue_count')}")
            root, ext = os.path.splitext(out)
            subs_out = f"{root}_subs{ext or '.mp4'}"
            br = burn_subtitles(out, srt_r["path"], subs_out)
            if br.get("ok"):
                print(f"  subs_burned={br.get('output_path') or subs_out}")
            else:
                print(
                    f"[WARN] subs burn failed: {br.get('error')} {br.get('message')}",
                    file=sys.stderr,
                )
        except Exception as e:
            print(f"[WARN] --subs failed: {e}", file=sys.stderr)

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
