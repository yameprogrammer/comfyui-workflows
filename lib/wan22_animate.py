"""
Wan2.2 Animate — character still + RGB dance/ref video → retarget clip.

Validated 2026-08-02 (cross-cast K-pop hook → male idol):
  pose + face crops + CLIP ref + face_strength ≥ 1.2 beats Fun Control / LTX V2V.

Requires ComfyUI-WanVideoWrapper + ComfyUI-WanAnimatePreprocess.
Optional SAM2 not required for the v1 path (mask/bg omitted).
"""

from __future__ import annotations

import os
import shutil
import time
import uuid
from typing import Any

from lib.comfy_client import (
    DEFAULT_SERVER,
    download_image,
    ensure_comfy_running,
    fail_result,
    get_comfy_input_dir,
    get_comfy_output_dir,
    history_execution_error,
    ok_result,
    queue_prompt,
    utc_now_iso,
    wait_for_history,
    write_meta,
)
from lib.ffmpeg_util import run_ffmpeg

DEFAULT_WIDTH = 544
DEFAULT_HEIGHT = 960
DEFAULT_FRAMES = 49
DEFAULT_FPS = 16.0
DEFAULT_STEPS = 8
DEFAULT_CFG = 1.0
DEFAULT_SHIFT = 5.0
DEFAULT_POSE_STRENGTH = 1.0
DEFAULT_FACE_STRENGTH = 1.3
DEFAULT_BLOCK_SWAP = 30
DEFAULT_RETARGET_PADDING = 48

DEFAULT_ANIMATE_MODEL = r"Wan2.2\Wan2.2-Animate-14B-Q4_K.gguf"
DEFAULT_VAE = "wan_2.1_vae.safetensors"
DEFAULT_T5 = "umt5-xxl-enc-bf16.safetensors"
DEFAULT_CLIP_VISION = "clip_vision_h.safetensors"
DEFAULT_LIGHTX = r"Wan2.2\lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank32_bf16.safetensors"
DEFAULT_RELIGHT = r"Wan2.2\WanAnimate_relight_lora_fp16.safetensors"

DEFAULT_NEGATIVE = (
    "still image, slowmotion, blurry, deformed hands, extra fingers, "
    "female face swap, identity change, low quality, watermark, "
    "melted face, wrong person"
)


def stage_to_comfy_input(src: str, name: str | None = None) -> str:
    if not os.path.isfile(src):
        raise FileNotFoundError(src)
    inp = get_comfy_input_dir()
    os.makedirs(inp, exist_ok=True)
    base = name or f"animate_{uuid.uuid4().hex[:10]}{os.path.splitext(src)[1]}"
    shutil.copy2(src, os.path.join(inp, base))
    return base


def prepare_headroom_video(
    video_path: str,
    output_path: str,
    *,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    duration_sec: float | None = 3.8,
    fps: float = DEFAULT_FPS,
    content_height_ratio: float = 0.90,
    top_bias: int = 50,
    timeout_sec: float = 600,
) -> dict[str, Any]:
    """Letterbox RGB dance ref with extra top pad so heads stay in frame."""
    if not os.path.isfile(video_path):
        return fail_result(error="VIDEO_MISSING", message=video_path)
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    inner_h = max(64, int(height * float(content_height_ratio)))
    # scale into inner box, then pad to full canvas with top bias
    vf = (
        f"scale={int(width)}:{inner_h}:force_original_aspect_ratio=decrease,"
        f"pad={int(width)}:{int(height)}:(ow-iw)/2:(oh-ih)/2+{int(top_bias)}:color=0x282830,"
        f"fps={float(fps)}"
    )
    args: list[str] = ["-y", "-i", video_path]
    if duration_sec is not None and float(duration_sec) > 0:
        args.extend(["-t", str(float(duration_sec))])
    args.extend(
        [
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            output_path,
        ]
    )
    r = run_ffmpeg(args, timeout_sec=timeout_sec)
    if r.get("ok") and os.path.isfile(output_path):
        r["output_path"] = os.path.abspath(output_path)
    return r


def prepare_headroom_still(
    image_path: str,
    output_path: str,
    *,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    content_scale: float = 0.88,
    bottom_margin_ratio: float = 0.04,
) -> dict[str, Any]:
    """Bottom-align character still with top headroom on a solid canvas."""
    try:
        from PIL import Image
    except ImportError:
        return fail_result(error="PIL_MISSING", message="Pillow required for headroom still")

    if not os.path.isfile(image_path):
        return fail_result(error="IMAGE_MISSING", message=image_path)
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    src = Image.open(image_path).convert("RGBA")
    max_w = max(64, int(width * 0.92))
    max_h = max(64, int(height * float(content_scale)))
    src.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (int(width), int(height)), (40, 40, 48, 255))
    x = (width - src.width) // 2
    y = height - src.height - int(height * float(bottom_margin_ratio))
    y = max(0, y)
    canvas.paste(src, (x, y), src)
    canvas.convert("RGB").save(output_path, quality=95)
    return ok_result(
        output_path=os.path.abspath(output_path),
        content_size=[src.width, src.height],
        paste_xy=[x, y],
    )


def build_animate_api(
    *,
    video_name: str,
    image_name: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    num_frames: int = DEFAULT_FRAMES,
    force_rate: float = DEFAULT_FPS,
    steps: int = DEFAULT_STEPS,
    cfg: float = DEFAULT_CFG,
    shift: float = DEFAULT_SHIFT,
    seed: int = 42,
    pose_strength: float = DEFAULT_POSE_STRENGTH,
    face_strength: float = DEFAULT_FACE_STRENGTH,
    block_swap: int = DEFAULT_BLOCK_SWAP,
    retarget_padding: int = DEFAULT_RETARGET_PADDING,
    positive: str = "",
    negative: str = "",
    filename_prefix: str = "wan22_animate/dance",
    animate_model: str = DEFAULT_ANIMATE_MODEL,
    vae_name: str = DEFAULT_VAE,
    t5_name: str = DEFAULT_T5,
    clip_name: str = DEFAULT_CLIP_VISION,
    lightx_lora: str = DEFAULT_LIGHTX,
    relight_lora: str = DEFAULT_RELIGHT,
    lightx_strength: float = 1.0,
    relight_strength: float = 1.0,
    use_relight: bool = True,
) -> dict[str, Any]:
    """Comfy API graph: ViTPose + face + CLIP ref → Wan Animate (no SAM2 mask)."""
    neg = negative or DEFAULT_NEGATIVE
    pos = positive or (
        "same character as reference image, full body dance, preserve face identity and outfit, "
        "natural motion, clear hands and feet"
    )

    api: dict[str, Any] = {
        "1": {
            "class_type": "VHS_LoadVideo",
            "inputs": {
                "video": video_name,
                "force_rate": float(force_rate),
                "custom_width": int(width),
                "custom_height": int(height),
                "frame_load_cap": int(num_frames),
                "skip_first_frames": 0,
                "select_every_nth": 1,
                "format": "Wan",
            },
        },
        "2": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "3": {
            "class_type": "ImageResizeKJv2",
            "inputs": {
                "image": ["2", 0],
                "width": int(width),
                "height": int(height),
                "upscale_method": "lanczos",
                "keep_proportion": "pad",
                "pad_color": "40, 40, 48",
                "crop_position": "bottom",
                "divisible_by": 16,
                "device": "cpu",
            },
        },
        "10": {
            "class_type": "OnnxDetectionModelLoader",
            "inputs": {
                "vitpose_model": "vitpose-l-wholebody.onnx",
                "yolo_model": "yolov10m.onnx",
                "onnx_device": "CUDAExecutionProvider",
            },
        },
        "11": {
            "class_type": "PoseAndFaceDetection",
            "inputs": {
                "model": ["10", 0],
                "images": ["1", 0],
                "retarget_image": ["3", 0],
                "width": int(width),
                "height": int(height),
            },
        },
        "12": {
            "class_type": "DrawViTPose",
            "inputs": {
                "pose_data": ["11", 0],
                "width": int(width),
                "height": int(height),
                "retarget_padding": int(retarget_padding),
                "body_stick_width": -1,
                "hand_stick_width": -1,
                "draw_head": True,
            },
        },
        "30": {
            "class_type": "WanVideoVAELoader",
            "inputs": {"model_name": vae_name, "precision": "bf16"},
        },
        "31": {
            "class_type": "WanVideoBlockSwap",
            "inputs": {
                "blocks_to_swap": int(block_swap),
                "offload_img_emb": False,
                "offload_txt_emb": False,
                "use_non_blocking": False,
                "vace_blocks_to_swap": 0,
                "prefetch_blocks": 0,
                "block_swap_debug": False,
            },
        },
        "32": {
            "class_type": "WanVideoModelLoader",
            "inputs": {
                "model": animate_model,
                "base_precision": "fp16",
                "quantization": "disabled",
                "load_device": "offload_device",
                "attention_mode": "sdpa",
                "rms_norm_function": "default",
            },
        },
        "33": {
            "class_type": "WanVideoSetBlockSwap",
            "inputs": {"model": ["32", 0], "block_swap_args": ["31", 0]},
        },
        "34": {
            "class_type": "WanVideoLoraSelect",
            "inputs": {
                "lora": lightx_lora,
                "strength": float(lightx_strength),
                "low_mem_load": False,
                "merge_loras": False,
            },
        },
        "40": {
            "class_type": "LoadWanVideoT5TextEncoder",
            "inputs": {
                "model_name": t5_name,
                "precision": "bf16",
                "load_device": "offload_device",
                "quantization": "disabled",
            },
        },
        "41": {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": clip_name},
        },
        "42": {
            "class_type": "WanVideoClipVisionEncode",
            "inputs": {
                "clip_vision": ["41", 0],
                "image_1": ["3", 0],
                "strength_1": 1.0,
                "strength_2": 1.0,
                "crop": "center",
                "combine_embeds": "average",
                "force_offload": True,
            },
        },
        "50": {
            "class_type": "WanVideoAnimateEmbeds",
            "inputs": {
                "vae": ["30", 0],
                "clip_embeds": ["42", 0],
                "ref_images": ["3", 0],
                "pose_images": ["12", 0],
                "face_images": ["11", 1],
                "width": int(width),
                "height": int(height),
                "num_frames": int(num_frames),
                "force_offload": True,
                "frame_window_size": int(num_frames),
                "colormatch": "disabled",
                "pose_strength": float(pose_strength),
                "face_strength": float(face_strength),
                "tiled_vae": False,
            },
        },
        "51": {
            "class_type": "WanVideoTextEncode",
            "inputs": {
                "t5": ["40", 0],
                "positive_prompt": pos,
                "negative_prompt": neg,
                "force_offload": True,
                "use_disk_cache": False,
                "device": "gpu",
            },
        },
        "60": {
            "class_type": "WanVideoSampler",
            "inputs": {
                "model": ["36", 0],
                "image_embeds": ["50", 0],
                "text_embeds": ["51", 0],
                "steps": int(steps),
                "cfg": float(cfg),
                "shift": float(shift),
                "seed": int(seed),
                "force_offload": True,
                "scheduler": "lcm",
                "riflex_freq_index": 0,
                "denoise_strength": 1.0,
                "batched_cfg": False,
                "rope_function": "comfy",
                "start_step": 0,
                "end_step": -1,
                "add_noise_to_samples": False,
            },
        },
        "61": {
            "class_type": "WanVideoDecode",
            "inputs": {
                "vae": ["30", 0],
                "samples": ["60", 0],
                "enable_vae_tiling": False,
                "tile_x": 272,
                "tile_y": 272,
                "tile_stride_x": 144,
                "tile_stride_y": 128,
                "normalization": "default",
            },
        },
        "70": {
            "class_type": "CreateVideo",
            "inputs": {"images": ["61", 0], "fps": float(force_rate)},
        },
        "71": {
            "class_type": "SaveVideo",
            "inputs": {
                "video": ["70", 0],
                "filename_prefix": filename_prefix,
                "format": "auto",
                "codec": "auto",
            },
        },
    }

    if use_relight and relight_lora:
        api["35"] = {
            "class_type": "WanVideoLoraSelect",
            "inputs": {
                "prev_lora": ["34", 0],
                "lora": relight_lora,
                "strength": float(relight_strength),
                "low_mem_load": False,
                "merge_loras": False,
            },
        }
        api["36"] = {
            "class_type": "WanVideoSetLoRAs",
            "inputs": {"model": ["33", 0], "lora": ["35", 0]},
        }
    else:
        api["36"] = {
            "class_type": "WanVideoSetLoRAs",
            "inputs": {"model": ["33", 0], "lora": ["34", 0]},
        }
    return api


def _extract_video(hist: dict) -> tuple[str, str, str]:
    for _nid, node_out in (hist.get("outputs") or {}).items():
        for key in ("gifs", "videos", "images"):
            items = node_out.get(key)
            if not items:
                continue
            if not isinstance(items, list):
                items = [items]
            for item in items:
                if isinstance(item, dict) and item.get("filename"):
                    return (
                        item["filename"],
                        item.get("subfolder", "") or "",
                        item.get("type", "output") or "output",
                    )
    raise FileNotFoundError(f"No video outputs: {list((hist.get('outputs') or {}).keys())}")


def generate_wan22_animate(
    character_image: str,
    reference_video: str,
    output_path: str,
    *,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    num_frames: int = DEFAULT_FRAMES,
    fps: float = DEFAULT_FPS,
    steps: int = DEFAULT_STEPS,
    cfg: float = DEFAULT_CFG,
    shift: float = DEFAULT_SHIFT,
    seed: int | None = None,
    pose_strength: float = DEFAULT_POSE_STRENGTH,
    face_strength: float = DEFAULT_FACE_STRENGTH,
    block_swap: int = DEFAULT_BLOCK_SWAP,
    retarget_padding: int = DEFAULT_RETARGET_PADDING,
    prompt: str = "",
    negative: str = "",
    headroom: bool = True,
    hook_sec: float | None = 3.8,
    use_relight: bool = True,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: int = 3600,
    meta_out: str | None = None,
    dry_run: bool = False,
    work_dir: str | None = None,
) -> dict[str, Any]:
    """
    Character still + RGB dance/ref video → Wan Animate retarget mp4.

    When headroom=True (default), preprocesses video/still for top margin
    (reduces head crop on tall dance poses).
    """
    if not os.path.isfile(character_image):
        return fail_result(error="SOURCE_MISSING", message=character_image)
    if not os.path.isfile(reference_video):
        return fail_result(error="VIDEO_MISSING", message=reference_video)

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    import tempfile

    td = work_dir or tempfile.mkdtemp(prefix="wan22_animate_")
    os.makedirs(td, exist_ok=True)
    stages: list[dict[str, Any]] = []

    char_path = os.path.abspath(character_image)
    vid_path = os.path.abspath(reference_video)

    if headroom:
        still_hr = os.path.join(td, "char_headroom.png")
        rs = prepare_headroom_still(
            char_path, still_hr, width=width, height=height
        )
        stages.append({"name": "still_headroom", "ok": bool(rs.get("ok"))})
        if not rs.get("ok"):
            return fail_result(
                error=rs.get("error") or "STILL_HEADROOM_FAILED",
                message=rs.get("message"),
                stages=stages,
            )
        char_path = still_hr

        vid_hr = os.path.join(td, "video_headroom.mp4")
        rv = prepare_headroom_video(
            vid_path,
            vid_hr,
            width=width,
            height=height,
            duration_sec=hook_sec,
            fps=fps,
        )
        stages.append({"name": "video_headroom", "ok": bool(rv.get("ok"))})
        if not rv.get("ok"):
            return fail_result(
                error=rv.get("error") or "VIDEO_HEADROOM_FAILED",
                message=rv.get("message"),
                stages=stages,
            )
        vid_path = vid_hr

    seed_i = int(seed if seed is not None else 42)
    api = build_animate_api(
        video_name="__vid__",
        image_name="__img__",
        width=width,
        height=height,
        num_frames=num_frames,
        force_rate=fps,
        steps=steps,
        cfg=cfg,
        shift=shift,
        seed=seed_i,
        pose_strength=pose_strength,
        face_strength=face_strength,
        block_swap=block_swap,
        retarget_padding=retarget_padding,
        positive=prompt,
        negative=negative,
        use_relight=use_relight,
    )

    meta: dict[str, Any] = {
        "tool": "generate_wan22_animate",
        "created_at": utc_now_iso(),
        "character_image": os.path.abspath(character_image),
        "reference_video": os.path.abspath(reference_video),
        "width": width,
        "height": height,
        "num_frames": num_frames,
        "fps": fps,
        "steps": steps,
        "pose_strength": pose_strength,
        "face_strength": face_strength,
        "block_swap": block_swap,
        "headroom": headroom,
        "hook_sec": hook_sec,
        "seed": seed_i,
        "stages": stages,
    }

    if dry_run:
        meta["dry_run"] = True
        meta["api_node_count"] = len(api)
        if meta_out:
            write_meta(meta_out, meta)
        return ok_result(dry_run=True, output_path=None, meta_path=meta_out, **meta)

    ensure_comfy_running(server_address)
    try:
        vname = stage_to_comfy_input(vid_path)
        iname = stage_to_comfy_input(char_path)
    except Exception as e:
        return fail_result(error="STAGE_FAILED", message=str(e), stages=stages)

    api["1"]["inputs"]["video"] = vname
    api["2"]["inputs"]["image"] = iname
    meta["comfy_video"] = vname
    meta["comfy_image"] = iname

    t0 = time.time()
    try:
        prompt_id = queue_prompt(server_address, api)
    except Exception as e:
        return fail_result(error="QUEUE_FAILED", message=str(e), **meta)

    meta["prompt_id"] = prompt_id
    try:
        hist = wait_for_history(server_address, prompt_id, timeout_sec=timeout_sec)
    except Exception as e:
        return fail_result(
            error="WAIT_FAILED", message=str(e), prompt_id=prompt_id, **meta
        )

    err = history_execution_error(hist)
    if err:
        return fail_result(
            error="EXECUTION_ERROR", message=err, prompt_id=prompt_id, **meta
        )

    try:
        fn, sub, typ = _extract_video(hist)
    except Exception as e:
        return fail_result(
            error="EXTRACT_FAILED", message=str(e), prompt_id=prompt_id, **meta
        )

    comfy_out = get_comfy_output_dir(server_address)
    src = os.path.join(comfy_out, sub, fn) if sub else os.path.join(comfy_out, fn)
    try:
        if os.path.isfile(src):
            shutil.copy2(src, output_path)
        else:
            download_image(server_address, fn, sub, typ, output_path)
    except Exception as e:
        return fail_result(error="COPY_FAILED", message=str(e), **meta)

    elapsed = round(time.time() - t0, 1)
    meta.update(
        {
            "ok": True,
            "output_path": os.path.abspath(output_path),
            "elapsed_sec": elapsed,
            "comfy_filename": fn,
            "subfolder": sub,
        }
    )
    if meta_out:
        write_meta(meta_out, meta)
        meta["meta_path"] = meta_out
    return ok_result(**meta)
