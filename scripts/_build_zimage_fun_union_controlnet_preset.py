#!/usr/bin/env python3
"""
Build API preset from official Comfy template:

  user/default/workflows/image_z_image_turbo_fun_union_controlnet.json

Flattens the embedded subgraph (Z-Image-Turbo Fun Control to Image) into a
pure API graph. Control preprocess (Canny vs raw pose) is done in the agent
script before LoadImage — same as prior generate_moody_controlnet behavior —
so one API graph covers Canny + Pose Union conditions.
"""
from __future__ import annotations

import _bootstrap  # noqa: F401
import json
import shutil
from pathlib import Path

ROOT = Path(r"F:\ComfyUI_workflows\agent_custom")
PRESETS = ROOT / "workflows" / "agent" / "presets"
HUMAN = ROOT / "workflows" / "human"
SRC_UI = Path(
    r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows"
    r"\image_z_image_turbo_fun_union_controlnet.json"
)

API_NAME = "zimage_fun_union_controlnet"
PRESET_KEY = "zimage_fun_union_controlnet"


def build_api() -> dict:
    # Node IDs match official outer + subgraph IDs for traceability.
    return {
        "58": {
            "class_type": "LoadImage",
            "inputs": {"image": "control_input.png"},
        },
        "62": {
            "class_type": "ImageScaleToMaxDimension",
            "inputs": {
                "image": ["58", 0],
                "upscale_method": "lanczos",
                "largest_size": 1024,
            },
        },
        "39": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": "qwen_3_4b.safetensors",
                "type": "lumina2",
                "device": "default",
            },
        },
        "46": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "ZImageTurbo\\moodyProMix_zitV12DPO.safetensors",
                "weight_dtype": "default",
            },
        },
        "40": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "ae.safetensors"},
        },
        "64": {
            "class_type": "ModelPatchLoader",
            "inputs": {
                "name": "Z-Image-Turbo-Fun-Controlnet-Union-2.1.safetensors"
            },
        },
        "45": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "photoreal cinematic still",
                "clip": ["39", 0],
            },
        },
        "42": {
            "class_type": "ConditioningZeroOut",
            "inputs": {"conditioning": ["45", 0]},
        },
        "69": {
            "class_type": "GetImageSize",
            "inputs": {"image": ["62", 0]},
        },
        "41": {
            "class_type": "EmptySD3LatentImage",
            "inputs": {
                "width": ["69", 0],
                "height": ["69", 1],
                "batch_size": 1,
            },
        },
        "60": {
            "class_type": "QwenImageDiffsynthControlnet",
            "inputs": {
                "model": ["46", 0],
                "model_patch": ["64", 0],
                "vae": ["40", 0],
                "image": ["62", 0],
                "strength": 1.0,
            },
        },
        "47": {
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {"model": ["60", 0], "shift": 3.0},
        },
        "44": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["47", 0],
                "seed": 0,
                "steps": 8,
                "cfg": 1.0,
                "sampler_name": "res_multistep",
                "scheduler": "simple",
                "positive": ["45", 0],
                "negative": ["42", 0],
                "latent_image": ["41", 0],
                "denoise": 1.0,
            },
        },
        "43": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["44", 0], "vae": ["40", 0]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["43", 0],
                "filename_prefix": "zimage_fun_union_cn",
            },
        },
    }


def build_ports() -> dict:
    return {
        "preset": PRESET_KEY,
        "workflow_api": f"presets/{API_NAME}.api.json",
        "description": (
            "Official Z-Image Turbo Fun Union ControlNet "
            "(image_z_image_turbo_fun_union_controlnet), subgraph flattened. "
            "Empty latent sized from control image; QwenImageDiffsynthControlnet + Union 2.1 patch."
        ),
        "source_ui": str(SRC_UI).replace("\\", "/"),
        "family": "zimage",
        "ports": {
            "positive": {"node": "45", "key": "text"},
            "seed": {"node": "44", "key": "seed"},
            "denoise": {"node": "44", "key": "denoise", "optional": True},
            "steps": {"node": "44", "key": "steps", "optional": True},
            "cfg": {"node": "44", "key": "cfg", "optional": True},
            "sampler_name": {"node": "44", "key": "sampler_name", "optional": True},
            "scheduler": {"node": "44", "key": "scheduler", "optional": True},
            "control_image": {
                "node": "58",
                "key": "image",
                "copy_to_input_dir": True,
            },
            "control_strength": {
                "node": "60",
                "key": "strength",
                "optional": True,
            },
            "unet_name": {"node": "46", "key": "unet_name", "optional": True},
            "clip_name": {"node": "39", "key": "clip_name", "optional": True},
            "vae_name": {"node": "40", "key": "vae_name", "optional": True},
            "patch_name": {"node": "64", "key": "name", "optional": True},
            "largest_size": {
                "node": "62",
                "key": "largest_size",
                "optional": True,
            },
            "filename_prefix": {
                "node": "9",
                "key": "filename_prefix",
                "optional": True,
            },
        },
        "defaults": {
            "denoise": 1.0,
            "steps": 8,
            "cfg": 1.0,
            "control_strength": 1.0,
            "largest_size": 1024,
            "filename_prefix": "zimage_fun_union_cn",
            "vae_name": "ae.safetensors",
            "clip_name": "qwen_3_4b.safetensors",
            "patch_name": "Z-Image-Turbo-Fun-Controlnet-Union-2.1.safetensors",
        },
        "notes": [
            "Source template: image_z_image_turbo_fun_union_controlnet.json",
            "In-graph Canny removed — agent applies canny/raw preprocess then LoadImage",
            "Latent size = GetImageSize(scaled control); no VAEEncode I2I base",
            "Identity comes from prompt (+ core_prefix), not from a face VAEEncode path",
            "Legacy I2I-ControlNet-moody remains via --legacy-mini only",
        ],
    }


def patch_feature_presets() -> None:
    path = PRESETS / "lonecat_feature_presets.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    presets = data.setdefault("presets", {})
    presets[PRESET_KEY] = {
        "feature_ids": ["controlnet", "model_diffusion"],
        "file": f"presets/{API_NAME}.api.json",
        "ports": f"presets/{API_NAME}.ports.json",
        "family": "zimage",
        "status": "ready",
        "source_workflow": "image_z_image_turbo_fun_union_controlnet",
    }
    # alias used in older plan text
    presets["lonecat_controlnet"] = {
        "feature_ids": ["controlnet", "model_diffusion"],
        "file": f"presets/{API_NAME}.api.json",
        "ports": f"presets/{API_NAME}.ports.json",
        "family": "zimage",
        "status": "ready",
        "alias_of": PRESET_KEY,
        "source_workflow": "image_z_image_turbo_fun_union_controlnet",
    }
    sel = data.setdefault("select_preset", {})
    sel["controlnet_default"] = PRESET_KEY
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("updated", path)


def patch_catalog() -> None:
    path = ROOT / "workflows" / "agent" / "catalog.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    wfs = data.setdefault("workflows", {})
    entry = {
        "file": f"presets/{API_NAME}.api.json",
        "ports": f"presets/{API_NAME}.ports.json",
        "format": "api",
        "role": "controlnet",
        "family": "zimage",
        "source": "image_z_image_turbo_fun_union_controlnet",
        "used_by": ["scripts/generate_moody_controlnet.py"],
    }
    wfs[PRESET_KEY] = entry
    wfs["lonecat_controlnet"] = dict(entry)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("updated", path)


def main() -> None:
    PRESETS.mkdir(parents=True, exist_ok=True)
    api = build_api()
    ports = build_ports()
    api_path = PRESETS / f"{API_NAME}.api.json"
    ports_path = PRESETS / f"{API_NAME}.ports.json"
    api_path.write_text(json.dumps(api, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ports_path.write_text(json.dumps(ports, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", api_path)
    print("wrote", ports_path)

    # Keep a human copy of the official UI source
    if SRC_UI.is_file():
        dest = HUMAN / "image_z_image_turbo_fun_union_controlnet.json"
        shutil.copy2(SRC_UI, dest)
        print("copied UI source →", dest)

    patch_feature_presets()
    patch_catalog()
    print("OK", PRESET_KEY)


if __name__ == "__main__":
    main()
