"""MiniMax Music 3 Execution Runner for AI Agent.

Generates full-length (up to 5 min / 300s), high-fidelity (32kHz stereo)
vocal songs and instrumental soundtracks using MiniMax Music 3.
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

DEFAULT_DIT = "minimax_music3_dit_fp16.safetensors"
DEFAULT_TEXT_ENCODER = "minimax_music3_text_encoder_pruned_int8_convrot.safetensors"
DEFAULT_VAE = "minimax_music3_dav.safetensors"

DEFAULT_SONG_CAPTION = (
    "Global Metadata: Upbeat energetic Synthwave K-Pop track. 124 BPM, A minor. "
    "Bright sparkling synth arpeggios, driving sub bass, polished modern studio production.\n\n"
    "Vocal Details: Clear charismatic female vocal, bright tone, confident delivery with airy harmonies.\n\n"
    "Arrangement: Punchy kick drum, crisp snare on 2 and 4, 80s synth brass, shimmering hi-hats."
)

DEFAULT_SONG_LYRICS = (
    "[Intro]\nYeah, let's go!\nLight up the neon sky!\n\n"
    "[Verse 1]\nMidnight city, feel the beat\nDancing down the electric street\n\n"
    "[Chorus]\nShine bright, we are unstoppable!\nFeel the rhythm, it's a miracle!"
)

DEFAULT_BGM_CAPTION = (
    "Global Metadata: Cinematic Cyberpunk Lo-fi BGM, instrumental soundtrack only. 90 BPM, D minor. "
    "Moody, atmospheric, nostalgic neon night vibes, deep sub bass, smooth electric piano chords.\n\n"
    "Vocal Details: Instrumental only, strictly no human voice, no vocals, pure soundtrack.\n\n"
    "Arrangement: Analog synth pads, warm Rhodes piano, gentle vinyl crackle, subtle hi-hats."
)

DEFAULT_BGM_LYRICS = "[Intro]\n(rain and vinyl crackle)\n\n[Instrumental]\n\n[Outro]\n(fading piano echoes)"


def build_music3_api_prompt(
    caption: str = DEFAULT_SONG_CAPTION,
    lyrics: str = DEFAULT_SONG_LYRICS,
    duration: float = 60.0,
    seed: int | None = None,
    steps: int = 35,
    cfg: float = 4.0,
    sampler: str = "euler",
    scheduler: str = "simple",
    filename_prefix: str = "audio/MiniMax_Music3",
    dit_model: str = DEFAULT_DIT,
    text_encoder: str = DEFAULT_TEXT_ENCODER,
    vae_model: str = DEFAULT_VAE,
) -> dict[str, Any]:
    """Assemble API graph for MiniMax Music 3."""
    if seed is None:
        seed = random.randint(1, 2**31 - 1)

    # Clamp duration (4s to 300s)
    dur = max(4.0, min(300.0, float(duration)))

    return {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": dit_model,
                "weight_dtype": "default"
            }
        },
        "2": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": text_encoder,
                "type": "minimax",
                "device": "default"
            }
        },
        "3": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": vae_model
            }
        },
        "4": {
            "class_type": "MiniMaxMusic3TextEncode",
            "inputs": {
                "clip": ["2", 0],
                "caption": caption,
                "lyrics": lyrics,
                "seed": seed,
                "max_duration": dur,
                "cfg_scale": 1.5,
                "top_k": 50
            }
        },
        "5": {
            "class_type": "EmptyMiniMaxMusic3LatentAudio",
            "inputs": {
                "seconds": ["4", 1],
                "batch_size": 1
            }
        },
        "6": {
            "class_type": "ConditioningZeroOut",
            "inputs": {
                "conditioning": ["4", 0]
            }
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["4", 0],
                "negative": ["6", 0],
                "latent_image": ["5", 0],
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
                "vae": ["3", 0]
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


def generate_minimax_music(
    caption: str | None = None,
    lyrics: str | None = None,
    output_path: str | Path | None = None,
    mode: str = "song",
    duration: float = 60.0,
    seed: int | None = None,
    steps: int = 35,
    cfg: float = 4.0,
    sampler: str = "euler",
    scheduler: str = "simple",
    server_url: str = DEFAULT_SERVER,
) -> dict[str, Any]:
    """Generate vocal songs or BGM via MiniMax Music 3."""
    t_start = time.time()

    is_bgm = mode.lower() in ("bgm", "instrumental", "soundtrack")
    actual_caption = caption or (DEFAULT_BGM_CAPTION if is_bgm else DEFAULT_SONG_CAPTION)
    actual_lyrics = lyrics or (DEFAULT_BGM_LYRICS if is_bgm else DEFAULT_SONG_LYRICS)
    prefix = "audio/MiniMax_Music3_BGM" if is_bgm else "audio/MiniMax_Music3_Song"

    prompt_graph = build_music3_api_prompt(
        caption=actual_caption,
        lyrics=actual_lyrics,
        duration=duration,
        seed=seed,
        steps=steps,
        cfg=cfg,
        sampler=sampler,
        scheduler=scheduler,
        filename_prefix=prefix,
    )

    prompt_id = queue_prompt(server_url, prompt_graph)
    history = wait_for_history(server_url, prompt_id, timeout_sec=600.0)

    # Extract audio output from history
    filename, subfolder, media_type = extract_first_audio(history)
    if not filename:
        return fail_result(error="NO_AUDIO", message="Execution finished but no output audio extracted from history")

    # Determine destination path
    if output_path is None:
        out_dir = Path("workspace") / "audio"
        out_dir.mkdir(parents=True, exist_ok=True)
        ext = os.path.splitext(filename)[1] or ".flac"
        final_dest = out_dir / f"minimax_{mode}_{int(time.time())}{ext}"
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
        "generator": "generate_minimax_music",
        "mode": "bgm" if is_bgm else "song",
        "backend": "minimax_music3",
        "caption": actual_caption,
        "lyrics": actual_lyrics,
        "duration_target": duration,
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
        mode="bgm" if is_bgm else "song",
    )
