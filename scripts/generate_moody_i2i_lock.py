#!/usr/bin/env python3
"""
Identity-strong I2I without IPAdapter (always works on Z-Image Moody).

Caps denoise and injects a hard same-person lock phrase. Use as default
identity engine when IPAdapter models/arch are unavailable.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

from generate_moody_i2i import generate_i2i_image

IDENTITY_LOCK = (
    "same exact person as reference photo, identical face identity, "
    "same facial structure eyes nose mouth, same hair color and style, "
    "consistent skin tone, do not change identity"
)


def generate_i2i_lock(
    input_image_path: str,
    prompt_text: str,
    denoise_val: float = 0.5,
    cfg_val: float = 3.5,
    model_type: str = "pro",
    output_filename: str | None = None,
    seed: int | None = None,
    negative_text: str = "",
    core_prefix: str = "",
    core_suffix: str = "",
    meta_out: str | None = None,
    server_address: str = "127.0.0.1:8188",
    timeout_sec: int = 600,
    workflow=None,
    max_denoise: float = 0.58,
) -> dict:
    denoise = min(float(denoise_val), float(max_denoise))
    instr = prompt_text
    if IDENTITY_LOCK not in (prompt_text or ""):
        instr = f"{IDENTITY_LOCK}, {prompt_text}"
    # Prefer lower denoise identity pass
    r = generate_i2i_image(
        input_image_path,
        instr,
        denoise_val=denoise,
        cfg_val=cfg_val,
        model_type=model_type,
        output_filename=output_filename,
        seed=seed,
        negative_text=negative_text
        or "different person, face morph, identity shift, age change, wrong hair",
        core_prefix=core_prefix,
        core_suffix=core_suffix,
        meta_out=meta_out,
        server_address=server_address,
        timeout_sec=timeout_sec,
        workflow=workflow,
    )
    if isinstance(r, dict) and r.get("ok") and r.get("meta"):
        r["meta"]["mode"] = "i2i_lock"
        r["meta"]["engine"] = "i2i_lock"
        r["meta"]["max_denoise"] = max_denoise
    return r
