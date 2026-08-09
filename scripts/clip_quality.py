#!/usr/bin/env python3
"""Agent surface for video clip quality (research → recommend → check → polish).

  python scripts/clip_quality.py recommend --goal hero --face-cu --duration 4
  python scripts/clip_quality.py check-prompt -p "slow push-in, soft blink"
  python scripts/clip_quality.py probe -i clip.mp4
  python scripts/clip_quality.py polish -i clip.mp4 -o out.mp4 --goal delivery --face
  python scripts/clip_quality.py episode-plan -e EP --phase full
  python scripts/clip_quality.py playbook

Research: docs/clip_quality_playbook.md · docs/ltx23_quality_research_and_improvement.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import subprocess
import sys
from pathlib import Path

from lib.clip_quality import (
    check_i2v_prompt,
    format_episode_plan,
    format_recommendation,
    plan_episode_quality,
    probe_clip,
    recommend_generation,
    recommend_post,
)


def cmd_recommend(args: argparse.Namespace) -> int:
    rec = recommend_generation(
        goal=args.goal,
        face_closeup=bool(args.face_cu),
        duration_sec=float(args.duration),
        backend=args.backend,
        has_end_frame=bool(args.flf),
        dialogue=bool(args.dialogue),
    )
    if args.json:
        print(json.dumps(rec, ensure_ascii=False, indent=2))
    else:
        print(format_recommendation(rec))
    return 0


def cmd_check_prompt(args: argparse.Namespace) -> int:
    text = args.prompt
    if args.prompt_file:
        text = Path(args.prompt_file).read_text(encoding="utf-8")
    r = check_i2v_prompt(text or "")
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"score={r['score']} ok={r['ok']} motion={r['has_motion']}")
        for w in r.get("warnings") or []:
            print(f"  WARN: {w}")
        if r.get("suggestion"):
            print(f"  try: {r['suggestion']}")
    return 0 if r.get("ok") else 2


def cmd_probe(args: argparse.Namespace) -> int:
    r = probe_clip(args.input)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        if not r.get("ok"):
            print(f"FAIL {r.get('error')}", file=sys.stderr)
            return 1
        print(
            f"{r['path']}: {r['width']}x{r['height']}  "
            f"{r['duration_sec']}s  {r['fps']}fps  frames~{r['approx_frames']}  "
            f"audio={r['has_audio']}"
        )
        for t in r.get("tips") or []:
            print(f"  tip: {t}")
        post = r.get("post") or {}
        for s in post.get("steps") or []:
            print(f"  post[{s['id']}]: {s['cli']}")
    return 0


def cmd_polish(args: argparse.Namespace) -> int:
    """Optional run: face enhance → upscale_video (best-effort)."""
    inp = Path(args.input)
    if not inp.is_file():
        print(f"missing input {inp}", file=sys.stderr)
        return 1
    out = Path(args.output or (str(inp.with_name(inp.stem + "_polish" + inp.suffix))))
    cur = str(inp)
    steps_ran: list[str] = []

    if args.face or args.dialogue:
        face_out = str(out.with_name(out.stem + "_face" + out.suffix))
        cmd = [
            sys.executable,
            "scripts/generate_wan22_face_enhance.py",
            "-i",
            cur,
            "-o",
            face_out,
        ]
        print("RUN", " ".join(cmd))
        if not args.dry_run:
            rc = subprocess.call(cmd)
            if rc == 0 and Path(face_out).is_file():
                cur = face_out
                steps_ran.append("face_enhance")
            else:
                print(
                    f"[polish] face enhance failed rc={rc} — continue without",
                    file=sys.stderr,
                )

    if args.goal in ("delivery", "deliver", "hero", "work") and not args.no_upscale:
        up_out = str(out)
        backend = args.upscale_backend or (
            "seedvr2" if args.goal in ("hero", "delivery", "deliver") and args.seedvr2 else None
        )
        cmd = [
            sys.executable,
            "scripts/upscale_video.py",
            "-i",
            cur,
            "-o",
            up_out,
            "--style",
            "photo",
            "--preset",
            args.upscale_preset or "deliver_1080",
        ]
        if backend:
            cmd += ["--backend", backend]
        print("RUN", " ".join(cmd))
        if not args.dry_run:
            rc = subprocess.call(cmd)
            if rc != 0:
                print(f"[polish] upscale failed rc={rc}", file=sys.stderr)
                return rc
            steps_ran.append("upscale_video")
            cur = up_out
        else:
            steps_ran.append("upscale_video(dry)")

    print(f"[polish] done steps={steps_ran} → {cur}")
    if args.json:
        print(json.dumps({"ok": True, "output": cur, "steps": steps_ran}, indent=2))
    return 0


def cmd_playbook(_args: argparse.Namespace) -> int:
    p = Path("docs/clip_quality_playbook.md")
    if p.is_file():
        print(p.read_text(encoding="utf-8")[:6000])
        if p.stat().st_size > 6000:
            print("\n... see full file:", p)
    else:
        print("missing docs/clip_quality_playbook.md")
    return 0


def cmd_episode_plan(args: argparse.Namespace) -> int:
    plan = plan_episode_quality(
        args.episode,
        phase=args.phase,
        shots=args.shots,
        hero_shots=args.hero_shots,
        face_closeup_ids=args.face_cu_shots,
        require_approved=not args.allow_draft,
    )
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(format_episode_plan(plan))
    return 0 if plan.get("ok") else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Video clip quality for agents")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("recommend", help="generation + post plan")
    pr.add_argument("--goal", default="work", help="draft|work|hero|delivery")
    pr.add_argument("--face-cu", action="store_true")
    pr.add_argument("--dialogue", action="store_true")
    pr.add_argument("--duration", type=float, default=4.0)
    pr.add_argument("--backend", default=None, help="ltx23_aio_i2v|wan22|…")
    pr.add_argument("--flf", action="store_true", help="has last frame")
    pr.add_argument("--json", action="store_true")
    pr.set_defaults(func=cmd_recommend)

    pc = sub.add_parser("check-prompt", help="I2V motion-only dialect check")
    pc.add_argument("--prompt", "-p", default=None)
    pc.add_argument("--prompt-file", default=None)
    pc.add_argument("--json", action="store_true")
    pc.set_defaults(func=cmd_check_prompt)

    pp = sub.add_parser("probe", help="ffprobe clip + tips")
    pp.add_argument("--input", "-i", required=True)
    pp.add_argument("--json", action="store_true")
    pp.set_defaults(func=cmd_probe)

    po = sub.add_parser("polish", help="face enhance + upscale chain (optional run)")
    po.add_argument("--input", "-i", required=True)
    po.add_argument("--output", "-o", default=None)
    po.add_argument("--goal", default="delivery")
    po.add_argument("--face", action="store_true")
    po.add_argument("--dialogue", action="store_true")
    po.add_argument("--no-upscale", action="store_true")
    po.add_argument("--seedvr2", action="store_true")
    po.add_argument("--upscale-backend", default=None)
    po.add_argument("--upscale-preset", default="deliver_1080")
    po.add_argument("--dry-run", action="store_true")
    po.add_argument("--json", action="store_true")
    po.set_defaults(func=cmd_polish)

    pe = sub.add_parser(
        "episode-plan",
        help="episode draft → work → hero CLI plan (L11)",
    )
    pe.add_argument("--episode", "-e", required=True)
    pe.add_argument(
        "--phase",
        default="full",
        choices=["draft", "work", "hero", "full"],
        help="which pipeline phase(s) to plan (default full)",
    )
    pe.add_argument(
        "--shots",
        default="all_approved",
        help="all_approved | all | S01,S02,...",
    )
    pe.add_argument(
        "--hero-shots",
        default=None,
        help="comma shot ids for hero re-gen (default: clip-approved / quality=hero)",
    )
    pe.add_argument(
        "--face-cu-shots",
        default=None,
        help="comma shot ids that need face polish",
    )
    pe.add_argument(
        "--allow-draft",
        action="store_true",
        help="include non-approved keyframes",
    )
    pe.add_argument("--json", action="store_true")
    pe.set_defaults(func=cmd_episode_plan)

    pb = sub.add_parser("playbook", help="print quality playbook")
    pb.set_defaults(func=cmd_playbook)

    args = p.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
