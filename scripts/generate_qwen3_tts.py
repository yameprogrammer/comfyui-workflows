#!/usr/bin/env python3
"""
Qwen3-TTS generation via local ComfyUI (FB_Qwen3TTS* nodes).

Modes:
  custom  — preset speaker (CustomVoice 1.7B installed) + optional instruct emotion
  design  — natural-language voice design (needs VoiceDesign model)
  clone   — reference audio clone (needs Base model + ref wav)

Community path for lip-sync video:
  TTS wav → prepare_driving → SI2V / LTX audio-conditioned talking avatar
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import random
import shutil
import sys
from typing import Any

from lib.comfy_client import (
    COMFYUI_INPUT_DIR,
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

# Speakers from FB_Qwen3TTSCustomVoice object_info
CUSTOM_SPEAKERS = (
    "Aiden",
    "Dylan",
    "Eric",
    "Ono_anna",
    "Ryan",
    "Serena",
    "Sohee",
    "Uncle_fu",
    "Vivian",
)

LANGUAGES = (
    "Auto",
    "Chinese",
    "English",
    "Japanese",
    "Korean",
    "French",
    "German",
    "Spanish",
    "Portuguese",
    "Russian",
    "Italian",
)


def _build_custom_api(
    *,
    text: str,
    speaker: str,
    language: str,
    instruct: str,
    model_choice: str,
    seed: int,
    max_new_tokens: int,
    filename_prefix: str,
) -> dict[str, Any]:
    return {
        "1": {
            "class_type": "FB_Qwen3TTSCustomVoice",
            "inputs": {
                "text": text,
                "speaker": speaker,
                "model_choice": model_choice,
                "device": "auto",
                "precision": "bf16",
                "language": language,
                "seed": seed,
                "instruct": instruct or "",
                "max_new_tokens": max_new_tokens,
                "top_p": 0.8,
                "top_k": 20,
                "temperature": 0.9,
                "repetition_penalty": 1.05,
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


def _build_design_api(
    *,
    text: str,
    instruct: str,
    language: str,
    model_choice: str,
    seed: int,
    max_new_tokens: int,
    filename_prefix: str,
) -> dict[str, Any]:
    return {
        "1": {
            "class_type": "FB_Qwen3TTSVoiceDesign",
            "inputs": {
                "text": text,
                "instruct": instruct,
                "model_choice": model_choice,
                "device": "auto",
                "precision": "bf16",
                "language": language,
                "seed": seed,
                "max_new_tokens": max_new_tokens,
                "top_p": 0.8,
                "top_k": 20,
                "temperature": 1.0,
                "repetition_penalty": 1.05,
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


def _build_clone_api(
    *,
    text: str,
    ref_audio_name: str,
    ref_text: str,
    language: str,
    model_choice: str,
    seed: int,
    max_new_tokens: int,
    filename_prefix: str,
) -> dict[str, Any]:
    # LoadAudio is standard Comfy for wav/mp3 from input folder
    return {
        "10": {
            "class_type": "LoadAudio",
            "inputs": {"audio": ref_audio_name},
        },
        "1": {
            "class_type": "FB_Qwen3TTSVoiceClone",
            "inputs": {
                "target_text": text,
                "model_choice": model_choice,
                "device": "auto",
                "precision": "bf16",
                "language": language,
                "ref_audio": ["10", 0],
                "ref_text": ref_text or "",
                "seed": seed,
                "max_new_tokens": max_new_tokens,
                "top_p": 0.8,
                "top_k": 20,
                "temperature": 0.9,
                "repetition_penalty": 1.05,
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


def generate_qwen3_tts(
    text: str,
    *,
    mode: str = "custom",
    speaker: str = "Sohee",
    language: str = "Korean",
    instruct: str = "",
    ref_audio: str | None = None,
    ref_text: str = "",
    model_size: str = "1.7B",
    output_filename: str | None = None,
    seed: int | None = None,
    max_new_tokens: int = 2048,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: int = 600,
    meta_out: str | None = None,
) -> dict:
    text = (text or "").strip()
    if not text:
        return fail_result(error="EMPTY_TEXT", message="text required")

    seed = seed if seed is not None else random.randint(1, 2**31 - 1)
    if output_filename is None:
        output_filename = os.path.join(
            r"F:\generated_audio", f"qwen3_tts_{mode}_{seed}.mp3"
        )
    parent = os.path.dirname(os.path.abspath(output_filename))
    if parent:
        os.makedirs(parent, exist_ok=True)

    prefix = f"agent_qwen3_tts_{mode}"
    mode = mode.lower().strip()
    if mode == "custom":
        if speaker not in CUSTOM_SPEAKERS:
            return fail_result(
                error="BAD_SPEAKER",
                message=f"{speaker} not in {CUSTOM_SPEAKERS}",
            )
        api = _build_custom_api(
            text=text,
            speaker=speaker,
            language=language,
            instruct=instruct,
            model_choice=model_size,
            seed=seed,
            max_new_tokens=max_new_tokens,
            filename_prefix=prefix,
        )
    elif mode == "design":
        if not (instruct or "").strip():
            return fail_result(
                error="NEED_INSTRUCT",
                message="voice design requires --instruct description",
            )
        api = _build_design_api(
            text=text,
            instruct=instruct.strip(),
            language=language,
            model_choice=model_size,
            seed=seed,
            max_new_tokens=max_new_tokens,
            filename_prefix=prefix,
        )
    elif mode == "clone":
        if not ref_audio or not os.path.isfile(ref_audio):
            return fail_result(
                error="REF_MISSING",
                message="clone mode needs --ref-audio wav/mp3",
            )
        os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
        temp_name = f"temp_qwen3_tts_ref_{os.getpid()}{os.path.splitext(ref_audio)[1]}"
        shutil.copy2(ref_audio, os.path.join(COMFYUI_INPUT_DIR, temp_name))
        # Clone often uses Base 0.6B/1.7B — default 0.6B is lighter if only that installed
        api = _build_clone_api(
            text=text,
            ref_audio_name=temp_name,
            ref_text=ref_text,
            language=language,
            model_choice=model_size,
            seed=seed,
            max_new_tokens=max_new_tokens,
            filename_prefix=prefix,
        )
    else:
        return fail_result(error="BAD_MODE", message="mode must be custom|design|clone")

    print(f"Qwen3-TTS mode={mode} lang={language} seed={seed}")
    print(f"  text[:120]={text[:120]!r}")
    if instruct:
        print(f"  instruct[:120]={instruct[:120]!r}")
    try:
        prompt_id = queue_prompt(server_address, api)
        print(f"Queued prompt_id={prompt_id}")
    except Exception as e:
        return fail_result(error="QUEUE_FAILED", message=str(e), seed=seed)

    try:
        history_entry = wait_for_history(
            server_address, prompt_id, timeout_sec=timeout_sec
        )
    except Exception as e:
        return fail_result(
            error="HISTORY_FAILED", message=str(e), seed=seed, prompt_id=prompt_id
        )

    try:
        audio_filename, subfolder, media_type = extract_first_audio(history_entry)
    except Exception as e:
        # Dump output keys for debug
        outs = history_entry.get("outputs") or {}
        keys = {nid: list(v.keys()) for nid, v in outs.items() if isinstance(v, dict)}
        return fail_result(
            error="COMFY_NO_AUDIO",
            message=f"{e}; outputs={keys}",
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

    meta_path = resolve_meta_out(output_filename, meta_out)
    meta = {
        "mode": f"qwen3_tts_{mode}",
        "text": text,
        "speaker": speaker if mode == "custom" else None,
        "instruct": instruct or None,
        "language": language,
        "model_size": model_size,
        "seed": seed,
        "ref_audio": os.path.abspath(ref_audio) if ref_audio else None,
        "ref_text": ref_text or None,
        "output_path": os.path.abspath(output_filename),
        "comfy_prompt_id": prompt_id,
        "created_at": utc_now_iso(),
        "si2v_hint": "audio_prepare_driving → audio_bind_driving / episode_s2v",
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
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Qwen3-TTS via ComfyUI (custom/design/clone)")
    p.add_argument("--text", "-t", required=True, help="Text to speak")
    p.add_argument(
        "--mode",
        "-m",
        choices=["custom", "design", "clone"],
        default="custom",
    )
    p.add_argument(
        "--speaker",
        default="Sohee",
        help=f"CustomVoice speaker: {', '.join(CUSTOM_SPEAKERS)}",
    )
    p.add_argument("--language", default="Korean", choices=list(LANGUAGES))
    p.add_argument(
        "--instruct",
        default="",
        help="Emotion/style (custom) or voice design description (design)",
    )
    p.add_argument("--ref-audio", default=None, help="Clone reference wav/mp3")
    p.add_argument("--ref-text", default="", help="Transcript of ref audio (clone)")
    p.add_argument("--model-size", default="1.7B", choices=["0.6B", "1.7B"])
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--max-tokens", type=int, default=2048)
    p.add_argument("--timeout", type=int, default=600)
    args = p.parse_args(argv)

    r = generate_qwen3_tts(
        args.text,
        mode=args.mode,
        speaker=args.speaker,
        language=args.language,
        instruct=args.instruct,
        ref_audio=args.ref_audio,
        ref_text=args.ref_text,
        model_size=args.model_size,
        output_filename=args.output,
        seed=args.seed,
        max_new_tokens=args.max_tokens,
        timeout_sec=args.timeout,
    )
    if not r.get("ok"):
        print(f"[ERROR] {r.get('error')}: {r.get('message')}", file=sys.stderr)
        return 30
    print(f"output={r.get('output_path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
