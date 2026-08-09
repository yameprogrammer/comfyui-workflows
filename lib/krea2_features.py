"""Lonecat Krea2 / Krea2 stack feature inventory for agents.

Reads:
  workflows/human/lonecat_krea2_v70/CAPABILITIES.json  (v7 full graph map)
  workflows/human/Krea2_SFW_NSFW_v10_CAPABILITIES.json (slim v10 features)

Discovery only — does not run Comfy.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from lib.comfy_client import WORKSPACE_ROOT

V70_CAP = os.path.join(
    WORKSPACE_ROOT,
    "workflows",
    "human",
    "lonecat_krea2_v70",
    "CAPABILITIES.json",
)
V10_CAP = os.path.join(
    WORKSPACE_ROOT,
    "workflows",
    "human",
    "Krea2_SFW_NSFW_v10_CAPABILITIES.json",
)

READYISH = frozenset(
    {
        "ready",
        "ready_via_v10",
        "ready_via_other_tool",
        "ready_experimental",
        "ready_in_v10_preset",
        "ready_in_t2i_preset",
    }
)


def _load(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def all_features(*, source: str | None = None) -> list[dict[str, Any]]:
    """Flatten features with `source` field (v70 | v10)."""
    out: list[dict[str, Any]] = []
    src_filter = (source or "").strip().lower() or None

    if src_filter in (None, "v70", "v7", "lonecat"):
        cap = _load(V70_CAP)
        for f in cap.get("features") or []:
            row = dict(f)
            row["source"] = "v70"
            row["workflow"] = cap.get("workflow")
            out.append(row)

    if src_filter in (None, "v10", "uncensored", "sfw_nsfw"):
        cap = _load(V10_CAP)
        for f in cap.get("features") or []:
            row = dict(f)
            row["source"] = "v10"
            row["workflow"] = cap.get("workflow")
            out.append(row)

    return out


def get_feature(feature_id: str) -> dict[str, Any] | None:
    fid = (feature_id or "").strip()
    for f in all_features():
        if f.get("feature_id") == fid:
            return f
    return None


def search_features(query: str, *, limit: int = 20) -> list[dict[str, Any]]:
    q = (query or "").strip().lower()
    if not q:
        return all_features()[:limit]
    tokens = [t for t in q.replace("/", " ").split() if t]
    scored: list[tuple[float, dict[str, Any]]] = []
    for f in all_features():
        blob = " ".join(
            str(x)
            for x in (
                f.get("feature_id"),
                f.get("name"),
                f.get("category"),
                f.get("when_to_use"),
                f.get("status"),
                f.get("agent_cli"),
                f.get("interim_cli"),
                " ".join(f.get("ui_groups") or []),
            )
            if x
        ).lower()
        score = 0.0
        for t in tokens:
            if t in blob:
                score += 3.0
            if t in str(f.get("feature_id", "")).lower():
                score += 4.0
        if score > 0:
            scored.append((score, f))
    scored.sort(key=lambda x: (-x[0], str(x[1].get("feature_id"))))
    return [r for _, r in scored[: max(1, limit)]]


def format_feature(f: dict[str, Any], *, verbose: bool = True) -> str:
    lines = [
        f"[{f.get('source')}] {f.get('feature_id')}  status={f.get('status')}",
        f"  {f.get('name')}",
    ]
    if f.get("when_to_use"):
        lines.append(f"  when: {f.get('when_to_use')}")
    cli = f.get("agent_cli") or f.get("interim_cli")
    if cli:
        lines.append(f"  cli:  {cli}")
    elif f.get("status") in READYISH:
        lines.append("  cli:  (see preset / CAPABILITIES)")
    else:
        lines.append("  cli:  (not wired — use UI or wait for API preset)")
    if verbose and f.get("gap"):
        lines.append(f"  gap:  {f.get('gap')}")
    if verbose and f.get("needs"):
        lines.append(f"  needs:{f.get('needs')}")
    if verbose and f.get("note"):
        lines.append(f"  note: {f.get('note')}")
    return "\n".join(lines)


def status_summary() -> dict[str, int]:
    counts: dict[str, int] = {}
    for f in all_features():
        st = str(f.get("status") or "?")
        counts[st] = counts.get(st, 0) + 1
    return counts


def ready_routes() -> list[dict[str, str]]:
    """Features an agent can call today without opening full v7 UI."""
    rows = []
    for f in all_features():
        st = str(f.get("status") or "")
        if st not in READYISH and not f.get("interim_cli"):
            continue
        cli = f.get("agent_cli") or f.get("interim_cli")
        if not cli:
            continue
        rows.append(
            {
                "feature_id": str(f.get("feature_id")),
                "status": st,
                "cli": str(cli),
                "name": str(f.get("name") or ""),
            }
        )
    return rows
