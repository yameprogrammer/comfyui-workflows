#!/usr/bin/env python3
"""
Generate BGM / instrumental beds via local ComfyUI.

Primary engine: ACE-Step 1.5 XL turbo (user's audio_ace_step1_5_xl_turbo workflow).
Fallback: SoniloTextToMusic (if available, no large ACE weights).

Outputs mp3/wav suitable for stories/<ep>/audio/music/ and assemble mix_policy.

Model files (ACE) expected under ComfyUI/models:
  diffusion_models/ACESTEP1.5/acestep_v1.5_xl_turbo_bf16.safetensors
  vae/ACESTEP1.5/ace_1.5_vae.safetensors
  text_encoders/ACESTEP1.5/qwen_0.6b_ace15.safetensors
  text_encoders/ACESTEP1.5/qwen_4b_ace15.safetensors
Download: https://huggingface.co/Comfy-Org/ace_step_1.5_ComfyUI_files
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import random
import re
import shutil
import subprocess
import sys
from typing import Any

from lib.comfy_client import (
    DEFAULT_SERVER,
    download_audio,
    extract_first_audio,
    fail_result,
    ok_result,
    queue_prompt,
    resolve_meta_out,
    utc_now_iso,
    wait_for_history,
    write_meta,
)


def _ffmpeg_bin() -> str | None:
    return shutil.which("ffmpeg")


def validate_bgm_audio(path: str) -> dict[str, Any]:
    """Fail hard on silent / full-scale garbage ACE outputs.

    ACE with generate_audio_codes=False often yields constant peak PCM
    (looks like a file, plays as silence/harsh digital hash).
    """
    if not path or not os.path.isfile(path):
        return {"ok": False, "error": "MISSING_FILE", "message": f"no file: {path}"}
    size = os.path.getsize(path)
    if size < 2000:
        return {
            "ok": False,
            "error": "AUDIO_TOO_SMALL",
            "message": f"file only {size} bytes",
            "size": size,
        }

    ff = _ffmpeg_bin()
    if not ff:
        # Cannot deep-validate; accept with warning.
        return {
            "ok": True,
            "warning": "ffmpeg not on PATH; skipped PCM check",
            "size": size,
        }

    try:
        proc = subprocess.run(
            [
                ff,
                "-hide_banner",
                "-nostats",
                "-i",
                path,
                "-af",
                "volumedetect",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except Exception as e:
        return {
            "ok": True,
            "warning": f"volumedetect failed: {e}",
            "size": size,
        }

    log = (proc.stderr or "") + "\n" + (proc.stdout or "")
    mean_m = re.search(r"mean_volume:\s*([-\d.]+)\s*dB", log)
    max_m = re.search(r"max_volume:\s*([-\d.]+)\s*dB", log)
    if not mean_m or not max_m:
        return {
            "ok": True,
            "warning": "could not parse volumedetect",
            "size": size,
            "ffmpeg_tail": log[-400:],
        }

    mean_db = float(mean_m.group(1))
    max_db = float(max_m.group(1))
    stats = {"mean_db": mean_db, "max_db": max_db, "size": size}

    # Near-digital silence
    if max_db <= -50.0:
        return {
            "ok": False,
            "error": "AUDIO_SILENT",
            "message": (
                f"max_volume={max_db} dB (silent). "
                "Regenerate with --audio-codes (default ON)."
            ),
            **stats,
        }

    # Full-scale flat / clipped garbage (ACE without audio codes)
    # Real music: max near 0 is ok but mean is much lower (e.g. -15..-30).
    if max_db >= -0.5 and mean_db >= -3.0:
        return {
            "ok": False,
            "error": "AUDIO_CLIPPED_GARBAGE",
            "message": (
                f"mean={mean_db} dB max={max_db} dB looks like constant full-scale PCM "
                "(not listenable). ACE needs generate_audio_codes=True; do not use "
                "--no-audio-codes. Also free VRAM / restart Comfy if previous run OOMed."
            ),
            **stats,
        }

    return {"ok": True, **stats}

# Paths matching user workflow audio_ace_step1_5_xl_turbo.json
UNET_TURBO = r"ACESTEP1.5\acestep_v1.5_xl_turbo_bf16.safetensors"
UNET_BASE = r"ACESTEP1.5\acestep_v1.5_xl_base_bf16.safetensors"
VAE_NAME = r"ACESTEP1.5\ace_1.5_vae.safetensors"
CLIP_0_6 = r"ACESTEP1.5\qwen_0.6b_ace15.safetensors"
CLIP_4B = r"ACESTEP1.5\qwen_4b_ace15.safetensors"
# Alternate layout used by some helper WFs
UNET_TURBO_ALT = r"AceStep\acestep_v1.5_xl_turbo_bf16.safetensors"

KEYSCALES = [
    "C major",
    "C# major",
    "D major",
    "Eb major",
    "E major",
    "F major",
    "F# major",
    "G major",
    "Ab major",
    "A major",
    "Bb major",
    "B major",
    "C minor",
    "C# minor",
    "D minor",
    "Eb minor",
    "E minor",
    "F minor",
    "F# minor",
    "G minor",
    "Ab minor",
    "A minor",
    "Bb minor",
    "B minor",
]


def _build_ace_api(
    *,
    tags: str,
    lyrics: str,
    seconds: float,
    bpm: int,
    seed: int,
    steps: int,
    cfg: float,
    language: str,
    keyscale: str,
    timesignature: str,
    generate_audio_codes: bool,
    unet_name: str,
    filename_prefix: str,
    aura_shift: float = 3.0,
) -> dict[str, Any]:
    """API graph from audio_ace_step1_5_xl_turbo.json (simplified, no Primitive nodes)."""
    return {
        "104": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": unet_name,
                "weight_dtype": "default",
            },
        },
        "105": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": CLIP_0_6,
                "clip_name2": CLIP_4B,
                "type": "ace",
                "device": "default",
            },
        },
        "106": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": VAE_NAME},
        },
        "78": {
            "class_type": "ModelSamplingAuraFlow",
            "inputs": {
                "model": ["104", 0],
                "shift": aura_shift,
            },
        },
        "94": {
            "class_type": "TextEncodeAceStepAudio1.5",
            "inputs": {
                "clip": ["105", 0],
                "tags": tags,
                "lyrics": lyrics or "",
                "seed": seed,
                "bpm": int(bpm),
                "duration": float(seconds),
                "timesignature": str(timesignature),
                "language": language,
                "keyscale": keyscale,
                "generate_audio_codes": bool(generate_audio_codes),
                # Safer LM sampling defaults:
                # stock top_p=0.9 + fp16 multinomial has been observed to
                # CUDA-assert and kill the whole Comfy process on this box.
                # top_p=1.0 skips nucleus filter; temperature=0 uses argmax.
                "cfg_scale": 2.0,
                "temperature": 0.0,
                "top_p": 1.0,
                "top_k": 0,
                "min_p": 0.0,
            },
        },
        "98": {
            "class_type": "EmptyAceStep1.5LatentAudio",
            "inputs": {
                "seconds": float(seconds),
                "batch_size": 1,
            },
        },
        "47": {
            "class_type": "ConditioningZeroOut",
            "inputs": {"conditioning": ["94", 0]},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["78", 0],
                "positive": ["94", 0],
                "negative": ["47", 0],
                "latent_image": ["98", 0],
                "seed": seed,
                "steps": int(steps),
                "cfg": float(cfg),
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
            },
        },
        "18": {
            "class_type": "VAEDecodeAudio",
            "inputs": {
                "samples": ["3", 0],
                "vae": ["106", 0],
            },
        },
        "107": {
            "class_type": "SaveAudioMP3",
            "inputs": {
                "audio": ["18", 0],
                "filename_prefix": filename_prefix,
                "quality": "V0",
            },
        },
    }


def _build_sonilo_api(
    *,
    prompt: str,
    duration: float,
    seed: int,
    filename_prefix: str,
) -> dict[str, Any]:
    return {
        "1": {
            "class_type": "SoniloTextToMusic",
            "inputs": {
                "prompt": prompt,
                "duration": float(duration),
                "seed": int(seed),
            },
        },
        "2": {
            "class_type": "SaveAudioMP3",
            "inputs": {
                "audio": ["1", 0],
                "filename_prefix": filename_prefix,
                "quality": "V0",
            },
        },
    }


def generate_bgm(
    prompt: str,
    *,
    lyrics: str = "",
    seconds: float = 45.0,
    bpm: int = 90,
    engine: str = "ace",
    profile: str = "turbo",
    seed: int | None = None,
    steps: int | None = None,
    cfg: float | None = None,
    language: str = "en",
    keyscale: str = "A minor",
    timesignature: str = "4",
    instrumental: bool = True,
    generate_audio_codes: bool = True,
    output_filename: str | None = None,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: int = 900,
    meta_out: str | None = None,
) -> dict:
    prompt = (prompt or "").strip()
    if not prompt:
        return fail_result(error="EMPTY_PROMPT", message="prompt required")

    seed = seed if seed is not None else random.randint(1, 2**31 - 1)
    seconds = max(5.0, min(float(seconds), 240.0))
    bpm = max(40, min(int(bpm), 200))

    if instrumental and "no vocal" not in prompt.lower() and "instrumental" not in prompt.lower():
        prompt = (
            f"{prompt.rstrip('.')}. instrumental only, no vocals, no singing, no rap, "
            f"background music bed, clean mix"
        )

    if output_filename is None:
        output_filename = os.path.join(
            r"F:\generated_audio", f"bgm_{engine}_{seed}.mp3"
        )
    parent = os.path.dirname(os.path.abspath(output_filename))
    if parent:
        os.makedirs(parent, exist_ok=True)

    prefix = f"agent_bgm_{engine}"
    engine = engine.lower().strip()

    if engine == "ace":
        if profile == "base":
            unet = UNET_BASE
            steps = steps if steps is not None else 20
            cfg = cfg if cfg is not None else 1.0
        else:
            unet = UNET_TURBO
            steps = steps if steps is not None else 8
            cfg = cfg if cfg is not None else 1.0
        api = _build_ace_api(
            tags=prompt,
            lyrics=lyrics if not instrumental else "",
            seconds=seconds,
            bpm=bpm,
            seed=seed,
            steps=steps,
            cfg=cfg,
            language=language,
            keyscale=keyscale,
            timesignature=timesignature,
            generate_audio_codes=generate_audio_codes,
            unet_name=unet,
            filename_prefix=prefix,
        )
    elif engine == "sonilo":
        steps = steps or 0
        cfg = cfg or 0
        api = _build_sonilo_api(
            prompt=prompt,
            duration=seconds,
            seed=seed,
            filename_prefix=prefix,
        )
    else:
        return fail_result(error="BAD_ENGINE", message="engine must be ace|sonilo")

    print(
        f"BGM engine={engine} profile={profile} sec={seconds} bpm={bpm} "
        f"seed={seed} steps={steps} audio_codes={generate_audio_codes if engine == 'ace' else 'n/a'}"
    )
    print(f"  prompt[:160]={prompt[:160]!r}")

    try:
        prompt_id = queue_prompt(server_address, api)
        print(f"Queued prompt_id={prompt_id}")
    except Exception as e:
        msg = str(e)
        if "value_not_in_list" in msg or "ACESTEP" in msg or "not in list" in msg:
            msg += (
                " | ACE-Step weights missing. Place files under "
                "ComfyUI/models/{diffusion_models,vae,text_encoders}/ACESTEP1.5/ "
                "from https://huggingface.co/Comfy-Org/ace_step_1.5_ComfyUI_files "
                "(see docs/ace_step_bgm_pipeline.md)"
            )
        return fail_result(error="QUEUE_FAILED", message=msg, seed=seed)

    try:
        history_entry = wait_for_history(
            server_address, prompt_id, timeout_sec=timeout_sec
        )
    except Exception as e:
        return fail_result(
            error="HISTORY_FAILED",
            message=str(e),
            seed=seed,
            prompt_id=prompt_id,
        )

    try:
        audio_filename, subfolder, media_type = extract_first_audio(history_entry)
    except Exception as e:
        outs = history_entry.get("outputs") or {}
        keys = {nid: list(v.keys()) for nid, v in outs.items() if isinstance(v, dict)}
        return fail_result(
            error="COMFY_NO_AUDIO",
            message=(
                f"{e}; outputs={keys}. "
                "If ACE models missing, download to models/diffusion_models|vae|text_encoders/ACESTEP1.5/ "
                "from huggingface.co/Comfy-Org/ace_step_1.5_ComfyUI_files"
            ),
            seed=seed,
            prompt_id=prompt_id,
        )

    print(f"Downloading {audio_filename}")
    try:
        download_audio(
            server_address, audio_filename, subfolder, media_type, output_filename
        )
    except Exception as e:
        return fail_result(
            error="DOWNLOAD_FAILED", message=str(e), seed=seed, prompt_id=prompt_id
        )

    check = validate_bgm_audio(output_filename)
    if not check.get("ok"):
        print(
            f"[ERROR] audio validation failed: {check.get('error')}: {check.get('message')}",
            file=sys.stderr,
        )
        return fail_result(
            error=check.get("error") or "AUDIO_INVALID",
            message=check.get("message") or "invalid audio",
            seed=seed,
            prompt_id=prompt_id,
            output_path=os.path.abspath(output_filename),
            audio_stats=check,
        )
    if check.get("warning"):
        print(f"[warn] {check['warning']}")
    else:
        print(
            f"Audio OK mean={check.get('mean_db')} dB max={check.get('max_db')} dB"
        )

    meta_path = resolve_meta_out(output_filename, meta_out)
    meta = {
        "mode": f"bgm_{engine}",
        "profile": profile,
        "prompt": prompt,
        "lyrics": lyrics or None,
        "seconds": seconds,
        "bpm": bpm,
        "seed": seed,
        "steps": steps,
        "cfg": cfg,
        "language": language,
        "keyscale": keyscale,
        "instrumental": instrumental,
        "generate_audio_codes": generate_audio_codes if engine == "ace" else None,
        "audio_stats": {
            k: check[k]
            for k in ("mean_db", "max_db", "size", "warning")
            if k in check
        },
        "output_path": os.path.abspath(output_filename),
        "comfy_prompt_id": prompt_id,
        "created_at": utc_now_iso(),
        "assemble_hint": "place under stories/<ep>/audio/music/ ; mix_policy bgm late",
    }
    if meta_path:
        write_meta(meta_path, meta)
        print(f"Meta saved: {meta_path}")

    print(f"OK {output_filename}")
    return ok_result(
        output_path=os.path.abspath(output_filename),
        seed=seed,
        prompt_id=prompt_id,
        meta_path=meta_path,
        meta=meta,
        audio_stats=check,
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Generate BGM with ACE-Step 1.5 (or Sonilo fallback)"
    )
    p.add_argument(
        "--prompt",
        "-p",
        required=True,
        help="Music style tags / description (ACE tags field)",
    )
    p.add_argument(
        "--lyrics",
        default="",
        help="Optional lyrics (omit for pure BGM; auto-empty if --instrumental)",
    )
    p.add_argument("--seconds", "-d", type=float, default=45.0, help="Duration (default 45)")
    p.add_argument("--bpm", type=int, default=90)
    p.add_argument(
        "--engine",
        choices=["ace", "sonilo"],
        default="ace",
        help="ace = ACE-Step 1.5 (default); sonilo = lightweight fallback",
    )
    p.add_argument(
        "--profile",
        choices=["turbo", "base"],
        default="turbo",
        help="ACE profile: turbo (fast, 8 steps) or base",
    )
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--steps", type=int, default=None)
    p.add_argument("--cfg", type=float, default=None)
    p.add_argument("--language", default="en", help="ACE lyric language code (en/ko/…)")
    p.add_argument("--keyscale", default="A minor")
    p.add_argument("--timesignature", default="4", choices=["2", "3", "4", "6"])
    p.add_argument(
        "--with-vocals",
        action="store_true",
        help="Allow vocals (default instrumental BGM only)",
    )
    p.add_argument(
        "--audio-codes",
        dest="audio_codes",
        action="store_true",
        default=True,
        help="ACE generate_audio_codes (default ON; quality critical)",
    )
    p.add_argument(
        "--no-audio-codes",
        dest="audio_codes",
        action="store_false",
        help="Disable audio codes (usually worse / can yield silence)",
    )
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--timeout", type=int, default=900)
    args = p.parse_args(argv)

    r = generate_bgm(
        args.prompt,
        lyrics=args.lyrics,
        seconds=args.seconds,
        bpm=args.bpm,
        engine=args.engine,
        profile=args.profile,
        seed=args.seed,
        steps=args.steps,
        cfg=args.cfg,
        language=args.language,
        keyscale=args.keyscale,
        timesignature=args.timesignature,
        instrumental=not args.with_vocals,
        generate_audio_codes=args.audio_codes,
        output_filename=args.output,
        timeout_sec=args.timeout,
    )
    if not r.get("ok"):
        print(f"[ERROR] {r.get('error')}: {r.get('message')}", file=sys.stderr)
        return 30
    print(f"output={r.get('output_path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
