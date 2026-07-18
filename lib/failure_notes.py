"""Shared agent failure notes under failures/."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from lib.comfy_client import WORKSPACE_ROOT

FAILURES_DIR = os.path.join(WORKSPACE_ROOT, "failures")
NOTES_DIR = os.path.join(FAILURES_DIR, "notes")
INDEX_PATH = os.path.join(FAILURES_DIR, "INDEX.md")
TAGS_PATH = os.path.join(FAILURES_DIR, "tags.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_dirs() -> None:
    os.makedirs(NOTES_DIR, exist_ok=True)


def load_tags() -> list[str]:
    if not os.path.isfile(TAGS_PATH):
        return []
    with open(TAGS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("tags") or [])


def _next_id(created_at: str | None = None) -> str:
    ensure_dirs()
    day = (created_at or _utc_now())[:10].replace("-", "")
    prefix = f"FN-{day}-"
    n = 0
    for name in os.listdir(NOTES_DIR):
        if name.startswith(prefix) and name.endswith(".json"):
            try:
                n = max(n, int(name[len(prefix) : -5]))
            except ValueError:
                pass
    return f"{prefix}{n + 1:03d}"


def note_path(note_id: str) -> str:
    return os.path.join(NOTES_DIR, f"{note_id}.json")


def write_note(note: dict[str, Any]) -> str:
    ensure_dirs()
    nid = note["id"]
    path = note_path(nid)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(note, f, ensure_ascii=False, indent=2)
        f.write("\n")
    rebuild_index()
    return path


def create_note(
    *,
    stage: str,
    tags: list[str],
    symptom: str,
    root_cause: str,
    fix: str,
    prevention: str,
    severity: str = "medium",
    agent: str = "unknown",
    episode_id: str | None = None,
    shot_id: str | None = None,
    related_paths: list[str] | None = None,
    user_visible: bool = True,
    refs: list[str] | None = None,
) -> dict[str, Any]:
    created = _utc_now()
    note = {
        "id": _next_id(created),
        "created_at": created,
        "agent": agent or "unknown",
        "episode_id": episode_id,
        "shot_id": shot_id,
        "stage": stage,
        "tags": [t.strip() for t in tags if t and t.strip()],
        "symptom": symptom.strip(),
        "root_cause": root_cause.strip(),
        "fix": fix.strip(),
        "prevention": prevention.strip(),
        "related_paths": related_paths or [],
        "severity": severity,
        "user_visible": bool(user_visible),
        "refs": refs or [],
    }
    if not note["tags"]:
        raise ValueError("tags required")
    for key in ("symptom", "root_cause", "fix", "prevention"):
        if len(note[key]) < 8:
            raise ValueError(f"{key} too short")
    write_note(note)
    return note


def list_notes(*, limit: int | None = None) -> list[dict[str, Any]]:
    ensure_dirs()
    notes: list[dict[str, Any]] = []
    for name in sorted(os.listdir(NOTES_DIR), reverse=True):
        if not name.endswith(".json"):
            continue
        path = os.path.join(NOTES_DIR, name)
        try:
            with open(path, encoding="utf-8") as f:
                notes.append(json.load(f))
        except (OSError, json.JSONDecodeError):
            continue
    notes.sort(key=lambda n: n.get("created_at") or "", reverse=True)
    if limit is not None:
        notes = notes[: max(0, int(limit))]
    return notes


def search_notes(
    query: str | None = None,
    *,
    tags: list[str] | None = None,
    stage: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    tags = [t.lower() for t in (tags or []) if t]
    q = (query or "").strip().lower()
    # support simple OR in query
    q_parts = [p.strip() for p in re.split(r"\s+OR\s+", q, flags=re.I) if p.strip()] if q else []

    out: list[dict[str, Any]] = []
    for note in list_notes():
        if stage and note.get("stage") != stage:
            continue
        note_tags = [str(t).lower() for t in (note.get("tags") or [])]
        if tags and not all(t in note_tags for t in tags):
            continue
        blob = " ".join(
            [
                note.get("id") or "",
                note.get("symptom") or "",
                note.get("root_cause") or "",
                note.get("fix") or "",
                note.get("prevention") or "",
                " ".join(note_tags),
                note.get("episode_id") or "",
                note.get("shot_id") or "",
            ]
        ).lower()
        if q_parts:
            if not any(p in blob for p in q_parts):
                continue
        elif q and q not in blob:
            continue
        out.append(note)
        if len(out) >= limit:
            break
    return out


def rebuild_index() -> None:
    ensure_dirs()
    notes = list_notes(limit=200)
    lines = [
        "# Failure notes INDEX (auto-generated)",
        "",
        "Do not edit by hand — `python scripts/failure_note.py add` regenerates.",
        "",
        "| id | sev | stage | tags | symptom |",
        "|----|-----|-------|------|---------|",
    ]
    for n in notes:
        tags = ", ".join(n.get("tags") or [])[:40]
        sym = (n.get("symptom") or "").replace("|", "/").replace("\n", " ")
        if len(sym) > 80:
            sym = sym[:77] + "..."
        lines.append(
            f"| `{n.get('id')}` | {n.get('severity')} | {n.get('stage')} | {tags} | {sym} |"
        )
    lines.append("")
    lines.append(f"_Updated: {_utc_now()} · count={len(notes)}_")
    lines.append("")
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def format_note_brief(note: dict[str, Any]) -> str:
    tags = ", ".join(note.get("tags") or [])
    return (
        f"{note.get('id')} [{note.get('severity')}/{note.get('stage')}] ({tags})\n"
        f"  symptom: {note.get('symptom')}\n"
        f"  cause:   {note.get('root_cause')}\n"
        f"  prevent: {note.get('prevention')}"
    )


def format_note_prevention(note: dict[str, Any]) -> str:
    """Before-gen focused card: prevention first (mistake prevention)."""
    tags = ", ".join(note.get("tags") or [])
    return (
        f"{note.get('id')} [{note.get('severity')}/{note.get('stage')}] ({tags})\n"
        f"  DO NOT: {note.get('symptom')}\n"
        f"  PREVENT: {note.get('prevention')}\n"
        f"  (cause was: {note.get('root_cause')})"
    )


def before_gen_checklist(query: str | None, *, limit: int = 8) -> list[dict[str, Any]]:
    """
    Search failure notes for a before-generation preflight.
    Empty query → recent high/critical notes.
    """
    q = (query or "").strip()
    if q:
        return search_notes(q, limit=limit)
    # no query: surface severe recent lessons
    notes = list_notes(limit=40)
    severe = [
        n
        for n in notes
        if str(n.get("severity") or "").lower() in ("critical", "high")
    ]
    return severe[: max(1, int(limit))]
