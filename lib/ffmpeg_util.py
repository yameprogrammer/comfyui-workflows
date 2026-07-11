"""FFmpeg helpers for episode assemble."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Any


def find_ffmpeg() -> str:
    env = os.environ.get("FFMPEG_PATH") or os.environ.get("FFMPEG")
    if env and os.path.isfile(env):
        return env
    which = shutil.which("ffmpeg")
    if which:
        return which
    raise FileNotFoundError(
        "ffmpeg not found on PATH; set FFMPEG_PATH to ffmpeg.exe"
    )


def run_ffmpeg(args: list[str], *, timeout_sec: float = 3600) -> dict[str, Any]:
    cmd = [find_ffmpeg(), "-y", *args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "FFMPEG_TIMEOUT", "message": f">{timeout_sec}s"}
    except FileNotFoundError as e:
        return {"ok": False, "error": "FFMPEG_MISSING", "message": str(e)}
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "")[-2000:]
        return {
            "ok": False,
            "error": "FFMPEG_FAILED",
            "message": err[:500],
            "returncode": proc.returncode,
            "cmd": cmd,
        }
    return {"ok": True, "cmd": cmd}


def concat_videos(
    clip_paths: list[str],
    output_path: str,
    *,
    reencode: bool = True,
    fps: int | None = None,
    timeout_sec: float = 3600,
) -> dict[str, Any]:
    """
    Concatenate videos in order via concat demuxer.
    reencode=True (default) is safer across mixed sources.
    """
    if not clip_paths:
        return {"ok": False, "error": "NO_CLIPS", "message": "empty clip list"}
    for p in clip_paths:
        if not os.path.isfile(p):
            return {"ok": False, "error": "CLIP_MISSING", "message": p}

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    # Windows: concat demuxer wants forward slashes / escaped quotes
    def _entry(path: str) -> str:
        ap = os.path.abspath(path).replace("\\", "/")
        ap = ap.replace("'", r"'\''")
        return f"file '{ap}'"

    list_body = "\n".join(_entry(p) for p in clip_paths) + "\n"
    fd, list_path = tempfile.mkstemp(suffix=".txt", prefix="ffconcat_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(list_body)

        if reencode:
            args = [
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_path,
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
            ]
            if fps:
                args.extend(["-r", str(int(fps))])
            args.append(output_path)
        else:
            args = [
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_path,
                "-c",
                "copy",
                output_path,
            ]
        result = run_ffmpeg(args, timeout_sec=timeout_sec)
        result["list_path"] = list_path
        result["output_path"] = os.path.abspath(output_path)
        return result
    finally:
        try:
            os.remove(list_path)
        except OSError:
            pass


def mux_bgm(
    video_path: str,
    audio_path: str,
    output_path: str,
    *,
    audio_volume: float = 0.35,
    timeout_sec: float = 3600,
) -> dict[str, Any]:
    """Replace/add BGM under video (video has no audio or we drop it)."""
    if not os.path.isfile(video_path):
        return {"ok": False, "error": "VIDEO_MISSING", "message": video_path}
    if not os.path.isfile(audio_path):
        return {"ok": False, "error": "AUDIO_MISSING", "message": audio_path}
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    # Drop existing audio; loop/cut BGM to video length via -shortest
    vol = max(0.0, min(2.0, float(audio_volume)))
    args = [
        "-i",
        video_path,
        "-i",
        audio_path,
        "-filter_complex",
        f"[1:a]volume={vol}[a]",
        "-map",
        "0:v:0",
        "-map",
        "[a]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        output_path,
    ]
    result = run_ffmpeg(args, timeout_sec=timeout_sec)
    result["output_path"] = os.path.abspath(output_path)
    return result
