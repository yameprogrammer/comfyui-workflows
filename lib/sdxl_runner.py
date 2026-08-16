"""SDXL photoreal / lightning / pony T2I — CheckpointLoaderSimple.

Not Illustrious (Danbooru XL pack). Not Krea (cinematic default).
"""

from __future__ import annotations

import os
from typing import Any

from lib.still_api import new_seed, run_still_api
from lib.still_model_profiles import (
    COMFY_MODELS,
    SDXL_CKPT_PROFILES,
    resolve_sdxl_profile,
)

FAMILY_SDXL = "sdxl_still"

DEFAULT_NEG = (
    "lowres, worst quality, low quality, jpeg artifacts, blurry, "
    "extra fingers, mutated hands, deformed, watermark, text"
)
PONY_NEG = (
    "score_4, score_5, score_6, worst quality, low quality, "
    "extra fingers, deformed, blurry, jpeg artifacts"
)
PONY_PREFIX = "score_9, score_8_up, score_7_up, "


def check_sdxl_models(model: str | None = None) -> dict[str, Any]:
    names = [model] if model else list(SDXL_CKPT_PROFILES)
    paths: dict[str, str] = {}
    missing: list[str] = []
    for name in names:
        spec = SDXL_CKPT_PROFILES[name]
        p = os.path.join(COMFY_MODELS, "checkpoints", spec["ckpt"])
        paths[name] = p
        if not os.path.isfile(p):
            missing.append(name)
    return {"ok": not missing, "missing": missing, "paths": paths}


def _apply_pony_prefix(prompt: str, *, enabled: bool) -> str:
    if not enabled:
        return prompt
    low = prompt.lower()
    if "score_9" in low or "score_8_up" in low:
        return prompt
    return PONY_PREFIX + prompt


def build_sdxl_t2i_api(
    *,
    prompt: str,
    negative: str,
    ckpt_name: str,
    width: int,
    height: int,
    seed: int,
    steps: int,
    cfg: float,
    sampler: str,
    scheduler: str,
    filename_prefix: str = "sdxl_t2i",
) -> dict[str, Any]:
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": ckpt_name},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["1", 1]},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["1", 1]},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": int(width),
                "height": int(height),
                "batch_size": 1,
            },
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
                "seed": int(seed),
                "steps": int(steps),
                "cfg": float(cfg),
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": 1.0,
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"images": ["6", 0], "filename_prefix": filename_prefix},
        },
    }


def generate_sdxl(
    *,
    prompt: str,
    output_path: str,
    model: str = "juggernaut",
    negative: str | None = None,
    width: int = 1024,
    height: int = 1024,
    seed: int | None = None,
    steps: int | None = None,
    cfg: float | None = None,
    sampler: str | None = None,
    scheduler: str | None = None,
    ckpt_name: str | None = None,
    pony_score_tags: bool = True,
    timeout_sec: float = 600,
    dry_run: bool = False,
) -> dict[str, Any]:
    try:
        spec = resolve_sdxl_profile(model)
    except KeyError as e:
        return {"ok": False, "error": "BAD_MODEL", "message": str(e)}
    chk = check_sdxl_models(spec["name"])
    if not chk["ok"] and not ckpt_name:
        return {
            "ok": False,
            "error": "MISSING_MODELS",
            "message": f"SDXL checkpoint missing: {chk['missing']}",
            "model_check": chk,
        }
    seed_i = new_seed(seed)
    ckpt = ckpt_name or spec["ckpt"]
    steps_i = int(steps if steps is not None else spec["steps"])
    cfg_f = float(cfg if cfg is not None else spec["cfg"])
    samp = sampler or spec["sampler"]
    sched = scheduler or spec["scheduler"]
    is_pony = spec["name"] == "pony"
    pos = _apply_pony_prefix(prompt, enabled=is_pony and pony_score_tags)
    if negative is None:
        neg = PONY_NEG if is_pony else DEFAULT_NEG
    else:
        neg = negative
    api = build_sdxl_t2i_api(
        prompt=pos,
        negative=neg,
        ckpt_name=ckpt,
        width=width,
        height=height,
        seed=seed_i,
        steps=steps_i,
        cfg=cfg_f,
        sampler=samp,
        scheduler=sched,
    )
    print(
        f"SDXL T2I model={spec['name']} {width}x{height} steps={steps_i} "
        f"cfg={cfg_f} {samp}/{sched} seed={seed_i} ckpt={ckpt}"
    )
    return run_still_api(
        api,
        output_path=output_path,
        family=FAMILY_SDXL,
        caller="generate_sdxl",
        seed=seed_i,
        timeout_sec=timeout_sec,
        dry_run=dry_run,
        meta={
            "mode": "sdxl_t2i",
            "model": spec["name"],
            "ckpt": ckpt,
            "prompt": pos[:2000],
            "negative": neg[:800],
            "width": width,
            "height": height,
            "steps": steps_i,
            "cfg": cfg_f,
            "sampler": samp,
            "scheduler": sched,
            "not_default_t2i": True,
            "not_illustrious": True,
        },
    )
