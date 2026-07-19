"""
Dance / reference-motion orchestration (MOTION shelf) — v1.

Primary: LTX V2V intent=motion (ref video drives body timing + camera).
Fallback: I2V with dance-oriented motion language when no ref video.

Design note: docs/dance_challenge_pipeline_design.md (full challenge line is later).
This module is the agent-callable **one-shot** tool, not the full episode pipe.
"""

from __future__ import annotations

import os
from typing import Any

from lib.comfy_client import fail_result, ok_result, utc_now_iso, write_meta
from lib.ffmpeg_util import probe_duration, run_ffmpeg

MODES = ("ref", "i2v")

# Text-only dance flavor when mode=i2v (no motion video)
DANCE_STYLES: dict[str, dict[str, str]] = {
    "general": {
        "label": "General dance energy",
        "prompt": (
            "full-body dance performance, rhythmic body motion, musical timing, "
            "natural weight shifts, continuous choreography, camera mostly locked or gentle move"
        ),
    },
    "kpop": {
        "label": "K-pop style choreography",
        "prompt": (
            "K-pop choreography energy, sharp hits on beat, clean arm and footwork, "
            "idol performance stage presence, continuous dance motion"
        ),
    },
    "hiphop": {
        "label": "Hip-hop / street",
        "prompt": (
            "hip-hop street dance, bounce and groove, isolations, confident attitude, "
            "full-body freestyle choreography"
        ),
    },
    "wave": {
        "label": "Wave / popping lite",
        "prompt": (
            "wave dance and body rolls, smooth continuous motion through torso and arms, "
            "rhythmic popping accents without freezing"
        ),
    },
    "cute": {
        "label": "Cute / aegyo dance",
        "prompt": (
            "cute short-form dance, bouncy steps, playful hand gestures, "
            "light full-body rhythm, social media dance challenge energy"
        ),
    },
    "slow": {
        "label": "Slow contemporary",
        "prompt": (
            "slow contemporary dance, fluid extensions, graceful weight transfer, "
            "cinematic body motion, continuous soft choreography"
        ),
    },
}


def list_dance_styles() -> list[str]:
    return sorted(DANCE_STYLES.keys())


def format_dance_styles_help() -> str:
    lines = ["id        label"]
    for sid in list_dance_styles():
        lines.append(f"{sid:10s} {DANCE_STYLES[sid]['label']}")
    return "\n".join(lines)


def trim_reference_video(
    video_path: str,
    output_path: str,
    *,
    start_sec: float = 0.0,
    duration_sec: float | None = None,
    timeout_sec: float = 600,
) -> dict[str, Any]:
    """Cut a hook segment for shorter V2V (ffmpeg re-encode)."""
    if not os.path.isfile(video_path):
        return fail_result(error="VIDEO_MISSING", message=video_path)
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    args: list[str] = ["-ss", str(max(0.0, float(start_sec))), "-i", video_path]
    if duration_sec is not None and float(duration_sec) > 0:
        args.extend(["-t", str(float(duration_sec))])
    args.extend(
        [
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            output_path,
        ]
    )
    r = run_ffmpeg(args, timeout_sec=timeout_sec)
    if r.get("ok") and os.path.isfile(output_path):
        r["output_path"] = os.path.abspath(output_path)
    return r


def run_dance_ref(
    *,
    character_image: str,
    output_path: str,
    mode: str = "ref",
    reference_video: str | None = None,
    dance_style: str = "general",
    extra: str = "",
    trim_start_sec: float = 0.0,
    hook_sec: float | None = None,
    strength: float | None = None,
    width: int = 544,
    height: int = 960,
    fps: float = 24.0,
    seed: int | None = None,
    backend: str | None = None,
    i2v_backend: str | None = None,
    audio_path: str | None = None,
    timeout_sec: int = 3600,
    meta_out: str | None = None,
    dry_run: bool = False,
    work_dir: str | None = None,
) -> dict[str, Any]:
    """
    mode=ref  — require reference_video; V2V intent=motion
    mode=i2v  — no video; I2V with dance_style prompt
    """
    mode = (mode or "ref").lower().strip()
    if mode not in MODES:
        return fail_result(error="BAD_MODE", message=f"mode must be one of {MODES}")

    if not os.path.isfile(character_image):
        return fail_result(error="SOURCE_MISSING", message=character_image)

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    stages: list[dict[str, Any]] = []
    meta_extra: dict[str, Any] = {
        "tool": "generate_dance_ref",
        "mode": mode,
        "character_image": os.path.abspath(character_image),
        "created_at": utc_now_iso(),
        "research": "docs/dance_challenge_pipeline_design.md",
        "note": (
            "v1 one-shot dance/ref motion. Full challenge episode pipe is separate. "
            "Quality upper-bound is model-limited (hands/feet/beat sync)."
        ),
    }

    if mode == "ref":
        if not reference_video or not os.path.isfile(reference_video):
            return fail_result(
                error="REF_VIDEO_REQUIRED",
                message="mode=ref needs --reference / -v existing dance video",
            )
        drive = os.path.abspath(reference_video)
        # Optional hook trim
        if (trim_start_sec and float(trim_start_sec) > 0) or (
            hook_sec is not None and float(hook_sec) > 0
        ):
            import tempfile

            td = work_dir or tempfile.mkdtemp(prefix="dance_ref_")
            os.makedirs(td, exist_ok=True)
            trimmed = os.path.join(td, "ref_hook.mp4")
            tr = trim_reference_video(
                drive,
                trimmed,
                start_sec=float(trim_start_sec or 0.0),
                duration_sec=float(hook_sec) if hook_sec is not None else None,
            )
            stages.append(
                {"name": "trim_ref", "ok": bool(tr.get("ok")), "error": tr.get("error")}
            )
            if not tr.get("ok"):
                return fail_result(
                    error=tr.get("error") or "TRIM_FAILED",
                    message=tr.get("message"),
                    stages=stages,
                )
            drive = trimmed
            meta_extra["trimmed_ref"] = drive
            meta_extra["trim_start_sec"] = float(trim_start_sec or 0.0)
            meta_extra["hook_sec"] = hook_sec

        from generate_v2v import generate_v2v

        style_extra = ""
        if dance_style and dance_style in DANCE_STYLES:
            style_extra = DANCE_STYLES[dance_style]["prompt"]
        user_p = ", ".join(x for x in (style_extra, (extra or "").strip()) if x)

        print(
            f"[dance_ref] mode=ref V2V motion drive={drive} "
            f"identity={character_image}"
        )
        r = generate_v2v(
            drive,
            character_image,
            output_path,
            intent="motion",
            prompt=user_p or None,
            strength=strength,
            width=width,
            height=height,
            fps=fps,
            duration_sec=float(hook_sec) if hook_sec is not None else None,
            trim_start_sec=0.0,  # already trimmed if needed
            audio_path=audio_path,
            backend=backend,
            seed=seed,
            timeout_sec=timeout_sec,
            meta_out=meta_out,
            dry_run=dry_run,
        )
        stages.append({"name": "v2v_motion", "ok": bool(r.get("ok")), "error": r.get("error")})
        meta_extra["v2v_intent"] = "motion"
        meta_extra["reference_video"] = os.path.abspath(reference_video)
        meta_extra["drive_video"] = drive
        meta_extra["dance_style"] = dance_style

    else:  # i2v
        style_id = (dance_style or "general").lower()
        if style_id not in DANCE_STYLES:
            return fail_result(
                error="BAD_DANCE_STYLE",
                message=f"unknown style {dance_style!r}; {list_dance_styles()}",
            )
        base = DANCE_STYLES[style_id]["prompt"]
        extra_s = (extra or "").strip()
        prompt = f"{base}, {extra_s}" if extra_s else base
        # length from hook_sec or default ~3s at 16fps
        use_fps = 16
        if hook_sec is not None and float(hook_sec) > 0:
            frames = max(9, int(round(float(hook_sec) * use_fps)))
        else:
            frames = 49
        if frames % 2 == 0:
            frames += 1

        from generate_i2v import DEFAULT_NEGATIVE, generate_i2v

        print(f"[dance_ref] mode=i2v style={style_id} frames={frames} (no ref video)")
        if dry_run:
            r = ok_result(
                dry_run=True,
                prompt=prompt,
                frames=frames,
                output_path=os.path.abspath(output_path),
            )
        else:
            r = generate_i2v(
                input_image_path=character_image,
                prompt_text=prompt,
                negative_text=(
                    DEFAULT_NEGATIVE
                    + ", still image, frozen pose, wrong identity, extra limbs"
                ),
                output_filename=output_path,
                num_frames=frames,
                frame_rate=use_fps,
                seed=seed,
                backend=i2v_backend,
                timeout_sec=timeout_sec,
                meta_out=meta_out,
            )
        stages.append({"name": "i2v_dance", "ok": bool(r.get("ok")), "error": r.get("error")})
        meta_extra["dance_style"] = style_id
        meta_extra["i2v_prompt"] = prompt[:400]
        meta_extra["frames"] = frames

    if not r.get("ok"):
        return fail_result(
            error=r.get("error") or "DANCE_REF_FAILED",
            message=r.get("message"),
            stages=stages,
            meta=meta_extra,
        )

    meta = r.get("meta") if isinstance(r.get("meta"), dict) else {}
    meta.update(meta_extra)
    meta["stages"] = stages
    meta["output_path"] = r.get("output_path") or os.path.abspath(output_path)
    mpath = r.get("meta_path") or meta_out
    if mpath is None and output_path:
        mpath = os.path.splitext(output_path)[0] + ".json"
    if mpath and not dry_run:
        write_meta(mpath, meta)

    return ok_result(
        output_path=meta["output_path"],
        seed=r.get("seed") or seed,
        prompt_id=r.get("prompt_id"),
        meta=meta,
        meta_path=mpath,
        mode=mode,
        stages=stages,
        dry_run=bool(dry_run or r.get("dry_run")),
    )
