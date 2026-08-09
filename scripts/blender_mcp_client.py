#!/usr/bin/env python3
"""Backward-compatible Blender MCP client.

Prefer: `from lib.blender_mcp import exec_blender_code, probe_blender`
This module re-exports for legacy mecha scripts.
"""

from __future__ import annotations

from lib.blender_mcp import (  # noqa: F401
    DEFAULT_HOST,
    DEFAULT_PORT,
    exec_blender_code,
    probe_blender,
    unwrap_result,
)

if __name__ == "__main__":
    import json
    import sys

    r = probe_blender()
    print(json.dumps(r, ensure_ascii=False, indent=2))
    raise SystemExit(0 if r.get("ok") else 1)
