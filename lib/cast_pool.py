"""Character casting pool — multi-engine candidate exploration before package lock."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from lib.comfy_client import WORKSPACE_ROOT, utc_now_iso

CASTS_DIR = os.path.join(WORKSPACE_ROOT, "characters", "casts")
ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")

# engine_id → runner kind
ENGINE_SPECS: dict[str, dict[str, Any]] = {
    "moody_real": {
        "kind": "moody",
        "model": "real",
        "label": "Moody Real",
        "strengths": ["photoreal", "fast_cast"],
    },
    "moody_pro": {
        "kind": "moody",
        "model": "pro",
        "label": "Moody Pro",
        "strengths": ["cinematic", "default_cast"],
    },
    "moody_wild": {
        "kind": "moody",
        "model": "wild",
        "label": "Moody Wild",
        "strengths": ["stylized", "exploration"],
    },
    "krea": {
        "kind": "krea",
        "model": None,
        "label": "Krea 2 Turbo",
        "strengths": ["detail", "alternate_quality"],
    },
}


def validate_cast_id(cast_id: str) -> bool:
    return bool(ID_RE.match(cast_id))


def cast_dir(cast_id: str) -> str:
    return os.path.join(CASTS_DIR, cast_id)


def parse_engines(spec: str | list[str] | None) -> list[str]:
    if spec is None:
        return ["moody_pro", "krea"]
    if isinstance(spec, list):
        raw = spec
    else:
        raw = [x.strip() for x in str(spec).split(",") if x.strip()]
    out = []
    for e in raw:
        key = e.lower().replace("-", "_")
        # aliases
        if key in ("real", "moody"):
            key = "moody_real" if key == "real" else "moody_pro"
        if key in ("pro",):
            key = "moody_pro"
        if key in ("wild",):
            key = "moody_wild"
        if key not in ENGINE_SPECS:
            raise KeyError(f"unknown cast engine {e!r}; known: {', '.join(ENGINE_SPECS)}")
        if key not in out:
            out.append(key)
    return out


def load_manifest(cast_id: str) -> dict[str, Any]:
    path = os.path.join(cast_dir(cast_id), "manifest.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(cast_id: str, data: dict[str, Any]) -> None:
    root = cast_dir(cast_id)
    os.makedirs(root, exist_ok=True)
    os.makedirs(os.path.join(root, "candidates"), exist_ok=True)
    path = os.path.join(root, "manifest.json")
    data["updated_at"] = utc_now_iso()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def ensure_cast(
    cast_id: str,
    *,
    prompt: str,
    negative: str = "",
    engines: list[str] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    root = cast_dir(cast_id)
    os.makedirs(os.path.join(root, "candidates"), exist_ok=True)
    man_path = os.path.join(root, "manifest.json")
    if os.path.isfile(man_path):
        man = load_manifest(cast_id)
        if prompt:
            man["prompt"] = prompt
        if negative:
            man["negative"] = negative
        if engines:
            man["engines"] = engines
        save_manifest(cast_id, man)
        return man

    man = {
        "cast_id": cast_id,
        "status": "open",
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "prompt": prompt,
        "negative": negative or (
            "blurry, low quality, deformed face, extra fingers, watermark, text, logo"
        ),
        "engines": engines or ["moody_pro", "krea"],
        "notes": notes,
        "candidates": [],
        "shortlist": [],
        "promoted_character_id": None,
        "research_notes": [
            "Phase A exploration only — multi-engine T2I, no identity lock yet.",
            "Community pattern: cast many → human pick → lock sheet (I2I/CN).",
        ],
    }
    save_manifest(cast_id, man)
    brief = os.path.join(root, "brief.md")
    if not os.path.isfile(brief):
        with open(brief, "w", encoding="utf-8") as f:
            f.write(f"# Cast pool: {cast_id}\n\n")
            f.write("## Prompt\n\n")
            f.write(prompt.strip() + "\n\n")
            f.write("## Process\n\n")
            f.write("1. Review `candidates/` + `contact_sheet.png`\n")
            f.write("2. `character_promote.py --from <img> --id <char_id> ...`\n")
            f.write("3. `character_expand_sheets.py --id <char_id>`\n")
    return man


def candidate_filename(cast_id: str, engine: str, seed: int, index: int) -> str:
    return f"{cast_id}__e{engine}__s{seed}__c{index:02d}.png"


def list_candidate_paths(cast_id: str) -> list[str]:
    root = os.path.join(cast_dir(cast_id), "candidates")
    if not os.path.isdir(root):
        return []
    files = [
        os.path.join(root, n)
        for n in sorted(os.listdir(root))
        if n.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    ]
    return files


def list_casts() -> list[str]:
    if not os.path.isdir(CASTS_DIR):
        return []
    out = []
    for name in sorted(os.listdir(CASTS_DIR)):
        if os.path.isfile(os.path.join(CASTS_DIR, name, "manifest.json")):
            out.append(name)
    return out


def format_cast_status(cast_id: str) -> str:
    man = load_manifest(cast_id)
    paths = list_candidate_paths(cast_id)
    lines = [
        f"cast={cast_id} status={man.get('status')} engines={man.get('engines')}",
        f"candidates_disk={len(paths)} manifest_entries={len(man.get('candidates') or [])}",
        f"shortlist={man.get('shortlist') or []}",
        f"promoted_character_id={man.get('promoted_character_id') or '—'}",
        f"prompt={(man.get('prompt') or '')[:100]}…",
        "",
        f"{'#':<3} {'ENGINE':<12} {'SEED':<10} {'FILE'}",
    ]
    for i, c in enumerate(man.get("candidates") or [], 1):
        lines.append(
            f"{i:<3} {str(c.get('engine') or '?'):<12} "
            f"{str(c.get('seed') or '?'):<10} {c.get('file') or '?'}"
        )
    if not (man.get("candidates") or []) and paths:
        for i, p in enumerate(paths, 1):
            lines.append(f"{i:<3} {'(disk)':<12} {'—':<10} candidates/{os.path.basename(p)}")
    return "\n".join(lines)


def add_shortlist(cast_id: str, files: list[str]) -> dict[str, Any]:
    man = load_manifest(cast_id)
    sl = list(man.get("shortlist") or [])
    for f in files:
        rel = f.replace("\\", "/")
        if "candidates/" not in rel and not os.path.isabs(f):
            rel = f"candidates/{os.path.basename(f)}"
        elif os.path.isabs(f):
            rel = f"candidates/{os.path.basename(f)}"
        if rel not in sl:
            sl.append(rel)
    man["shortlist"] = sl
    man["status"] = "shortlisted" if sl else man.get("status")
    save_manifest(cast_id, man)
    return man
