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
DEFAULT_GEMMA = "gemma_3_12B_it_fp8_e4m3fn.safetensors"
DEFAULT_TEXT_PROJ = "ltx-2.3_text_projection_bf16.safetensors"
DEFAULT_VIDEO_VAE = "LTX23_video_vae_bf16.safetensors"
DEFAULT_AUDIO_VAE = "LTX23_audio_vae_bf16.safetensors"

# Distilled single-pass sigma schedule (community custom-audio / basic GGUF)
DISTILLED_SIGMAS = "1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0"

DEFAULT_NEG = (
    "blurry, oversaturated, pixelated, low resolution, grainy, distorted, noise, "
    "compression artifacts, jpeg artifacts, glitches, watermark, text, logo, "
    "signature, copyright, subtitles, still image, static, frozen, morphing face, "
    "identity shift, desync mouth"
)


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
) -> dict[str, Any]:
    """Minimal single-stage LTX distilled I2V + custom audio latent."""
    width = snap_ltx_dim(width, 32)
    height = snap_ltx_dim(height, 32)
    num_frames = snap_ltx_frames(num_frames)
    fps_i = max(1, int(round(float(fps))))
    neg = (negative or DEFAULT_NEG).strip()

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
        "3": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": gemma,
                "clip_name2": text_proj,
                "type": "ltxv",
                "device": "default",
            },
        },
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
                "cfg": float(cfg),
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
    return api
