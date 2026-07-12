"""Run LTX 2.3 IA2V using the user's successful AIO API graph (not a mini rewrite).

Template source: history of manual success producing ltx2_00060-audio.mp4
(~94s). Nodes include half-res stage-1, latent upscale, stage-2 refine,
TrimAudioDuration, DualClipLoaderGGUF, GGUFLoaderKJ, multi LoRA, VHS combine.
"""
from __future__ import annotations

import copy
import json
import math
import os
from pathlib import Path
from typing import Any

from lib.comfy_client import WORKSPACE_ROOT

DEFAULT_TEMPLATE = os.path.join(
    WORKSPACE_ROOT,
    "workflows",
    "agent",
    "ltx23_ia2v_from_manual_success_05473dc9.json",
)

# Manual success used longer_edge=1024, aspect 9:16 → 576x1024
DEFAULT_LONGER_EDGE = 1024
DEFAULT_FPS = 24


def load_template(path: str | None = None) -> dict[str, Any]:
    p = path or os.environ.get("AGENT_LTX_AIO_TEMPLATE") or DEFAULT_TEMPLATE
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "api_graph" in data:
        return data
    # raw API graph file
    return {"api_graph": data, "prompt_id": None, "note": "raw graph"}


def _set_input(node: dict[str, Any], key: str, value: Any) -> None:
    node.setdefault("inputs", {})[key] = value


def build_ia2v_live_api(
    *,
    image_name: str,
    audio_name: str,
    prompt: str,
    negative: str = "animation, cartoon, text",
    seed: int | None = None,
    audio_duration_sec: float | None = None,
    clip_length_sec: float | None = None,
    trim_start_sec: float = 0.0,
    longer_edge: int | None = None,
    aspect: str = "9:16",
    fps: int = DEFAULT_FPS,
    filename_prefix: str = "agent_ltx_ia2v",
    template_path: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (api_graph, meta) with inputs injected into the manual success template."""
    pack = load_template(template_path)
    g: dict[str, Any] = copy.deepcopy(pack["api_graph"])

    # --- derive lengths (same rules as human IA2V usage) ---
    if audio_duration_sec is None or audio_duration_sec <= 0:
        audio_duration_sec = 3.0
    # clip slightly longer than audio is OK (user: trim later); default +1.5s
    if clip_length_sec is None or clip_length_sec <= 0:
        clip_length_sec = max(audio_duration_sec + 1.5, audio_duration_sec)
    # trim to full usable speech (not demo 220/10)
    trim_dur = float(audio_duration_sec)
    clip_sec_i = int(math.ceil(float(clip_length_sec) - 1e-9))
    clip_sec_i = max(1, min(clip_sec_i, 20))
    edge = int(longer_edge or DEFAULT_LONGER_EDGE)
    edge = max(512, min(edge, 2048))
    # round longer edge to multiple of 64 (AIO notes)
    edge = int(round(edge / 64.0) * 64)
    fps_i = int(fps if fps and fps > 0 else DEFAULT_FPS)

    # --- inject root ports ---
    if "149" in g:
        _set_input(g["149"], "image", image_name)
    if "412" in g:
        _set_input(g["412"], "audio", audio_name)
        # drop stale audioUI if present
        g["412"].get("inputs", {}).pop("audioUI", None)
    if "1792" in g:
        _set_input(g["1792"], "start_index", float(trim_start_sec))
        _set_input(g["1792"], "duration", float(trim_dur))
    if "196" in g:  # Clip Length slider (seconds)
        _set_input(g["196"], "Xi", clip_sec_i)
        _set_input(g["196"], "Xf", float(clip_sec_i))
        _set_input(g["196"], "isfloatX", 0)
    if "1688" in g:  # Longer Edge
        _set_input(g["1688"], "Xi", edge)
        _set_input(g["1688"], "Xf", float(edge))
        _set_input(g["1688"], "isfloatX", 0)
    if "1774" in g:  # Aspect Ratio combo
        _set_input(g["1774"], "combo", aspect if aspect in (
            "16:9", "9:16", "1:1", "3:2", "2:3", "4:3", "3:4", "original", "custom"
        ) else "9:16")
    if "869" in g:  # fps
        _set_input(g["869"], "value", fps_i)
    if "115" in g and seed is not None:
        _set_input(g["115"], "noise_seed", int(seed))
    if "1797" in g:
        _set_input(g["1797"], "text", prompt)
    if "1798" in g:
        # use Text Multiline, not LLM prompt rewriter
        _set_input(g["1798"], "switch", False)
    if "593" in g:
        _set_input(g["593"], "text", negative or "animation, cartoon, text")
    if "188" in g:
        _set_input(g["188"], "filename_prefix", filename_prefix)
        _set_input(g["188"], "save_output", True)

    meta = {
        "template": pack.get("prompt_id") or Path(template_path or DEFAULT_TEMPLATE).name,
        "template_note": pack.get("note"),
        "image_name": image_name,
        "audio_name": audio_name,
        "trim_start_sec": float(trim_start_sec),
        "trim_duration_sec": float(trim_dur),
        "clip_length_sec": clip_sec_i,
        "longer_edge": edge,
        "aspect": aspect,
        "fps": fps_i,
        "seed": seed,
        "runner": "ltx_aio_live_template",
    }
    return g, meta


def is_live_template_available(path: str | None = None) -> bool:
    p = path or os.environ.get("AGENT_LTX_AIO_TEMPLATE") or DEFAULT_TEMPLATE
    return os.path.isfile(p)
