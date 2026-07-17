#!/usr/bin/env python3
"""
Build API preset from official Comfy template:

  image_qwen_image_edit_2509.json
  → active subgraph "Image Edit (Qwen 2509)" flattened

enable_turbo_mode (default True):
  Lightning LoRA ON, steps=4, cfg=1
False:
  base UNet only, steps=20, cfg=4
"""
from __future__ import annotations

import _bootstrap  # noqa: F401
import json
import shutil
from pathlib import Path

ROOT = Path(r"F:\ComfyUI_workflows\agent_custom")
PRESETS = ROOT / "workflows" / "agent" / "presets"
HUMAN = ROOT / "workflows" / "human"
SRC = Path(
    r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows"
    r"\image_qwen_image_edit_2509.json"
)

API_NAME = "qwen_edit_2509"
PRESET_KEY = "qwen_edit_2509"

# Agent: LoaderGGUF (not ~20GB fp8 UNETLoader)
GGUF = r"QwenImage\Qwen-Image-Edit-2509-Q5_K_M.gguf"
LORA_LIGHTNING = (
    r"QwenImage\Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
)
CLIP = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
VAE = "qwen_image_vae.safetensors"


def build_api() -> dict:
    return {
        # --- media ---
        "78": {
            "class_type": "LoadImage",
            "inputs": {"image": "qwen_edit_input.png"},
        },
        "79": {
            "class_type": "LoadImage",
            "inputs": {"image": "qwen_edit_input2.png"},
        },
        "80": {
            "class_type": "LoadImage",
            "inputs": {"image": "qwen_edit_input3.png"},
        },
        "117": {
            "class_type": "FluxKontextImageScale",
            "inputs": {"image": ["78", 0]},
        },
        # --- loaders ---
        "39": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "38": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": CLIP,
                "type": "qwen_image",
                "device": "default",
            },
        },
        "37": {
            "class_type": "LoaderGGUF",
            "inputs": {"gguf_name": GGUF},
        },
        "89": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["37", 0],
                "lora_name": LORA_LIGHTNING,
                "strength_model": 1.0,
            },
        },
        # turbo switch: True → lightning (4/1), False → quality (20/4)
        "443": {
            "class_type": "PrimitiveBoolean",
            "inputs": {"value": True},
        },
        "436": {"class_type": "PrimitiveInt", "inputs": {"value": 4}},
        "438": {"class_type": "PrimitiveInt", "inputs": {"value": 20}},
        "437": {"class_type": "PrimitiveFloat", "inputs": {"value": 1.0}},
        "439": {"class_type": "PrimitiveFloat", "inputs": {"value": 4.0}},
        "440": {
            "class_type": "ComfySwitchNode",
            "inputs": {
                "switch": ["443", 0],
                "on_false": ["37", 0],
                "on_true": ["89", 0],
            },
        },
        "441": {
            "class_type": "ComfySwitchNode",
            "inputs": {
                "switch": ["443", 0],
                "on_false": ["438", 0],
                "on_true": ["436", 0],
            },
        },
        "442": {
            "class_type": "ComfySwitchNode",
            "inputs": {
                "switch": ["443", 0],
                "on_false": ["439", 0],
                "on_true": ["437", 0],
            },
        },
        "66": {
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {"model": ["440", 0], "shift": 3.0},
        },
        "75": {
            "class_type": "CFGNorm",
            "inputs": {"model": ["66", 0], "strength": 1.0, "pre_cfg": False},
        },
        # positive (instruction) + empty negative
        "111": {
            "class_type": "TextEncodeQwenImageEditPlus",
            "inputs": {
                "clip": ["38", 0],
                "prompt": "edit instruction",
                "vae": ["39", 0],
                "image1": ["117", 0],
            },
        },
        "110": {
            "class_type": "TextEncodeQwenImageEditPlus",
            "inputs": {
                "clip": ["38", 0],
                "prompt": "",
                "vae": ["39", 0],
                "image1": ["117", 0],
            },
        },
        "88": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["117", 0], "vae": ["39", 0]},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["75", 0],
                "positive": ["111", 0],
                "negative": ["110", 0],
                "latent_image": ["88", 0],
                "seed": 0,
                "steps": ["441", 0],
                "cfg": ["442", 0],
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["39", 0]},
        },
        "60": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["8", 0],
                "filename_prefix": "QwenEdit_2509",
            },
        },
    }


def build_ports() -> dict:
    return {
        "preset": PRESET_KEY,
        "workflow_api": f"presets/{API_NAME}.api.json",
        "description": (
            "Official image_qwen_image_edit_2509 (Image Edit Qwen 2509 subgraph). "
            "enable_turbo_mode switches Lightning 4step vs quality 20/CFG4."
        ),
        "source_ui": str(SRC).replace("\\", "/"),
        "family": "qwen_edit",
        "ports": {
            "input_image": {
                "node": "78",
                "key": "image",
                "copy_to_input_dir": True,
            },
            "input_image2": {
                "node": "79",
                "key": "image",
                "copy_to_input_dir": True,
                "optional": True,
            },
            "input_image3": {
                "node": "80",
                "key": "image",
                "copy_to_input_dir": True,
                "optional": True,
            },
            "positive": {"node": "111", "key": "prompt"},
            "seed": {"node": "3", "key": "seed"},
            "denoise": {"node": "3", "key": "denoise", "optional": True},
            "enable_turbo": {
                "node": "443",
                "key": "value",
                "optional": True,
            },
            "gguf_name": {"node": "37", "key": "gguf_name", "optional": True},
            "clip_name": {"node": "38", "key": "clip_name", "optional": True},
            "vae_name": {"node": "39", "key": "vae_name", "optional": True},
            "lora_name": {"node": "89", "key": "lora_name", "optional": True},
            "lightning_strength": {
                "node": "89",
                "key": "strength_model",
                "optional": True,
            },
            "steps_turbo": {"node": "436", "key": "value", "optional": True},
            "steps_quality": {"node": "438", "key": "value", "optional": True},
            "cfg_turbo": {"node": "437", "key": "value", "optional": True},
            "cfg_quality": {"node": "439", "key": "value", "optional": True},
            "filename_prefix": {
                "node": "60",
                "key": "filename_prefix",
                "optional": True,
            },
        },
        "defaults": {
            "enable_turbo": True,
            "denoise": 1.0,
            "steps_turbo": 4,
            "steps_quality": 20,
            "cfg_turbo": 1.0,
            "cfg_quality": 4.0,
            "filename_prefix": "QwenEdit_2509",
            "gguf_name": GGUF,
            "clip_name": CLIP,
            "vae_name": VAE,
            "lora_name": LORA_LIGHTNING,
        },
        "notes": [
            "Agent: LoaderGGUF (Q5_K_M) instead of fp8 UNETLoader",
            "Active path: subgraph Image Edit (Qwen 2509); Raw Latent branch omitted",
            "Agent --no-lightning maps to enable_turbo=false",
        ],
    }


def patch_catalog_and_features() -> None:
    # catalog
    cat_path = ROOT / "workflows" / "agent" / "catalog.json"
    cat = json.loads(cat_path.read_text(encoding="utf-8"))
    entry = {
        "file": f"presets/{API_NAME}.api.json",
        "ports": f"presets/{API_NAME}.ports.json",
        "format": "api",
        "role": "qwen_instruction_edit",
        "family": "qwen_edit",
        "source": "image_qwen_image_edit_2509",
        "used_by": [
            "scripts/generate_qwen_edit.py",
            "scripts/shot_keyframe_edit.py",
        ],
    }
    cat.setdefault("workflows", {})[PRESET_KEY] = entry
    cat["workflows"]["qwen_edit_2509"] = entry
    cat_path.write_text(
        json.dumps(cat, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # feature presets
    fp_path = PRESETS / "lonecat_feature_presets.json"
    fp = json.loads(fp_path.read_text(encoding="utf-8"))
    fp.setdefault("presets", {})[PRESET_KEY] = {
        "feature_ids": ["qwen_edit", "qwen_edit_2509"],
        "file": f"presets/{API_NAME}.api.json",
        "ports": f"presets/{API_NAME}.ports.json",
        "family": "qwen_edit",
        "status": "ready",
        "source_workflow": "image_qwen_image_edit_2509",
    }
    fp.setdefault("select_preset", {})["qwen_edit_default"] = PRESET_KEY
    fp_path.write_text(
        json.dumps(fp, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("updated catalog + feature presets")


def main() -> None:
    PRESETS.mkdir(parents=True, exist_ok=True)
    api = build_api()
    ports = build_ports()
    (PRESETS / f"{API_NAME}.api.json").write_text(
        json.dumps(api, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (PRESETS / f"{API_NAME}.ports.json").write_text(
        json.dumps(ports, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("wrote api+ports")
    if SRC.is_file():
        shutil.copy2(SRC, HUMAN / "image_qwen_image_edit_2509.json")
        print("copied UI → human/")
    patch_catalog_and_features()
    print("OK", PRESET_KEY)


if __name__ == "__main__":
    main()
