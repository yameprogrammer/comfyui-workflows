"""Stable Audio 3.0 Execution Runner for AI Agent.

Generates studio-grade 44.1kHz stereo instrumental music,
ambient soundscapes, solo instrument loops, and cinematic SFX sound effects.
"""

from __future__ import annotations

import json
import os
import random
import shutil
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from lib.comfy_client import (
    DEFAULT_SERVER,
    download_audio,
    extract_first_audio,
    fail_result,
    ok_result,
    queue_prompt,
    utc_now_iso,
    wait_for_history,
    write_meta,
)

DEFAULT_CKPT = "stable_audio_3_medium.safetensors"
DEFAULT_CLIP = "t5gemma_b_b_ul2.safetensors"

DEFAULT_INSTRUMENTAL_PROMPT = (
    "Emotional solo grand piano melody, neo-classical, intimate room acoustics, "
    "warm tape warmth, melancholic, 80 BPM, 44.1kHz studio recording"
)

DEFAULT_INSTRUMENTAL_NEGATIVE = "noise, distorted, low quality, harsh frequencies, vocal, speech"

DEFAULT_SFX_PROMPT = (
    "Cinematic heavy explosion with deep sub bass rumble, distant thunder, "
    "debris falling, realistic stereo reverb, 44.1kHz"
)

DEFAULT_SFX_NEGATIVE = "music, voice, speech, singing, melody, low quality, harsh distortion"


def build_stable_audio_api_prompt(
    prompt: str = DEFAULT_INSTRUMENTAL_PROMPT,
    negative_prompt: str = DEFAULT_INSTRUMENTAL_NEGATIVE,
    duration: float = 15.0,
    seed: int | None = None,
    steps: int = 30,
    cfg: float = 6.0,
    sampler: str = "euler",
    scheduler: str = "simple",
    filename_prefix: str = "audio/Stable_Audio_3",
    ckpt_name: str = DEFAULT_CKPT,
    clip_name: str = DEFAULT_CLIP,
) -> dict[str, Any]:
    """Assemble API prompt graph for Stable Audio 3."""
    if seed is None:
        seed = random.randint(1, 2**31 - 1)

    dur = max(1.0, min(90.0, float(duration)))

    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": ckpt_name
            }
        },
        "2": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": clip_name,
                "type": "stable_audio",
                "device": "default"
            }
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["2", 0],
                "text": prompt
            }
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["2", 0],
                "text": negative_prompt
            }
        },
        "5": {
            "class_type": "ConditioningStableAudio",
            "inputs": {
                "positive": ["3", 0],
                "negative": ["4", 0],
                "seconds_start": 0.0,
                "seconds_total": dur
            }
        },
        "6": {
            "class_type": "EmptyLatentAudio",
            "inputs": {
                "seconds": dur,
                "batch_size": 1
            }
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["5", 0],
                "negative": ["5", 1],
                "latent_image": ["6", 0],
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": 1.0
            }
        },
        "8": {
            "class_type": "VAEDecodeAudio",
            "inputs": {
                "samples": ["7", 0],
                "vae": ["1", 2]
            }
        },
        "9": {
            "class_type": "SaveAudio",
            "inputs": {
                "audio": ["8", 0],
                "filename_prefix": filename_prefix
            }
        }
    }


def generate_stable_audio(
    prompt: str | None = None,
    negative_prompt: str | None = None,
    output_path: str | Path | None = None,
    mode: str = "instrumental",
    duration: float = 15.0,
    seed: int | None = None,
    steps: int = 30,
    cfg: float = 6.0,
    sampler: str = "euler",
    scheduler: str = "simple",
    server_url: str = DEFAULT_SERVER,
) -> dict[str, Any]:
    """Generate instrumental music or SFX sound effects via Stable Audio 3.0."""
    t_start = time.time()

    is_sfx = mode.lower() in ("sfx", "effect", "foley", "sound_effect")
    actual_prompt = prompt or (DEFAULT_SFX_PROMPT if is_sfx else DEFAULT_INSTRUMENTAL_PROMPT)
    actual_negative = negative_prompt or (DEFAULT_SFX_NEGATIVE if is_sfx else DEFAULT_INSTRUMENTAL_NEGATIVE)
    prefix = "audio/Stable_Audio_3_SFX" if is_sfx else "audio/Stable_Audio_3_Instrumental"

    prompt_graph = build_stable_audio_api_prompt(
        prompt=actual_prompt,
        negative_prompt=actual_negative,
        duration=duration,
        seed=seed,
        steps=steps,
        cfg=cfg,
        sampler=sampler,
        scheduler=scheduler,
        filename_prefix=prefix,
    )

    prompt_id = queue_prompt(server_url, prompt_graph)
    history = wait_for_history(server_url, prompt_id, timeout_sec=300.0)

    filename, subfolder, media_type = extract_first_audio(history)
    if not filename:
        return fail_result(error="NO_AUDIO", message="Execution finished but no output audio extracted from history")

    if output_path is None:
        out_dir = Path("workspace") / "audio"
        out_dir.mkdir(parents=True, exist_ok=True)
        ext = os.path.splitext(filename)[1] or ".flac"
        final_dest = out_dir / f"stable_audio_{mode}_{int(time.time())}{ext}"
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
        "generator": "generate_stable_audio",
        "mode": "sfx" if is_sfx else "instrumental",
        "backend": "stable_audio_3_medium",
        "prompt": actual_prompt,
        "negative_prompt": actual_negative,
        "duration": duration,
        "steps": steps,
        "cfg": cfg,
        "seed": seed,
        "prompt_id": prompt_id,
        "created_at": utc_now_iso(),
        "elapsed_seconds": elapsed,
    }
    write_meta(str(final_dest) + ".meta.json", meta)

    return ok_result(
        path=str(final_dest),
        output_path=str(final_dest),
        meta_path=str(final_dest) + ".meta.json",
        meta=meta,
        prompt_id=prompt_id,
        elapsed_seconds=elapsed,
        mode="sfx" if is_sfx else "instrumental",
    )
