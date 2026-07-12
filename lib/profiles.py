"""Purpose profile loader (video_ref | full_sheet | artbook). SSOT: characters/profiles.json"""

from __future__ import annotations

import os
from typing import Any

from lib.character_package import CHARACTERS_DIR, load_json, load_presets

DEFAULT_PROFILES_PATH = os.path.join(CHARACTERS_DIR, "profiles.json")
PROFILE_IDS = ("video_ref", "full_sheet", "artbook")


def character_sheet_process_profile(doc: dict | None = None) -> str:
    """Production character sheet process profile (industry full pack)."""
    doc = doc or load_profiles_doc()
    return doc.get("character_sheet_process_profile") or "full_sheet"


def load_profiles_doc(path: str | None = None) -> dict:
    return load_json(path or DEFAULT_PROFILES_PATH)


def default_profile_id(doc: dict | None = None) -> str:
    doc = doc or load_profiles_doc()
    return doc.get("default_profile") or "video_ref"


def get_profile(profile_id: str | None = None, path: str | None = None) -> dict[str, Any]:
    doc = load_profiles_doc(path)
    pid = profile_id or default_profile_id(doc)
    profiles = doc.get("profiles") or {}
    if pid not in profiles:
        known = ", ".join(sorted(profiles.keys()))
        raise KeyError(f"unknown profile '{pid}' (known: {known})")
    profile = dict(profiles[pid])
    profile["id"] = pid
    profile["_mvp_aliases"] = list((doc.get("mvp_aliases") or {}).get(pid) or [])
    profile["_doc"] = doc
    return profile


def mvp_aliases_for(profile_id: str | None = None, path: str | None = None) -> list[str]:
    profile = get_profile(profile_id, path)
    return list(profile.get("_mvp_aliases") or [])


def size_for_sheet(profile: dict, sheet: str, view: str | None = None) -> tuple[int, int]:
    """Map sheet/view to profile sizes entry."""
    sizes = profile.get("sizes") or {}
    key = "master_face"
    if sheet == "master":
        key = "master_full_body" if view in ("full",) else "master_face"
    elif sheet == "expression":
        key = "expression"
    elif sheet == "turnaround":
        key = "turnaround"
    elif sheet == "costume":
        key = "costume"
        if view and str(view).startswith("detail"):
            key = "expression"
    elif sheet == "pose":
        key = "pose"
    elif sheet == "head":
        key = "head" if "head" in sizes else "expression"
    elif sheet == "props":
        key = "props" if "props" in sizes else "expression"
    pair = sizes.get(key) or sizes.get("master_face") or [1024, 1024]
    return int(pair[0]), int(pair[1])


def expand_sheet_groups_to_preset_ids(
    group_names: list[str],
    presets: dict | None = None,
) -> list[str]:
    """Expand profile mvp_sheet_groups names using sheet_presets.mvp_sheet_groups."""
    presets = presets or load_presets()
    groups = presets.get("mvp_sheet_groups") or {}
    result: list[str] = []
    seen: set[str] = set()
    for name in group_names:
        if name in groups:
            for pid in groups[name]:
                if pid not in seen:
                    seen.add(pid)
                    result.append(pid)
        elif name not in seen:
            # allow raw preset id
            seen.add(name)
            result.append(name)
    return result


def profile_all_mvp_preset_ids(profile: dict, presets: dict | None = None) -> list[str]:
    """Preset ids for expand when --sheets all_mvp under this profile (I2I only groups)."""
    presets = presets or load_presets()
    # Prefer explicit full_pack key for full_sheet / artbook
    key = profile.get("all_mvp_key")
    group_map = presets.get("mvp_sheet_groups") or {}
    if key and key in group_map:
        return list(group_map[key])
    groups = list(profile.get("mvp_sheet_groups") or [])
    # master is T2I — expand skips it; use expression/turnaround/costume/pose from MVP
    expand_groups = [g for g in groups if g != "master"]
    if not expand_groups:
        expand_groups = ["expression"]
    return expand_sheet_groups_to_preset_ids(expand_groups, presets)


def ensure_export_dirs(package_root: str, profile: dict) -> str:
    sub = profile.get("export_subdir") or f"exports/{profile.get('id', 'video_ref')}"
    # export_subdir is relative to package, e.g. exports/video_ref
    path = os.path.join(package_root, sub.replace("/", os.sep))
    os.makedirs(path, exist_ok=True)
    os.makedirs(os.path.join(path, "approved"), exist_ok=True)
    return path


def apply_profile_to_bible(bible: dict, profile: dict) -> dict:
    pid = profile.get("id") or "video_ref"
    bible["active_profile"] = pid
    exports = bible.setdefault("exports", {})
    for key in ("video_ref", "full_sheet", "artbook"):
        exports.setdefault(
            key,
            {
                "status": "draft",
                "updated_at": None,
                "path": f"exports/{key}",
            },
        )
    if pid in exports:
        exports[pid]["path"] = profile.get("export_subdir") or f"exports/{pid}"
    return bible


def sync_export_status(bible: dict, profile_id: str, status: str, updated_at: str) -> None:
    exports = bible.setdefault("exports", {})
    entry = exports.setdefault(
        profile_id,
        {"status": "draft", "updated_at": None, "path": f"exports/{profile_id}"},
    )
    entry["status"] = status
    entry["updated_at"] = updated_at
