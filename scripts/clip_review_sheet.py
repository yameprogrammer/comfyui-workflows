#!/usr/bin/env python3
"""Clip review helper (P1-4): first/last frames + optional contact grid.

Does NOT auto-approve. Human gate still required (clip_status / lip_status).

  python scripts/clip_review_sheet.py -e cafe_gomin_ep01
  python scripts/clip_review_sheet.py -e cafe_gomin_ep01 --shots S02,S05
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.ffmpeg_util import run_ffmpeg
from lib.one_take import work_clip_path
from lib.story_package import StoryPackage, validate_episode_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_PARTIAL = 31


def _extract_frame(video: str, png: str, *, at: str) -> bool:
    """at: 'first' | 'last'"""
    os.makedirs(os.path.dirname(png) or ".", exist_ok=True)
    if at == "first":
        r = run_ffmpeg(
            ["-y", "-i", video, "-frames:v", "1", "-q:v", "2", png],
            timeout_sec=60,
        )
    else:
        r = run_ffmpeg(
            ["-y", "-sseof", "-0.05", "-i", video, "-frames:v", "1", "-q:v", "2", png],
            timeout_sec=60,
        )
        if not (r.get("ok") and os.path.isfile(png) and os.path.getsize(png) > 500):
            r = run_ffmpeg(
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
                timeout_sec=120,
            )
    return bool(r.get("ok") and os.path.isfile(png) and os.path.getsize(png) > 500)


def _make_contact(pairs: list[tuple[str, str, str]], out_path: str, thumb_w: int = 270) -> bool:
    """pairs: (sid, first_png, last_png)"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("[WARN] PIL missing — skip contact grid", file=sys.stderr)
        return False

    if not pairs:
        return False

    rows = []
    for sid, fpath, lpath in pairs:
        imgs = []
        for p in (fpath, lpath):
            if os.path.isfile(p):
                im = Image.open(p).convert("RGB")
                h = max(1, int(im.height * (thumb_w / im.width)))
                im = im.resize((thumb_w, h), Image.Resampling.LANCZOS)
                imgs.append(im)
            else:
                imgs.append(Image.new("RGB", (thumb_w, int(thumb_w * 16 / 9)), (40, 40, 40)))
        # pad to same height
        mh = max(im.height for im in imgs)
        pad = []
        for im in imgs:
            if im.height < mh:
                canvas = Image.new("RGB", (im.width, mh), (20, 20, 20))
                canvas.paste(im, (0, (mh - im.height) // 2))
                pad.append(canvas)
            else:
                pad.append(im)
        row = Image.new("RGB", (thumb_w * 2 + 8, mh + 28), (18, 18, 20))
        row.paste(pad[0], (0, 24))
        row.paste(pad[1], (thumb_w + 8, 24))
        draw = ImageDraw.Draw(row)
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((4, 4), f"{sid}  first | last", fill=(220, 220, 220), font=font)
        rows.append(row)

    total_h = sum(r.height for r in rows) + 4 * (len(rows) - 1)
    total_w = max(r.width for r in rows)
    sheet = Image.new("RGB", (total_w, total_h), (12, 12, 14))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height + 4
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    sheet.save(out_path)
    return True


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Extract first/last frames for clip review")
    p.add_argument("--episode", "-e", required=True)
    p.add_argument("--shots", default=None, help="Comma list (default: all with work clips)")
    p.add_argument(
        "--out-dir",
        default=None,
        help="Output dir (default: stories/<ep>/board/clip_review)",
    )
    p.add_argument(
        "--no-contact",
        action="store_true",
        help="Only per-shot first/last png, no grid",
    )
    args = p.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] bad episode id", file=sys.stderr)
        return EXIT_USAGE
    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] episode missing {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    shots = sorted(story.shots(), key=lambda s: s.get("order", 0))
    if args.shots:
        want = {x.strip() for x in args.shots.split(",") if x.strip()}
        shots = [s for s in shots if s.get("shot_id") in want]

    out_dir = args.out_dir or story.path("board", "clip_review")
    os.makedirs(out_dir, exist_ok=True)

    ok = 0
    fail = 0
    pairs: list[tuple[str, str, str]] = []

    print(f"clip_review_sheet episode={args.episode} out={out_dir}")
    for shot in shots:
        sid = shot.get("shot_id")
        clip = work_clip_path(story, shot, sid)
        if not os.path.isfile(clip):
            print(f"  SKIP {sid} no work clip")
            continue
        first = os.path.join(out_dir, f"{sid}_first.png")
        last = os.path.join(out_dir, f"{sid}_last.png")
        f_ok = _extract_frame(clip, first, at="first")
        l_ok = _extract_frame(clip, last, at="last")
        if f_ok and l_ok:
            ok += 1
            pairs.append((sid, first, last))
            st = shot.get("clip_status") or "pending"
            lip = shot.get("lip_status") or "-"
            print(f"  OK {sid} clip_status={st} lip={lip} → {sid}_first/last.png")
        else:
            fail += 1
            print(f"  FAIL {sid} extract first={f_ok} last={l_ok}")

    contact = os.path.join(out_dir, "contact_first_last.png")
    if pairs and not args.no_contact:
        if _make_contact(pairs, contact):
            print(f"  contact={contact}")

    print(
        f"\nDone ok={ok} fail={fail}. "
        "Review frames then: shot_approve -e EP -s SHOT --clip approved"
    )
    if ok == 0:
        return EXIT_PARTIAL if fail else EXIT_MISSING
    return EXIT_OK if fail == 0 else EXIT_PARTIAL


if __name__ == "__main__":
    raise SystemExit(main())
