#!/usr/bin/env python3
"""
Post-run QA for episode AV — fail loud so agents do not ship silent/spill/aspect junk.

Checks:
  - work clips exist for approved shots
  - SI2V shots have driving audio refs
  - per-clip aspect roughly matches episode format work size
  - audio spill risk (stem longer than shot)
  - final export optional has audio + non-silent mean volume
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys

from lib.audio_package import (
    check_stem_fits_shot,
    find_bgm,
    resolve_driving_audio,
    shot_motion_driver,
)
from lib.comfy_client import utc_now_iso, write_meta
from lib.ffmpeg_util import probe_duration, probe_has_audio
from lib.story_package import StoryPackage, validate_episode_id
from lib.video_backends import get_preset, load_video_backends, resolve_s2v_backend

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_QA = 42


def _probe_mean_db(path: str) -> float | None:
    try:
        import re
        import shutil
        import subprocess

        ff = shutil.which("ffmpeg") or "ffmpeg"
        proc = subprocess.run(
            [ff, "-hide_banner", "-i", path, "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        log = (proc.stderr or "") + (proc.stdout or "")
        m = re.search(r"mean_volume:\s*([-\d.]+)\s*dB", log)
        return float(m.group(1)) if m else None
    except Exception:
        return None


def _expected_work_size(story: StoryPackage) -> tuple[int, int]:
    cfg = load_video_backends()
    preset_id = story.doc.get("default_work_preset") or cfg.get("default_work_preset")
    try:
        pr = get_preset(str(preset_id), cfg)
        return int(pr["width"]), int(pr["height"])
    except Exception:
        return 960, 544


def run_episode_qa(
    episode_id: str,
    *,
    strict: bool = True,
    check_final: bool = True,
) -> dict:
    story = StoryPackage.load(episode_id)
    exp_w, exp_h = _expected_work_size(story)
    issues: list[dict] = []
    shots_out: list[dict] = []

    try:
        s2v_default = resolve_s2v_backend(None, episode_doc=story.doc)
    except Exception as e:
        s2v_default = f"error:{e}"

    for shot in sorted(story.shots(), key=lambda s: s.get("order", 0)):
        sid = shot.get("shot_id") or "?"
        driver = shot_motion_driver(shot, story.doc)
        entry: dict = {
            "shot_id": sid,
            "driver": driver,
            "keyframe_status": shot.get("keyframe_status"),
        }
        if shot.get("keyframe_status") != "approved":
            entry["skip"] = "not_approved"
            shots_out.append(entry)
            continue

        work_rel = shot.get("clip_work_s2v") or shot.get("clip_work")
        if not work_rel:
            work_rel = (
                f"clips/work/{sid}_s2v.mp4"
                if driver == "si2v"
                else f"clips/work/{sid}.mp4"
            )
        work_path = story.path(*str(work_rel).replace("\\", "/").split("/"))
        entry["work_path"] = work_path
        entry["work_exists"] = os.path.isfile(work_path)

        if not entry["work_exists"]:
            issues.append(
                {
                    "code": "MISSING_WORK_CLIP",
                    "shot_id": sid,
                    "message": f"missing {work_rel}",
                }
            )
            shots_out.append(entry)
            continue

        dur = probe_duration(work_path)
        entry["duration"] = dur
        has_a = probe_has_audio(work_path)
        entry["has_audio"] = has_a

        # aspect: allow pad (letterbox) — check via ffprobe width/height if possible
        try:
            import json as _json
            import shutil
            import subprocess

            ffprobe = shutil.which("ffprobe") or "ffprobe"
            raw = subprocess.check_output(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=width,height",
                    "-of",
                    "json",
                    work_path,
                ],
                text=True,
                timeout=30,
            )
            st = (_json.loads(raw).get("streams") or [{}])[0]
            w, h = int(st.get("width") or 0), int(st.get("height") or 0)
            entry["width"], entry["height"] = w, h
            # square SI2V is a format warning (agent should prefer work aspect)
            if w and h and abs(w / h - exp_w / exp_h) > 0.08:
                issues.append(
                    {
                        "code": "ASPECT_MISMATCH",
                        "shot_id": sid,
                        "message": (
                            f"clip {w}x{h} vs work {exp_w}x{exp_h} "
                            f"(expect format-consistent SI2V/I2V; avoid square default)"
                        ),
                        "severity": "warning",
                    }
                )
                entry["aspect_ok"] = False
            else:
                entry["aspect_ok"] = True
        except Exception:
            entry["aspect_ok"] = None

        if driver == "si2v":
            if resolve_driving_audio(story.root, shot) is None:
                issues.append(
                    {
                        "code": "SI2V_NO_DRIVING",
                        "shot_id": sid,
                        "message": "motion_driver=si2v but no audio_refs.driving|dialogue",
                    }
                )
            # prefer speech present on work clip or will be baked at assemble
            refs = shot.get("audio_refs") if isinstance(shot.get("audio_refs"), dict) else {}
            for key in ("driving", "dialogue", "vo"):
                item = refs.get(key)
                if not isinstance(item, dict) or not item.get("path"):
                    continue
                ap = story.path(*str(item["path"]).replace("\\", "/").split("/"))
                if not os.path.isfile(ap):
                    continue
                shot_d = float(shot.get("duration_sec") or dur or 4.0)
                fit = check_stem_fits_shot(ap, shot_d)
                entry["stem_fit"] = fit
                if not fit.get("ok"):
                    issues.append(
                        {
                            "code": "AUDIO_SPILL",
                            "shot_id": sid,
                            "message": fit.get("message"),
                        }
                    )
                break

        shots_out.append(entry)

    bgm = find_bgm(story.root, story.doc)
    final_rel = f"exports/final/{episode_id}_av_final.mp4"
    # also accept work_final naming from smoke
    final_candidates = [
        story.path("exports", "final", f"{episode_id}_av_final.mp4"),
        story.path("exports", "final", f"{episode_id}_work_final.mp4"),
        story.path("exports", "final", f"{episode_id}_final.mp4"),
    ]
    final_path = next((p for p in final_candidates if os.path.isfile(p)), None)
    final_info: dict = {"path": final_path, "exists": bool(final_path)}
    if check_final and final_path:
        final_info["duration"] = probe_duration(final_path)
        final_info["has_audio"] = probe_has_audio(final_path)
        mean_db = _probe_mean_db(final_path)
        final_info["mean_db"] = mean_db
        if not final_info["has_audio"]:
            issues.append(
                {
                    "code": "FINAL_NO_AUDIO",
                    "message": f"final has no audio track: {final_path}",
                }
            )
        elif mean_db is not None and mean_db < -45.0:
            issues.append(
                {
                    "code": "FINAL_NEAR_SILENT",
                    "message": f"final mean_volume={mean_db} dB looks silent",
                }
            )

    hard = [i for i in issues if i.get("severity") != "warning"]
    warnings = [i for i in issues if i.get("severity") == "warning"]
    ok = len(hard) == 0 if strict else True
    if not strict and hard:
        # still ok=false for hard issues when reporting; caller uses exit code
        ok = False

    report = {
        "ok": ok and len(hard) == 0,
        "episode_id": episode_id,
        "default_backend_s2v": s2v_default,
        "expected_work_size": {"width": exp_w, "height": exp_h},
        "bgm": bgm,
        "shots": shots_out,
        "final": final_info,
        "issues": hard,
        "warnings": warnings,
        "created_at": utc_now_iso(),
    }
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Episode AV QA (agent fail-loud gate)")
    p.add_argument("--episode", "-e", required=True)
    p.add_argument(
        "--strict",
        action="store_true",
        default=True,
        help="Non-zero exit on hard issues (default)",
    )
    p.add_argument(
        "--no-strict",
        dest="strict",
        action="store_false",
        help="Report only (always exit 0 unless missing episode)",
    )
    p.add_argument("--no-final", action="store_true", help="Skip final export checks")
    p.add_argument("--json", action="store_true", help="Print full JSON report")
    args = p.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] code=2 bad episode id", file=sys.stderr)
        return EXIT_USAGE
    try:
        report = run_episode_qa(
            args.episode,
            strict=args.strict,
            check_final=not args.no_final,
        )
    except FileNotFoundError:
        print(f"[ERROR] code=11 episode missing: {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    meta_path = StoryPackage.load(args.episode).path("meta", "episode_qa.json")
    write_meta(meta_path, report)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"episode_qa episode={args.episode} ok={report['ok']}")
        print(f"  s2v_default={report.get('default_backend_s2v')}")
        print(
            f"  work_size={report['expected_work_size']['width']}x"
            f"{report['expected_work_size']['height']}"
        )
        print(f"  bgm={report.get('bgm')}")
        print(f"  final={report.get('final')}")
        for i in report.get("issues") or []:
            print(f"  [ISSUE] {i.get('code')}: {i.get('message')} shot={i.get('shot_id')}")
        for w in report.get("warnings") or []:
            print(f"  [WARN] {w.get('code')}: {w.get('message')} shot={w.get('shot_id')}")
        print(f"  meta={meta_path}")

    if args.strict and not report["ok"]:
        return EXIT_QA
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
