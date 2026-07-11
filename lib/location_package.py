"""Location package load/save helpers (mirrors character_package patterns)."""

from __future__ import annotations

import json
import os
import re
import shutil
from typing import Any

from lib.comfy_client import WORKSPACE_ROOT, utc_now_iso

LOCATIONS_DIR = os.path.join(WORKSPACE_ROOT, "locations")
TEMPLATE_DIR = os.path.join(LOCATIONS_DIR, "_template")
DEFAULT_PRESETS_PATH = os.path.join(LOCATIONS_DIR, "location_presets.json")
PROFILES_PATH = os.path.join(LOCATIONS_DIR, "profiles.json")

ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")

APPROVE_ALIASES = {
    "master_wide",
    "angle_eye",
    "angle_reverse",
    "angle_high",
    "angle_low",
    "empty_stage",
    "light_day",
    "light_golden",
    "light_night",
    "landmark_a",
    "landmark_b",
}


def validate_location_id(location_id: str) -> bool:
    return bool(ID_RE.match(location_id))


def package_dir(location_id: str) -> str:
    return os.path.join(LOCATIONS_DIR, location_id)


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: dict) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_presets(path: str | None = None) -> dict:
    return load_json(path or DEFAULT_PRESETS_PATH)


def load_profiles(path: str | None = None) -> dict:
    return load_json(path or PROFILES_PATH)


def get_location_profile(profile_id: str | None = None) -> dict[str, Any]:
    doc = load_profiles()
    pid = profile_id or doc.get("default_profile") or "video_ref"
    profiles = doc.get("profiles") or {}
    if pid not in profiles:
        raise KeyError(f"Unknown location profile {pid!r}")
    entry = dict(profiles[pid])
    entry["id"] = pid
    return entry


def mvp_aliases_for(profile_id: str | None = None) -> list[str]:
    presets = load_presets()
    profile = get_location_profile(profile_id)
    key = profile.get("mvp_aliases_key") or "mvp_aliases_video_ref"
    return list(presets.get(key) or presets.get("mvp_aliases_video_ref") or [])


def copy_template(location_id: str, force: bool = False) -> str:
    dest = package_dir(location_id)
    if os.path.exists(dest):
        if not force:
            raise FileExistsError(dest)
        shutil.rmtree(dest)
    if not os.path.isdir(TEMPLATE_DIR):
        raise FileNotFoundError(TEMPLATE_DIR)
    shutil.copytree(TEMPLATE_DIR, dest)
    return dest


def asset_filename(
    location_id: str,
    sheet: str,
    view: str,
    variant: str,
    seed: int,
    candidate: int,
) -> str:
    return (
        f"{location_id}__{sheet}__{view}__{variant}"
        f"__s{seed}__c{candidate:02d}.png"
    )


def fill_bible_from_create(
    bible: dict,
    *,
    location_id: str,
    name: str,
    architecture: str,
    positive_core: str,
    negative_core: str,
    profile_id: str,
    location_type: str = "",
    atmosphere: list[str] | None = None,
) -> dict:
    now = utc_now_iso()
    bible["location_id"] = location_id
    bible["name"] = name
    bible["status"] = "draft"
    bible["level"] = "L1"
    bible["created_at"] = now
    bible["updated_at"] = now
    bible["active_profile"] = profile_id
    bible["type"] = location_type or bible.get("type") or ""
    bible["atmosphere"] = atmosphere or bible.get("atmosphere") or []
    bible["architecture_lock"] = architecture.strip()
    bible.setdefault("prompts", {})
    bible["prompts"]["positive_core"] = positive_core.strip()
    bible["prompts"]["negative_core"] = negative_core.strip()
    return bible


def fill_manifest_from_create(
    manifest: dict,
    *,
    location_id: str,
    profile_id: str,
    model: str = "pro",
) -> dict:
    now = utc_now_iso()
    manifest["location_id"] = location_id
    manifest["status"] = "draft"
    manifest["created_at"] = now
    manifest["updated_at"] = now
    manifest["base_model"] = f"moody_{model}"
    manifest["level"] = "L1"
    manifest["assets"] = []
    manifest["approved"] = {}
    manifest["mvp_profile"] = profile_id
    manifest["missing_mvp"] = mvp_aliases_for(profile_id)
    return manifest


class LocationPackage:
    def __init__(self, location_id: str):
        self.location_id = location_id
        self.root = package_dir(location_id)
        if not os.path.isdir(self.root):
            raise FileNotFoundError(self.root)
        self.bible_path = os.path.join(self.root, "bible.json")
        self.manifest_path = os.path.join(self.root, "manifest.json")
        self.bible = load_json(self.bible_path)
        self.manifest = load_json(self.manifest_path)

    @classmethod
    def load(cls, location_id: str) -> "LocationPackage":
        return cls(location_id)

    def save_bible(self) -> None:
        self.bible["updated_at"] = utc_now_iso()
        save_json(self.bible_path, self.bible)

    def save_manifest(self) -> None:
        self.manifest["updated_at"] = utc_now_iso()
        save_json(self.manifest_path, self.manifest)

    def path(self, *parts: str) -> str:
        return os.path.join(self.root, *parts)

    def resolve(self, rel_or_abs: str) -> str:
        if os.path.isabs(rel_or_abs):
            return rel_or_abs
        return os.path.join(self.root, rel_or_abs)

    def read_positive_core(self) -> str:
        p = self.path("prompts", "positive_core.txt")
        with open(p, "r", encoding="utf-8") as f:
            return f.read().strip()

    def read_negative_core(self) -> str:
        p = self.path("prompts", "negative_core.txt")
        with open(p, "r", encoding="utf-8") as f:
            return f.read().strip()

    def write_core_prompts(self, positive: str, negative: str) -> None:
        with open(self.path("prompts", "positive_core.txt"), "w", encoding="utf-8") as f:
            f.write(positive.strip() + "\n")
        with open(self.path("prompts", "negative_core.txt"), "w", encoding="utf-8") as f:
            f.write(negative.strip() + "\n")
        self.bible.setdefault("prompts", {})
        self.bible["prompts"]["positive_core"] = positive.strip()
        self.bible["prompts"]["negative_core"] = negative.strip()

    def append_asset(self, asset: dict[str, Any]) -> None:
        self.manifest.setdefault("assets", []).append(asset)
        self.save_manifest()

    def append_changelog(self, line: str) -> None:
        path = self.path("versions", "CHANGELOG.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"- {utc_now_iso()}: {line}\n")

    def active_profile_id(self) -> str:
        return self.bible.get("active_profile") or "video_ref"

    def recompute_missing_mvp(self, profile_id: str | None = None) -> list[str]:
        pid = profile_id or self.active_profile_id()
        required = mvp_aliases_for(pid)
        approved_keys = set(self.manifest.get("approved", {}).keys())
        missing = [k for k in required if k not in approved_keys]
        self.manifest["missing_mvp"] = missing
        self.manifest["mvp_profile"] = pid
        if not missing and self.manifest.get("level") in (None, "L1"):
            self.manifest["level"] = "L2"
        return missing

    def approve(self, source_path: str, alias: str, set_primary: bool = False) -> str:
        if alias not in APPROVE_ALIASES:
            raise ValueError(f"Invalid approve alias: {alias}")
        if not os.path.exists(source_path):
            raise FileNotFoundError(source_path)

        dest_name = f"{alias}.png"
        dest_path = self.path("approved", dest_name)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        src_abs = os.path.abspath(source_path)
        dst_abs = os.path.abspath(dest_path)
        if src_abs != dst_abs:
            shutil.copy2(source_path, dest_path)

        rel_dest = f"approved/{dest_name}"
        try:
            rel_source = os.path.relpath(source_path, self.root).replace("\\", "/")
        except ValueError:
            rel_source = source_path

        self.manifest.setdefault("approved", {})[alias] = {
            "path": rel_dest,
            "source": rel_source,
            "approved_at": utc_now_iso(),
        }

        sheet_index = self.bible.setdefault("sheet_index", {})
        group = "master"
        if alias.startswith("angle_") or alias == "empty_stage":
            group = "angles" if alias != "empty_stage" else "empty_stage"
        elif alias.startswith("light_"):
            group = "lighting"
        elif alias.startswith("landmark_"):
            group = "landmarks"
        sheet_index.setdefault(group, [])
        if rel_dest not in sheet_index[group]:
            sheet_index[group].append(rel_dest)

        identity = self.bible.setdefault("identity", {})
        if set_primary or alias == "master_wide" or identity.get("primary_ref") is None:
            if alias == "master_wide" or set_primary:
                identity["primary_ref"] = rel_dest

        self.recompute_missing_mvp()
        if not self.manifest.get("missing_mvp"):
            self.bible["status"] = "approved"
            self.manifest["status"] = "approved"
            self.manifest["level"] = "L2"
            self.bible["level"] = "L2"

        self.save_bible()
        self.save_manifest()
        self.append_changelog(f"approved {alias} from {rel_source}")
        return dest_path

    def default_source_ref(self) -> str | None:
        identity = self.bible.get("identity") or {}
        primary = identity.get("primary_ref")
        if primary:
            path = self.resolve(primary)
            if os.path.isfile(path):
                return path
        approved = self.manifest.get("approved") or {}
        if "master_wide" in approved:
            path = self.resolve(approved["master_wide"]["path"])
            if os.path.isfile(path):
                return path
        return None
