#!/usr/bin/env python3
"""
Qwen3-TTS generation via local ComfyUI (FB_Qwen3TTS* nodes).

Modes:
  custom  — preset speaker + instruct emotion/style (CustomVoice model)
  design  — natural-language voice design (VoiceDesign model; auto-download)
  clone   — reference audio clone (Base model; auto-download) — your voice or others

Tuning awkward / unnatural delivery:
  --temperature  --top-p  --top-k  --repetition-penalty  --seed  --instruct
  shorter text lines, accurate --ref-text for clone, 5–15s clean ref audio

Community path for lip-sync:
  TTS wav → prepare_driving → episode_s2v (LTX / InfiniteTalk)
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

# Voice library for clone profiles (your voice / talent samples)
VOICES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "voices"
)


def resolve_voice_profile(voice_id: str) -> dict[str, Any] | None:
    """Load voices/<id>/voice.json if present."""
    path = os.path.join(VOICES_DIR, voice_id, "voice.json")
    if not os.path.isfile(path):
        return None
    import json

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _sampling_inputs(
    *,
    seed: int,
    max_new_tokens: int,
    top_p: float,
    top_k: int,
    temperature: float,
    repetition_penalty: float,
) -> dict[str, Any]:
    return {
        "seed": seed,
        "max_new_tokens": max_new_tokens,
        "top_p": top_p,
        "top_k": top_k,
        "temperature": temperature,
        "repetition_penalty": repetition_penalty,
    }


def _build_custom_api(
    *,
    text: str,
    speaker: str,
    language: str,
    instruct: str,
    model_choice: str,
    seed: int,
    max_new_tokens: int,
    top_p: float,
    top_k: int,
    temperature: float,
    repetition_penalty: float,
    filename_prefix: str,
) -> dict[str, Any]:
    inputs = {
        "text": text,
        "speaker": speaker,
        "model_choice": model_choice,
        "device": "auto",
        "precision": "bf16",
        "language": language,
        "instruct": instruct or "",
        **_sampling_inputs(
            seed=seed,
            max_new_tokens=max_new_tokens,
            top_p=top_p,
            top_k=top_k,
            temperature=temperature,
            repetition_penalty=repetition_penalty,
        ),
    }
    return {
        "1": {"class_type": "FB_Qwen3TTSCustomVoice", "inputs": inputs},
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
    top_p: float,
    top_k: int,
    temperature: float,
    repetition_penalty: float,
    filename_prefix: str,
) -> dict[str, Any]:
    inputs = {
        "text": text,
        "instruct": instruct,
        "model_choice": model_choice,
        "device": "auto",
        "precision": "bf16",
        "language": language,
        **_sampling_inputs(
            seed=seed,
            max_new_tokens=max_new_tokens,
            top_p=top_p,
            top_k=top_k,
            temperature=temperature,
            repetition_penalty=repetition_penalty,
        ),
    }
    return {
        "1": {"class_type": "FB_Qwen3TTSVoiceDesign", "inputs": inputs},
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
    top_p: float,
    top_k: int,
    temperature: float,
    repetition_penalty: float,
    filename_prefix: str,
) -> dict[str, Any]:
    inputs = {
        "target_text": text,
        "model_choice": model_choice,
        "device": "auto",
        "precision": "bf16",
        "language": language,
        "ref_audio": ["10", 0],
        "ref_text": ref_text or "",
        **_sampling_inputs(
            seed=seed,
            max_new_tokens=max_new_tokens,
            top_p=top_p,
            top_k=top_k,
            temperature=temperature,
            repetition_penalty=repetition_penalty,
        ),
    }
    return {
        "10": {
            "class_type": "LoadAudio",
            "inputs": {"audio": ref_audio_name},
        },
        "1": {"class_type": "FB_Qwen3TTSVoiceClone", "inputs": inputs},
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
    voice_id: str | None = None,
    model_size: str = "1.7B",
    output_filename: str | None = None,
    seed: int | None = None,
    max_new_tokens: int = 2048,
    top_p: float = 0.8,
    top_k: int = 20,
    temperature: float = 0.9,
    repetition_penalty: float = 1.05,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: int = 600,
    meta_out: str | None = None,
) -> dict:
    text = (text or "").strip()
    if not text:
        return fail_result(error="EMPTY_TEXT", message="text required")

    # Resolve registered voice profile for clone convenience
    if voice_id:
        prof = resolve_voice_profile(voice_id)
        if not prof:
            return fail_result(
                error="VOICE_MISSING",
                message=f"voices/{voice_id}/voice.json not found — run voice_register.py",
            )
        mode = "clone"
        ref_audio = prof.get("ref_audio")
        if ref_audio and not os.path.isabs(ref_audio):
            ref_audio = os.path.join(VOICES_DIR, voice_id, ref_audio)
        ref_text = ref_text or (prof.get("ref_text") or "")
        language = language if language != "Auto" else (prof.get("language") or language)
        if prof.get("default_instruct") and not instruct:
            instruct = str(prof["default_instruct"])

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

    # Clone/design often need their own checkpoints; FB nodes download on first use
    if mode == "clone" and model_size == "1.7B":
        # CustomVoice-only installs still download Base when clone runs
        pass

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
            top_p=top_p,
            top_k=top_k,
            temperature=temperature,
            repetition_penalty=repetition_penalty,
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
            top_p=top_p,
            top_k=top_k,
            temperature=temperature,
            repetition_penalty=repetition_penalty,
            filename_prefix=prefix,
        )
    elif mode == "clone":
        if not ref_audio or not os.path.isfile(ref_audio):
            return fail_result(
                error="REF_MISSING",
                message=(
                    "clone needs --ref-audio wav/mp3 (5–15s clean speech) "
                    "or --voice-id registered profile"
                ),
            )
        os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
        ext = os.path.splitext(ref_audio)[1] or ".wav"
        temp_name = f"temp_qwen3_tts_ref_{os.getpid()}{ext}"
        shutil.copy2(ref_audio, os.path.join(COMFYUI_INPUT_DIR, temp_name))
        # Base model: 0.6B lighter first-time; 1.7B better quality if VRAM allows
        api = _build_clone_api(
            text=text,
            ref_audio_name=temp_name,
            ref_text=ref_text,
            language=language,
            model_choice=model_size,
            seed=seed,
            max_new_tokens=max_new_tokens,
            top_p=top_p,
            top_k=top_k,
            temperature=temperature,
            repetition_penalty=repetition_penalty,
            filename_prefix=prefix,
        )
    else:
        return fail_result(error="BAD_MODE", message="mode must be custom|design|clone")

    print(f"Qwen3-TTS mode={mode} lang={language} seed={seed} temp={temperature}")
    print(f"  text[:120]={text[:120]!r}")
    if instruct:
        print(f"  instruct[:120]={instruct[:120]!r}")
    if mode == "clone":
        print(f"  ref={ref_audio} ref_text_len={len(ref_text or '')}")
        print("  note: first clone run may download Base model into models/Qwen3-TTS/")

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
        "voice_id": voice_id,
        "instruct": instruct or None,
        "language": language,
        "model_size": model_size,
        "seed": seed,
        "top_p": top_p,
        "top_k": top_k,
        "temperature": temperature,
        "repetition_penalty": repetition_penalty,
        "ref_audio": os.path.abspath(ref_audio) if ref_audio else None,
        "ref_text": ref_text or None,
        "output_path": os.path.abspath(output_filename),
        "comfy_prompt_id": prompt_id,
        "created_at": utc_now_iso(),
        "si2v_hint": "audio_prepare_driving → episode_tts --bind-si2v / episode_s2v",
        "tune_hint": (
            "awkward? try lower temperature (0.6–0.8), shorter lines, "
            "clearer instruct, or clone with 5–15s clean ref + ref_text"
        ),
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
    p = argparse.ArgumentParser(
        description="Qwen3-TTS custom / design / clone (tunable sampling)"
    )
    p.add_argument("--text", "-t", required=True)
    p.add_argument("--mode", "-m", choices=["custom", "design", "clone"], default="custom")
    p.add_argument("--speaker", default="Sohee", help=f"custom: {', '.join(CUSTOM_SPEAKERS)}")
    p.add_argument("--language", default="Korean", choices=list(LANGUAGES))
    p.add_argument("--instruct", default="", help="Emotion/style or voice design text")
    p.add_argument("--ref-audio", default=None, help="Clone: 5–15s clean speech sample")
    p.add_argument("--ref-text", default="", help="Clone: exact transcript of ref audio")
    p.add_argument(
        "--voice-id",
        default=None,
        help="Registered clone profile under voices/<id>/ (implies mode=clone)",
    )
    p.add_argument("--model-size", default="1.7B", choices=["0.6B", "1.7B"])
    p.add_argument("--output", "-o", default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--max-tokens", type=int, default=2048)
    p.add_argument(
        "--temperature",
        type=float,
        default=0.9,
        help="Lower (0.6–0.8) = more stable; higher = more expressive/risky",
    )
    p.add_argument("--top-p", type=float, default=0.8)
    p.add_argument("--top-k", type=int, default=20)
    p.add_argument(
        "--repetition-penalty",
        type=float,
        default=1.05,
        help="Raise slightly (1.1–1.2) if loops/awkward repeats",
    )
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
        voice_id=args.voice_id,
        model_size=args.model_size,
        output_filename=args.output,
        seed=args.seed,
        max_new_tokens=args.max_tokens,
        top_p=args.top_p,
        top_k=args.top_k,
        temperature=args.temperature,
        repetition_penalty=args.repetition_penalty,
        timeout_sec=args.timeout,
    )
    if not r.get("ok"):
        print(f"[ERROR] {r.get('error')}: {r.get('message')}", file=sys.stderr)
        return 30
    print(f"output={r.get('output_path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
