"""Episode audio stems + production_mode / mix_policy helpers."""

from __future__ import annotations

import os
from typing import Any

# production_mode → default mix_policy / motion_driver
MODE_DEFAULTS: dict[str, dict[str, Any]] = {
    "music_video": {
        "mix_policy": "music_locked",
        "default_motion_driver": "i2v",
        "use_clip_audio": False,
        "bgm_volume": 1.0,
    },
    "story": {
        "mix_policy": "dialogue_sfx_first_bgm_late",
        "default_motion_driver": "i2v",
        "use_clip_audio": False,
        "bgm_volume": 0.28,
    },
    "hybrid": {
        "mix_policy": "layered",
        "default_motion_driver": "i2v",
        "use_clip_audio": False,
        "bgm_volume": 0.3,
    },
    "video_only": {
        "mix_policy": "video_only",
        "default_motion_driver": "i2v",
        "use_clip_audio": False,
        "bgm_volume": 0.35,
    },
}

MIX_POLICIES = (
    "video_only",
    "music_locked",
    "bgm_under",
    "dialogue_sfx_first_bgm_late",
    "layered",
)

MOTION_DRIVERS = ("i2v", "si2v", "still", "flf2v")

STEM_DIRS = ("masters", "music", "dialogue", "vo", "sfx", "beds", "exports")

AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg")


def normalize_production_mode(mode: str | None) -> str:
    m = (mode or "video_only").strip().lower()
    if m in MODE_DEFAULTS:
        return m
    # aliases
    if m in ("mv", "music", "music-video"):
        return "music_video"
    if m in ("drama", "narrative", "film"):
        return "story"
    if m in ("silent", "none", ""):
        return "video_only"
    return "video_only"


def resolve_mix_policy(doc: dict[str, Any]) -> str:
    explicit = doc.get("mix_policy")
    if explicit and str(explicit) in MIX_POLICIES:
        return str(explicit)
    mode = normalize_production_mode(doc.get("production_mode"))
    return str(MODE_DEFAULTS[mode]["mix_policy"])


def resolve_default_motion_driver(doc: dict[str, Any]) -> str:
    if doc.get("default_motion_driver"):
        return str(doc["default_motion_driver"])
    mode = normalize_production_mode(doc.get("production_mode"))
    return str(MODE_DEFAULTS[mode]["default_motion_driver"])


def shot_motion_driver(shot: dict[str, Any], doc: dict[str, Any]) -> str:
    d = shot.get("motion_driver") or resolve_default_motion_driver(doc)
    d = str(d).strip().lower()
    return d if d in MOTION_DRIVERS else "i2v"


def audio_section(doc: dict[str, Any]) -> dict[str, Any]:
    mode = normalize_production_mode(doc.get("production_mode"))
    defaults = MODE_DEFAULTS[mode]
    sec = dict(doc.get("audio") or {})
    if "bgm_volume" not in sec:
        sec["bgm_volume"] = defaults.get("bgm_volume", 0.35)
    if "use_clip_audio" not in sec:
        sec["use_clip_audio"] = defaults.get("use_clip_audio", False)
    if "dialogue_volume" not in sec:
        sec["dialogue_volume"] = 1.0
    if "sfx_volume" not in sec:
        sec["sfx_volume"] = 0.85
    if "vo_volume" not in sec:
        sec["vo_volume"] = 1.0
    return sec


def ensure_audio_dirs(episode_root: str) -> list[str]:
    created = []
    base = os.path.join(episode_root, "audio")
    for name in STEM_DIRS:
        p = os.path.join(base, name)
        if not os.path.isdir(p):
            os.makedirs(p, exist_ok=True)
            created.append(p)
            # keep git placeholder optional
            gk = os.path.join(p, ".gitkeep")
            if not os.path.isfile(gk):
                with open(gk, "w", encoding="utf-8") as f:
                    f.write("")
    return created


def _list_audio_files(folder: str) -> list[str]:
    if not os.path.isdir(folder):
        return []
    out = []
    for name in sorted(os.listdir(folder)):
        low = name.lower()
        if low.startswith("."):
            continue
        if any(low.endswith(ext) for ext in AUDIO_EXTS):
            out.append(os.path.join(folder, name))
    return out


def resolve_path(episode_root: str, rel_or_abs: str | None) -> str | None:
    if not rel_or_abs:
        return None
    p = str(rel_or_abs).strip()
    if not p:
        return None
    if os.path.isabs(p) and os.path.isfile(p):
        return p
    cand = os.path.join(episode_root, p.replace("/", os.sep))
    if os.path.isfile(cand):
        return cand
    return None


def find_master_music(episode_root: str, doc: dict[str, Any]) -> str | None:
    sec = audio_section(doc)
    for key in ("master", "bgm", "music"):
        hit = resolve_path(episode_root, sec.get(key))
        if hit:
            return hit
    for sub in ("masters", "music"):
        files = _list_audio_files(os.path.join(episode_root, "audio", sub))
        if files:
            return files[0]
    return None


def find_bgm(episode_root: str, doc: dict[str, Any]) -> str | None:
    """BGM bed (story late) — prefer music/ over masters/."""
    sec = audio_section(doc)
    hit = resolve_path(episode_root, sec.get("bgm") or sec.get("music"))
    if hit:
        return hit
    files = _list_audio_files(os.path.join(episode_root, "audio", "music"))
    if files:
        return files[0]
    # fallback master only if music_locked style
    return find_master_music(episode_root, doc)


def list_stem_files(episode_root: str, stem: str) -> list[str]:
    return _list_audio_files(os.path.join(episode_root, "audio", stem))


def collect_simple_stems(episode_root: str, doc: dict[str, Any]) -> dict[str, Any]:
    """Flat stem lists for P0 mix (not yet shot-timeline layered)."""
    sec = audio_section(doc)
    return {
        "master": find_master_music(episode_root, doc),
        "bgm": find_bgm(episode_root, doc),
        "dialogue": list_stem_files(episode_root, "dialogue"),
        "vo": list_stem_files(episode_root, "vo"),
        "sfx": list_stem_files(episode_root, "sfx"),
        "volumes": {
            "bgm": float(sec.get("bgm_volume") or 0.35),
            "dialogue": float(sec.get("dialogue_volume") or 1.0),
            "vo": float(sec.get("vo_volume") or 1.0),
            "sfx": float(sec.get("sfx_volume") or 0.85),
        },
        "use_clip_audio": bool(sec.get("use_clip_audio")),
    }


def _parse_ref_item(item: Any) -> dict[str, Any] | None:
    """Normalize audio_refs entry to {path, start_sec, end_sec, at_sec, gain}."""
    if item is None:
        return None
    if isinstance(item, str):
        return {
            "path": item,
            "start_sec": 0.0,
            "end_sec": None,
            "at_sec": 0.0,
            "gain": None,
        }
    if not isinstance(item, dict):
        return None
    path = item.get("path") or item.get("file")
    if not path:
        return None
    return {
        "path": str(path),
        "start_sec": float(item["start_sec"]) if item.get("start_sec") is not None else 0.0,
        "end_sec": float(item["end_sec"]) if item.get("end_sec") is not None else None,
        "at_sec": float(item["at_sec"]) if item.get("at_sec") is not None else 0.0,
        "gain": float(item["gain"]) if item.get("gain") is not None else None,
    }


def resolve_driving_audio(episode_root: str, shot: dict[str, Any]) -> dict[str, Any] | None:
    refs = shot.get("audio_refs") or {}
    if not isinstance(refs, dict):
        return None
    raw = refs.get("driving") or refs.get("dialogue")
    parsed = _parse_ref_item(raw)
    if not parsed:
        return None
    abspath = resolve_path(episode_root, parsed["path"])
    if not abspath:
        return None
    parsed["path"] = abspath
    return parsed


def materialize_driving_audio(
    episode_root: str,
    shot: dict[str, Any],
    *,
    prepare_mode: str = "auto",
    cache_dir: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """
    Resolve shot driving audio, optional time slice, then prep filters → wav path.

    prepare_mode default `auto` → demucs if installed else center_voicey.
    Returns {ok, path, source, prepare_mode, sliced, error?, message?}.
    """
    from lib.ffmpeg_util import prepare_driving_audio, resolve_driving_prep_mode, slice_audio

    sid = str(shot.get("shot_id") or "shot")
    ref = resolve_driving_audio(episode_root, shot)
    if not ref:
        return {
            "ok": False,
            "error": "DRIVING_MISSING",
            "message": f"{sid}: audio_refs.driving|dialogue required",
        }

    src = ref["path"]
    start = float(ref.get("start_sec") or 0.0)
    end = ref.get("end_sec")
    needs_slice = start > 0.001 or end is not None

    out_dir = cache_dir or os.path.join(episode_root, "audio", "exports", "s2v_drive")
    os.makedirs(out_dir, exist_ok=True)
    try:
        mode = resolve_driving_prep_mode(prepare_mode)
    except ValueError as e:
        return {"ok": False, "error": "BAD_MODE", "message": str(e)}
    safe_mode = "".join(c if c.isalnum() or c in "-_" else "_" for c in mode)
    base = f"{sid}_drive_{safe_mode}"
    final_path = os.path.join(out_dir, f"{base}.wav")

    if os.path.isfile(final_path) and not force:
        return {
            "ok": True,
            "path": final_path,
            "source": src,
            "prepare_mode": mode,
            "sliced": needs_slice,
            "cached": True,
        }

    work_src = src
    if needs_slice:
        slice_path = os.path.join(out_dir, f"{sid}_slice_raw.wav")
        if end is not None:
            sr = slice_audio(src, slice_path, start_sec=start, end_sec=float(end))
        else:
            # start only: slice from start through remaining duration via long t
            # Prefer full-file re-encode from start if no end (use remaining).
            # Probe duration loosely: if unknown, skip slice when start==0 already handled.
            import subprocess
            import json as _json

            dur = None
            try:
                out = subprocess.check_output(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-show_entries",
                        "format=duration",
                        "-of",
                        "json",
                        src,
                    ],
                    text=True,
                    timeout=30,
                )
                dur = float(_json.loads(out)["format"]["duration"])
            except Exception:
                dur = None
            if dur is None or dur <= start:
                return {
                    "ok": False,
                    "error": "SLICE_RANGE",
                    "message": f"cannot slice {src} start={start} dur={dur}",
                }
            sr = slice_audio(
                src, slice_path, start_sec=start, duration_sec=max(0.05, dur - start)
            )
        if not sr.get("ok"):
            return {
                "ok": False,
                "error": sr.get("error") or "SLICE_FAILED",
                "message": sr.get("message"),
            }
        work_src = slice_path

    pr = prepare_driving_audio(work_src, final_path, mode=mode)
    if not pr.get("ok"):
        return {
            "ok": False,
            "error": pr.get("error") or "PREP_FAILED",
            "message": pr.get("message"),
        }
    return {
        "ok": True,
        "path": final_path,
        "source": src,
        "prepare_mode": mode,
        "sliced": needs_slice,
        "cached": False,
    }


def collect_timeline_events(
    episode_root: str,
    doc: dict[str, Any],
    *,
    shot_durations: dict[str, float] | None = None,
    include_episode_bgm: bool = True,
) -> list[dict[str, Any]]:
    """
    Build timed audio events for layered mix.

    Each event:
      path, timeline_start_sec, source_start_sec, source_end_sec|None,
      volume, role, shot_id|None
    """
    sec = audio_section(doc)
    vols = {
        "bgm": float(sec.get("bgm_volume") or 0.35),
        "dialogue": float(sec.get("dialogue_volume") or 1.0),
        "vo": float(sec.get("vo_volume") or 1.0),
        "sfx": float(sec.get("sfx_volume") or 0.85),
        "driving": float(sec.get("dialogue_volume") or 1.0),
        "master": 1.0,
    }
    events: list[dict[str, Any]] = []
    t = 0.0
    shots = sorted(doc.get("shots") or [], key=lambda s: s.get("order", 0))

    for shot in shots:
        sid = str(shot.get("shot_id") or "?")
        if shot_durations and sid in shot_durations:
            dur = float(shot_durations[sid])
        else:
            dur = float(shot.get("duration_sec") or 4.0)
        refs = shot.get("audio_refs") if isinstance(shot.get("audio_refs"), dict) else {}

        # single-object refs
        for key, role in (
            ("driving", "driving"),
            ("dialogue", "dialogue"),
            ("vo", "vo"),
            ("music", "music_slice"),
        ):
            parsed = _parse_ref_item(refs.get(key))
            if not parsed:
                continue
            abspath = resolve_path(episode_root, parsed["path"])
            if not abspath:
                continue
            gain = parsed["gain"] if parsed["gain"] is not None else vols.get(role, 1.0)
            if role == "music_slice":
                gain = parsed["gain"] if parsed["gain"] is not None else vols["bgm"]
            events.append(
                {
                    "path": abspath,
                    "timeline_start_sec": t + float(parsed["at_sec"] or 0.0),
                    "source_start_sec": float(parsed["start_sec"] or 0.0),
                    "source_end_sec": parsed["end_sec"],
                    "volume": float(gain),
                    "role": role,
                    "shot_id": sid,
                }
            )

        # sfx list
        sfx_list = refs.get("sfx")
        if sfx_list is None and shot.get("sfx"):
            # textual cues only — no files
            sfx_list = []
        if isinstance(sfx_list, dict):
            sfx_list = [sfx_list]
        for item in sfx_list or []:
            parsed = _parse_ref_item(item)
            if not parsed:
                continue
            abspath = resolve_path(episode_root, parsed["path"])
            if not abspath:
                continue
            gain = parsed["gain"] if parsed["gain"] is not None else vols["sfx"]
            events.append(
                {
                    "path": abspath,
                    "timeline_start_sec": t + float(parsed["at_sec"] or 0.0),
                    "source_start_sec": float(parsed["start_sec"] or 0.0),
                    "source_end_sec": parsed["end_sec"],
                    "volume": float(gain),
                    "role": "sfx",
                    "shot_id": sid,
                }
            )

        t += max(0.01, dur)

    if include_episode_bgm:
        policy = resolve_mix_policy(doc)
        if policy == "music_locked":
            master = find_master_music(episode_root, doc)
            if master:
                # master track full level unless explicitly overridden via audio.master_volume
                mvol = sec.get("master_volume")
                events.append(
                    {
                        "path": master,
                        "timeline_start_sec": 0.0,
                        "source_start_sec": 0.0,
                        "source_end_sec": None,
                        "volume": float(mvol) if mvol is not None else 1.0,
                        "role": "master",
                        "shot_id": None,
                    }
                )
        else:
            bgm = find_bgm(episode_root, doc)
            # avoid double if already placed as music slice events only
            if bgm and not any(e["role"] == "master" for e in events):
                # only add bed if not music_locked-style exclusive elsewhere
                if not any(e["role"] == "master" for e in events):
                    events.append(
                        {
                            "path": bgm,
                            "timeline_start_sec": 0.0,
                            "source_start_sec": 0.0,
                            "source_end_sec": None,
                            "volume": vols["bgm"],
                            "role": "bgm",
                            "shot_id": None,
                        }
                    )

    return events


def audio_readiness(episode_root: str, doc: dict[str, Any]) -> dict[str, Any]:
    """What assemble needs vs what exists."""
    policy = resolve_mix_policy(doc)
    stems = collect_simple_stems(episode_root, doc)
    timeline = collect_timeline_events(episode_root, doc, include_episode_bgm=True)
    missing: list[str] = []
    ready = True
    if policy == "video_only":
        pass
    elif policy in ("music_locked", "bgm_under"):
        if not stems["master"] and not stems["bgm"]:
            missing.append("music or masters track")
            ready = False
    elif policy == "dialogue_sfx_first_bgm_late":
        has_voice = bool(stems["dialogue"] or stems["vo"])
        has_sfx = bool(stems["sfx"])
        has_bgm = bool(stems["bgm"])
        has_tl = bool(timeline)
        if not (has_voice or has_sfx or has_bgm or has_tl):
            missing.append("dialogue/vo/sfx/bgm (at least one stem for story mix)")
            ready = True  # soft fallback to video_only
    elif policy == "layered":
        if not timeline and not any(
            [stems["master"], stems["bgm"], stems["dialogue"], stems["vo"], stems["sfx"]]
        ):
            missing.append("any audio stem or audio_refs for layered mix")

    # si2v shots need driving audio
    si2v_missing = []
    for shot in doc.get("shots") or []:
        if shot_motion_driver(shot, doc) != "si2v":
            continue
        if not resolve_driving_audio(episode_root, shot):
            si2v_missing.append(shot.get("shot_id") or "?")
    if si2v_missing:
        missing.append(f"si2v driving audio for: {', '.join(si2v_missing)}")
        ready = False

    return {
        "mix_policy": policy,
        "production_mode": normalize_production_mode(doc.get("production_mode")),
        "stems": {
            "master": stems["master"],
            "bgm": stems["bgm"],
            "dialogue_n": len(stems["dialogue"]),
            "vo_n": len(stems["vo"]),
            "sfx_n": len(stems["sfx"]),
        },
        "timeline_events": len(timeline),
        "missing": missing,
        "ready": ready,
        "si2v_missing": si2v_missing,
    }
