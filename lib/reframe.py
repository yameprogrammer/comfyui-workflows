"""
Shot-size reframe — toolbox CAMERA / TRANSFORM shelf.

Center-weighted crop (and optional letterbox to target aspect) so agents can
get wide / medium / CU variants from one still without a full regenerate.

v1 = deterministic PIL geometry (fast, no Comfy). Optional later: I2I outpaint.
"""

from __future__ import annotations

import os
from typing import Any

from lib.comfy_client import fail_result, ok_result, utc_now_iso, write_meta

# Relative crop window vs min(source side): larger = tighter (more zoom)
SHOT_SIZES: dict[str, dict[str, Any]] = {
    "extreme_wide": {
        "label": "Extreme wide (almost full frame)",
        "zoom": 1.0,
        "focus": "center",
    },
    "wide": {
        "label": "Wide",
        "zoom": 0.92,
        "focus": "center",
    },
    "medium_wide": {
        "label": "Medium wide",
        "zoom": 0.78,
        "focus": "center",
    },
    "medium": {
        "label": "Medium",
        "zoom": 0.62,
        "focus": "center",
    },
    "medium_close": {
        "label": "Medium close-up",
        "zoom": 0.48,
        "focus": "upper",  # bias up for faces
    },
    "close_up": {
        "label": "Close-up",
        "zoom": 0.36,
        "focus": "upper",
    },
    "extreme_close": {
        "label": "Extreme close-up",
        "zoom": 0.24,
        "focus": "upper",
    },
    "insert": {
        "label": "Insert / detail",
        "zoom": 0.28,
        "focus": "center",
    },
}

ALIASES = {
    "ew": "extreme_wide",
    "w": "wide",
    "mw": "medium_wide",
    "m": "medium",
    "ms": "medium",
    "mcu": "medium_close",
    "cu": "close_up",
    "ecu": "extreme_close",
    "detail": "insert",
}


def list_shot_sizes() -> list[str]:
    return list(SHOT_SIZES.keys())


def resolve_shot_size(name: str) -> str:
    key = str(name).strip().lower().replace(" ", "_").replace("-", "_")
    if key in SHOT_SIZES:
        return key
    if key in ALIASES:
        return ALIASES[key]
    known = ", ".join(list_shot_sizes())
    raise KeyError(f"Unknown shot size {name!r}. Known: {known}")


def _crop_box(
    w: int,
    h: int,
    *,
    zoom: float,
    focus: str,
) -> tuple[int, int, int, int]:
    """Return (left, top, right, bottom) crop in source pixels."""
    zoom = max(0.05, min(1.0, float(zoom)))
    cw = max(1, int(round(w * zoom)))
    ch = max(1, int(round(h * zoom)))
    # keep source aspect of crop window = full frame aspect
    # zoom is scale of the window relative to full frame
    left = (w - cw) // 2
    if focus == "upper":
        # face bias: top third center
        top = max(0, int(round((h - ch) * 0.22)))
    elif focus == "lower":
        top = min(h - ch, int(round((h - ch) * 0.65)))
    else:
        top = (h - ch) // 2
    left = max(0, min(left, w - cw))
    top = max(0, min(top, h - ch))
    return left, top, left + cw, top + ch


def reframe_image(
    input_path: str,
    output_path: str,
    *,
    shot_size: str = "medium",
    width: int | None = None,
    height: int | None = None,
    meta_out: str | None = None,
) -> dict[str, Any]:
    """
    Crop by shot-size zoom, then resize to width×height if given
    else keep crop resolution.
    """
    try:
        from PIL import Image
    except ImportError:
        return fail_result(error="PIL_MISSING", message="pip install Pillow")

    if not os.path.isfile(input_path):
        return fail_result(error="SOURCE_MISSING", message=input_path)

    try:
        size_id = resolve_shot_size(shot_size)
    except KeyError as e:
        return fail_result(error="BAD_SHOT_SIZE", message=str(e))

    spec = SHOT_SIZES[size_id]
    im = Image.open(input_path).convert("RGB")
    sw, sh = im.size
    box = _crop_box(sw, sh, zoom=float(spec["zoom"]), focus=str(spec.get("focus") or "center"))
    cropped = im.crop(box)

    tw, th = width, height
    if tw is not None and th is not None:
        tw, th = int(tw), int(th)
        cropped = cropped.resize((tw, th), Image.Resampling.LANCZOS)
    elif (tw is None) ^ (th is None):
        return fail_result(
            error="SIZE_PAIR",
            message="Provide both --width and --height, or neither",
        )

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    cropped.save(output_path)

    meta = {
        "mode": "reframe",
        "shot_size": size_id,
        "label": spec.get("label"),
        "zoom": spec.get("zoom"),
        "focus": spec.get("focus"),
        "source_image": os.path.abspath(input_path),
        "crop_box": list(box),
        "output_size": list(cropped.size),
        "output_path": os.path.abspath(output_path),
        "created_at": utc_now_iso(),
        "engine": "pil_geometry",
        "note": "No generative outpaint; tighter = more zoom crop",
    }
    mpath = meta_out
    if mpath is None:
        mpath = os.path.splitext(output_path)[0] + ".json"
    if mpath:
        write_meta(mpath, meta)

    return ok_result(
        output_path=os.path.abspath(output_path),
        meta=meta,
        meta_path=os.path.abspath(mpath) if mpath else None,
        shot_size=size_id,
    )


def reframe_pack(
    input_path: str,
    pack_dir: str,
    *,
    sizes: list[str] | None = None,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    """Write multiple shot-size reframes + optional contact later by caller."""
    os.makedirs(pack_dir, exist_ok=True)
    ids = sizes or ["wide", "medium", "medium_close", "close_up"]
    arts: list[dict[str, Any]] = []
    stages: list[dict[str, Any]] = []
    for sid in ids:
        try:
            rid = resolve_shot_size(sid)
        except KeyError as e:
            stages.append({"name": sid, "ok": False, "error": str(e)})
            continue
        out = os.path.join(pack_dir, f"reframe_{rid}.png")
        r = reframe_image(
            input_path,
            out,
            shot_size=rid,
            width=width,
            height=height,
        )
        stages.append({"name": rid, "ok": bool(r.get("ok")), "path": r.get("output_path")})
        if r.get("ok"):
            arts.append({"role": rid, "path": r["output_path"]})

    ok_any = any(s.get("ok") for s in stages)
    if not ok_any:
        return fail_result(error="REFRAME_PACK_FAILED", stages=stages)
    return ok_result(
        pack_dir=os.path.abspath(pack_dir),
        artifacts=arts,
        stages=stages,
        output_path=arts[0]["path"] if arts else None,
    )
