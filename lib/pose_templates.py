"""Generate simple full-body pose templates for ControlNet Canny turnaround."""

from __future__ import annotations

import os
from typing import Tuple

from lib.comfy_client import WORKSPACE_ROOT

POSE_DIR = os.path.join(WORKSPACE_ROOT, "characters", "pose_templates")

# Maps turnaround view -> template id
VIEW_TO_TEMPLATE = {
    "front": "stand_front",
    "qf": "stand_qf",
    "side": "stand_side",
    "back": "stand_back",
}


def pose_template_path(template_id: str, width: int = 1024, height: int = 1536) -> str:
    os.makedirs(POSE_DIR, exist_ok=True)
    return os.path.join(POSE_DIR, f"{template_id}_{width}x{height}.png")


def ensure_pose_template(template_id: str, width: int = 1024, height: int = 1536) -> str:
    """
    Prefer OpenPose-style maps (Z-Image Union Pose condition).
    Falls back to legacy black stick silhouette only if openpose generation fails.
    """
    try:
        from lib.openpose_maps import ensure_openpose_map

        return ensure_openpose_map(template_id, width=width, height=height, force=False)
    except Exception as e:
        print(f"[pose_templates] openpose map failed ({e}); legacy stick fallback")
    path = pose_template_path(template_id, width, height)
    if not os.path.exists(path):
        generate_pose_template(template_id, path, width, height)
    return path


def ensure_view_pose(view: str, width: int = 1024, height: int = 1536) -> str:
    tid = VIEW_TO_TEMPLATE.get(view, "stand_front")
    return ensure_pose_template(tid, width, height)


def generate_pose_template(
    template_id: str,
    path: str,
    width: int = 1024,
    height: int = 1536,
) -> str:
    """Draw a high-contrast body silhouette suitable for Canny edges."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    cx = width // 2
    # Vertical proportions (head to toe)
    head_y = int(height * 0.10)
    head_r = int(min(width, height) * 0.055)
    neck_y = head_y + head_r + int(height * 0.01)
    shoulder_y = int(height * 0.22)
    hip_y = int(height * 0.48)
    knee_y = int(height * 0.68)
    foot_y = int(height * 0.90)
    shoulder_w = int(width * 0.16)
    hip_w = int(width * 0.12)
    limb = max(8, int(width * 0.025))

    black = (0, 0, 0)

    def line(a, b, w=limb):
        draw.line([a, b], fill=black, width=w)

    def circle(xy, r):
        x, y = xy
        draw.ellipse([x - r, y - r, x + r, y + r], fill=black)

    # Head
    circle((cx, head_y), head_r)
    line((cx, neck_y), (cx, shoulder_y), limb + 2)

    if template_id == "stand_side":
        # Side profile: limbs overlap on x
        # Face direction indicator (nose bump)
        draw.polygon(
            [
                (cx + head_r, head_y),
                (cx + head_r + int(head_r * 0.7), head_y + 4),
                (cx + head_r, head_y + int(head_r * 0.4)),
            ],
            fill=black,
        )
        line((cx, shoulder_y), (cx + int(width * 0.08), int(height * 0.38)), limb)  # front arm
        line((cx, shoulder_y), (cx - int(width * 0.02), hip_y), limb + 4)  # torso
        line((cx, hip_y), (cx + int(width * 0.02), knee_y), limb + 2)
        line((cx + int(width * 0.02), knee_y), (cx + int(width * 0.04), foot_y), limb + 2)
        line((cx, hip_y), (cx - int(width * 0.01), knee_y), limb + 1)
        line((cx - int(width * 0.01), knee_y), (cx - int(width * 0.02), foot_y), limb + 1)

    elif template_id == "stand_back":
        line((cx - shoulder_w, shoulder_y), (cx + shoulder_w, shoulder_y), limb + 2)
        line((cx - shoulder_w, shoulder_y), (cx - shoulder_w - 10, hip_y), limb)
        line((cx + shoulder_w, shoulder_y), (cx + shoulder_w + 10, hip_y), limb)
        line((cx, shoulder_y), (cx, hip_y), limb + 4)
        line((cx - hip_w, hip_y), (cx + hip_w, hip_y), limb + 2)
        line((cx - hip_w // 2, hip_y), (cx - hip_w // 2 - 8, knee_y), limb + 2)
        line((cx + hip_w // 2, hip_y), (cx + hip_w // 2 + 8, knee_y), limb + 2)
        line((cx - hip_w // 2 - 8, knee_y), (cx - hip_w // 2 - 10, foot_y), limb + 2)
        line((cx + hip_w // 2 + 8, knee_y), (cx + hip_w // 2 + 10, foot_y), limb + 2)
        # hair mass on back of head
        draw.ellipse(
            [cx - head_r, head_y - head_r // 2, cx + head_r, head_y + head_r],
            outline=black,
            width=limb,
        )

    elif template_id == "stand_qf":
        # Three-quarter: asymmetric shoulders
        line((cx - int(shoulder_w * 0.7), shoulder_y), (cx + int(shoulder_w * 1.1), shoulder_y), limb + 2)
        line((cx, shoulder_y), (cx + 8, hip_y), limb + 4)
        line((cx - int(shoulder_w * 0.7), shoulder_y), (cx - int(shoulder_w * 0.9), hip_y), limb)
        line((cx + int(shoulder_w * 1.1), shoulder_y), (cx + int(shoulder_w * 1.0), hip_y), limb)
        line((cx - hip_w // 2 + 10, hip_y), (cx - hip_w // 2, knee_y), limb + 2)
        line((cx + hip_w // 2 + 10, hip_y), (cx + hip_w // 2 + 15, knee_y), limb + 2)
        line((cx - hip_w // 2, knee_y), (cx - hip_w // 2 - 5, foot_y), limb + 2)
        line((cx + hip_w // 2 + 15, knee_y), (cx + hip_w // 2 + 18, foot_y), limb + 2)
        # face quarter
        draw.ellipse(
            [cx - int(head_r * 0.3), head_y - head_r, cx + head_r, head_y + head_r],
            fill=black,
        )

    elif template_id == "walk_side":
        # Side mid-stride
        draw.polygon(
            [
                (cx + head_r, head_y),
                (cx + head_r + int(head_r * 0.7), head_y + 4),
                (cx + head_r, head_y + int(head_r * 0.4)),
            ],
            fill=black,
        )
        line((cx, shoulder_y), (cx + int(width * 0.12), int(height * 0.40)), limb)  # front arm
        line((cx, shoulder_y), (cx - int(width * 0.10), int(height * 0.42)), limb)  # back arm
        line((cx, shoulder_y), (cx, hip_y), limb + 4)
        line((cx, hip_y), (cx + int(width * 0.10), knee_y - 20), limb + 2)  # front leg
        line((cx + int(width * 0.10), knee_y - 20), (cx + int(width * 0.14), foot_y), limb + 2)
        line((cx, hip_y), (cx - int(width * 0.08), knee_y), limb + 2)  # back leg
        line((cx - int(width * 0.08), knee_y), (cx - int(width * 0.12), foot_y - 10), limb + 2)

    elif template_id == "sit_chair":
        seat_y = int(height * 0.55)
        line((cx - shoulder_w, shoulder_y), (cx + shoulder_w, shoulder_y), limb + 2)
        line((cx, shoulder_y), (cx, seat_y), limb + 4)
        line((cx - shoulder_w, shoulder_y), (cx - shoulder_w - 5, seat_y - 20), limb)
        line((cx + shoulder_w, shoulder_y), (cx + shoulder_w + 5, seat_y - 20), limb)
        # thighs
        line((cx - hip_w, seat_y), (cx + hip_w + 30, seat_y), limb + 3)
        # lower legs down
        line((cx + hip_w + 20, seat_y), (cx + hip_w + 20, foot_y), limb + 2)
        line((cx - hip_w // 2, seat_y), (cx - hip_w // 2 - 5, foot_y), limb + 2)
        # simple seat
        draw.rectangle(
            [cx - hip_w - 20, seat_y, cx + hip_w + 40, seat_y + limb],
            outline=black,
            width=max(2, limb // 2),
        )

    elif template_id == "hands_hips":
        line((cx - shoulder_w, shoulder_y), (cx + shoulder_w, shoulder_y), limb + 2)
        line((cx, shoulder_y), (cx, hip_y), limb + 4)
        # arms to hips
        line((cx - shoulder_w, shoulder_y), (cx - hip_w - 5, hip_y), limb)
        line((cx + shoulder_w, shoulder_y), (cx + hip_w + 5, hip_y), limb)
        line((cx - hip_w, hip_y), (cx + hip_w, hip_y), limb + 2)
        line((cx - hip_w // 2, hip_y), (cx - hip_w // 2, knee_y), limb + 2)
        line((cx + hip_w // 2, hip_y), (cx + hip_w // 2, knee_y), limb + 2)
        line((cx - hip_w // 2, knee_y), (cx - hip_w // 2, foot_y), limb + 2)
        line((cx + hip_w // 2, knee_y), (cx + hip_w // 2, foot_y), limb + 2)

    elif template_id == "wave":
        line((cx - shoulder_w, shoulder_y), (cx + shoulder_w, shoulder_y), limb + 2)
        line((cx, shoulder_y), (cx, hip_y), limb + 4)
        line((cx - shoulder_w, shoulder_y), (cx - shoulder_w - 5, hip_y), limb)
        # raised arm wave
        line((cx + shoulder_w, shoulder_y), (cx + shoulder_w + 15, int(height * 0.12)), limb)
        line((cx + shoulder_w + 15, int(height * 0.12)), (cx + shoulder_w + 35, int(height * 0.08)), limb)
        line((cx - hip_w, hip_y), (cx + hip_w, hip_y), limb + 2)
        line((cx - hip_w // 2, hip_y), (cx - hip_w // 2, knee_y), limb + 2)
        line((cx + hip_w // 2, hip_y), (cx + hip_w // 2, knee_y), limb + 2)
        line((cx - hip_w // 2, knee_y), (cx - hip_w // 2, foot_y), limb + 2)
        line((cx + hip_w // 2, knee_y), (cx + hip_w // 2, foot_y), limb + 2)

    elif template_id == "look_aside":
        # erase centered head drawn above, redraw offset head (body faces front)
        draw.ellipse(
            [cx - head_r - 2, head_y - head_r - 2, cx + head_r + 2, head_y + head_r + 2],
            fill=(255, 255, 255),
        )
        hx = cx + int(head_r * 0.55)
        circle((hx, head_y), head_r)
        line((hx, neck_y), (cx, shoulder_y), limb + 2)
        line((cx - shoulder_w, shoulder_y), (cx + shoulder_w, shoulder_y), limb + 2)
        line((cx, shoulder_y), (cx, hip_y), limb + 4)
        line((cx - shoulder_w, shoulder_y), (cx - shoulder_w - 5, hip_y), limb)
        line((cx + shoulder_w, shoulder_y), (cx + shoulder_w + 5, hip_y), limb)
        line((cx - hip_w, hip_y), (cx + hip_w, hip_y), limb + 2)
        line((cx - hip_w // 2, hip_y), (cx - hip_w // 2, knee_y), limb + 2)
        line((cx + hip_w // 2, hip_y), (cx + hip_w // 2, knee_y), limb + 2)
        line((cx - hip_w // 2, knee_y), (cx - hip_w // 2, foot_y), limb + 2)
        line((cx + hip_w // 2, knee_y), (cx + hip_w // 2, foot_y), limb + 2)

    else:  # stand_front
        line((cx - shoulder_w, shoulder_y), (cx + shoulder_w, shoulder_y), limb + 2)
        line((cx - shoulder_w, shoulder_y), (cx - shoulder_w - 5, hip_y), limb)
        line((cx + shoulder_w, shoulder_y), (cx + shoulder_w + 5, hip_y), limb)
        line((cx, shoulder_y), (cx, hip_y), limb + 4)
        line((cx - hip_w, hip_y), (cx + hip_w, hip_y), limb + 2)
        line((cx - hip_w // 2, hip_y), (cx - hip_w // 2, knee_y), limb + 2)
        line((cx + hip_w // 2, hip_y), (cx + hip_w // 2, knee_y), limb + 2)
        line((cx - hip_w // 2, knee_y), (cx - hip_w // 2, foot_y), limb + 2)
        line((cx + hip_w // 2, knee_y), (cx + hip_w // 2, foot_y), limb + 2)
        # feet
        line((cx - hip_w // 2, foot_y), (cx - hip_w // 2 - 20, foot_y), limb)
        line((cx + hip_w // 2, foot_y), (cx + hip_w // 2 + 20, foot_y), limb)

    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    img.save(path)
    return path


def ensure_all_turnaround_poses(width: int = 1024, height: int = 1536) -> dict[str, str]:
    out = {}
    for view, tid in VIEW_TO_TEMPLATE.items():
        out[view] = ensure_pose_template(tid, width, height)
    return out
