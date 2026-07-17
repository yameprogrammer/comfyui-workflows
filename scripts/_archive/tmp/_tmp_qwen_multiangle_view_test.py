#!/usr/bin/env python3
"""Multi-view angle test: same source → several views, check distinct outputs."""
from __future__ import annotations

import _bootstrap  # noqa: F401
import hashlib
import json
import os
import sys

from generate_qwen_angle import generate_qwen_angle

CANDIDATES = [
    r"characters/sonagi_heroine_v1/approved/master_front.png",
    r"characters/sonagi_heroine_v2/approved/master_front.png",
    r"characters/sho_heroine_v3/approved/master_front.png",
    r"characters/pose_templates/stand_back_1024x1536.png",
]
VIEWS = [
    "body_front",
    "body_qf",
    "body_side",
    "body_back",
    "head_front",
    "head_side",
]
OUT_DIR = r"F:\generated_images\qwen_multiangle_view_test"


def main() -> int:
    src = None
    for c in CANDIDATES:
        if os.path.isfile(c):
            src = c
            break
    if not src:
        print("NO_SOURCE")
        return 2

    print("SOURCE", os.path.abspath(src))
    os.makedirs(OUT_DIR, exist_ok=True)

    results = []
    for i, view in enumerate(VIEWS):
        out = os.path.join(OUT_DIR, f"{view}.png")
        r = generate_qwen_angle(
            src,
            view,
            output_filename=out,
            seed=1000 + i,
            timeout_sec=900,
        )
        ok = bool(r.get("ok")) and os.path.isfile(out)
        h = None
        size = None
        if ok:
            size = os.path.getsize(out)
            with open(out, "rb") as f:
                h = hashlib.md5(f.read()).hexdigest()[:12]
        meta = r.get("meta") or {}
        row = {
            "view": view,
            "ok": ok,
            "error": r.get("error"),
            "message": (r.get("message") or "")[:200],
            "prompt": meta.get("prompt"),
            "horizontal_angle": meta.get("horizontal_angle"),
            "vertical_angle": meta.get("vertical_angle"),
            "zoom": meta.get("zoom"),
            "bytes": size,
            "md5_12": h,
            "path": out if ok else None,
        }
        results.append(row)
        status = "OK" if ok else "FAIL"
        print(
            f"[{status}] {view} h={row['horizontal_angle']} "
            f"v={row['vertical_angle']} z={row['zoom']} "
            f"md5={h} err={r.get('error')}"
        )

    hashes = [x["md5_12"] for x in results if x["md5_12"]]
    unique = len(set(hashes))
    n_ok = sum(1 for x in results if x["ok"])
    print("---")
    print(f"ok={n_ok}/{len(results)} unique_images={unique}/{len(hashes)}")
    if n_ok < len(VIEWS):
        print("RESULT=FAIL_SOME_VIEWS")
        code = 1
    elif unique < 2:
        print("RESULT=FAIL_IDENTICAL_OUTPUTS")
        code = 1
    elif unique < 4:
        print("RESULT=PARTIAL_distinct_but_few")
        code = 0
    else:
        print("RESULT=PASS_angle_change_visible")
        code = 0

    summary = os.path.join(OUT_DIR, "_summary.json")
    with open(summary, "w", encoding="utf-8") as f:
        json.dump(
            {
                "source": os.path.abspath(src),
                "n_ok": n_ok,
                "unique_images": unique,
                "results": results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print("summary", summary)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
