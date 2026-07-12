"""FFmpeg helpers for episode assemble."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
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


def probe_duration(path: str) -> float | None:
    try:
        import json

        out = subprocess.check_output(
            [
                shutil.which("ffprobe") or "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                path,
            ],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=30,
        )
        return float(json.loads(out)["format"]["duration"])
    except Exception:
        return None


def probe_has_audio(path: str) -> bool:
    try:
        import json

        out = subprocess.check_output(
            [
                shutil.which("ffprobe") or "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "json",
                path,
            ],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=30,
        )
        streams = json.loads(out).get("streams") or []
        return any(s.get("codec_type") == "audio" for s in streams)
    except Exception:
        return False


def normalize_clip(
    input_path: str,
    output_path: str,
    *,
    width: int = 960,
    height: int = 544,
    fps: float = 25.0,
    audio_path: str | None = None,
    audio_volume: float = 1.0,
    keep_video_audio: bool = True,
    max_audio_sec: float | None = None,
    timeout_sec: float = 3600,
) -> dict[str, Any]:
    """
    Normalize a clip to fixed canvas + fps for clean concat.

    Audio priority:
      1) explicit audio_path (e.g. VO stem)
      2) keep embedded video audio if keep_video_audio and present (SI2V lips)
      3) silence matching video duration
    """
    if not os.path.isfile(input_path):
        return {"ok": False, "error": "CLIP_MISSING", "message": input_path}
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    w, h = int(width), int(height)
    fps_f = max(1.0, float(fps))
    vfilter = (
        f"fps={fps_f},scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p"
    )
    vol = max(0.0, min(2.0, float(audio_volume)))
    has_a = probe_has_audio(input_path)
    vdur = probe_duration(input_path) or 0.0

    args: list[str] = ["-i", input_path]
    # Optional external audio as input 1
    use_ext = bool(audio_path and os.path.isfile(audio_path))
    if use_ext:
        args.extend(["-i", audio_path])

    if use_ext:
        # Trim/pad external audio to video length so stems never spill into next shot
        cap = max_audio_sec if max_audio_sec is not None else vdur
        if cap and cap > 0:
            achain = (
                f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                f"atrim=0:{cap:.4f},asetpts=PTS-STARTPTS,volume={vol},"
                f"apad=whole_dur={vdur:.4f},atrim=0:{vdur:.4f},asetpts=PTS-STARTPTS[aout]"
            )
        else:
            achain = (
                f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                f"volume={vol}[aout]"
            )
        fc = f"[0:v]{vfilter}[vout];{achain}"
        args.extend(
            [
                "-filter_complex",
                fc,
                "-map",
                "[vout]",
                "-map",
                "[aout]",
            ]
        )
    elif keep_video_audio and has_a:
        fc = (
            f"[0:v]{vfilter}[vout];"
            f"[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"volume={vol}[aout]"
        )
        args.extend(
            [
                "-filter_complex",
                fc,
                "-map",
                "[vout]",
                "-map",
                "[aout]",
            ]
        )
    else:
        # silence
        dur = vdur if vdur > 0 else 1.0
        args = [
            "-i",
            input_path,
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=channel_layout=stereo:sample_rate=48000",
            "-filter_complex",
            f"[0:v]{vfilter}[vout]",
            "-map",
            "[vout]",
            "-map",
            "1:a",
            "-shortest",
        ]

    args.extend(
        [
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
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            output_path,
        ]
    )
    result = run_ffmpeg(args, timeout_sec=timeout_sec)
    result["output_path"] = os.path.abspath(output_path)
    return result


def concat_videos(
    clip_paths: list[str],
    output_path: str,
    *,
    reencode: bool = True,
    fps: int | None = None,
    width: int | None = None,
    height: int | None = None,
    timeout_sec: float = 3600,
) -> dict[str, Any]:
    """
    Concatenate videos in order.

    When reencode=True (default), each clip is first normalized to the same
    canvas/fps (filter-based) so mixed 16fps I2V + 25fps SI2V keep duration and
    lip-sync. Optional width/height/fps override the normalize target.
    """
    if not clip_paths:
        return {"ok": False, "error": "NO_CLIPS", "message": "empty clip list"}
    for p in clip_paths:
        if not os.path.isfile(p):
            return {"ok": False, "error": "CLIP_MISSING", "message": p}

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    # Stream-copy path (same codec only)
    if not reencode:
        def _entry(path: str) -> str:
            ap = os.path.abspath(path).replace("\\", "/")
            ap = ap.replace("'", r"'\''")
            return f"file '{ap}'"

        list_body = "\n".join(_entry(p) for p in clip_paths) + "\n"
        fd, list_path = tempfile.mkstemp(suffix=".txt", prefix="ffconcat_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(list_body)
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
            result["output_path"] = os.path.abspath(output_path)
            return result
        finally:
            try:
                os.remove(list_path)
            except OSError:
                pass

    # Normalize each clip then concat demuxer (identical streams)
    tw = int(width or 960)
    th = int(height or 544)
    tfps = float(fps or 25)
    tmp_dir = tempfile.mkdtemp(prefix="ffnorm_")
    norms: list[str] = []
    try:
        for i, src in enumerate(clip_paths):
            dst = os.path.join(tmp_dir, f"n_{i:03d}.mp4")
            r = normalize_clip(
                src,
                dst,
                width=tw,
                height=th,
                fps=tfps,
                keep_video_audio=True,
                timeout_sec=timeout_sec,
            )
            if not r.get("ok"):
                return r
            norms.append(dst)

        def _entry(path: str) -> str:
            ap = os.path.abspath(path).replace("\\", "/")
            ap = ap.replace("'", r"'\''")
            return f"file '{ap}'"

        list_body = "\n".join(_entry(p) for p in norms) + "\n"
        fd, list_path = tempfile.mkstemp(suffix=".txt", prefix="ffconcat_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(list_body)
            args = [
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_path,
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                output_path,
            ]
            result = run_ffmpeg(args, timeout_sec=timeout_sec)
            result["output_path"] = os.path.abspath(output_path)
            result["normalized"] = norms
            return result
        finally:
            try:
                os.remove(list_path)
            except OSError:
                pass
    finally:
        for p in norms:
            try:
                os.remove(p)
            except OSError:
                pass
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass


def mix_bgm_keep_video_audio(
    video_path: str,
    bgm_path: str,
    output_path: str,
    *,
    bgm_volume: float = 0.22,
    video_audio_volume: float = 1.0,
    timeout_sec: float = 3600,
) -> dict[str, Any]:
    """Keep dialogue/VO already on video; mix BGM underneath (no stem re-lay)."""
    if not os.path.isfile(video_path):
        return {"ok": False, "error": "VIDEO_MISSING", "message": video_path}
    if not os.path.isfile(bgm_path):
        return {"ok": False, "error": "AUDIO_MISSING", "message": bgm_path}
    if not probe_has_audio(video_path):
        return mux_bgm(
            video_path,
            bgm_path,
            output_path,
            audio_volume=bgm_volume,
            timeout_sec=timeout_sec,
        )
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    bv = max(0.0, min(2.0, float(bgm_volume)))
    vv = max(0.0, min(2.0, float(video_audio_volume)))
    # Speech first; BGM quieter. normalize=0 keeps dialogue level from being crushed.
    # duration=first follows video (speech) length; BGM is trimmed via -shortest.
    fc = (
        f"[0:a]aformat=sample_fmts=fltp:channel_layouts=stereo,"
        f"aresample=48000,volume={vv}[va];"
        f"[1:a]aformat=sample_fmts=fltp:channel_layouts=stereo,"
        f"aresample=48000,volume={bv}[ba];"
        f"[va][ba]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
        f"alimiter=limit=0.95[aout]"
    )
    args = [
        "-i",
        video_path,
        "-i",
        bgm_path,
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
    result = run_ffmpeg(args, timeout_sec=timeout_sec)
    result["output_path"] = os.path.abspath(output_path)
    return result


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


# SI2V driving-audio prep modes.
# Full-mix music often starves lip motion; emphasize speech band / stereo center.
# "demucs" is optional (requires `demucs` package + model download).
DRIVING_PREP_MODES = (
    "copy",
    "voicey",
    "center",
    "vocal_band",
    "center_voicey",
    "demucs",
    "auto",
)


def demucs_available() -> bool:
    """True if demucs imports in preferred Comfy portable / current Python."""
    py_candidates = [
        os.environ.get("COMFY_PYTHON") or "",
        r"F:\ComfyUI_windows_portable\python_embeded\python.exe",
        sys.executable,
    ]
    py = next((p for p in py_candidates if p and os.path.isfile(p)), sys.executable)
    try:
        chk = subprocess.run(
            [py, "-c", "import demucs"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return chk.returncode == 0
    except Exception:
        return False


def resolve_driving_prep_mode(mode: str | None = None) -> str:
    """
    Resolve prep mode. `auto` → demucs if installed else center_voicey.
    """
    m = (mode or "auto").strip().lower()
    if m in ("", "auto", "default"):
        return "demucs" if demucs_available() else "center_voicey"
    if m not in DRIVING_PREP_MODES or m == "auto":
        raise ValueError(f"unknown driving prep mode {mode!r}")
    return m


def _driving_af_chain(mode: str) -> str | None:
    """Return ffmpeg -af filter graph for mode, or None for re-encode only."""
    m = (mode or "copy").strip().lower()
    if m in ("copy", "raw", "none", ""):
        return None
    if m == "voicey":
        # Mild speech-band EQ + light dynamics (same idea as ad-hoc *voicey* slices).
        return (
            "highpass=f=90,"
            "lowpass=f=9000,"
            "equalizer=f=2500:t=q:w=1.2:g=4,"
            "equalizer=f=400:t=q:w=1.0:g=-2,"
            "acompressor=threshold=-18dB:ratio=3:attack=10:release=120,"
            "loudnorm=I=-16:TP=-1.5:LRA=11"
        )
    if m == "center":
        # Mid channel from stereo (vocals often hard-panned center in masters).
        return "pan=mono|c0=0.5*c0+0.5*c1"
    if m == "vocal_band":
        # Narrower band for mouth cues; kills bass beds and cymbals somewhat.
        return (
            "highpass=f=180,"
            "lowpass=f=4500,"
            "equalizer=f=2000:t=q:w=1.0:g=5,"
            "acompressor=threshold=-20dB:ratio=4:attack=8:release=100,"
            "loudnorm=I=-16:TP=-1.5:LRA=11"
        )
    if m == "center_voicey":
        return (
            "pan=mono|c0=0.5*c0+0.5*c1,"
            "highpass=f=100,"
            "lowpass=f=8000,"
            "equalizer=f=2500:t=q:w=1.2:g=5,"
            "acompressor=threshold=-18dB:ratio=3.5:attack=8:release=100,"
            "loudnorm=I=-16:TP=-1.5:LRA=11"
        )
    if m == "demucs":
        # Handled in prepare_driving_audio (external package).
        return None
    raise ValueError(
        f"unknown driving prep mode {mode!r}; choose from {DRIVING_PREP_MODES}"
    )


def separate_vocals_demucs(
    input_path: str,
    output_path: str,
    *,
    model: str = "htdemucs",
    timeout_sec: float = 1800,
) -> dict[str, Any]:
    """
    Extract vocals stem via demucs CLI if installed.

    Install (portable or system): `pip install demucs`
    First run downloads model weights.
    """
    if not os.path.isfile(input_path):
        return {"ok": False, "error": "AUDIO_MISSING", "message": input_path}
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    # Prefer Comfy portable python (torch usually present), then current interpreter.
    py_candidates = [
        os.environ.get("COMFY_PYTHON") or "",
        r"F:\ComfyUI_windows_portable\python_embeded\python.exe",
        sys.executable if "sys" in dir() else "",
    ]
    import sys as _sys

    py_candidates.append(_sys.executable)
    py = next((p for p in py_candidates if p and os.path.isfile(p)), _sys.executable)

    # Quick import check
    try:
        chk = subprocess.run(
            [py, "-c", "import demucs"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if chk.returncode != 0:
            return {
                "ok": False,
                "error": "DEMUCS_MISSING",
                "message": (
                    f"demucs not importable in {py}. "
                    "Install: `python -m pip install demucs` then retry mode=demucs. "
                    "Fallback: --mode center_voicey"
                ),
            }
    except Exception as e:
        return {"ok": False, "error": "DEMUCS_CHECK_FAILED", "message": str(e)}

    out_dir = tempfile.mkdtemp(prefix="demucs_")
    try:
        cmd = [
            py,
            "-m",
            "demucs",
            "-n",
            model,
            "--two-stems",
            "vocals",
            "-o",
            out_dir,
            input_path,
        ]
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
            return {"ok": False, "error": "DEMUCS_TIMEOUT", "message": f">{timeout_sec}s"}
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "")[-800:]
            return {
                "ok": False,
                "error": "DEMUCS_FAILED",
                "message": err[:500],
                "returncode": proc.returncode,
            }
        # demucs writes out_dir/<model>/<track_name>/vocals.wav
        vocals = None
        for root, _d, files in os.walk(out_dir):
            for fn in files:
                if fn.lower() == "vocals.wav":
                    vocals = os.path.join(root, fn)
                    break
            if vocals:
                break
        if not vocals or not os.path.isfile(vocals):
            return {
                "ok": False,
                "error": "DEMUCS_NO_VOCALS",
                "message": f"no vocals.wav under {out_dir}",
            }
        # Normalize to mono 48k pcm
        return prepare_driving_audio(
            vocals,
            output_path,
            mode="voicey",
            sample_rate=48000,
            mono=True,
            timeout_sec=timeout_sec,
        )
    finally:
        try:
            shutil.rmtree(out_dir, ignore_errors=True)
        except Exception:
            pass


def normalize_clip_audio(
    input_path: str,
    output_path: str | None = None,
    *,
    sample_rate: int = 48000,
    stereo: bool = True,
    loudnorm: bool = False,
    audio_bitrate: str = "192k",
    timeout_sec: float = 600,
) -> dict[str, Any]:
    """
    Re-encode clip audio for player compatibility.

    InfiniteTalk/VHS often emits 16 kHz mono AAC, which some Windows players
    treat as silent. Default remux keeps video stream, AAC 48 kHz stereo.
    """
    if not os.path.isfile(input_path):
        return {"ok": False, "error": "CLIP_MISSING", "message": input_path}
    out = output_path or input_path
    parent = os.path.dirname(os.path.abspath(out))
    if parent:
        os.makedirs(parent, exist_ok=True)

    # Write via temp if in-place
    tmp_out = out
    in_place = os.path.abspath(out) == os.path.abspath(input_path)
    if in_place:
        fd, tmp_out = tempfile.mkstemp(suffix=".mp4", prefix="norm_audio_")
        os.close(fd)

    af_parts: list[str] = []
    if loudnorm:
        af_parts.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    args: list[str] = ["-i", input_path, "-c:v", "copy"]
    if af_parts:
        args.extend(["-af", ",".join(af_parts)])
    args.extend(
        [
            "-c:a",
            "aac",
            "-ar",
            str(int(sample_rate)),
            "-ac",
            "2" if stereo else "1",
            "-b:a",
            audio_bitrate,
            "-movflags",
            "+faststart",
            tmp_out,
        ]
    )
    result = run_ffmpeg(args, timeout_sec=timeout_sec)
    if not result.get("ok"):
        if in_place and os.path.isfile(tmp_out):
            try:
                os.remove(tmp_out)
            except OSError:
                pass
        return result
    if in_place:
        try:
            os.replace(tmp_out, out)
        except OSError:
            shutil.copy2(tmp_out, out)
            try:
                os.remove(tmp_out)
            except OSError:
                pass
    result["output_path"] = os.path.abspath(out)
    result["sample_rate"] = int(sample_rate)
    result["channels"] = 2 if stereo else 1
    result["loudnorm"] = bool(loudnorm)
    return result


def prepare_driving_audio(
    input_path: str,
    output_path: str,
    *,
    mode: str = "center_voicey",
    sample_rate: int = 48000,
    mono: bool = True,
    timeout_sec: float = 600,
) -> dict[str, Any]:
    """
    Prepare a SI2V driving stem from a mix or dialogue wav.

    FFmpeg modes: copy|voicey|center|vocal_band|center_voicey.
    Optional demucs: true vocal stem if package installed; else clear error.
    """
    if not os.path.isfile(input_path):
        return {"ok": False, "error": "AUDIO_MISSING", "message": input_path}
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    try:
        mode_l = resolve_driving_prep_mode(mode)
    except ValueError as e:
        return {"ok": False, "error": "BAD_MODE", "message": str(e)}

    if mode_l == "demucs":
        r = separate_vocals_demucs(input_path, output_path, timeout_sec=max(timeout_sec, 1800))
        if r.get("ok"):
            r["mode"] = "demucs"
            r["resolved_from"] = (mode or "").strip().lower() or "auto"
        return r

    try:
        af = _driving_af_chain(mode_l)
    except ValueError as e:
        return {"ok": False, "error": "BAD_MODE", "message": str(e)}

    args: list[str] = ["-i", input_path]
    if af:
        args.extend(["-af", af])
    # Force layout after filters that may already emit mono.
    ac = 1 if mono else 2
    args.extend(
        [
            "-c:a",
            "pcm_s16le",
            "-ar",
            str(int(sample_rate)),
            "-ac",
            str(ac),
            output_path,
        ]
    )
    result = run_ffmpeg(args, timeout_sec=timeout_sec)
    result["output_path"] = os.path.abspath(output_path)
    result["mode"] = mode_l
    result["sample_rate"] = int(sample_rate)
    result["channels"] = ac
    return result
