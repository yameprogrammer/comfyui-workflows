"""Run LTX 2.3 AIO by loading the real UI workflow + mode mute switches.

This replaces ad-hoc mini graphs. Mode selection follows Orchestrator [[P:]] table.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

from lib.comfy_client import WORKSPACE_ROOT
from lib.ltx_aio_mode_select import apply_aio_mode_to_ui_workflow, describe_mode
from lib.ltx_aio_ui_expand import expand_ui_workflow_to_api

# Production SSOT: full LTX 2.3 All-In-One for RTX v44 (mode switches re-applied each run)
DEFAULT_UI_WF_BASE = os.path.join(
    WORKSPACE_ROOT,
    "workflows",
    "human",
    "ltx23AllInOneWorkflowForRTX_v44.json",
)
# Optional IA2V-saved snapshot (fallback only)
DEFAULT_UI_WF_IA2V = os.path.join(
    WORKSPACE_ROOT,
    "workflows",
    "human",
    "ltx23AllInOneWorkflowForRTX_v44_IA2V.json",
)
# Back-compat alias
DEFAULT_UI_WF = DEFAULT_UI_WF_BASE


def _load_ui(path: str | None = None) -> dict[str, Any]:
    """Load real AIO UI workflow. Prefer v44 base; env override; then IA2V snapshot."""
    candidates = [
        path,
        os.environ.get("AGENT_LTX_AIO_UI_WORKFLOW"),
        DEFAULT_UI_WF_BASE,
        DEFAULT_UI_WF_IA2V,
        os.path.join(
            r"F:\ComfyUI_workflows", "ltx23AllInOneWorkflowForRTX_v44.json"
        ),
    ]
    p = None
    for c in candidates:
        if c and os.path.isfile(c):
            p = c
            break
    if not p:
        raise FileNotFoundError(
            "LTX AIO UI workflow not found "
            f"(tried {DEFAULT_UI_WF_BASE!r} and fallbacks)"
        )
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _set(api: dict[str, Any], nid: str, key: str, value: Any) -> None:
    if nid not in api:
        return
    api[nid].setdefault("inputs", {})[key] = value


# Default negative append for pure visual I2V/FLF (face drift is LTX's weak spot)
FACE_STABILITY_NEGATIVE = (
    "morphing face, identity shift, face melt, deformed face, asymmetric eyes, "
    "changing facial features, plastic skin, warped mouth, extra teeth"
)

# Motion-prompt suffix: stability only — do not re-describe wardrobe/face beauty essay
FACE_STABILITY_PROMPT_SUFFIX = (
    "keep facial identity stable, natural micro expression only, "
    "no face morph, continuous motion"
)


def apply_ltx_face_stability_loras(
    api: dict[str, Any],
    *,
    enable_detailer: bool = True,
    detailer_strength: float = 0.55,
    distilled_strength: float | None = None,
) -> dict[str, Any]:
    """
    Tune Power Lora Loader (node 211) for face/identity stability.

    AIO ships ``ltx-2-19b-ic-lora-detailer`` **OFF** by default — turning it on
    is the main face-collapse mitigation available without a second pass.
    """
    report: dict[str, Any] = {"detailer": None, "distilled": None, "slots": []}
    node = api.get("211")
    if not isinstance(node, dict):
        report["error"] = "power_lora_node_211_missing"
        return report
    inputs = node.setdefault("inputs", {})
    for key, val in list(inputs.items()):
        if not str(key).startswith("lora_") or not isinstance(val, dict):
            continue
        name = str(val.get("lora") or "")
        low = name.lower().replace("\\", "/")
        slot = {"key": key, "lora": name, "on": val.get("on"), "strength": val.get("strength")}
        if "detailer" in low:
            if enable_detailer:
                val["on"] = True
                val["strength"] = float(detailer_strength)
            slot["on"] = val.get("on")
            slot["strength"] = val.get("strength")
            report["detailer"] = slot
        if distilled_strength is not None and "distilled" in low:
            val["strength"] = float(distilled_strength)
            slot["strength"] = val.get("strength")
            report["distilled"] = slot
        report["slots"].append(slot)
    return report


def build_aio_switched_api(
    *,
    mode: str,
    image_name: str | None = None,
    audio_name: str | None = None,
    last_image_name: str | None = None,
    mid_image_name: str | None = None,
    video_name: str | None = None,
    prompt: str = "",
    negative: str = "animation, cartoon, text",
    seed: int | None = None,
    audio_duration_sec: float | None = None,
    clip_length_sec: float | None = None,
    trim_start_sec: float = 0.0,
    longer_edge: int | None = None,
    aspect: str | None = None,
    fps: int = 24,
    filename_prefix: str = "agent_ltx_aio",
    ui_workflow_path: str | None = None,
    object_info: dict[str, Any] | None = None,
    face_stability: bool | None = None,
    detailer_strength: float | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply mode switches on real AIO UI WF, expand to API, inject run params."""
    ui = _load_ui(ui_workflow_path)
    ui = apply_aio_mode_to_ui_workflow(ui, mode)
    # Fetch object_info once if not provided (widget field names)
    if object_info is None:
        try:
            import json
            import urllib.request

            object_info = json.loads(
                urllib.request.urlopen(
                    "http://127.0.0.1:8188/object_info", timeout=60
                ).read()
            )
        except Exception:
            object_info = None
    api = expand_ui_workflow_to_api(ui, object_info=object_info)

    # lengths
    if audio_duration_sec is not None and audio_duration_sec > 0:
        trim_dur = float(audio_duration_sec)
    else:
        trim_dur = 3.0
    if clip_length_sec is None or clip_length_sec <= 0:
        # AIO Clip Length is whole seconds. Production default: audio + 1.5s then ceil.
        # S02 bench (2026-07-13): +1.5 (→6s on 3.72s VO) beat tight ceil(audio) for
        # lip + prop stability. Tight mode: AGENT_LTX_CLIP_TIGHT=1 or PAD_SEC=0.
        # AGENT_LTX_CLIP_PAD_SEC = fractional pad before ceil (default 1.5)
        # AGENT_LTX_CLIP_EXTRA_SEC = whole seconds after ceil (default 0)
        import os

        tight = os.environ.get("AGENT_LTX_CLIP_TIGHT", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        default_pad = "0" if tight else "1.5"
        try:
            pad = float(os.environ.get("AGENT_LTX_CLIP_PAD_SEC", default_pad) or default_pad)
        except ValueError:
            pad = 0.0 if tight else 1.5
        try:
            extra = int(float(os.environ.get("AGENT_LTX_CLIP_EXTRA_SEC", "0") or 0))
        except ValueError:
            extra = 0
        if mode.endswith("_audio") or mode == "i2v_audio":
            clip_length_sec = float(
                int(math.ceil(trim_dur + pad - 1e-9)) + max(0, extra)
            )
        else:
            clip_length_sec = trim_dur
    clip_i = max(1, min(20, int(math.ceil(float(clip_length_sec) - 1e-9))))
    edge = int(longer_edge or 1024)
    edge = max(512, min(2048, int(round(edge / 64.0) * 64)))
    if aspect is None:
        aspect = "9:16"
    fps_i = int(fps if fps and fps > 0 else 24)

    # inject standard ports
    if image_name:
        _set(api, "149", "image", image_name)
    if audio_name:
        _set(api, "412", "audio", audio_name)
        if "412" in api:
            api["412"].get("inputs", {}).pop("audioUI", None)
    if last_image_name:
        _set(api, "786", "image", last_image_name)
    if mid_image_name:
        _set(api, "1705", "image", mid_image_name)
    # V2V: VHS_LoadVideo [[P:03 Video to Video]] (node 787 in AIO v44)
    if video_name:
        load_ids = []
        if "787" in api:
            load_ids.append("787")
        for nid, node in api.items():
            if not isinstance(node, dict):
                continue
            if node.get("class_type") == "VHS_LoadVideo" and nid not in load_ids:
                load_ids.append(str(nid))
        skip_frames = 0
        if fps_i > 0 and float(trim_start_sec or 0) > 0:
            skip_frames = max(0, int(round(float(trim_start_sec) * float(fps_i))))
        frame_cap = 0
        if fps_i > 0 and float(trim_dur or 0) > 0:
            frame_cap = max(1, int(round(float(trim_dur) * float(fps_i))))
        for nid in load_ids:
            _set(api, nid, "video", video_name)
            _set(api, nid, "force_rate", float(fps_i))
            if skip_frames:
                _set(api, nid, "skip_first_frames", int(skip_frames))
            if frame_cap:
                _set(api, nid, "frame_load_cap", int(frame_cap))
            # Keep UI preview payload in sync if expand left it as a dict
            try:
                prev = (api.get(nid) or {}).get("inputs", {}).get("videopreview")
                if isinstance(prev, dict):
                    params = dict(prev.get("params") or {})
                    params["filename"] = video_name
                    params["type"] = "input"
                    params["force_rate"] = float(fps_i)
                    if skip_frames:
                        params["skip_first_frames"] = int(skip_frames)
                    if frame_cap:
                        params["frame_load_cap"] = int(frame_cap)
                    prev = dict(prev)
                    prev["params"] = params
                    _set(api, nid, "videopreview", prev)
            except Exception:
                pass

    _set(api, "1792", "start_index", float(trim_start_sec))
    _set(api, "1792", "duration", float(trim_dur))
    _set(api, "196", "Xi", clip_i)
    _set(api, "196", "Xf", float(clip_i))
    _set(api, "196", "isfloatX", 0)
    _set(api, "1688", "Xi", edge)
    _set(api, "1688", "Xf", float(edge))
    _set(api, "1688", "isfloatX", 0)
    _set(api, "1774", "combo", aspect)
    _set(api, "869", "value", fps_i)
    if seed is not None:
        _set(api, "115", "noise_seed", int(seed))

    # Face stability: default ON for still-driven modes (i2v/flf/fml), OFF for pure t2v
    pure_visual = mode in (
        "i2v",
        "flf",
        "fml",
        "v2v",
        "i2v_audio",
        "flf_audio",
        "fml_audio",
        "v2v_audio",
    )
    import os as _os

    env_face = (_os.environ.get("AGENT_LTX_FACE_STABILITY") or "").strip().lower()
    if face_stability is None:
        if env_face in ("0", "false", "off", "no"):
            face_stability = False
        elif env_face in ("1", "true", "on", "yes"):
            face_stability = True
        else:
            face_stability = pure_visual

    prompt_final = prompt or ""
    neg_final = negative or "animation, cartoon, text"
    face_lora_report: dict[str, Any] | None = None
    if face_stability:
        # motion prompt: append stability clause once
        if prompt_final and "identity stable" not in prompt_final.lower() and "face morph" not in prompt_final.lower():
            prompt_final = prompt_final.rstrip(",. ") + ", " + FACE_STABILITY_PROMPT_SUFFIX
        elif not prompt_final:
            prompt_final = FACE_STABILITY_PROMPT_SUFFIX
        # negative: merge face terms
        for token in FACE_STABILITY_NEGATIVE.split(", "):
            if token and token.lower() not in neg_final.lower():
                neg_final = (neg_final.rstrip(", ") + ", " + token) if neg_final else token
        try:
            d_str = float(
                detailer_strength
                if detailer_strength is not None
                else (_os.environ.get("AGENT_LTX_DETAILER_STRENGTH") or "0.55")
            )
        except ValueError:
            d_str = 0.55
        face_lora_report = apply_ltx_face_stability_loras(
            api,
            enable_detailer=True,
            detailer_strength=d_str,
        )

    if prompt_final:
        _set(api, "1797", "text", prompt_final)
    _set(api, "1798", "switch", False)  # use Text Multiline, not LLM rewriter
    if neg_final:
        _set(api, "593", "text", neg_final)
    _set(api, "188", "filename_prefix", filename_prefix)
    _set(api, "188", "save_output", True)

    # Drop NEVER-mode nodes from API (safer than relying on Comfy mode field)
    # BUT keep nodes that are linked from ALWAYS path even if... no, NEVER should be skipped.
    # Removing NEVER nodes can break links; Comfy handles mode=2 by not executing.
    # Keep mode field on nodes.

    meta = {
        "runner": "ltx_aio_workflow_runner",
        "mode": mode,
        "mode_info": describe_mode(mode),
        "ui_workflow": ui_workflow_path or DEFAULT_UI_WF,
        "api_nodes": len(api),
        "trim_start_sec": float(trim_start_sec),
        "trim_duration_sec": float(trim_dur),
        "clip_length_sec": clip_i,
        "longer_edge": edge,
        "aspect": aspect,
        "fps": fps_i,
        "seed": seed,
        "mode_changes": len(ui.get("_agent_aio_mode_changes") or []),
        "active_ports": ui.get("_agent_aio_active_ports"),
        "video_name": video_name,
        "image_name": image_name,
        "face_stability": bool(face_stability),
        "face_lora": face_lora_report,
        "prompt_final_preview": (prompt_final or "")[:200],
        "negative_final_preview": (neg_final or "")[:200],
    }
    return api, meta
