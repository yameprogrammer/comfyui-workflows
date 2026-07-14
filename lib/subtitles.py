"""Episode SRT generation + soft burn-in helpers (P2-2).

Timeline is shot-order cumulative duration using work-clip length when present,
else shots[].duration_sec. Only shots with non-empty dialogue/vo become cues.
"""

from __future__ import annotations

import os
import re
from typing import Any

from lib.audio_package import probe_audio_duration
from lib.one_take import work_clip_path
from lib.story_package import StoryPackage


def _fmt_ts(sec: float) -> str:
    if sec < 0:
        sec = 0.0
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    if ms >= 1000:
        s += 1
        ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _dialogue_text(shot: dict) -> str:
    for key in ("dialogue", "vo", "subtitle", "caption"):
        t = (shot.get(key) or "").strip()
        if t:
            return t
    return ""


def _shot_media_duration(story: StoryPackage, shot: dict) -> float:
    sid = str(shot.get("shot_id") or "")
    clip = work_clip_path(story, shot, sid)
    if os.path.isfile(clip):
        d = probe_audio_duration(clip)
        if d and d > 0.05:
            return float(d)
    try:
        return max(0.1, float(shot.get("duration_sec") or 3.0))
    except (TypeError, ValueError):
        return 3.0


def build_cues(
    story: StoryPackage,
    *,
    shots: list[dict] | None = None,
    pad_end_sec: float = 0.05,
    min_cue_sec: float = 0.4,
) -> list[dict[str, Any]]:
    """Return [{index, shot_id, start, end, text}, ...] in timeline order."""
    ordered = shots or sorted(story.shots(), key=lambda s: s.get("order", 0))
    t = 0.0
    cues: list[dict[str, Any]] = []
    idx = 1
    for shot in ordered:
        dur = _shot_media_duration(story, shot)
        text = _dialogue_text(shot)
        if text:
            start = t
            end = max(start + min_cue_sec, t + dur - pad_end_sec)
            # wrap long lines roughly at 18 chars for vertical shorts
            text_fmt = _wrap_ko(text, width=16)
            cues.append(
                {
                    "index": idx,
                    "shot_id": shot.get("shot_id"),
                    "start": start,
                    "end": end,
                    "text": text_fmt,
                    "raw_text": text,
                }
            )
            idx += 1
        t += dur
    return cues


def _wrap_ko(text: str, width: int = 16) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    if len(text) <= width:
        return text
    lines: list[str] = []
    buf = ""
    for ch in text:
        buf += ch
        if len(buf) >= width and ch in (" ", "，", ",", "。", ".", "!", "?", "…", "요", "다", "죠"):
            lines.append(buf.strip())
            buf = ""
        elif len(buf) >= width + 4:
            lines.append(buf.strip())
            buf = ""
    if buf.strip():
        lines.append(buf.strip())
    return "\n".join(lines) if lines else text


def cues_to_srt(cues: list[dict[str, Any]]) -> str:
    blocks = []
    for c in cues:
        blocks.append(
            f"{c['index']}\n"
            f"{_fmt_ts(float(c['start']))} --> {_fmt_ts(float(c['end']))}\n"
            f"{c['text']}\n"
        )
    return "\n".join(blocks).rstrip() + ("\n" if blocks else "")


def write_episode_srt(
    story: StoryPackage,
    *,
    out_path: str | None = None,
    shots: list[dict] | None = None,
) -> dict[str, Any]:
    cues = build_cues(story, shots=shots)
    srt = cues_to_srt(cues)
    if out_path is None:
        out_path = story.path("exports", "final", f"{story.episode_id}.srt")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig") as f:
        f.write(srt)
    return {
        "ok": True,
        "path": os.path.abspath(out_path),
        "cue_count": len(cues),
        "cues": cues,
    }


def burn_subtitles(
    video_in: str,
    srt_path: str,
    video_out: str,
    *,
    font_size: int = 22,
    margin_v: int = 80,
    timeout_sec: float = 600,
) -> dict[str, Any]:
    """Soft-burn SRT with ffmpeg subtitles filter (libass)."""
    from lib.ffmpeg_util import run_ffmpeg

    if not os.path.isfile(video_in):
        return {"ok": False, "error": "VIDEO_MISSING", "message": video_in}
    if not os.path.isfile(srt_path):
        return {"ok": False, "error": "SRT_MISSING", "message": srt_path}

    # Escape path for subtitles filter on Windows
    srt_esc = srt_path.replace("\\", "/").replace(":", "\\:")
    # force_style: white text, black outline, bottom center — shorts friendly
    force = (
        f"Fontsize={int(font_size)},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        f"BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV={int(margin_v)}"
    )
    vf = f"subtitles='{srt_esc}':force_style='{force}'"
    os.makedirs(os.path.dirname(os.path.abspath(video_out)) or ".", exist_ok=True)
    r = run_ffmpeg(
        [
            "-i",
            video_in,
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-c:a",
            "copy",
            video_out,
        ],
        timeout_sec=timeout_sec,
    )
    if r.get("ok") and os.path.isfile(video_out):
        r["output_path"] = os.path.abspath(video_out)
    return r
