"""Look / Style Core package helpers."""

from __future__ import annotations

import json
import os
import re
import shutil
from typing import Any

from lib.comfy_client import WORKSPACE_ROOT, utc_now_iso

LOOKS_DIR = os.path.join(WORKSPACE_ROOT, "looks")
TEMPLATE_DIR = os.path.join(LOOKS_DIR, "_template")
ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_look_id(look_id: str) -> bool:
    return bool(ID_RE.match(look_id)) and look_id != "_template"


def look_dir(look_id: str) -> str:
    return os.path.join(LOOKS_DIR, look_id)


def list_looks() -> list[str]:
    if not os.path.isdir(LOOKS_DIR):
        return []
    out = []
    for name in sorted(os.listdir(LOOKS_DIR)):
        if name.startswith("_"):
            continue
        if os.path.isfile(os.path.join(LOOKS_DIR, name, "bible.json")):
            out.append(name)
    return out


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


def load_look_cores(look_id: str) -> tuple[str, str]:
    root = look_dir(look_id)
    if not os.path.isdir(root):
        raise FileNotFoundError(f"look not found: {look_id}")
    pos_path = os.path.join(root, "prompts", "positive_core.txt")
    neg_path = os.path.join(root, "prompts", "negative_core.txt")
    with open(pos_path, "r", encoding="utf-8") as f:
        pos = f.read().strip()
    with open(neg_path, "r", encoding="utf-8") as f:
        neg = f.read().strip()
    if not pos:
        raise ValueError(f"look {look_id}: empty positive_core")
    return pos, neg


def look_readiness(look_id: str) -> dict[str, Any]:
    root = look_dir(look_id)
    missing: list[str] = []
    if not os.path.isdir(root):
        return {
            "look_id": look_id,
            "ok": False,
            "missing": ["package_dir"],
            "status": "missing",
        }
    bible_path = os.path.join(root, "bible.json")
    pos = os.path.join(root, "prompts", "positive_core.txt")
    neg = os.path.join(root, "prompts", "negative_core.txt")
    if not os.path.isfile(bible_path):
        missing.append("bible.json")
    if not os.path.isfile(pos):
        missing.append("prompts/positive_core.txt")
    if not os.path.isfile(neg):
        missing.append("prompts/negative_core.txt")
    status = "draft"
    name = look_id
    if os.path.isfile(bible_path):
        try:
            bible = load_json(bible_path)
            status = bible.get("status") or "draft"
            name = bible.get("name") or look_id
        except Exception:
            missing.append("bible_invalid")
    pos_len = 0
    if os.path.isfile(pos):
        with open(pos, "r", encoding="utf-8") as f:
            pos_len = len(f.read().strip())
    if pos_len < 20:
        missing.append("positive_core_too_short")
    ok = not missing and status in ("approved", "draft", "in_review")
    # draft still usable if cores present
    if "positive_core_too_short" in missing or "prompts/positive_core.txt" in missing:
        ok = False
    return {
        "look_id": look_id,
        "name": name,
        "status": status,
        "ok": ok and not any(
            m in missing
            for m in (
                "package_dir",
                "bible.json",
                "prompts/positive_core.txt",
                "positive_core_too_short",
            )
        ),
        "missing": missing,
        "positive_len": pos_len,
        "has_mood_refs": os.path.isdir(os.path.join(root, "refs", "mood"))
        and any(
            n.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
            for n in os.listdir(os.path.join(root, "refs", "mood"))
        )
        if os.path.isdir(os.path.join(root, "refs", "mood"))
        else False,
    }


def create_look(
    look_id: str,
    *,
    name: str,
    positive: str,
    negative: str | None = None,
    description: str = "",
    keywords: list[str] | None = None,
    medium: str = "cinematic_photoreal",
    force: bool = False,
    status: str = "draft",
) -> str:
    if not validate_look_id(look_id):
        raise ValueError(f"invalid look_id {look_id}")
    dest = look_dir(look_id)
    if os.path.exists(dest):
        if not force:
            raise FileExistsError(dest)
        shutil.rmtree(dest)
    if not os.path.isdir(TEMPLATE_DIR):
        raise FileNotFoundError(TEMPLATE_DIR)
    shutil.copytree(TEMPLATE_DIR, dest)
    os.makedirs(os.path.join(dest, "refs", "mood"), exist_ok=True)

    default_neg = (
        negative
        or "cartoon, anime, oversaturated, neon glow, random style shift, "
        "plastic skin, watermark, text, logo, low quality, blurry"
    )
    with open(os.path.join(dest, "prompts", "positive_core.txt"), "w", encoding="utf-8") as f:
        f.write(positive.strip() + "\n")
    with open(os.path.join(dest, "prompts", "negative_core.txt"), "w", encoding="utf-8") as f:
        f.write(default_neg.strip() + "\n")

    bible = {
        "look_id": look_id,
        "name": name,
        "status": status,
        "medium": medium,
        "description": description or name,
        "keywords": keywords or [],
        "default_for_formats": [],
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "process": "look_create_v1",
    }
    save_json(os.path.join(dest, "bible.json"), bible)
    return dest
