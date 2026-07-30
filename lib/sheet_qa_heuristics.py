"""Lightweight post-gen checks for character sheet outputs."""

from __future__ import annotations

import os
from typing import Any


def check_sheet_output(
    path: str,
    preset: dict[str, Any] | None = None,
    size_hint: tuple[int, int] | None = None,
    *,
    tol: int = 32,
) -> dict[str, Any]:
    """Return {ok, reasons} for framing / aspect sanity.

    v1: pixel size vs size_hint + landscape-fullbody ban.
    """
    preset = preset or {}
    reasons: list[str] = []
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
    if sheet in ("costume", "pose", "turnaround", "master") and view in (
        "full",
        "",
    ):
        if w > h:
            reasons.append(f"fullbody_landscape {w}x{h}")

    if sheet == "costume" and view.startswith("detail") and w > h * 1.4:
        # extreme landscape detail is often wrong workflow default
        reasons.append(f"detail_extreme_landscape {w}x{h}")

    return {
        "ok": len(reasons) == 0,
        "reasons": reasons,
        "path": path,
        "size": [w, h],
        "size_hint": list(size_hint) if size_hint else None,
    }
