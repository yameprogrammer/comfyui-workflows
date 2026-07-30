"""S2V backend node preflight against ComfyUI /object_info.

Use before queueing InfiniteTalk (or other graph backends) so agents fail
with BACKEND_UNAVAILABLE instead of HTTP 400 missing_node_type.
"""

from __future__ import annotations

from typing import Any

from lib.comfy_client import DEFAULT_SERVER, _http_json

# Factory graph: scripts/generate_s2v.py build_infinitetalk_api
INFINITETALK_REQUIRED_NODES: list[str] = [
    "WanVideoClipVisionEncode",
    "WanVideoModelLoader",
    "WanVideoSampler",
    "WanVideoDecode",
    "WanVideoVAELoader",
    "WanVideoTextEncodeCached",
    "WanVideoImageToVideoMultiTalk",
    "WanVideoBlockSwap",
    "MultiTalkModelLoader",
    "MultiTalkWav2VecEmbeds",
    "DownloadAndLoadWav2VecModel",
    "CLIPVisionLoader",
    "JWLoadAudio",
    "ImageResizeKJv2",
    "VHS_VideoCombine",
    "LoadImage",
]

# Soft dependencies (optional features)
INFINITETALK_OPTIONAL_NODES: list[str] = [
    "WanVideoLoraSelect",
    "WanVideoSetLoRAs",
    "WanVideoTeaCache",
]

REQUIRED_NODES_S2V: dict[str, list[str]] = {
    "infinitetalk": list(INFINITETALK_REQUIRED_NODES),
}

HINTS_S2V: dict[str, str] = {
    "infinitetalk": (
        "Re-enable ComfyUI-WanVideoWrapper under custom_nodes "
        "(folder must NOT end with .disabled), restart Comfy, then: "
        "python scripts/tool_health.py --backend infinitetalk. "
        "Until healthy, use --backend ltx23_ia2v. "
        "See docs/superpowers/plans/2026-07-30-full-sheet-and-infinitetalk-fix.md"
    ),
}


def fetch_object_info(
    server_address: str = DEFAULT_SERVER,
    *,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """GET /object_info; keys are class_type names."""
    data = _http_json(server_address, "/object_info", timeout=timeout)
    if not isinstance(data, dict):
        return {}
    return data


def check_backend_nodes(
    backend: str,
    object_info: dict[str, Any] | None = None,
    server: str | None = None,
    *,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Return ok/missing/present for a s2v backend's required class_types.

    Unknown backends with no registry entry return ok=True (no check).
    """
    b = (backend or "").strip().lower()
    required = list(REQUIRED_NODES_S2V.get(b) or [])
    if not required:
        return {
            "ok": True,
            "backend": b,
            "missing": [],
            "present": [],
            "required": [],
            "hint": "",
            "skipped": True,
            "message": f"no required-node registry for {b!r}",
        }

    info = object_info
    err: str | None = None
    if info is None:
        try:
            info = fetch_object_info(server or DEFAULT_SERVER, timeout=timeout)
        except Exception as e:
            return {
                "ok": False,
                "backend": b,
                "missing": list(required),
                "present": [],
                "required": required,
                "hint": HINTS_S2V.get(b, ""),
                "skipped": False,
                "error": "COMFY_UNREACHABLE",
                "message": str(e)[:400],
            }

    present = [n for n in required if n in info]
    missing = [n for n in required if n not in info]
    optional = INFINITETALK_OPTIONAL_NODES if b == "infinitetalk" else []
    optional_missing = [n for n in optional if n not in info]

    ok = len(missing) == 0
    hint = HINTS_S2V.get(b, "") if not ok else ""
    msg = (
        f"backend {b}: all {len(required)} required nodes present"
        if ok
        else f"backend {b}: missing {len(missing)} node(s): {', '.join(missing[:8])}"
        + ("…" if len(missing) > 8 else "")
    )
    return {
        "ok": ok,
        "backend": b,
        "missing": missing,
        "present": present,
        "required": required,
        "optional_missing": optional_missing,
        "hint": hint,
        "skipped": False,
        "error": None if ok else "BACKEND_UNAVAILABLE",
        "message": msg,
    }


def list_checked_backends() -> list[str]:
    return sorted(REQUIRED_NODES_S2V.keys())
