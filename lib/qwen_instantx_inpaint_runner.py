"""Qwen InstantX Inpainting ControlNet — run the **real UI workflow**.

SSOT:
  workflows/human/image_qwen_image_instantx_inpainting_controlnet.json

Path (same idea as LTX AIO / Kenpechi NSFW):
  1. Load human UI JSON
  2. expand_ui_workflow_to_api  (mode 4 outpaint / lightning branches omitted)
  3. Port inject only: image, mask, prompt, seed, steps, cfg, CN strength, …
  4. POST /prompt → first SaveImage

Active pack path (mode 0):
  LoadImage → Scale → VAEEncode + Grow/Blur Mask subgraph
  → ControlNetInpaintingAliMamaApply (InstantX)
  → SetLatentNoiseMask → KSampler → VAEDecode
  → ImageCompositeMasked (paste unmasked pixels) → SaveImage

Bypassed by default (mode 4, not deleted):
  Outpainting branch (ImagePadForOutpaint + second model set)
  Lightning 4-step LoRA (Ctrl-B to enable in UI)

Agent optional: --lightning rewires model through LoraLoader if file exists.
"""

from __future__ import annotations

import json
import os
import random
import shutil
import time
from pathlib import Path
from typing import Any

from lib.comfy_client import (
    COMFYUI_INPUT_DIR,
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
HUMAN_UI = (
    WORKSPACE_ROOT
    / "workflows"
    / "human"
    / "image_qwen_image_instantx_inpainting_controlnet.json"
)
# Optional cached API next to presets (built on first run / by builder)
API_PRESET = (
    WORKSPACE_ROOT
    / "workflows"
    / "agent"
    / "presets"
    / "qwen_instantx_inpaint.api.json"
)

# Pack ships heavy fp8 UNETLoader (~20GB). Agent default = GGUF (same as qwen_edit_2509).
UNET_FP8_PACK = r"QwenImage\qwen_image_edit_2509_fp8_e4m3fn.safetensors"
GGUF_DEFAULT = r"QwenImage\Qwen-Image-Edit-2509-Q5_K_M.gguf"
GGUF_LIGHT = r"QwenImage\qwen-image-edit-2511-Q4_K_M.gguf"  # lower VRAM fallback
CLIP_DEFAULT = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
VAE_DEFAULT = "qwen_image_vae.safetensors"
CN_DEFAULT = "Qwen-Image-InstantX-ControlNet-Inpainting.safetensors"
# Pack names Lightning without QwenImage\ prefix; local lightning is Edit-2511 path
LIGHTNING_CANDIDATES = (
    r"QwenImage\Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors",
    r"QwenImage\Qwen-Image-Lightning-8steps-V2.0-bf16.safetensors",
    "Qwen-Image-Lightning-4steps-V1.0.safetensors",
)


def _load_ui(path: Path | str | None = None) -> dict[str, Any]:
    p = Path(path or HUMAN_UI)
    if not p.is_file():
        raise FileNotFoundError(f"InstantX UI workflow not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _fetch_object_info(server: str = DEFAULT_SERVER) -> dict[str, Any] | None:
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://{server}/object_info", timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _stage(src: str, prefix: str) -> str:
    src_p = Path(src)
    if not src_p.is_file():
        raise FileNotFoundError(f"missing file: {src}")
    dest_dir = Path(COMFYUI_INPUT_DIR)
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = f"{prefix}_{int(time.time())}_{src_p.name}"
    shutil.copy2(src_p, dest_dir / name)
    return name


def _swap_unet_to_gguf(
    api: dict[str, Any],
    *,
    gguf_name: str = GGUF_DEFAULT,
    use_fp8: bool = False,
) -> dict[str, Any]:
    """Keep pack graph; replace UNETLoader (node 37) with LoaderGGUF for VRAM.

    Same agent pattern as qwen_edit_2509: structure retained, weight backend lighter.
    """
    if use_fp8:
        if "37" in api and api["37"].get("class_type") == "LoaderGGUF":
            api["37"] = {
                "class_type": "UNETLoader",
                "inputs": {
                    "unet_name": UNET_FP8_PACK,
                    "weight_dtype": "default",
                },
                "_meta": {"title": "UNet fp8 (pack default)"},
            }
        return api
    # Find UNET loaders on active path (node 37 in pack)
    for nid, node in list(api.items()):
        if node.get("class_type") != "UNETLoader":
            continue
        api[nid] = {
            "class_type": "LoaderGGUF",
            "inputs": {"gguf_name": gguf_name},
            "_meta": {
                "title": "UNet GGUF (agent)",
                "note": f"swapped from UNETLoader for VRAM; gguf={gguf_name}",
            },
        }
    return api


def build_api_from_ui(
    *,
    ui_path: str | Path | None = None,
    server_address: str = DEFAULT_SERVER,
    cache: bool = True,
    gguf_name: str | None = None,
    use_fp8: bool = False,
) -> dict[str, Any]:
    """Expand real UI → API (inpaint path only; outpaint stays bypassed).

    Default: UNETLoader → LoaderGGUF (Q5_K_M). Pass use_fp8=True for pack weights.
    """
    ui = _load_ui(ui_path)
    oi = _fetch_object_info(server_address)
    api = expand_ui_workflow_to_api(ui, object_info=oi)
    api = _swap_unet_to_gguf(
        api,
        gguf_name=gguf_name or GGUF_DEFAULT,
        use_fp8=use_fp8,
    )
    if cache:
        try:
            API_PRESET.parent.mkdir(parents=True, exist_ok=True)
            with open(API_PRESET, "w", encoding="utf-8") as f:
                json.dump(api, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    return api


def _set(api: dict[str, Any], nid: str, key: str, value: Any) -> None:
    if nid not in api:
        return
    api[nid].setdefault("inputs", {})[key] = value


def _wire_external_mask(api: dict[str, Any], mask_name: str) -> None:
    """Optional separate mask image → ImageToMask → GrowMask (keeps pack chain).

    Does not remove pack nodes; only retargets GrowMask input from LoadImage.MASK
    to an explicit mask image (white/red = inpaint region).
    """
    api["agent_mask_img"] = {
        "class_type": "LoadImage",
        "inputs": {"image": mask_name},
        "_meta": {"title": "Agent Mask Image"},
    }
    api["agent_mask"] = {
        "class_type": "ImageToMask",
        "inputs": {"image": ["agent_mask_img", 0], "channel": "red"},
        "_meta": {"title": "Agent Mask"},
    }
    # GrowMask is first in subgraph instance 121
    if "121:199" in api:
        api["121:199"].setdefault("inputs", {})["mask"] = ["agent_mask", 0]


def _enable_lightning(api: dict[str, Any], lora_name: str | None = None) -> str | None:
    """Optional: insert Lightning LoRA between UNET and ModelSampling (pack has this bypassed)."""
    lora = lora_name
    if not lora:
        for c in LIGHTNING_CANDIDATES:
            # existence is not checked here; Comfy will error if missing
            lora = c
            break
    if not lora or "37" not in api or "66" not in api:
        return None
    api["agent_lightning"] = {
        "class_type": "LoraLoaderModelOnly",
        "inputs": {
            "model": ["37", 0],
            "lora_name": lora,
            "strength_model": 1.0,
        },
        "_meta": {"title": "Agent Lightning LoRA"},
    }
    # ModelSampling was model=['37',0]
    api["66"].setdefault("inputs", {})["model"] = ["agent_lightning", 0]
    return lora


def apply_ports(
    api: dict[str, Any],
    *,
    image_name: str,
    prompt: str,
    negative: str = " ",
    seed: int | None = None,
    steps: int | None = None,
    cfg: float | None = None,
    denoise: float | None = None,
    cn_strength: float | None = None,
    max_dim: int | None = None,
    grow_mask: int | None = None,
    blur_radius: int | None = None,
    filename_prefix: str = "QwenInstantX_Inpaint",
    mask_name: str | None = None,
    unet_name: str | None = None,
    gguf_name: str | None = None,
    enable_lightning: bool = False,
    lightning_lora: str | None = None,
) -> dict[str, Any]:
    """Port patch only on expanded API."""
    seed_i = int(seed if seed is not None else random.randint(1, 2**31 - 1))
    _set(api, "71", "image", image_name)
    _set(api, "6", "text", prompt)
    _set(api, "7", "text", negative if negative is not None else " ")
    _set(api, "3", "seed", seed_i)
    if steps is not None:
        _set(api, "3", "steps", int(steps))
    if cfg is not None:
        _set(api, "3", "cfg", float(cfg))
    if denoise is not None:
        _set(api, "3", "denoise", float(denoise))
    if cn_strength is not None:
        _set(api, "108", "strength", float(cn_strength))
    if max_dim is not None:
        _set(api, "172", "largest_size", int(max_dim))
    if grow_mask is not None and "121:199" in api:
        _set(api, "121:199", "expand", int(grow_mask))
    if blur_radius is not None and "121:252" in api:
        _set(api, "121:252", "blur_radius", int(blur_radius))
    _set(api, "60", "filename_prefix", filename_prefix)
    _set(api, "163", "filename_prefix", f"{filename_prefix}_composite")
    # Model backend: prefer GGUF port; unet_name only if node is still UNETLoader
    if gguf_name and "37" in api and api["37"].get("class_type") == "LoaderGGUF":
        _set(api, "37", "gguf_name", gguf_name)
    if unet_name:
        _set(api, "37", "unet_name", unet_name)
    if mask_name:
        _wire_external_mask(api, mask_name)
    lightning_used = None
    if enable_lightning:
        lightning_used = _enable_lightning(api, lightning_lora)
    model_info = None
    if "37" in api:
        model_info = {
            "class_type": api["37"].get("class_type"),
            "inputs": dict(api["37"].get("inputs") or {}),
        }
    return {
        "seed": seed_i,
        "image_name": image_name,
        "mask_name": mask_name,
        "lightning": lightning_used,
        "prompt": prompt[:200],
        "model": model_info,
    }


def generate_qwen_instantx_inpaint(
    *,
    image_path: str,
    prompt: str,
    output_path: str,
    mask_path: str | None = None,
    negative: str = " ",
    seed: int | None = None,
    steps: int | None = None,
    cfg: float | None = None,
    denoise: float | None = None,
    cn_strength: float | None = None,
    max_dim: int | None = None,
    grow_mask: int | None = None,
    blur_radius: int | None = None,
    enable_lightning: bool = False,
    lightning_lora: str | None = None,
    unet_name: str | None = None,
    gguf_name: str | None = None,
    use_fp8: bool = False,
    timeout_sec: float = 600,
    server_address: str = DEFAULT_SERVER,
    ui_path: str | Path | None = None,
) -> dict[str, Any]:
    try:
        api = build_api_from_ui(
            ui_path=ui_path,
            server_address=server_address,
            gguf_name=gguf_name or GGUF_DEFAULT,
            use_fp8=use_fp8,
        )
    except Exception as e:
        return fail_result(error="EXPAND_FAILED", message=str(e))

    try:
        image_name = _stage(image_path, "qwen_ix_img")
        mask_name = _stage(mask_path, "qwen_ix_mask") if mask_path else None
    except Exception as e:
        return fail_result(error="INPUT_MISSING", message=str(e))

    port_meta = apply_ports(
        api,
        image_name=image_name,
        prompt=prompt,
        negative=negative,
        seed=seed,
        steps=steps,
        cfg=cfg,
        denoise=denoise,
        cn_strength=cn_strength,
        max_dim=max_dim,
        grow_mask=grow_mask,
        blur_radius=blur_radius,
        mask_name=mask_name,
        unet_name=unet_name,
        gguf_name=None if use_fp8 else (gguf_name or GGUF_DEFAULT),
        enable_lightning=enable_lightning,
        lightning_lora=lightning_lora,
    )

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

    try:
        filename, subfolder, ftype = extract_first_image(history)
        # Prefer composite SaveImage (163) if present in history
        outputs = history.get("outputs") or {}
        if "163" in outputs:
            imgs = (outputs["163"].get("images") or [])
            if imgs:
                filename = imgs[0].get("filename") or filename
                subfolder = imgs[0].get("subfolder") or subfolder
                ftype = imgs[0].get("type") or ftype
    except Exception as e:
        return fail_result(error="NO_IMAGE_OUTPUT", message=str(e), prompt_id=prompt_id)

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    try:
        download_image(server_address, filename, subfolder, ftype, output_path)
    except Exception as e:
        return fail_result(error="DOWNLOAD_FAILED", message=str(e), prompt_id=prompt_id)

    meta = {
        "tool": "generate_qwen_inpaint",
        "workflow": str(ui_path or HUMAN_UI),
        "runner": "real_ui + expand + ports",
        "role": "qwen_instantx_inpaint",
        "comfy_prompt_id": prompt_id,
        "comfy_image": {"filename": filename, "subfolder": subfolder, "type": ftype},
        "output_path": os.path.abspath(output_path),
        "created_at": utc_now_iso(),
        **port_meta,
    }
    meta_path = os.path.splitext(output_path)[0] + ".meta.json"
    write_meta(meta_path, meta)
    return ok_result(meta_path=meta_path, **meta)
