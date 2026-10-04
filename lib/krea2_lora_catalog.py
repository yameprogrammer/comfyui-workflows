"""Krea2 LoRA catalog for agents.

Drop weights in F:\\model\\loras\\Krea2.
A sibling ``<stem>.purpose.json`` says when to use the file.
Built-in cards cover the LoRAs already on disk.

SSOT: docs/krea2_loras_agent.md
CLI: scripts/krea2_lora_status.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

LORA_LIBRARY = Path(r"F:\model\loras")
DROP_ROOTS = [
    LORA_LIBRARY / "Krea2",
    LORA_LIBRARY / "Krea 2",
]
WEIGHT_SUFFIXES = {".safetensors", ".gguf"}
SLOTS = ("t2i", "nsfw_t2i", "identity_edit", "control")
MIN_BYTES = 1_000_000

# Basename → purpose. A sibling .purpose.json overrides these fields.
KNOWN: dict[str, dict[str, Any]] = {
    "krea2_darkbrush.safetensors": {
        "id": "darkbrush",
        "slot": "t2i",
        "purpose": "Krea2 스틸에 다크 브러시·회화 질감을 얹는다",
        "when": [
            "붓터치·회화 질감이 보여야 하는 Krea2 스틸",
            "dark brush or painterly texture on a still",
        ],
        "when_not": [
            "깨끗한 실사 기본 키프레임",
            "얼굴만 고치는 identity edit",
            "뎁스·포즈 구조 제어",
        ],
        "strength": 0.7,
        "trigger": None,
        "keywords": [
            "darkbrush",
            "brush",
            "붓",
            "브러시",
            "회화",
            "페인터",
            "painterly",
            "paint",
        ],
    },
    "krea2_identity_edit_v1_2.safetensors": {
        "id": "identity_edit",
        "slot": "identity_edit",
        "purpose": "기존 얼굴은 두고 한 가지만 고친다",
        "when": [
            "이미 있는 얼굴은 두고 한 가지만 고칠 때",
            "one change on an existing face",
        ],
        "when_not": [
            "텍스트만으로 새 스틸",
            "generate_krea --lora 슬롯",
            "뎁스 구조 제어",
        ],
        "strength": 1.0,
        "trigger": None,
        "keywords": ["identity", "아이덴티티", "얼굴", "같은 얼굴", "edit"],
    },
    "depth-control-lora.safetensors": {
        "id": "depth_control",
        "slot": "control",
        "purpose": "뎁스·구조 이미지를 따라 Krea2 실사를 다시 그린다",
        "when": [
            "뎁스나 구조 이미지를 따라 실사를 다시 그릴 때",
            "depth or structure control",
        ],
        "when_not": [
            "텍스트만으로 새 스틸",
            "generate_krea --lora 슬롯",
            "얼굴 한 곳만 수정",
        ],
        "strength": 1.0,
        "trigger": None,
        "keywords": ["depth", "뎁스", "control", "구조", "포즈"],
    },
}


def _comfy_name(path: Path) -> str:
    try:
        rel = path.resolve().relative_to(LORA_LIBRARY.resolve())
    except ValueError:
        rel = Path(path.name)
    return str(rel).replace("/", "\\")


def _load_sidecar(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    card_path = path.with_name(path.stem + ".purpose.json")
    if not card_path.is_file():
        return None, None
    try:
        data = json.loads(card_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(data, dict):
        return None, "purpose card must be a JSON object"
    return data, None


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _merge_card(basename: str, sidecar: dict[str, Any] | None) -> dict[str, Any]:
    base = dict(KNOWN.get(basename) or {})
    if sidecar:
        for key, value in sidecar.items():
            if value is not None:
                base[key] = value
    if "id" not in base:
        stem = Path(basename).stem
        base["id"] = re.sub(r"[^A-Za-z0-9_]+", "_", stem).strip("_").lower() or "lora"
    base["when"] = _as_str_list(base.get("when"))
    base["when_not"] = _as_str_list(base.get("when_not"))
    base["keywords"] = _as_str_list(base.get("keywords"))
    return base


def _usable(card: dict[str, Any]) -> str | None:
    slot = str(card.get("slot") or "").strip()
    if slot not in SLOTS:
        return "invalid_slot"
    if not str(card.get("purpose") or "").strip():
        return "unclassified"
    if not card.get("when"):
        return "unclassified"
    return None


def render_cli(entry: dict[str, Any]) -> str:
    slot = entry.get("slot")
    if slot == "t2i":
        lora = entry.get("comfy_name") or ""
        strength = entry.get("strength", 0.7)
        return (
            'python scripts/generate_krea.py -p "..." '
            f'--lora "{lora}" --lora-strength {strength} -o out.png'
        )
    if slot == "nsfw_t2i":
        lora = entry.get("comfy_name") or ""
        strength = entry.get("strength", 1.0)
        return (
            'python scripts/generate_krea_nsfw.py -p "..." '
            f'--lora "{lora}" --lora-strength {strength} -o out.png'
        )
    if slot == "identity_edit":
        return (
            "python scripts/generate_krea2_identity_edit.py "
            '-i face.png -p "Change only ..." -o out.png'
        )
    if slot == "control":
        return (
            'python scripts/generate_krea2_control.py -i depth.png -p "..." -o out.png'
        )
    return ""


def _iter_weights(roots: list[Path], min_bytes: int) -> list[Path]:
    found: list[Path] = []
    seen: set[tuple[int, int]] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in WEIGHT_SUFFIXES:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            if stat.st_size < min_bytes:
                continue
            key = (stat.st_dev, stat.st_ino)
            if key in seen:
                continue
            seen.add(key)
            found.append(path)
    return found


def catalog(
    roots: list[Path] | None = None,
    min_bytes: int = MIN_BYTES,
) -> list[dict[str, Any]]:
    """One row per weight file. ``apply`` is true only for a filled purpose card."""
    rows: list[dict[str, Any]] = []
    for path in _iter_weights(roots if roots is not None else DROP_ROOTS, min_bytes):
        sidecar, error = _load_sidecar(path)
        card = _merge_card(path.name, sidecar)
        if error:
            problem = "error_card"
        elif sidecar is None and path.name not in KNOWN:
            problem = "unclassified"
        else:
            problem = _usable(card)
        strength = card.get("strength", 0.7 if card.get("slot") == "t2i" else 1.0)
        try:
            strength = float(strength)
        except (TypeError, ValueError):
            strength = 0.7
            problem = problem or "invalid_strength"
        row: dict[str, Any] = {
            "id": card.get("id"),
            "name": path.name,
            "slot": card.get("slot"),
            "status": "ready" if problem is None else problem,
            "apply": problem is None,
            "purpose": str(card.get("purpose") or "").strip(),
            "when": card.get("when") or [],
            "when_not": card.get("when_not") or [],
            "strength": strength,
            "trigger": card.get("trigger"),
            "keywords": card.get("keywords") or [],
            "path": str(path),
            "comfy_name": _comfy_name(path),
            "purpose_card": str(path.with_name(path.stem + ".purpose.json")),
            "card_error": error,
        }
        if card.get("source"):
            row["source"] = card["source"]
        if card.get("notes"):
            row["notes"] = card["notes"]
        row["cli"] = render_cli(row) if row["apply"] else (
            f'python scripts/krea2_lora_status.py draft "{path.name}"'
        )
        rows.append(row)
    return rows


def status_summary(**kwargs: Any) -> dict[str, Any]:
    rows = catalog(**kwargs)
    return {
        "ok": True,
        "drop_roots": [str(p) for p in (kwargs.get("roots") or DROP_ROOTS)],
        "loras": rows,
        "ready_ids": [row["id"] for row in rows if row["apply"]],
        "blocked_ids": [row["id"] for row in rows if not row["apply"]],
        "rule": (
            "Apply at most one ready LoRA whose when matches the shot. "
            "t2i uses generate_krea --lora. nsfw_t2i uses generate_krea_nsfw --lora and is adult 18+ only. identity_edit and control use their own CLI. "
            "Unclassified files stay off. Clean photoreal stills use no LoRA."
        ),
    }


def recommend(query: str, **kwargs: Any) -> dict[str, Any]:
    """Pick a ready LoRA whose purpose/when/keywords overlap the query."""
    text = (query or "").strip().lower()
    tokens = [tok for tok in re.split(r"\s+", text) if len(tok) >= 2]
    scored: list[tuple[int, dict[str, Any]]] = []
    for row in catalog(**kwargs):
        if not row.get("apply"):
            continue
        blob = " ".join(
            [
                str(row.get("id") or ""),
                str(row.get("purpose") or ""),
                str(row.get("trigger") or ""),
                " ".join(row.get("when") or []),
                " ".join(row.get("keywords") or []),
            ]
        ).lower()
        score = 0
        for keyword in row.get("keywords") or []:
            if str(keyword).lower() in text:
                score += 3
        for when in row.get("when") or []:
            lowered = str(when).lower()
            if lowered and lowered in text:
                score += 2
        if str(row.get("id") or "").lower() in text:
            score += 2
        if str(row.get("purpose") or "").lower() and str(row["purpose"]).lower() in text:
            score += 2
        for tok in tokens:
            if tok in blob:
                score += 1
        if score:
            scored.append((score, row))
    scored.sort(key=lambda item: (-item[0], str(item[1].get("id"))))
    return {
        "query": query,
        "match": scored[0][1] if scored else None,
        "score": scored[0][0] if scored else 0,
        "alternatives": [row for _, row in scored[1:3]],
    }


def draft_card(filename: str, roots: list[Path] | None = None, min_bytes: int = MIN_BYTES) -> dict[str, Any]:
    """Write an empty purpose card next to a weight. Does not overwrite."""
    target_name = Path(filename).name
    hits = [
        path
        for path in _iter_weights(roots if roots is not None else DROP_ROOTS, min_bytes)
        if path.name == target_name
    ]
    if not hits:
        return {"ok": False, "error": "NOT_FOUND", "filename": target_name}
    path = hits[0]
    card_path = path.with_name(path.stem + ".purpose.json")
    if card_path.is_file():
        return {"ok": False, "error": "EXISTS", "purpose_card": str(card_path)}
    stem = re.sub(r"[^A-Za-z0-9_]+", "_", path.stem).strip("_").lower() or "lora"
    payload = {
        "id": stem,
        "slot": "t2i",
        "purpose": "",
        "when": [],
        "when_not": ["깨끗한 실사 기본 키프레임"],
        "strength": 0.7,
        "trigger": None,
        "keywords": [],
    }
    card_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"ok": True, "purpose_card": str(card_path), "path": str(path)}


def format_table(rows: list[dict[str, Any]] | None = None) -> str:
    data = rows if rows is not None else catalog()
    lines = [
        "Krea2 LoRAs (drop new files in F:\\model\\loras\\Krea2)",
        f"{'id':<22} {'status':<14} {'slot':<16} strength",
        "-" * 72,
    ]
    for row in data:
        lines.append(
            f"{str(row.get('id')):<22} {str(row.get('status')):<14} "
            f"{str(row.get('slot') or '-'):<16} {row.get('strength')}"
        )
        purpose = row.get("purpose") or "(no purpose yet)"
        lines.append(f"{'':22} {purpose}")
        if row.get("apply") and row.get("when"):
            lines.append(f"{'':22} when: {row['when'][0]}")
        if row.get("source"):
            lines.append(f"{'':22} source: {row['source']}")
        lines.append(f"{'':22} {row.get('cli')}")
    lines.append("")
    lines.append(
        "Rule: one ready LoRA only when its when matches. "
        "Unclassified stays off. Clean stills use generate_krea with no --lora."
    )
    lines.append("SSOT: docs/krea2_loras_agent.md")
    return "\n".join(lines)
