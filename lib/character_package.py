"""Character package load/save helpers."""

from __future__ import annotations

import json
import os
import re
import shutil
from typing import Any

from lib.comfy_client import WORKSPACE_ROOT, utc_now_iso

CHARACTERS_DIR = os.path.join(WORKSPACE_ROOT, "characters")
TEMPLATE_DIR = os.path.join(CHARACTERS_DIR, "_template")
DEFAULT_PRESETS_PATH = os.path.join(CHARACTERS_DIR, "sheet_presets.json")

ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")

APPROVE_ALIASES = {
    "master_front",
    "master_full",
    "turn_front",
    "turn_qf",
    "turn_side",
    "turn_back",
    "expr_neutral",
    "expr_joy",
    "expr_sad",
    "expr_angry",
    "expr_surprise",
    "expr_think",
    "costume_default",
    "costume_alt1",
}


def validate_character_id(character_id: str) -> bool:
    return bool(ID_RE.match(character_id))


def package_dir(character_id: str) -> str:
    return os.path.join(CHARACTERS_DIR, character_id)


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


def copy_template(character_id: str, force: bool = False) -> str:
    dest = package_dir(character_id)
    if os.path.exists(dest):
        if not force:
            raise FileExistsError(dest)
        shutil.rmtree(dest)
    if not os.path.isdir(TEMPLATE_DIR):
        raise FileNotFoundError(TEMPLATE_DIR)
    shutil.copytree(TEMPLATE_DIR, dest)
    return dest


def asset_filename(
    character_id: str,
    sheet: str,
    view: str,
    variant: str,
    seed: int,
    candidate: int,
) -> str:
    return (
        f"{character_id}__{sheet}__{view}__{variant}"
        f"__s{seed}__c{candidate:02d}.png"
    )


class CharacterPackage:
    def __init__(self, character_id: str):
        self.character_id = character_id
        self.root = package_dir(character_id)
        if not os.path.isdir(self.root):
            raise FileNotFoundError(self.root)
        self.bible_path = os.path.join(self.root, "bible.json")
        self.manifest_path = os.path.join(self.root, "manifest.json")
        self.bible = load_json(self.bible_path)
        self.manifest = load_json(self.manifest_path)

    @classmethod
    def load(cls, character_id: str) -> "CharacterPackage":
        return cls(character_id)

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
        # allow "approved/master_front.png" or "refs/..."
        candidate = os.path.join(self.root, rel_or_abs)
        return candidate

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

    def recompute_missing_mvp(self) -> list[str]:
        approved_keys = set(self.manifest.get("approved", {}).keys())
        # master_full optional for soft MVP gate; still tracked
        required = [
            "master_front",
            "turn_front",
            "turn_qf",
            "turn_side",
            "turn_back",
            "expr_neutral",
            "expr_joy",
            "expr_sad",
            "expr_angry",
            "expr_surprise",
            "expr_think",
            "costume_default",
            "costume_alt1",
        ]
        missing = [k for k in required if k not in approved_keys]
        self.manifest["missing_mvp"] = missing
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
        shutil.copy2(source_path, dest_path)

        rel_dest = f"approved/{dest_name}"
        # store source relative if under package
        try:
            rel_source = os.path.relpath(source_path, self.root).replace("\\", "/")
        except ValueError:
            rel_source = source_path

        self.manifest.setdefault("approved", {})[alias] = {
            "path": rel_dest,
            "source": rel_source,
            "approved_at": utc_now_iso(),
        }

        # sheet_index convenience
        sheet_index = self.bible.setdefault("sheet_index", {})
        group = "master"
        if alias.startswith("turn_"):
            group = "turnaround"
        elif alias.startswith("expr_"):
            group = "expression"
        elif alias.startswith("costume_"):
            group = "costume"
        sheet_index.setdefault(group, [])
        if rel_dest not in sheet_index[group]:
            sheet_index[group].append(rel_dest)

        identity = self.bible.setdefault("identity", {})
        if set_primary or alias == "master_front" or identity.get("primary_ref") is None:
            if alias == "master_front" or set_primary:
                identity["primary_ref"] = rel_dest

        self.recompute_missing_mvp()
        if not self.manifest.get("missing_mvp"):
            self.bible["status"] = "approved"
            self.manifest["status"] = "approved"
            self.manifest["level"] = "L2"

        self.save_bible()
        self.save_manifest()
        self.append_changelog(f"approved {alias} from {rel_source}")
        return dest_path

    def default_source_ref(self) -> str | None:
        identity = self.bible.get("identity") or {}
        primary = identity.get("primary_ref")
        if primary:
            path = self.resolve(primary)
            if os.path.exists(path):
                return path
        fallback = self.path("approved", "master_front.png")
        if os.path.exists(fallback):
            return fallback
        return None


def model_key_from_bible(base_model: str | None) -> str:
    mapping = {
        "moody_real": "real",
        "moody_pro": "pro",
        "moody_wild": "wild",
        "real": "real",
        "pro": "pro",
        "wild": "wild",
    }
    if not base_model:
        return "pro"
    return mapping.get(base_model, "pro")


def fill_bible_from_create(
    bible: dict,
    character_id: str,
    display_name: str,
    model: str,
    positive_core: str,
    negative_core: str,
    appearance_prompt: str,
) -> dict:
    now = utc_now_iso()
    base_model = {"real": "moody_real", "pro": "moody_pro", "wild": "moody_wild"}.get(model, "moody_pro")
    bible["id"] = character_id
    bible["display_name"] = display_name
    bible["version"] = "0.1.0"
    bible["status"] = "draft"
    bible["created_at"] = now
    bible["updated_at"] = now
    bible.setdefault("style", {})
    bible["style"]["medium"] = "cinematic_photoreal"
    bible["style"]["base_model"] = base_model
    bible["style"]["look"] = appearance_prompt[:200]
    bible.setdefault("prompts", {})
    bible["prompts"]["positive_core"] = positive_core
    bible["prompts"]["negative_core"] = negative_core
    bible["prompts"]["trigger"] = character_id
    bible["prompts"]["positive_core_file"] = "prompts/positive_core.txt"
    bible["prompts"]["negative_core_file"] = "prompts/negative_core.txt"
    bible.setdefault("identity", {})
    bible["identity"]["mode"] = "refs_only"
    bible["identity"]["primary_ref"] = None
    return bible


def fill_manifest_from_create(manifest: dict, character_id: str, model: str) -> dict:
    now = utc_now_iso()
    base_model = {"real": "moody_real", "pro": "moody_pro", "wild": "moody_wild"}.get(model, "moody_pro")
    manifest["character_id"] = character_id
    manifest["package_version"] = "0.1.0"
    manifest["status"] = "draft"
    manifest["created_at"] = now
    manifest["updated_at"] = now
    manifest["base_model"] = base_model
    manifest["level"] = "L1"
    manifest["assets"] = []
    manifest["approved"] = {}
    return manifest
