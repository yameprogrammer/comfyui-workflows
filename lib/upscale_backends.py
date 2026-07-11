"""Upscale backend + deliver-size presets (upscale_backends.json)."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

from lib.comfy_client import WORKSPACE_ROOT
from lib.video_backends import get_format, load_video_backends

DEFAULT_CONFIG_PATH = os.path.join(WORKSPACE_ROOT, "upscale_backends.json")


@lru_cache(maxsize=4)
def load_upscale_backends(path: str | None = None) -> dict[str, Any]:
    cfg_path = path or DEFAULT_CONFIG_PATH
    if not os.path.isfile(cfg_path):
        raise FileNotFoundError(f"upscale_backends.json not found: {cfg_path}")
    with open(cfg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("upscale_backends.json must be an object")
    return data


def clear_upscale_backends_cache() -> None:
    load_upscale_backends.cache_clear()


def list_upscale_backend_ids(cfg: dict[str, Any] | None = None) -> list[str]:
    doc = cfg or load_upscale_backends()
    return sorted((doc.get("backends") or {}).keys())


def list_upscale_preset_ids(cfg: dict[str, Any] | None = None) -> list[str]:
    doc = cfg or load_upscale_backends()
    return sorted((doc.get("presets") or {}).keys())


def get_upscale_backend(backend_id: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = cfg or load_upscale_backends()
    backends = doc.get("backends") or {}
    if backend_id not in backends:
        known = ", ".join(sorted(backends.keys())) or "(none)"
        raise KeyError(f"Unknown upscale backend {backend_id!r}. Known: {known}")
    entry = dict(backends[backend_id])
    entry["id"] = backend_id
    return entry


def get_upscale_preset(preset_id: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = cfg or load_upscale_backends()
    presets = doc.get("presets") or {}
    if preset_id not in presets:
        known = ", ".join(sorted(presets.keys())) or "(none)"
        raise KeyError(f"Unknown upscale preset {preset_id!r}. Known: {known}")
    entry = dict(presets[preset_id])
    entry["id"] = preset_id
    if "short_edge" not in entry:
        raise ValueError(f"Preset {preset_id!r} missing short_edge")
    return entry


def parse_aspect(aspect: str) -> tuple[int, int]:
    """Return (w_ratio, h_ratio) for strings like '16:9'."""
    parts = aspect.replace("x", ":").split(":")
    if len(parts) != 2:
        raise ValueError(f"Bad aspect {aspect!r}")
    return int(parts[0]), int(parts[1])


def size_from_short_edge(aspect: str, short_edge: int) -> tuple[int, int]:
    """
    Compute even (width, height) so the shorter side == short_edge.
    Landscape: height=short_edge; portrait: width=short_edge; square: both.
    """
    wr, hr = parse_aspect(aspect)
    short_edge = int(short_edge)
    if wr == hr:
        s = short_edge - (short_edge % 2)
        return s, s
    if wr > hr:
        # landscape: short = height
        h = short_edge - (short_edge % 2)
        w = int(round(h * wr / hr))
        w = w - (w % 2)
        return max(w, 2), max(h, 2)
    # portrait: short = width
    w = short_edge - (short_edge % 2)
    h = int(round(w * hr / wr))
    h = h - (h % 2)
    return max(w, 2), max(h, 2)


def resolve_target_size(
    *,
    preset: str | None = None,
    format_id: str | None = None,
    aspect: str | None = None,
    width: int | None = None,
    height: int | None = None,
    short_edge: int | None = None,
    config_path: str | None = None,
) -> dict[str, Any]:
    """
    Resolve final pixel size for upscale.

    Priority:
      1. explicit width+height
      2. short_edge + aspect/format
      3. preset short_edge + aspect/format
    """
    cfg = load_upscale_backends(config_path)
    preset_id = (preset or cfg.get("default_preset") or "deliver_1080").strip()
    pr = get_upscale_preset(preset_id, cfg)

    resolved_aspect = aspect
    resolved_format = format_id
    if not resolved_aspect:
        if format_id:
            try:
                fmt = get_format(format_id)
                resolved_aspect = str(fmt.get("aspect") or "16:9")
                resolved_format = format_id
            except Exception:
                resolved_aspect = "16:9"
        else:
            # fall back to video_backends default format
            try:
                vcfg = load_video_backends()
                fid = str(vcfg.get("default_format") or "cinematic_16x9")
                fmt = get_format(fid)
                resolved_aspect = str(fmt.get("aspect") or "16:9")
                resolved_format = fid
            except Exception:
                resolved_aspect = "16:9"

    if width is not None and height is not None:
        w, h = int(width), int(height)
        se = min(w, h)
    else:
        se = int(short_edge) if short_edge is not None else int(pr["short_edge"])
        w, h = size_from_short_edge(resolved_aspect, se)

    return {
        "preset_id": preset_id,
        "preset": pr,
        "format_id": resolved_format,
        "aspect": resolved_aspect,
        "width": w,
        "height": h,
        "short_edge": min(w, h),
        "long_edge": max(w, h),
    }


def resolve_upscale_job(
    *,
    backend: str | None = None,
    preset: str | None = None,
    format_id: str | None = None,
    aspect: str | None = None,
    width: int | None = None,
    height: int | None = None,
    short_edge: int | None = None,
    config_path: str | None = None,
) -> dict[str, Any]:
    cfg = load_upscale_backends(config_path)
    backend_id = (backend or cfg.get("default_backend") or "seedvr2").strip()
    be = get_upscale_backend(backend_id, cfg)
    if (be.get("status") or "ready").lower() != "ready":
        raise RuntimeError(f"Upscale backend {backend_id!r} status={be.get('status')}")

    target = resolve_target_size(
        preset=preset,
        format_id=format_id,
        aspect=aspect,
        width=width,
        height=height,
        short_edge=short_edge,
        config_path=config_path,
    )
    return {
        "backend_id": backend_id,
        "backend": be,
        "config": cfg,
        **target,
    }
