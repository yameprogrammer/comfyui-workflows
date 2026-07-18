"""
YouTube reference ingest for agent toolbox (no Comfy).

Capabilities:
  - meta (title, duration, chapters, channel…)
  - captions / auto-subs → timed transcript
  - optional Whisper ASR fallback
  - extractive summary + highlight candidates
  - optional media download + ffmpeg highlight clips

Policy: internal reference / analysis only — not for re-upload of source media.
SSOT research: docs/youtube_ref_ingest_research.md
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from lib.comfy_client import WORKSPACE_ROOT

SOURCE_POLICY = (
    "Internal reference / analysis only. Do not re-upload or redistribute source "
    "media or full transcripts as your product. Final deliverables must use factory "
    "generated assets. Respect YouTube ToS and copyright."
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def find_ytdlp() -> str:
    env = os.environ.get("YTDLP_PATH") or os.environ.get("YT_DLP")
    if env and os.path.isfile(env):
        return env
    which = shutil.which("yt-dlp")
    if which:
        return which
    # pyenv shims sometimes need python -m
    return "yt-dlp"


def _ytdlp_cmd(args: list[str]) -> list[str]:
    """Build yt-dlp argv.

    Prefer ``python -m yt_dlp`` when importable (avoids Windows .bat ``%`` expansion
    breaking ``%(ext)s`` templates). Fall back to PATH binary.
    """
    try:
        import yt_dlp  # noqa: F401

        return [sys.executable, "-m", "yt_dlp", *args]
    except Exception:
        pass
    exe = find_ytdlp()
    # Never put bare %(…) templates in args under .bat shims — use fixed names instead.
    return [exe, *args]


def extract_video_id(url: str) -> str | None:
    u = (url or "").strip()
    if not u:
        return None
    if re.fullmatch(r"[\w-]{11}", u):
        return u
    try:
        p = urlparse(u)
    except Exception:
        return None
    host = (p.netloc or "").lower()
    if "youtu.be" in host:
        vid = (p.path or "").strip("/").split("/")[0]
        return vid if re.fullmatch(r"[\w-]{11}", vid) else None
    if "youtube" in host or "youtube-nocookie" in host:
        qs = parse_qs(p.query or "")
        if "v" in qs and qs["v"]:
            return qs["v"][0]
        parts = [x for x in (p.path or "").split("/") if x]
        if parts and parts[0] in ("embed", "shorts", "live", "v") and len(parts) > 1:
            return parts[1] if re.fullmatch(r"[\w-]{11}", parts[1]) else None
    return None


def default_out_dir(video_id: str | None = None) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    vid = video_id or "unknown"
    return os.path.join(WORKSPACE_ROOT, "dumps", f"yt_ref_{vid}_{stamp}")


def _run(
    cmd: list[str],
    *,
    timeout_sec: float = 600,
    cwd: str | None = None,
) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "TIMEOUT", "message": f"{timeout_sec}s", "cmd": cmd}
    except FileNotFoundError as e:
        return {"ok": False, "error": "CMD_MISSING", "message": str(e), "cmd": cmd}
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "")[-3000:]
        return {
            "ok": False,
            "error": "CMD_FAILED",
            "message": err[:800],
            "returncode": proc.returncode,
            "cmd": cmd,
        }
    return {
        "ok": True,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
        "cmd": cmd,
    }


def fetch_meta(url: str, *, timeout_sec: float = 120) -> dict[str, Any]:
    """yt-dlp -J flat meta (no download)."""
    r = _run(
        _ytdlp_cmd(["-J", "--no-download", "--no-warnings", "--", url]),
        timeout_sec=timeout_sec,
    )
    if not r.get("ok"):
        return r
    try:
        raw = json.loads(r["stdout"])
    except json.JSONDecodeError as e:
        return {"ok": False, "error": "META_JSON", "message": str(e)}
    chapters = []
    for ch in raw.get("chapters") or []:
        chapters.append(
            {
                "start": float(ch.get("start_time") or 0),
                "end": float(ch.get("end_time") or 0) if ch.get("end_time") is not None else None,
                "title": ch.get("title") or "",
            }
        )
    meta = {
        "ok": True,
        "url": url,
        "video_id": raw.get("id") or extract_video_id(url),
        "title": raw.get("title"),
        "description": (raw.get("description") or "")[:4000],
        "duration_sec": raw.get("duration"),
        "channel": raw.get("channel") or raw.get("uploader"),
        "channel_id": raw.get("channel_id"),
        "upload_date": raw.get("upload_date"),
        "view_count": raw.get("view_count"),
        "thumbnail": raw.get("thumbnail"),
        "categories": raw.get("categories") or [],
        "tags": (raw.get("tags") or [])[:40],
        "chapters": chapters,
        "language": raw.get("language"),
        "webpage_url": raw.get("webpage_url") or url,
        "extractor": raw.get("extractor"),
    }
    return meta


def _parse_vtt_timestamp(ts: str) -> float:
    # 00:00:01.000 or 00:01.000
    ts = ts.strip().replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(parts[0])


def parse_vtt(path: str, *, source: str = "auto") -> list[dict[str, Any]]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    # strip WEBVTT header / NOTE / STYLE
    lines = text.replace("\r\n", "\n").split("\n")
    segments: list[dict[str, Any]] = []
    i = 0
    ts_re = re.compile(
        r"(\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{1,2}:\d{2}\.\d{3})\s*-->\s*"
        r"(\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{1,2}:\d{2}\.\d{3})"
    )
    while i < len(lines):
        line = lines[i].strip()
        m = ts_re.search(line)
        if not m:
            i += 1
            continue
        start = _parse_vtt_timestamp(m.group(1))
        end = _parse_vtt_timestamp(m.group(2))
        i += 1
        body: list[str] = []
        while i < len(lines) and lines[i].strip():
            # drop cue settings tags
            t = re.sub(r"<[^>]+>", "", lines[i]).strip()
            if t and not t.isdigit():
                body.append(t)
            i += 1
        text_body = " ".join(body).strip()
        if text_body:
            segments.append(
                {"start": start, "end": end, "text": text_body, "source": source}
            )
    return _dedupe_segments(segments)


def parse_srt(path: str, *, source: str = "manual") -> list[dict[str, Any]]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip())
    segments: list[dict[str, Any]] = []
    ts_re = re.compile(
        r"(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})"
    )
    for block in blocks:
        lines = [ln for ln in block.split("\n") if ln.strip()]
        if len(lines) < 2:
            continue
        m = None
        body_start = 1
        for idx, ln in enumerate(lines):
            m = ts_re.search(ln)
            if m:
                body_start = idx + 1
                break
        if not m:
            continue
        start = _parse_vtt_timestamp(m.group(1).replace(",", "."))
        end = _parse_vtt_timestamp(m.group(2).replace(",", "."))
        body = " ".join(lines[body_start:]).strip()
        body = re.sub(r"<[^>]+>", "", body)
        if body:
            segments.append({"start": start, "end": end, "text": body, "source": source})
    return _dedupe_segments(segments)


def _dedupe_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    prev = None
    for seg in segments:
        t = (seg.get("text") or "").strip()
        if not t:
            continue
        key = (round(float(seg["start"]), 2), t)
        if prev == key:
            continue
        prev = key
        out.append(seg)
    return out


def segments_to_srt(segments: list[dict[str, Any]]) -> str:
    def fmt(t: float) -> str:
        if t < 0:
            t = 0
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = t % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

    lines: list[str] = []
    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{fmt(float(seg['start']))} --> {fmt(float(seg['end']))}")
        lines.append(str(seg.get("text") or ""))
        lines.append("")
    return "\n".join(lines)


def _expand_sub_langs(langs: list[str]) -> str:
    """
    yt-dlp auto captions often use codes like en-en / ko-en.
    Prefer tight list (avoid en.* which matches en-de, en-fr, … and hammer the API).
    """
    parts: list[str] = []
    for lang in langs:
        lang = (lang or "").strip()
        if not lang:
            continue
        if "*" in lang:
            parts.append(lang)
            continue
        parts.append(lang)
        parts.append(f"{lang}-{lang}")  # e.g. en-en
        if lang != "en":
            parts.append(f"{lang}-en")  # translated from English
    # unique preserve order
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return ",".join(out) if out else "en,en-en"


def download_captions(
    url: str,
    work_dir: str,
    *,
    langs: list[str] | None = None,
    timeout_sec: float = 300,
) -> dict[str, Any]:
    """Download subtitles only into work_dir. Prefer manual over auto."""
    langs = langs or ["ko", "en"]
    lang_arg = _expand_sub_langs(langs)
    work_dir = os.path.abspath(work_dir)
    os.makedirs(work_dir, exist_ok=True)
    # Use basename only + cwd=work_dir so Windows bat never sees relative nested paths.
    # yt-dlp writes: cap.<lang>.vtt in work_dir.
    out_base = "cap"
    last_r: dict[str, Any] = {}
    # try manual first, then auto
    for auto in (False, True):
        # clean previous caps
        for old in Path(work_dir).glob("cap.*"):
            try:
                old.unlink()
            except OSError:
                pass
        flags = ["--write-auto-subs"] if auto else ["--write-subs"]
        cmd = _ytdlp_cmd(
            [
                "--skip-download",
                *flags,
                "--sub-langs",
                lang_arg,
                "--sub-format",
                "vtt/srt/best",
                "-o",
                out_base,
                "--no-warnings",
                "--",
                url,
            ]
        )
        r = _run(cmd, timeout_sec=timeout_sec, cwd=work_dir)
        last_r = r
        files = sorted(
            list(Path(work_dir).glob("cap*.vtt"))
            + list(Path(work_dir).glob("cap*.srt"))
            + list(Path(work_dir).rglob("*.vtt"))
            + list(Path(work_dir).rglob("*.srt"))
        )
        # ignore non-caption junk
        files = [f for f in files if f.suffix.lower() in (".vtt", ".srt")]
        if not files:
            continue
        source = "auto" if auto else "manual"
        preferred = None
        for lang in langs:
            for f in files:
                name = f.name.lower()
                if (
                    f".{lang}." in name
                    or f".{lang}-" in name
                    or name.startswith(f"cap.{lang}")
                ):
                    preferred = f
                    break
            if preferred:
                break
        path = str(preferred or files[0])
        if path.endswith(".srt"):
            segs = parse_srt(path, source=source)
        else:
            segs = parse_vtt(path, source=source)
        if not segs:
            continue
        return {
            "ok": True,
            "source": source,
            "path": path,
            "segments": segs,
            "files": [str(f) for f in files],
            "ytdlp": r,
            "sub_langs": lang_arg,
        }
    return {
        "ok": False,
        "error": "NO_CAPTIONS",
        "message": "No manual or auto captions for requested languages",
        "langs": langs,
        "sub_langs": lang_arg,
        "ytdlp": last_r,
    }


def download_audio(
    url: str,
    out_path: str,
    *,
    timeout_sec: float = 1800,
) -> dict[str, Any]:
    out_path = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    # m4a/webm audio — write into out dir with fixed stem (bat-safe)
    out_dir = os.path.dirname(out_path)
    stem = Path(out_path).stem
    cmd = _ytdlp_cmd(
        [
            "-f",
            "bestaudio/best",
            "-x",
            "--audio-format",
            "wav",
            "-o",
            stem,
            "--no-warnings",
            "--",
            url,
        ]
    )
    r = _run(cmd, timeout_sec=timeout_sec, cwd=out_dir)
    if not r.get("ok"):
        return r
    # find produced wav
    cand = os.path.join(out_dir, stem + ".wav")
    if os.path.isfile(cand):
        if cand != out_path:
            shutil.move(cand, out_path)
        return {"ok": True, "path": out_path}
    wavs = sorted(Path(out_dir).glob(stem + "*.wav")) + sorted(
        Path(out_dir).glob("*.wav")
    )
    if wavs:
        shutil.move(str(wavs[0]), out_path)
        return {"ok": True, "path": out_path}
    return {
        "ok": False,
        "error": "AUDIO_MISSING",
        "message": "yt-dlp finished but no wav",
        "ytdlp": r,
    }


def whisper_transcribe(
    audio_path: str,
    *,
    language: str | None = "ko",
    model_size: str = "base",
) -> dict[str, Any]:
    """ASR fallback via faster-whisper or openai-whisper if installed."""
    if not os.path.isfile(audio_path):
        return {"ok": False, "error": "AUDIO_MISSING", "message": audio_path}
    # faster-whisper preferred
    try:
        from faster_whisper import WhisperModel  # type: ignore

        model = WhisperModel(model_size, device="cuda", compute_type="float16")
        segments_iter, info = model.transcribe(
            audio_path, language=language if language and language != "auto" else None
        )
        segs = []
        for s in segments_iter:
            segs.append(
                {
                    "start": float(s.start),
                    "end": float(s.end),
                    "text": (s.text or "").strip(),
                    "source": "whisper",
                }
            )
        return {
            "ok": True,
            "segments": _dedupe_segments(segs),
            "engine": "faster-whisper",
            "language": getattr(info, "language", language),
        }
    except Exception as e_fw:
        try:
            import whisper  # type: ignore

            model = whisper.load_model(model_size)
            result = model.transcribe(
                audio_path, language=None if language in (None, "auto") else language
            )
            segs = []
            for s in result.get("segments") or []:
                segs.append(
                    {
                        "start": float(s.get("start") or 0),
                        "end": float(s.get("end") or 0),
                        "text": (s.get("text") or "").strip(),
                        "source": "whisper",
                    }
                )
            return {
                "ok": True,
                "segments": _dedupe_segments(segs),
                "engine": "openai-whisper",
                "language": result.get("language"),
            }
        except Exception as e_ow:
            return {
                "ok": False,
                "error": "WHISPER_UNAVAILABLE",
                "message": f"faster-whisper: {e_fw}; whisper: {e_ow}",
            }


def download_video(
    url: str,
    out_path: str,
    *,
    max_height: int = 720,
    timeout_sec: float = 3600,
) -> dict[str, Any]:
    out_path = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    base, ext = os.path.splitext(out_path)
    if not ext:
        ext = ".mp4"
        out_path = base + ext
    out_dir = os.path.dirname(out_path)
    stem = Path(out_path).stem
    # Avoid shell metacharacters (< > *) — Windows .bat shims treat them as redirect/glob.
    # Prefer exact height steps then best mp4/best.
    h = int(max_height)
    heights = []
    for cand in (h, 1080, 720, 480, 360):
        if cand not in heights and cand <= max(h, 1080):
            heights.append(cand)
    parts: list[str] = []
    for hh in heights:
        parts.append(f"best[height={hh}][ext=mp4]")
        parts.append(f"best[height={hh}]")
    parts.extend(["best[ext=mp4]", "best"])
    fmt = "/".join(parts)
    # Force .mp4 name — without template yt-dlp may write extension-less file.
    out_name = stem + ".mp4"
    cmd = _ytdlp_cmd(
        [
            "-f",
            fmt,
            "--merge-output-format",
            "mp4",
            "-o",
            out_name,
            "--no-warnings",
            "--",
            url,
        ]
    )
    r = _run(cmd, timeout_sec=timeout_sec, cwd=out_dir)
    if not r.get("ok"):
        return r
    for cand in (
        os.path.join(out_dir, out_name),
        os.path.join(out_dir, stem),  # extension-less leftover
        out_path,
        os.path.join(out_dir, stem + ".mkv"),
        os.path.join(out_dir, stem + ".webm"),
        os.path.join(out_dir, "vidtest"),
    ):
        if os.path.isfile(cand) and os.path.getsize(cand) > 1000:
            if cand != out_path:
                shutil.move(cand, out_path)
            return {"ok": True, "path": out_path}
    vids = sorted(Path(out_dir).glob(stem + ".*")) + sorted(Path(out_dir).glob("*.mp4"))
    for v in vids:
        if v.suffix.lower() in (".mp4", ".mkv", ".webm", "") or v.name == stem:
            if v.stat().st_size > 1000:
                shutil.move(str(v), out_path)
                return {"ok": True, "path": out_path}
    return {
        "ok": False,
        "error": "VIDEO_MISSING",
        "message": "download finished, file not found",
        "ytdlp": r,
    }


def build_summary(
    meta: dict[str, Any],
    segments: list[dict[str, Any]],
    *,
    max_chars: int = 2500,
) -> str:
    """Extractive summary (no LLM) — enough for agent handoff."""
    lines = [
        f"# Reference summary (extractive)",
        "",
        f"- **title**: {meta.get('title')}",
        f"- **channel**: {meta.get('channel')}",
        f"- **duration_sec**: {meta.get('duration_sec')}",
        f"- **url**: {meta.get('webpage_url') or meta.get('url')}",
        f"- **video_id**: {meta.get('video_id')}",
        "",
        "## Policy",
        SOURCE_POLICY,
        "",
    ]
    chapters = meta.get("chapters") or []
    if chapters:
        lines.append("## Chapters")
        for ch in chapters:
            lines.append(
                f"- [{_fmt_ts(ch.get('start'))}] {ch.get('title')} "
                f"({ch.get('start')}s–{ch.get('end')})"
            )
        lines.append("")
    lines.append("## Transcript excerpt")
    lines.append("")
    buf = []
    total = 0
    for seg in segments:
        t = (seg.get("text") or "").strip()
        if not t:
            continue
        line = f"[{_fmt_ts(seg.get('start'))}] {t}"
        if total + len(line) > max_chars:
            buf.append("…")
            break
        buf.append(line)
        total += len(line) + 1
    lines.extend(buf or ["_(no transcript segments)_"])
    lines.append("")
    lines.append("## Agent next")
    lines.append(
        "Read transcript.json for full timed text. Use video-direction / CREATIVE "
        "to plan shorts; do not re-upload source clips as final product."
    )
    return "\n".join(lines)


def _fmt_ts(sec: Any) -> str:
    try:
        t = float(sec or 0)
    except (TypeError, ValueError):
        t = 0.0
    m = int(t // 60)
    s = int(t % 60)
    return f"{m:02d}:{s:02d}"


def propose_highlights(
    meta: dict[str, Any],
    segments: list[dict[str, Any]],
    *,
    max_clips: int = 5,
    target_sec: float = 45.0,
    min_sec: float = 12.0,
    max_sec: float = 60.0,
) -> list[dict[str, Any]]:
    """Heuristic highlights: chapters first, else dense transcript windows."""
    highlights: list[dict[str, Any]] = []
    duration = float(meta.get("duration_sec") or 0) or None

    chapters = meta.get("chapters") or []
    if chapters:
        for i, ch in enumerate(chapters):
            start = float(ch.get("start") or 0)
            end = ch.get("end")
            if end is None:
                if i + 1 < len(chapters):
                    end = float(chapters[i + 1].get("start") or start + target_sec)
                else:
                    end = start + target_sec
            end = float(end)
            if duration:
                end = min(end, duration)
            length = end - start
            if length < min_sec:
                end = start + min(max_sec, max(min_sec, target_sec))
            if length > max_sec:
                end = start + max_sec
            highlights.append(
                {
                    "id": f"ch_{i+1:02d}",
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "label": ch.get("title") or f"Chapter {i+1}",
                    "score": 0.9 - i * 0.05,
                    "reason": "chapter",
                }
            )
            if len(highlights) >= max_clips:
                break
        return highlights[:max_clips]

    if not segments:
        # cold open default
        end = min(max_sec, duration or target_sec)
        return [
            {
                "id": "open_01",
                "start": 0.0,
                "end": round(float(end), 2),
                "label": "Cold open",
                "score": 0.5,
                "reason": "no_chapters_no_transcript",
            }
        ]

    # Sliding windows by char density
    windows: list[dict[str, Any]] = []
    n = len(segments)
    j = 0
    for i in range(n):
        start = float(segments[i]["start"])
        end = start
        chars = 0
        j = max(j, i)
        while j < n and (float(segments[j]["end"]) - start) <= max_sec:
            end = float(segments[j]["end"])
            chars += len(segments[j].get("text") or "")
            if (end - start) >= min_sec and chars > 40:
                dens = chars / max(end - start, 1.0)
                windows.append(
                    {
                        "start": start,
                        "end": end,
                        "chars": chars,
                        "density": dens,
                        "text": " ".join(
                            (segments[k].get("text") or "") for k in range(i, j + 1)
                        )[:120],
                    }
                )
            j += 1

    windows.sort(key=lambda w: w["density"], reverse=True)
    picked: list[dict[str, Any]] = []
    for w in windows:
        if len(picked) >= max_clips:
            break
        # non-overlap
        if any(
            not (w["end"] <= p["start"] or w["start"] >= p["end"]) for p in picked
        ):
            continue
        picked.append(w)

    if not picked and segments:
        start = float(segments[0]["start"])
        end = min(start + target_sec, float(segments[-1]["end"]))
        picked = [{"start": start, "end": end, "density": 0, "text": segments[0].get("text")}]

    out = []
    for i, w in enumerate(picked):
        out.append(
            {
                "id": f"win_{i+1:02d}",
                "start": round(float(w["start"]), 2),
                "end": round(float(w["end"]), 2),
                "label": (w.get("text") or f"Highlight {i+1}")[:80],
                "score": round(float(w.get("density") or 0), 3),
                "reason": "transcript_density",
            }
        )
    return out


def cut_clip(
    video_path: str,
    out_path: str,
    start: float,
    end: float,
    *,
    reencode: bool = False,
) -> dict[str, Any]:
    from lib.ffmpeg_util import run_ffmpeg

    if end <= start:
        return {"ok": False, "error": "BAD_RANGE", "message": f"{start}-{end}"}
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    dur = end - start
    if reencode:
        args = [
            "-ss",
            str(start),
            "-i",
            video_path,
            "-t",
            str(dur),
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            out_path,
        ]
    else:
        args = [
            "-ss",
            str(start),
            "-i",
            video_path,
            "-t",
            str(dur),
            "-c",
            "copy",
            "-avoid_negative_ts",
            "make_zero",
            out_path,
        ]
    r = run_ffmpeg(args, timeout_sec=600)
    if r.get("ok"):
        r["path"] = out_path
    return r


def write_package(
    out_dir: str,
    *,
    meta: dict[str, Any],
    segments: list[dict[str, Any]],
    highlights: list[dict[str, Any]] | None = None,
    summary: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    paths: dict[str, str] = {}

    meta_path = os.path.join(out_dir, "meta.json")
    meta_out = {k: v for k, v in meta.items() if k != "ok"}
    meta_out["created_at"] = utc_now_iso()
    meta_out["policy"] = SOURCE_POLICY
    if extra:
        meta_out["ingest"] = extra
    Path(meta_path).write_text(
        json.dumps(meta_out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    paths["meta"] = meta_path

    tr = {
        "video_id": meta.get("video_id"),
        "url": meta.get("webpage_url") or meta.get("url"),
        "segment_count": len(segments),
        "segments": segments,
        "created_at": utc_now_iso(),
    }
    tr_path = os.path.join(out_dir, "transcript.json")
    Path(tr_path).write_text(json.dumps(tr, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["transcript_json"] = tr_path

    srt_path = os.path.join(out_dir, "transcript.srt")
    Path(srt_path).write_text(segments_to_srt(segments), encoding="utf-8")
    paths["transcript_srt"] = srt_path

    if summary is None:
        summary = build_summary(meta, segments)
    sum_path = os.path.join(out_dir, "summary.md")
    Path(sum_path).write_text(summary, encoding="utf-8")
    paths["summary"] = sum_path

    if highlights is not None:
        hl = {
            "video_id": meta.get("video_id"),
            "count": len(highlights),
            "highlights": highlights,
            "created_at": utc_now_iso(),
        }
        hl_path = os.path.join(out_dir, "highlights.json")
        Path(hl_path).write_text(
            json.dumps(hl, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        paths["highlights"] = hl_path

    src_path = os.path.join(out_dir, "SOURCE.md")
    Path(src_path).write_text(
        "\n".join(
            [
                f"# Source",
                "",
                f"- URL: {meta.get('webpage_url') or meta.get('url')}",
                f"- video_id: {meta.get('video_id')}",
                f"- title: {meta.get('title')}",
                f"- channel: {meta.get('channel')}",
                "",
                "## Policy",
                SOURCE_POLICY,
                "",
            ]
        ),
        encoding="utf-8",
    )
    paths["source"] = src_path
    return paths


def ingest_youtube(
    url: str,
    out_dir: str | None = None,
    *,
    langs: list[str] | None = None,
    whisper: bool = False,
    whisper_model: str = "base",
    download_media: bool = False,
    max_height: int = 720,
    highlights: bool = True,
    max_clips: int = 5,
    cut_clips: bool = False,
    reencode_clips: bool = False,
) -> dict[str, Any]:
    """
    Full ingest pipeline → package dir.
    """
    vid = extract_video_id(url)
    out_dir = out_dir or default_out_dir(vid)
    os.makedirs(out_dir, exist_ok=True)
    work = os.path.join(out_dir, "_work")
    os.makedirs(work, exist_ok=True)

    result: dict[str, Any] = {
        "ok": False,
        "url": url,
        "out_dir": out_dir,
        "steps": {},
    }

    meta = fetch_meta(url)
    result["steps"]["meta"] = {
        "ok": bool(meta.get("ok")),
        "error": meta.get("error"),
        "message": meta.get("message"),
    }
    if not meta.get("ok"):
        result["error"] = meta.get("error") or "META_FAILED"
        result["message"] = meta.get("message")
        return result

    vid = meta.get("video_id") or vid
    segments: list[dict[str, Any]] = []
    cap = download_captions(url, work, langs=langs)
    result["steps"]["captions"] = {
        "ok": bool(cap.get("ok")),
        "source": cap.get("source"),
        "error": cap.get("error"),
        "message": cap.get("message"),
        "count": len(cap.get("segments") or []),
    }
    if cap.get("ok"):
        segments = list(cap.get("segments") or [])

    if (not segments) and whisper:
        audio_path = os.path.join(work, "audio.wav")
        ar = download_audio(url, audio_path)
        result["steps"]["audio"] = {"ok": bool(ar.get("ok")), "error": ar.get("error")}
        if ar.get("ok"):
            wr = whisper_transcribe(
                ar["path"],
                language=(langs or ["ko"])[0] if langs else "ko",
                model_size=whisper_model,
            )
            result["steps"]["whisper"] = {
                "ok": bool(wr.get("ok")),
                "engine": wr.get("engine"),
                "error": wr.get("error"),
                "message": wr.get("message"),
            }
            if wr.get("ok"):
                segments = list(wr.get("segments") or [])

    hl_list: list[dict[str, Any]] | None = None
    if highlights:
        hl_list = propose_highlights(meta, segments, max_clips=max_clips)
        result["steps"]["highlights"] = {"ok": True, "count": len(hl_list)}

    media_path = None
    if download_media or cut_clips:
        media_path = os.path.join(out_dir, "source.mp4")
        vr = download_video(url, media_path, max_height=max_height)
        result["steps"]["video"] = {
            "ok": bool(vr.get("ok")),
            "path": vr.get("path"),
            "error": vr.get("error"),
            "message": vr.get("message"),
        }
        if vr.get("ok"):
            media_path = vr["path"]
        else:
            media_path = None
            if cut_clips:
                result["steps"]["cut"] = {
                    "ok": False,
                    "error": "NO_MEDIA",
                    "message": "download failed; cannot cut",
                }

    clip_paths: list[str] = []
    if cut_clips and media_path and hl_list:
        clips_dir = os.path.join(out_dir, "clips")
        os.makedirs(clips_dir, exist_ok=True)
        cut_ok = 0
        for h in hl_list:
            out_c = os.path.join(clips_dir, f"{h['id']}.mp4")
            cr = cut_clip(
                media_path,
                out_c,
                float(h["start"]),
                float(h["end"]),
                reencode=reencode_clips,
            )
            if cr.get("ok"):
                cut_ok += 1
                clip_paths.append(out_c)
                h["clip"] = out_c
        result["steps"]["cut"] = {"ok": cut_ok > 0, "count": cut_ok}

    paths = write_package(
        out_dir,
        meta=meta,
        segments=segments,
        highlights=hl_list,
        extra={
            "langs": langs or ["ko", "en"],
            "whisper_requested": whisper,
            "download_media": download_media or cut_clips,
            "segment_source": (segments[0].get("source") if segments else None),
        },
    )
    if media_path:
        paths["media"] = media_path
    if clip_paths:
        paths["clips"] = clip_paths  # type: ignore

    result["ok"] = True
    result["video_id"] = vid
    result["title"] = meta.get("title")
    result["segment_count"] = len(segments)
    result["highlight_count"] = len(hl_list or [])
    result["paths"] = paths
    result["policy"] = SOURCE_POLICY
    return result


def load_package(package_dir: str) -> dict[str, Any]:
    package_dir = os.path.abspath(package_dir)
    meta_path = os.path.join(package_dir, "meta.json")
    tr_path = os.path.join(package_dir, "transcript.json")
    hl_path = os.path.join(package_dir, "highlights.json")
    if not os.path.isfile(meta_path):
        raise FileNotFoundError(f"meta.json missing in {package_dir}")
    meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
    segments = []
    if os.path.isfile(tr_path):
        tr = json.loads(Path(tr_path).read_text(encoding="utf-8"))
        segments = list(tr.get("segments") or [])
    highlights = []
    if os.path.isfile(hl_path):
        hl = json.loads(Path(hl_path).read_text(encoding="utf-8"))
        highlights = list(hl.get("highlights") or [])
    return {
        "package_dir": package_dir,
        "meta": meta,
        "segments": segments,
        "highlights": highlights,
    }


def cut_highlights_from_package(
    package_dir: str,
    *,
    media_path: str | None = None,
    max_clips: int | None = None,
    reencode: bool = False,
    rebuild_highlights: bool = False,
) -> dict[str, Any]:
    pkg = load_package(package_dir)
    meta = pkg["meta"]
    segments = pkg["segments"]
    highlights = pkg["highlights"]
    if rebuild_highlights or not highlights:
        highlights = propose_highlights(
            meta, segments, max_clips=max_clips or 5
        )
    media = media_path or os.path.join(package_dir, "source.mp4")
    if not os.path.isfile(media):
        url = meta.get("webpage_url") or meta.get("url")
        if not url:
            return {"ok": False, "error": "NO_URL", "message": "no media and no url"}
        dr = download_video(url, media)
        if not dr.get("ok"):
            return dr
        media = dr["path"]
    clips_dir = os.path.join(package_dir, "clips")
    os.makedirs(clips_dir, exist_ok=True)
    if max_clips:
        highlights = highlights[: max_clips]
    done = []
    for h in highlights:
        out_c = os.path.join(clips_dir, f"{h['id']}.mp4")
        cr = cut_clip(
            media,
            out_c,
            float(h["start"]),
            float(h["end"]),
            reencode=reencode,
        )
        if cr.get("ok"):
            h["clip"] = out_c
            done.append(out_c)
    # rewrite highlights
    hl_path = os.path.join(package_dir, "highlights.json")
    Path(hl_path).write_text(
        json.dumps(
            {
                "video_id": meta.get("video_id"),
                "count": len(highlights),
                "highlights": highlights,
                "created_at": utc_now_iso(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "ok": True,
        "package_dir": package_dir,
        "clips": done,
        "highlights": highlights,
        "media": media,
    }
