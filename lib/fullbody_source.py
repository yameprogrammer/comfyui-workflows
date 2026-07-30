"""Ensure a full-body master exists for turnaround / costume structure edits."""

from __future__ import annotations

import os
import random
import sys
from typing import Any

# scripts/ on path for generate_* CLIs (same pattern as other lib runners)
_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from generate_moody import generate_image
from generate_krea2_identity_edit import run_identity_edit
from lib.character_package import CharacterPackage, asset_filename, load_json, load_presets
from lib.comfy_client import utc_now_iso, write_meta
from lib.profiles import get_profile, size_for_sheet
from lib.prompt_assembly import assemble_prompt
from lib.sheet_prompt_policy import strip_framing_clauses
from lib.sheet_qa_heuristics import check_sheet_output


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

KREA_FULLBODY_INSTRUCTION = (
    "Change framing to FULL BODY head-to-toe model sheet standing front view, "
    "feet and shoes fully visible at the bottom of the frame, entire legs visible, "
    "arms relaxed slightly away from torso, orthographic model-sheet distance, "
    "not a close-up, not cropped at thighs or knees, fully clothed, "
    "plain light gray seamless studio background, even soft lighting"
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
            if "krea2" in low:
                score += 3
            if "upper" in low or "close" in low:
                score -= 5
            ranked.append((score, os.path.join(master_dir, name)))
        ranked.sort(key=lambda x: (-x[0], x[1]))
        if ranked and ranked[0][0] > 0:
            return ranked[0][1]
    return None


def _face_source(pkg: CharacterPackage) -> str | None:
    for rel in (
        ("approved", "master_front.png"),
        ("approved", "master_front_upper.png"),
    ):
        p = pkg.path(*rel)
        if os.path.isfile(p):
            return p
    try:
        p = pkg.default_source_ref()
        if p and os.path.isfile(p):
            return p
    except Exception:
        pass
    return None


def _register_fullbody_asset(
    pkg: CharacterPackage,
    *,
    out_path: str,
    meta_path: str,
    seed: int,
    profile_id: str | None,
    engine: str,
    extra_meta: dict | None = None,
) -> None:
    meta: dict[str, Any] = {}
    if os.path.isfile(meta_path):
        try:
            meta = load_json(meta_path) or {}
        except Exception:
            meta = {}
    meta.update(
        {
            "character_id": pkg.character_id,
            "sheet": "master",
            "view": "full",
            "variant": "neutral_fullbody",
            "preset_id": "master.full_body",
            "profile": profile_id,
            "role": "turnaround_source",
            "engine": engine,
        }
    )
    if extra_meta:
        meta.update(extra_meta)
    write_meta(meta_path, meta)
    rel = os.path.relpath(out_path, pkg.root).replace("\\", "/")
    pkg.manifest.setdefault("assets", []).append(
        {
            "path": rel,
            "meta_path": os.path.relpath(meta_path, pkg.root).replace("\\", "/"),
            "sheet": "master",
            "view": "full",
            "variant": "neutral_fullbody",
            "seed": seed,
            "candidate": 1,
            "preset_id": "master.full_body",
            "engine": engine,
            "created_at": utc_now_iso(),
        }
    )
    pkg.save_manifest()
    pkg.append_changelog(f"generated full-body master {rel} engine={engine}")


def generate_fullbody_master(
    pkg: CharacterPackage,
    model: str = "pro",
    profile_id: str | None = None,
    seed: int | None = None,
    timeout_sec: int = 600,
    *,
    prefer_krea: bool = True,
) -> dict[str, Any]:
    """Generate full-body master into refs/master.

    Prefer krea2_identity from master_front (proven head-to-toe + face lock).
    Fallback: T2I with framing-stripped core.
    """
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
    face = _face_source(pkg)
    preset_view = {"sheet": "master", "view": "full"}

    # --- Path A: krea2 from face ---
    if prefer_krea and face and os.path.isfile(face):
        krea_prompt = assemble_prompt(
            core=(
                "Exact same person as the input photo, preserve face identity, "
                "same eyes nose mouth hair"
            ),
            instruction=KREA_FULLBODY_INSTRUCTION,
            style_lock=wardrobe_block,
            quality_tags=quality,
        )
        short = strip_framing_clauses(positive_core or "")
        if short:
            krea_prompt = assemble_prompt(core=short[:240], instruction=krea_prompt)
        print(
            f"[fullbody] krea2_identity from face {os.path.basename(face)} "
            f"{w}x{h} seed={seed}"
        )
        result = run_identity_edit(
            input_image=face,
            prompt=krea_prompt,
            output_path=out_path,
            seed=seed,
            steps=14,
            denoise=1.0,
            ref_boost=5.5,
            aspect_ratio="2:3 (Portrait Photo)",
            megapixels=max(1.0, (w * h) / (1024.0 * 1024.0)),
            timeout_sec=timeout_sec,
            meta_out=meta_path,
            filename_prefix=f"fullbody_{pkg.character_id}",
        )
        if result.get("ok") and os.path.isfile(out_path):
            qa = check_sheet_output(out_path, preset_view, (w, h), require_feet=True)
            if qa.get("ok"):
                _register_fullbody_asset(
                    pkg,
                    out_path=out_path,
                    meta_path=meta_path,
                    seed=int(result.get("seed") or seed),
                    profile_id=profile.get("id"),
                    engine="krea2_identity",
                    extra_meta={"framing_qa": qa},
                )
                # Promote to approved master_full for downstream
                try:
                    pkg.approve(out_path, "master_full")
                    print(f"[fullbody] approved master_full ← {os.path.basename(out_path)}")
                except Exception as e:
                    print(f"[fullbody] warn master_full approve: {e}")
                result["output_path"] = out_path
                result["framing_qa"] = qa
                return result
            print(
                f"[fullbody] krea2 framing_qa FAIL: {qa.get('reasons')}; fallback T2I"
            )
        else:
            print(
                f"[fullbody] krea2 failed: {result.get('error')} "
                f"{result.get('message')}; fallback T2I"
            )

    # --- Path B: T2I fallback ---
    id_core = strip_framing_clauses(positive_core or "")
    prompt = assemble_prompt(
        core=id_core,
        instruction=full_preset.get("instruction") or FULLBODY_PROMPT_LOCK,
        style_lock=assemble_prompt(
            core=full_preset.get("style_lock", ""),
            instruction=wardrobe_block,
        ),
        quality_tags=quality,
    )
    # Force full-body lock at end
    prompt = assemble_prompt(core=prompt, instruction=FULLBODY_PROMPT_LOCK)
    negative = assemble_prompt(
        core=negative_core,
        instruction=neg_extra,
        style_lock=FULLBODY_NEGATIVE,
    )

    print(f"[fullbody] T2I fallback {w}x{h} seed={seed}")
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

    qa = check_sheet_output(out_path, preset_view, (w, h), require_feet=True)
    _register_fullbody_asset(
        pkg,
        out_path=out_path,
        meta_path=meta_path,
        seed=int(result.get("seed") or seed),
        profile_id=profile.get("id"),
        engine="t2i",
        extra_meta={"framing_qa": qa},
    )
    if qa.get("ok"):
        try:
            pkg.approve(out_path, "master_full")
            print(f"[fullbody] approved master_full ← {os.path.basename(out_path)}")
        except Exception as e:
            print(f"[fullbody] warn master_full approve: {e}")
    else:
        print(
            f"[fullbody] WARN T2I framing_qa FAIL {qa.get('reasons')} "
            f"— file kept but not ideal as fullbody source"
        )
    result["output_path"] = out_path
    result["framing_qa"] = qa
    return result


def ensure_fullbody_source(
    pkg: CharacterPackage,
    model: str = "pro",
    profile_id: str | None = None,
    force_generate: bool = False,
    timeout_sec: int = 600,
) -> str | None:
    """Return path to a full-body source; generate if missing.

    If an existing master_full fails feet-zone QA and force is not set, still
    return it (compat) but log a warning. force_generate regenerates via krea2/T2I.
    """
    existing = find_fullbody_source(pkg)
    if existing and not force_generate:
        qa = check_sheet_output(
            existing, {"sheet": "master", "view": "full"}, None, require_feet=True
        )
        if not qa.get("ok"):
            print(
                f"[fullbody] existing source may be weak framing: "
                f"{os.path.basename(existing)} {qa.get('reasons')} "
                f"(use force_generate to rebuild)"
            )
        return existing

    r = generate_fullbody_master(
        pkg,
        model=model,
        profile_id=profile_id,
        timeout_sec=timeout_sec,
        prefer_krea=True,
    )
    if r.get("ok") and r.get("output_path"):
        return str(r["output_path"])
    return find_fullbody_source(pkg)
