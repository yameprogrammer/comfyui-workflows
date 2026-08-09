"""Blender MCP client — execute Python inside a running Blender with MCP server.

Default: 127.0.0.1:9876 (common blender-mcp / addon port).

  from lib.blender_mcp import exec_blender_code, probe_blender

Agent tools should fail closed when Blender is not reachable.
"""

from __future__ import annotations

import json
import socket
from typing import Any


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9876
DEFAULT_TIMEOUT_SEC = 120.0


def probe_blender(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout_sec: float = 3.0,
) -> dict[str, Any]:
    """Return {ok, blender_version?} or {ok: False, error}."""
    code = """
import bpy
result = {
    "status": "ok",
    "blender_version": list(bpy.app.version),
    "object_count": len(bpy.data.objects),
}
"""
    try:
        res = exec_blender_code(code, host=host, port=port, timeout_sec=timeout_sec)
    except Exception as e:
        return {"ok": False, "error": "CONNECT", "message": str(e)}
    payload = _unwrap(res)
    if isinstance(payload, dict) and payload.get("status") == "ok":
        return {
            "ok": True,
            "blender_version": payload.get("blender_version"),
            "object_count": payload.get("object_count"),
        }
    return {"ok": False, "error": "BAD_RESPONSE", "message": str(res)[:500]}


def exec_blender_code(
    code: str,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    strict_json: bool = False,
) -> dict[str, Any]:
    """Send execute request; return parsed JSON response from Blender MCP."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(float(timeout_sec))
    try:
        sock.connect((host, int(port)))
        req = {
            "type": "execute",
            "code": code,
            "strict_json": bool(strict_json),
        }
        payload = json.dumps(req).encode("utf-8") + b"\x00"
        sock.sendall(payload)

        buf = bytearray()
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buf.extend(chunk)
            if b"\x00" in buf:
                break
    finally:
        try:
            sock.close()
        except Exception:
            pass

    raw = buf.decode("utf-8", errors="replace").rstrip("\x00")
    if not raw.strip():
        raise RuntimeError("empty response from Blender MCP")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"non-JSON Blender MCP response: {raw[:400]}") from e


def _unwrap(res: Any) -> Any:
    if not isinstance(res, dict):
        return res
    payload = res.get("result", res)
    if isinstance(payload, str):
        try:
            return json.loads(payload)
        except Exception:
            return payload
    return payload


def unwrap_result(res: Any) -> dict[str, Any]:
    """Normalize MCP response to a dict with status field when possible."""
    payload = _unwrap(res)
    if isinstance(payload, dict):
        return payload
    return {"status": "error", "message": str(payload)[:800]}
