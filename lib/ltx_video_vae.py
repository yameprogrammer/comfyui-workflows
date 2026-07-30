"""LTX-2.3 video VAE selection: stock vs PrunaVAED (Kijai Comfy convert).

PrunaVAED (PrunaAI) is a drop-in *decoder* for LTX-2.3: ~1.7× decode wall,
~50% lower peak decode VRAM, near-original quality (HF bench). Encoder/latent
format unchanged. Comfy weight (Kijai convert) embeds pruned `config` metadata
so stock VAELoader works when the file is present.

Factory policy (2026-07-31):
  - prefer Pruna when file is on disk under models/vae (extra_model_paths)
  - fallback to stock LTX23 video VAE
  - override: AGENT_LTX_VIDEO_VAE=pruna|stock|<filename>
             or explicit resolve_ltx_video_vae(...)

Audio VAE and TAE preview VAEs are never swapped here.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Stock factory video VAE
STOCK_VIDEO_VAE = "LTX23_video_vae_bf16.safetensors"
# Kijai Comfy convert of PrunaAI/PrunaVAED
PRUNA_VIDEO_VAE = "pruna_ltx2.3_vae_comfy_bf16.safetensors"

_DEFAULT_VAE_DIRS = (
    Path(r"F:\model\vae"),
    Path(r"F:\ComfyUI_windows_portable\ComfyUI\models\vae"),
)


def _vae_search_dirs() -> list[Path]:
    dirs: list[Path] = []
    for key in ("AGENT_COMFY_VAE_DIR", "COMFYUI_VAE_DIR"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            dirs.append(Path(raw))
    data = (os.environ.get("AGENT_COMFY_DATA_DIR") or os.environ.get("COMFYUI_DATA_DIR") or "").strip()
    if data:
        dirs.append(Path(data) / "models" / "vae")
    dirs.extend(_DEFAULT_VAE_DIRS)
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[Path] = []
    for d in dirs:
        k = str(d).lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(d)
    return out


def vae_file_exists(name: str) -> bool:
    """True if ``name`` is found under known vae dirs (or absolute path)."""
    n = (name or "").strip()
    if not n:
        return False
    p = Path(n)
    if p.is_file():
        return True
    base = Path(n).name
    for d in _vae_search_dirs():
        if (d / base).is_file():
            return True
    return False


def resolve_ltx_video_vae(
    prefer: str | None = None,
    *,
    require_pruna: bool = False,
) -> dict[str, Any]:
    """Resolve which video VAE filename to load.

    ``prefer`` (or env AGENT_LTX_VIDEO_VAE):
      - None / \"auto\" — Pruna if on disk, else stock
      - \"pruna\" / \"prunavaed\" / \"fast\" — Pruna (fallback stock unless require_pruna)
      - \"stock\" / \"default\" / \"ltx\" — stock LTX23 video
      - any other string — treated as filename (basename)

    Returns dict: name, kind (pruna|stock|custom), source, exists, fallback_used.
    """
    raw = (prefer if prefer is not None else os.environ.get("AGENT_LTX_VIDEO_VAE") or "auto")
    raw = str(raw).strip()
    low = raw.lower().replace("\\", "/")

    def _ok(name: str) -> bool:
        return vae_file_exists(name)

    result: dict[str, Any] = {
        "name": STOCK_VIDEO_VAE,
        "kind": "stock",
        "source": "default",
        "exists": _ok(STOCK_VIDEO_VAE),
        "fallback_used": False,
        "prefer": raw,
        "pruna_name": PRUNA_VIDEO_VAE,
        "stock_name": STOCK_VIDEO_VAE,
    }

    if low in ("", "auto", "prefer_pruna", "default_auto"):
        if _ok(PRUNA_VIDEO_VAE):
            result.update(name=PRUNA_VIDEO_VAE, kind="pruna", source="auto", exists=True)
        else:
            result.update(
                name=STOCK_VIDEO_VAE,
                kind="stock",
                source="auto_fallback_stock",
                exists=_ok(STOCK_VIDEO_VAE),
                fallback_used=True,
            )
        return result

    if low in ("pruna", "prunavaed", "pruna_vae", "fast", "speed"):
        if _ok(PRUNA_VIDEO_VAE):
            result.update(name=PRUNA_VIDEO_VAE, kind="pruna", source="explicit_pruna", exists=True)
            return result
        if require_pruna:
            result.update(
                name=PRUNA_VIDEO_VAE,
                kind="pruna",
                source="missing_pruna",
                exists=False,
                fallback_used=False,
            )
            return result
        result.update(
            name=STOCK_VIDEO_VAE,
            kind="stock",
            source="pruna_missing_fallback_stock",
            exists=_ok(STOCK_VIDEO_VAE),
            fallback_used=True,
        )
        return result

    if low in ("stock", "default", "ltx", "ltx23", "official", "full"):
        result.update(
            name=STOCK_VIDEO_VAE,
            kind="stock",
            source="explicit_stock",
            exists=_ok(STOCK_VIDEO_VAE),
        )
        return result

    # custom filename
    base = Path(raw.replace("\\", "/")).name
    result.update(
        name=base,
        kind="custom" if base not in (PRUNA_VIDEO_VAE, STOCK_VIDEO_VAE) else (
            "pruna" if base == PRUNA_VIDEO_VAE else "stock"
        ),
        source="filename",
        exists=_ok(base),
    )
    return result


def is_ltx_video_vae_name(name: str) -> bool:
    """Heuristic: filename is an LTX *video* VAE (not audio, not TAE)."""
    low = (name or "").lower().replace("\\", "/")
    if not low:
        return False
    if "audio" in low:
        return False
    if "tae" in low:
        return False
    if "pruna" in low and "ltx" in low:
        return True
    if "ltx23_video" in low or "ltx_video" in low or "ltx-2" in low and "video" in low:
        return True
    if low.endswith("ltx23_video_vae_bf16.safetensors"):
        return True
    if low == PRUNA_VIDEO_VAE.lower() or low == STOCK_VIDEO_VAE.lower():
        return True
    return False


def apply_ltx_video_vae_to_api(
    api: dict[str, Any],
    *,
    prefer: str | None = None,
    require_pruna: bool = False,
) -> dict[str, Any]:
    """Patch VAELoader / VAELoaderKJ video nodes in an API prompt graph.

    Only nodes whose current vae_name looks like LTX video (or empty stock path)
    are patched. Audio + TAE left alone.
    """
    resolved = resolve_ltx_video_vae(prefer, require_pruna=require_pruna)
    target = str(resolved["name"])
    patched: list[str] = []
    skipped: list[dict[str, str]] = []

    for nid, node in (api or {}).items():
        if not isinstance(node, dict):
            continue
        ct = node.get("class_type") or ""
        if ct not in ("VAELoader", "VAELoaderKJ"):
            continue
        inputs = node.setdefault("inputs", {})
        cur = str(inputs.get("vae_name") or "")
        if is_ltx_video_vae_name(cur) or cur in ("", STOCK_VIDEO_VAE, PRUNA_VIDEO_VAE):
            # Also accept bare stock name variants
            if cur and not is_ltx_video_vae_name(cur) and "tae" not in cur.lower() and "audio" not in cur.lower():
                # unknown non-empty non-ltx — skip
                if cur.lower() not in (
                    STOCK_VIDEO_VAE.lower(),
                    PRUNA_VIDEO_VAE.lower(),
                ):
                    skipped.append({"id": str(nid), "vae_name": cur, "reason": "not_ltx_video"})
                    continue
            inputs["vae_name"] = target
            patched.append(str(nid))
        else:
            skipped.append({"id": str(nid), "vae_name": cur, "reason": "not_ltx_video"})

    return {
        **resolved,
        "patched_node_ids": patched,
        "skipped": skipped,
        "applied": bool(patched),
    }
