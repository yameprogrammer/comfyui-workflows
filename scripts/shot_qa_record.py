#!/usr/bin/env python3
"""Record structured visual QA for a shot (Rule 7.3 hard gate input).

Approve (shot_approve --status approved / --clip approved) requires a
verdict=pass JSON written by this tool, with required checklist items.

  # After opening boards/qa/S03_keyframe_pack.png
  python scripts/shot_qa_record.py -e EP -s S03 --stage keyframe --verdict pass \\
    --pass-required --notes "matches master_front; hands OK; medium OK"

  python scripts/shot_qa_record.py -e EP -s S03 --stage keyframe --verdict fail \\
    --check K4_anatomy=fail:extra_fingers --notes "regen"

  python scripts/shot_qa_record.py -e EP -s S03 --stage clip --verdict pass \\
    --pass-required --notes "full motion, no freeze"
  # freeze detection is ON by default for clip stage (--no-freeze-check to skip)

  # Episode identity pass (after episode_identity_sheet)
  python scripts/shot_qa_record.py -e EP --stage identity --verdict pass \\
    --notes "same cast across all keyframes"
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys

from lib.story_package import StoryPackage, validate_episode_id
from lib.visual_qa import (
    CLIP_REQUIRED_CHECKS,
    KEYFRAME_REQUIRED_CHECKS,
    build_qa_report,
    file_sha256,
    keyframe_abs,
    parse_check_cli,
    pass_all_required_checks,
    qa_json_path,
    qa_pack_path,
    qa_pack_rel,
    save_identity_qa,
    save_qa_report,
    work_clip_abs,
)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_QA = 23


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Write meta/visual_qa/<shot>_<stage>.json for approve gate"
    )
    p.add_argument("--episode", "-e", default=None)
    p.add_argument("--shot", "-s", default=None, help="Shot id (required except identity)")
    p.add_argument(
        "--stage",
        choices=["keyframe", "clip", "identity"],
        default="keyframe",
    )
    p.add_argument(
        "--verdict",
        choices=["pass", "fail", "pending"],
        default=None,
    )
    p.add_argument("--notes", default="", help="Free-text evidence of what you looked at")
    p.add_argument(
        "--method",
        choices=["vision_open", "human", "heuristic", "hybrid", "skipped"],
        default="vision_open",
    )
    p.add_argument(
        "--agent",
        default="",
        help="Agent name for audit (default env AGENT_NAME)",
    )
    p.add_argument(
        "--check",
        action="append",
        default=[],
        help="Checklist item ID=pass|fail[:note] (repeatable)",
    )
    p.add_argument(
        "--pass-required",
        action="store_true",
        help="Mark all required checks pass (must still open pack & write honest notes)",
    )
    p.add_argument(
        "--from-json",
        default=None,
        help="Merge checks/notes from a JSON file",
    )
    p.add_argument(
        "--run-freeze-check",
        action="store_true",
        default=None,
        help="Clip stage: run freeze detect (DEFAULT on for --stage clip)",
    )
    p.add_argument(
        "--no-freeze-check",
        action="store_true",
        help="Clip stage: skip freeze heuristic (debug / intentional still)",
    )
    p.add_argument(
        "--allow-freeze",
        action="store_true",
        help="Clip stage: allow static/freeze_tail (intentional still hold)",
    )
    p.add_argument(
        "--list-required",
        action="store_true",
        help="Print required check IDs and exit",
    )
    args = p.parse_args(argv)

    if args.list_required:
        print("keyframe:", ", ".join(KEYFRAME_REQUIRED_CHECKS))
        print("clip:", ", ".join(CLIP_REQUIRED_CHECKS))
        print("identity: I1_cast_consistency")
        return EXIT_OK

    if not args.episode or not args.verdict:
        print("[ERROR] --episode and --verdict required", file=sys.stderr)
        return EXIT_USAGE

    if not validate_episode_id(args.episode):
        print("[ERROR] code=2 invalid episode id", file=sys.stderr)
        return EXIT_USAGE

    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] code=11 episode missing: {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    if args.stage == "identity":
        path = save_identity_qa(
            story,
            verdict=args.verdict,
            notes=args.notes,
            method=args.method,
            agent=args.agent,
        )
        print(f"OK identity verdict={args.verdict}")
        print(f"  file={path}")
        print(f"  QA_LOG={story.path('QA_LOG.md')}")
        if args.verdict != "pass":
            print("  (approve path for motion still uses per-shot keyframe QA)")
        return EXIT_OK

    if not args.shot:
        print("[ERROR] --shot required for keyframe/clip", file=sys.stderr)
        return EXIT_USAGE
    try:
        shot = story.get_shot(args.shot)
    except KeyError:
        print(f"[ERROR] shot missing {args.shot}", file=sys.stderr)
        return EXIT_USAGE

    checks = {}
    notes = args.notes or ""
    evidence: list[str] = []
    extra: dict = {}

    if args.from_json:
        with open(args.from_json, "r", encoding="utf-8") as f:
            blob = json.load(f)
        if isinstance(blob.get("checks"), dict):
            checks.update(blob["checks"])
        if blob.get("notes") and not notes:
            notes = str(blob["notes"])
        if blob.get("evidence_paths"):
            evidence.extend(blob["evidence_paths"])

    checks.update(parse_check_cli(args.check))
    if args.pass_required:
        base = pass_all_required_checks(args.stage)
        for k, v in base.items():
            checks.setdefault(k, v)

    if args.verdict == "pass" and args.method == "skipped":
        print(
            "[ERROR] method=skipped cannot pair with verdict=pass",
            file=sys.stderr,
        )
        return EXIT_USAGE

    if args.verdict == "pass" and not (notes or "").strip():
        print(
            "[ERROR] --notes required for verdict=pass "
            "(what did you open and verify?)",
            file=sys.stderr,
        )
        return EXIT_USAGE

    # Artifact bind
    artifact_rel = None
    artifact_abs = None
    if args.stage == "keyframe":
        artifact_abs = keyframe_abs(story, shot)
        artifact_rel = shot.get("keyframe") or f"keyframes/{args.shot}.png"
        if not artifact_abs:
            print(f"[ERROR] keyframe file missing for {args.shot}", file=sys.stderr)
            return EXIT_MISSING
    else:
        artifact_abs = work_clip_abs(story, shot)
        if artifact_abs:
            # store path relative to episode if under root
            try:
                artifact_rel = os.path.relpath(artifact_abs, story.root).replace("\\", "/")
            except ValueError:
                artifact_rel = artifact_abs
        if not artifact_abs:
            print(f"[ERROR] work clip missing for {args.shot}", file=sys.stderr)
            return EXIT_MISSING

    sha = file_sha256(artifact_abs) if artifact_abs else None

    pack = qa_pack_path(story, args.shot, args.stage)
    if os.path.isfile(pack):
        evidence.append(qa_pack_rel(args.shot, args.stage))
    else:
        print(
            f"[WARN] QA pack not found ({pack}). "
            f"Run: python scripts/shot_qa_pack.py -e {args.episode} -s {args.shot} "
            f"--stage {args.stage}",
            file=sys.stderr,
        )

    # Freeze detection DEFAULT ON for clip stage
    run_freeze = args.stage == "clip" and not args.no_freeze_check
    if args.run_freeze_check is True:
        run_freeze = True
    if args.stage == "clip" and run_freeze and artifact_abs:
        from lib.visual_qa import gate_work_clip_no_freeze, shot_allows_still_freeze

        sample_dir = story.path("boards", "qa", f"{args.shot}_clip_frames")
        os.makedirs(sample_dir, exist_ok=True)
        allow_still = args.allow_freeze or shot_allows_still_freeze(shot, story.doc)
        gate = gate_work_clip_no_freeze(
            artifact_abs,
            sample_dir=sample_dir,
            allow_still=allow_still,
            force=True,  # explicit QA always probes unless --no-freeze-check
        )
        fr = gate.get("report") or {}
        extra["freeze_heuristic"] = fr
        extra["freeze_gate"] = {
            k: v for k, v in gate.items() if k != "report"
        }
        if not gate.get("ok") and gate.get("error") == "FREEZE_PAD_SUSPECT":
            checks["C1_no_freeze_pad"] = {
                "pass": False,
                "note": (
                    f"{gate.get('kind')}: mid-end diff={fr.get('mean_abs_diff')} "
                    f"thr={fr.get('threshold')} pairs={fr.get('pairs')}"
                ),
            }
            if args.verdict == "pass":
                print(
                    f"[ERROR] freeze/{gate.get('kind')} detected — forcing verdict=fail. "
                    "Regen full motion; intentional still: --allow-freeze",
                    file=sys.stderr,
                )
                args.verdict = "fail"
                notes = (notes + " | freeze_heuristic_fail").strip(" |")
        elif fr.get("ok") and "C1_no_freeze_pad" not in checks:
            checks["C1_no_freeze_pad"] = {
                "pass": True,
                "note": (
                    f"heuristic ok kind={fr.get('kind')} "
                    f"diff={fr.get('mean_abs_diff')}"
                ),
            }
        elif gate.get("allowed_still") and "C1_no_freeze_pad" not in checks:
            checks["C1_no_freeze_pad"] = {
                "pass": True,
                "note": "intentional still allowed (--allow-freeze / motion_driver=still)",
            }

    if args.verdict == "pass":
        req = (
            KEYFRAME_REQUIRED_CHECKS
            if args.stage == "keyframe"
            else CLIP_REQUIRED_CHECKS
        )
        missing = [c for c in req if c not in checks]
        if missing:
            print(
                f"[ERROR] missing required checks: {missing}. "
                f"Use --pass-required or --check ID=pass",
                file=sys.stderr,
            )
            return EXIT_USAGE

    try:
        report = build_qa_report(
            episode_id=args.episode,
            shot_id=args.shot,
            stage=args.stage,
            verdict=args.verdict,
            checks=checks,
            notes=notes,
            method=args.method,
            agent=args.agent,
            artifact=artifact_rel,
            artifact_sha256=sha,
            evidence_paths=evidence,
            extra=extra or None,
        )
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return EXIT_USAGE

    path = save_qa_report(story, report)
    print(f"OK shot={args.shot} stage={args.stage} verdict={report['verdict']}")
    print(f"  file={path}")
    print(f"  artifact={artifact_abs}")
    print(f"  sha256={(sha or '')[:16]}...")
    if evidence:
        print(f"  evidence={evidence}")
    print(f"  QA_LOG={story.path('QA_LOG.md')}")
    if report["verdict"] == "pass":
        if args.stage == "keyframe":
            print(
                f"  next: python scripts/shot_approve.py -e {args.episode} "
                f"-s {args.shot} --status approved"
            )
        else:
            print(
                f"  next: python scripts/shot_approve.py -e {args.episode} "
                f"-s {args.shot} --clip approved"
            )
    else:
        print("  next: regenerate / edit, then re-record pass")
        return EXIT_QA
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
