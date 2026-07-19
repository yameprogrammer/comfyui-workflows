"""
Character-consistent still generation policy + orchestration.

Research SSOT: docs/character_consistency_research.md
Backends: Lonecat T2I/I2I identity, Qwen multi-angle, Fun Union ControlNet.
No homemade Comfy graph inject — only validated runners.
"""

from __future__ import annotations

import os
import re
from typing import Any

from lib.comfy_client import fail_result, ok_result, utc_now_iso, write_meta
from lib.contact_sheet import build_contact_sheet

# ---------------------------------------------------------------------------
# Research-backed defaults
# ---------------------------------------------------------------------------

IDENTITY_LOCK = (
    "same exact person as reference photo, identical face identity, "
    "same facial structure eyes nose mouth, same hair color and style, "
    "consistent skin tone, do not change identity"
)

IDENTITY_NEGATIVE = (
    "different person, face morph, identity shift, age change, wrong hair, "
    "wrong ethnicity, face swap artifact, deformed face, extra face"
)

# Denoise ladder (photoreal Lonecat I2I) — see research doc §3
DENOISE_LOCK_DEFAULT = 0.52
DENOISE_LOCK_MAX = 0.58
DENOISE_REMIX_DEFAULT = 0.62
DENOISE_REMIX_MAX = 0.72
DENOISE_SOFT_DEFAULT = 0.45

MODES = ("lock", "remix", "soft", "anchor", "pack", "angle", "pose")

# Mini identity board (Mickmumpitz-style sheet lite)
PACK_VARIANTS: list[dict[str, Any]] = [
    {
        "id": "expr_soft_smile",
        "prompt": "soft natural smile, warm eyes, head-and-shoulders portrait, same outfit",
        "denoise": 0.48,
    },
    {
        "id": "expr_neutral",
        "prompt": "neutral calm expression, straight gaze, head-and-shoulders portrait, same outfit",
        "denoise": 0.46,
    },
    {
        "id": "expr_serious",
        "prompt": "serious focused expression, slight brow tension, head-and-shoulders, same outfit",
        "denoise": 0.48,
    },
    {
        "id": "ward_light_layer",
        "prompt": (
            "same person wearing a simple light jacket over the same base clothes, "
            "standing three-quarter view, studio soft light"
        ),
        "denoise": 0.56,
    },
    {
        "id": "scene_indoor",
        "prompt": (
            "same person sitting at a wooden cafe table, natural window light, "
            "medium shot upper body, holding a ceramic cup"
        ),
        "denoise": 0.55,
    },
    {
        "id": "scene_outdoor",
        "prompt": (
            "same person standing on a quiet city sidewalk at golden hour, "
            "medium full shot, soft backlight, candid"
        ),
        "denoise": 0.58,
    },
]


def mode_denoise_defaults(mode: str) -> tuple[float, float]:
    """Return (default_denoise, max_denoise) for mode."""
    m = (mode or "lock").lower().strip()
    if m == "soft":
        return DENOISE_SOFT_DEFAULT, DENOISE_LOCK_MAX
    if m == "remix":
        return DENOISE_REMIX_DEFAULT, DENOISE_REMIX_MAX
    if m in ("lock", "pack"):
        return DENOISE_LOCK_DEFAULT, DENOISE_LOCK_MAX
    if m == "pose":
        return 0.70, 0.85
    return DENOISE_LOCK_DEFAULT, DENOISE_LOCK_MAX


def strip_face_reessay(prompt: str) -> str:
    """
    Soft strip of common face re-description fluff on I2I paths.
    Research: change-only prompts beat full face essays on img2img.
    """
    if not prompt:
        return ""
    text = prompt.strip()
    # Drop leading "a photo of a woman with ..." style if too face-heavy — keep action tail
    # Conservative: only collapse repeated identity boilerplate we ourselves inject.
    text = re.sub(r"(?i)\bsame exact person as reference photo[,\s]*", "", text)
    text = re.sub(r"(?i)\bidentical face identity[,\s]*", "", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" ,;")
    return text


def assemble_identity_prompt(
    instruction: str,
    *,
    core_prefix: str = "",
    core_suffix: str = "",
    inject_lock: bool = True,
) -> str:
    """Build I2I instruction: optional bible core + lock + change-only action."""
    parts: list[str] = []
    if core_prefix and str(core_prefix).strip():
        parts.append(str(core_prefix).strip())
    if inject_lock:
        parts.append(IDENTITY_LOCK)
    action = strip_face_reessay(instruction or "")
    if action:
        parts.append(action)
    if core_suffix and str(core_suffix).strip():
        parts.append(str(core_suffix).strip())
    return ", ".join(parts)


def assemble_anchor_prompt(prompt: str, *, core_prefix: str = "") -> str:
    """T2I anchor: detailed appearance first (research: face traits must be explicit)."""
    bits = []
    if core_prefix and str(core_prefix).strip():
        bits.append(str(core_prefix).strip())
    bits.append((prompt or "").strip())
    # Light consistency bias for first lockable face
    bits.append(
        "single subject, clear face visible, consistent facial features, "
        "photoreal cinematic portrait, sharp eyes"
    )
    return ", ".join(b for b in bits if b)


def _ensure_parent(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)


def run_anchor(
    *,
    prompt: str,
    output_path: str,
    model_type: str = "pro",
    seed: int | None = None,
    negative: str = "",
    width: int | None = 1024,
    height: int | None = 1024,
    core_prefix: str = "",
    timeout_sec: int = 600,
    meta_out: str | None = None,
) -> dict[str, Any]:
    from generate_moody import generate_image

    final = assemble_anchor_prompt(prompt, core_prefix=core_prefix)
    neg = negative or (
        "multiple people, deformed face, blurry face, watermark, text, logo, "
        "extra limbs, identity soup"
    )
    r = generate_image(
        final,
        model_type=model_type,
        output_filename=output_path,
        seed=seed,
        negative_text=neg,
        width=width,
        height=height,
        meta_out=meta_out,
        timeout_sec=timeout_sec,
    )
    if isinstance(r, dict) and r.get("ok") and r.get("meta"):
        r["meta"]["character_consistency_mode"] = "anchor"
        r["meta"]["identity_policy"] = "t2i_master_face"
    return r


def run_identity_i2i(
    *,
    input_image: str,
    prompt: str,
    output_path: str,
    mode: str = "lock",
    denoise: float | None = None,
    model_type: str = "pro",
    seed: int | None = None,
    negative: str = "",
    core_prefix: str = "",
    core_suffix: str = "",
    width: int | None = None,
    height: int | None = None,
    timeout_sec: int = 600,
    meta_out: str | None = None,
    family: str | None = None,
) -> dict[str, Any]:
    from generate_moody_i2i_lock import generate_i2i_lock

    if not os.path.isfile(input_image):
        return fail_result(error="SOURCE_MISSING", message=input_image)

    default_d, max_d = mode_denoise_defaults(mode)
    d = float(denoise) if denoise is not None else default_d
    # lock phrase injected inside generate_i2i_lock; we still assemble change-only body
    action = strip_face_reessay(prompt)
    if core_prefix:
        action = f"{core_prefix.strip()}, {action}" if action else core_prefix.strip()
    if core_suffix:
        action = f"{action}, {core_suffix.strip()}" if action else core_suffix.strip()

    r = generate_i2i_lock(
        input_image_path=input_image,
        prompt_text=action,
        denoise_val=d,
        model_type=model_type,
        output_filename=output_path,
        seed=seed,
        negative_text=negative or IDENTITY_NEGATIVE,
        max_denoise=max_d,
        width=width,
        height=height,
        timeout_sec=timeout_sec,
        meta_out=meta_out,
        family=family,
    )
    if isinstance(r, dict) and r.get("ok") and r.get("meta"):
        r["meta"]["character_consistency_mode"] = mode
        r["meta"]["identity_policy"] = "i2i_lock_lonecat"
        r["meta"]["denoise_requested"] = d
        r["meta"]["denoise_cap"] = max_d
        r["meta"]["research"] = "docs/character_consistency_research.md"
    return r


def run_angle(
    *,
    input_image: str,
    view: str,
    output_path: str,
    seed: int | None = None,
    extra: str = "",
    timeout_sec: int = 600,
) -> dict[str, Any]:
    from generate_qwen_angle import generate_qwen_angle

    if not os.path.isfile(input_image):
        return fail_result(error="SOURCE_MISSING", message=input_image)
    r = generate_qwen_angle(
        input_image,
        view,
        output_filename=output_path,
        seed=seed,
        extra_prompt=extra or "",
        timeout_sec=timeout_sec,
    )
    if isinstance(r, dict) and r.get("ok") and r.get("meta"):
        r["meta"]["character_consistency_mode"] = "angle"
        r["meta"]["identity_policy"] = "qwen_multiangle"
    return r


def run_pose(
    *,
    input_image: str | None,
    control_image: str,
    prompt: str,
    output_path: str,
    denoise: float | None = None,
    strength: float = 0.75,
    model_type: str = "pro",
    seed: int | None = None,
    negative: str = "",
    core_prefix: str = "",
    timeout_sec: int = 600,
    width: int | None = 1024,
    height: int | None = 1024,
    meta_out: str | None = None,
) -> dict[str, Any]:
    from generate_moody_controlnet import generate_controlnet_image

    if not os.path.isfile(control_image):
        return fail_result(error="CONTROL_MISSING", message=control_image)

    default_d, max_d = mode_denoise_defaults("pose")
    d = min(float(denoise) if denoise is not None else default_d, max_d)
    final = assemble_identity_prompt(
        prompt,
        core_prefix=core_prefix,
        inject_lock=True,
    )
    # API ControlNet: empty latent; identity via prompt + optional face path in meta
    r = generate_controlnet_image(
        input_image_path=input_image or control_image,
        control_image_path=control_image,
        prompt_text=final,
        denoise_val=d,
        control_strength=float(strength),
        model_type=model_type,
        output_filename=output_path,
        seed=seed,
        negative_text=negative or IDENTITY_NEGATIVE,
        core_prefix=core_prefix,
        timeout_sec=timeout_sec,
        meta_out=meta_out,
        empty_latent=True,
        latent_width=width,
        latent_height=height,
    )

    if isinstance(r, dict) and r.get("ok") and r.get("meta"):
        r["meta"]["character_consistency_mode"] = "pose"
        r["meta"]["identity_policy"] = "controlnet_union_plus_lock_prompt"
        r["meta"]["control_strength"] = strength
        if input_image:
            r["meta"]["face_ref"] = os.path.abspath(input_image)
    return r


def run_pack(
    *,
    input_image: str,
    pack_dir: str,
    model_type: str = "pro",
    seed: int | None = 42,
    variants: list[dict[str, Any]] | None = None,
    core_prefix: str = "",
    timeout_sec: int = 600,
    contact_sheet: bool = True,
    width: int | None = None,
    height: int | None = None,
    family: str | None = None,
) -> dict[str, Any]:
    """Generate a small identity board (expressions / wardrobe / scenes)."""
    if not os.path.isfile(input_image):
        return fail_result(error="SOURCE_MISSING", message=input_image)

    os.makedirs(pack_dir, exist_ok=True)
    items = variants or PACK_VARIANTS
    artifacts: list[dict[str, Any]] = []
    stages: list[dict[str, Any]] = []
    paths: list[str] = []
    base_seed = seed if seed is not None else 42

    for i, var in enumerate(items):
        vid = str(var.get("id") or f"v{i:02d}")
        out = os.path.join(pack_dir, f"{vid}.png")
        d = var.get("denoise")
        r = run_identity_i2i(
            input_image=input_image,
            prompt=str(var.get("prompt") or ""),
            output_path=out,
            mode="lock",
            denoise=float(d) if d is not None else None,
            model_type=model_type,
            seed=base_seed + i,
            core_prefix=core_prefix,
            timeout_sec=timeout_sec,
            width=width,
            height=height,
            family=family,
            meta_out=os.path.splitext(out)[0] + ".json",
        )
        ok = bool(r.get("ok"))
        stages.append({"name": vid, "ok": ok, "error": r.get("error"), "path": out if ok else None})
        if ok:
            paths.append(out)
            artifacts.append({"role": vid, "path": os.path.abspath(out)})
        else:
            artifacts.append(
                {
                    "role": f"{vid}_failed",
                    "error": r.get("error"),
                    "message": r.get("message"),
                }
            )

    sheet_path = None
    if contact_sheet and paths:
        sheet_path = os.path.join(pack_dir, "contact_sheet.png")
        cs = build_contact_sheet(paths, sheet_path, cols=3)
        if cs.get("ok"):
            artifacts.append({"role": "contact_sheet", "path": cs["output_path"]})
            sheet_path = cs["output_path"]

    meta = {
        "mode": "character_consistency_pack",
        "source_image": os.path.abspath(input_image),
        "pack_dir": os.path.abspath(pack_dir),
        "seed_base": base_seed,
        "variants": [v.get("id") for v in items],
        "stages": stages,
        "contact_sheet": sheet_path,
        "created_at": utc_now_iso(),
        "research": "docs/character_consistency_research.md",
    }
    meta_path = os.path.join(pack_dir, "pack.meta.json")
    write_meta(meta_path, meta)

    ok_all = all(s.get("ok") for s in stages) and bool(stages)
    if not stages:
        return fail_result(error="PACK_EMPTY", message="no variants")
    if not any(s.get("ok") for s in stages):
        return fail_result(
            error="PACK_ALL_FAILED",
            message="every pack variant failed",
            stages=stages,
            meta=meta,
            meta_path=meta_path,
        )
    return ok_result(
        output_path=sheet_path or paths[0],
        pack_dir=os.path.abspath(pack_dir),
        artifacts=artifacts,
        stages=stages,
        meta=meta,
        meta_path=meta_path,
        partial=not ok_all,
    )


def run_character_consistent(
    *,
    mode: str,
    prompt: str = "",
    input_image: str | None = None,
    output_path: str | None = None,
    control_image: str | None = None,
    view: str | None = None,
    pack_dir: str | None = None,
    denoise: float | None = None,
    model_type: str = "pro",
    seed: int | None = None,
    negative: str = "",
    core_prefix: str = "",
    core_suffix: str = "",
    width: int | None = None,
    height: int | None = None,
    timeout_sec: int = 600,
    meta_out: str | None = None,
    family: str | None = None,
    strength: float = 0.75,
    contact_sheet: bool = True,
) -> dict[str, Any]:
    """Dispatch by mode. Returns comfy-style ok/error dict."""
    m = (mode or "lock").lower().strip()
    if m not in MODES:
        return fail_result(
            error="BAD_MODE",
            message=f"mode must be one of {MODES}, got {mode!r}",
        )

    if m == "anchor":
        if not prompt:
            return fail_result(error="PROMPT_REQUIRED", message="anchor needs -p")
        if not output_path:
            return fail_result(error="OUTPUT_REQUIRED", message="anchor needs -o")
        _ensure_parent(output_path)
        return run_anchor(
            prompt=prompt,
            output_path=output_path,
            model_type=model_type,
            seed=seed,
            negative=negative,
            width=width or 1024,
            height=height or 1024,
            core_prefix=core_prefix,
            timeout_sec=timeout_sec,
            meta_out=meta_out,
        )

    if m == "pack":
        if not input_image:
            return fail_result(error="INPUT_REQUIRED", message="pack needs -i ref image")
        dest = pack_dir or (
            os.path.join(os.path.dirname(os.path.abspath(output_path)), "pack")
            if output_path
            else None
        )
        if not dest:
            return fail_result(
                error="PACK_DIR_REQUIRED",
                message="pack needs --pack-dir or -o parent path",
            )
        return run_pack(
            input_image=input_image,
            pack_dir=dest,
            model_type=model_type,
            seed=seed,
            core_prefix=core_prefix,
            timeout_sec=timeout_sec,
            contact_sheet=contact_sheet,
            width=width,
            height=height,
            family=family,
        )

    if m == "angle":
        if not input_image:
            return fail_result(error="INPUT_REQUIRED", message="angle needs -i")
        if not view:
            return fail_result(
                error="VIEW_REQUIRED",
                message="angle needs --view (e.g. head_front, head_left_45)",
            )
        if not output_path:
            return fail_result(error="OUTPUT_REQUIRED", message="angle needs -o")
        _ensure_parent(output_path)
        return run_angle(
            input_image=input_image,
            view=view,
            output_path=output_path,
            seed=seed,
            extra=prompt or "",
            timeout_sec=timeout_sec,
        )

    if m == "pose":
        if not control_image:
            return fail_result(error="CONTROL_REQUIRED", message="pose needs --control")
        if not prompt:
            return fail_result(error="PROMPT_REQUIRED", message="pose needs -p")
        if not output_path:
            return fail_result(error="OUTPUT_REQUIRED", message="pose needs -o")
        _ensure_parent(output_path)
        return run_pose(
            input_image=input_image,
            control_image=control_image,
            prompt=prompt,
            output_path=output_path,
            denoise=denoise,
            strength=strength,
            model_type=model_type,
            seed=seed,
            negative=negative,
            core_prefix=core_prefix,
            timeout_sec=timeout_sec,
            width=width or 1024,
            height=height or 1024,
            meta_out=meta_out,
        )

    # lock | remix | soft
    if not input_image:
        return fail_result(
            error="INPUT_REQUIRED",
            message=f"{m} needs -i reference face/body image",
        )
    if not prompt:
        return fail_result(error="PROMPT_REQUIRED", message=f"{m} needs -p change instruction")
    if not output_path:
        return fail_result(error="OUTPUT_REQUIRED", message=f"{m} needs -o")
    _ensure_parent(output_path)
    return run_identity_i2i(
        input_image=input_image,
        prompt=prompt,
        output_path=output_path,
        mode=m,
        denoise=denoise,
        model_type=model_type,
        seed=seed,
        negative=negative,
        core_prefix=core_prefix,
        core_suffix=core_suffix,
        width=width,
        height=height,
        timeout_sec=timeout_sec,
        meta_out=meta_out,
        family=family,
    )
