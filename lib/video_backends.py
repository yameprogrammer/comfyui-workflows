"""I2V backend + resolution preset SSOT (video_backends.json)."""

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


def resolve_i2v_job(
    *,
    backend: str | None = None,
    preset: str | None = None,
    width: int | None = None,
    height: int | None = None,
    workflow: str | None = None,
    config_path: str | None = None,
) -> dict[str, Any]:
    """
    Resolve backend, preset, size, and workflow path for an I2V run.

    Returns dict with keys:
      backend_id, backend, preset_id, preset, width, height,
      workflow_path, workflow_ref, status
    Raises KeyError/ValueError/FileNotFoundError on bad config.
    Raises BackendNotReady for planned backends without an explicit workflow file.
    """
    cfg = load_video_backends(config_path)
    backend_id = (backend or cfg.get("default_backend") or "wan22").strip()
    preset_id = (preset or cfg.get("default_work_preset") or "work_16x9_540").strip()

    be = get_backend(backend_id, cfg)
    pr = get_preset(preset_id, cfg)

    w = int(width) if width is not None else int(pr["width"])
    h = int(height) if height is not None else int(pr["height"])

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
        "preset_id": preset_id,
        "preset": pr,
        "width": w,
        "height": h,
        "workflow_path": workflow_path,
        "workflow_ref": str(workflow_ref),
        "status": status,
        "default_deliver_preset": cfg.get("default_deliver_preset"),
    }


class BackendNotReady(RuntimeError):
    def __init__(self, backend_id: str, message: str):
        self.backend_id = backend_id
        super().__init__(message)
