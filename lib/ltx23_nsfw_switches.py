"""Kenpechi LTX 2.3 v2.0 — Fast Groups Bypasser / group switch control.

Mirrors what the UI **Fast Groups Bypasser (rgthree)** does: enable/disable whole
groups by title. Agents never delete nodes; they set node.mode:

  MODE_ALWAYS (0)  — group ON
  MODE_NEVER  (2)  — group OFF (expand skips; same idea as AIO [[P:]] mute)

Source UI (SSOT):
  workflows/human/ltx23_nsfw/ltx23I2VWorkflow_v20.json
  workflows/human/ltx23_nsfw/ltx23DirectorWorkflow_directorV20.json

Bypasser inventory (both packs share model area):

| Bypasser title                 | matchTitle groups                          |
|--------------------------------|--------------------------------------------|
| GGUF Model                     | GGUF model, CLIP GGUF                      |
| Safetensors Model & VAE        | Safetensors Model, Video-Audio VAE         |
| Include VAE Checkpoint         | Included VAE Checkpoint, Included Audio VAE|
| Text Encoder                   | CLIP Safetensors, Included CLIP            |
| Distilled Lora                 | Distilled Lora  (+ DMD Lora label unused)  |
| Sigmas or Steps                | Sigmas, Basic Scheduler  (pick one)        |
| Sage Attention & Torch Settings| Sage Attention, Patch Torch Settings       |
| RIFE Frame Interpolation       | RIFE…, Don't Use RIFE  (pick one)          |
| Final Upscale                  | RTX Super Resolution, Upscale Model        |
| IC Lora (Director only)        | IC Lora                                    |

Default agent profile **gguf_10eros** (matches local 10Eros GGUF + CLIP GGUF):
  ON : GGUF model, CLIP GGUF, Video-Audio VAE, Sigmas, Sage, Torch, Ltx Upscale
  OFF: Safetensors Model, CLIP Safetensors, Checkpoint/Included*, Distilled Lora,
       Basic Scheduler, Final Upscale (RTX + Upscale Model)
  RIFE: optional (default Don't Use RIFE — no flownet required)

Note: UI packs Video-Audio VAE with the Safetensors bypasser. For GGUF the agent
enables **Video-Audio VAE group alone** (still no node deletion — group mode only).
"""

from __future__ import annotations

import copy
import re
from typing import Any

MODE_ALWAYS = 0
MODE_NEVER = 2
MODE_BYPASS = 4  # UI bypass = pass-through (expand rewires; do not convert to NEVER)

# Profile → groups ON (title exact match, case-insensitive). All other *switchable*
# groups listed in SWITCHABLE_GROUPS are forced OFF. Untouched groups keep modes.
PROFILES: dict[str, dict[str, Any]] = {
    "gguf_10eros": {
        "description": (
            "UnetLoaderGGUF 10Eros + DualCLIPLoaderGGUF + Video/Audio VAE. "
            "Sigmas (not BasicScheduler). Distilled Lora group OFF "
            "(use Power Lora DMD/slots as in pack Input area)."
        ),
        "on": [
            "GGUF model",
            "CLIP GGUF",
            "Video-Audio VAE",
            "Sigmas",
            "Sage Attention",
            "Ltx Upscale",
        ],
        "off": [
            "Safetensors Model",
            "CLIP Safetensors",
            "Included VAE Checkpoint",
            "Included Audio VAE",
            "Included CLIP",
            "Distilled Lora",
            "Basic Scheduler",
            "RTX Super Resolution",
            "Upscale Model",
            "IC Lora",
            # torch 2.6 host: fp16_accumulation needs 2.7.1+ — bypass this group
            "Patch Torch Settings",
        ],
        # mutually exclusive pair — default no RIFE for API reliability
        "rife": False,
    },
    "as_saved": {
        "description": (
            "Do not re-pick model groups. Only convert UI bypass (mode 4) → NEVER (2) "
            "so expand omits already-bypassed branches. Honor the JSON as exported."
        ),
        "on": None,
        "off": None,
        "rife": None,
    },
}

# Groups that RIFE bypasser toggles (title may have encoding quirks)
RIFE_ON_GROUP = "RIFE Frame Interpolation"
RIFE_OFF_GROUP_SUBSTR = "use RIFE"  # matches Don't Use RIFE / Don’t Use RIFE


def _node_center(n: dict[str, Any]) -> tuple[float, float]:
    pos = n.get("pos") or [0, 0]
    size = n.get("size") or [0, 0]
    if isinstance(pos, dict):
        x, y = float(pos.get("0", 0)), float(pos.get("1", 0))
    else:
        x, y = float(pos[0]), float(pos[1] if len(pos) > 1 else 0)
    if isinstance(size, dict):
        w, h = float(size.get("0", 0)), float(size.get("1", 0))
    else:
        w = float(size[0]) if size else 0.0
        h = float(size[1]) if size and len(size) > 1 else 0.0
    return x + w / 2.0, y + h / 2.0


def _in_group(n: dict[str, Any], g: dict[str, Any]) -> bool:
    b = g.get("bounding") or g.get("bounding_rect")
    if not b or len(b) < 4:
        return False
    gx, gy, gw, gh = float(b[0]), float(b[1]), float(b[2]), float(b[3])
    cx, cy = _node_center(n)
    return gx <= cx <= gx + gw and gy <= cy <= gy + gh


def _norm_title(t: str | None) -> str:
    if not t:
        return ""
    # normalize nbsp / curly apostrophe
    s = t.replace("\xa0", " ").replace("’", "'").replace("`", "'")
    return re.sub(r"\s+", " ", s).strip().lower()


def _group_title_matches(group_title: str, wanted: str) -> bool:
    return _norm_title(group_title) == _norm_title(wanted)


def _find_groups(workflow: dict[str, Any], wanted: str) -> list[dict[str, Any]]:
    out = []
    for g in workflow.get("groups") or []:
        if _group_title_matches(str(g.get("title") or ""), wanted):
            out.append(g)
    return out


def _find_groups_substr(workflow: dict[str, Any], substr: str) -> list[dict[str, Any]]:
    sub = _norm_title(substr)
    out = []
    for g in workflow.get("groups") or []:
        if sub in _norm_title(str(g.get("title") or "")):
            out.append(g)
    return out


def set_group_mode(
    workflow: dict[str, Any],
    group_title: str,
    mode: int,
    *,
    substr: bool = False,
) -> list[dict[str, Any]]:
    """Set mode for all root nodes whose center lies in matching group(s)."""
    groups = (
        _find_groups_substr(workflow, group_title)
        if substr
        else _find_groups(workflow, group_title)
    )
    changes: list[dict[str, Any]] = []
    if not groups:
        return changes
    for g in groups:
        gtitle = g.get("title")
        for n in workflow.get("nodes") or []:
            if not _in_group(n, g):
                continue
            # Never mute the bypasser nodes themselves or the whole graph dies
            ct = n.get("type") or ""
            if "Bypasser" in ct:
                continue
            old = n.get("mode", 0)
            if old != mode:
                changes.append(
                    {
                        "id": n.get("id"),
                        "type": ct,
                        "title": n.get("title"),
                        "group": gtitle,
                        "from": old,
                        "to": mode,
                    }
                )
            n["mode"] = mode
    return changes


def convert_bypass_to_never(workflow: dict[str, Any]) -> int:
    """Deprecated no-op.

    UI mode 4 is **bypass (pass-through)**, not mute. Converting 4→2 broke
    Distilled-LoRA / Final-Upscale passthrough chains. Expand now handles
    mode 2 (omit) vs mode 4 (passthrough) separately — do not rewrite here.
    """
    return 0


def apply_rife_switch(workflow: dict[str, Any], enable_rife: bool) -> list[dict[str, Any]]:
    """Mutually exclusive: RIFE Frame Interpolation XOR Don't Use RIFE."""
    changes: list[dict[str, Any]] = []
    if enable_rife:
        changes.extend(set_group_mode(workflow, RIFE_ON_GROUP, MODE_ALWAYS))
        for g in _find_groups_substr(workflow, RIFE_OFF_GROUP_SUBSTR):
            t = str(g.get("title") or "")
            if "interpolation" in _norm_title(t):
                continue
            changes.extend(set_group_mode(workflow, t, MODE_BYPASS))
    else:
        changes.extend(set_group_mode(workflow, RIFE_ON_GROUP, MODE_BYPASS))
        for g in _find_groups_substr(workflow, RIFE_OFF_GROUP_SUBSTR):
            t = str(g.get("title") or "")
            if "interpolation" in _norm_title(t):
                continue
            changes.extend(set_group_mode(workflow, t, MODE_ALWAYS))
            # Pack ships Don't Use RIFE VideoCombine as mode=4 — force execute
            for n in workflow.get("nodes") or []:
                if not _in_group(n, g):
                    continue
                n["mode"] = MODE_ALWAYS
            for sg in (workflow.get("definitions") or {}).get("subgraphs") or []:
                name = str(sg.get("name") or "")
                if "don't" in _norm_title(name) or "dont" in _norm_title(name):
                    for inode in sg.get("nodes") or []:
                        inode["mode"] = MODE_ALWAYS
    return changes


def apply_switch_profile(
    workflow: dict[str, Any],
    profile: str = "gguf_10eros",
    *,
    rife: bool | None = None,
) -> dict[str, Any]:
    """Deep-copy workflow and apply named switch profile (group modes only)."""
    if profile not in PROFILES:
        raise ValueError(
            f"unknown profile {profile!r}; known={sorted(PROFILES)}"
        )
    spec = PROFILES[profile]
    wf = copy.deepcopy(workflow)
    log: list[dict[str, Any]] = []

    if profile == "as_saved":
        converted = convert_bypass_to_never(wf)
        wf["_agent_nsfw_profile"] = profile
        wf["_agent_nsfw_switch_log"] = [{"action": "bypass_to_never", "count": converted}]
        return wf

    for title in spec.get("on") or []:
        log.extend(set_group_mode(wf, title, MODE_ALWAYS))
    # OFF switch groups use BYPASS (4) — same as Fast Groups Bypasser —
    # so expand can pass-through (Distilled LoRA / Final Upscale chains).
    for title in spec.get("off") or []:
        log.extend(set_group_mode(wf, title, MODE_BYPASS))

    rife_flag = spec.get("rife") if rife is None else rife
    if rife_flag is not None:
        log.extend(apply_rife_switch(wf, bool(rife_flag)))

    wf["_agent_nsfw_profile"] = profile
    wf["_agent_nsfw_switch_log"] = log
    wf["_agent_nsfw_rife"] = rife_flag
    return wf


def list_profiles() -> list[dict[str, Any]]:
    return [
        {"id": k, "description": v.get("description"), "on": v.get("on"), "off": v.get("off")}
        for k, v in PROFILES.items()
    ]


def list_bypassers(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for n in workflow.get("nodes") or []:
        if "Bypasser" not in (n.get("type") or ""):
            continue
        props = n.get("properties") or {}
        out.append(
            {
                "id": n.get("id"),
                "title": n.get("title"),
                "matchTitle": props.get("matchTitle"),
                "mode": n.get("mode"),
            }
        )
    return out
