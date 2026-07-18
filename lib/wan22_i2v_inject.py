"""Wan2.2 I2V/FLF graph inject helpers (agent API presets).

Improvements (2026-07-18):
  - High/Low model + LoRA matching by filename keywords (not loader order)
  - Force scalar CFG on both samplers (drop CFG schedule link)
  - Optional scheduler / shift / LoRA strengths / quant tier / boundary
  - Strip unused CLIP→bridge dead path if present
"""

from __future__ import annotations

from typing import Any

# Relative to Comfy models/diffusion_models (or unet) as used by WanVideoModelLoader
WAN_I2V_GGUF: dict[str, dict[str, str]] = {
    "q4": {
        "high": r"Wan2.2\Wan2.2-I2V-A14B-HighNoise-Q4_K_M.gguf",
        "low": r"Wan2.2\Wan2.2-I2V-A14B-LowNoise-Q4_K_M.gguf",
    },
    "q5": {
        "high": r"Wan2.2\Wan2.2-I2V-A14B-HighNoise-Q5_K_M.gguf",
        "low": r"Wan2.2\Wan2.2-I2V-A14B-LowNoise-Q5_K_M.gguf",
    },
}

WAN_I2V_LIGHTX2V_LORA = {
    "high": r"Wan2.2\Wan_2_2_I2V_A14B_HIGH_lightx2v_4step_lora_260412_rank_64_fp16.safetensors",
    "low": r"Wan2.2\Wan_2_2_I2V_A14B_LOW_lightx2v_4step_lora_260412_rank_64_fp16.safetensors",
}

WAN_VAE = "wan_2.1_vae.safetensors"
WAN_T5 = "umt5-xxl-enc-bf16.safetensors"

# Common WanVideoWrapper / Comfy schedulers used with Wan2.2 + lightx2v
WAN_SCHEDULERS = (
    "dpm++_sde",
    "euler",
    "euler_ancestral",
    "uni_pc",
    "uni_pc_bh2",
    "res_multistep",
    "lcm",
    "flowmatch_euler",
    "simple",
    "normal",
    "sgm_uniform",
    "karras",
    "exponential",
    "ddim_uniform",
    "beta",
    "linear_quadratic",
    "kl_optimal",
)

# Dead CLIP path node class types (not used when WanVideoTextEncode feeds samplers)
_DEAD_CLIP_TYPES = frozenset(
    {
        "CLIPLoader",
        "CLIPTextEncode",
        "WanVideoTextEmbedBridge",
    }
)


def find_nodes(api_prompt: dict, class_type: str) -> list[str]:
    return [nid for nid, n in api_prompt.items() if n.get("class_type") == class_type]


def link_node_id(val: Any) -> str | None:
    if isinstance(val, list) and len(val) >= 1:
        return str(val[0])
    return None


def classify_high_low(path_or_name: str) -> str:
    """Return 'high' | 'low' | 'unknown' from model/LoRA path."""
    u = (path_or_name or "").replace("\\", "/").upper()
    base = u.rsplit("/", 1)[-1]
    # Prefer explicit HIGH/LOW tokens (avoid matching substring in other words)
    if "HIGHNOISE" in base or "HIGH_NOISE" in base or "_HIGH_" in f"_{base}_" or "HIGH-NOISE" in base:
        return "high"
    if "LOWNOISE" in base or "LOW_NOISE" in base or "_LOW_" in f"_{base}_" or "LOW-NOISE" in base:
        return "low"
    # lightx2v style: ...HIGH_lightx2v... / ...LOW_lightx2v...
    if "HIGH" in base and "LOW" not in base:
        return "high"
    if "LOW" in base and "HIGH" not in base:
        return "low"
    if "HIGH" in base:
        return "high"
    if "LOW" in base:
        return "low"
    return "unknown"


def resolve_quant_paths(quant: str | None) -> dict[str, str]:
    key = (quant or "q4").strip().lower().replace("_k_m", "").replace("-", "")
    if key in ("q4", "q4km", "4"):
        key = "q4"
    elif key in ("q5", "q5km", "5"):
        key = "q5"
    else:
        raise ValueError(f"unknown wan quant {quant!r}; use q4|q5")
    paths = WAN_I2V_GGUF.get(key)
    if not paths:
        raise ValueError(f"no GGUF map for quant {key}")
    return {"quant": key, "high": paths["high"], "low": paths["low"]}


# Dedicated NSFW dual UNets (relative to models/diffusion_models)
WAN_I2V_NSFW_REMIX = {
    "high": r"Wan2.2\nsfw_remix\Wan2.2_Remix_NSFW_i2v_14b_HIGH_fp8_v3.0.safetensors",
    "low": r"Wan2.2\nsfw_remix\Wan2.2_Remix_NSFW_i2v_14b_LOW_fp8_v3.0.safetensors",
}


def strip_dead_clip_path(api_prompt: dict) -> list[str]:
    """Remove CLIPLoader/CLIPTextEncode/TextEmbedBridge if no sampler uses them.

    Agent presets historically carried a disconnected CLIP path while
    WanVideoTextEncode feeds samplers. Safe to drop for clarity/load noise.
    """
    samplers = find_nodes(api_prompt, "WanVideoSampler")
    referenced: set[str] = set()
    for sid in samplers:
        te = api_prompt[sid].get("inputs", {}).get("text_embeds")
        lid = link_node_id(te)
        if lid:
            referenced.add(lid)
            # one hop
            node = api_prompt.get(lid) or {}
            for v in (node.get("inputs") or {}).values():
                rid = link_node_id(v)
                if rid:
                    referenced.add(rid)

    removed: list[str] = []
    for nid in list(api_prompt.keys()):
        ct = api_prompt[nid].get("class_type")
        if ct not in _DEAD_CLIP_TYPES:
            continue
        if nid in referenced:
            continue
        # Only remove if nothing in the live text path needs it
        del api_prompt[nid]
        removed.append(nid)
    return removed


def apply_steps_and_boundary(
    api_prompt: dict,
    steps: int,
    boundary: int | None = None,
) -> dict:
    """Wire total steps + high/low boundary (default steps//2)."""
    steps_n = max(1, int(steps))
    if boundary is None:
        bound = max(1, steps_n // 2)
    else:
        bound = max(1, min(int(boundary), steps_n))

    steps_const: set[str] = set()
    boundary_const: set[str] = set()

    for nid in find_nodes(api_prompt, "WanVideoSampler"):
        inp = api_prompt[nid]["inputs"]
        sid = link_node_id(inp.get("steps"))
        if sid:
            steps_const.add(sid)
        else:
            inp["steps"] = steps_n
        for key in ("start_step", "end_step"):
            bid = link_node_id(inp.get(key))
            if bid:
                boundary_const.add(bid)

    for sid in steps_const:
        node = api_prompt.get(sid)
        if node and node.get("class_type") == "INTConstant":
            node["inputs"]["value"] = steps_n

    for bid in boundary_const:
        node = api_prompt.get(bid)
        if node and node.get("class_type") == "INTConstant":
            node["inputs"]["value"] = bound

    for nid in find_nodes(api_prompt, "INTConstant"):
        if nid in steps_const or nid in boundary_const:
            continue
        if api_prompt[nid]["inputs"].get("value") == 30:
            api_prompt[nid]["inputs"]["value"] = steps_n

    return {
        "steps": steps_n,
        "boundary": bound,
        "steps_const_ids": sorted(steps_const),
        "boundary_const_ids": sorted(boundary_const),
    }


def apply_block_swap(api_prompt: dict, blocks_to_swap: int) -> dict:
    blocks = max(0, int(blocks_to_swap))
    ids = find_nodes(api_prompt, "WanVideoBlockSwap")
    for nid in ids:
        api_prompt[nid]["inputs"]["blocks_to_swap"] = blocks
    return {"blocks_to_swap": blocks, "node_ids": ids}


def _trace_to_model_loader(api_prompt: dict, start_nid: str | None) -> str | None:
    """Walk model/ input links until WanVideoModelLoader (max depth 12)."""
    seen: set[str] = set()
    nid = start_nid
    for _ in range(12):
        if not nid or nid in seen or nid not in api_prompt:
            return None
        seen.add(nid)
        node = api_prompt[nid]
        if node.get("class_type") == "WanVideoModelLoader":
            return nid
        inp = node.get("inputs") or {}
        # Prefer explicit model socket, else first link
        nxt = link_node_id(inp.get("model"))
        if not nxt:
            for v in inp.values():
                nxt = link_node_id(v)
                if nxt:
                    break
        nid = nxt
    return None


def resolve_loader_roles(api_prompt: dict) -> dict[str, str | None]:
    """Map high/low expert → ModelLoader id via sampler wiring, then filename, then order.

    High expert = sampler that starts at step 0 (end_step = boundary).
    Low expert  = sampler that starts at boundary (or has samples from high).
    """
    high_id: str | None = None
    low_id: str | None = None
    method = "none"

    for sid in find_nodes(api_prompt, "WanVideoSampler"):
        inp = api_prompt[sid].get("inputs") or {}
        start = inp.get("start_step")
        # bare 0 or missing → high pass; linked boundary const → low pass if samples wired
        start_link = link_node_id(start)
        has_samples = inp.get("samples") is not None and inp.get("samples") != ""
        model_sock = link_node_id(inp.get("model"))
        loader = _trace_to_model_loader(api_prompt, model_sock)
        if loader is None:
            continue
        if start == 0 or start == 0.0 or (start is None and not has_samples):
            high_id = loader
            method = "sampler_start0"
        elif has_samples or start_link is not None:
            low_id = loader
            method = "sampler_chain" if method == "none" else method + "+low"

    # Filename on loaders
    if high_id is None or low_id is None:
        for lid in find_nodes(api_prompt, "WanVideoModelLoader"):
            role = classify_high_low(str(api_prompt[lid].get("inputs", {}).get("model") or ""))
            if role == "high" and high_id is None:
                high_id = lid
                method = method + "+name_high" if method != "none" else "filename"
            elif role == "low" and low_id is None:
                low_id = lid
                method = method + "+name_low" if method != "none" else "filename"

    # Last resort: document order
    loaders = find_nodes(api_prompt, "WanVideoModelLoader")
    if high_id is None and loaders:
        high_id = loaders[0]
        method = method + "+order" if method != "none" else "order"
    if low_id is None:
        for lid in loaders:
            if lid != high_id:
                low_id = lid
                break

    return {"high": high_id, "low": low_id, "method": method}


def apply_models_and_attention(
    api_prompt: dict,
    *,
    quant: str = "q4",
    attention_mode: str = "sageattn",
    model_high: str | None = None,
    model_low: str | None = None,
    unet_profile: str | None = None,
) -> dict:
    """Assign High/Low weights by graph role (sampler wiring); set attention on all loaders.

    model_high/low: explicit paths (relative to Comfy diffusion_models / unet).
    unet_profile: 'q4'|'q5'|'remix' — used when explicit paths omitted.
    """
    profile = (unet_profile or quant or "q4").strip().lower()
    if model_high and model_low:
        high_path = str(model_high).replace("/", "\\")
        low_path = str(model_low).replace("/", "\\")
        quant_label = profile if profile not in ("q4", "q5") else profile
        if profile in ("remix", "nsfw_remix", "nsfw"):
            quant_label = "remix_fp8"
    elif profile in ("remix", "nsfw_remix", "nsfw"):
        high_path = WAN_I2V_NSFW_REMIX["high"]
        low_path = WAN_I2V_NSFW_REMIX["low"]
        quant_label = "remix_fp8"
    else:
        q = resolve_quant_paths(quant if profile in ("q4", "q5") else "q4")
        high_path, low_path = q["high"], q["low"]
        quant_label = q["quant"]

    roles = resolve_loader_roles(api_prompt)
    high_id = roles.get("high")
    low_id = roles.get("low")

    for lid in find_nodes(api_prompt, "WanVideoModelLoader"):
        li = api_prompt[lid].setdefault("inputs", {})
        li["base_precision"] = "bf16"
        li["quantization"] = "disabled"
        li.pop("compile_args", None)
        li["attention_mode"] = attention_mode

    if high_id and high_id in api_prompt:
        api_prompt[high_id]["inputs"]["model"] = high_path
        api_prompt[high_id]["inputs"]["attention_mode"] = attention_mode
    if low_id and low_id in api_prompt:
        api_prompt[low_id]["inputs"]["model"] = low_path
        api_prompt[low_id]["inputs"]["attention_mode"] = attention_mode

    return {
        "quant": quant_label,
        "unet_profile": profile,
        "model_high": high_path,
        "model_low": low_path,
        "loader_high": high_id,
        "loader_low": low_id,
        "role_method": roles.get("method"),
        "attention_mode": attention_mode,
    }


def apply_loras(
    api_prompt: dict,
    *,
    strength_high: float = 1.0,
    strength_low: float = 1.0,
) -> dict:
    """Set lightx2v HIGH/LOW LoRA paths + strengths via SetLoRAs→loader role, else name."""
    roles = resolve_loader_roles(api_prompt)
    high_loader = roles.get("high")
    low_loader = roles.get("low")
    high_ids: list[str] = []
    low_ids: list[str] = []
    assigned: set[str] = set()

    for sid in find_nodes(api_prompt, "WanVideoSetLoRAs"):
        inp = api_prompt[sid].get("inputs") or {}
        loader = _trace_to_model_loader(api_prompt, link_node_id(inp.get("model")))
        lora_nid = link_node_id(inp.get("lora"))
        if not lora_nid or lora_nid not in api_prompt:
            continue
        if api_prompt[lora_nid].get("class_type") != "WanVideoLoraSelect":
            continue
        if loader == high_loader:
            role = "high"
        elif loader == low_loader:
            role = "low"
        else:
            role = classify_high_low(str(api_prompt[lora_nid]["inputs"].get("lora") or ""))
            if role == "unknown":
                role = "high"
        if role == "low":
            api_prompt[lora_nid]["inputs"]["lora"] = WAN_I2V_LIGHTX2V_LORA["low"]
            api_prompt[lora_nid]["inputs"]["strength"] = float(strength_low)
            low_ids.append(lora_nid)
        else:
            api_prompt[lora_nid]["inputs"]["lora"] = WAN_I2V_LIGHTX2V_LORA["high"]
            api_prompt[lora_nid]["inputs"]["strength"] = float(strength_high)
            high_ids.append(lora_nid)
        api_prompt[lora_nid]["inputs"]["merge_loras"] = False
        assigned.add(lora_nid)

    # Any leftover LoraSelect nodes: filename
    for nid in find_nodes(api_prompt, "WanVideoLoraSelect"):
        if nid in assigned:
            continue
        cur = str(api_prompt[nid]["inputs"].get("lora", ""))
        role = classify_high_low(cur)
        if role == "low":
            api_prompt[nid]["inputs"]["lora"] = WAN_I2V_LIGHTX2V_LORA["low"]
            api_prompt[nid]["inputs"]["strength"] = float(strength_low)
            low_ids.append(nid)
        else:
            api_prompt[nid]["inputs"]["lora"] = WAN_I2V_LIGHTX2V_LORA["high"]
            api_prompt[nid]["inputs"]["strength"] = float(strength_high)
            high_ids.append(nid)
        api_prompt[nid]["inputs"]["merge_loras"] = False

    return {
        "lora_high": WAN_I2V_LIGHTX2V_LORA["high"],
        "lora_low": WAN_I2V_LIGHTX2V_LORA["low"],
        "strength_high": float(strength_high),
        "strength_low": float(strength_low),
        "nodes_high": high_ids,
        "nodes_low": low_ids,
        "role_method": roles.get("method"),
    }


def apply_sampler_tuning(
    api_prompt: dict,
    *,
    cfg: float = 1.0,
    seed: int | None = None,
    scheduler: str | None = None,
    shift: float | None = None,
) -> dict:
    """Force scalar CFG (no schedule link); optional scheduler/shift; seed."""
    cfg_f = float(cfg)
    sched = (scheduler or "").strip() or None
    if sched and sched not in WAN_SCHEDULERS:
        # allow unknown — Comfy may support more; only warn via return
        pass
    shift_f = float(shift) if shift is not None else None

    sampler_ids = find_nodes(api_prompt, "WanVideoSampler")
    cfg_was_linked = False
    for nid in sampler_ids:
        inp = api_prompt[nid].setdefault("inputs", {})
        if isinstance(inp.get("cfg"), list):
            cfg_was_linked = True
        # Always scalar CFG for lightx2v distill (both high and low)
        inp["cfg"] = cfg_f
        if seed is not None and not (
            isinstance(inp.get("seed"), list) and len(inp.get("seed") or []) == 2
        ):
            inp["seed"] = int(seed)
        if sched:
            inp["scheduler"] = sched
        if shift_f is not None:
            inp["shift"] = shift_f

    # Drop orphan CFG schedule nodes (optional cleanup)
    removed_cfg_nodes: list[str] = []
    for nid in find_nodes(api_prompt, "CreateCFGScheduleFloatList"):
        # remove if no longer referenced
        still_used = False
        for sid in sampler_ids:
            if link_node_id(api_prompt[sid]["inputs"].get("cfg")) == nid:
                still_used = True
                break
        if not still_used:
            del api_prompt[nid]
            removed_cfg_nodes.append(nid)

    return {
        "cfg": cfg_f,
        "cfg_was_linked": cfg_was_linked,
        "scheduler": sched
        or (
            api_prompt[sampler_ids[0]]["inputs"].get("scheduler")
            if sampler_ids
            else None
        ),
        "shift": shift_f
        if shift_f is not None
        else (
            api_prompt[sampler_ids[0]]["inputs"].get("shift") if sampler_ids else None
        ),
        "samplers": sampler_ids,
        "removed_cfg_schedule_nodes": removed_cfg_nodes,
    }


def apply_support_models(api_prompt: dict) -> dict:
    for nid in find_nodes(api_prompt, "WanVideoVAELoader"):
        api_prompt[nid]["inputs"]["model_name"] = WAN_VAE
    for nid in find_nodes(api_prompt, "LoadWanVideoT5TextEncoder"):
        api_prompt[nid]["inputs"]["model_name"] = WAN_T5
    return {"vae": WAN_VAE, "t5": WAN_T5}


def default_shift_for_scheduler(scheduler: str | None) -> float | None:
    """When user picks scheduler without shift, suggest lightx2v-friendly defaults."""
    s = (scheduler or "").strip().lower()
    if not s:
        return None
    if s in ("euler", "euler_ancestral", "flowmatch_euler"):
        return 5.0
    if s in ("res_multistep",):
        return 8.0
    if s in ("dpm++_sde", "uni_pc", "uni_pc_bh2"):
        return 8.0
    return None


def _rewire_setloras_to(api_prompt: dict, old_lora_nid: str, new_lora_nid: str) -> list[str]:
    """Point WanVideoSetLoRAs.lora links from old LoraSelect to new chained node."""
    touched: list[str] = []
    for sid in find_nodes(api_prompt, "WanVideoSetLoRAs"):
        inp = api_prompt[sid].setdefault("inputs", {})
        if link_node_id(inp.get("lora")) == str(old_lora_nid):
            inp["lora"] = [str(new_lora_nid), 0]
            touched.append(sid)
    return touched


def chain_extra_loras(
    api_prompt: dict,
    *,
    lora_high: str | None = None,
    lora_low: str | None = None,
    strength_high: float = 0.85,
    strength_low: float = 0.9,
) -> dict:
    """Chain optional style/NSFW LoRAs after lightx2v via prev_lora on WanVideoLoraSelect.

    High/Low roles come from SetLoRAs→loader wiring (same as apply_loras).
    Missing path → skip that side (no crash).
    """
    if not lora_high and not lora_low:
        return {"chained": False, "reason": "no_extra_loras"}

    roles = resolve_loader_roles(api_prompt)
    high_loader = roles.get("high")
    low_loader = roles.get("low")
    base_high: str | None = None
    base_low: str | None = None

    for sid in find_nodes(api_prompt, "WanVideoSetLoRAs"):
        inp = api_prompt[sid].get("inputs") or {}
        loader = _trace_to_model_loader(api_prompt, link_node_id(inp.get("model")))
        lora_nid = link_node_id(inp.get("lora"))
        if not lora_nid:
            continue
        if loader == high_loader:
            base_high = lora_nid
        elif loader == low_loader:
            base_low = lora_nid

    # Fallback: filename on LoraSelect
    if base_high is None or base_low is None:
        for nid in find_nodes(api_prompt, "WanVideoLoraSelect"):
            role = classify_high_low(str(api_prompt[nid]["inputs"].get("lora") or ""))
            if role == "high" and base_high is None:
                base_high = nid
            elif role == "low" and base_low is None:
                base_low = nid

    chained: list[dict] = []
    if lora_high and base_high:
        nid = "agent_extra_lora_high"
        api_prompt[nid] = {
            "class_type": "WanVideoLoraSelect",
            "inputs": {
                "lora": str(lora_high).replace("/", "\\"),
                "strength": float(strength_high),
                "low_mem_load": False,
                "merge_loras": False,
                "prev_lora": [str(base_high), 0],
            },
        }
        rewired = _rewire_setloras_to(api_prompt, base_high, nid)
        chained.append(
            {
                "side": "high",
                "node": nid,
                "base": base_high,
                "path": lora_high,
                "strength": float(strength_high),
                "setloras": rewired,
            }
        )
    if lora_low and base_low:
        nid = "agent_extra_lora_low"
        api_prompt[nid] = {
            "class_type": "WanVideoLoraSelect",
            "inputs": {
                "lora": str(lora_low).replace("/", "\\"),
                "strength": float(strength_low),
                "low_mem_load": False,
                "merge_loras": False,
                "prev_lora": [str(base_low), 0],
            },
        }
        rewired = _rewire_setloras_to(api_prompt, base_low, nid)
        chained.append(
            {
                "side": "low",
                "node": nid,
                "base": base_low,
                "path": lora_low,
                "strength": float(strength_low),
                "setloras": rewired,
            }
        )

    return {
        "chained": bool(chained),
        "items": chained,
        "base_high": base_high,
        "base_low": base_low,
        "requested_high": lora_high,
        "requested_low": lora_low,
    }
