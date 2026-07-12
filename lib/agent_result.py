"""Unified agent-facing result envelope for pipeline / smoke / QA."""

from __future__ import annotations

import json
import os
from typing import Any

from lib.comfy_client import utc_now_iso, write_meta


def agent_result(
    *,
    ok: bool,
    tool: str,
    episode_id: str | None = None,
    error: str | None = None,
    message: str | None = None,
    exit_code: int = 0,
    artifacts: list[dict[str, Any]] | None = None,
    qa: dict[str, Any] | None = None,
    stages: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a machine-readable result dict for agents."""
    out: dict[str, Any] = {
        "ok": bool(ok),
        "tool": tool,
        "episode_id": episode_id,
        "error": error,
        "message": message,
        "exit_code": int(exit_code),
        "artifacts": artifacts or [],
        "qa": qa,
        "stages": stages or [],
        "created_at": utc_now_iso(),
    }
    if extra:
        out.update(extra)
    return out


def write_agent_result(path: str, result: dict[str, Any]) -> str:
    """Persist result JSON; returns absolute path."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    write_meta(path, result)
    return os.path.abspath(path)


def print_agent_summary(result: dict[str, Any]) -> None:
    """Human + agent-friendly one-block summary on stdout."""
    ok = result.get("ok")
    print("=== AGENT_RESULT ===")
    print(f"ok={ok} tool={result.get('tool')} episode={result.get('episode_id')}")
    if result.get("error"):
        print(f"error={result.get('error')}")
    if result.get("message"):
        print(f"message={result.get('message')}")
    print(f"exit_code={result.get('exit_code')}")
    for s in result.get("stages") or []:
        print(
            f"  stage={s.get('name')} exit={s.get('exit_code')} "
            f"ok={s.get('ok')}"
        )
    qa = result.get("qa") or {}
    if qa:
        print(
            f"  qa.ok={qa.get('ok')} issues={len(qa.get('issues') or [])} "
            f"warnings={len(qa.get('warnings') or [])}"
        )
        for i in (qa.get("issues") or [])[:8]:
            print(f"    [ISSUE] {i.get('code')}: {i.get('message')}")
    arts = result.get("artifacts") or []
    if arts:
        print(f"  artifacts={len(arts)}")
        for a in arts[:12]:
            print(f"    - {a.get('role')}: {a.get('path')}")
    # Contract notes for agents
    notes = result.get("agent_notes") or []
    for n in notes:
        print(f"  NOTE: {n}")
    print("=== END_AGENT_RESULT ===")


def dumps_agent_result(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)
