"""
Multi-view OpenPose strips for character design turnaround sheets.

Community pattern (r/StableDiffusion etc.):
  one wide OpenPose template with front | 3/4 | side | back → ControlNet Pose
  + prompt: character turnaround / reference sheet / orthographic / consistent
"""

from __future__ import annotations

import os
from typing import List, Sequence, Tuple

from lib.comfy_client import WORKSPACE_ROOT
from lib.openpose_maps import (
    OPENPOSE_SUBDIR,
    POSE_DIR,
    draw_openpose_map,
    _head_keypoints,
    _pose_keypoints,
)

BODY_VIEWS = ("stand_front", "stand_qf", "stand_side", "stand_back")
HEAD_VIEWS = ("head_front", "head_qf", "head_side", "head_back")


def _paste_panel(canvas, panel, x0: int) -> None:
    canvas.paste(panel, (x0, 0))


def build_multiview_openpose(
    view_ids: Sequence[str],
    *,
    panel_w: int,
    panel_h: int,
    out_path: str,
    force: bool = False,
) -> str:
    """Compose N OpenPose panels left-to-right into one strip."""
    if not force and os.path.isfile(out_path):
        return out_path
    from PIL import Image

    panels = []
    for vid in view_ids:
        kps = _pose_keypoints(vid)
        panels.append(draw_openpose_map(kps, panel_w, panel_h))
    n = len(panels)
    canvas = Image.new("RGB", (panel_w * n, panel_h), (0, 0, 0))
    for i, p in enumerate(panels):
        _paste_panel(canvas, p, i * panel_w)
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    canvas.save(out_path)
    return out_path


def ensure_body_turnaround_strip(
    panel_w: int = 512,
    panel_h: int = 768,
    force: bool = False,
) -> str:
    out = os.path.join(
        POSE_DIR,
        OPENPOSE_SUBDIR,
        f"multiview_body_F-QF-S-B_{panel_w * 4}x{panel_h}.png",
    )
    return build_multiview_openpose(
        BODY_VIEWS, panel_w=panel_w, panel_h=panel_h, out_path=out, force=force
    )


def ensure_head_turnaround_strip(
    panel_w: int = 512,
    panel_h: int = 512,
    force: bool = False,
) -> str:
    out = os.path.join(
        POSE_DIR,
        OPENPOSE_SUBDIR,
        f"multiview_head_F-QF-S-B_{panel_w * 4}x{panel_h}.png",
    )
    return build_multiview_openpose(
        HEAD_VIEWS, panel_w=panel_w, panel_h=panel_h, out_path=out, force=force
    )


def crop_strip_to_panels(
    strip_path: str,
    out_dir: str,
    n_panels: int,
    name_prefix: str,
) -> List[str]:
    """Split a generated multi-view image into panel PNGs."""
    from PIL import Image

    os.makedirs(out_dir, exist_ok=True)
    im = Image.open(strip_path).convert("RGB")
    w, h = im.size
    pw = w // n_panels
    paths = []
    labels = ["front", "qf", "side", "back"][:n_panels]
    for i, lab in enumerate(labels):
        box = (i * pw, 0, (i + 1) * pw, h)
        panel = im.crop(box)
        op = os.path.join(out_dir, f"{name_prefix}__{lab}.png")
        panel.save(op)
        paths.append(op)
    return paths
