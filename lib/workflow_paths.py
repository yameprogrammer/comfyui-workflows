"""Resolve ComfyUI workflow JSON paths for agent tooling.

Priority:
  1. Explicit path with a directory component (absolute or relative)
  2. workflows/agent/  (SSOT for agent CLIs under scripts/)
  3. Repository root   (optional leftover; not used in normal layout)

Aliases are defined in workflows/agent/catalog.json.
CLI entrypoints live under scripts/ (see scripts/_bootstrap.py).
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

from lib.comfy_client import WORKSPACE_ROOT

AGENT_WORKFLOWS_DIR = os.path.join(WORKSPACE_ROOT, "workflows", "agent")
HUMAN_WORKFLOWS_DIR = os.path.join(WORKSPACE_ROOT, "workflows", "human")
CATALOG_PATH = os.path.join(AGENT_WORKFLOWS_DIR, "catalog.json")

# Built-in fallback if catalog.json is missing (keep in sync with catalog).
_BUILTIN_ALIASES: dict[str, str] = {
    "t2i_moody": "T2I-moody.json",
    "i2i_moody": "I2I-moody.json",
    "i2i_controlnet_moody": "I2I-ControlNet-moody.json",
    "i2v_wan22_a14b": "I2V-wan22-a14b.json",
    "t2i_krea": "T2I-krea.json",
    "t2i_z_image_turbo": "T2I-z-image-turbo.json",
    # filename stems also accepted
    "T2I-moody": "T2I-moody.json",
    "I2I-moody": "I2I-moody.json",
    "I2I-ControlNet-moody": "I2I-ControlNet-moody.json",
    "I2V-wan22-a14b": "I2V-wan22-a14b.json",
    "T2I-krea": "T2I-krea.json",
    "T2I-z-image-turbo": "T2I-z-image-turbo.json",
}


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    if not os.path.isfile(CATALOG_PATH):
        return {"version": 0, "workflows": {}}
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def clear_catalog_cache() -> None:
    load_catalog.cache_clear()


def alias_to_filename(name: str) -> str | None:
    """Map catalog key or bare stem to a filename; None if unknown."""
    key = name.strip()
    if key.lower().endswith(".json"):
        return os.path.basename(key)

    catalog = load_catalog()
    workflows = catalog.get("workflows") or {}
    if key in workflows:
        entry = workflows[key]
        if isinstance(entry, dict):
            return entry.get("file") or entry.get("filename")
        if isinstance(entry, str):
            return entry

    # case-insensitive catalog key
    lower = {k.lower(): k for k in workflows}
    if key.lower() in lower:
        entry = workflows[lower[key.lower()]]
        if isinstance(entry, dict):
            return entry.get("file") or entry.get("filename")
        if isinstance(entry, str):
            return entry

    if key in _BUILTIN_ALIASES:
        return _BUILTIN_ALIASES[key]
    if key.lower() in {k.lower(): k for k in _BUILTIN_ALIASES}:
        # rebuild lower map once
        for k, v in _BUILTIN_ALIASES.items():
            if k.lower() == key.lower():
                return v

    # treat as filename stem
    if not key.endswith(".json"):
        return f"{key}.json"
    return key


def resolve_workflow(name_or_path: str, *, require: bool = True) -> str:
    """
    Resolve a workflow alias, filename, or path to an absolute file path.

    Search order for bare names / aliases:
      workflows/agent/<file> → <repo_root>/<file>

    If ``name_or_path`` is an existing file path, return its absolute path.
    """
    raw = (name_or_path or "").strip()
    if not raw:
        if require:
            raise FileNotFoundError("Empty workflow name/path")
        return ""

    # Explicit path (absolute, or contains a directory component): use as-is if present.
    has_dir = os.path.dirname(raw) not in ("", ".")
    if has_dir or os.path.isabs(raw):
        if os.path.isfile(raw):
            return os.path.abspath(raw)
        cand_ws = os.path.join(WORKSPACE_ROOT, raw)
        if os.path.isfile(cand_ws):
            return os.path.abspath(cand_ws)
        if require:
            raise FileNotFoundError(f"Workflow path not found: {name_or_path!r}")
        return os.path.abspath(raw)

    # Bare alias or filename: prefer agent SSOT, then repo-root legacy.
    filename = alias_to_filename(raw)
    if not filename:
        if require:
            raise FileNotFoundError(f"Unknown workflow: {name_or_path!r}")
        return ""

    candidates = [
        os.path.join(AGENT_WORKFLOWS_DIR, filename),
        os.path.join(WORKSPACE_ROOT, filename),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return os.path.abspath(path)

    if require:
        searched = ", ".join(candidates)
        raise FileNotFoundError(
            f"Workflow not found for {name_or_path!r} (tried: {searched})"
        )
    return candidates[0]


def default_workflow(alias: str) -> str:
    """Resolve a catalog alias; raises if missing."""
    return resolve_workflow(alias, require=True)
