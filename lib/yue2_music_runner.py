"""YuE2 Music Generation and Music Cover Runner for AI Agent.

Generates full-length (up to 360s / 6 min) high-fidelity songs and music covers
using M·A·P YuE2 (3B model) with ABC symbolic notation planning and SheetSage2.
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
    DEFAULT_SERVER,
    download_audio,
    extract_first_audio,
    fail_result,
    get_comfy_input_dir,
    ok_result,
    queue_prompt,
    utc_now_iso,
    wait_for_history,
    write_meta,
)

DEFAULT_CKPT = "yue2_3b_int8_convrot.safetensors"
DEFAULT_AUDIO_ENCODER = "sheetsage2_bf16.safetensors"

DEFAULT_STEPS = 32
DEFAULT_CFG = 1.0
DEFAULT_SAMPLER = "dpm_2"
DEFAULT_SCHEDULER = "sgm_uniform"
DEFAULT_DURATION = 120.0
MIN_DURATION = 4.0
MAX_DURATION = 360.0

DEFAULT_STYLE = (
    "female vocals, emotional pop ballad, grand piano, acoustic guitar, strings, "
    "intimate room acoustics, slow tempo, 78 bpm, clean modern studio production"
)

DEFAULT_LYRICS = (
    "[Intro]\n(soft piano intro)\n\n"
    "[Verse 1]\n창밖에 스며든 불빛 사이로\n지나간 시간들이 조용히 머물러\n\n"
    "[Chorus]\n다시 부르는 이 노래 속에\n우리의 기억이 살아 숨쉬어\n\n"
    "[Outro]\n(fading piano melody)"
)


def clamp_duration(duration: float) -> float:
    return max(MIN_DURATION, min(MAX_DURATION, float(duration)))


def build_yue2_text2music_prompt(
    style: str = DEFAULT_STYLE,
    lyrics: str = DEFAULT_LYRICS,
    duration: float = DEFAULT_DURATION,
    seed: int | None = None,
    abc_planning: bool = True,
    abc_mode: str = "full",
    steps: int = DEFAULT_STEPS,
    cfg: float = DEFAULT_CFG,
    sampler: str = DEFAULT_SAMPLER,
    scheduler: str = DEFAULT_SCHEDULER,
    ckpt_name: str = DEFAULT_CKPT,
    filename_prefix: str = "audio/YuE2_Text2Music",
) -> dict[str, Any]:
    """Assemble API prompt graph for YuE2 Text-to-Music generation."""
    if seed is None:
        seed = random.randint(1, 2**31 - 1)

    dur = clamp_duration(duration)
    mode = abc_mode if abc_planning else "off"

    graph: dict[str, Any] = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": ckpt_name,
            },
        },
    }

    if abc_planning and mode != "off":
        graph["2"] = {
            "class_type": "YuE2GenerateABC",
            "inputs": {
                "clip": ["1", 1],
                "style": style,
                "lyrics": lyrics,
                "seed": seed,
                "mode": mode,
                "max_abc_tokens": 8192,
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 30,
                "repetition_penalty": 1.005,
                "penalty_window": 100,
            },
        }
        abc_input: Any = ["2", 0]
        cfg_scale = 1.0
    else:
        abc_input = ""
        cfg_scale = 1.01

    graph["3"] = {
        "class_type": "YuE2GenerateMusic",
        "inputs": {
            "clip": ["1", 1],
            "style": style,
            "lyrics": lyrics,
            "abc": abc_input,
            "seed": seed,
            "mode": "melody" if mode == "melody" else "full",
            "max_duration": dur,
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 100,
            "repetition_penalty": 1.2,
            "cfg_scale": cfg_scale,
        },
    }

    graph["4"] = {
        "class_type": "ConditioningZeroOut",
        "inputs": {
            "conditioning": ["3", 0],
        },
    }

    graph["5"] = {
        "class_type": "EmptyYuE2LatentAudio",
        "inputs": {
            "seconds": ["3", 1],
            "batch_size": 1,
        },
    }

    graph["6"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": ["1", 0],
            "positive": ["3", 0],
            "negative": ["4", 0],
            "latent_image": ["5", 0],
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "denoise": 1.0,
        },
    }

    graph["7"] = {
        "class_type": "VAEDecodeAudio",
        "inputs": {
            "samples": ["6", 0],
            "vae": ["1", 2],
        },
    }

    graph["8"] = {
        "class_type": "SaveAudio",
        "inputs": {
            "audio": ["7", 0],
            "filename_prefix": filename_prefix,
        },
    }

    return graph


def build_yue2_cover_prompt(
    audio_filename: str,
    style: str = DEFAULT_STYLE,
    lyrics: str = DEFAULT_LYRICS,
    duration: float = DEFAULT_DURATION,
    seed: int | None = None,
    mode: str = "melody",
    steps: int = DEFAULT_STEPS,
    cfg: float = DEFAULT_CFG,
    sampler: str = DEFAULT_SAMPLER,
    scheduler: str = DEFAULT_SCHEDULER,
    ckpt_name: str = DEFAULT_CKPT,
    audio_encoder_name: str = DEFAULT_AUDIO_ENCODER,
    filename_prefix: str = "audio/YuE2_MusicCover",
) -> dict[str, Any]:
    """Assemble API prompt graph for YuE2 Music Cover via SheetSage2 transcription."""
    if seed is None:
        seed = random.randint(1, 2**31 - 1)

    dur = clamp_duration(duration)

    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": ckpt_name,
            },
        },
        "2": {
            "class_type": "AudioEncoderLoader",
            "inputs": {
                "audio_encoder_name": audio_encoder_name,
            },
        },
        "3": {
            "class_type": "LoadAudio",
            "inputs": {
                "audio": audio_filename,
            },
        },
        "4": {
            "class_type": "SheetSage2AudioToABC",
            "inputs": {
                "audio_encoder": ["2", 0],
                "audio": ["3", 0],
                "mode": mode,
            },
        },
        "5": {
            "class_type": "YuE2GenerateMusic",
            "inputs": {
                "clip": ["1", 1],
                "style": style,
                "lyrics": lyrics,
                "abc": ["4", 0],
                "seed": seed,
                "mode": mode,
                "max_duration": dur,
                "temperature": 1.0,
                "top_p": 0.95,
                "top_k": 100,
                "repetition_penalty": 1.2,
                "cfg_scale": 1.0,
            },
        },
        "6": {
            "class_type": "ConditioningZeroOut",
            "inputs": {
                "conditioning": ["5", 0],
            },
        },
        "7": {
            "class_type": "EmptyYuE2LatentAudio",
            "inputs": {
                "seconds": ["5", 1],
                "batch_size": 1,
            },
        },
        "8": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["7", 0],
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": 1.0,
            },
        },
        "9": {
            "class_type": "VAEDecodeAudio",
            "inputs": {
                "samples": ["8", 0],
                "vae": ["1", 2],
            },
        },
        "10": {
            "class_type": "SaveAudio",
            "inputs": {
                "audio": ["9", 0],
                "filename_prefix": filename_prefix,
            },
        },
    }


def generate_yue2_music(
    style: str | None = None,
    lyrics: str | None = None,
    audio_path: str | Path | None = None,
    output_path: str | Path | None = None,
    mode: str = "text2music",
    duration: float = DEFAULT_DURATION,
    seed: int | None = None,
    abc_planning: bool = True,
    abc_mode: str = "full",
    steps: int = DEFAULT_STEPS,
    cfg: float = DEFAULT_CFG,
    sampler: str = DEFAULT_SAMPLER,
    scheduler: str = DEFAULT_SCHEDULER,
    ckpt_name: str = DEFAULT_CKPT,
    audio_encoder_name: str = DEFAULT_AUDIO_ENCODER,
    server_url: str = DEFAULT_SERVER,
) -> dict[str, Any]:
    """Execute YuE2 music generation or music cover via ComfyUI."""
    t_start = time.time()
    is_cover = mode.lower() in ("cover", "music_cover", "audio2music")
    actual_style = style or DEFAULT_STYLE
    actual_lyrics = lyrics or DEFAULT_LYRICS
    duration = clamp_duration(duration)

    if is_cover:
        if not audio_path or not os.path.isfile(audio_path):
            return fail_result(
                error="MISSING_AUDIO",
                message=f"Cover mode requires valid input audio path: {audio_path}",
            )
        # Stage reference audio into ComfyUI input directory
        input_dir = Path(get_comfy_input_dir(server_url))
        input_dir.mkdir(parents=True, exist_ok=True)
        src = Path(audio_path).resolve()
        cover_filename = f"yue2_cover_ref_{int(time.time())}_{src.name}"
        staged_path = input_dir / cover_filename
        shutil.copy2(src, staged_path)

        prefix = "audio/YuE2_Cover"
        prompt_graph = build_yue2_cover_prompt(
            audio_filename=cover_filename,
            style=actual_style,
            lyrics=actual_lyrics,
            duration=duration,
            seed=seed,
            mode=abc_mode if abc_mode in ("melody", "full") else "melody",
            steps=steps,
            cfg=cfg,
            sampler=sampler,
            scheduler=scheduler,
            ckpt_name=ckpt_name,
            audio_encoder_name=audio_encoder_name,
            filename_prefix=prefix,
        )
    else:
        prefix = "audio/YuE2_Song"
        prompt_graph = build_yue2_text2music_prompt(
            style=actual_style,
            lyrics=actual_lyrics,
            duration=duration,
            seed=seed,
            abc_planning=abc_planning,
            abc_mode=abc_mode,
            steps=steps,
            cfg=cfg,
            sampler=sampler,
            scheduler=scheduler,
            ckpt_name=ckpt_name,
            filename_prefix=prefix,
        )

    prompt_id = queue_prompt(server_url, prompt_graph)
    history = wait_for_history(server_url, prompt_id, timeout_sec=900.0)

    filename, subfolder, media_type = extract_first_audio(history)
    if not filename:
        return fail_result(
            error="NO_AUDIO",
            message="Execution finished but no output audio extracted from ComfyUI history",
        )

    if output_path is None:
        out_dir = Path("workspace") / "audio"
        out_dir.mkdir(parents=True, exist_ok=True)
        ext = os.path.splitext(filename)[1] or ".flac"
        final_dest = out_dir / f"yue2_{mode}_{int(time.time())}{ext}"
    else:
        final_dest = Path(output_path).resolve()
        final_dest.parent.mkdir(parents=True, exist_ok=True)

    download_audio(
        server_url,
        filename,
        subfolder,
        media_type,
        str(final_dest),
    )

    elapsed = round(time.time() - t_start, 2)
    meta = {
        "generator": "generate_yue2_music",
        "mode": "cover" if is_cover else "text2music",
        "backend": "yue2",
        "checkpoint": ckpt_name,
        "audio_encoder": audio_encoder_name if is_cover else None,
        "style": actual_style,
        "lyrics": actual_lyrics,
        "abc_planning": abc_planning if not is_cover else True,
        "abc_mode": abc_mode,
        "duration_ceiling": duration,
        "steps": steps,
        "cfg": cfg,
        "sampler": sampler,
        "scheduler": scheduler,
        "seed": seed,
        "prompt_id": prompt_id,
        "created_at": utc_now_iso(),
        "elapsed_seconds": elapsed,
    }
    if is_cover and audio_path:
        meta["reference_audio"] = str(audio_path)

    write_meta(str(final_dest) + ".meta.json", meta)

    return ok_result(
        path=str(final_dest),
        output_path=str(final_dest),
        meta_path=str(final_dest) + ".meta.json",
        meta=meta,
        prompt_id=prompt_id,
        elapsed_seconds=elapsed,
        mode="cover" if is_cover else "text2music",
    )
