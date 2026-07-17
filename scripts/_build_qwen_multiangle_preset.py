#!/usr/bin/env python3
"""
Build API preset from official:

  멀티앵글생성-qwen-image.json

Flattens subgraph + keeps QwenMultiangleCameraNode for <sks> angle prompts.
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
    r"\멀티앵글생성-qwen-image.json"
)

API_NAME = "qwen_multiangle_image"
PRESET_KEY = "qwen_multiangle_image"


def build_api() -> dict:
    """
    Flattened graph (node ids from official WF / subgraph):

      LoadImage 41
        → QwenMultiangleCameraNode 111 (angles → <sks> prompt)
        → FluxKontextImageScale 106
      LoaderGGUF 113 → Lightning 107 → Angles LoRA 110 → AuraFlow 94 → CFGNorm 98
      CLIPLoader 93 + VAE 95
      TextEncodeQwenImageEditPlus 103 (pos) / 100 (neg empty)
      FluxKontextMultiReferenceLatentMethod 97/96
      VAEEncode 104 → KSampler 105 → VAEDecode 102 → SaveImage 9
    """
    return {
        "41": {
            "class_type": "LoadImage",
            "inputs": {"image": "qwen_angle_input.png"},
        },
        "111": {
            "class_type": "QwenMultiangleCameraNode",
            "inputs": {
                "image": ["41", 0],
                "horizontal_angle": 0,
                "vertical_angle": 0,
                "zoom": 5.0,
                "default_prompts": True,
                "camera_view": False,
            },
        },
        "106": {
            "class_type": "FluxKontextImageScale",
            "inputs": {"image": ["41", 0]},
        },
        "113": {
            "class_type": "LoaderGGUF",
            "inputs": {
                "gguf_name": r"QwenImage\qwen-image-edit-2511-Q4_K_M.gguf"
            },
        },
        "107": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["113", 0],
                "lora_name": (
                    r"QwenImage\Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors"
                ),
                "strength_model": 1.0,
            },
        },
        "110": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["107", 0],
                "lora_name": (
                    r"QwenImage\qwen-image-edit-2511-multiple-angles-lora.safetensors"
                ),
                "strength_model": 1.0,
            },
        },
        "94": {
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {"model": ["110", 0], "shift": 3.1},
        },
        "98": {
            "class_type": "CFGNorm",
            "inputs": {"model": ["94", 0], "strength": 1.0, "pre_cfg": False},
        },
        "93": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                "type": "qwen_image",
                "device": "default",
            },
        },
        "95": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "qwen_image_vae.safetensors"},
        },
        "103": {
            "class_type": "TextEncodeQwenImageEditPlus",
            "inputs": {
                "clip": ["93", 0],
                "prompt": ["111", 0],
                "vae": ["95", 0],
                "image1": ["106", 0],
            },
        },
        "100": {
            "class_type": "TextEncodeQwenImageEditPlus",
            "inputs": {
                "clip": ["93", 0],
                "prompt": "",
                "vae": ["95", 0],
                "image1": ["106", 0],
            },
        },
        "97": {
            "class_type": "FluxKontextMultiReferenceLatentMethod",
            "inputs": {
                "conditioning": ["103", 0],
                "reference_latents_method": "index_timestep_zero",
            },
        },
        "96": {
            "class_type": "FluxKontextMultiReferenceLatentMethod",
            "inputs": {
                "conditioning": ["100", 0],
                "reference_latents_method": "index_timestep_zero",
            },
        },
        "104": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["106", 0], "vae": ["95", 0]},
        },
        "105": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["98", 0],
                "positive": ["97", 0],
                "negative": ["96", 0],
                "latent_image": ["104", 0],
                "seed": 0,
                "steps": 4,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
            },
        },
        "102": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["105", 0], "vae": ["95", 0]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["102", 0],
                "filename_prefix": "Qwen_multiangle",
            },
        },
    }


def build_ports() -> dict:
    return {
        "preset": PRESET_KEY,
        "workflow_api": f"presets/{API_NAME}.api.json",
        "description": (
            "멀티앵글생성-qwen-image (subgraph flattened): "
            "Qwen-Image-Edit-2511 GGUF + Lightning + Multiple-Angles LoRA + "
            "QwenMultiangleCameraNode"
        ),
        "source_ui": str(SRC).replace("\\", "/"),
        "family": "qwen_angle",
        "ports": {
            "input_image": {
                "node": "41",
                "key": "image",
                "copy_to_input_dir": True,
            },
            "horizontal_angle": {
                "node": "111",
                "key": "horizontal_angle",
                "optional": True,
            },
            "vertical_angle": {
                "node": "111",
                "key": "vertical_angle",
                "optional": True,
            },
            "zoom": {"node": "111", "key": "zoom", "optional": True},
            # Direct prompt override (bypasses multiangle node output if set on 103)
            "positive": {"node": "103", "key": "prompt", "optional": True},
            "seed": {"node": "105", "key": "seed"},
            "steps": {"node": "105", "key": "steps", "optional": True},
            "cfg": {"node": "105", "key": "cfg", "optional": True},
            "denoise": {"node": "105", "key": "denoise", "optional": True},
            "sampler_name": {
                "node": "105",
                "key": "sampler_name",
                "optional": True,
            },
            "scheduler": {"node": "105", "key": "scheduler", "optional": True},
            "lightning_strength": {
                "node": "107",
                "key": "strength_model",
                "optional": True,
            },
            "angles_strength": {
                "node": "110",
                "key": "strength_model",
                "optional": True,
            },
            "gguf_name": {"node": "113", "key": "gguf_name", "optional": True},
            "filename_prefix": {
                "node": "9",
                "key": "filename_prefix",
                "optional": True,
            },
        },
        "defaults": {
            "horizontal_angle": 0,
            "vertical_angle": 0,
            "zoom": 5.0,
            "steps": 4,
            "cfg": 1.0,
            "denoise": 1.0,
            "lightning_strength": 1.0,
            "angles_strength": 1.0,
            "filename_prefix": "Qwen_multiangle",
        },
        "notes": [
            "Source: 멀티앵글생성-qwen-image.json",
            "QwenMultiangleCameraNode emits <sks> … prompts for Angles LoRA",
            "If port positive is set, it overrides linked multiangle prompt on node 103",
            "Agent view keys map to horizontal_angle/vertical_angle/zoom",
        ],
    }


def patch_feature_presets() -> None:
    path = PRESETS / "lonecat_feature_presets.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    presets = data.setdefault("presets", {})
    presets[PRESET_KEY] = {
        "feature_ids": ["qwen_multiangle", "qwen_angle"],
        "file": f"presets/{API_NAME}.api.json",
        "ports": f"presets/{API_NAME}.ports.json",
        "family": "qwen_angle",
        "status": "ready",
        "source_workflow": "멀티앵글생성-qwen-image",
    }
    presets["qwen_angle_2511"] = {
        "alias_of": PRESET_KEY,
        "file": f"presets/{API_NAME}.api.json",
        "ports": f"presets/{API_NAME}.ports.json",
        "family": "qwen_angle",
        "status": "ready",
    }
    sel = data.setdefault("select_preset", {})
    sel["qwen_angle_default"] = PRESET_KEY
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
        "role": "qwen_multiangle",
        "family": "qwen_angle",
        "source": "멀티앵글생성-qwen-image",
        "used_by": [
            "scripts/generate_qwen_angle.py",
            "scripts/character_qwen_turns.py",
        ],
    }
    wfs[PRESET_KEY] = entry
    wfs["qwen_angle_2511"] = dict(entry)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("updated", path)


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
        dest = HUMAN / "멀티앵글생성-qwen-image.json"
        shutil.copy2(SRC, dest)
        print("copied UI →", dest)
    patch_feature_presets()
    patch_catalog()
    print("OK", PRESET_KEY)


if __name__ == "__main__":
    main()
