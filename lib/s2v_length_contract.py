"""SI2V audio–length contract (P0-1).

Prevents silent dialogue cuts when InfiniteTalk/LTX frame caps clamp below
the driving audio length. Fail loud unless explicitly allowed to clamp.

Env:
  AGENT_IT_MAX_FRAMES   default 257 (~10.7s @24fps). Was 129 (~5.4s).
  AGENT_LTX_MAX_FRAMES  default 361
  AGENT_S2V_TAIL_SEC    extra frames after audio (default 0.15)
  AGENT_S2V_ALLOW_CLAMP if 1/true → allow clamp with WARN (old behaviour)
  AGENT_S2V_DRIVE_SLACK_SEC  max |drive−tts| before DRIVE_MISMATCH (default 0.35)
"""

from __future__ import annotations

import math
import os
from typing import Any


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)) or default)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)) or default)
    except ValueError:
        return default


def default_it_max_frames() -> int:
    return _env_int("AGENT_IT_MAX_FRAMES", 257)


def default_ltx_max_frames() -> int:
    return _env_int("AGENT_LTX_MAX_FRAMES", 361)


def default_tail_sec() -> float:
    return max(0.0, _env_float("AGENT_S2V_TAIL_SEC", 0.15))


def allow_clamp() -> bool:
    return _env_bool("AGENT_S2V_ALLOW_CLAMP", False)


def drive_slack_sec() -> float:
    return max(0.0, _env_float("AGENT_S2V_DRIVE_SLACK_SEC", 0.35))


def max_frames_for_backend(backend: str) -> int:
    b = (backend or "").strip().lower()
    if b == "infinitetalk":
        return default_it_max_frames()
    # LTX family
    return default_ltx_max_frames()


def frames_from_duration(
    duration_sec: float,
    fps: float,
    *,
    tail_sec: float | None = None,
    snap_fn=None,
) -> int:
    """ceil(duration*fps) + tail frames; optional snap (IT 4n+1 / LTX)."""
    fps = float(fps) if fps and fps > 0 else 24.0
    tail = default_tail_sec() if tail_sec is None else max(0.0, float(tail_sec))
    dur = max(0.05, float(duration_sec))
    raw = int(math.ceil(dur * fps - 1e-9))
    if tail > 0:
        raw += int(math.ceil(tail * fps))
    raw = max(1, raw)
    if snap_fn is not None:
        return int(snap_fn(raw))
    return raw


def clip_duration_sec(num_frames: int, fps: float) -> float:
    fps = float(fps) if fps and fps > 0 else 24.0
    return float(num_frames) / fps


def apply_frame_cap(
    num_frames: int,
    *,
    backend: str,
    fps: float,
    audio_duration_sec: float | None = None,
    allow_clamp_override: bool | None = None,
) -> dict[str, Any]:
    """
    Enforce max frames. Default: hard fail if needed frames exceed cap.

    Returns:
      ok, num_frames, max_frames, clamped, error?, message?, suggest_split?
    """
    backend = (backend or "").strip().lower()
    max_f = max_frames_for_backend(backend)
    n = int(num_frames)
    min_f = 17 if backend == "infinitetalk" else 1
    if n < min_f:
        n = min_f

    do_clamp = (
        allow_clamp()
        if allow_clamp_override is None
        else bool(allow_clamp_override)
    )

    if n <= max_f:
        return {
            "ok": True,
            "num_frames": n,
            "max_frames": max_f,
            "clamped": False,
            "clip_sec": clip_duration_sec(n, fps),
            "audio_duration_sec": audio_duration_sec,
        }

    clip_need = clip_duration_sec(n, fps)
    cap_sec = clip_duration_sec(max_f, fps)
    msg = (
        f"SI2V needs {n} frames (~{clip_need:.2f}s @ {fps}fps) but "
        f"max for {backend} is {max_f} (~{cap_sec:.2f}s). "
        f"Audio would be cut. Raise AGENT_IT_MAX_FRAMES / AGENT_LTX_MAX_FRAMES, "
        f"split the shot dialogue, or set AGENT_S2V_ALLOW_CLAMP=1 / --allow-clamp "
        f"(not recommended)."
    )
    if audio_duration_sec:
        msg += f" audio_duration={float(audio_duration_sec):.2f}s."

    if do_clamp:
        return {
            "ok": True,
            "num_frames": max_f,
            "max_frames": max_f,
            "clamped": True,
            "clip_sec": cap_sec,
            "audio_duration_sec": audio_duration_sec,
            "warning": msg,
            "suggest_split": True,
        }

    return {
        "ok": False,
        "error": "FRAMES_EXCEED_MAX",
        "message": msg,
        "num_frames": n,
        "max_frames": max_f,
        "clamped": False,
        "clip_sec": clip_need,
        "audio_duration_sec": audio_duration_sec,
        "suggest_split": True,
        "suggest_max_dialogue_sec": round(cap_sec - default_tail_sec(), 2),
    }


def check_drive_vs_tts(
    drive_sec: float | None,
    tts_sec: float | None,
    *,
    slack_sec: float | None = None,
) -> dict[str, Any]:
    """
    Ensure prepared drive length is not shorter than TTS (common demucs shrink).

    drive much longer than tts is OK (silence tail). drive shorter → fail.
    """
    slack = drive_slack_sec() if slack_sec is None else max(0.0, float(slack_sec))
    if drive_sec is None or tts_sec is None:
        return {
            "ok": True,
            "drive_sec": drive_sec,
            "tts_sec": tts_sec,
            "warning": "could_not_compare",
        }
    d, t = float(drive_sec), float(tts_sec)
    shortfall = t - d - slack
    if shortfall > 0:
        return {
            "ok": False,
            "error": "DRIVE_SHORTER_THAN_TTS",
            "drive_sec": d,
            "tts_sec": t,
            "shortfall_sec": shortfall,
            "message": (
                f"driving audio {d:.2f}s is shorter than TTS/dialogue {t:.2f}s "
                f"by ~{shortfall:.2f}s (slack={slack:.2f}). "
                f"Use prepare_mode=center_voicey (not demucs shrink) or re-export TTS."
            ),
        }
    return {
        "ok": True,
        "drive_sec": d,
        "tts_sec": t,
        "shortfall_sec": 0.0,
    }


def recommended_duration_sec(
    drive_sec: float | None,
    tts_sec: float | None,
    *,
    tail_sec: float | None = None,
) -> float | None:
    """shots[].duration_sec suggestion: max(drive,tts)+tail."""
    tail = default_tail_sec() if tail_sec is None else max(0.0, float(tail_sec))
    vals = [v for v in (drive_sec, tts_sec) if v is not None and v > 0]
    if not vals:
        return None
    return round(max(vals) + tail, 3)


def validate_pre_generate(
    *,
    backend: str,
    fps: float,
    drive_path: str | None,
    tts_path: str | None = None,
    num_frames: int | None = None,
    tail_sec: float | None = None,
    allow_clamp_override: bool | None = None,
    snap_fn=None,
) -> dict[str, Any]:
    """
    Full preflight for one SI2V shot.

    Returns ok + fields: drive_sec, tts_sec, num_frames, duration_sec, errors...
    """
    from lib.audio_package import probe_audio_duration

    drive_sec = probe_audio_duration(drive_path) if drive_path else None
    tts_sec = probe_audio_duration(tts_path) if tts_path else None

    cmp = check_drive_vs_tts(drive_sec, tts_sec)
    if not cmp.get("ok"):
        return {
            "ok": False,
            **cmp,
            "drive_sec": drive_sec,
            "tts_sec": tts_sec,
        }

    # Frame count from longest relevant audio
    base_dur = None
    for v in (drive_sec, tts_sec):
        if v is not None:
            base_dur = v if base_dur is None else max(base_dur, v)
    if base_dur is None:
        base_dur = 5.0

    if num_frames is None:
        n = frames_from_duration(base_dur, fps, tail_sec=tail_sec, snap_fn=snap_fn)
    else:
        n = int(num_frames)
        if snap_fn is not None:
            n = int(snap_fn(n))

    cap = apply_frame_cap(
        n,
        backend=backend,
        fps=fps,
        audio_duration_sec=base_dur,
        allow_clamp_override=allow_clamp_override,
    )
    if not cap.get("ok"):
        return {
            "ok": False,
            "drive_sec": drive_sec,
            "tts_sec": tts_sec,
            **cap,
        }

    dur_rec = recommended_duration_sec(drive_sec, tts_sec, tail_sec=tail_sec)
    out = {
        "ok": True,
        "drive_sec": drive_sec,
        "tts_sec": tts_sec,
        "num_frames": cap["num_frames"],
        "max_frames": cap["max_frames"],
        "clamped": cap.get("clamped", False),
        "clip_sec": cap.get("clip_sec"),
        "duration_sec": dur_rec,
        "base_audio_sec": base_dur,
    }
    if cap.get("warning"):
        out["warning"] = cap["warning"]
    if cmp.get("warning"):
        out["compare_warning"] = cmp["warning"]
    return out
