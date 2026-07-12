#!/usr/bin/env python3
"""
Fast agent AV reliability gate (minimal GPU).

Checks config contracts, profile wiring, QA import, and optional episode state.
Does not queue long Comfy jobs unless --full (still skips multi-minute IT by default).

Usage:
  python scripts/smoke_agent_av.py
  python scripts/smoke_agent_av.py -e sonagi_cafe_smoke_v1
  python scripts/smoke_agent_av.py -e EP --json
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys

from lib.agent_result import agent_result, print_agent_summary, write_agent_result
from lib.video_backends import load_video_backends, resolve_s2v_backend

EXIT_OK = 0
EXIT_FAIL = 42
EXIT_MISSING = 11


def _check_profiles() -> list[dict]:
    issues = []
    # Import without executing main
    import importlib.util

    path = os.path.join(os.path.dirname(__file__), "episode_pipeline.py")
    spec = importlib.util.spec_from_file_location("episode_pipeline_mod", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    profiles = getattr(mod, "PROFILES", {})
    for name in ("preview", "deliver", "hero"):
        if name not in profiles:
            issues.append({"code": "PROFILE_MISSING", "message": name})
    deliver = profiles.get("deliver") or {}
    hero = profiles.get("hero") or {}
    if deliver.get("s2v_backend") != "ltx23_ia2v":
        issues.append(
            {
                "code": "DELIVER_NOT_LTX",
                "message": f"deliver s2v={deliver.get('s2v_backend')}",
            }
        )
    if hero.get("s2v_backend") != "infinitetalk":
        issues.append(
            {
                "code": "HERO_NOT_IT",
                "message": f"hero s2v={hero.get('s2v_backend')}",
            }
        )
    # mild contract
    if float(hero.get("s2v_audio_scale") or 0) > 1.5:
        issues.append(
            {
                "code": "HERO_SCALE_HIGH",
                "message": f"hero audio_scale={hero.get('s2v_audio_scale')} (expect ~1.35 mild)",
            }
        )
    if int(hero.get("s2v_steps") or 0) not in (8, 10, 12):
        issues.append(
            {
                "code": "HERO_STEPS",
                "message": f"hero steps={hero.get('s2v_steps')}",
            }
        )
    return issues


def run_smoke(episode_id: str | None) -> dict:
    issues: list[dict] = []
    warnings: list[dict] = []
    artifacts: list[dict] = []

    cfg = load_video_backends()
    default_s2v = resolve_s2v_backend(None)
    if default_s2v != "ltx23_ia2v":
        issues.append(
            {
                "code": "DEFAULT_S2V",
                "message": f"resolve default={default_s2v} expected ltx23_ia2v",
            }
        )
    if cfg.get("default_backend_s2v") != "ltx23_ia2v":
        warnings.append(
            {
                "code": "JSON_DEFAULT_S2V",
                "message": str(cfg.get("default_backend_s2v")),
            }
        )

    issues.extend(_check_profiles())

    # speed lora file exists under portable (optional warn)
    lora = os.path.join(
        r"F:\ComfyUI_windows_portable\ComfyUI\models\loras",
        r"Wan2.1\Wan21_I2V_14B_lightx2v_cfg_step_distill_lora_rank64.safetensors",
    )
    if not os.path.isfile(lora):
        warnings.append({"code": "SPEED_LORA_MISSING", "message": lora})
    else:
        artifacts.append({"role": "speed_lora", "path": lora})

    qa_report = None
    if episode_id:
        try:
            from lib.story_package import StoryPackage, validate_episode_id

            if not validate_episode_id(episode_id):
                issues.append({"code": "BAD_EPISODE_ID", "message": episode_id})
            else:
                story = StoryPackage.load(episode_id)
                artifacts.append({"role": "shots_json", "path": story.path("shots.json")})
                from episode_qa import run_episode_qa

                qa_report = run_episode_qa(episode_id, strict=False, check_final=True)
                if not qa_report.get("ok"):
                    # soft for smoke unless hard issues on required contracts
                    for i in qa_report.get("issues") or []:
                        warnings.append(i)
                # lip gate visibility
                for sh in story.shots():
                    from lib.audio_package import shot_motion_driver

                    if shot_motion_driver(sh, story.doc) != "si2v":
                        continue
                    lip = (sh.get("lip_status") or "pending").lower()
                    if lip not in ("approved", "ok"):
                        warnings.append(
                            {
                                "code": "LIP_VISUAL_PENDING",
                                "shot_id": sh.get("shot_id"),
                                "message": (
                                    f"si2v shot lip_status={lip!r} — "
                                    f"run: shot_approve -e {episode_id} -s {sh.get('shot_id')} --lip approved"
                                ),
                            }
                        )
        except FileNotFoundError:
            return agent_result(
                ok=False,
                tool="smoke_agent_av",
                episode_id=episode_id,
                error="EPISODE_MISSING",
                message=episode_id,
                exit_code=EXIT_MISSING,
            )

    # Import critical modules
    for mod in ("generate_s2v", "assemble_video", "episode_s2v", "episode_tts"):
        try:
            __import__(mod)
        except Exception as e:
            issues.append({"code": "IMPORT_FAIL", "message": f"{mod}: {e}"})

    ok = len(issues) == 0
    notes = [
        "Lip quality is not auto-scored. SI2V/hero cuts need human (or vision) lip_status=approved.",
        "Agent daily path: episode_pipeline --profile deliver (LTX). Hero lips: --backend infinitetalk (mild).",
        "Ideogram 4 typography tool is backlog — not part of this gate.",
    ]
    result = agent_result(
        ok=ok,
        tool="smoke_agent_av",
        episode_id=episode_id,
        error=None if ok else (issues[0].get("code") if issues else "SMOKE_FAIL"),
        message="agent AV contract smoke",
        exit_code=EXIT_OK if ok else EXIT_FAIL,
        artifacts=artifacts,
        qa={
            "ok": ok,
            "issues": issues,
            "warnings": warnings,
            "episode_qa": qa_report,
        },
        extra={
            "default_backend_s2v": default_s2v,
            "agent_notes": notes,
        },
    )
    return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Agent AV reliability smoke (fast gate)")
    p.add_argument("--episode", "-e", default=None, help="Optional episode id")
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--write",
        default=None,
        help="Write result JSON path (default meta under episode or ./agent_smoke_result.json)",
    )
    args = p.parse_args(argv)

    result = run_smoke(args.episode)
    out = args.write
    if not out and args.episode:
        try:
            from lib.story_package import StoryPackage

            out = StoryPackage.load(args.episode).path("meta", "agent_smoke_result.json")
        except Exception:
            out = "agent_smoke_result.json"
    if not out:
        out = "agent_smoke_result.json"
    write_agent_result(out, result)
    result.setdefault("artifacts", []).append({"role": "smoke_result", "path": out})

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_agent_summary(result)
        print(f"wrote={out}")

    return int(result.get("exit_code") or 0)


if __name__ == "__main__":
    raise SystemExit(main())
