#!/usr/bin/env python3
"""One-line EDIT: clips + title + look + mix → master (not concat).

  python scripts/edit_pack.py -i a.mp4 -i b.mp4 --xfade 0.25 \\
    --text "포기하지 마" --font yeonung --motion pop --stagger 0.06 --look night \\
    --audio bed.wav --vo line.wav \\
    -o "%AGENT_WORKSPACE%/edits/s01/master.mp4" --qa
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys

from lib.comfy_client import fail_result, ok_result
from lib.edit_compile_ffmpeg import compile_ffmpeg
from lib.edit_motion import load_glyphs
from lib.edit_pack import (
    attach_mix,
    build_pack,
    build_title_overlays,
    pack_duration,
    plan_warning,
    refuse_frozen_clips,
    resolve_title_window,
    sidecar_paths,
    title_kind,
)
from lib.edit_timeline import save_timeline, validate_timeline
from lib.edit_title import render_title
from lib.ffmpeg_util import run_ffmpeg
from lib.output_policy import die_if_toolbox


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="클립+자막+룩을 한 줄로 마스터. concat/assemble_video 납품 금지.",
    )
    p.add_argument("--input", "-i", action="append", default=[], dest="inputs")
    p.add_argument("--output", "-o", required=True)
    p.add_argument("--xfade", type=float, default=0.25)
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--fps", type=int, default=24)

    p.add_argument("--text", default=None)
    p.add_argument("--subtext", default="")
    p.add_argument("--preset", default=None)
    p.add_argument("--layout", default=None)
    p.add_argument("--color", default=None)
    p.add_argument("--outline", default=None)
    p.add_argument("--outline-width", type=int, default=None)
    p.add_argument("--size", default=None)
    p.add_argument("--weight", default=None)
    p.add_argument("--tilt", type=float, default=None)
    p.add_argument("--box", default=None)
    p.add_argument("--bubble", default=None)
    p.add_argument("--bar", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--react-color", default=None)
    p.add_argument("--x", type=float, default=None)
    p.add_argument("--y", type=float, default=None)
    p.add_argument("--font", default=None)
    p.add_argument("--title-start", type=float, default=None)
    p.add_argument("--title-end", type=float, default=None)

    p.add_argument("--motion", default=None, help="pop|fade|slide_up|… (text 있으면 기본 pop)")
    p.add_argument("--fade-in", type=float, default=None)
    p.add_argument("--fade-out", type=float, default=None)
    p.add_argument("--move", type=float, default=None)
    p.add_argument("--scale-from", type=float, default=None)
    p.add_argument("--scale-to", type=float, default=None)
    p.add_argument("--direction", default=None)
    p.add_argument("--distance", type=float, default=None)
    p.add_argument("--dx", type=float, default=None)
    p.add_argument("--dy", type=float, default=None)
    p.add_argument("--stagger", type=float, default=None, help="letter delay seconds; implies --split glyphs")

    p.add_argument("--look", default=None, help="punch|night|warm|cool|soft|bleach|none")
    p.add_argument("--contrast", type=float, default=None)
    p.add_argument("--saturation", type=float, default=None)
    p.add_argument("--brightness", type=float, default=None)
    p.add_argument("--gamma", type=float, default=None)
    p.add_argument("--temperature", type=float, default=None)
    p.add_argument("--amount", type=float, default=None)
    p.add_argument("--lut", default=None)

    p.add_argument("--audio", default=None, help="bed / master music (wav/mp3/mp4)")
    p.add_argument("--vo", default=None, help="voice-over; ducks --audio when both set")
    p.add_argument("--duck", type=float, default=None, help="bed duck amount when VO present (default 0.28)")
    p.add_argument("--audio-fade-in", type=float, default=None)
    p.add_argument("--audio-fade-out", type=float, default=None)
    p.add_argument("--audio-volume", type=float, default=None)
    p.add_argument("--vo-volume", type=float, default=None)
    p.add_argument("--vo-start", type=float, default=0.0)

    p.add_argument("--qa", action="store_true")
    p.add_argument("--timeline-only", action="store_true", help="write timeline (+ title PNG), skip ffmpeg")
    p.add_argument("--print-graph", action="store_true")
    p.add_argument("--allow-freeze", action="store_true", help="intentional still / debug only")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    if not args.inputs:
        p.error("provide at least one -i clip")
    if args.stagger is not None and not args.text:
        p.error("--stagger requires --text")
    if args.qa and args.timeline_only:
        p.error("--qa needs a rendered master (drop --timeline-only)")

    try:
        die_if_toolbox(args.output)
    except SystemExit as e:
        return int(e.code or 14)

    paths = sidecar_paths(args.output)
    try:
        die_if_toolbox(paths["timeline"])
    except SystemExit as e:
        return int(e.code or 14)

    try:
        tl = build_pack(
            args.inputs,
            xfade=args.xfade,
            width=args.width,
            height=args.height,
            fps=args.fps,
            look=args.look,
            contrast=args.contrast,
            saturation=args.saturation,
            brightness=args.brightness,
            gamma=args.gamma,
            temperature=args.temperature,
            amount=args.amount,
            lut=args.lut,
        )
        title_res = None
        overlays: list = []
        if args.text:
            split = "glyphs" if args.stagger is not None else None
            title_res = render_title(
                args.text,
                paths["title"],
                preset=args.preset,
                width=args.width,
                height=args.height,
                subtext=args.subtext,
                font=args.font,
                color=args.color,
                outline=args.outline,
                outline_width=args.outline_width,
                size=args.size,
                tilt=args.tilt,
                layout=args.layout,
                weight=args.weight,
                box=args.box,
                bubble=args.bubble,
                bar=args.bar,
                react_color=args.react_color,
                x=args.x,
                y=args.y,
                split=split,
            )
            if not title_res.get("ok"):
                if args.json:
                    print(json.dumps(title_res, indent=2, ensure_ascii=False))
                else:
                    print(
                        f"[FAILED] {title_res.get('error')}: {title_res.get('message')}",
                        file=sys.stderr,
                    )
                return 1
            start, end = resolve_title_window(
                pack_duration(tl),
                start=args.title_start,
                end=args.title_end,
            )
            glyphs = None
            if args.stagger is not None:
                gpath = title_res.get("glyphs") or paths["glyphs"]
                glyphs = load_glyphs(gpath)
            motion = args.motion if args.motion is not None else "pop"
            overlays = build_title_overlays(
                path=title_res["path"],
                text=args.text,
                start=start,
                end=end,
                motion=motion,
                kind=title_kind(title_res.get("layout") or args.layout),
                stagger=args.stagger,
                glyphs=glyphs,
                fade_in=args.fade_in,
                fade_out=args.fade_out,
                move=args.move,
                scale_from=args.scale_from,
                scale_to=args.scale_to,
                direction=args.direction,
                distance=args.distance,
                dx=args.dx,
                dy=args.dy,
            )
            tl.setdefault("overlays", []).extend(overlays)
            tl = validate_timeline(tl)
        if args.audio or args.vo:
            tl = attach_mix(
                tl,
                audio=args.audio,
                vo=args.vo,
                duck=args.duck,
                fade_in=args.audio_fade_in,
                fade_out=args.audio_fade_out,
                audio_volume=args.audio_volume,
                vo_volume=args.vo_volume,
                vo_start=args.vo_start,
            )
        timeline_path = save_timeline(tl, paths["timeline"])
    except Exception as e:
        res = fail_result(error="PACK_INVALID", message=str(e), tool="edit_pack")
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    warn = plan_warning(args.output)
    duration = pack_duration(tl)

    if not args.timeline_only and not args.print_graph:
        sample_root = os.path.join(os.path.dirname(paths["master"]), "_freeze_qa")
        freeze = refuse_frozen_clips(
            tl,
            timeline_path=timeline_path,
            allow_freeze=args.allow_freeze,
            sample_root=sample_root,
        )
        if not freeze.get("ok"):
            res = fail_result(
                error=freeze.get("error") or "FREEZE_PAD_SUSPECT",
                message=freeze.get("message"),
                tool="edit_pack",
                hits=freeze.get("hits"),
            )
            if args.json:
                print(json.dumps(res, indent=2, ensure_ascii=False))
            else:
                print(f"[FAILED] {res.get('error')} {res.get('message')}", file=sys.stderr)
            return 1

    if args.timeline_only or args.print_graph:
        spec = None
        if args.print_graph:
            try:
                spec = compile_ffmpeg(tl, args.output, timeline_path=timeline_path)
            except Exception as e:
                res = fail_result(error="TIMELINE_INVALID", message=str(e), tool="edit_pack")
                if args.json:
                    print(json.dumps(res, indent=2, ensure_ascii=False))
                else:
                    print(f"[ERROR] {e}", file=sys.stderr)
                return 1
            print(spec["graph"])
        res = ok_result(
            tool="edit_pack",
            path=timeline_path,
            timeline=timeline_path,
            duration=duration,
            clips=len(tl["clips"]),
            overlays=len(tl.get("overlays") or []),
            audio=len(tl.get("audio") or []),
            look=(tl.get("look") or {}).get("name"),
            warning=warn,
        )
        if spec:
            res["graph"] = spec["graph"]
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            extra = f" warning={warn}" if warn else ""
            print(f"[OK] timeline → {timeline_path} duration={duration:.2f}s{extra}")
        return 0

    try:
        spec = compile_ffmpeg(tl, args.output, timeline_path=timeline_path)
    except Exception as e:
        res = fail_result(error="TIMELINE_INVALID", message=str(e), tool="edit_pack")
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    ff = run_ffmpeg(spec["argv"], timeout_sec=3600)
    if not ff.get("ok"):
        res = fail_result(error="FFMPEG_FAILED", message=ff.get("message"), tool="edit_pack")
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"[FAILED] FFMPEG_FAILED {ff.get('message')}", file=sys.stderr)
        return 1

    qa_path = None
    if args.qa:
        from lib.edit_qa import edit_qa_pack

        try:
            die_if_toolbox(paths["qa"])
        except SystemExit as e:
            return int(e.code or 14)
        qa_res = edit_qa_pack(args.output, paths["qa"])
        if not qa_res.get("ok"):
            res = fail_result(
                error=qa_res.get("error") or "QA_FAILED",
                message=qa_res.get("message"),
                tool="edit_pack",
                path=os.path.abspath(args.output),
                timeline=timeline_path,
            )
            if args.json:
                print(json.dumps(res, indent=2, ensure_ascii=False))
            else:
                print(f"[FAILED] QA {qa_res.get('error')}: {qa_res.get('message')}", file=sys.stderr)
            return 1
        qa_path = qa_res.get("path") or paths["qa"]

    res = ok_result(
        tool="edit_pack",
        path=os.path.abspath(args.output),
        timeline=timeline_path,
        duration=spec["duration"],
        clips=len(tl["clips"]),
        overlays=len(tl.get("overlays") or []),
        audio=len(tl.get("audio") or []),
        look=(tl.get("look") or {}).get("name"),
        qa=qa_path,
        warning=warn,
    )
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        extra = f" qa={qa_path}" if qa_path else ""
        if warn:
            extra += f" warning={warn}"
        print(f"[OK] master → {res['path']} duration={res['duration']:.2f}s{extra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
