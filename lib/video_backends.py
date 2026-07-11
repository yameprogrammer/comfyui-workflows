"""I2V backend + aspect-format + resolution preset SSOT (video_backends.json).

Aspect ratio is **not** fixed to 16:9. Choose a format profile
(cinematic_16x9, shorts_9x16, classic_4x3, portrait_3x4, square_1x1, …)
or a work/deliver preset that already carries an aspect.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

from lib.comfy_client import WORKSPACE_ROOT
from lib.workflow_paths import resolve_workflow

DEFAULT_CONFIG_PATH = os.path.join(WORKSPACE_ROOT, "video_backends.json")


@lru_cache(maxsize=4)
def load_video_backends(path: str | None = None) -> dict[str, Any]:
    cfg_path = path or DEFAULT_CONFIG_PATH
    if not os.path.isfile(cfg_path):
        raise FileNotFoundError(f"video_backends.json not found: {cfg_path}")
    with open(cfg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("video_backends.json must be an object")
    return data


def clear_video_backends_cache() -> None:
    load_video_backends.cache_clear()


def list_backend_ids(cfg: dict[str, Any] | None = None) -> list[str]:
    doc = cfg or load_video_backends()
    return sorted((doc.get("backends") or {}).keys())


def list_preset_ids(cfg: dict[str, Any] | None = None, *, stage: str | None = None) -> list[str]:
    doc = cfg or load_video_backends()
    presets = doc.get("presets") or {}
    out = []
    for pid, entry in presets.items():
        if stage is None or (entry or {}).get("stage") == stage:
            out.append(pid)
    return sorted(out)


def list_format_ids(cfg: dict[str, Any] | None = None) -> list[str]:
    doc = cfg or load_video_backends()
    return sorted((doc.get("formats") or {}).keys())


def get_backend(backend_id: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = cfg or load_video_backends()
    backends = doc.get("backends") or {}
    if backend_id not in backends:
        known = ", ".join(sorted(backends.keys())) or "(none)"
        raise KeyError(f"Unknown backend {backend_id!r}. Known: {known}")
    entry = dict(backends[backend_id])
    entry["id"] = backend_id
    return entry


def get_preset(preset_id: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = cfg or load_video_backends()
    presets = doc.get("presets") or {}
    if preset_id not in presets:
        known = ", ".join(sorted(presets.keys())) or "(none)"
        raise KeyError(f"Unknown preset {preset_id!r}. Known: {known}")
    entry = dict(presets[preset_id])
    entry["id"] = preset_id
    if "width" not in entry or "height" not in entry:
        raise ValueError(f"Preset {preset_id!r} missing width/height")
    return entry


def get_format(format_id: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = cfg or load_video_backends()
    formats = doc.get("formats") or {}
    if format_id not in formats:
        known = ", ".join(sorted(formats.keys())) or "(none)"
        raise KeyError(f"Unknown format {format_id!r}. Known: {known}")
    entry = dict(formats[format_id])
    entry["id"] = format_id
    return entry


def resolve_i2v_job(
    *,
    backend: str | None = None,
    format_id: str | None = None,
    preset: str | None = None,
    width: int | None = None,
    height: int | None = None,
    workflow: str | None = None,
    config_path: str | None = None,
) -> dict[str, Any]:
    """
    Resolve backend, format, work preset, size, and workflow path for an I2V run.

    Priority for work size:
      1. explicit width+height
      2. explicit --preset
      3. format's default_work_preset
      4. config default_work_preset / default_format

    Returns keys including:
      backend_id, format_id, aspect, preset_id, preset, width, height,
      deliver_preset_id, workflow_path, status
    """
    cfg = load_video_backends(config_path)
    backend_id = (backend or cfg.get("default_backend") or "wan22").strip()

    explicit_format = bool(format_id and str(format_id).strip())
    explicit_preset = bool(preset and str(preset).strip())

    fmt: dict[str, Any] | None = None
    resolved_format_id: str | None = None

    if explicit_format:
        resolved_format_id = str(format_id).strip()
        fmt = get_format(resolved_format_id, cfg)
    elif not explicit_preset and cfg.get("default_format"):
        # No format/preset from caller → use default format profile
        resolved_format_id = str(cfg["default_format"])
        try:
            fmt = get_format(resolved_format_id, cfg)
        except KeyError:
            fmt = None
            resolved_format_id = None

    if explicit_preset:
        preset_id = str(preset).strip()
    elif fmt and fmt.get("default_work_preset"):
        preset_id = str(fmt["default_work_preset"])
    else:
        preset_id = str(cfg.get("default_work_preset") or "work_16x9_540")

    be = get_backend(backend_id, cfg)
    pr = get_preset(preset_id, cfg)

    # Explicit format + explicit preset must agree on aspect
    if explicit_format and explicit_preset and fmt and pr.get("aspect") and fmt.get("aspect"):
        if pr["aspect"] != fmt["aspect"]:
            raise ValueError(
                f"Preset {preset_id!r} aspect={pr['aspect']!r} does not match "
                f"format {resolved_format_id!r} aspect={fmt['aspect']!r}"
            )

    # If only preset was chosen, attach a matching format (if any) for deliver hints
    if explicit_preset and not explicit_format:
        aspect_hint = pr.get("aspect")
        for fid in list_format_ids(cfg):
            candidate = get_format(fid, cfg)
            if candidate.get("aspect") == aspect_hint:
                resolved_format_id = fid
                fmt = candidate
                break

    # Deliver pixel tier (short-edge) — not aspect-specific. Prefer default_deliver_tier.
    # Legacy names (deliver_16x9_1080, …) map via deliver_aliases → deliver_1080 etc.
    aliases = cfg.get("deliver_aliases") or {}
    raw_deliver = None
    if fmt and (fmt.get("default_deliver_tier") or fmt.get("default_deliver_preset")):
        raw_deliver = fmt.get("default_deliver_tier") or fmt.get("default_deliver_preset")
    else:
        raw_deliver = cfg.get("default_deliver_tier") or cfg.get("default_deliver_preset") or "deliver_1080"
    deliver_preset_id = str(aliases.get(str(raw_deliver), raw_deliver))

    w = int(width) if width is not None else int(pr["width"])
    h = int(height) if height is not None else int(pr["height"])

    aspect = pr.get("aspect") or (fmt or {}).get("aspect")

    status = (be.get("status") or "ready").lower()
    workflow_ref = workflow or be.get("workflow") or ""

    if status in ("planned", "disabled") and not workflow:
        raise BackendNotReady(
            backend_id,
            f"Backend {backend_id!r} status={status!r}. "
            f"{be.get('notes') or 'Not implemented yet.'}",
        )

    if not workflow_ref:
        raise ValueError(f"Backend {backend_id!r} has no workflow mapping")

    try:
        workflow_path = resolve_workflow(str(workflow_ref))
    except FileNotFoundError as e:
        if status in ("planned", "disabled"):
            raise BackendNotReady(backend_id, str(e)) from e
        raise

    return {
        "backend_id": backend_id,
        "backend": be,
        "format_id": resolved_format_id,
        "format": fmt,
        "aspect": aspect,
        "preset_id": preset_id,
        "preset": pr,
        "width": w,
        "height": h,
        "deliver_preset_id": deliver_preset_id,
        "workflow_path": workflow_path,
        "workflow_ref": str(workflow_ref),
        "status": status,
        # backward-compatible alias
        "default_deliver_preset": deliver_preset_id,
    }


class BackendNotReady(RuntimeError):
    def __init__(self, backend_id: str, message: str):
        self.backend_id = backend_id
        super().__init__(message)
