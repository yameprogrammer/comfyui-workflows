#!/usr/bin/env python3
"""One-shot: I2I variations of sonagi cast v1 anchor (pro s88035 c02)."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import os
import sys

from lib.cast_pool import cast_dir, ensure_cast, save_manifest
from lib.comfy_client import utc_now_iso
from lib.contact_sheet import build_contact_sheet
from generate_moody_i2i import generate_i2i_image
from generate_moody_i2i_lock import generate_i2i_lock

CAST = "sonagi_heroine_cast_v2"
REF = os.path.join(
    cast_dir(CAST), "ref", "anchor_pro_s88035_c02.png"
)

BASE = (
    "same exact person as reference photo, mid-20s Korean woman, "
    "oval face, soft jawline, warm brown eyes, straight natural brows, "
    "natural realistic skin texture, shoulder-length dark brown soft wavy hair, "
    "soft neutral expression, medium close-up portrait, front-facing, looking at camera, "
    "cinematic photoreal film still, Moody-grade naturalistic color, soft dramatic lighting, "
    "plain light gray seamless studio background, sharp focus, high detail"
)
NEG = (
    "different person, face morph, identity shift, age change, blonde, glasses, "
    "heavy makeup, cartoon, anime, blurry, watermark, text, logo, busy background"
)

# (tag, eng, mode, model, denoise, seed, prompt_extra)
JOBS = [
    (
        "lock_a",
        "i2i_lock",
        "lock",
        "pro",
        0.42,
        91001,
        "identical face identity, black crew-neck t-shirt, clean studio portrait",
    ),
    (
        "lock_b",
        "i2i_lock",
        "lock",
        "pro",
        0.48,
        91017,
        "identical face identity, soft neutral expression, subtle film grain",
    ),
    (
        "lock_c",
        "i2i_lock",
        "lock",
        "pro",
        0.52,
        91033,
        "identical face identity, slightly softer eyes, rainy-day ballad mood, black crew-neck",
    ),
    (
        "i2i_hair",
        "i2i",
        "i2i",
        "pro",
        0.55,
        91049,
        "same person, hair a touch longer soft waves past shoulders, black crew-neck t-shirt",
    ),
    (
        "i2i_light",
        "i2i",
        "i2i",
        "pro",
        0.58,
        91065,
        "same person, gentle side key light, cinematic restrained contrast, black crew-neck",
    ),
    (
        "i2i_soft",
        "i2i",
        "i2i",
        "pro",
        0.60,
        91081,
        "same person, very slight soft smile, warm brown eyes, black crew-neck t-shirt",
    ),
    (
        "lock_real",
        "i2i_lock",
        "lock",
        "real",
        0.48,
        91097,
        "identical face identity, photoreal skin, black crew-neck t-shirt",
    ),
    (
        "i2i_real",
        "i2i",
        "i2i",
        "real",
        0.56,
        91113,
        "same person, natural softbox lighting, black crew-neck, film still quality",
    ),
    (
        "i2i_wild",
        "i2i",
        "i2i",
        "wild",
        0.50,
        91129,
        "same person, intimate close portrait, soft dramatic light, black crew-neck",
    ),
    (
        "lock_d",
        "i2i_lock",
        "lock",
        "pro",
        0.45,
        91145,
        "identical face identity, center-part soft waves, reserved melancholic warmth, black crew-neck",
    ),
]


def main() -> int:
    if not os.path.isfile(REF):
        print(f"[ERROR] missing anchor ref: {REF}", file=sys.stderr)
        return 2

    root = cast_dir(CAST)
    cand = os.path.join(root, "candidates")
    os.makedirs(cand, exist_ok=True)

    man = ensure_cast(
        CAST,
        prompt=BASE + " | variations from anchor pro s88035 c02 via I2I",
        negative=NEG,
        engines=["i2i_lock", "i2i"],
        notes="Centered on v1 moody_pro s88035 c02; I2I variations not multi-T2I random.",
    )
    entries = list(man.get("candidates") or [])

    anchor_rel = "candidates/sonagi_heroine_cast_v2__eanchor__s88035__c00.png"
    if not any(e.get("file") == anchor_rel for e in entries):
        entries.append(
            {
                "file": anchor_rel,
                "engine": "anchor",
                "seed": 88035,
                "index": 0,
                "tag": "anchor_v1_c02",
                "created_at": utc_now_iso(),
                "status": "anchor",
            }
        )

    ok_n = fail_n = 0
    for i, (tag, eng, mode, model, denoise, seed, extra) in enumerate(JOBS, start=1):
        fn = f"{CAST}__e{eng}__{tag}__s{seed}__c{i:02d}.png"
        out = os.path.join(cand, fn)
        prompt = f"{BASE}, {extra}"
        print(
            f"\n=== [{i}/{len(JOBS)}] {tag} mode={mode} model={model} "
            f"d={denoise} seed={seed} ==="
        )
        if os.path.isfile(out):
            print("  SKIP exists")
            ok_n += 1
        else:
            if mode == "lock":
                r = generate_i2i_lock(
                    REF,
                    prompt,
                    denoise_val=denoise,
                    cfg_val=3.5,
                    model_type=model,
                    output_filename=out,
                    seed=seed,
                    negative_text=NEG,
                    timeout_sec=600,
                    max_denoise=0.58,
                )
            else:
                r = generate_i2i_image(
                    REF,
                    prompt,
                    denoise_val=denoise,
                    cfg_val=1.0,
                    model_type=model,
                    output_filename=out,
                    seed=seed,
                    negative_text=NEG,
                    timeout_sec=600,
                )
            ok = bool(isinstance(r, dict) and r.get("ok")) or os.path.isfile(out)
            if ok:
                ok_n += 1
                print(f"  OK {out}")
            else:
                fail_n += 1
                print(f"  FAIL {r}")
                continue

        rel = f"candidates/{fn}"
        if not any(e.get("file") == rel for e in entries):
            entries.append(
                {
                    "file": rel,
                    "engine": eng,
                    "seed": seed,
                    "index": i,
                    "tag": tag,
                    "model": model,
                    "denoise": denoise,
                    "mode": mode,
                    "created_at": utc_now_iso(),
                    "status": "candidate",
                }
            )

    man["candidates"] = entries
    man["status"] = "open"
    man["anchor"] = {
        "source_cast": "sonagi_heroine_cast_v1",
        "source_file": "candidates/sonagi_heroine_cast_v1__emoody_pro__s88035__c02.png",
        "local_ref": "ref/anchor_pro_s88035_c02.png",
    }
    save_manifest(CAST, man)

    paths = [
        os.path.join(cand, n)
        for n in sorted(os.listdir(cand))
        if n.lower().endswith(".png")
    ]
    sheet = os.path.join(root, "contact_sheet.png")
    cs = build_contact_sheet(paths, sheet, cols=4)
    print(f"\nDone ok={ok_n} fail={fail_n} contact={cs}")
    print(f"next: review {root}")
    return 0 if fail_n == 0 else 31


if __name__ == "__main__":
    raise SystemExit(main())
