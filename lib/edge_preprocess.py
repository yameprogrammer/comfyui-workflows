"""Control-image edge preprocessing without hard dependency on OpenCV."""

from __future__ import annotations

import os


def write_canny_rgb(control_image_path: str, dest_path: str, low: int = 50, high: int = 150) -> str:
    """
    Write an RGB edge map for ControlNet.

    Prefer OpenCV Canny when available; fall back to PIL FIND_EDGES.
    """
    parent = os.path.dirname(dest_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    try:
        import cv2

        img = cv2.imread(control_image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise RuntimeError(f"cv2 failed to read: {control_image_path}")
        edges = cv2.Canny(img, low, high)
        edges_rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
        cv2.imwrite(dest_path, edges_rgb)
        return dest_path
    except Exception:
        pass

    from PIL import Image, ImageFilter, ImageOps

    im = Image.open(control_image_path).convert("L")
    # Boost contrast so stick figures produce strong edges
    im = ImageOps.autocontrast(im)
    edges = im.filter(ImageFilter.FIND_EDGES)
    edges = ImageOps.invert(edges)  # white bg / dark lines often better for some CN; invert for black edges on white
    # Our pose templates are black on white; FIND_EDGES yields bright edges — keep black lines on white
    edges = ImageOps.autocontrast(edges)
    edges_rgb = edges.convert("RGB")
    edges_rgb.save(dest_path)
    return dest_path
