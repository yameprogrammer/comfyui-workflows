"""Krea Moodboard search/apply → optional Krea2 T2I."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from lib.comfy_client import (
    DEFAULT_SERVER,
    ensure_parent_dir,
    fail_result,
    ok_result,
    queue_prompt,
    utc_now_iso,
    wait_for_history,
    write_meta,
)
from lib.comfy_engine_session import ensure_engine
from lib.workflow_api_runner import run_workflow_api

FAMILY = "krea2_still"


def build_moodboard_search_prompt(
    query: str,
    *,
    seed: int = 0,
    top_k: int = 5,
    strength: str = "normal",
    random_mode: str = "balanced",
) -> dict[str, Any]:
    # KreaMoodboardSearch → 5 strings; wire Apply to consume them
    return {
        "1": {
            "class_type": "KreaMoodboardSearch",
            "inputs": {
                "query": query,
                "top_k": int(top_k),
                "min_score": 1,
                "random_from_top_k": 0,
                "seed": int(seed),
                "strength": strength,
                "random_mode": random_mode,
            },
        },
        "2": {
            "class_type": "KreaMoodboardApply",
            "inputs": {
                "prompt": "",  # filled via port
                "negative_prompt": "",
                "moodboard_positive": ["1", 0],
                "moodboard_negative": ["1", 1],
                "metadata_json": ["1", 2],
                "strength": strength,
                "style_only": False,
                "separator": "newline",
            },
        },
        "3": {
            "class_type": "SaveText",
            "inputs": {
                "text": ["2", 0],
                "filename_prefix": "moodboard_prompt",
                "format": "txt",
            },
        },
        "4": {
            "class_type": "SaveText",
            "inputs": {
                "text": ["1", 0],
                "filename_prefix": "moodboard_style",
                "format": "txt",
            },
        },
    }


def _strings_from_node(outs: dict, nid: str) -> list[str]:
    node = outs.get(nid) or {}
    found: list[str] = []
    for key in ("text", "string", "strings", "result"):
        val = node.get(key)
        if isinstance(val, list):
            for x in val:
                if isinstance(x, str) and x.strip():
                    found.append(x.strip())
        elif isinstance(val, str) and val.strip():
            found.append(val.strip())
    # any other list of strings
    if not found:
        for v in node.values():
            if isinstance(v, list):
                for x in v:
                    if isinstance(x, str) and len(x.strip()) > 2:
                        found.append(x.strip())
    return found


def moodboard_expand(
    query: str,
    *,
    user_prompt: str = "",
    seed: int | None = None,
    strength: str = "normal",
    server_address: str = DEFAULT_SERVER,
    timeout_sec: float = 120,
) -> dict[str, Any]:
    seed_i = int(seed if seed is not None else random.randint(0, 2**31 - 1))
    api = build_moodboard_search_prompt(query, seed=seed_i, strength=strength)
    # inject user prompt into Apply
    api["2"]["inputs"]["prompt"] = user_prompt or ""
    try:
        ensure_engine("krea_moodboard", server_address, caller="krea2_moodboard")
        pid = queue_prompt(server_address, api)
        hist = wait_for_history(server_address, pid, timeout_sec=timeout_sec)
    except Exception as e:
        return fail_result(error="MOODBOARD_FAIL", message=str(e))

    outs = hist.get("outputs") or {}
    # SaveText nodes materialize STRING outputs (Apply=node3, style block=node4)
    applied = _strings_from_node(outs, "3") or _strings_from_node(outs, "2")
    style_only = _strings_from_node(outs, "4") or _strings_from_node(outs, "1")
    final_prompt = applied[0] if applied else ""
    if not final_prompt and style_only:
        final_prompt = (
            f"{user_prompt}\n{style_only[0]}" if user_prompt else style_only[0]
        )
    if not final_prompt:
        return fail_result(
            error="NO_MOODBOARD_TEXT",
            message=f"no strings in outputs {list(outs.keys())}",
            history_outputs=outs,
            prompt_id=pid,
        )
    # Style block is usually the second half of applied prompt after first blank line
    style_block = style_only[0] if style_only else ""
    if not style_block and "\n\n" in final_prompt:
        style_block = final_prompt.split("\n\n", 1)[-1]
    return ok_result(
        prompt=final_prompt,
        negative="",
        metadata_json="{}",
        style_block=style_block,
        query=query,
        seed=seed_i,
        prompt_id=pid,
    )


def moodboard_then_krea(
    query: str,
    *,
    user_prompt: str,
    output_path: str,
    seed: int | None = None,
    strength: str = "normal",
    width: int = 1024,
    height: int = 1024,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: float = 600,
) -> dict[str, Any]:
    mb = moodboard_expand(
        query,
        user_prompt=user_prompt,
        seed=seed,
        strength=strength,
        server_address=server_address,
        timeout_sec=min(180.0, timeout_sec),
    )
    if not mb.get("ok"):
        return mb
    prompt = str(mb.get("prompt") or "").strip()
    ensure_parent_dir(output_path)
    eng = ensure_engine(FAMILY, server_address, caller="krea2_moodboard_t2i")
    if not eng.get("ok"):
        return fail_result(error="ENGINE", message=eng.get("message"), prompt=prompt)

    r = run_workflow_api(
        "krea2_t2i_v10",
        ports={
            "positive": prompt,
            "width": width,
            "height": height,
            "filename_prefix": "krea2_moodboard",
        },
        output_path=output_path,
        seed=seed if seed is not None else mb.get("seed"),
        server_address=server_address,
        timeout_sec=timeout_sec,
    )
    if not r.get("ok"):
        r = dict(r)
        r["prompt"] = prompt
        r["moodboard"] = mb
        return r
    meta = {
        "tool": "generate_krea2_moodboard",
        "query": query,
        "user_prompt": user_prompt,
        "prompt_used": prompt,
        "negative": mb.get("negative"),
        "style_block": mb.get("style_block"),
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
        prompt=prompt,
        style_block=mb.get("style_block"),
        meta_path=mp,
    )
