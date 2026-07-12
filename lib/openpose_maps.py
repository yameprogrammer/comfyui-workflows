"""
OpenPose-style pose maps for Z-Image Union ControlNet.

Community pattern (Z-Image Turbo Fun ControlNet Union 2.1):
  OpenPose / DWPose skeleton RGB map → ControlNet control image (NOT Canny of stick figures).

This module:
  1) Synthesizes BODY_18 OpenPose maps (black bg, colored limbs) for standard sheet poses
  2) Optionally extracts OpenPose from a photo via Comfy portable python + controlnet_aux

Refs:
  - https://stable-diffusion-art.com/z-image-controlnet-union/
  - alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union (Pose condition)
"""

from __future__ import annotations

import os
import subprocess
from typing import Dict, List, Optional, Sequence, Tuple

from lib.comfy_client import WORKSPACE_ROOT

POSE_DIR = os.path.join(WORKSPACE_ROOT, "characters", "pose_templates")
OPENPOSE_SUBDIR = "openpose"

# BODY_18 limb pairs (1-based OpenPose indices as in CMU / controlnet_aux)
LIMB_SEQ: List[Tuple[int, int]] = [
    (2, 3),
    (2, 6),
    (3, 4),
    (4, 5),
    (6, 7),
    (7, 8),
    (2, 9),
    (9, 10),
    (10, 11),
    (2, 12),
    (12, 13),
    (13, 14),
    (2, 1),
    (1, 15),
    (15, 17),
    (1, 16),
    (16, 18),
]

LIMB_COLORS = [
    (255, 0, 0),
    (255, 85, 0),
    (255, 170, 0),
    (255, 255, 0),
    (170, 255, 0),
    (85, 255, 0),
    (0, 255, 0),
    (0, 255, 85),
    (0, 255, 170),
    (0, 255, 255),
    (0, 170, 255),
    (0, 85, 255),
    (0, 0, 255),
    (85, 0, 255),
    (170, 0, 255),
    (255, 0, 255),
    (255, 0, 170),
]

JOINT_COLORS = [
    (255, 0, 0),
    (255, 85, 0),
    (255, 170, 0),
    (255, 255, 0),
    (170, 255, 0),
    (85, 255, 0),
    (0, 255, 0),
    (0, 255, 85),
    (0, 255, 170),
    (0, 255, 255),
    (0, 170, 255),
    (0, 85, 255),
    (0, 0, 255),
    (85, 0, 255),
    (170, 0, 255),
    (255, 0, 255),
    (255, 0, 170),
    (255, 0, 85),
]


def _base_front_keypoints() -> List[Optional[Tuple[float, float]]]:
    """Normalized (x, y) BODY_18 for standing front model-sheet pose."""
    # y increases downward
    nose = (0.50, 0.10)
    neck = (0.50, 0.16)
    r_sh = (0.38, 0.20)
    l_sh = (0.62, 0.20)
    r_el = (0.34, 0.32)
    l_el = (0.66, 0.32)
    r_wr = (0.32, 0.44)
    l_wr = (0.68, 0.44)
    r_hip = (0.44, 0.48)
    l_hip = (0.56, 0.48)
    r_kn = (0.44, 0.68)
    l_kn = (0.56, 0.68)
    r_an = (0.44, 0.88)
    l_an = (0.56, 0.88)
    r_eye = (0.47, 0.09)
    l_eye = (0.53, 0.09)
    r_ear = (0.44, 0.10)
    l_ear = (0.56, 0.10)
    # indices 0..17
    return [
        nose,
        neck,
        r_sh,
        r_el,
        r_wr,
        l_sh,
        l_el,
        l_wr,
        r_hip,
        r_kn,
        r_an,
        l_hip,
        l_kn,
        l_an,
        r_eye,
        l_eye,
        r_ear,
        l_ear,
    ]


def _offset(
    kps: Sequence[Optional[Tuple[float, float]]],
    dx: float = 0.0,
    dy: float = 0.0,
) -> List[Optional[Tuple[float, float]]]:
    out: List[Optional[Tuple[float, float]]] = []
    for p in kps:
        if p is None:
            out.append(None)
        else:
            out.append((p[0] + dx, p[1] + dy))
    return out


def _pose_keypoints(template_id: str) -> List[Optional[Tuple[float, float]]]:
    """Return BODY_18 keypoints for a named sheet pose."""
    k = _base_front_keypoints()
    tid = (template_id or "stand_front").lower()

    if tid in ("stand_front", "stand_idle"):
        # slight weight shift
        k[9] = (0.43, 0.68)
        k[10] = (0.42, 0.88)
        return k

    if tid in ("stand_qf", "look_aside"):
        # three-quarter: compress x, shift right shoulder forward
        out = []
        for i, p in enumerate(k):
            if p is None:
                out.append(None)
                continue
            x, y = p
            # perspective squash toward center-right
            x = 0.50 + (x - 0.50) * 0.75 + 0.04
            if i in (2, 3, 4):  # right arm slightly back
                x -= 0.02
            if i in (5, 6, 7):  # left arm forward
                x += 0.03
            out.append((x, y))
        if tid == "look_aside":
            # head turn: nose/eyes shift
            out[0] = (0.56, 0.10)
            out[14] = (0.54, 0.09)
            out[15] = (0.58, 0.09)
            out[16] = (0.52, 0.10)
            out[17] = None  # far ear hidden
        return out

    if tid == "stand_side":
        # strict right-facing profile — collapse shoulders/hips to midline
        cx = 0.52
        return [
            (0.58, 0.10),  # nose forward
            (cx, 0.16),  # neck
            (cx, 0.20),  # R shoulder (near)
            (0.58, 0.32),  # R elbow
            (0.62, 0.44),  # R wrist
            (cx, 0.20),  # L shoulder (overlap)
            (0.48, 0.33),  # L elbow slightly back
            (0.46, 0.44),  # L wrist
            (cx, 0.48),  # R hip
            (0.56, 0.68),  # R knee
            (0.58, 0.88),  # R ankle
            (cx, 0.48),  # L hip
            (0.50, 0.68),  # L knee
            (0.48, 0.88),  # L ankle
            (0.57, 0.09),  # R eye
            None,  # L eye hidden
            (0.54, 0.10),  # R ear
            None,  # L ear
        ]

    if tid == "stand_back":
        # back view — no face, ears outer
        return [
            None,  # nose hidden
            (0.50, 0.16),
            (0.62, 0.20),  # viewer-left = character right when facing away... use mirror of front
            (0.66, 0.32),
            (0.68, 0.44),
            (0.38, 0.20),
            (0.34, 0.32),
            (0.32, 0.44),
            (0.56, 0.48),
            (0.56, 0.68),
            (0.56, 0.88),
            (0.44, 0.48),
            (0.44, 0.68),
            (0.44, 0.88),
            None,
            None,
            (0.58, 0.12),
            (0.42, 0.12),
        ]

    if tid == "walk_side":
        cx = 0.50
        return [
            (0.56, 0.11),
            (cx, 0.17),
            (cx, 0.21),
            (0.60, 0.34),  # front arm
            (0.66, 0.42),
            (cx, 0.21),
            (0.42, 0.34),  # back arm
            (0.38, 0.44),
            (cx, 0.48),
            (0.58, 0.66),  # front leg
            (0.64, 0.86),
            (cx, 0.48),
            (0.44, 0.68),  # back leg
            (0.40, 0.86),
            (0.55, 0.10),
            None,
            (0.52, 0.11),
            None,
        ]

    if tid == "sit_chair":
        return [
            (0.50, 0.14),
            (0.50, 0.20),
            (0.38, 0.24),
            (0.34, 0.36),
            (0.36, 0.48),  # hands near lap
            (0.62, 0.24),
            (0.66, 0.36),
            (0.64, 0.48),
            (0.44, 0.52),
            (0.46, 0.70),  # knee forward
            (0.48, 0.88),
            (0.56, 0.52),
            (0.58, 0.70),
            (0.58, 0.88),
            (0.47, 0.13),
            (0.53, 0.13),
            (0.44, 0.14),
            (0.56, 0.14),
        ]

    if tid == "hands_hips":
        k[3] = (0.36, 0.36)  # R elbow out
        k[4] = (0.40, 0.48)  # R wrist on hip
        k[6] = (0.64, 0.36)
        k[7] = (0.60, 0.48)
        return k

    if tid == "wave":
        k[5] = (0.62, 0.20)
        k[6] = (0.70, 0.18)  # raised elbow
        k[7] = (0.74, 0.10)  # raised wrist
        return k

    return k


def draw_openpose_map(
    keypoints: Sequence[Optional[Tuple[float, float]]],
    width: int = 1024,
    height: int = 1536,
    stick_width: int = 6,
) -> "object":
    """Draw OpenPose BODY_18 map → PIL RGB Image (black background)."""
    from PIL import Image, ImageDraw
    import math

    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    def xy(i: int) -> Optional[Tuple[int, int]]:
        if i < 0 or i >= len(keypoints) or keypoints[i] is None:
            return None
        x, y = keypoints[i]  # type: ignore
        return int(x * width), int(y * height)

    # limbs
    for (a, b), color in zip(LIMB_SEQ, LIMB_COLORS):
        p1 = xy(a - 1)
        p2 = xy(b - 1)
        if not p1 or not p2:
            continue
        draw.line([p1, p2], fill=color, width=stick_width)
        # thick joint blend
        r = max(3, stick_width // 2 + 1)
        draw.ellipse([p1[0] - r, p1[1] - r, p1[0] + r, p1[1] + r], fill=color)
        draw.ellipse([p2[0] - r, p2[1] - r, p2[0] + r, p2[1] + r], fill=color)

    # joints
    for i, color in enumerate(JOINT_COLORS):
        p = xy(i)
        if not p:
            continue
        r = max(4, stick_width)
        draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=color)

    return img


def openpose_map_path(template_id: str, width: int = 1024, height: int = 1536) -> str:
    os.makedirs(os.path.join(POSE_DIR, OPENPOSE_SUBDIR), exist_ok=True)
    return os.path.join(
        POSE_DIR, OPENPOSE_SUBDIR, f"openpose_{template_id}_{width}x{height}.png"
    )


def ensure_openpose_map(
    template_id: str,
    width: int = 1024,
    height: int = 1536,
    force: bool = False,
) -> str:
    """Ensure a synthetic OpenPose map PNG exists for template_id."""
    path = openpose_map_path(template_id, width, height)
    if force or not os.path.isfile(path):
        kps = _pose_keypoints(template_id)
        img = draw_openpose_map(kps, width, height)
        img.save(path)
    return path


def ensure_all_openpose_maps(
    width: int = 1024,
    height: int = 1536,
    force: bool = False,
) -> Dict[str, str]:
    ids = [
        "stand_front",
        "stand_qf",
        "stand_side",
        "stand_back",
        "stand_idle",
        "walk_side",
        "sit_chair",
        "hands_hips",
        "wave",
        "look_aside",
    ]
    return {tid: ensure_openpose_map(tid, width, height, force=force) for tid in ids}


def find_comfy_python() -> Optional[str]:
    candidates = [
        os.environ.get("COMFY_PYTHON"),
        r"F:\ComfyUI_windows_portable\python_embeded\python.exe",
        r"F:\ComfyUI_windows_portable\python_embeded\python",
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def extract_openpose_from_image(
    image_path: str,
    output_path: str,
    *,
    include_hand: bool = True,
    include_face: bool = True,
    comfy_python: str | None = None,
) -> str:
    """
    Run OpenPose detector via Comfy portable python (has torch/cv2 + controlnet_aux).
    Falls back to synthetic stand_front if extraction fails.
    """
    if not os.path.isfile(image_path):
        raise FileNotFoundError(image_path)

    py = comfy_python or find_comfy_python()
    annotators = os.path.join(
        r"F:\ComfyUI_windows_portable\ComfyUI\custom_nodes\comfyui_controlnet_aux\ckpts",
        "lllyasviel",
        "Annotators",
    )
    aux_src = r"F:\ComfyUI_windows_portable\ComfyUI\custom_nodes\comfyui_controlnet_aux\src"

    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    if not py or not os.path.isdir(annotators):
        # fallback synthetic
        ensure_openpose_map("stand_front", force=False)
        from shutil import copy2

        copy2(openpose_map_path("stand_front"), output_path)
        return output_path

    code = f"""
import sys, os
sys.path.insert(0, r"{aux_src}")
from custom_controlnet_aux.open_pose import OpenposeDetector
from PIL import Image
import numpy as np
model = OpenposeDetector.from_pretrained(r"{annotators}")
img = np.array(Image.open(r"{image_path}").convert("RGB"))
out = model(img, include_hand={include_hand}, include_face={include_face}, hand_and_face=True)
if hasattr(out, "save"):
    out.save(r"{output_path}")
else:
    Image.fromarray(np.array(out).astype("uint8")).save(r"{output_path}")
print("OK", r"{output_path}")
"""
    try:
        r = subprocess.run(
            [py, "-c", code],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if r.returncode != 0 or not os.path.isfile(output_path):
            print(f"[openpose extract] fail rc={r.returncode} {r.stderr[-500:]}")
            ensure_openpose_map("stand_front")
            from shutil import copy2

            copy2(openpose_map_path("stand_front"), output_path)
        else:
            print(f"[openpose extract] {output_path}")
    except Exception as e:
        print(f"[openpose extract] exception {e}")
        ensure_openpose_map("stand_front")
        from shutil import copy2

        copy2(openpose_map_path("stand_front"), output_path)
    return output_path
