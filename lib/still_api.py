"""Shared Comfy API-graph runner for still T2I/I2I/inpaint CLIs."""

from __future__ import annotations

import os
import random
import shutil
from typing import Any

from lib.comfy_client import (
    DEFAULT_SERVER,
    download_image,
    extract_first_image,
    fail_result,
    get_comfy_input_dir,
    ok_result,
    queue_prompt,
    resolve_meta_out,
    utc_now_iso,
    wait_for_history,
    write_meta,
)
from lib.comfy_engine_session import ensure_engine
from lib.output_policy import die_if_toolbox


def stage_input_image(local_path: str, *, prefix: str = "still") -> str:
    if not local_path or not os.path.isfile(local_path):
        raise FileNotFoundError(f"input image missing: {local_path}")
    input_dir = get_comfy_input_dir()
    os.makedirs(input_dir, exist_ok=True)
    dest_name = f"{prefix}_{os.path.basename(local_path)}"
    dest = os.path.join(input_dir, dest_name)
    if not os.path.isfile(dest) or os.path.getsize(dest) != os.path.getsize(local_path):
        shutil.copy2(local_path, dest)
    return dest_name


def run_still_api(
    api: dict[str, Any],
    *,
    output_path: str,
    family: str,
    caller: str,
    seed: int,
    timeout_sec: float = 900,
    server_address: str = DEFAULT_SERVER,
    meta: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    output_path = die_if_toolbox(output_path)
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    if dry_run:
        return ok_result(
            dry_run=True,
            output_path=os.path.abspath(output_path),
            seed=seed,
            family=family,
            api_nodes=list(api.keys()),
            meta=meta or {},
        )

    eng = ensure_engine(family, server_address, caller=caller)
    if not eng.get("ok"):
        return fail_result(
            error=eng.get("error") or "ENGINE_SESSION",
            message=eng.get("message") or "comfy engine free/gate failed",
            engine_session=eng,
        )

    try:
        prompt_id = queue_prompt(server_address, api)
        print(f"Queued prompt_id={prompt_id}")
    except Exception as e:
        return fail_result(error="QUEUE_FAILED", message=str(e), seed=seed)

    try:
        history = wait_for_history(server_address, prompt_id, timeout_sec=timeout_sec)
    except Exception as e:
        return fail_result(
            error="HISTORY_FAILED", message=str(e), seed=seed, prompt_id=prompt_id
        )

    status = history.get("status") or {}
    if status.get("status_str") == "error" or status.get("completed") is False:
        msgs = status.get("messages") or []
        return fail_result(
            error="EXECUTION_ERROR",
            message=str(msgs)[:800],
            seed=seed,
            prompt_id=prompt_id,
        )

    try:
        filename, subfolder, media_type = extract_first_image(history)
    except Exception as e:
        outs = history.get("outputs") or {}
        keys = {nid: list(v.keys()) for nid, v in outs.items() if isinstance(v, dict)}
        return fail_result(
            error="COMFY_NO_IMAGE",
            message=f"{e}; outputs={keys}",
            seed=seed,
            prompt_id=prompt_id,
        )

    print(f"Downloading {filename}")
    try:
        download_image(server_address, filename, subfolder, media_type, output_path)
    except Exception as e:
        return fail_result(
            error="DOWNLOAD_FAILED", message=str(e), seed=seed, prompt_id=prompt_id
        )

    payload = {
        "output_path": os.path.abspath(output_path),
        "seed": seed,
        "comfy_prompt_id": prompt_id,
        "family": family,
        "caller": caller,
        "created_at": utc_now_iso(),
    }
    if meta:
        payload.update(meta)
    meta_path = resolve_meta_out(output_path, None)
    if meta_path:
        write_meta(meta_path, payload)
        print(f"Meta saved: {meta_path}")
    print(f"OK {output_path}")
    return ok_result(
        output_path=os.path.abspath(output_path),
        seed=seed,
        prompt_id=prompt_id,
        meta_path=meta_path,
        meta=payload,
        engine_session=eng,
    )


def new_seed(explicit: int | None) -> int:
    if explicit is not None:
        return int(explicit)
    return random.randint(1, 2**31 - 1)
