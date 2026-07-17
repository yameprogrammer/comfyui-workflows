#!/usr/bin/env python3
"""
I2I identity path (formerly IP-Adapter node inject).

**Deprecated inject:** runtime IPAdapterUnifiedLoader / IPAdapterAdvanced injection
into mini graphs is no longer the default. Production uses Lonecat AIO API preset
``lonecat_i2i_identity`` via generate_moody_i2i / generate_i2i_lock.

Callers (shot_compose, character_expand_sheets) keep the same function name so
engine="ipadapter" still works; it now means "identity-strong Lonecat I2I".
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse

from lib.comfy_client import DEFAULT_SERVER
from generate_moody_i2i_lock import generate_i2i_lock

# Kept for import compatibility; inject is no longer used on the default path.
IDENTITY_LOCK = (
    "same exact person as reference, identical face identity, same facial structure, "
    "same eyes nose mouth proportions, consistent skin tone and hair"
)


def inject_ipadapter(
    api_prompt: dict,
    *,
    load_image_node: str,
    model_source: list,
    weight: float = 0.72,
    preset: str = "PLUS FACE (portraits)",
) -> tuple[dict, str]:
    """Deprecated: do not use. Runtime node inject is removed from production path."""
    raise RuntimeError(
        "inject_ipadapter is deprecated. Use generate_i2i_ipadapter / "
        "generate_i2i_lock → lonecat_i2i_identity (workflow_api_runner). "
        "Do not assemble IPAdapter nodes at runtime."
    )


def generate_i2i_ipadapter(
    input_image_path: str,
    prompt_text: str,
    denoise_val: float = 0.55,
    cfg_val: float = 3.5,
    model_type: str = "pro",
    output_filename: str | None = None,
    seed: int | None = None,
    negative_text: str = "",
    core_prefix: str = "",
    core_suffix: str = "",
    meta_out: str | None = None,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: int = 600,
    workflow: str | None = None,
    ipa_weight: float = 0.72,
    ipa_preset: str = "PLUS FACE (portraits)",
    identity_lock: bool = True,
    *,
    preset: str | None = None,
    family: str | None = None,
    backend: str | None = None,
    width: int | None = None,
    height: int | None = None,
    unet_name: str | None = None,
    max_denoise: float = 0.65,
) -> dict:
    """
    Identity-strong I2I via Lonecat API (same as i2i_lock, slightly higher denoise cap).

    ``ipa_weight`` / ``ipa_preset`` are accepted for CLI/caller compatibility and
    recorded in meta only — no IPAdapter nodes are injected.
    """
    if ipa_weight != 0.72 or ipa_preset != "PLUS FACE (portraits)":
        print(
            f"[note] ipa_weight={ipa_weight} ipa_preset={ipa_preset!r} "
            f"ignored for graph (meta only); Lonecat I2I has no IPA inject"
        )

    # i2i_lock already adds identity phrase; if identity_lock False, use plain instruction
    if identity_lock:
        r = generate_i2i_lock(
            input_image_path,
            prompt_text,
            denoise_val=denoise_val,
            cfg_val=cfg_val,
            model_type=model_type,
            output_filename=output_filename,
            seed=seed,
            negative_text=negative_text,
            core_prefix=core_prefix,
            core_suffix=core_suffix,
            meta_out=meta_out,
            server_address=server_address,
            timeout_sec=timeout_sec,
            workflow=workflow,
            max_denoise=max_denoise,
            preset=preset,
            family=family,
            backend=backend,
            width=width,
            height=height,
            unet_name=unet_name,
        )
    else:
        from generate_moody_i2i import generate_i2i_image

        denoise = min(float(denoise_val), float(max_denoise))
        r = generate_i2i_image(
            input_image_path,
            prompt_text,
            denoise_val=denoise,
            cfg_val=cfg_val,
            model_type=model_type,
            output_filename=output_filename,
            seed=seed,
            negative_text=negative_text,
            core_prefix=core_prefix,
            core_suffix=core_suffix,
            meta_out=meta_out,
            server_address=server_address,
            timeout_sec=timeout_sec,
            workflow=workflow,
            preset=preset,
            family=family,
            backend=backend,
            width=width,
            height=height,
            unet_name=unet_name,
        )

    if isinstance(r, dict) and r.get("ok") and r.get("meta"):
        r["meta"]["mode"] = "i2i_ipadapter"
        r["meta"]["engine"] = "ipadapter_via_lonecat"
        r["meta"]["ipa_preset"] = ipa_preset
        r["meta"]["ipa_weight"] = ipa_weight
        r["meta"]["ipa_inject"] = False
        r["meta"]["note"] = (
            "IPAdapter node inject deprecated; Lonecat lonecat_i2i_identity API path"
        )
    return r


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "I2I identity (Lonecat API). IPAdapter inject removed — "
            "same path as i2i_lock / lonecat_i2i_identity."
        )
    )
    p.add_argument("--input", "-i", required=True)
    p.add_argument("--prompt", "-p", required=True)
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--model", "-m", choices=["real", "pro", "wild"], default="pro")
    p.add_argument("--denoise", "-d", type=float, default=0.55)
    p.add_argument("--cfg", type=float, default=3.5)
    p.add_argument(
        "--weight",
        type=float,
        default=0.72,
        help="Legacy IPA weight (meta only; no inject)",
    )
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--preset", type=str, default=None)
    args = p.parse_args(argv)
    r = generate_i2i_ipadapter(
        args.input,
        args.prompt,
        denoise_val=args.denoise,
        cfg_val=args.cfg,
        model_type=args.model,
        output_filename=args.output,
        seed=args.seed,
        ipa_weight=args.weight,
        timeout_sec=args.timeout,
        preset=args.preset,
    )
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
