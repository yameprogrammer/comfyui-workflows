#!/usr/bin/env python3
"""
Export human-facing storyboard package from episode keyframes.

Community format:
  - Contact sheet / board grid (animatic-style review)
  - Per-shot inventory + motion_prompt reminders
  - Checklist before I2V

Usage:
  python scripts/storyboard_export.py --episode mina_cafe_ep01
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys

from lib.comfy_client import utc_now_iso
from lib.contact_sheet import build_contact_sheet
from lib.story_package import StoryPackage, validate_episode_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Export storyboard contact + README for episode")
    ap.add_argument("--episode", "-e", required=True)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--thumb-max", type=int, default=320)
    args = ap.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] bad episode id", file=sys.stderr)
        return EXIT_USAGE
    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] episode missing {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    board_dir = story.path("board")
    os.makedirs(board_dir, exist_ok=True)

    shots = sorted(story.shots(), key=lambda s: s.get("order", 0))
    paths: list[str] = []
    rows: list[dict] = []
    missing_kf = 0
    for s in shots:
        sid = s.get("shot_id") or "?"
        rel = s.get("keyframe") or f"keyframes/{sid}.png"
        path = story.path(*str(rel).replace("\\", "/").split("/"))
        status = s.get("keyframe_status") or ("draft" if os.path.isfile(path) else "missing")
        if os.path.isfile(path):
            paths.append(path)
        else:
            missing_kf += 1
        rows.append(
            {
                "shot_id": sid,
                "order": s.get("order"),
                "shot_type": s.get("shot_type"),
                "action": (s.get("action") or "")[:160],
                "character_ids": s.get("character_ids") or [],
                "location_id": s.get("location_id"),
                "keyframe": rel,
                "keyframe_status": status,
                "keyframe_end": s.get("keyframe_end"),
                "motion_prompt": s.get("motion_prompt") or "",
                "duration_sec": s.get("duration_sec"),
            }
        )

    contact_out = os.path.join(board_dir, "storyboard_contact.png")
    if paths:
        r = build_contact_sheet(
            paths, contact_out, cols=args.cols, thumb_max=args.thumb_max
        )
        if not r.get("ok"):
            print(f"[WARN] contact sheet: {r.get('error')} {r.get('message')}")
        else:
            print(f"OK contact={contact_out} panels={len(paths)}")
    else:
        print("[WARN] no keyframe PNGs found — compose shots first")

    inv_path = os.path.join(board_dir, "shots_inventory.json")
    with open(inv_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "episode_id": args.episode,
                "exported_at": utc_now_iso(),
                "format": story.format_id(),
                "look_id": story.look_id(),
                "shot_count": len(rows),
                "keyframes_present": len(paths),
                "keyframes_missing": missing_kf,
                "shots": rows,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
        f.write("\n")
    print(f"OK inventory={inv_path}")

    readme = os.path.join(board_dir, "README_STORYBOARD.md")
    lines = [
        f"# Storyboard package — `{args.episode}`",
        "",
        f"- exported: {utc_now_iso()}",
        f"- format: `{story.format_id()}`",
        f"- look: `{story.look_id()}`",
        f"- shots: {len(rows)} · keyframes present: {len(paths)} · missing: {missing_kf}",
        "",
        "## Community production format",
        "",
        "1. **Asset packs** locked (character + location + look)",
        "2. **This board** = human gate before motion",
        "3. **Per-shot keyframe PNG** @ episode aspect = I2V first frame",
        "4. **motion_prompt** = camera/body motion only — do **not** re-describe face",
        "5. Optional **keyframe_end** for first–last / FLF2V bridges",
        "6. Approve keyframes → `episode_i2v` / `episode_s2v`",
        "",
        "SSOT research: `docs/storyboard_keyframe_community_research.md`",
        "",
        "## Files",
        "",
        f"- `board/storyboard_contact.png` — review grid",
        f"- `board/shots_inventory.json` — machine inventory",
        f"- `keyframes/S0x.png` — production stills",
        f"- `shots.json` — shot list SSOT",
        "",
        "## Checklist (before I2V)",
        "",
        "- [ ] Contact sheet identity + wardrobe continuity OK",
        "- [ ] Same location landmarks read across same `location_id`",
        "- [ ] Each shot `keyframe_status=approved`",
        "- [ ] `motion_prompt` is motion/camera only",
        "- [ ] Clip duration ~3–6s (backend limits)",
        "",
        "## Shots",
        "",
    ]
    for r in rows:
        lines.append(
            f"- **{r['shot_id']}** ({r.get('shot_type')}) "
            f"[{r.get('keyframe_status')}] "
            f"chars={r.get('character_ids')} loc={r.get('location_id')}"
        )
        lines.append(f"  - action: {r.get('action')}")
        if r.get("motion_prompt"):
            lines.append(f"  - motion: {r.get('motion_prompt')}")
    with open(readme, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"OK readme={readme}")
    print(
        f"\nDone episode={args.episode} "
        f"present={len(paths)} missing={missing_kf}"
    )
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
