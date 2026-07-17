"""Boogu + Ideogram4 + Krea2 typography/design pipeline (RedCraft collection WF).

Source UI:
  workflows/human/NEWKrea2BooguIdeogram4_booguKrea2.json
  Civitai: NEW Krea2 & Ideogram4 WF — Boogu dense text + Ideogram layout + Krea polish

Pipeline (agent default without Gemini/SeedVR):
  caption → Boogu T2I → scale → Ideogram refine → Krea2 refine → SaveImage

Modes:
  boogu     — Boogu-only (dense text / poster draft)
  pipeline  — full chain, no SeedVR2 (default)
  upscale   — pipeline + SeedVR2 (heavy VRAM)

Agent supplies caption (JSON Ideogram-style or plain prose). GeminiNode is skipped;
caption is injected into Boogu / Ideogram / Krea encode nodes.
"""

from __future__ import annotations

import json
import os
import random
import shutil
from pathlib import Path
from typing import Any

from lib.comfy_client import (
    DEFAULT_SERVER,
    download_image,
    extract_first_image,
    fail_result,
    ok_result,
    queue_prompt,
    utc_now_iso,
    wait_for_history,
    write_meta,
)
from lib.ltx_aio_ui_expand import expand_ui_workflow_to_api

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
HUMAN_UI = WORKSPACE_ROOT / "workflows" / "human" / "NEWKrea2BooguIdeogram4_booguKrea2.json"

# Node sets for prune (after expand; subgraph instance 907:*)
BOOGU_NODES = {
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "11",
}
# Ideogram branch needs Boogu image feed for this pack (scale 917 from boogu decode)
PIPELINE_EXTRA = {
    "917",
    "901",
    "902",
    "903",
    "908",
    "915",
    "920",
    "921",
    "922",
    "923",
    "924",
    "925",
    "926",
    "927",
    "928",
}
# subgraph ideogram internals (prefixes)
IDEOGRAM_PREFIX = "907:"
SEEDVR_NODES = {"909", "910", "911", "912"}
# Always drop for agent (API key / unused primitives)
DROP_ALWAYS = {
    "900",
    "904",
    "905",
    "906",
    "913",
    "914",
    "916",
    "GeminiNode",
}


def _load_ui(path: Path | str | None = None) -> dict[str, Any]:
    p = Path(path or HUMAN_UI)
    if not p.is_file():
        raise FileNotFoundError(f"workflow not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _fetch_object_info(server: str = DEFAULT_SERVER) -> dict[str, Any] | None:
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://{server}/object_info", timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _set(api: dict[str, Any], nid: str, key: str, value: Any) -> None:
    if nid not in api:
        return
    api[nid].setdefault("inputs", {})[key] = value


def _alive_keep(mode: str) -> set[str]:
    mode = (mode or "pipeline").lower().strip()
    if mode in ("boogu", "boogu_only"):
        return set(BOOGU_NODES)
    keep = set(BOOGU_NODES) | set(PIPELINE_EXTRA)
    # keep all 907:* from api later
    if mode in ("upscale", "pipeline_upscale", "full"):
        keep |= set(SEEDVR_NODES)
    return keep


def _prune_api(api: dict[str, Any], mode: str) -> dict[str, Any]:
    mode = (mode or "pipeline").lower().strip()
    keep_ids = _alive_keep(mode)
    out: dict[str, Any] = {}
    for nid, node in api.items():
        sn = str(nid)
        ct = node.get("class_type") or ""
        if ct in ("GeminiNode", "PreviewAny", "PreviewImage", "Note", "MarkdownNote"):
            continue
        if sn in DROP_ALWAYS:
            continue
        if sn.startswith(IDEOGRAM_PREFIX):
            if mode in ("boogu", "boogu_only"):
                continue
            out[sn] = node
            continue
        if sn in SEEDVR_NODES and mode not in ("upscale", "pipeline_upscale", "full"):
            continue
        if sn in keep_ids or sn.startswith(IDEOGRAM_PREFIX):
            out[sn] = node
    # second pass: drop links to missing
    alive = set(out.keys())
    for nid, node in out.items():
        ins = node.get("inputs") or {}
        cleaned = {}
        for k, v in ins.items():
            if isinstance(v, list) and len(v) >= 2 and str(v[0]) not in alive:
                continue
            cleaned[k] = v
        node["inputs"] = cleaned
    return out


def build_api(
    *,
    caption: str,
    mode: str = "pipeline",
    seed: int | None = None,
    width: int = 768,
    height: int = 1152,
    boogu_steps: int | None = None,
    krea_denoise: float | None = None,
    filename_prefix: str = "BooguKreaIdeo",
    server_address: str = DEFAULT_SERVER,
    ui_path: str | Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    ui = _load_ui(ui_path)
    oi = _fetch_object_info(server_address)
    api = expand_ui_workflow_to_api(ui, object_info=oi)
    api = _prune_api(api, mode)
    seed_i = int(seed if seed is not None else random.randint(1, 2**31 - 1))
    caption = (caption or "").strip()
    if not caption:
        raise ValueError("caption/prompt required")

    # Boogu
    _set(api, "6", "text", caption)
    _set(api, "3", "width", int(width))
    _set(api, "3", "height", int(height))
    _set(api, "9", "seed", seed_i)
    if boogu_steps is not None:
        _set(api, "9", "steps", int(boogu_steps))
    _set(api, "11", "filename_prefix", f"{filename_prefix}_boogu")

    # Ideogram caption + noise seed
    if "907:186" in api:
        _set(api, "907:186", "text", caption)
    if "907:184" in api:
        _set(api, "907:184", "noise_seed", seed_i + 1)
    # size for ideogram primitives (pack 960x1440)
    if "907:188" in api:
        _set(api, "907:188", "value", int(width))
    if "907:189" in api:
        _set(api, "907:189", "value", int(height))
    _set(api, "915", "filename_prefix", f"{filename_prefix}_ideogram")

    # Krea2 refine
    if "927" in api:
        _set(api, "927", "text", caption)
    if "922" in api:
        _set(api, "922", "seed", seed_i + 2)
        if krea_denoise is not None:
            _set(api, "922", "denoise", float(krea_denoise))
    _set(api, "926", "filename_prefix", f"{filename_prefix}_krea2")

    if "909" in api:
        _set(api, "909", "seed", seed_i + 3)
    _set(api, "912", "filename_prefix", f"{filename_prefix}_seedvr2")

    meta = {
        "tool": "generate_boogu_typo",
        "mode": mode,
        "seed": seed_i,
        "width": width,
        "height": height,
        "caption_preview": caption[:240],
        "ui": str(ui_path or HUMAN_UI),
        "api_nodes": len(api),
        "pipeline": "Boogu → Ideogram4 refine → Krea2 refine"
        + (" → SeedVR2" if mode in ("upscale", "full", "pipeline_upscale") else ""),
    }
    return api, meta


def generate_boogu_typo(
    *,
    caption: str,
    output_path: str,
    mode: str = "pipeline",
    seed: int | None = None,
    width: int = 768,
    height: int = 1152,
    boogu_steps: int | None = None,
    krea_denoise: float | None = None,
    filename_prefix: str = "BooguKreaIdeo",
    prefer_save: str = "krea2",
    timeout_sec: float = 900,
    server_address: str = DEFAULT_SERVER,
    ui_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    prefer_save: which SaveImage to download first
      boogu | ideogram | krea2 | seedvr2 | any
    """
    try:
        api, meta = build_api(
            caption=caption,
            mode=mode,
            seed=seed,
            width=width,
            height=height,
            boogu_steps=boogu_steps,
            krea_denoise=krea_denoise,
            filename_prefix=filename_prefix,
            server_address=server_address,
            ui_path=ui_path,
        )
    except Exception as e:
        return fail_result(error="BUILD_FAILED", message=str(e))

    try:
        prompt_id = queue_prompt(server_address, api)
    except Exception as e:
        return fail_result(error="QUEUE_FAILED", message=str(e))

    try:
        history = wait_for_history(server_address, prompt_id, timeout_sec=timeout_sec)
    except TimeoutError as e:
        return fail_result(error="COMFY_TIMEOUT", message=str(e), prompt_id=prompt_id)
    except Exception as e:
        return fail_result(error="EXEC_FAILED", message=str(e), prompt_id=prompt_id)

    # Prefer stage save
    prefer_map = {
        "boogu": "11",
        "ideogram": "915",
        "krea2": "926",
        "seedvr2": "912",
    }
    outputs = history.get("outputs") or {}
    filename = subfolder = ftype = None
    pick_id = prefer_map.get((prefer_save or "krea2").lower())
    order = []
    if pick_id:
        order.append(pick_id)
    order.extend(["926", "915", "11", "912"])
    for nid in order:
        if nid in outputs:
            imgs = (outputs[nid].get("images") or [])
            if imgs:
                filename = imgs[0].get("filename")
                subfolder = imgs[0].get("subfolder") or ""
                ftype = imgs[0].get("type") or "output"
                meta["save_node"] = nid
                break
    if not filename:
        try:
            filename, subfolder, ftype = extract_first_image(history)
        except Exception as e:
            return fail_result(
                error="NO_IMAGE",
                message=str(e),
                prompt_id=prompt_id,
                history_keys=list(outputs.keys()),
            )

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    try:
        download_image(server_address, filename, subfolder, ftype, output_path)
    except Exception as e:
        return fail_result(error="DOWNLOAD_FAILED", message=str(e), prompt_id=prompt_id)

    meta.update(
        {
            "comfy_prompt_id": prompt_id,
            "output_path": os.path.abspath(output_path),
            "created_at": utc_now_iso(),
            "role": "typography_design_pipeline",
        }
    )
    meta_path = os.path.splitext(output_path)[0] + ".meta.json"
    write_meta(meta_path, meta)
    return ok_result(meta_path=meta_path, **meta)
