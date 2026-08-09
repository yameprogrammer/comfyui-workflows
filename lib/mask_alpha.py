"""Apply a mask image as alpha channel for Comfy LoadImage mask output (slot 1)."""

from __future__ import annotations

from pathlib import Path


def apply_mask_as_alpha(
    image_path: str | Path,
    mask_path: str | Path,
    output_path: str | Path,
    *,
    invert: bool = False,
) -> Path:
    """Write RGBA PNG where alpha = mask luminance (white = keep/inpaint region).

    ComfyUI LoadImage exposes alpha as MASK. Illustrious Detailer Inpaint uses
    LoadImage output slot 1 as the noise/control mask.
    """
    from PIL import Image, ImageOps

    src = Path(image_path)
    msk = Path(mask_path)
    out = Path(output_path)
    if not src.is_file():
        raise FileNotFoundError(f"image missing: {src}")
    if not msk.is_file():
        raise FileNotFoundError(f"mask missing: {msk}")

    im = Image.open(src).convert("RGBA")
    mask = Image.open(msk).convert("L")
    if mask.size != im.size:
        mask = mask.resize(im.size, Image.Resampling.BILINEAR)
    if invert:
        mask = ImageOps.invert(mask)
    r, g, b, _a = im.split()
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.merge("RGBA", (r, g, b, mask)).save(out, format="PNG")
    return out
