#!/usr/bin/env python3
"""
Orchestrate episode stages for a commission handoff.

Stages (in order):
  status → assets → compose → contact_sheet → i2v → s2v → upscale → assemble → qa → package

Default: status only unless --run is given.
Use --from / --to to slice the pipeline. --dry-run is forwarded where supported.
QA is auto-appended after motion/assemble when missing. Emits AGENT_RESULT JSON.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from lib.episode_status import episode_status_report, format_status_text
from lib.story_package import validate_episode_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_STAGE = 31

STAGES = [
    "status",
    "assets",
    "compose",
    "contact_sheet",
    "i2v",
    "s2v",
    "upscale",
    "assemble",
    "qa",
    "package",
]

# Agent profiles — speed-aware highway (docs/agent_video_tooling_reliability.md §10–11)
# IT hero (user QA 2026-07-13 lip bench C): 24fps / 12step / scale 1.5 / lightx2v / TeaCache off
PROFILES = {
    "preview": {
        "s2v_backend": "ltx23_ia2v",
        "s2v_prepare_mode": "center_voicey",
        "s2v_square": False,
        "s2v_audio_scale": 1.5,
        "s2v_fps": 25.0,
        "s2v_steps": 20,
        "s2v_long_edge": 960,
        "assemble_stage": "work",
        "qa_strict": False,
        "notes": "Fast LTX SI2V; explore/smoke",
    },
    "deliver": {
        "s2v_backend": "ltx23_ia2v",
        "s2v_prepare_mode": "center_voicey",
        "s2v_square": False,
        "s2v_audio_scale": 1.5,
        "s2v_fps": 25.0,
        "s2v_steps": 20,
        "s2v_long_edge": 960,
        "assemble_stage": "work",
        "qa_strict": True,
        "notes": "Agent default ship path: LTX SI2V (~1–2min/cut) + speaking prompts + QA strict",
    },
    "hero": {
        "s2v_backend": "infinitetalk",
        "s2v_prepare_mode": "center_voicey",
        "s2v_square": False,
        # Lip winner S02_it_lip_24fps_s12_as1.5_notea (2026-07-13)
        "s2v_audio_scale": 1.5,
        "s2v_fps": 24.0,
        "s2v_steps": 12,
        "s2v_long_edge": 832,
        "s2v_speed": True,
        "s2v_teacache": False,
        "assemble_stage": "work",
        "qa_strict": True,
        "notes": (
            "InfiniteTalk lip: lightx2v, 832/24fps/12step, audio_scale 1.5, "
            "TeaCache off. Hero dialogue CU only."
        ),
    },
}


def _slice_stages(from_s: str, to_s: str) -> list[str]:
    if from_s not in STAGES or to_s not in STAGES:
        raise ValueError(f"stages must be one of {STAGES}")
    i = STAGES.index(from_s)
    j = STAGES.index(to_s)
    if j < i:
        raise ValueError("--to must be after --from")
    return STAGES[i : j + 1]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Episode pipeline orchestrator (status → … → package)"
    )
    parser.add_argument("--episode", "-e", required=True)
    parser.add_argument(
        "--from",
        dest="from_stage",
        default="status",
        choices=STAGES,
        help="First stage (default status)",
    )
    parser.add_argument(
        "--to",
        dest="to_stage",
        default="package",
        choices=STAGES,
        help="Last stage when --run (default package)",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute stages (without this, only prints status + plan)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Forward dry-run to child stages (no Comfy/FFmpeg work)",
    )
    parser.add_argument(
        "--profile",
        choices=list(PROFILES.keys()),
        default="deliver",
        help="Agent profile: deliver|preview (LTX, fast) | hero (InfiniteTalk lips, slow)",
    )
    parser.add_argument("--i2v-backend", default=None)
    parser.add_argument(
        "--s2v-prepare-mode",
        default=None,
        help="SI2V driving prep (default from profile: center_voicey)",
    )
    parser.add_argument(
        "--s2v-backend",
        default=None,
        help="Override SI2V backend (default from profile / video_backends)",
    )
    parser.add_argument("--upscale-backend", default=None)
    parser.add_argument("--upscale-preset", default=None)
    parser.add_argument(
        "--assemble-stage",
        choices=["auto", "work", "deliver"],
        default=None,
        help="Assemble clip stage (default from profile: work)",
    )
    parser.add_argument("--no-bgm", action="store_true")
    parser.add_argument("--no-zip", action="store_true")
    parser.add_argument(
        "--compose-force",
        action="store_true",
        help="With compose stage: recompose existing keyframes",
    )
    parser.add_argument("--stop-on-error", action="store_true", default=True)
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument(
        "--no-qa-strict",
        action="store_true",
        help="QA stage reports only (do not fail pipeline)",
    )
    args = parser.parse_args(argv)

    profile = PROFILES[args.profile]
    if args.s2v_backend is None:
        args.s2v_backend = profile["s2v_backend"]
    if args.s2v_prepare_mode is None:
        args.s2v_prepare_mode = profile["s2v_prepare_mode"]
    if args.assemble_stage is None:
        args.assemble_stage = profile["assemble_stage"]
    qa_strict = profile.get("qa_strict", True) and not args.no_qa_strict

    if not validate_episode_id(args.episode):
        print("[ERROR] code=2 invalid episode id", file=sys.stderr)
        return EXIT_USAGE

    try:
        stages = _slice_stages(args.from_stage, args.to_stage)
    except ValueError as e:
        print(f"[ERROR] code=2 {e}", file=sys.stderr)
        return EXIT_USAGE

    try:
        report = episode_status_report(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] code=11 episode missing: {args.episode}", file=sys.stderr)
        return EXIT_MISSING

    print("=== STATUS ===")
    print(format_status_text(report))
    print()
    print(
        f"=== PLAN profile={args.profile} stages={stages} "
        f"run={args.run} dry_run={args.dry_run} ==="
    )
    print(f"  s2v_backend={args.s2v_backend} prepare={args.s2v_prepare_mode}")
    print(f"  assemble_stage={args.assemble_stage} qa_strict={qa_strict}")
    print(f"  profile_notes={profile.get('notes')}")
    print(f"suggested overall_next={report['overall_next']}")

    if not args.run:
        print("\n(pass --run to execute plan; use --dry-run for no-op children)")
        return EXIT_OK

    stop = not args.continue_on_error
    ep = args.episode
    failed = []
    stage_results: list[dict] = []

    # Always append qa after assemble if running a ship path without explicit qa
    if args.run and "assemble" in stages and "qa" not in stages and "package" in stages:
        # insert qa before package
        pi = stages.index("package")
        stages = stages[:pi] + ["qa"] + stages[pi:]
    elif args.run and stages[-1] in ("assemble", "upscale", "s2v", "i2v") and "qa" not in stages:
        stages = list(stages) + ["qa"]

    for stage in stages:
        print(f"\n>>> STAGE {stage}")
        code = 0
        if stage == "status":
            print(format_status_text(episode_status_report(ep)))
            continue
        if stage == "assets":
            from assets_list import main as assets_main

            code = assets_main(["--episode", ep])
        elif stage == "compose":
            from shot_compose import main as compose_main

            argv2 = ["--episode", ep, "--all"]
            if args.dry_run:
                argv2.append("--dry-run")
            if args.compose_force:
                argv2.append("--force")
            code = compose_main(argv2)
        elif stage == "contact_sheet":
            from episode_contact_sheet import main as contact_main

            argv2 = ["--episode", ep]
            if args.dry_run:
                argv2.append("--dry-run")
            code = contact_main(argv2)
        elif stage == "i2v":
            from episode_i2v import main as i2v_main

            argv2 = ["--episode", ep, "--shots", "all_approved"]
            if args.dry_run:
                argv2.append("--dry-run")
            if args.i2v_backend:
                argv2.extend(["--backend", args.i2v_backend])
            if stop:
                argv2.append("--stop-on-error")
            code = i2v_main(argv2)
        elif stage == "s2v":
            from episode_s2v import main as s2v_main

            argv2 = [
                "--episode",
                ep,
                "--shots",
                "all_approved",
                "--prepare-mode",
                args.s2v_prepare_mode,
                "--audio-scale",
                str(profile.get("s2v_audio_scale", 1.5)),
                "--fps",
                str(profile.get("s2v_fps", 25.0)),
                "--steps",
                str(int(profile.get("s2v_steps", 20))),
                "--long-edge",
                str(int(profile.get("s2v_long_edge", 960))),
            ]
            if args.s2v_backend:
                argv2.extend(["--backend", args.s2v_backend])
            # format-consistent canvas unless profile forces square
            if profile.get("s2v_square"):
                argv2.append("--square")
            else:
                argv2.append("--no-square")
            if not profile.get("s2v_speed", True) and profile.get("s2v_backend") == "infinitetalk":
                argv2.append("--no-speed")
            # TeaCache default off for IT; only pass --teacache when profile enables it
            if profile.get("s2v_teacache") and profile.get("s2v_backend") == "infinitetalk":
                argv2.append("--teacache")
            elif (
                profile.get("s2v_backend") == "infinitetalk"
                and profile.get("s2v_teacache") is False
            ):
                argv2.append("--no-teacache")
            if args.dry_run:
                argv2.append("--dry-run")
            if stop:
                argv2.append("--stop-on-error")
            code = s2v_main(argv2)
            # Soft-ok when no si2v shots exist (exit 21)
            if code == 21:
                print("[INFO] s2v stage: no si2v shots — continue")
                code = 0
        elif stage == "upscale":
            from episode_upscale import main as up_main

            argv2 = ["--episode", ep]
            if args.dry_run:
                argv2.append("--dry-run")
            if args.upscale_backend:
                argv2.extend(["--backend", args.upscale_backend])
            if args.upscale_preset:
                argv2.extend(["--preset", args.upscale_preset])
            if stop:
                argv2.append("--stop-on-error")
            code = up_main(argv2)
        elif stage == "assemble":
            from assemble_video import main as asm_main

            argv2 = [
                "--episode",
                ep,
                "--stage",
                args.assemble_stage,
                "--mix-policy",
                "layered",
            ]
            if args.dry_run:
                argv2.append("--dry-run")
            if args.no_bgm:
                argv2.append("--no-bgm")
            code = asm_main(argv2)
        elif stage == "qa":
            from episode_qa import main as qa_main

            argv2 = ["--episode", ep]
            if qa_strict:
                argv2.append("--strict")
            else:
                argv2.append("--no-strict")
            # ship gates: clip always; lip hard on hero
            if args.profile in ("deliver", "hero"):
                argv2.append("--require-clip")
            if args.profile == "hero":
                argv2.append("--require-lip")
            if args.dry_run:
                print("[dry-run] skip episode_qa")
                code = 0
            else:
                code = qa_main(argv2)
        elif stage == "package":
            from package_delivery import main as pkg_main

            argv2 = ["--episode", ep]
            if args.dry_run:
                argv2.append("--dry-run")
            if args.no_zip:
                argv2.append("--no-zip")
            code = pkg_main(argv2)
        else:
            print(f"unknown stage {stage}")
            code = EXIT_STAGE

        print(f"<<< STAGE {stage} exit={code}")
        stage_results.append(
            {"name": stage, "exit_code": code, "ok": code == 0}
        )
        if code != 0:
            # dry-run may hit "no clips" on assemble when i2v was also dry-run
            soft = args.dry_run and code in (21,)
            if soft:
                print(f"[WARN] stage {stage} soft-fail under --dry-run (exit={code})")
                continue
            failed.append((stage, code))
            if stop:
                print(f"[STOP] stage {stage} failed")
                _emit_pipeline_result(
                    ep,
                    ok=False,
                    profile=args.profile,
                    stages=stage_results,
                    failed=failed,
                    exit_code=EXIT_STAGE,
                )
                return EXIT_STAGE

    ok = not failed
    print("\nPipeline finished OK" if ok else f"\nCompleted with failures: {failed}")
    print(format_status_text(episode_status_report(ep)))
    _emit_pipeline_result(
        ep,
        ok=ok,
        profile=args.profile,
        stages=stage_results,
        failed=failed,
        exit_code=EXIT_OK if ok else EXIT_STAGE,
    )
    return EXIT_OK if ok else EXIT_STAGE


def _emit_pipeline_result(
    episode_id: str,
    *,
    ok: bool,
    profile: str,
    stages: list,
    failed: list,
    exit_code: int,
) -> None:
    """Write unified AGENT_RESULT for agents."""
    try:
        from lib.agent_result import agent_result, print_agent_summary, write_agent_result
        from lib.story_package import StoryPackage
        from episode_qa import run_episode_qa

        story = StoryPackage.load(episode_id)
        qa = None
        try:
            qa = run_episode_qa(
                episode_id,
                strict=False,
                check_final=True,
                require_lip=(profile == "hero"),
            )
        except Exception as e:
            qa = {"ok": False, "error": str(e)}

        arts = []
        for name in (
            f"{episode_id}_av_final.mp4",
            f"{episode_id}_work_final.mp4",
            f"{episode_id}_final.mp4",
        ):
            p = story.path("exports", "final", name)
            if os.path.isfile(p):
                arts.append({"role": "final", "path": p})
                break
        meta_path = story.path("meta", "agent_pipeline_result.json")
        result = agent_result(
            ok=ok and bool((qa or {}).get("ok", True) or not failed),
            tool="episode_pipeline",
            episode_id=episode_id,
            error=None if ok else "PIPELINE_STAGE_FAILED",
            message=f"profile={profile} failed={failed}",
            exit_code=exit_code,
            artifacts=arts,
            qa=qa,
            stages=stages,
            extra={
                "profile": profile,
                "agent_notes": [
                    "Per-cut clip_status must be approved before assemble (Rule 7.2): "
                    "shot_approve -e EP -s SHOT --clip approved",
                    "SI2V/hero lip_status: shot_approve -e EP -s SHOT --lip approved "
                    "(also synced by --clip approved on si2v)",
                    "Daily path: --profile deliver (LTX). Hero lips: --profile hero or --backend infinitetalk",
                    "See docs/agent_av_smoke_checklist.md",
                    "Copy episode to YOUR workspace: "
                    f"python scripts/export_episode_to_workspace.py -e {episode_id} "
                    "--dest <YOUR_PROJECT>/episodes/<ep>  (or set AGENT_WORKSPACE)",
                ],
                "factory_episode_root": story.root,
                "workspace_export_hint": (
                    f"python scripts/export_episode_to_workspace.py -e {episode_id} "
                    f"--dest <AGENT_WORKSPACE>/episodes/{episode_id}"
                ),
            },
        )
        # ok: pipeline stages ok; if QA has only lip warnings, deliver still ok
        if ok and qa and not qa.get("ok") and qa.get("issues"):
            result["ok"] = False
            result["error"] = "QA_HARD_ISSUES"
            result["exit_code"] = EXIT_STAGE
        write_agent_result(meta_path, result)
        print_agent_summary(result)
        print(f"result_json={meta_path}")
    except Exception as e:
        print(f"[WARN] AGENT_RESULT emit failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
