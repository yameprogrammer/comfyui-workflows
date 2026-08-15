"""music_skeleton.v1 — harmonic skeleton load/save/extract."""

from __future__ import annotations

import json
import os
import struct
import subprocess
from typing import Any

from lib.comfy_client import fail_result
from lib.music_theory import NOTE_TO_PC, parse_chord

SKELETON_SCHEMA = "music_skeleton.v1"

_MAJ_TMPL = (1.0, 0.0, 0.0, 0.0, 0.8, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0)
_MIN_TMPL = (1.0, 0.0, 0.0, 0.8, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0)


def skeleton_from_symbols(
    symbols: list[str],
    *,
    bpm: float,
    key: str,
    beats_per_chord: int = 4,
    source_path: str | None = None,
) -> dict[str, Any]:
    if not symbols:
        raise ValueError("at least one chord symbol is required")
    bpm = float(bpm)
    if bpm <= 0:
        raise ValueError("bpm must be positive")
    bpc = max(1, int(beats_per_chord))
    sec_per_chord = (bpc * 60.0) / bpm
    chords: list[dict[str, Any]] = []
    t = 0.0
    for i, raw in enumerate(symbols):
        parsed = parse_chord(raw)
        start = t
        end = t + sec_per_chord
        chords.append(
            {
                "start_sec": start,
                "end_sec": end,
                "bar": i + 1,
                "symbol": parsed["symbol"],
                "root": parsed["root"],
                "quality": parsed["quality"],
            }
        )
        t = end
    duration = chords[-1]["end_sec"]
    return {
        "schema": SKELETON_SCHEMA,
        "source": {
            "path": source_path,
            "duration_sec": duration,
            "kind": "chord_symbols",
        },
        "key": str(key or "C"),
        "mode": "minor" if chords and chords[0]["quality"] in {"min", "min7"} else "major",
        "bpm": bpm,
        "time_signature": [4, 4],
        "keep_available": ["harmony_only", "contour"],
        "chords": chords,
        "sections": [{"name": "A", "start_sec": 0.0, "end_sec": duration}],
        "melody_contour": [],
    }


def save_skeleton(skel: dict, path: str) -> str:
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(skel, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return os.path.abspath(path)


def load_skeleton(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("skeleton JSON must be an object")
    if data.get("schema") not in (None, SKELETON_SCHEMA):
        raise ValueError(f"unsupported skeleton schema {data.get('schema')!r}")
    data["schema"] = SKELETON_SCHEMA
    if not data.get("chords"):
        raise ValueError("skeleton has no chords")
    return data


def _decode_mono_f32(audio_path: str, sr: int = 22050) -> tuple[list[float] | Any, int]:
    from lib.ffmpeg_util import find_ffmpeg

    ff = find_ffmpeg()
    proc = subprocess.run(
        [ff, "-v", "error", "-i", audio_path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout:
        raise RuntimeError((proc.stderr or b"").decode("utf-8", "replace")[-400:] or "ffmpeg decode failed")
    n = len(proc.stdout) // 4
    samples = struct.unpack("<" + "f" * n, proc.stdout[: n * 4])
    try:
        import numpy as np

        return np.frombuffer(proc.stdout[: n * 4], dtype="<f4"), sr
    except ImportError:
        return list(samples), sr


def _dot(a: Any, b: Any) -> float:
    return float(sum(float(x) * float(y) for x, y in zip(a, b)))


def _norm(a: Any) -> float:
    return float(sum(float(x) * float(x) for x in a) ** 0.5) or 1.0


def _chroma_frame(frame: Any, sr: int) -> list[float]:
    try:
        import numpy as np

        spec = np.abs(np.fft.rfft(frame * np.hanning(len(frame))))
        freqs = np.fft.rfftfreq(len(frame), 1.0 / sr)
        chroma = [0.0] * 12
        for mag, freq in zip(spec, freqs):
            if freq < 50 or freq > 2000:
                continue
            midi = 69 + 12 * np.log2(freq / 440.0)
            pc = int(round(midi)) % 12
            chroma[pc] += float(mag)
        return chroma
    except ImportError as e:
        raise RuntimeError("CHROMA_BACKEND_MISSING") from e


def _best_chord(chroma: list[float]) -> tuple[str, str, float]:
    best = ("C", "maj", -1.0)
    cn = _norm(chroma)
    for root, pc in NOTE_TO_PC.items():
        if len(root) == 2 and root[1] == "b":
            continue
        if root in {"B#", "E#", "Fb", "Cb"}:
            continue
        for quality, tmpl in (("maj", _MAJ_TMPL), ("min", _MIN_TMPL)):
            rot = tmpl[-pc:] + tmpl[:-pc] if pc else tmpl
            score = _dot(chroma, rot) / (cn * _norm(rot))
            if score > best[2]:
                best = (root, quality, score)
    return best


def extract_skeleton(audio_path: str, *, hop_sec: float = 0.5) -> dict:
    if not os.path.isfile(audio_path):
        return fail_result(error="SOURCE_MISSING", message=audio_path)
    try:
        import numpy as np  # noqa: F401
    except ImportError:
        return fail_result(
            error="CHROMA_BACKEND_MISSING",
            message="numpy is required for audio extract; use --chords instead",
        )
    try:
        samples, sr = _decode_mono_f32(audio_path)
    except Exception as e:
        return fail_result(error="DECODE_FAILED", message=str(e)[:400])

    import numpy as np

    x = np.asarray(samples, dtype=np.float32)
    if x.size < 2048:
        return fail_result(error="AUDIO_TOO_SHORT", message="need at least ~0.1s")
    hop = max(256, int(float(hop_sec) * sr))
    win = 4096
    chromas: list[list[float]] = []
    flux: list[float] = []
    prev = None
    for start in range(0, max(1, x.size - win), hop):
        frame = x[start : start + win]
        if frame.size < win:
            frame = np.pad(frame, (0, win - frame.size))
        ch = _chroma_frame(frame, sr)
        chromas.append(ch)
        spec = np.abs(np.fft.rfft(frame * np.hanning(len(frame))))
        if prev is not None:
            flux.append(float(np.maximum(spec - prev, 0).sum()))
        prev = spec

    bpm = 96.0
    if len(flux) > 8:
        f = np.asarray(flux, dtype=np.float64)
        f = f - f.mean()
        corr = np.correlate(f, f, mode="full")[len(f) - 1 :]
        min_lag = max(1, int(0.3 / hop_sec))
        max_lag = max(min_lag + 1, int(2.0 / hop_sec))
        sl = corr[min_lag:max_lag]
        if sl.size:
            lag = int(np.argmax(sl)) + min_lag
            beat_sec = lag * hop_sec
            if beat_sec > 0:
                bpm = max(60.0, min(180.0, 60.0 / beat_sec))

    hold_frames = max(1, int(round((60.0 / bpm) / hop_sec)))
    chords: list[dict[str, Any]] = []
    if chromas:
        cur_root, cur_q, _ = _best_chord(chromas[0])
        run = 1
        start_i = 0
        for i, ch in enumerate(chromas[1:], start=1):
            root, q, _ = _best_chord(ch)
            if root == cur_root and q == cur_q:
                run += 1
                continue
            if run >= hold_frames or not chords:
                symbol = cur_root + ("" if cur_q == "maj" else "m")
                chords.append(
                    {
                        "start_sec": start_i * hop_sec,
                        "end_sec": i * hop_sec,
                        "bar": len(chords) + 1,
                        "symbol": symbol,
                        "root": cur_root,
                        "quality": cur_q,
                    }
                )
                start_i = i
            cur_root, cur_q, run = root, q, 1
        symbol = cur_root + ("" if cur_q == "maj" else "m")
        end_sec = len(chromas) * hop_sec
        if not chords or chords[-1]["symbol"] != symbol:
            chords.append(
                {
                    "start_sec": start_i * hop_sec,
                    "end_sec": end_sec,
                    "bar": len(chords) + 1,
                    "symbol": symbol,
                    "root": cur_root,
                    "quality": cur_q,
                }
            )
        else:
            chords[-1]["end_sec"] = end_sec

    if not chords:
        chords = [
            {
                "start_sec": 0.0,
                "end_sec": 4.0,
                "bar": 1,
                "symbol": "C",
                "root": "C",
                "quality": "maj",
            }
        ]

    roots = [c["root"] for c in chords]
    key = max(set(roots), key=roots.count)
    min_n = sum(1 for c in chords if c["quality"] == "min")
    mode = "minor" if min_n > len(chords) / 2 else "major"
    duration = float(chords[-1]["end_sec"])
    bar_sec = 4.0 * 60.0 / bpm
    sections = []
    t = 0.0
    name_i = 0
    labels = "ABCDEFGH"
    while t < duration:
        nxt = min(duration, t + 8 * bar_sec)
        sections.append({"name": labels[name_i % len(labels)], "start_sec": t, "end_sec": nxt})
        t = nxt
        name_i += 1
    return {
        "schema": SKELETON_SCHEMA,
        "source": {"path": os.path.abspath(audio_path), "duration_sec": duration, "kind": "local_audio"},
        "key": key,
        "mode": mode,
        "bpm": round(float(bpm), 2),
        "time_signature": [4, 4],
        "keep_available": ["harmony_only", "contour"],
        "chords": chords,
        "sections": sections or [{"name": "A", "start_sec": 0.0, "end_sec": duration}],
        "melody_contour": [],
    }


def parse_chord_list(text: str) -> list[str]:
    parts = [p.strip() for p in (text or "").replace("|", ",").split(",")]
    return [p for p in parts if p]
