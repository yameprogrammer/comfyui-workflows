"""Build a simple contact sheet image from episode stills."""

from __future__ import annotations

import math
import os
from typing import Any


def build_contact_sheet(
    image_paths: list[str],
    output_path: str,
    *,
    cols: int = 3,
    thumb_max: int = 512,
    pad: int = 8,
    bg: tuple[int, int, int] = (24, 24, 24),
) -> dict[str, Any]:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return {
            "ok": False,
            "error": "PIL_MISSING",
            "message": "Pillow not installed; pip install Pillow",
        }

    paths = [p for p in image_paths if os.path.isfile(p)]
    if not paths:
        return {"ok": False, "error": "NO_IMAGES", "message": "no stills"}

    thumbs: list[Any] = []
    labels: list[str] = []
    for p in paths:
        try:
            im = Image.open(p).convert("RGB")
        except Exception:
            continue
        im.thumbnail((thumb_max, thumb_max))
        thumbs.append(im)
        labels.append(os.path.splitext(os.path.basename(p))[0])

    if not thumbs:
        return {"ok": False, "error": "NO_THUMBS", "message": "could not open images"}

    cols = max(1, int(cols))
    rows = int(math.ceil(len(thumbs) / cols))
    cell_w = max(t.size[0] for t in thumbs) + pad * 2
    cell_h = max(t.size[1] for t in thumbs) + pad * 2 + 18
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), bg)
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    for i, (thumb, label) in enumerate(zip(thumbs, labels)):
        r, c = divmod(i, cols)
        x0 = c * cell_w + pad
        y0 = r * cell_h + pad
        sheet.paste(thumb, (x0, y0))
        draw.text((x0, y0 + thumb.size[1] + 2), label, fill=(220, 220, 220), font=font)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    sheet.save(output_path)
    return {
        "ok": True,
        "output_path": os.path.abspath(output_path),
        "count": len(thumbs),
        "cols": cols,
        "rows": rows,
    }
