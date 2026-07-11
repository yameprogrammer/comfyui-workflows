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


def mix_audio_under_video(
    video_path: str,
    output_path: str,
    *,
    tracks: list[dict[str, Any]],
    timeout_sec: float = 3600,
) -> dict[str, Any]:
    """
    Mux one or more audio files under a (possibly silent) video.

    tracks: list of {path, volume?, role?}
    Multiple tracks are amix'd then mapped under video.
    Single track uses volume filter only (same as mux_bgm).
    """
    if not os.path.isfile(video_path):
        return {"ok": False, "error": "VIDEO_MISSING", "message": video_path}
    valid: list[dict[str, Any]] = []
    for t in tracks:
        p = t.get("path")
        if p and os.path.isfile(str(p)):
            valid.append(
                {
                    "path": str(p),
                    "volume": float(t.get("volume") if t.get("volume") is not None else 1.0),
                    "role": t.get("role") or "audio",
                }
            )
    if not valid:
        return {"ok": False, "error": "NO_AUDIO_TRACKS", "message": "no valid audio paths"}

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    if len(valid) == 1:
        return mux_bgm(
            video_path,
            valid[0]["path"],
            output_path,
            audio_volume=valid[0]["volume"],
            timeout_sec=timeout_sec,
        )

    # multi: -i video -i a0 -i a1 ... ; volume each; amix; map
    args: list[str] = ["-i", video_path]
    for t in valid:
        args.extend(["-i", t["path"]])

    filter_parts: list[str] = []
    labels: list[str] = []
    for i, t in enumerate(valid):
        # audio input index = i+1
        vol = max(0.0, min(2.0, float(t["volume"])))
        lab = f"a{i}"
        filter_parts.append(f"[{i + 1}:a]volume={vol}[{lab}]")
        labels.append(f"[{lab}]")
    n = len(valid)
    filter_parts.append(
        f"{''.join(labels)}amix=inputs={n}:duration=longest:dropout_transition=0[aout]"
    )
    fc = ";".join(filter_parts)
    args.extend(
        [
            "-filter_complex",
            fc,
            "-map",
            "0:v:0",
            "-map",
            "[aout]",
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
    )
    result = run_ffmpeg(args, timeout_sec=timeout_sec)
    result["output_path"] = os.path.abspath(output_path)
    result["tracks"] = [{"path": t["path"], "volume": t["volume"], "role": t["role"]} for t in valid]
    return result


def mix_timeline_under_video(
    video_path: str,
    output_path: str,
    *,
    events: list[dict[str, Any]],
    timeout_sec: float = 3600,
) -> dict[str, Any]:
    """
    Place multiple audio clips on a timeline under video.

    events: path, timeline_start_sec, volume, role?,
            source_start_sec?, source_end_sec?
    Uses atrim + adelay + amix. Ends with -shortest (video length).
    """
    if not os.path.isfile(video_path):
        return {"ok": False, "error": "VIDEO_MISSING", "message": video_path}

    valid: list[dict[str, Any]] = []
    for e in events:
        p = e.get("path")
        if not p or not os.path.isfile(str(p)):
            continue
        valid.append(
            {
                "path": str(p),
                "timeline_start_sec": max(0.0, float(e.get("timeline_start_sec") or 0.0)),
                "source_start_sec": max(0.0, float(e.get("source_start_sec") or 0.0)),
                "source_end_sec": (
                    float(e["source_end_sec"]) if e.get("source_end_sec") is not None else None
                ),
                "volume": max(0.0, min(2.0, float(e.get("volume") if e.get("volume") is not None else 1.0))),
                "role": e.get("role") or "audio",
                "shot_id": e.get("shot_id"),
            }
        )
    if not valid:
        return {"ok": False, "error": "NO_AUDIO_EVENTS", "message": "no valid timeline events"}

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    # Simple case: one event at t=0 full file
    if (
        len(valid) == 1
        and valid[0]["timeline_start_sec"] == 0.0
        and valid[0]["source_start_sec"] == 0.0
        and valid[0]["source_end_sec"] is None
    ):
        return mux_bgm(
            video_path,
            valid[0]["path"],
            output_path,
            audio_volume=valid[0]["volume"],
            timeout_sec=timeout_sec,
        )

    args: list[str] = ["-i", video_path]
    for e in valid:
        args.extend(["-i", e["path"]])

    filter_parts: list[str] = []
    labels: list[str] = []
    for i, e in enumerate(valid):
        idx = i + 1
        # atrim source window
        ss = e["source_start_sec"]
        se = e["source_end_sec"]
        if se is not None and se > ss:
            trim = f"atrim=start={ss}:end={se},asetpts=PTS-STARTPTS"
        elif ss > 0:
            trim = f"atrim=start={ss},asetpts=PTS-STARTPTS"
        else:
            trim = "anull"
        delay_ms = int(round(e["timeline_start_sec"] * 1000))
        # stereo-safe adelay
        delay = f"adelay={delay_ms}|{delay_ms}"
        vol = e["volume"]
        lab = f"a{i}"
        if trim == "anull":
            filter_parts.append(f"[{idx}:a]{delay},volume={vol}[{lab}]")
        else:
            filter_parts.append(f"[{idx}:a]{trim},{delay},volume={vol}[{lab}]")
        labels.append(f"[{lab}]")

    n = len(valid)
    filter_parts.append(
        f"{''.join(labels)}amix=inputs={n}:duration=longest:dropout_transition=0:normalize=0[aout]"
    )
    fc = ";".join(filter_parts)
    args.extend(
        [
            "-filter_complex",
            fc,
            "-map",
            "0:v:0",
            "-map",
            "[aout]",
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
    )
    result = run_ffmpeg(args, timeout_sec=timeout_sec)
    result["output_path"] = os.path.abspath(output_path)
    result["events"] = valid
    return result


def slice_audio(
    input_path: str,
    output_path: str,
    *,
    start_sec: float = 0.0,
    end_sec: float | None = None,
    duration_sec: float | None = None,
    timeout_sec: float = 600,
) -> dict[str, Any]:
    """Extract [start, end) or [start, start+duration) from audio file."""
    if not os.path.isfile(input_path):
        return {"ok": False, "error": "AUDIO_MISSING", "message": input_path}
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    ss = max(0.0, float(start_sec))
    # Always re-encode: stream-copy seek on wav often leaves wrong duration metadata
    # (observed: 5s request → ffprobe still ~40s).
    if duration_sec is not None:
        dur = max(0.05, float(duration_sec))
    elif end_sec is not None and float(end_sec) > ss:
        dur = float(end_sec) - ss
    else:
        return {"ok": False, "error": "BAD_RANGE", "message": "need end_sec or duration_sec"}

    args = [
        "-ss",
        str(ss),
        "-i",
        input_path,
        "-t",
        str(dur),
        "-c:a",
        "pcm_s16le",
        "-ar",
        "48000",
        "-ac",
        "2",
        output_path,
    ]
    result = run_ffmpeg(args, timeout_sec=timeout_sec)
    result["output_path"] = os.path.abspath(output_path)
    result["start_sec"] = ss
    result["duration_sec"] = dur
    return result
