#!/usr/bin/env python3
"""Export MiniMax → LTX full spatial upscale ComfyUI UI + API workflows."""

from __future__ import annotations

import json
import os
import uuid

UNET = r"LTX2.3\LTX-2.3-22B-distilled-1.1-Q4_K_M.gguf"
IC_LORA = r"LTX2.3\ltx2.3_upscale_ic-lora_06250.safetensors"
SPATIAL = "ltx-2.3-spatial-upscaler-x2-1.1.safetensors"
VIDEO_VAE = "LTX23_video_vae_bf16.safetensors"
AUDIO_VAE = "LTX23_audio_vae_bf16.safetensors"
PROMPT = (
    "high quality, sharp details, clean motion, natural textures, "
    "preserve original composition and identity, crisp anime lines"
)


def inp(name, type_, link=None, widget=None, shape=None):
    d = {"name": name, "type": type_, "link": link}
    if widget:
        d["widget"] = {"name": widget}
    if shape is not None:
        d["shape"] = shape
    return d


def build_ui() -> dict:
    nodes = [
        {
            "id": 1,
            "type": "UnetLoaderGGUF",
            "pos": [40, 200],
            "size": [420, 60],
            "flags": {},
            "order": 0,
            "mode": 0,
            "inputs": [inp("unet_name", "COMBO", widget="unet_name")],
            "outputs": [
                {"name": "MODEL", "type": "MODEL", "links": [], "slot_index": 0}
            ],
            "properties": {"Node name for S&R": "UnetLoaderGGUF"},
            "widgets_values": [UNET],
            "title": "LTX 2.3 Distilled GGUF Q4",
        },
        {
            "id": 2,
            "type": "VAELoaderKJ",
            "pos": [40, 320],
            "size": [420, 110],
            "flags": {},
            "order": 1,
            "mode": 0,
            "inputs": [
                inp("vae_name", "COMBO", widget="vae_name"),
                inp("device", "COMBO", widget="device"),
                inp("weight_dtype", "COMBO", widget="weight_dtype"),
            ],
            "outputs": [{"name": "VAE", "type": "VAE", "links": [], "slot_index": 0}],
            "properties": {"Node name for S&R": "VAELoaderKJ"},
            "widgets_values": [VIDEO_VAE, "main_device", "bf16"],
            "title": "LTX Video VAE",
        },
        {
            "id": 3,
            "type": "VAELoaderKJ",
            "pos": [40, 480],
            "size": [420, 110],
            "flags": {},
            "order": 2,
            "mode": 0,
            "inputs": [
                inp("vae_name", "COMBO", widget="vae_name"),
                inp("device", "COMBO", widget="device"),
                inp("weight_dtype", "COMBO", widget="weight_dtype"),
            ],
            "outputs": [{"name": "VAE", "type": "VAE", "links": [], "slot_index": 0}],
            "properties": {"Node name for S&R": "VAELoaderKJ"},
            "widgets_values": [AUDIO_VAE, "main_device", "bf16"],
            "title": "LTX Audio VAE",
        },
        {
            "id": 4,
            "type": "CRTAutoDLLTX23CLIP",
            "pos": [40, 640],
            "size": [320, 50],
            "flags": {},
            "order": 3,
            "mode": 0,
            "inputs": [],
            "outputs": [{"name": "CLIP", "type": "CLIP", "links": [], "slot_index": 0}],
            "properties": {"Node name for S&R": "CRTAutoDLLTX23CLIP"},
            "widgets_values": [],
            "title": "LTX CLIP (Gemma + projection)",
        },
        {
            "id": 5,
            "type": "LatentUpscaleModelLoader",
            "pos": [40, 740],
            "size": [420, 60],
            "flags": {},
            "order": 4,
            "mode": 0,
            "inputs": [inp("model_name", "COMBO", widget="model_name")],
            "outputs": [
                {
                    "name": "LATENT_UPSCALE_MODEL",
                    "type": "LATENT_UPSCALE_MODEL",
                    "links": [],
                    "slot_index": 0,
                }
            ],
            "properties": {"Node name for S&R": "LatentUpscaleModelLoader"},
            "widgets_values": [SPATIAL],
            "title": "LTX Spatial Upscaler x2",
        },
        {
            "id": 6,
            "type": "LoraLoaderModelOnly",
            "pos": [520, 200],
            "size": [380, 90],
            "flags": {},
            "order": 5,
            "mode": 0,
            "inputs": [
                inp("model", "MODEL"),
                inp("lora_name", "COMBO", widget="lora_name"),
                inp("strength_model", "FLOAT", widget="strength_model"),
            ],
            "outputs": [{"name": "MODEL", "type": "MODEL", "links": [], "slot_index": 0}],
            "properties": {"Node name for S&R": "LoraLoaderModelOnly"},
            "widgets_values": [IC_LORA, 0.75],
            "title": "Upscale IC-LoRA (model_upscale)",
        },
        {
            "id": 7,
            "type": "VHS_LoadVideo",
            "pos": [520, 360],
            "size": [320, 280],
            "flags": {},
            "order": 6,
            "mode": 0,
            "inputs": [
                inp("video", "COMBO", widget="video"),
                inp("force_rate", "FLOAT", widget="force_rate"),
                inp("custom_width", "INT", widget="custom_width"),
                inp("custom_height", "INT", widget="custom_height"),
                inp("frame_load_cap", "INT", widget="frame_load_cap"),
                inp("skip_first_frames", "INT", widget="skip_first_frames"),
                inp("select_every_nth", "INT", widget="select_every_nth"),
                inp("meta_batch", "VHS_BatchManager", shape=7),
                inp("vae", "VAE", shape=7),
                inp("format", "COMBO", widget="format"),
            ],
            "outputs": [
                {"name": "IMAGE", "type": "IMAGE", "links": [], "slot_index": 0},
                {"name": "frame_count", "type": "INT", "links": None, "slot_index": 1},
                {"name": "audio", "type": "AUDIO", "links": [], "slot_index": 2},
                {
                    "name": "video_info",
                    "type": "VHS_VIDEOINFO",
                    "links": None,
                    "slot_index": 3,
                },
            ],
            "properties": {"Node name for S&R": "VHS_LoadVideo"},
            "widgets_values": {
                "video": "i2v_work.mp4",
                "force_rate": 24,
                "custom_width": 0,
                "custom_height": 0,
                "frame_load_cap": 0,
                "skip_first_frames": 0,
                "select_every_nth": 1,
                "format": "LTXV",
                "videopreview": {"hidden": False, "paused": False, "params": {}},
            },
            "title": "Load MiniMax / source video",
        },
        {
            "id": 8,
            "type": "CRT_LTX23USConfig",
            "pos": [920, 360],
            "size": [400, 200],
            "flags": {},
            "order": 7,
            "mode": 0,
            "inputs": [
                inp("prompt", "STRING", widget="prompt"),
                inp("seed", "INT", widget="seed"),
                inp("Image I2V / V2V FirstFrame", "IMAGE", shape=7),
                inp("Video (V2V image batch)", "IMAGE", shape=7),
                inp("V2V Depth (override)", "IMAGE", shape=7),
                inp("source_audio", "AUDIO", shape=7),
            ],
            "outputs": [
                {
                    "name": "LTX23_US_CONFIG_PIPE",
                    "type": "LTX23_US_CONFIG_PIPE",
                    "links": [],
                    "slot_index": 0,
                }
            ],
            "properties": {"Node name for S&R": "CRT_LTX23USConfig"},
            "widgets_values": [PROMPT, 42],
            "title": "Prompt + seed (V2V Upscale config)",
        },
        {
            "id": 9,
            "type": "CRT_LTX23USModelsPipe",
            "pos": [920, 160],
            "size": [380, 200],
            "flags": {},
            "order": 8,
            "mode": 0,
            "inputs": [
                inp("model", "MODEL"),
                inp("vae", "VAE"),
                inp("audio_vae", "VAE"),
                inp("clip", "CLIP"),
                inp("model_union_control", "MODEL", shape=7),
                inp("model_outpaint", "MODEL", shape=7),
                inp("model_upscale", "MODEL", shape=7),
                inp("spatial_upscale_model", "LATENT_UPSCALE_MODEL", shape=7),
                inp("da3_model", "DA3MODEL", shape=7),
                inp("latent_downscale_factor", "FLOAT", widget="latent_downscale_factor"),
            ],
            "outputs": [
                {
                    "name": "LTX23_US_MODELS_PIPE",
                    "type": "LTX23_US_MODELS_PIPE",
                    "links": [],
                    "slot_index": 0,
                }
            ],
            "properties": {"Node name for S&R": "CRT_LTX23USModelsPipe"},
            "widgets_values": [1.0],
            "title": "Models pipe (base + upscale IC-LoRA + spatial)",
        },
        {
            "id": 10,
            "type": "CRT_LTX23UnifiedSampler",
            "pos": [1380, 200],
            "size": [420, 520],
            "flags": {},
            "order": 9,
            "mode": 0,
            "inputs": [
                inp("models_pipe", "LTX23_US_MODELS_PIPE"),
                inp("config_pipe", "LTX23_US_CONFIG_PIPE"),
                inp("workflow_mode", "COMBO", widget="workflow_mode"),
                inp("hq", "BOOLEAN", widget="hq"),
                inp("live_preview", "BOOLEAN", widget="live_preview"),
                inp("frame_count_from_audio", "BOOLEAN", widget="frame_count_from_audio"),
                inp("vae_decode_tiled", "BOOLEAN", widget="vae_decode_tiled"),
                inp(
                    "unload_model_before_vae_decode",
                    "BOOLEAN",
                    widget="unload_model_before_vae_decode",
                ),
                inp("low_vram", "BOOLEAN", widget="low_vram"),
                inp("megapixels_target", "FLOAT", widget="megapixels_target"),
                inp("aspect_ratio", "COMBO", widget="aspect_ratio"),
                inp("frame_count", "INT", widget="frame_count"),
                inp("v2v_mode", "COMBO", widget="v2v_mode"),
                inp("v2v_guide_strength", "FLOAT", widget="v2v_guide_strength"),
                inp("depth_megapixels", "FLOAT", widget="depth_megapixels"),
                inp("v2v_aspect_ratio", "COMBO", widget="v2v_aspect_ratio"),
                inp("sampler_main", "COMBO", widget="sampler_main"),
                inp("sampler_refine", "COMBO", widget="sampler_refine"),
                inp("steps", "INT", widget="steps"),
                inp("generated_audio_gain_db", "FLOAT", widget="generated_audio_gain_db"),
                inp("firstframe_strength", "FLOAT", widget="firstframe_strength"),
                inp("depth_mouth_mask", "BOOLEAN", widget="depth_mouth_mask"),
                inp("mouth_detect_megapixels", "FLOAT", widget="mouth_detect_megapixels"),
                inp("mouth_single_item", "BOOLEAN", widget="mouth_single_item"),
                inp("mouth_detect_chunk_size", "INT", widget="mouth_detect_chunk_size"),
                inp("mouth_mask_expand", "INT", widget="mouth_mask_expand"),
                inp("mouth_mask_blur", "FLOAT", widget="mouth_mask_blur"),
            ],
            "outputs": [
                {"name": "IMAGE", "type": "IMAGE", "links": [], "slot_index": 0},
                {"name": "AUDIO", "type": "AUDIO", "links": [], "slot_index": 1},
            ],
            "properties": {"Node name for S&R": "CRT_LTX23UnifiedSampler"},
            "widgets_values": [
                "V2V",
                False,
                False,
                False,
                False,
                False,
                False,
                1.5,
                "16:9 (Landscape)",
                121,
                "Upscale",
                0.45,
                0.5,
                "16:9 (Landscape)",
                "euler_cfg_pp",
                "euler_cfg_pp",
                4,
                0.0,
                1.0,
                False,
                0.3,
                True,
                8,
                0,
                0.0,
            ],
            "title": "V2V Upscale (spatial + IC-LoRA refine)",
            "color": "#233",
            "bgcolor": "#355",
        },
        {
            "id": 11,
            "type": "VHS_VideoCombine",
            "pos": [1880, 280],
            "size": [320, 300],
            "flags": {},
            "order": 10,
            "mode": 0,
            "inputs": [
                inp("images", "IMAGE"),
                inp("audio", "AUDIO", shape=7),
                inp("meta_batch", "VHS_BatchManager", shape=7),
                inp("vae", "VAE", shape=7),
                inp("frame_rate", "FLOAT", widget="frame_rate"),
                inp("loop_count", "INT", widget="loop_count"),
                inp("filename_prefix", "STRING", widget="filename_prefix"),
                inp("format", "COMBO", widget="format"),
                inp("pingpong", "BOOLEAN", widget="pingpong"),
                inp("save_output", "BOOLEAN", widget="save_output"),
            ],
            "outputs": [
                {
                    "name": "Filenames",
                    "type": "VHS_FILENAMES",
                    "links": None,
                    "slot_index": 0,
                }
            ],
            "properties": {"Node name for S&R": "VHS_VideoCombine"},
            "widgets_values": {
                "frame_rate": 24,
                "loop_count": 0,
                "filename_prefix": "video/MiniMax_LTX_spatial_full",
                "format": "video/h264-mp4",
                "pingpong": False,
                "save_output": True,
                "videopreview": {"hidden": False, "paused": False, "params": {}},
            },
            "title": "Save upscaled video",
        },
        {
            "id": 12,
            "type": "MarkdownNote",
            "pos": [40, -40],
            "size": [900, 200],
            "flags": {},
            "order": 11,
            "mode": 0,
            "inputs": [],
            "outputs": [],
            "properties": {},
            "widgets_values": [
                """## MiniMax → LTX 2.3 Full Spatial Upscale (community quality)

**Pipeline:** low-res video (e.g. MiniMax H3 work 864×480) → LTX spatial x2 + **upscale IC-LoRA refine**

### How to use
1. Copy your source mp4 into Comfy **input** folder
2. Select it on **Load MiniMax / source video**
3. Optional: edit prompt / seed / steps / megapixels_target (1.5 ≈ 1632×896)
4. Queue Prompt

### Defaults (smoke-tested 2026-08-07, RTX 4090)
- UNet: `LTX2.3\\\\LTX-2.3-22B-distilled-1.1-Q4_K_M.gguf`
- Spatial: `ltx-2.3-spatial-upscaler-x2-1.1.safetensors`
- IC-LoRA: `LTX2.3\\\\ltx2.3_upscale_ic-lora_06250.safetensors` @ 0.75
- steps=4 · guide=0.45 · megapixels=1.5 · ~3 min for 5s clip

### Agent CLI
```
python scripts/upscale_ltx_spatial.py -i work.mp4 -o out.mp4 --path full
```
Requires: **ComfyUI-LTXVideo** + **crt-nodes**
"""
            ],
            "title": "README",
            "color": "#222",
            "bgcolor": "#000",
        },
    ]

    by_id = {n["id"]: n for n in nodes}
    links: list = []
    lid = 0

    def wire(src, ss, dst, ds, typ):
        nonlocal lid
        lid += 1
        links.append([lid, src, ss, dst, ds, typ])
        by_id[dst]["inputs"][ds]["link"] = lid
        outs = by_id[src]["outputs"][ss]
        if outs.get("links") is None:
            outs["links"] = []
        outs["links"].append(lid)

    # unet → lora / pipe.model
    wire(1, 0, 6, 0, "MODEL")
    wire(1, 0, 9, 0, "MODEL")
    # lora → pipe.model_upscale (slot 6)
    wire(6, 0, 9, 6, "MODEL")
    wire(2, 0, 9, 1, "VAE")
    wire(3, 0, 9, 2, "VAE")
    wire(4, 0, 9, 3, "CLIP")
    wire(5, 0, 9, 7, "LATENT_UPSCALE_MODEL")
    # LoadVideo IMAGE/AUDIO → Config (slots 3=Video batch, 5=source_audio)
    wire(7, 0, 8, 3, "IMAGE")
    wire(7, 2, 8, 5, "AUDIO")
    wire(9, 0, 10, 0, "LTX23_US_MODELS_PIPE")
    wire(8, 0, 10, 1, "LTX23_US_CONFIG_PIPE")
    wire(10, 0, 11, 0, "IMAGE")
    wire(10, 1, 11, 1, "AUDIO")

    return {
        "id": str(uuid.uuid4()),
        "revision": 0,
        "last_node_id": 12,
        "last_link_id": lid,
        "nodes": nodes,
        "links": links,
        "groups": [
            {
                "id": 1,
                "title": "1) Models",
                "bounding": [20, 140, 480, 700],
                "color": "#3f789e",
                "font_size": 24,
                "flags": {},
            },
            {
                "id": 2,
                "title": "2) Source + config",
                "bounding": [500, 140, 420, 520],
                "color": "#3f789e",
                "font_size": 24,
                "flags": {},
            },
            {
                "id": 3,
                "title": "3) Upscale sampler",
                "bounding": [900, 120, 960, 700],
                "color": "#8A8",
                "font_size": 24,
                "flags": {},
            },
        ],
        "config": {},
        "extra": {
            "ds": {"scale": 0.75, "offset": [80, 80]},
            "frontendVersion": "1.48.6",
            "info": {
                "name": "MiniMax_LTX_Spatial_Full_Upscale",
                "author": "agent_custom",
                "description": "MiniMax low-res → LTX 2.3 spatial x2 + IC-LoRA full upscale",
                "version": "1.0",
            },
        },
        "version": 0.4,
    }


def build_api() -> dict:
    return {
        "1": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {"unet_name": UNET},
        },
        "2": {
            "class_type": "VAELoaderKJ",
            "inputs": {
                "vae_name": VIDEO_VAE,
                "device": "main_device",
                "weight_dtype": "bf16",
            },
        },
        "3": {
            "class_type": "VAELoaderKJ",
            "inputs": {
                "vae_name": AUDIO_VAE,
                "device": "main_device",
                "weight_dtype": "bf16",
            },
        },
        "4": {"class_type": "CRTAutoDLLTX23CLIP", "inputs": {}},
        "5": {
            "class_type": "LatentUpscaleModelLoader",
            "inputs": {"model_name": SPATIAL},
        },
        "6": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["1", 0],
                "lora_name": IC_LORA,
                "strength_model": 0.75,
            },
        },
        "7": {
            "class_type": "VHS_LoadVideo",
            "inputs": {
                "video": "i2v_work.mp4",
                "force_rate": 24.0,
                "custom_width": 0,
                "custom_height": 0,
                "frame_load_cap": 0,
                "skip_first_frames": 0,
                "select_every_nth": 1,
                "format": "LTXV",
            },
        },
        "8": {
            "class_type": "CRT_LTX23USConfig",
            "inputs": {
                "prompt": PROMPT,
                "seed": 42,
                "Video (V2V image batch)": ["7", 0],
                "source_audio": ["7", 2],
            },
        },
        "9": {
            "class_type": "CRT_LTX23USModelsPipe",
            "inputs": {
                "model": ["1", 0],
                "vae": ["2", 0],
                "audio_vae": ["3", 0],
                "clip": ["4", 0],
                "model_upscale": ["6", 0],
                "spatial_upscale_model": ["5", 0],
                "latent_downscale_factor": 1.0,
            },
        },
        "10": {
            "class_type": "CRT_LTX23UnifiedSampler",
            "inputs": {
                "models_pipe": ["9", 0],
                "config_pipe": ["8", 0],
                "workflow_mode": "V2V",
                "hq": False,
                "live_preview": False,
                "frame_count_from_audio": False,
                "vae_decode_tiled": False,
                "unload_model_before_vae_decode": False,
                "low_vram": False,
                "megapixels_target": 1.5,
                "aspect_ratio": "16:9 (Landscape)",
                "frame_count": 121,
                "v2v_mode": "Upscale",
                "v2v_guide_strength": 0.45,
                "depth_megapixels": 0.5,
                "v2v_aspect_ratio": "16:9 (Landscape)",
                "sampler_main": "euler_cfg_pp",
                "sampler_refine": "euler_cfg_pp",
                "steps": 4,
                "generated_audio_gain_db": 0.0,
                "firstframe_strength": 1.0,
                "depth_mouth_mask": False,
                "mouth_detect_megapixels": 0.3,
                "mouth_single_item": True,
                "mouth_detect_chunk_size": 8,
                "mouth_mask_expand": 0,
                "mouth_mask_blur": 0.0,
            },
        },
        "11": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "images": ["10", 0],
                "audio": ["10", 1],
                "frame_rate": 24.0,
                "loop_count": 0,
                "filename_prefix": "video/MiniMax_LTX_spatial_full",
                "format": "video/h264-mp4",
                "pingpong": False,
                "save_output": True,
            },
        },
    }


def main() -> None:
    ui = build_ui()
    api = build_api()
    targets_ui = [
        r"F:\ComfyUI_workflows\agent_custom\workflows\human\minimax_h3\MiniMax_LTX_Spatial_Full_Upscale.json",
        r"F:\ComfyUI_windows_portable\ComfyUI\workflows\MiniMax_LTX_Spatial_Full_Upscale.json",
        r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows\MiniMax_LTX_Spatial_Full_Upscale.json",
    ]
    api_path = r"F:\ComfyUI_workflows\agent_custom\workflows\human\minimax_h3\MiniMax_LTX_Spatial_Full_Upscale.api.json"
    for p in targets_ui:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(ui, f, ensure_ascii=False, indent=2)
        print("UI", p)
    with open(api_path, "w", encoding="utf-8") as f:
        json.dump(api, f, ensure_ascii=False, indent=2)
    print("API", api_path)
    print("nodes", len(ui["nodes"]), "links", len(ui["links"]))


if __name__ == "__main__":
    main()
