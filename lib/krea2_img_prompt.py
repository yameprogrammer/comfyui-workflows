"""Image → caption (Florence2) then optional Krea2 T2I."""

from __future__ import annotations

import os
import random
import shutil
import time
from pathlib import Path
from typing import Any

from lib.comfy_client import (
    DEFAULT_SERVER,
    ensure_parent_dir,
    fail_result,
    get_comfy_input_dir,
    ok_result,
    queue_prompt,
    utc_now_iso,
    wait_for_history,
    write_meta,
)
from lib.comfy_engine_session import ensure_engine
from lib.workflow_api_runner import run_workflow_api

FAMILY = "krea2_still"


def _stage(path: str, server: str, prefix: str = "imgprompt") -> str:
    src = Path(path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(str(src))
    dest_dir = Path(get_comfy_input_dir(server))
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = f"{prefix}_{src.stem[:40]}_{int(time.time() * 1000) % 10_000_000}{src.suffix.lower() or '.png'}"
    shutil.copy2(src, dest_dir / name)
    return name


def build_florence_caption_prompt(
    image_name: str,
    *,
    task: str = "detailed_caption",
    seed: int = 1,
    model: str = "microsoft/Florence-2-base",
) -> dict[str, Any]:
    return {
        "1": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "2": {
            "class_type": "DownloadAndLoadFlorence2Model",
            "inputs": {"model": model, "precision": "fp16"},
        },
        "3": {
            "class_type": "Florence2Run",
            "inputs": {
                "image": ["1", 0],
                "florence2_model": ["2", 0],
                "text_input": "",
                "task": task,
                "fill_mask": False,
                "keep_model_loaded": False,
                "max_new_tokens": 256,
                "num_beams": 3,
                "do_sample": False,
                "seed": int(seed),
            },
        },
        # Force Florence execution + persist caption text for debugging
        "4": {
            "class_type": "SaveText",
            "inputs": {
                "text": ["3", 2],
                "filename_prefix": "florence_caption",
                "format": "txt",
            },
        },
    }


def _extract_florence_text(history: dict[str, Any]) -> str | None:
    outs = history.get("outputs") or {}
    # Florence2Run is node 3; string is often under "text" or "string" or list
    for nid in ("3", "4"):
        node_out = outs.get(nid) or outs.get(int(nid)) if False else outs.get(nid)
        if not isinstance(node_out, dict):
            continue
        for key in ("text", "string", "strings", "caption"):
            val = node_out.get(key)
            if isinstance(val, list) and val:
                s = val[0]
                if isinstance(s, str) and s.strip():
                    return s.strip()
            if isinstance(val, str) and val.strip():
                return val.strip()
        # nested
        for v in node_out.values():
            if isinstance(v, list) and v and isinstance(v[0], str) and len(v[0]) > 8:
                return v[0].strip()
            if isinstance(v, str) and len(v) > 8:
                return v.strip()
    return None


def caption_image(
    image_path: str,
    *,
    task: str = "detailed_caption",
    seed: int | None = None,
    florence_model: str = "microsoft/Florence-2-base",
    server_address: str = DEFAULT_SERVER,
    timeout_sec: float = 300,
    free_policy: str | None = None,
) -> dict[str, Any]:
    seed_i = int(seed if seed is not None else random.randint(1, 2**31 - 1))
    server = server_address
    eng = ensure_engine("florence2", server, policy=free_policy, caller="krea2_img_prompt")
    if not eng.get("ok"):
        # Florence is light; allow other family
        pass
    try:
        name = _stage(image_path, server)
    except Exception as e:
        return fail_result(error="STAGE", message=str(e))

    api = build_florence_caption_prompt(
        name, task=task, seed=seed_i, model=florence_model
    )
    try:
        pid = queue_prompt(server, api)
        hist = wait_for_history(server, pid, timeout_sec=timeout_sec)
    except Exception as e:
        return fail_result(error="CAPTION_FAIL", message=str(e))

    text = _extract_florence_text(hist)
    if not text:
        # fallback: try all string-looking outputs
        return fail_result(
            error="NO_CAPTION",
            message=f"Florence produced no text; outputs={list((hist.get('outputs') or {}).keys())}",
            prompt_id=pid,
            history_outputs=hist.get("outputs"),
        )
    return ok_result(
        caption=text,
        prompt_id=pid,
        seed=seed_i,
        task=task,
        florence_model=florence_model,
    )


def caption_then_krea(
    image_path: str,
    *,
    output_path: str,
    extra_prompt: str = "",
    task: str = "detailed_caption",
    seed: int | None = None,
    width: int = 1024,
    height: int = 576,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: float = 600,
) -> dict[str, Any]:
    cap = caption_image(
        image_path,
        task=task,
        seed=seed,
        server_address=server_address,
        timeout_sec=min(300.0, timeout_sec),
    )
    if not cap.get("ok"):
        return cap
    caption = str(cap.get("caption") or "").strip()
    prompt = caption
    if extra_prompt.strip():
        prompt = f"{caption}, {extra_prompt.strip()}"

    eng = ensure_engine(FAMILY, server_address, caller="krea2_img_prompt_t2i")
    if not eng.get("ok"):
        return fail_result(error="ENGINE", message=eng.get("message"), caption=caption)

    ensure_parent_dir(output_path)
    r = run_workflow_api(
        "krea2_t2i_v10",
        ports={
            "positive": prompt,
            "width": width,
            "height": height,
            "filename_prefix": "krea2_img_prompt",
        },
        output_path=output_path,
        seed=seed if seed is not None else cap.get("seed"),
        server_address=server_address,
        timeout_sec=timeout_sec,
    )
    if not r.get("ok"):
        r = dict(r)
        r["caption"] = caption
        r["prompt_used"] = prompt
        return r

    meta = {
        "tool": "generate_krea2_img_prompt",
        "caption": caption,
        "prompt_used": prompt,
        "extra_prompt": extra_prompt,
        "task": task,
        "output_path": r.get("output_path"),
        "seed": r.get("seed"),
        "created_at": utc_now_iso(),
    }
    mp = str(Path(output_path).with_suffix(Path(output_path).suffix + ".meta.json"))
    try:
        write_meta(mp, meta)
    except Exception:
        mp = None
    return ok_result(
        output_path=r.get("output_path"),
        seed=r.get("seed"),
        prompt_id=r.get("prompt_id"),
        caption=caption,
        prompt_used=prompt,
        meta_path=mp,
    )
