"""Video clip quality helpers for agents (research → actionable levers).

Community / vendor consensus (2026):
  - Wan 2.2: top open visual quality; LTX 2.3: speed + long/audio-native, softer detail
  - I2V prompts: motion/camera only — do not re-describe face/wardrobe
  - Prefer shorter pure clips (≤4s@24fps / ≤97 frames) then FLF/chain extend
  - Generate at work tier (720p) then face polish + upscale for delivery
  - Wan blur: more steps, Euler, avoid ultra-long single takes; dual high/low noise
  - Stitch: prefer near-lossless intermediates when chaining long takes
  - Face CU: face enhance after I2V; InfiniteTalk for lips, not long body motion

Factory SSOT already: ``--ltx-profile draft|work|hero``, Wan ``--profile preview|deliver|quality``,
upscale_recommend, wan22_face_enhance, flf2v, chain_*.

This module turns that into one discovery surface for agents.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# --- I2V prompt dialect (L7) -------------------------------------------------

# Tokens that usually mean "re-describing the still" on I2V (bad)
_LOOK_REDESCRIBE = re.compile(
    r"\b("
    r"beautiful face|pretty face|detailed face|sharp eyes|blue eyes|brown eyes|"
    r"long hair|black hair|blonde|wardrobe|wearing|dressed in|outfit|"
    r"masterpiece|best quality|8k|photorealistic|ultra detailed|"
    r"1girl|1boy|solo portrait"
    r")\b",
    re.I,
)
_MOTION_HINTS = re.compile(
    r"\b("
    r"camera|pan|tilt|dolly|push|pull|zoom|orbit|track|"
    r"blink|turn|turns|nod|breath|breathe|walk|run|smile|glance|"
    r"head|shoulder|hand|gesture|wind|hair move|subtle|slow|gentle|"
    r"static frame|locked frame|hold"
    r")\b",
    re.I,
)


def check_i2v_prompt(prompt: str) -> dict[str, Any]:
    """Return warnings for I2V motion-prompt dialect issues."""
    text = (prompt or "").strip()
    warnings: list[str] = []
    score = 1.0
    if not text:
        return {
            "ok": False,
            "score": 0.0,
            "warnings": ["empty prompt — write motion/camera only"],
            "hits_look": [],
            "has_motion": False,
        }
    hits = sorted({m.group(0).lower() for m in _LOOK_REDESCRIBE.finditer(text)})
    if hits:
        score -= 0.35
        warnings.append(
            "look/identity re-describe tokens (I2V should be motion-only): "
            + ", ".join(hits[:8])
        )
    has_motion = bool(_MOTION_HINTS.search(text))
    if not has_motion:
        score -= 0.25
        warnings.append(
            "few motion/camera verbs — add camera move or body action "
            "(e.g. slow push-in, soft blink, slight head turn)"
        )
    if len(text) > 400:
        score -= 0.1
        warnings.append("very long prompt — prefer short motion sentence for I2V")
    score = max(0.0, min(1.0, score))
    return {
        "ok": score >= 0.55 and not hits[:1] or (has_motion and score >= 0.4),
        "score": round(score, 2),
        "warnings": warnings,
        "hits_look": hits,
        "has_motion": has_motion,
        "suggestion": (
            "gentle head turn toward camera, soft blink, subtle breathing, "
            "locked medium frame, continuous motion"
            if not has_motion
            else None
        ),
    }


# --- Generation recommend ----------------------------------------------------

def recommend_generation(
    *,
    goal: str = "work",
    face_closeup: bool = False,
    duration_sec: float = 4.0,
    backend: str | None = None,
    has_end_frame: bool = False,
    dialogue: bool = False,
) -> dict[str, Any]:
    """Recommend engine + profile + hard rules for a clip."""
    goal = (goal or "work").strip().lower()
    if goal in ("preview", "scout", "fast"):
        goal = "draft"
    if goal in ("delivery", "deliver", "final", "hero"):
        goal = "hero" if goal == "hero" else "work"
    if goal not in ("draft", "work", "hero"):
        goal = "work"

    be = (backend or "").strip().lower() or None
    # Defaults from factory A/B + community
    if dialogue and face_closeup:
        primary = "infinitetalk"  # lips hero
        alt = "ltx23_ia2v"
    elif has_end_frame:
        primary = "ltx23_aio_flf" if not be else be
        alt = "wan22_flf"
    elif be in ("wan", "wan22"):
        primary = "wan22"
        alt = "ltx23_aio_i2v"
    else:
        primary = be or "ltx23_aio_i2v"
        alt = "wan22"

    # Frame budget (research: short pure takes)
    max_sec = {"draft": 3.0, "work": 4.0, "hero": 3.5}[goal]
    if duration_sec > max_sec + 0.25:
        length_note = (
            f"duration {duration_sec:.1f}s > recommended pure-take {max_sec}s — "
            "split shots or FLF/chain last-frame extend"
        )
        frames = int(round(max_sec * 24)) | 1  # odd frames often required
        if frames % 8 != 1:
            frames = (frames // 8) * 8 + 1
    else:
        length_note = None
        frames = int(round(duration_sec * 24))
        if frames < 17:
            frames = 17
        if frames % 8 != 1:
            frames = max(17, (frames // 8) * 8 + 1)

    ltx_profile = goal  # draft|work|hero
    wan_profile = {"draft": "preview", "work": "deliver", "hero": "quality"}[goal]

    steps = {
        "draft": {"ltx": None, "wan": 4},
        "work": {"ltx": None, "wan": 6},
        "hero": {"ltx": None, "wan": 8},
    }[goal]

    cli_parts = [
        "python scripts/generate_i2v.py",
        '-i key.png -o out.mp4',
        f'-p "MOTION ONLY prompt"',
        f"--backend {primary}",
        f"--frames {frames}",
    ]
    if primary.startswith("ltx") or primary == "ltx23_aio_i2v":
        cli_parts.append(f"--ltx-profile {ltx_profile}")
    if primary.startswith("wan"):
        cli_parts.append(f"--profile {wan_profile}")
    if has_end_frame:
        cli_parts.append("--last end.png")

    two_stage_note = (
        "LTX AIO always 2-stage (latent upsample); "
        f"profile={ltx_profile} tunes upscale IC strength "
        + ("0.55 hero" if ltx_profile == "hero" else "0.45 work / 0.4 draft")
    )
    return {
        "goal": goal,
        "backend": primary,
        "backend_alt": alt,
        "ltx_profile": ltx_profile,
        "wan_profile": wan_profile,
        "two_stage": True if primary.startswith("ltx") else None,
        "frames": frames,
        "fps": 24,
        "duration_sec_target": round(frames / 24, 2),
        "face_closeup": face_closeup,
        "dialogue": dialogue,
        "length_warning": length_note,
        "steps_hint": steps,
        "still_qa": "Open keyframe; reject broken anatomy/identity before I2V",
        "post_stack": recommend_post(
            goal="delivery" if goal == "hero" else "work",
            face_closeup=face_closeup,
            dialogue=dialogue,
            soft_clip=(goal == "hero"),
        ),
        "cli_example": " ".join(cli_parts),
        "episode_plan_cli": (
            "python scripts/clip_quality.py episode-plan -e EP --phase full"
        ),
        "rules": [
            "I2V prompt = motion/camera only (no wardrobe/face essay)",
            "Approve still before motion (shot_qa / open file)",
            "≤97 frames pure I2V; longer → chain FLF / last-frame",
            "Pure I2V soft-caps long frames (profile max_pure_i2v_sec); --allow-long-i2v to force",
            "After gen: face enhance on CU · upscale for delivery (not during gen)",
            "Chain intermediates: avoid heavy recompress (crf low / prores if stitching many)",
            two_stage_note,
        ],
        "failure_preflight": (
            'python scripts/failure_note.py search "freeze OR blur OR face OR framing"'
        ),
        "research": [
            "Wan 2.2 edge on still detail; LTX 2.3 default for speed/long/audio (factory A/B)",
            "Community: more steps fixes Wan blur; Euler; dual high/low noise polish",
            "LTX: work 720p start; CFG ~3–3.5; hero short clips; AIO always 2-stage + IC LoRA",
            "Episode: draft all → work → hero only showcase (clip_quality episode-plan)",
            "FLF/keyframe planning beats one long take for identity",
        ],
    }


def recommend_post(
    *,
    goal: str = "work",
    face_closeup: bool = False,
    dialogue: bool = False,
    soft_clip: bool = False,
) -> dict[str, Any]:
    """Recommend post-generation polish chain (does not run tools)."""
    goal = (goal or "work").strip().lower()
    steps: list[dict[str, str]] = []
    if face_closeup or dialogue:
        steps.append(
            {
                "id": "face_enhance",
                "when": "face smear / CU after I2V or S2V",
                "cli": "python scripts/generate_wan22_face_enhance.py -i clip.mp4 -o clip_face.mp4",
            }
        )
    if goal in ("delivery", "deliver", "hero", "master", "work"):
        media_goal = "delivery" if goal in ("delivery", "deliver", "hero", "master") else "batch"
        steps.append(
            {
                "id": "upscale_pick",
                "when": "resolution polish after structure is OK",
                "cli": (
                    f"python scripts/upscale_recommend.py pick --media video "
                    f"--goal {media_goal} --domain photo"
                ),
            }
        )
        if goal in ("hero", "master", "delivery", "deliver"):
            steps.append(
                {
                    "id": "upscale_video",
                    "when": "apply recommended backend (ESRGAN default; SeedVR2 hero)",
                    "cli": (
                        "python scripts/upscale_video.py -i clip.mp4 -o clip_1080.mp4 "
                        "--style photo --preset deliver_1080"
                    ),
                }
            )
    if soft_clip:
        steps.append(
            {
                "id": "seedvr2_opt",
                "when": "AI softness / blur recovery (slow)",
                "cli": (
                    "python scripts/upscale_video.py -i clip.mp4 -o clip_hero.mp4 "
                    "--backend seedvr2 --preset deliver_1080"
                ),
            }
        )
    if dialogue:
        steps.append(
            {
                "id": "audio_check",
                "when": "lips/audio already muxed — do not re-encode lossy many times",
                "cli": "ffprobe -hide_banner clip.mp4",
            }
        )
    return {
        "goal": goal,
        "steps": steps,
        "skip_if": "do not upscale before fixing freeze/identity — regenerate motion first",
    }


def plan_episode_quality(
    episode_id: str,
    *,
    phase: str = "draft",
    shots: str = "all_approved",
    hero_shots: str | None = None,
    face_closeup_ids: str | None = None,
    require_approved: bool = True,
) -> dict[str, Any]:
    """Plan draft → work → hero CLI steps for an episode (does not run Comfy).

    phase:
      draft  — scout motion for approved keyframes
      work   — default production tier
      hero   — re-gen only hero_shots (or clip-approved) at hero + polish hints
      full   — emit draft then work then hero sequence
    """
    from lib.story_package import StoryPackage, validate_episode_id

    if not validate_episode_id(episode_id):
        return {"ok": False, "error": f"invalid episode id: {episode_id}"}
    try:
        story = StoryPackage.load(episode_id)
    except FileNotFoundError:
        return {"ok": False, "error": f"episode missing: {episode_id}"}

    phase = (phase or "draft").strip().lower()
    if phase not in ("draft", "work", "hero", "full"):
        phase = "draft"

    all_shots = sorted(story.shots(), key=lambda s: s.get("order", 0))
    if shots in ("all", "all_approved", "*"):
        selected = list(all_shots)
    else:
        want = {x.strip() for x in shots.split(",") if x.strip()}
        selected = [s for s in all_shots if s.get("shot_id") in want]

    if require_approved or shots == "all_approved":
        selected = [
            s
            for s in selected
            if s.get("keyframe_status") == "approved"
            or (not require_approved and shots != "all_approved")
        ]

    hero_set: set[str] = set()
    if hero_shots:
        hero_set = {x.strip() for x in hero_shots.split(",") if x.strip()}
    else:
        # Default hero candidates: clip already approved, or marked quality=hero
        for s in selected:
            sid = str(s.get("shot_id") or "")
            if s.get("clip_status") == "approved":
                hero_set.add(sid)
            if str(s.get("quality") or s.get("ltx_profile") or "").lower() in (
                "hero",
                "showcase",
                "quality",
            ):
                hero_set.add(sid)

    face_set: set[str] = set()
    if face_closeup_ids:
        face_set = {x.strip() for x in face_closeup_ids.split(",") if x.strip()}
    else:
        for s in selected:
            st = str(s.get("shot_type") or s.get("framing") or "").lower()
            if any(k in st for k in ("cu", "close", "face", "ecu", "bcus")):
                face_set.add(str(s.get("shot_id") or ""))

    shot_ids = [str(s.get("shot_id")) for s in selected if s.get("shot_id")]
    steps: list[dict[str, Any]] = []

    def _episode_i2v_cli(prof: str, ids: list[str] | None = None) -> str:
        sh = ",".join(ids) if ids else "all_approved"
        return (
            f"python scripts/episode_i2v.py -e {episode_id} "
            f"--shots {sh} --ltx-profile {prof} --fps 24"
        )

    if phase in ("draft", "full"):
        steps.append(
            {
                "id": "draft_batch",
                "when": "scout motion for all approved keyframes (fast ~540)",
                "cli": _episode_i2v_cli("draft"),
                "shots": shot_ids,
            }
        )
        steps.append(
            {
                "id": "draft_qa",
                "when": "open clips; reject freeze/identity; re-gen bad shots only",
                "cli": f"python scripts/episode_status.py -e {episode_id}",
            }
        )
    if phase in ("work", "full"):
        steps.append(
            {
                "id": "work_batch",
                "when": "production motion at work 720p (default)",
                "cli": _episode_i2v_cli("work"),
                "shots": shot_ids,
            }
        )
        steps.append(
            {
                "id": "work_approve",
                "when": "clip QA + shot_approve --clip approved per cut",
                "cli": (
                    f"python scripts/shot_qa_pack.py -e {episode_id} -s <SID> && "
                    f"python scripts/shot_approve.py -e {episode_id} -s <SID> --clip approved"
                ),
            }
        )
    if phase in ("hero", "full"):
        hids = sorted(hero_set) if hero_set else shot_ids[:1]
        steps.append(
            {
                "id": "hero_regen",
                "when": "re-gen hero candidates only (~1080 + stronger 2-stage IC)",
                "cli": _episode_i2v_cli("hero", hids),
                "shots": hids,
            }
        )
        for hid in hids:
            if hid in face_set or not face_set:
                steps.append(
                    {
                        "id": f"hero_polish_{hid}",
                        "when": f"face/upscale polish for {hid}",
                        "cli": (
                            f"python scripts/clip_quality.py polish "
                            f"-i stories/{episode_id}/clips/work/{hid}.mp4 "
                            f"-o stories/{episode_id}/clips/deliver/{hid}.mp4 "
                            f"--goal delivery --face --seedvr2 --dry-run"
                        ),
                        "shot_id": hid,
                    }
                )

    rules = [
        "Never mass-approve without opening files (Rule 7.3)",
        "Draft all → approve structure → work batch → hero only showcase cuts",
        "I2V prompts motion-only; check with clip_quality check-prompt",
        "AIO is always 2-stage; hero raises upscale IC strength",
        "Pure I2V soft-caps long frames unless --allow-long-i2v",
    ]
    return {
        "ok": True,
        "episode": episode_id,
        "phase": phase,
        "shot_count": len(shot_ids),
        "shot_ids": shot_ids,
        "hero_candidates": sorted(hero_set) if hero_set else [],
        "face_closeups": sorted(face_set),
        "steps": steps,
        "rules": rules,
        "research": [
            "L11: episode draft → work → hero-only approved cuts",
            "L4: AIO 2-stage always on; profile tunes IC LoRA",
        ],
    }


def format_episode_plan(plan: dict[str, Any]) -> str:
    if not plan.get("ok"):
        return f"FAIL {plan.get('error')}"
    lines = [
        f"## Episode quality plan  ep={plan.get('episode')}  phase={plan.get('phase')}",
        f"shots={plan.get('shot_count')}  "
        f"hero_candidates={','.join(plan.get('hero_candidates') or []) or '(none yet)'}",
        f"face_cu={','.join(plan.get('face_closeups') or []) or '(none tagged)'}",
        "",
        "### Steps",
    ]
    for i, s in enumerate(plan.get("steps") or [], 1):
        lines.append(f"{i}. [{s.get('id')}] {s.get('when')}")
        lines.append(f"   {s.get('cli')}")
    lines.append("")
    lines.append("### Rules")
    for r in plan.get("rules") or []:
        lines.append(f"- {r}")
    return "\n".join(lines)


def format_recommendation(rec: dict[str, Any]) -> str:
    lines = [
        f"## Clip quality plan  goal={rec.get('goal')}  backend={rec.get('backend')}",
        f"alt={rec.get('backend_alt')}  frames={rec.get('frames')} "
        f"(~{rec.get('duration_sec_target')}s @24fps)",
        f"ltx_profile={rec.get('ltx_profile')}  wan_profile={rec.get('wan_profile')}  "
        f"two_stage={rec.get('two_stage')}",
        "",
        "### Generate",
        rec.get("cli_example") or "",
        f"still QA: {rec.get('still_qa')}",
    ]
    if rec.get("episode_plan_cli"):
        lines.append(f"episode: {rec['episode_plan_cli']}")
    if rec.get("length_warning"):
        lines.append(f"LENGTH: {rec['length_warning']}")
    lines.append("")
    lines.append("### Rules")
    for r in rec.get("rules") or []:
        lines.append(f"- {r}")
    lines.append("")
    lines.append(f"### Preflight\n{rec.get('failure_preflight')}")
    post = rec.get("post_stack") or {}
    if post.get("steps"):
        lines.append("")
        lines.append("### Post")
        for s in post["steps"]:
            lines.append(f"- [{s['id']}] {s['when']}")
            lines.append(f"  {s['cli']}")
    lines.append("")
    lines.append("### Research anchors")
    for r in rec.get("research") or []:
        lines.append(f"- {r}")
    return "\n".join(lines)


def probe_clip(path: str | Path) -> dict[str, Any]:
    """Lightweight probe via ffprobe if available."""
    import json
    import subprocess

    p = Path(path)
    if not p.is_file():
        return {"ok": False, "error": f"missing {p}"}
    try:
        r = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                "-show_format",
                str(p),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if r.returncode != 0:
            return {"ok": False, "error": r.stderr[:300], "path": str(p)}
        data = json.loads(r.stdout or "{}")
        v = next(
            (s for s in data.get("streams") or [] if s.get("codec_type") == "video"),
            {},
        )
        a = next(
            (s for s in data.get("streams") or [] if s.get("codec_type") == "audio"),
            None,
        )
        w, h = int(v.get("width") or 0), int(v.get("height") or 0)
        dur = float((data.get("format") or {}).get("duration") or 0)
        fps_s = v.get("r_frame_rate") or "0/1"
        try:
            num, den = fps_s.split("/")
            fps = float(num) / float(den) if float(den) else 0.0
        except Exception:
            fps = 0.0
        frames = int(round(dur * fps)) if fps else 0
        tips: list[str] = []
        if dur > 4.2:
            tips.append("clip >~4s pure take — quality risk; prefer split/extend next time")
        if max(w, h) < 720 and max(w, h) > 0:
            tips.append("below 720 long-edge — upscale after structure OK")
        if max(w, h) >= 1280:
            tips.append("already ≥720p class — face polish may help more than heavy upscale")
        if not a:
            tips.append("no audio stream — fine for pure I2V; mux later if needed")
        return {
            "ok": True,
            "path": str(p),
            "width": w,
            "height": h,
            "duration_sec": round(dur, 2),
            "fps": round(fps, 2),
            "approx_frames": frames,
            "has_audio": bool(a),
            "tips": tips,
            "post": recommend_post(
                goal="delivery" if max(w, h) < 1080 else "work",
                face_closeup=max(w, h) > 0 and min(w, h) / max(w, h) > 0.7,
            ),
        }
    except FileNotFoundError:
        return {"ok": False, "error": "ffprobe not found", "path": str(p)}
    except Exception as e:
        return {"ok": False, "error": str(e), "path": str(p)}
