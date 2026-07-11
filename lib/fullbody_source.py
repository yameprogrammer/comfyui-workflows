"""Ensure a full-body master exists for turnaround / costume structure edits."""

from __future__ import annotations

import os
import random
from typing import Any

from generate_moody import generate_image
from lib.character_package import CharacterPackage, asset_filename, load_presets
from lib.comfy_client import utc_now_iso, write_meta
from lib.profiles import get_profile, size_for_sheet
from lib.prompt_assembly import assemble_prompt


FULLBODY_PROMPT_LOCK = (
    "full body standing character sheet photo, entire body head-to-toe in frame, "
    "feet clearly visible, front view, arms relaxed slightly away from torso, "
    "neutral expression, orthographic model-sheet pose, not a close-up, not a headshot, "
    "not cropped at waist or knees, fully clothed"
)

FULLBODY_NEGATIVE = (
    "nude, naked, topless, bottomless, nsfw, bare breasts, genitals, lingerie only, "
    "close-up, portrait crop, headshot, cropped feet"
)


def find_fullbody_source(pkg: CharacterPackage) -> str | None:
    """Prefer approved master_full, then best full-looking master ref."""
    candidates = [
        pkg.path("approved", "master_full.png"),
        pkg.path("approved", "master_full_body.png"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p

    master_dir = pkg.path("refs", "master")
    if os.path.isdir(master_dir):
        ranked = []
        for name in os.listdir(master_dir):
            if not name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                continue
            low = name.lower()
            score = 0
            if "full" in low:
                score += 10
            if "fullbody" in low or "full_body" in low:
                score += 10
            if "upper" in low or "close" in low:
                score -= 5
            ranked.append((score, os.path.join(master_dir, name)))
        ranked.sort(key=lambda x: (-x[0], x[1]))
        if ranked and ranked[0][0] > 0:
            return ranked[0][1]
    return None


def generate_fullbody_master(
    pkg: CharacterPackage,
    model: str = "pro",
    profile_id: str | None = None,
    seed: int | None = None,
    timeout_sec: int = 600,
) -> dict[str, Any]:
    """T2I a full-body master into refs/master and return generation result dict."""
    profile = get_profile(profile_id or pkg.active_profile_id())
    presets = load_presets()
    full_preset = presets["presets"]["master.full_body"]
    quality = (presets.get("global") or {}).get("quality_tags", "")
    positive_core = pkg.read_positive_core()
    negative_core = pkg.read_negative_core()
    neg_extra = full_preset.get("negative_extra", "")
    wardrobe = (pkg.bible.get("appearance") or {}).get("wardrobe_default") or (
        "black crew-neck t-shirt, light wash blue jeans, white sneakers, fully clothed"
    )
    wardrobe_block = f"wearing {wardrobe}, fully clothed casual outfit"

    # Prefer locked full-body instruction over close-up pilot master text
    prompt = assemble_prompt(
        core=positive_core,
        instruction=full_preset.get("instruction") or FULLBODY_PROMPT_LOCK,
        style_lock=assemble_prompt(
            core=full_preset.get("style_lock", ""),
            instruction=wardrobe_block,
        ),
        quality_tags=quality,
    )
    negative = assemble_prompt(
        core=negative_core,
        instruction=neg_extra,
        style_lock=FULLBODY_NEGATIVE,
    )

    w, h = size_for_sheet(profile, "master", "full")
    seed = seed if seed is not None else random.randint(1, 1125899906842624)
    fname = asset_filename(
        pkg.character_id,
        sheet="master",
        view="full",
        variant="neutral_fullbody",
        seed=seed,
        candidate=1,
    )
    out_path = pkg.path("refs", "master", fname)
    meta_path = pkg.path("meta", os.path.splitext(fname)[0] + ".json")

    print(f"[fullbody] Generating master full-body {w}x{h} seed={seed}")
    result = generate_image(
        prompt_text=prompt,
        model_type=model,
        output_filename=out_path,
        seed=seed,
        negative_text=negative,
        width=w,
        height=h,
        meta_out=meta_path,
        timeout_sec=timeout_sec,
    )
    if not result.get("ok"):
        return result

    meta = result.get("meta") or {}
    meta.update(
        {
            "character_id": pkg.character_id,
            "sheet": "master",
            "view": "full",
            "variant": "neutral_fullbody",
            "preset_id": "master.full_body",
            "profile": profile.get("id"),
            "role": "turnaround_source",
        }
    )
    write_meta(meta_path, meta)
    rel = os.path.relpath(out_path, pkg.root).replace("\\", "/")
    pkg.manifest.setdefault("assets", []).append(
        {
            "path": rel,
            "meta_path": os.path.relpath(meta_path, pkg.root).replace("\\", "/"),
            "sheet": "master",
            "view": "full",
            "variant": "neutral_fullbody",
            "seed": result.get("seed", seed),
            "candidate": 1,
            "preset_id": "master.full_body",
            "created_at": utc_now_iso(),
        }
    )
    pkg.save_manifest()
    pkg.append_changelog(f"generated full-body master {rel}")
    result["output_path"] = out_path
    return result


def ensure_fullbody_source(
    pkg: CharacterPackage,
    model: str = "pro",
    profile_id: str | None = None,
    force_generate: bool = False,
    seed: int | None = None,
    timeout_sec: int = 600,
) -> str | None:
    """Return path to a full-body source image, generating if needed."""
    if not force_generate:
        existing = find_fullbody_source(pkg)
        if existing:
            print(f"[fullbody] using existing: {existing}")
            return existing
    result = generate_fullbody_master(
        pkg,
        model=model,
        profile_id=profile_id,
        seed=seed,
        timeout_sec=timeout_sec,
    )
    if result.get("ok"):
        return result.get("output_path")
    print(f"[fullbody] generation failed: {result.get('error')}")
    return None
