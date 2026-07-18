#!/usr/bin/env python3
"""
Image-to-Video via ComfyUI (multi-backend entry).

Default backend: wan22 (Wan2.2 I2V A14B GGUF + lightx2v).
Presets / backends SSOT: video_backends.json (see docs/video_delivery_and_backends.md).

Delivery policy:
  - Generate at work resolution with final aspect ratio (default work_16x9_540).
  - Upscale to at least 1080p in a later pipeline stage — do not treat work-res as final.
"""

from __future__ import annotations
import _bootstrap  # noqa: F401  # repo root + scripts on path

import argparse
import json
import os
import random
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from lib.comfy_client import (
    COMFYUI_INPUT_DIR,
    DEFAULT_SERVER,
    ensure_parent_dir,
    fail_result,
    ok_result,
    resolve_meta_out,
    utc_now_iso,
    write_meta,
)
from lib.comfy_engine_session import ensure_engine, family_for_i2v_backend
from lib.comfy_ui_convert import convert_ui_to_api, fetch_object_info
from lib.prompt_assembly import load_text
from lib.video_backends import (
    BackendNotReady,
    list_backend_ids,
    list_format_ids,
    list_preset_ids,
    load_video_backends,
    resolve_i2v_job,
)
from lib.workflow_paths import resolve_workflow

DEFAULT_NEGATIVE = (
    "static, still image, blurry, low quality, worst quality, deformed, "
    "bad anatomy, watermark, text, logo, jitter, flicker"
)

# Comfy output folder for VHS saves
COMFY_OUTPUT_DIR = r"F:\ComfyUI_windows_portable\ComfyUI\output"
COMFY_TEMP_DIR = r"F:\ComfyUI_windows_portable\ComfyUI\temp"


def _find_nodes(api_prompt: dict, class_type: str) -> list[str]:
    return [nid for nid, n in api_prompt.items() if n.get("class_type") == class_type]


def _snap_dim(n: int, multiple: int = 16) -> int:
    """Round dimension to nearest multiple (min = multiple). Wan latent needs %16==0."""
    if n < multiple:
        return multiple
    return max(multiple, int(round(n / multiple) * multiple))


def _snap_frames(n: int) -> int:
    """Wan / many video DiTs prefer 4n+1 frame counts (min 9)."""
    n = max(9, int(n))
    # nearest 4k+1
    base = ((n - 1) // 4) * 4 + 1
    alt = base + 4
    if abs(alt - n) < abs(base - n):
        return alt
    return base


def _link_node_id(val) -> str | None:
    """Comfy link input is [node_id, slot] or bare value."""
    if isinstance(val, list) and len(val) >= 1:
        return str(val[0])
    return None


def resolve_wan_attention(explicit: str | None = None) -> str:
    """Default sageattn (same policy as InfiniteTalk). Fallback: AGENT_WAN_ATTENTION=sdpa."""
    if explicit is not None and str(explicit).strip():
        return str(explicit).strip()
    return (os.environ.get("AGENT_WAN_ATTENTION") or "sageattn").strip() or "sageattn"


# P1: speed profiles (knobs only; aspect still from --format/--preset)
# QA 2026-07-13: TeaCache/MagCache → temporal grain/"자글자글" unusable on deliver path.
# Cache remains opt-in via --cache for experiments only (not profile defaults).
I2V_SPEED_PROFILES: dict[str, dict] = {
    "preview": {
        "steps": 4,
        "cache": "none",
        "teacache_thresh": 0.15,
        "magcache_thresh": 0.01,
        "magcache_k": 2,
        # Bench 2026-07-13: lower swap = faster; 0 OK on 368x640 smoke (24GB class)
        "block_swap": 8,
        "max_long_edge": 480,
        "notes": "fast scout: fewer steps + smaller long_edge; low block_swap",
    },
    "deliver": {
        "steps": 6,
        "cache": "none",
        "teacache_thresh": 0.15,
        "magcache_thresh": 0.01,
        "magcache_k": 2,
        # Starting point only — raise on OOM/long clips, lower if VRAM free. See docs §4.1
        "block_swap": 10,
        "max_long_edge": None,
        "notes": "production I2V: sage + lightx2v; block_swap start=10 (tune per job)",
    },
    "quality": {
        "steps": 8,
        "cache": "none",
        "teacache_thresh": 0.15,
        "magcache_thresh": 0.01,
        "magcache_k": 2,
        "block_swap": 10,
        "max_long_edge": None,
        "notes": "hero still motion; more steps; block_swap=10",
    },
}


def resolve_i2v_speed_profile(name: str | None) -> dict:
    key = (name or "deliver").strip().lower() or "deliver"
    if key not in I2V_SPEED_PROFILES:
        raise ValueError(
            f"unknown I2V profile {name!r}; known: {', '.join(I2V_SPEED_PROFILES)}"
        )
    return dict(I2V_SPEED_PROFILES[key], name=key)


def _apply_max_long_edge(width: int, height: int, max_long_edge: int | None) -> tuple[int, int]:
    if not max_long_edge or max_long_edge <= 0:
        return width, height
    le = max(width, height)
    if le <= max_long_edge:
        return width, height
    scale = float(max_long_edge) / float(le)
    return _snap_dim(int(round(width * scale)), 16), _snap_dim(int(round(height * scale)), 16)


def _apply_wan22_block_swap(api_prompt: dict, blocks_to_swap: int) -> dict:
    blocks = max(0, int(blocks_to_swap))
    ids = _find_nodes(api_prompt, "WanVideoBlockSwap")
    for nid in ids:
        api_prompt[nid]["inputs"]["blocks_to_swap"] = blocks
    return {"blocks_to_swap": blocks, "node_ids": ids}


def _apply_wan22_cache(
    api_prompt: dict,
    *,
    cache: str,
    teacache_thresh: float = 0.2,
    magcache_thresh: float = 0.02,
    magcache_k: int = 4,
) -> dict:
    """Attach WanVideoTeaCache or WanVideoMagCache to all WanVideoSampler cache_args."""
    mode = (cache or "none").strip().lower()
    samplers = _find_nodes(api_prompt, "WanVideoSampler")
    if mode in ("", "none", "off", "false", "0"):
        for nid in samplers:
            api_prompt[nid]["inputs"].pop("cache_args", None)
        return {"cache": "none", "samplers": samplers}

    node_id = "agent_wan_cache"
    if mode in ("teacache", "tea"):
        api_prompt[node_id] = {
            "class_type": "WanVideoTeaCache",
            "inputs": {
                "rel_l1_thresh": float(teacache_thresh),
                "start_step": 1,
                "end_step": -1,
                "cache_device": "offload_device",
                "use_coefficients": True,
                "mode": "e",
            },
        }
        kind = "teacache"
        thresh = float(teacache_thresh)
    elif mode in ("magcache", "mag"):
        api_prompt[node_id] = {
            "class_type": "WanVideoMagCache",
            "inputs": {
                "magcache_thresh": float(magcache_thresh),
                "magcache_K": int(magcache_k),
                "start_step": 1,
                "end_step": -1,
                "cache_device": "offload_device",
            },
        }
        kind = "magcache"
        thresh = float(magcache_thresh)
    else:
        raise ValueError(f"unknown cache mode {cache!r}; use teacache|magcache|none")

    for nid in samplers:
        api_prompt[nid]["inputs"]["cache_args"] = [node_id, 0]

    return {
        "cache": kind,
        "node_id": node_id,
        "thresh": thresh,
        "magcache_k": int(magcache_k) if kind == "magcache" else None,
        "samplers": samplers,
    }


def _apply_wan22_steps_and_boundary(api_prompt: dict, steps: int) -> dict:
    """Wire total steps + dual high/low boundary (steps//2) into INTConstants / samplers.

    WF pattern: both WanVideoSampler share steps INTConstant; boundary INT feeds
    high end_step and low start_step.
    """
    steps_n = max(1, int(steps))
    boundary = max(1, steps_n // 2)
    steps_const: set[str] = set()
    boundary_const: set[str] = set()

    for nid in _find_nodes(api_prompt, "WanVideoSampler"):
        inp = api_prompt[nid]["inputs"]
        sid = _link_node_id(inp.get("steps"))
        if sid:
            steps_const.add(sid)
        else:
            inp["steps"] = steps_n
        for key in ("start_step", "end_step"):
            raw = inp.get(key)
            bid = _link_node_id(raw)
            if bid:
                boundary_const.add(bid)

    for sid in steps_const:
        node = api_prompt.get(sid)
        if node and node.get("class_type") == "INTConstant":
            node["inputs"]["value"] = steps_n

    for bid in boundary_const:
        node = api_prompt.get(bid)
        if node and node.get("class_type") == "INTConstant":
            node["inputs"]["value"] = boundary

    # Legacy: older graphs used a lone INTConstant(30) as step count
    for nid in _find_nodes(api_prompt, "INTConstant"):
        if nid in steps_const or nid in boundary_const:
            continue
        val = api_prompt[nid]["inputs"].get("value")
        if val == 30:
            api_prompt[nid]["inputs"]["value"] = steps_n

    return {
        "steps": steps_n,
        "boundary": boundary,
        "steps_const_ids": sorted(steps_const),
        "boundary_const_ids": sorted(boundary_const),
    }


def _is_wan22_family(backend_id: str, wf_path: str = "") -> bool:
    b = (backend_id or "").strip().lower()
    if b in ("wan22", "wan22_flf", "wan22_flf2v", "flf2v") or b.startswith("wan22"):
        return True
    name = os.path.basename(wf_path or "").lower()
    return "wan" in name


def _pick_load_image_nodes(api_prompt: dict) -> tuple[str | None, str | None]:
    """Return (start_load_id, end_load_id) for FLF-aware LoadImage assignment."""
    loaders = _find_nodes(api_prompt, "LoadImage")
    if not loaders:
        return None, None
    start_id = None
    end_id = None
    for nid in loaders:
        title = str((api_prompt[nid].get("_meta") or {}).get("title") or "").lower()
        if "end" in title and end_id is None:
            end_id = nid
        elif start_id is None:
            start_id = nid
    if start_id is None:
        start_id = loaders[0]
    if end_id is None and len(loaders) >= 2:
        # Prefer fixed FLF preset ids, else second loader
        if "167" in api_prompt and api_prompt["167"].get("class_type") == "LoadImage":
            end_id = "167"
        else:
            end_id = next((n for n in loaders if n != start_id), None)
    return start_id, end_id


def generate_i2v(
    input_image_path: str,
    prompt_text: str,
    negative_text: str = DEFAULT_NEGATIVE,
    output_filename: str | None = None,
    width: int | None = None,
    height: int | None = None,
    num_frames: int = 49,
    seed: int | None = None,
    steps: int | None = None,
    cfg: float = 1.0,
    frame_rate: int = 16,
    backend: str | None = None,
    format_id: str | None = None,
    preset: str | None = None,
    workflow_path: str | None = None,
    meta_out: str | None = None,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: int = 1800,
    attention_mode: str | None = None,
    dry_run: bool = False,
    profile: str | None = "deliver",
    ltx_profile: str | None = None,
    cache: str | None = None,
    teacache_thresh: float | None = None,
    magcache_thresh: float | None = None,
    magcache_k: int | None = None,
    block_swap: int | None = None,
    apply_profile_long_edge: bool = True,
    end_image_path: str | None = None,
):
    if not os.path.exists(input_image_path):
        print(f"Error: input image not found: {input_image_path}")
        return fail_result(error="SOURCE_MISSING", message=input_image_path)

    end_image_path = (end_image_path or "").strip() or None
    if end_image_path and not os.path.isfile(end_image_path):
        return fail_result(
            error="END_IMAGE_MISSING",
            message=f"end/last frame not found: {end_image_path}",
        )

    # FLF: quality default = LTX AIO flf (A/B 2026-07-17 preferred over Wan GGUF)
    _be_hint = (backend or "").strip().lower()
    if end_image_path and not workflow_path:
        if not _be_hint or _be_hint in ("flf2v", "wan22_flf2v", ""):
            backend = "ltx23_aio_flf"
            print(f"FLF mode: end_image={end_image_path} → backend=ltx23_aio_flf (quality default)")
        elif _be_hint in ("wan22",):
            # bare wan22 + last frame → still Wan FLF graph
            backend = "wan22_flf"
            print(f"FLF mode: end_image={end_image_path} → backend=wan22_flf (explicit wan)")

    # Early LTX AIO path (before resolve_i2v_job — no Wan workflow file required)
    _be_early = (backend or "").strip().lower()
    if not _be_early:
        try:
            from lib.video_backends import load_video_backends

            _be_early = str(
                load_video_backends().get("default_backend") or ""
            ).strip().lower()
        except Exception:
            _be_early = ""
    if _be_early in (
        "ltx23",
        "ltx23_aio",
        "ltx23_aio_i2v",
        "ltx23_ia2v",
        "ltx23_aio_flf",
        "ltx23_aio_flf_audio",
        "flf2v",
    ) or _be_early.startswith("ltx23_aio"):
        from generate_s2v import generate_s2v
        from lib.video_backends import resolve_i2v_job as _resolve_sizes

        # Size: LTX quality profile (hero→720p-class) unless explicit WxH
        try:
            from lib.ltx_quality_profiles import apply_ltx_quality_profile

            _qp = apply_ltx_quality_profile(
                profile_name=ltx_profile,
                width=width,
                height=height,
                format_id=format_id,
                fps=float(frame_rate or 24),
                num_frames=num_frames,
                has_audio=False,
                user_explicit_size=bool(width and height),
            )
            _pid = str(_qp.get("profile_id") or "work")
            _tedge = int(_qp.get("longer_edge") or 1280)
            if not (width and height):
                width = int(_qp["width"])
                height = int(_qp["height"])
            elif _pid in ("hero", "work") and max(int(width), int(height)) + 32 < _tedge:
                # lift legacy 540 / below-profile sizes to tier default
                if _pid == "hero" or max(int(width), int(height)) <= 960:
                    width = int(_qp["width"])
                    height = int(_qp["height"])
            for _w in _qp.get("warnings") or []:
                print(f"[ltx-profile WARN] {_w}")
        except Exception:
            try:
                job = _resolve_sizes(
                    backend="wan22",  # size/preset only; LTX does not use Wan graph
                    format_id=format_id,
                    preset=preset,
                    width=width,
                    height=height,
                )
                width = int(job["width"])
                height = int(job["height"])
            except Exception:
                width = int(width or 1280)
                height = int(height or 720)

        if _be_early in ("ltx23", "ltx23_aio", "ltx23_aio_i2v", ""):
            s2v_backend = "ltx23_aio_i2v"
        elif _be_early in ("flf2v",):
            s2v_backend = "ltx23_aio_flf"
        else:
            s2v_backend = _be_early
        if end_image_path and s2v_backend in ("ltx23_aio_i2v", "ltx23_aio"):
            s2v_backend = "ltx23_aio_flf"
        print(
            f"I2V → LTX AIO real WF backend={s2v_backend} "
            f"{width}x{height} ltx_profile={ltx_profile or 'work'} "
            f"(ltx23AllInOneWorkflowForRTX_v44)"
            + (f" last={end_image_path}" if end_image_path else "")
        )
        if dry_run:
            return ok_result(
                dry_run=True,
                backend=s2v_backend,
                width=width,
                height=height,
                ltx_profile=ltx_profile or "work",
                message="ltx_aio dry-run",
            )
        return generate_s2v(
            input_image_path=input_image_path,
            audio_path=None,
            last_image_path=end_image_path,
            output_filename=output_filename
            or os.path.join(r"F:\generated_videos", "output_i2v_ltx.mp4"),
            prompt=prompt_text,
            negative=negative_text,
            width=width,
            height=height,
            num_frames=num_frames,
            fps=float(frame_rate or 24),
            seed=seed,
            cfg=cfg,
            backend=s2v_backend,
            server_address=server_address,
            timeout_sec=timeout_sec,
            meta_out=meta_out,
            ltx_profile=ltx_profile,
            format_id=format_id,
        )

    try:
        speed_prof = resolve_i2v_speed_profile(profile)
    except ValueError as e:
        return fail_result(error="BAD_PROFILE", message=str(e))

    # Profile fills defaults; explicit args win when not None
    if steps is None:
        steps = int(speed_prof["steps"])
    cache_mode = (cache if cache is not None else speed_prof["cache"]) or "none"
    tc_thresh = (
        float(teacache_thresh)
        if teacache_thresh is not None
        else float(speed_prof["teacache_thresh"])
    )
    mc_thresh = (
        float(magcache_thresh)
        if magcache_thresh is not None
        else float(speed_prof["magcache_thresh"])
    )
    mc_k = int(magcache_k if magcache_k is not None else speed_prof["magcache_k"])
    blocks = int(block_swap if block_swap is not None else speed_prof["block_swap"])

    try:
        job = resolve_i2v_job(
            backend=backend,
            format_id=format_id,
            preset=preset,
            width=width,
            height=height,
            workflow=workflow_path,
        )
    except BackendNotReady as e:
        print(f"Error: backend not ready: {e}")
        return fail_result(error="BACKEND_NOT_READY", message=str(e), backend=e.backend_id)
    except (KeyError, ValueError, FileNotFoundError) as e:
        print(f"Error: I2V config: {e}")
        return fail_result(error="I2V_CONFIG", message=str(e))

    backend_id = job["backend_id"]
    preset_id = job["preset_id"]
    format_id = job.get("format_id")
    aspect = job.get("aspect")
    width = int(job["width"])
    height = int(job["height"])
    wf_path = job.get("workflow_path") or ""

    if apply_profile_long_edge:
        mle = speed_prof.get("max_long_edge")
        ow, oh = width, height
        width, height = _apply_max_long_edge(width, height, mle)
        if (width, height) != (ow, oh):
            print(
                f"[profile {speed_prof['name']}] long_edge cap {mle}: "
                f"{ow}x{oh} -> {width}x{height}"
            )

    eng = ensure_engine(
        family_for_i2v_backend(backend_id),
        server_address,
        caller=f"generate_i2v:{backend_id}",
    )
    if not eng.get("ok"):
        return fail_result(
            error=eng.get("error") or "ENGINE_SESSION",
            message=eng.get("message") or "comfy engine free/gate failed",
            engine_session=eng,
            backend=backend_id,
        )

    # WanVideoSampler fails when latent spatial dims disagree (classic 960x540:
    # 540 % 16 != 0). Snap both axes; also normalize frame count to 4n+1.
    orig_w, orig_h, orig_f = width, height, num_frames
    width = _snap_dim(width, 16)
    height = _snap_dim(height, 16)
    num_frames = _snap_frames(num_frames)
    if (width, height, num_frames) != (orig_w, orig_h, orig_f):
        print(
            f"[WARN] I2V snap for Wan: {orig_w}x{orig_h} f={orig_f} "
            f"-> {width}x{height} f={num_frames} (dims %16, frames 4n+1)"
        )

    if not _is_wan22_family(backend_id, wf_path) and not workflow_path:
        # Only Wan22 family inject path is implemented in this module for now.
        # Explicit --workflow can still force a graph for experiments.
        if job["status"] != "ready":
            return fail_result(
                error="BACKEND_NOT_READY",
                message=f"Backend {backend_id} not implemented in generate_i2v runner",
                backend=backend_id,
            )

    if end_image_path and not _is_wan22_family(backend_id, wf_path):
        return fail_result(
            error="FLF_BACKEND",
            message=f"end/last image requires wan22_flf (got backend={backend_id})",
            backend=backend_id,
        )

    if not os.path.exists(wf_path):
        print(f"Error: workflow not found: {wf_path}")
        return fail_result(error="WORKFLOW_MISSING", message=wf_path)

    if output_filename is None:
        output_filename = os.path.join(r"F:\generated_videos", "output_i2v.mp4")
    ensure_parent_dir(output_filename)

    # Copy start (+ optional end) into Comfy input
    temp_name = "temp_i2v_input.png"
    temp_end_name = "temp_i2v_end.png"
    try:
        os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
        shutil.copy2(input_image_path, os.path.join(COMFYUI_INPUT_DIR, temp_name))
        print(f"Copied start to ComfyUI input: {temp_name}")
        if end_image_path:
            shutil.copy2(end_image_path, os.path.join(COMFYUI_INPUT_DIR, temp_end_name))
            print(f"Copied end to ComfyUI input: {temp_end_name}")
    except Exception as e:
        return fail_result(error="INPUT_COPY_FAILED", message=str(e))

    flf_tag = " FLF" if end_image_path else ""
    print(
        f"I2V{flf_tag} job backend={backend_id} format={format_id or '-'} "
        f"aspect={aspect or '-'} preset={preset_id} "
        f"{width}x{height} workflow={os.path.basename(wf_path)}"
    )
    print(f"Loading I2V workflow: {wf_path}")
    with open(wf_path, "r", encoding="utf-8") as f:
        wf_data = json.load(f)

    # Prefer API-format graph (presets/*.api.json). UI JSON only as legacy fallback.
    is_api_format = (
        isinstance(wf_data, dict)
        and "nodes" not in wf_data
        and any(
            isinstance(v, dict) and "class_type" in v
            for v in wf_data.values()
        )
    )
    if is_api_format:
        api_prompt = wf_data
        print(f"  format=api nodes={len(api_prompt)} (no convert_ui_to_api)")
    else:
        try:
            object_info = fetch_object_info(server_address)
        except Exception as e:
            print(f"[WARN] object_info fetch failed: {e}; conversion may be incomplete")
            object_info = {}
        print("  format=ui → convert_ui_to_api (legacy; prefer presets/*.api.json)")
        api_prompt = convert_ui_to_api(wf_data, object_info, server_address)

    new_seed = seed if seed is not None else random.randint(1, 2**31 - 1)

    wan_attention = resolve_wan_attention(attention_mode)
    wan_step_info: dict = {}
    wan_cache_info: dict = {}
    wan_swap_info: dict = {}
    vhs_prefix = f"agent_i2v_{int(time.time())}"

    # --- wan22 / wan22_flf graph patch (API preset preferred) ---
    if _is_wan22_family(backend_id, wf_path):
        model_high = r"Wan2.2\Wan2.2-I2V-A14B-HighNoise-Q4_K_M.gguf"
        model_low = r"Wan2.2\Wan2.2-I2V-A14B-LowNoise-Q4_K_M.gguf"
        lora_high = r"Wan2.2\Wan_2_2_I2V_A14B_HIGH_lightx2v_4step_lora_260412_rank_64_fp16.safetensors"
        lora_low = r"Wan2.2\Wan_2_2_I2V_A14B_LOW_lightx2v_4step_lora_260412_rank_64_fp16.safetensors"
        loaders = _find_nodes(api_prompt, "WanVideoModelLoader")
        # Never use fp16_fast — needs torch nightly allow_fp16_accumulation
        for lid in loaders:
            li = api_prompt[lid].setdefault("inputs", {})
            li["base_precision"] = "bf16"
            li["quantization"] = "disabled"
            li.pop("compile_args", None)
        if len(loaders) >= 2:
            api_prompt[loaders[0]]["inputs"]["model"] = model_high
            api_prompt[loaders[0]]["inputs"]["attention_mode"] = wan_attention
            api_prompt[loaders[1]]["inputs"]["model"] = model_low
            api_prompt[loaders[1]]["inputs"]["attention_mode"] = wan_attention
        elif len(loaders) == 1:
            api_prompt[loaders[0]]["inputs"]["attention_mode"] = wan_attention
        loras = _find_nodes(api_prompt, "WanVideoLoraSelect")
        for nid in loras:
            cur = str(api_prompt[nid]["inputs"].get("lora", ""))
            if "LOW" in cur.upper() or "low" in cur:
                api_prompt[nid]["inputs"]["lora"] = lora_low
            else:
                api_prompt[nid]["inputs"]["lora"] = lora_high
            api_prompt[nid]["inputs"]["merge_loras"] = False
        for nid in _find_nodes(api_prompt, "WanVideoVAELoader"):
            api_prompt[nid]["inputs"]["model_name"] = "wan_2.1_vae.safetensors"
        for nid in _find_nodes(api_prompt, "LoadWanVideoT5TextEncoder"):
            api_prompt[nid]["inputs"]["model_name"] = "umt5-xxl-enc-bf16.safetensors"

        start_load, end_load = _pick_load_image_nodes(api_prompt)
        if start_load:
            api_prompt[start_load]["inputs"]["image"] = temp_name
        if end_image_path:
            if not end_load:
                return fail_result(
                    error="FLF_GRAPH_NO_END_LOAD",
                    message=(
                        "end/last image set but workflow has no end LoadImage. "
                        "Use preset i2v_wan22_a14b_flf / backend wan22_flf."
                    ),
                    backend=backend_id,
                    workflow=os.path.basename(wf_path),
                )
            api_prompt[end_load]["inputs"]["image"] = temp_end_name
        elif end_load:
            # Non-FLF run on FLF graph: mirror start into end to avoid missing file
            api_prompt[end_load]["inputs"]["image"] = temp_name

        for nid in _find_nodes(api_prompt, "WanVideoTextEncode"):
            api_prompt[nid]["inputs"]["positive_prompt"] = prompt_text
            api_prompt[nid]["inputs"]["negative_prompt"] = negative_text or DEFAULT_NEGATIVE

        for nid in _find_nodes(api_prompt, "ImageResizeKJv2"):
            # Only set absolute size on start resize; end resize may link width/height
            inp = api_prompt[nid]["inputs"]
            if not isinstance(inp.get("width"), list):
                inp["width"] = width
            if not isinstance(inp.get("height"), list):
                inp["height"] = height
        # Force start resize (node 68 when present) to target work size
        if "68" in api_prompt and api_prompt["68"].get("class_type") == "ImageResizeKJv2":
            api_prompt["68"]["inputs"]["width"] = width
            api_prompt["68"]["inputs"]["height"] = height

        for nid in _find_nodes(api_prompt, "WanVideoImageToVideoEncode"):
            inp = api_prompt[nid]["inputs"]
            # Prefer linked dims from resize when present; else absolute
            if not isinstance(inp.get("width"), list):
                inp["width"] = width
            if not isinstance(inp.get("height"), list):
                inp["height"] = height
            inp["num_frames"] = num_frames
            if end_image_path:
                inp["fun_or_fl2v_model"] = True
                # ensure end_image wired if graph has end resize 168
                if "168" in api_prompt and not inp.get("end_image"):
                    inp["end_image"] = ["168", 0]

        for nid in _find_nodes(api_prompt, "WanVideoSampler"):
            inp = api_prompt[nid]["inputs"]
            if not (isinstance(inp.get("seed"), list) and len(inp.get("seed") or []) == 2):
                inp["seed"] = new_seed
            if not (isinstance(inp.get("cfg"), list) and len(inp.get("cfg") or []) == 2):
                inp["cfg"] = cfg

        # P0 W0: steps + dual-pass boundary (was only patching INTConstant==30 → no-op)
        wan_step_info = _apply_wan22_steps_and_boundary(api_prompt, int(steps))
        steps = int(wan_step_info["steps"])

        # P1: BlockSwap + TeaCache/MagCache on both high/low samplers
        wan_swap_info = _apply_wan22_block_swap(api_prompt, blocks)
        try:
            wan_cache_info = _apply_wan22_cache(
                api_prompt,
                cache=str(cache_mode),
                teacache_thresh=tc_thresh,
                magcache_thresh=mc_thresh,
                magcache_k=mc_k,
            )
        except ValueError as e:
            return fail_result(error="BAD_CACHE", message=str(e), backend=backend_id)

        # Unique prefix avoids Comfy execution_cache returning empty outputs +
        # picking an older agent_i2v_*.mp4 by mtime (false "2s" successes).
        tag = "flf" if end_image_path else "i2v"
        vhs_prefix = f"agent_{tag}_{int(new_seed)}_{int(time.time())}"
        for nid in _find_nodes(api_prompt, "VHS_VideoCombine"):
            inp = api_prompt[nid]["inputs"]
            inp["frame_rate"] = frame_rate
            inp["filename_prefix"] = vhs_prefix
            inp["save_output"] = True
            inp["format"] = inp.get("format") or "video/h264-mp4"
    else:
        print(
            f"[ERROR] Runner has no inject path for backend={backend_id}. "
            "Add graph wiring or wait for backend implementation."
        )
        return fail_result(
            error="BACKEND_RUNNER_MISSING",
            message=f"no inject path for {backend_id}",
            backend=backend_id,
        )

    for _nid, node in api_prompt.items():
        node["inputs"].pop("_widgets_values", None)

    boundary = wan_step_info.get("boundary")
    print(
        f"Queue I2V: profile={speed_prof['name']} {width}x{height} frames={num_frames} "
        f"steps={steps}"
        f"{f' boundary={boundary}' if boundary is not None else ''} "
        f"cfg={cfg} seed={new_seed} attention={wan_attention} "
        f"cache={wan_cache_info.get('cache', cache_mode)} "
        f"block_swap={wan_swap_info.get('blocks_to_swap', blocks)}"
    )
    if dry_run:
        meta_path = resolve_meta_out(output_filename, meta_out)
        meta = {
            "mode": "i2v",
            "backend": backend_id,
            "status": "dry_run",
            "format": format_id,
            "preset": preset_id,
            "speed_profile": speed_prof["name"],
            "aspect": aspect or job["preset"].get("aspect"),
            "workflow": os.path.basename(wf_path),
            "seed": new_seed,
            "width": width,
            "height": height,
            "num_frames": num_frames,
            "steps": steps,
            "steps_boundary": boundary,
            "steps_wiring": wan_step_info,
            "cache": wan_cache_info,
            "block_swap": wan_swap_info,
            "cfg": cfg,
            "frame_rate": frame_rate,
            "attention_mode": wan_attention,
            "dry_run": True,
            "created_at": utc_now_iso(),
        }
        if meta_path:
            write_meta(meta_path, meta)
        print("[dry-run] skip Comfy queue")
        return ok_result(
            output_path=os.path.abspath(output_filename) if output_filename else None,
            seed=new_seed,
            meta_path=meta_path,
            meta=meta,
            backend=backend_id,
            preset=preset_id,
            dry_run=True,
            speed_profile=speed_prof["name"],
        )

    t0 = time.time()
    payload = json.dumps({"prompt": api_prompt}).encode("utf-8")
    req = urllib.request.Request(
        f"http://{server_address}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            prompt_id = res["prompt_id"]
            print(f"Prompt queued: {prompt_id}")
            if res.get("node_errors"):
                print(f"[WARN] node_errors: {res['node_errors']}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[ERROR] queue failed HTTP {e.code}: {body[:2000]}")
        return fail_result(error="QUEUE_FAILED", message=body[:500], seed=new_seed)
    except Exception as e:
        print(f"[ERROR] queue failed: {e}")
        return fail_result(error="QUEUE_FAILED", message=str(e), seed=new_seed)

    deadline = time.time() + timeout_sec
    history_entry = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://{server_address}/history/{prompt_id}", timeout=30
            ) as resp:
                hist = json.loads(resp.read().decode("utf-8"))
                if prompt_id in hist:
                    history_entry = hist[prompt_id]
                    print("Generation completed!")
                    break
        except Exception:
            pass
        time.sleep(2)
    if history_entry is None:
        return fail_result(error="COMFY_TIMEOUT", message="I2V timeout", seed=new_seed, prompt_id=prompt_id)

    status = history_entry.get("status") or {}
    if status.get("status_str") == "error" or status.get("completed") is False:
        err_msg = "execution error"
        for msg in status.get("messages") or []:
            if msg and msg[0] == "execution_error":
                err_msg = msg[1].get("exception_message") or err_msg
                print(
                    f"[ERROR] node={msg[1].get('node_id')} {msg[1].get('node_type')}: "
                    f"{str(err_msg)[:500]}"
                )
        return fail_result(
            error="EXECUTION_ERROR", message=str(err_msg)[:500], seed=new_seed, prompt_id=prompt_id
        )

    video_info = None
    outputs = history_entry.get("outputs") or {}
    for _nid, out in outputs.items():
        for key in ("gifs", "videos"):
            if key in out and out[key]:
                video_info = out[key][0]
                break
        if video_info:
            break

    if not video_info:
        candidates = []
        prefix_l = vhs_prefix.lower()
        for folder in (COMFY_OUTPUT_DIR, COMFY_TEMP_DIR):
            if not os.path.isdir(folder):
                continue
            for root, _dirs, files in os.walk(folder):
                for fn in files:
                    low = fn.lower()
                    if low.endswith(".mp4") and prefix_l in low:
                        fp = os.path.join(root, fn)
                        candidates.append((os.path.getmtime(fp), fp))
        if candidates:
            candidates.sort(reverse=True)
            src = candidates[0][1]
            shutil.copy2(src, output_filename)
            print(f"Copied matched prefix mp4: {src} -> {output_filename}")
        else:
            # Fully cached runs can leave empty outputs — do not steal old agent_i2v_*.mp4
            print(
                f"[ERROR] No video in history outputs "
                f"(prefix={vhs_prefix!r}). If Comfy fully cache-hit, re-run with new seed."
            )
            return fail_result(
                error="COMFY_NO_OUTPUT",
                message=f"no video output for prefix {vhs_prefix}",
                seed=new_seed,
                prompt_id=prompt_id,
            )
    else:
        filename = video_info.get("filename")
        subfolder = video_info.get("subfolder", "")
        ftype = video_info.get("type", "output")
        base = COMFY_OUTPUT_DIR if ftype == "output" else COMFY_TEMP_DIR
        src = os.path.join(base, subfolder, filename) if subfolder else os.path.join(base, filename)
        if os.path.exists(src):
            shutil.copy2(src, output_filename)
            print(f"Copied video: {src} -> {output_filename}")
        else:
            view_url = (
                f"http://{server_address}/view?filename={urllib.parse.quote(filename)}"
                f"&subfolder={urllib.parse.quote(subfolder)}&type={ftype}"
            )
            print(f"Downloading video via API: {filename}")
            urllib.request.urlretrieve(view_url, output_filename)

    elapsed = round(time.time() - t0, 2)
    print(f"I2V elapsed_sec={elapsed} attention={wan_attention} steps={steps}")

    meta_path = resolve_meta_out(output_filename, meta_out)
    meta = {
        "mode": "i2v",
        "backend": backend_id,
        "format": format_id,
        "preset": preset_id,
        "aspect": aspect or job["preset"].get("aspect"),
        "stage": job["preset"].get("stage"),
        "deliver_preset_hint": job.get("deliver_preset_id") or job.get("default_deliver_preset"),
        "workflow": os.path.basename(wf_path),
        "prompt": prompt_text,
        "negative": negative_text,
        "seed": new_seed,
        "width": width,
        "height": height,
        "num_frames": num_frames,
        "steps": steps,
        "steps_boundary": boundary,
        "steps_wiring": wan_step_info or None,
        "cfg": cfg,
        "frame_rate": frame_rate,
        "attention_mode": wan_attention,
        "speed_profile": speed_prof["name"],
        "cache": wan_cache_info or {"cache": cache_mode},
        "block_swap": wan_swap_info or {"blocks_to_swap": blocks},
        "elapsed_sec": elapsed,
        "source_image": os.path.abspath(input_image_path),
        "output_path": os.path.abspath(output_filename),
        "comfy_prompt_id": prompt_id,
        "created_at": utc_now_iso(),
        "p0_speed": {
            "steps_wired": True,
            "attention_default": "sageattn",
            "elapsed_logged": True,
        },
        "p1_speed": {
            "cache": (wan_cache_info or {}).get("cache"),
            "block_swap": (wan_swap_info or {}).get("blocks_to_swap"),
            "profile": speed_prof["name"],
        },
    }
    if meta_path:
        write_meta(meta_path, meta)
        print(f"Meta saved: {meta_path}")

    return ok_result(
        output_path=os.path.abspath(output_filename),
        seed=new_seed,
        prompt_id=prompt_id,
        meta_path=meta_path,
        meta=meta,
        backend=backend_id,
        preset=preset_id,
        elapsed_sec=elapsed,
        attention_mode=wan_attention,
        speed_profile=speed_prof["name"],
    )


def _build_parser() -> argparse.ArgumentParser:
    try:
        cfg = load_video_backends()
        backends = list_backend_ids(cfg)
        presets = list_preset_ids(cfg)
        formats = list_format_ids(cfg)
        default_backend = cfg.get("default_backend", "wan22")
        # None → resolve_i2v_job applies default_format from JSON
        default_format = None
        default_preset = None
    except Exception:
        backends = ["wan22", "ltx23"]
        presets = ["work_16x9_540"]
        formats = ["cinematic_16x9", "shorts_9x16", "classic_4x3", "portrait_3x4"]
        default_backend = "wan22"
        default_format = None
        default_preset = None

    parser = argparse.ArgumentParser(
        description=(
            "Image-to-Video multi-backend CLI. "
            "Aspect comes from --format (16:9 / 9:16 / 4:3 / 3:4 / 1:1), not a fixed global ratio."
        )
    )
    parser.add_argument("--input", "-i", required=True, help="Keyframe image path")
    parser.add_argument(
        "--prompt",
        "-p",
        default=None,
        help="Motion / scene prompt (combined with --motion-preset if set)",
    )
    parser.add_argument("--prompt-file", default=None)
    parser.add_argument(
        "--motion-preset",
        default=None,
        help=(
            "Motion intent preset id (idle, push_in, pan_left, talk_gesture, …). "
            "See --list-motion-presets. Composed with -p as extra action."
        ),
    )
    parser.add_argument(
        "--list-motion-presets",
        action="store_true",
        help="Print I2V motion intent presets and exit",
    )
    parser.add_argument("--negative", default=DEFAULT_NEGATIVE)
    parser.add_argument("--negative-file", default=None)
    parser.add_argument("--output", "-o", default=None)
    parser.add_argument(
        "--backend",
        default=default_backend,
        help=f"I2V backend id (default: {default_backend}). Known: {', '.join(backends)}",
    )
    parser.add_argument(
        "--format",
        dest="format_id",
        default=default_format,
        help=(
            "Aspect/format profile (optional; default from video_backends.json "
            f"default_format). Known: {', '.join(formats)}. "
            "Examples: cinematic_16x9, shorts_9x16, classic_4x3, portrait_3x4."
        ),
    )
    parser.add_argument(
        "--preset",
        default=default_preset,
        help=(
            "Work resolution preset override (optional). "
            f"If omitted, format's default work preset is used. Known: {', '.join(presets)}"
        ),
    )
    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help="Override preset width (use with --height)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=None,
        help="Override preset height (use with --width)",
    )
    parser.add_argument("--frames", type=int, default=49, help="Frame count")
    parser.add_argument("--fps", type=int, default=16)
    parser.add_argument(
        "--steps",
        type=int,
        default=None,
        help="Sampler steps (default: from --profile; deliver=6)",
    )
    parser.add_argument("--cfg", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--profile",
        choices=list(I2V_SPEED_PROFILES.keys()),
        default="deliver",
        help="Wan speed profile preview|deliver|quality (default deliver; LTX ignores)",
    )
    parser.add_argument(
        "--ltx-profile",
        default=None,
        help=(
            "LTX quality tier draft|work|hero (default work=720p). "
            "draft≈540 · work≈1280 · hero≈1920. docs/ltx23_quality_research_and_improvement.md"
        ),
    )
    parser.add_argument(
        "--list-ltx-profiles",
        action="store_true",
        help="Print LTX quality profiles and exit",
    )
    parser.add_argument(
        "--cache",
        choices=["teacache", "magcache", "none"],
        default=None,
        help=(
            "Step cache: teacache|magcache|none. Default none "
            "(QA: Tea/Mag grain rejected on deliver path)"
        ),
    )
    parser.add_argument("--teacache-thresh", type=float, default=None)
    parser.add_argument("--magcache-thresh", type=float, default=None)
    parser.add_argument("--magcache-k", type=int, default=None)
    parser.add_argument(
        "--block-swap",
        type=int,
        default=None,
        help=(
            "WanVideoBlockSwap blocks — VRAM vs speed; tune per job "
            "(start deliver=10; raise if OOM; 0=fastest/more VRAM). "
            "See docs/wan22_i2v_speed_research.md §4.1"
        ),
    )
    parser.add_argument(
        "--no-profile-long-edge",
        action="store_true",
        help="Do not apply preview max_long_edge downscale",
    )
    parser.add_argument(
        "--attention",
        default=None,
        help=(
            "WanVideoModelLoader attention_mode (default: sageattn via AGENT_WAN_ATTENTION). "
            "Examples: sageattn, sdpa, flash_attn_2"
        ),
    )
    parser.add_argument(
        "--workflow",
        default=None,
        help="Override workflow path or catalog alias (skips backend workflow map)",
    )
    parser.add_argument(
        "--last",
        "--end-image",
        dest="end_image",
        default=None,
        help=(
            "FLF end/last frame image path. Selects backend wan22_flf "
            "(preset i2v_wan22_a14b_flf) unless --workflow overrides."
        ),
    )
    parser.add_argument("--meta-out", default=None)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build/inject graph and write meta only (no Comfy queue)",
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="Print I2V speed profiles and exit",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="Print presets from video_backends.json and exit",
    )
    parser.add_argument(
        "--list-backends",
        action="store_true",
        help="Print backends from video_backends.json and exit",
    )
    parser.add_argument(
        "--list-formats",
        action="store_true",
        help="Print aspect/format profiles and exit",
    )
    return parser


if __name__ == "__main__":
    parser = _build_parser()
    # allow --list-* without --input
    if any(
        a in (
            "--list-presets",
            "--list-backends",
            "--list-formats",
            "--list-profiles",
            "--list-motion-presets",
            "--list-ltx-profiles",
        )
        for a in sys.argv[1:]
    ):
        pre = argparse.ArgumentParser(add_help=False)
        pre.add_argument("--list-presets", action="store_true")
        pre.add_argument("--list-backends", action="store_true")
        pre.add_argument("--list-formats", action="store_true")
        pre.add_argument("--list-profiles", action="store_true")
        pre.add_argument("--list-motion-presets", action="store_true")
        pre.add_argument("--list-ltx-profiles", action="store_true")
        pre_args, _ = pre.parse_known_args()
        if pre_args.list_motion_presets:
            from lib.motion_presets import format_motion_presets_help

            print(format_motion_presets_help())
            sys.exit(0)
        if getattr(pre_args, "list_ltx_profiles", False):
            from lib.ltx_quality_profiles import format_ltx_profiles_table

            print(format_ltx_profiles_table())
            sys.exit(0)
        cfg = load_video_backends()
        if pre_args.list_backends:
            for bid in list_backend_ids(cfg):
                b = cfg["backends"][bid]
                print(f"{bid}  status={b.get('status')}  {b.get('engine', '')}")
        if pre_args.list_formats:
            for fid in list_format_ids(cfg):
                f = cfg["formats"][fid]
                print(
                    f"{fid}  aspect={f.get('aspect')}  "
                    f"work={f.get('default_work_preset')}  "
                    f"deliver={f.get('default_deliver_preset')}"
                )
        if pre_args.list_presets:
            for pid in list_preset_ids(cfg):
                p = cfg["presets"][pid]
                print(
                    f"{pid}  {p['width']}x{p['height']}  "
                    f"aspect={p.get('aspect')}  stage={p.get('stage')}"
                )
        if pre_args.list_profiles:
            for name, p in I2V_SPEED_PROFILES.items():
                print(
                    f"{name}  steps={p['steps']} cache={p['cache']} "
                    f"block_swap={p['block_swap']} "
                    f"max_long_edge={p.get('max_long_edge')}  # {p.get('notes')}"
                )
        sys.exit(0)

    args = parser.parse_args()

    prompt = load_text(args.prompt_file) if args.prompt_file else (args.prompt or "")
    motion_preset_id = None
    if getattr(args, "motion_preset", None):
        from lib.motion_presets import compose_motion_prompt, resolve_motion_preset_id

        motion_preset_id = resolve_motion_preset_id(args.motion_preset)
        if not motion_preset_id:
            parser.error(
                f"Unknown --motion-preset {args.motion_preset!r} "
                f"(use --list-motion-presets)"
            )
        prompt, neg_extra = compose_motion_prompt(motion_preset_id, prompt)
        if not prompt:
            parser.error("motion preset produced empty prompt")
    elif not prompt:
        parser.error("--prompt or --prompt-file or --motion-preset required")
    else:
        neg_extra = None

    negative = load_text(args.negative_file) if args.negative_file else args.negative
    if neg_extra:
        negative = f"{negative}, {neg_extra}" if negative else neg_extra

    if (args.width is None) ^ (args.height is None):
        parser.error("Provide both --width and --height, or neither (use --format/--preset)")

    wf = None
    if args.workflow:
        wf = resolve_workflow(args.workflow)

    result = generate_i2v(
        input_image_path=args.input,
        prompt_text=prompt,
        negative_text=negative,
        output_filename=args.output,
        width=args.width,
        height=args.height,
        num_frames=args.frames,
        seed=args.seed,
        steps=args.steps,
        cfg=args.cfg,
        frame_rate=args.fps,
        backend=args.backend,
        format_id=args.format_id,
        preset=args.preset,
        workflow_path=wf,
        meta_out=args.meta_out,
        timeout_sec=args.timeout,
        attention_mode=args.attention,
        dry_run=bool(args.dry_run),
        profile=args.profile,
        ltx_profile=getattr(args, "ltx_profile", None),
        cache=args.cache,
        teacache_thresh=args.teacache_thresh,
        magcache_thresh=args.magcache_thresh,
        magcache_k=args.magcache_k,
        block_swap=args.block_swap,
        apply_profile_long_edge=not args.no_profile_long_edge,
        end_image_path=args.end_image,
    )
    sys.exit(0 if result.get("ok") else 1)
