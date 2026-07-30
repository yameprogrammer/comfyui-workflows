"""Lightweight post-gen checks for character sheet outputs."""

from __future__ import annotations

import os
from typing import Any


def extract_lower_body_crop(
    path: str,
    out_path: str,
    *,
    top_frac: float = 0.52,
    target_size: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Crop lower portion of a full-body plate for footwear detail (deterministic).

    ``top_frac`` is the fraction of height discarded from the top (0.52 ≈ keep bottom 48%).
    Optional ``target_size`` (w,h) resizes with LANCZOS after crop for sheet size_hint match.
    """
    from PIL import Image

    if not path or not os.path.isfile(path):
        return {"ok": False, "error": "source_missing", "path": path}
    with Image.open(path) as im:
        im = im.convert("RGB")
        w, h = im.size
        y0 = int(max(0, min(h - 8, h * float(top_frac))))
        crop = im.crop((0, y0, w, h))
        # Prefer square-ish product plate: center-crop width if very tall strip
        cw, ch = crop.size
        if ch > 0 and cw / ch > 1.35:
            side = ch
            x0 = max(0, (cw - side) // 2)
            crop = crop.crop((x0, 0, x0 + side, ch))
        if target_size and len(target_size) >= 2:
            tw, th = int(target_size[0]), int(target_size[1])
            if tw > 0 and th > 0 and (crop.size != (tw, th)):
                crop = crop.resize((tw, th), Image.Resampling.LANCZOS)
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
        crop.save(out_path)
    return {
        "ok": True,
        "path": out_path,
        "size": list(crop.size),
        "source": path,
        "top_frac": top_frac,
    }


def face_zone_score(
    path: str,
    *,
    top_frac: float = 0.32,
) -> dict[str, Any]:
    """Heuristic: skin-like / high-detail content in the top band (face risk).

    Used to fail footwear plates that still show a face CU.
    """
    from PIL import Image

    with Image.open(path) as im:
        rgb = im.convert("RGB")
        w, h = rgb.size
        y1 = max(1, int(h * top_frac))
        crop = rgb.crop((int(w * 0.15), 0, int(w * 0.85), y1))
        crop.thumbnail((96, 96))
        pixels = list(crop.getdata())
    if not pixels:
        return {"score": 0.0, "n": 0}
    skin = 0
    for r, g, b in pixels:
        # rough skin / face-ish: mid warm tones, not pure gray bg
        if r > 80 and g > 50 and b > 40 and r >= g - 10 and r >= b and (r - b) > 8:
            skin += 1
        elif 40 < (r + g + b) / 3 < 200 and max(r, g, b) - min(r, g, b) > 25:
            # detailed non-flat region (hair/eyes)
            skin += 0.35
    score = min(1.0, skin / len(pixels))
    return {"score": float(score), "n": len(pixels), "band_h": y1}


def bottom_subject_score(
    path: str,
    *,
    bottom_frac: float = 0.14,
    bg_threshold: int = 235,
) -> dict[str, Any]:
    """Heuristic: structured subject in the bottom band (feet/shoes zone).

    Avoids false positives from full-frame dark backgrounds: require mid-luma
    structure near the horizontal center (feet under torso), not pure black void.
    """
    from PIL import Image

    with Image.open(path) as im:
        rgb = im.convert("RGB")
        w, h = rgb.size
        y0 = max(0, int(h * (1.0 - bottom_frac)))
        crop = rgb.crop((int(w * 0.2), y0, int(w * 0.8), h))
        crop.thumbnail((96, 64))
        pixels = list(crop.getdata())
    if not pixels:
        return {"score": 0.0, "n": 0, "mid_frac": 0.0}
    # mid-luma colored/structured pixels ≈ shoes/legs (not pure black floor, not white)
    mid = 0
    for r, g, b in pixels:
        luma = (r + g + b) / 3.0
        mx = max(r, g, b)
        mn = min(r, g, b)
        if 35 <= luma <= 210 and (mx - mn > 12 or 50 <= luma <= 180):
            mid += 1
    score = mid / len(pixels)
    return {
        "score": score,
        "n": len(pixels),
        "mid_frac": score,
        "band": [int(w * 0.2), y0, int(w * 0.8), h],
    }


def check_sheet_output(
    path: str,
    preset: dict[str, Any] | None = None,
    size_hint: tuple[int, int] | None = None,
    *,
    tol: int = 32,
    require_feet: bool | None = None,
    feet_min_score: float = 0.08,
) -> dict[str, Any]:
    """Return {ok, reasons} for framing / aspect / feet-zone sanity.

    v1: pixel size vs size_hint + landscape-fullbody ban + bottom content for full body.
    """
    preset = preset or {}
    reasons: list[str] = []
    extras: dict[str, Any] = {}
    if not path or not os.path.isfile(path):
        return {"ok": False, "reasons": ["file_missing"], "path": path}

    try:
        from PIL import Image

        with Image.open(path) as im:
            w, h = im.size
    except Exception as e:
        return {"ok": False, "reasons": [f"unreadable:{e}"], "path": path}

    sheet = str(preset.get("sheet") or "").lower()
    view = str(preset.get("view") or "").lower()

    if size_hint and len(size_hint) >= 2:
        ew, eh = int(size_hint[0]), int(size_hint[1])
        if abs(w - ew) > tol or abs(h - eh) > tol:
            reasons.append(f"size_mismatch got={w}x{h} expected≈{ew}x{eh}")

    # Full-body plates must be portrait (taller than wide)
    is_fullbody = sheet in ("costume", "pose", "turnaround", "master") and view in (
        "full",
        "",
    )
    if is_fullbody:
        if w > h:
            reasons.append(f"fullbody_landscape {w}x{h}")
        # Auto-enable feet check for full costume/pose unless explicitly disabled
        if require_feet is None:
            require_feet = sheet in ("costume", "pose", "master")
        if require_feet:
            try:
                feet = bottom_subject_score(path)
                extras["feet"] = feet
                if float(feet.get("score") or 0.0) < feet_min_score:
                    reasons.append(
                        f"feet_zone_empty score={feet.get('score'):.3f}<{feet_min_score}"
                    )
            except Exception as e:
                extras["feet_error"] = str(e)

    if sheet == "costume" and view.startswith("detail") and w > h * 1.4:
        # extreme landscape detail is often wrong workflow default
        reasons.append(f"detail_extreme_landscape {w}x{h}")

    # Footwear / feet detail: reject face-in-frame
    if sheet == "costume" and view in (
        "detail_feet",
        "detail_foot",
        "detail_shoes",
    ):
        try:
            fz = face_zone_score(path, top_frac=0.45)
            extras["face_zone"] = fz
            if float(fz.get("score") or 0.0) > 0.22:
                reasons.append(f"face_in_footwear_plate score={fz.get('score'):.3f}")
        except Exception as e:
            extras["face_zone_error"] = str(e)

    out: dict[str, Any] = {
        "ok": len(reasons) == 0,
        "reasons": reasons,
        "path": path,
        "size": [w, h],
        "size_hint": list(size_hint) if size_hint else None,
    }
    out.update(extras)
    return out
