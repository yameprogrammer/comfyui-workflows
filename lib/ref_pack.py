"""
Lightweight identity **ref pack** without full character package.

Toolbox TRANSFORM / ASSETS-lite:
  master face + optional multi-angle + soft lock board → one folder + contact sheet.

Uses existing backends (copy / i2i_lock / qwen_angle). No stories/ or characters/ required.
"""

from __future__ import annotations

import os
import shutil
from typing import Any

from lib.character_consistency import run_identity_i2i
from lib.comfy_client import fail_result, ok_result, utc_now_iso, write_meta
from lib.contact_sheet import build_contact_sheet

DEFAULT_ANGLE_VIEWS = (
    "head_front",
    "head_left_45",
    "head_right_45",
)

# Profile → flags. CLI flags still override.
REF_PACK_PROFILES: dict[str, dict[str, Any]] = {
    "copy": {
        "do_angles": False,
        "do_soft_variants": False,
        "angle_views": (),
        "note": "Copy master only (no Comfy)",
    },
    "quick": {
        "do_angles": False,
        "do_soft_variants": True,
        "angle_views": (),
        "note": "master + clean + 2 expr (I2I only, no angles)",
    },
    "default": {
        "do_angles": True,
        "do_soft_variants": True,
        "angle_views": ("head_left_45",),
        "note": "quick + one side angle (balance speed/coverage)",
    },
    "full": {
        "do_angles": True,
        "do_soft_variants": True,
        "angle_views": DEFAULT_ANGLE_VIEWS,
        "note": "master + clean + expr + front/L45/R45",
    },
}


def resolve_ref_pack_profile(name: str | None) -> dict[str, Any]:
    key = (name or "default").strip().lower()
    if key not in REF_PACK_PROFILES:
        known = ", ".join(REF_PACK_PROFILES)
        raise KeyError(f"Unknown ref_pack profile {name!r}. Known: {known}")
    out = dict(REF_PACK_PROFILES[key])
    out["id"] = key
    return out


def run_ref_pack(
    *,
    input_image: str,
    pack_dir: str,
    model_type: str = "pro",
    seed: int | None = 42,
    do_angles: bool | None = None,
    do_soft_variants: bool | None = None,
    angle_views: list[str] | None = None,
    timeout_sec: int = 600,
    contact_sheet: bool = True,
    profile: str | None = "default",
) -> dict[str, Any]:
    if not os.path.isfile(input_image):
        return fail_result(error="SOURCE_MISSING", message=input_image)

    try:
        prof = resolve_ref_pack_profile(profile)
    except KeyError as e:
        return fail_result(error="BAD_PROFILE", message=str(e))

    if do_angles is None:
        do_angles = bool(prof["do_angles"])
    if do_soft_variants is None:
        do_soft_variants = bool(prof["do_soft_variants"])
    if angle_views is None:
        angle_views = list(prof.get("angle_views") or ())

    os.makedirs(pack_dir, exist_ok=True)
    base_seed = int(seed if seed is not None else 42)
    stages: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    paths: list[str] = []

    # 1) master copy
    master = os.path.join(pack_dir, "master_face.png")
    shutil.copy2(input_image, master)
    paths.append(master)
    artifacts.append({"role": "master_face", "path": os.path.abspath(master)})
    stages.append({"name": "master_face", "ok": True, "path": master})

    # 2) soft cleaned master (identity lock, low denoise)
    if do_soft_variants:
        clean = os.path.join(pack_dir, "master_clean.png")
        r = run_identity_i2i(
            input_image=master,
            prompt="clean studio portrait, same person, neutral soft expression, sharp eyes",
            output_path=clean,
            mode="soft",
            denoise=0.42,
            model_type=model_type,
            seed=base_seed,
            timeout_sec=timeout_sec,
        )
        stages.append(
            {
                "name": "master_clean",
                "ok": bool(r.get("ok")),
                "error": r.get("error"),
                "path": clean if r.get("ok") else None,
            }
        )
        if r.get("ok"):
            paths.append(clean)
            artifacts.append({"role": "master_clean", "path": os.path.abspath(clean)})
            angle_src = clean
        else:
            angle_src = master
    else:
        angle_src = master

    # 3) multi-angle
    if do_angles:
        from generate_qwen_angle import generate_qwen_angle

        views = list(angle_views or DEFAULT_ANGLE_VIEWS)
        for i, view in enumerate(views):
            out = os.path.join(pack_dir, f"angle_{view}.png")
            try:
                ar = generate_qwen_angle(
                    angle_src,
                    view,
                    output_filename=out,
                    seed=base_seed + 10 + i,
                    timeout_sec=timeout_sec,
                )
            except Exception as e:
                ar = fail_result(error="ANGLE_EXCEPTION", message=str(e))
            ok = bool(ar.get("ok"))
            stages.append(
                {
                    "name": f"angle_{view}",
                    "ok": ok,
                    "error": ar.get("error"),
                    "path": out if ok else None,
                }
            )
            if ok:
                paths.append(out)
                artifacts.append({"role": f"angle_{view}", "path": os.path.abspath(out)})

    # 4) soft expression board (optional mini)
    if do_soft_variants:
        for j, (vid, prompt, d) in enumerate(
            (
                ("expr_smile", "soft natural smile, same outfit, head-and-shoulders", 0.46),
                ("expr_neutral", "neutral calm expression, same outfit, head-and-shoulders", 0.44),
            )
        ):
            out = os.path.join(pack_dir, f"{vid}.png")
            r = run_identity_i2i(
                input_image=angle_src,
                prompt=prompt,
                output_path=out,
                mode="soft",
                denoise=d,
                model_type=model_type,
                seed=base_seed + 20 + j,
                timeout_sec=timeout_sec,
            )
            ok = bool(r.get("ok"))
            stages.append({"name": vid, "ok": ok, "error": r.get("error"), "path": out if ok else None})
            if ok:
                paths.append(out)
                artifacts.append({"role": vid, "path": os.path.abspath(out)})

    sheet_path = None
    if contact_sheet and len(paths) >= 2:
        sheet_path = os.path.join(pack_dir, "contact_sheet.png")
        cs = build_contact_sheet(paths, sheet_path, cols=3)
        if cs.get("ok"):
            artifacts.append({"role": "contact_sheet", "path": cs["output_path"]})
            sheet_path = cs["output_path"]

    # Prefer cleaned master as primary identity ref for downstream tools
    primary = master
    for role in ("master_clean", "master_face"):
        for a in artifacts:
            if a.get("role") == role and a.get("path") and os.path.isfile(a["path"]):
                primary = a["path"]
                break
        else:
            continue
        break

    meta = {
        "mode": "ref_pack",
        "tool": "generate_ref_pack",
        "profile": prof.get("id"),
        "profile_note": prof.get("note"),
        "source_image": os.path.abspath(input_image),
        "pack_dir": os.path.abspath(pack_dir),
        "primary_ref": os.path.abspath(primary),
        "seed_base": base_seed,
        "stages": stages,
        "artifacts": artifacts,
        "contact_sheet": sheet_path,
        "created_at": utc_now_iso(),
        "note": (
            "One-shot identity ref pack — not characters/<id>. "
            "Use primary_ref as -i for character_consistent / i2v / style_transfer."
        ),
        "next_tools": [
            "generate_character_consistent --mode lock -i <primary_ref>",
            "generate_i2v -i <primary_ref> --motion-preset idle",
            "generate_style_transfer --mode preset --style anime -i <primary_ref>",
            "character_promote / character package if you need long-term SSOT",
        ],
    }
    meta_path = os.path.join(pack_dir, "ref_pack.meta.json")
    write_meta(meta_path, meta)

    manifest = {
        "kind": "oneshot_ref_pack",
        "version": 1,
        "profile": prof.get("id"),
        "primary_ref": os.path.abspath(primary),
        "files": {a["role"]: a["path"] for a in artifacts if a.get("path")},
        "created_at": meta["created_at"],
    }
    manifest_path = os.path.join(pack_dir, "manifest.json")
    write_meta(manifest_path, manifest)

    readme_path = os.path.join(pack_dir, "README.md")
    try:
        with open(readme_path, "w", encoding="utf-8") as fh:
            fh.write("# One-shot ref pack\n\n")
            fh.write("Lightweight identity board — **not** a `characters/<id>` package.\n\n")
            fh.write(f"- **Profile:** `{prof.get('id')}` — {prof.get('note')}\n")
            fh.write(f"- **Primary ref (use as `-i`):** `{os.path.basename(primary)}`\n")
            fh.write(f"- **Source:** `{os.path.abspath(input_image)}`\n\n")
            fh.write("## Files\n\n")
            for a in artifacts:
                if a.get("path"):
                    fh.write(f"- `{a['role']}`: `{os.path.basename(a['path'])}`\n")
            fh.write("\n## Next (examples)\n\n")
            fh.write("```bash\n")
            fh.write(
                f"python scripts/generate_character_consistent.py --mode lock "
                f"-i \"{primary}\" -p \"cafe table, soft smile\" -o scene.png\n"
            )
            fh.write(
                f"python scripts/generate_i2v.py -i \"{primary}\" "
                f"--motion-preset idle -o clip.mp4\n"
            )
            fh.write("```\n")
    except OSError:
        readme_path = None

    ok_core = any(
        s.get("ok") and s.get("name") in ("master_face", "master_clean") for s in stages
    )
    if not ok_core:
        return fail_result(error="REF_PACK_FAILED", stages=stages, meta=meta)
    partial = not all(s.get("ok") for s in stages if s.get("name") != "master_face")
    return ok_result(
        output_path=sheet_path or primary,
        pack_dir=os.path.abspath(pack_dir),
        primary_ref=os.path.abspath(primary),
        artifacts=artifacts,
        stages=stages,
        meta=meta,
        meta_path=meta_path,
        manifest_path=os.path.abspath(manifest_path),
        readme_path=os.path.abspath(readme_path) if readme_path else None,
        partial=partial,
    )
