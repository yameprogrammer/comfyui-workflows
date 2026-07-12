"""LTX 2.3 image+custom-audio SI2V (IA2V) graph builder.

Community path: LTX-2.3 I2V/T2V Basic Custom Audio — encode driving audio into
AV latent, condition first frame on keyframe image, sample distilled GGUF.

Official IC-LoRA LipDub (V2V) needs gated HF weights; not used here.
"""

from __future__ import annotations

from typing import Any

# Local portable inventory (relative to Comfy models/)
DEFAULT_UNET_GGUF = r"LTX2.3\LTX-2.3-22B-distilled-1.1-Q4_K_M.gguf"
DEFAULT_DISTILL_LORA = r"LTX2.3\ltx-2.3-22b-distilled-lora-384.safetensors"
# Align with user All-in-One v44 Power Lora stack (primary distilled dynamic)
AIO_DISTILL_LORA = (
    r"LTX2.3\ltx-2.3-22b-distilled-1.1_lora-dynamic_fro09_avg_rank_111_bf16.safetensors"
)
AIO_DISTILL_LORA_STRENGTH = 0.9
AIO_DEFAULT_FPS = 24.0
# Real AIO UI workflow (agent copy). Runtime uses ltx_aio_workflow_runner + [[P:]] mutes.
AIO_SOURCE_UI_WORKFLOW = (
    r"F:\ComfyUI_workflows\agent_custom\workflows\human"
    r"\ltx23AllInOneWorkflowForRTX_v44.json"
)
AIO_SOURCE_UI_WORKFLOW_IA2V = (
    r"F:\ComfyUI_workflows\agent_custom\workflows\human"
    r"\ltx23AllInOneWorkflowForRTX_v44_IA2V.json"
)
# TE default: fp4 mixed safetensors + DualCLIPLoader.
# GGUF TE (DualClipLoaderGGUF) logs huge "clip missing: vision_model.*" and can thrash
# under --disable-smart-memory; AIO docs also list gemma_3_12B_it_fp4_mixed.
DEFAULT_GEMMA = "gemma_3_12B_it_fp4_mixed.safetensors"
DEFAULT_GEMMA_GGUF = "gemma-3-12b-it-UD-Q4_K_XL.gguf"
DEFAULT_GEMMA_FP8 = "gemma_3_12B_it_fp8_e4m3fn.safetensors"
DEFAULT_TEXT_PROJ = "ltx-2.3_text_projection_bf16.safetensors"
DEFAULT_VIDEO_VAE = "LTX23_video_vae_bf16.safetensors"
DEFAULT_AUDIO_VAE = "LTX23_audio_vae_bf16.safetensors"

# Distilled single-pass sigma schedule (community custom-audio / basic GGUF)
DISTILLED_SIGMAS = "1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0"


# User AIO mode table → agent mode ids ([[P:]] ports via ltx_aio_mode_select)
AIO_MODES = (
    "i2v",  # Image to Video
    "i2v_audio",  # Image + Audio (default SI2V)
    "flf",  # First/Last Frame
    "flf_audio",  # First/Last + Audio
    "fml",  # First/Mid/Last
    "fml_audio",  # First/Mid/Last + Audio
    "v2v",  # Video to Video
    "v2v_audio",  # Video to Video + Audio
    "t2v",  # Text to Video
    "t2v_audio",  # Text + Audio
)

BACKEND_TO_AIO_MODE = {
    "ltx23_ia2v": "i2v_audio",
    "ltx23_aio": "i2v_audio",
    "ltx23_aio_i2v": "i2v",
    "ltx23_aio_flf": "flf",
    "ltx23_aio_flf_audio": "flf_audio",
    "ltx23_aio_fml": "fml",
    "ltx23_aio_fml_audio": "fml_audio",
    "ltx23_aio_v2v": "v2v",
    "ltx23_aio_v2v_audio": "v2v_audio",
    "ltx23_aio_t2v": "t2v",
    "ltx23_aio_t2v_audio": "t2v_audio",
}


def is_ltx_backend(backend: str | None) -> bool:
    b = (backend or "").strip().lower()
    return b == "ltx23_ia2v" or b.startswith("ltx23_aio")


def resolve_aio_mode(backend: str | None, mode: str | None = None) -> str:
    if mode and str(mode).strip():
        m = str(mode).strip().lower().replace("-", "_")
        aliases = {
            "image": "i2v",
            "image_audio": "i2v_audio",
            "image+audio": "i2v_audio",
            "ia2v": "i2v_audio",
            "first_last": "flf",
            "first_last_audio": "flf_audio",
            "first_mid_last": "fml",
            "first_mid_last_audio": "fml_audio",
            "video": "v2v",
            "video_to_video": "v2v",
            "video_audio": "v2v_audio",
            "text": "t2v",
            "text_audio": "t2v_audio",
            "text_to_video": "t2v",
        }
        m = aliases.get(m, m)
        if m not in AIO_MODES:
            raise ValueError(f"unknown aio mode {mode!r}; choose from {AIO_MODES}")
        return m
    b = (backend or "ltx23_aio").strip().lower()
    return BACKEND_TO_AIO_MODE.get(b, "i2v_audio")

DEFAULT_NEG = (
    "blurry, oversaturated, pixelated, low resolution, grainy, distorted, noise, "
    "compression artifacts, jpeg artifacts, glitches, watermark, text, logo, "
    "signature, copyright, subtitles, still image, static, frozen, morphing face, "
    "identity shift, desync mouth"
)


def dual_clip_loader_node(
    gemma: str | None = None,
    text_proj: str | None = None,
) -> dict[str, Any]:
    """DualCLIP loader: GGUF TE → DualClipLoaderGGUF (user AIO); else DualCLIPLoader."""
    g = gemma or DEFAULT_GEMMA
    p = text_proj or DEFAULT_TEXT_PROJ
    if str(g).lower().endswith(".gguf"):
        return {
            "class_type": "DualClipLoaderGGUF",
            "inputs": {
                "clip_name1": g,
                "clip_name2": p,
                "type": "ltxv",
                "device": "default",
            },
        }
    return {
        "class_type": "DualCLIPLoader",
        "inputs": {
            "clip_name1": g,
            "clip_name2": p,
            "type": "ltxv",
            "device": "default",
        },
    }


def snap_ltx_dim(n: int, multiple: int = 32) -> int:
    if n < multiple:
        return multiple
    return max(multiple, int(round(n / multiple) * multiple))


def snap_ltx_frames(n: int) -> int:
    """LTX EmptyLTXVLatentVideo prefers length with step 8; community uses 8k+1."""
    n = max(9, int(n))
    # nearest 8k+1
    base = ((n - 1) // 8) * 8 + 1
    alt = base + 8
    return alt if abs(alt - n) < abs(base - n) else max(9, base)


def build_ltx_custom_audio_api(
    *,
    image_name: str,
    audio_name: str,
    prompt: str,
    negative: str,
    width: int,
    height: int,
    num_frames: int,
    fps: float,
    seed: int,
    cfg: float = 1.0,
    unet_gguf: str = DEFAULT_UNET_GGUF,
    distill_lora: str = DEFAULT_DISTILL_LORA,
    lora_strength: float = 0.6,
    gemma: str = DEFAULT_GEMMA,
    text_proj: str = DEFAULT_TEXT_PROJ,
    video_vae: str = DEFAULT_VIDEO_VAE,
    audio_vae: str = DEFAULT_AUDIO_VAE,
    filename_prefix: str = "agent_ltx_s2v",
    profile: str = "ia2v",
) -> dict[str, Any]:
    """LEGACY mini single-stage LTX I2V+audio graph.

    Prefer ``lib.ltx_aio_workflow_runner.build_aio_switched_api`` (real AIO UI
    workflow + [[P:]] mode switches). Kept only for AGENT_LTX_FORCE_MINI_GRAPH=1.

    profile:
      - ia2v: lighter lora-384 @ 0.6
      - aio:  dynamic distill lora @ 0.9
    """
    width = snap_ltx_dim(width, 32)
    height = snap_ltx_dim(height, 32)
    num_frames = snap_ltx_frames(num_frames)
    fps_i = max(1, int(round(float(fps))))
    neg = (negative or DEFAULT_NEG).strip()
    prof = (profile or "ia2v").strip().lower()
    if prof == "aio":
        if distill_lora == DEFAULT_DISTILL_LORA:
            distill_lora = AIO_DISTILL_LORA
        if abs(float(lora_strength) - 0.6) < 1e-6:
            lora_strength = AIO_DISTILL_LORA_STRENGTH
        if filename_prefix == "agent_ltx_s2v":
            filename_prefix = "agent_ltx_aio"

    api: dict[str, Any] = {
        "1": {
            "class_type": "UnetLoaderGGUF",
            "inputs": {"unet_name": unet_gguf},
        },
        "2": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["1", 0],
                "lora_name": distill_lora,
                "strength_model": float(lora_strength),
            },
        },
        "3": dual_clip_loader_node(gemma, text_proj),
        "4": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": video_vae},
        },
        "5": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": audio_vae},
        },
        "6": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name},
        },
        "7": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["6", 0],
                "upscale_method": "lanczos",
                "width": int(width),
                "height": int(height),
                "crop": "center",
            },
        },
        "8": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["3", 0]},
        },
        "9": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": neg, "clip": ["3", 0]},
        },
        "10": {
            "class_type": "LTXVConditioning",
            "inputs": {
                "positive": ["8", 0],
                "negative": ["9", 0],
                "frame_rate": float(fps),
            },
        },
        "11": {
            "class_type": "EmptyLTXVLatentVideo",
            "inputs": {
                "width": int(width),
                "height": int(height),
                "length": int(num_frames),
                "batch_size": 1,
            },
        },
        "12": {
            "class_type": "LTXVImgToVideoInplace",
            "inputs": {
                "vae": ["4", 0],
                "image": ["7", 0],
                "latent": ["11", 0],
                "strength": 1.0,
                "bypass": False,
            },
        },
        "13": {
            "class_type": "LoadAudio",
            "inputs": {"audio": audio_name},
        },
        "14": {
            "class_type": "LTXVAudioVAEEncode",
            "inputs": {
                "audio": ["13", 0],
                "audio_vae": ["5", 0],
            },
        },
        "15": {
            "class_type": "LTXVConcatAVLatent",
            "inputs": {
                "video_latent": ["12", 0],
                "audio_latent": ["14", 0],
            },
        },
        "16": {
            "class_type": "ManualSigmas",
            "inputs": {"sigmas": DISTILLED_SIGMAS},
        },
        "17": {
            "class_type": "KSamplerSelect",
            "inputs": {"sampler_name": "euler"},
        },
        "18": {
            "class_type": "RandomNoise",
            "inputs": {"noise_seed": int(seed)},
        },
        "19": {
            "class_type": "CFGGuider",
            "inputs": {
                "model": ["2", 0],
                "positive": ["10", 0],
                "negative": ["10", 1],
                "cfg": float(1.0 if cfg is None else cfg),
            },
        },
        "20": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["18", 0],
                "guider": ["19", 0],
                "sampler": ["17", 0],
                "sigmas": ["16", 0],
                "latent_image": ["15", 0],
            },
        },
        "21": {
            "class_type": "LTXVSeparateAVLatent",
            "inputs": {"av_latent": ["20", 0]},
        },
        "22": {
            "class_type": "LTXVTiledVAEDecode",
            "inputs": {
                "vae": ["4", 0],
                "latents": ["21", 0],
                "horizontal_tiles": 1,
                "vertical_tiles": 1,
                "overlap": 1,
                "last_frame_fix": False,
            },
        },
        "23": {
            "class_type": "LTXVAudioVAEDecode",
            "inputs": {
                "samples": ["21", 1],
                "audio_vae": ["5", 0],
            },
        },
        "24": {
            "class_type": "CreateVideo",
            "inputs": {
                "images": ["22", 0],
                "audio": ["23", 0],
                "fps": float(fps),
            },
        },
        "25": {
            "class_type": "SaveVideo",
            "inputs": {
                "video": ["24", 0],
                "filename_prefix": filename_prefix,
                "format": "mp4",
                "codec": "h264",
            },
        },
    }
    # Note: SaveVideo codec path may still emit non-420; agent post-normalize
    # to yuv420p when needed (see generate_s2v ensure_playable_h264).
    return api


def aio_profile_defaults() -> dict[str, Any]:
    """Defaults for --backend ltx23_aio (Image + Audio mode of user AIO table)."""
    return {
        "profile": "aio",
        "unet_gguf": DEFAULT_UNET_GGUF,
        "distill_lora": AIO_DISTILL_LORA,
        "lora_strength": AIO_DISTILL_LORA_STRENGTH,
        "fps": AIO_DEFAULT_FPS,
        "source_ui_workflow": AIO_SOURCE_UI_WORKFLOW,
        "mode_table": "02 Image to Video + Audio input",
        "modes": list(AIO_MODES),
        "backend_aliases": dict(BACKEND_TO_AIO_MODE),
    }


def build_ltx_aio_mode_api(
    *,
    mode: str,
    first_image: str,
    prompt: str,
    negative: str,
    width: int,
    height: int,
    num_frames: int,
    fps: float,
    seed: int,
    audio_name: str | None = None,
    last_image: str | None = None,
    mid_image: str | None = None,
    cfg: float = 1.0,
    unet_gguf: str = DEFAULT_UNET_GGUF,
    distill_lora: str = AIO_DISTILL_LORA,
    lora_strength: float = AIO_DISTILL_LORA_STRENGTH,
    guide_strength: float = 0.9,
    filename_prefix: str = "agent_ltx_aio",
) -> dict[str, Any]:
    """LEGACY mini multi-mode graph (NOT real AIO Orchestrator mute).

    Prefer ``build_aio_switched_api`` which loads the human AIO UI workflow and
    applies [[P:]] port mutes. Kept for AGENT_LTX_FORCE_MINI_GRAPH=1 only.

    Modes: i2v / i2v_audio / flf / flf_audio / fml / fml_audio / v2v
    """
    mode = resolve_aio_mode(None, mode)
    width = snap_ltx_dim(width, 32)
    height = snap_ltx_dim(height, 32)
    num_frames = snap_ltx_frames(num_frames)
    fps_f = float(fps)
    neg = (negative or DEFAULT_NEG).strip()
    use_audio = mode in ("i2v_audio", "flf_audio", "fml_audio") or (
        mode == "v2v" and bool(audio_name)
    )
    if mode == "v2v":
        # Agent V2V = regenerate/continue from provided first_image (last frame of source)
        # Full latent ExtendSampler path deferred; same sampler chain as I2V.
        pass
    if use_audio and not audio_name:
        raise ValueError(f"mode {mode} requires audio_name")
    if mode in ("flf", "flf_audio") and not last_image:
        raise ValueError(f"mode {mode} requires last_image")
    if mode in ("fml", "fml_audio"):
        if not last_image or not mid_image:
            raise ValueError(f"mode {mode} requires mid_image and last_image")

    # Shared loaders + text (node ids stable for meta/debug)
    api: dict[str, Any] = {
        "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": unet_gguf}},
        "2": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["1", 0],
                "lora_name": distill_lora,
                "strength_model": float(lora_strength),
            },
        },
        "3": dual_clip_loader_node(DEFAULT_GEMMA, DEFAULT_TEXT_PROJ),
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": DEFAULT_VIDEO_VAE}},
        "5": {"class_type": "VAELoader", "inputs": {"vae_name": DEFAULT_AUDIO_VAE}},
        "6": {"class_type": "LoadImage", "inputs": {"image": first_image}},
        "7": {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["6", 0],
                "upscale_method": "lanczos",
                "width": int(width),
                "height": int(height),
                "crop": "center",
            },
        },
        "8": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["3", 0]},
        },
        "9": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": neg, "clip": ["3", 0]},
        },
        "10": {
            "class_type": "LTXVConditioning",
            "inputs": {
                "positive": ["8", 0],
                "negative": ["9", 0],
                "frame_rate": fps_f,
            },
        },
        "11": {
            "class_type": "EmptyLTXVLatentVideo",
            "inputs": {
                "width": int(width),
                "height": int(height),
                "length": int(num_frames),
                "batch_size": 1,
            },
        },
        "12": {
            "class_type": "LTXVImgToVideoInplace",
            "inputs": {
                "vae": ["4", 0],
                "image": ["7", 0],
                "latent": ["11", 0],
                "strength": 1.0,
                "bypass": False,
            },
        },
    }

    latent_ref: list[Any] = ["12", 0]
    pos_ref: list[Any] = ["10", 0]
    neg_ref: list[Any] = ["10", 1]
    next_id = 30

    def _add_guide(image_node: str, frame_idx: int) -> None:
        nonlocal next_id, latent_ref, pos_ref, neg_ref, api
        nid = str(next_id)
        next_id += 1
        # scale guide image
        sid = str(next_id)
        next_id += 1
        api[sid] = {
            "class_type": "ImageScale",
            "inputs": {
                "image": [image_node, 0],
                "upscale_method": "lanczos",
                "width": int(width),
                "height": int(height),
                "crop": "center",
            },
        }
        api[nid] = {
            "class_type": "LTXVAddGuide",
            "inputs": {
                "positive": pos_ref,
                "negative": neg_ref,
                "vae": ["4", 0],
                "latent": latent_ref,
                "image": [sid, 0],
                "frame_idx": int(frame_idx),
                "strength": float(guide_strength),
            },
        }
        # AddGuide returns (positive, negative, latent)
        pos_ref = [nid, 0]
        neg_ref = [nid, 1]
        latent_ref = [nid, 2]

    # Optional mid / last stills
    if mode in ("fml", "fml_audio"):
        mid_load = str(next_id)
        next_id += 1
        api[mid_load] = {"class_type": "LoadImage", "inputs": {"image": mid_image}}
        mid_idx = max(1, int(num_frames) // 2)
        _add_guide(mid_load, mid_idx)

    if mode in ("flf", "flf_audio", "fml", "fml_audio"):
        last_load = str(next_id)
        next_id += 1
        api[last_load] = {"class_type": "LoadImage", "inputs": {"image": last_image}}
        last_idx = max(0, int(num_frames) - 1)
        _add_guide(last_load, last_idx)

    # Stable distilled sampler (euler + ManualSigmas). Avoid experimental branches.
    api["16"] = {"class_type": "ManualSigmas", "inputs": {"sigmas": DISTILLED_SIGMAS}}
    api["17"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}}
    api["18"] = {"class_type": "RandomNoise", "inputs": {"noise_seed": int(seed)}}
    api["19"] = {
        "class_type": "CFGGuider",
        "inputs": {
            "model": ["2", 0],
            "positive": pos_ref,
            "negative": neg_ref,
            "cfg": float(1.0 if cfg is None else cfg),
        },
    }

    # Audio branch (stable agent path — not full AIO mute graph):
    # AIO uses TrimAudioDuration so driving audio length matches clip length.
    # Mismatch (audio >> video frames) inflates AV latents and can OOM mid-sample.
    # Encode trimmed audio → ConcatAV → sample; final file uses trimmed track.
    if use_audio:
        # seconds that match EmptyLTXVLatentVideo length @ fps
        audio_dur = max(0.04, float(num_frames) / max(1e-6, fps_f))
        api["13"] = {"class_type": "LoadAudio", "inputs": {"audio": audio_name}}
        # Same role as AIO root TrimAudioDuration (start + duration)
        api["29"] = {
            "class_type": "TrimAudioDuration",
            "inputs": {
                "audio": ["13", 0],
                "start_index": 0.0,
                "duration": float(audio_dur),
            },
        }
        api["14"] = {
            "class_type": "LTXVAudioVAEEncode",
            "inputs": {"audio": ["29", 0], "audio_vae": ["5", 0]},
        }
        api["15"] = {
            "class_type": "LTXVConcatAVLatent",
            "inputs": {
                "video_latent": latent_ref,
                "audio_latent": ["14", 0],
            },
        }
        api["20"] = {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["18", 0],
                "guider": ["19", 0],
                "sampler": ["17", 0],
                "sigmas": ["16", 0],
                "latent_image": ["15", 0],
            },
        }
        api["21"] = {
            "class_type": "LTXVSeparateAVLatent",
            "inputs": {"av_latent": ["20", 0]},
        }
        video_latent_out = ["21", 0]
        use_source_audio_track = True
        source_audio_ref: list[Any] = ["29", 0]  # trimmed
    else:
        # Video-only: sample video latent only (no empty-audio concat — lower VRAM)
        api["20"] = {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["18", 0],
                "guider": ["19", 0],
                "sampler": ["17", 0],
                "sigmas": ["16", 0],
                "latent_image": latent_ref,
            },
        }
        video_latent_out = ["20", 0]
        use_source_audio_track = False
        source_audio_ref = None

    api["22"] = {
        "class_type": "LTXVTiledVAEDecode",
        "inputs": {
            "vae": ["4", 0],
            "latents": video_latent_out,
            "horizontal_tiles": 1,
            "vertical_tiles": 1,
            "overlap": 1,
            "last_frame_fix": False,
        },
    }

    if use_source_audio_track and source_audio_ref is not None:
        api["24"] = {
            "class_type": "CreateVideo",
            "inputs": {
                "images": ["22", 0],
                "audio": source_audio_ref,
                "fps": fps_f,
            },
        }
    else:
        api["24"] = {
            "class_type": "CreateVideo",
            "inputs": {
                "images": ["22", 0],
                "fps": fps_f,
            },
        }

    api["25"] = {
        "class_type": "SaveVideo",
        "inputs": {
            "video": ["24", 0],
            "filename_prefix": f"{filename_prefix}_{mode}",
            "format": "mp4",
            "codec": "h264",
        },
    }
    return api
