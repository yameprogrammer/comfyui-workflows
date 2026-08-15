"""Built-in electronic-instrument preview (numpy). No soundfont required."""

from __future__ import annotations

import os
import wave
from typing import Any

from lib.comfy_client import fail_result, ok_result
from lib.midi_smf import MidiTrack


def _midi_hz(pitch: int) -> float:
    return 440.0 * (2.0 ** ((int(pitch) - 69) / 12.0))


def synth_render_tracks(
    tracks: list[MidiTrack],
    wav_path: str,
    *,
    bpm: float,
    ticks_per_beat: int = 480,
    sr: int = 44100,
) -> dict[str, Any]:
    try:
        import numpy as np
    except ImportError:
        return fail_result(error="NUMPY_MISSING", message="numpy required for built-in synth")

    max_tick = 0
    for tr in tracks:
        for n in tr.events:
            max_tick = max(max_tick, int(n.start_tick) + int(n.duration_tick))
    if max_tick <= 0:
        return fail_result(error="EMPTY_MIDI", message="no notes to render")

    sec_per_tick = (60.0 / float(bpm)) / float(ticks_per_beat)
    n_samples = int(max_tick * sec_per_tick * sr) + int(0.4 * sr)
    mix = np.zeros(n_samples, dtype=np.float32)

    def _stamp(start_s: float, sig: Any) -> None:
        a0 = int(start_s * sr)
        if a0 >= n_samples or a0 < 0:
            return
        a1 = min(n_samples, a0 + len(sig))
        mix[a0:a1] += sig[: a1 - a0]

    def _tone(
        freq: float,
        dur_s: float,
        amp: float,
        *,
        attack: float,
        decay: float,
        harmonics: list[tuple[int, float]],
    ) -> Any:
        n = max(8, int((dur_s + decay * 2.2) * sr))
        t = np.arange(n, dtype=np.float32) / sr
        att = np.minimum(t / max(1e-4, attack), 1.0)
        env = att * np.exp(-t / max(1e-3, decay))
        sig = np.zeros(n, dtype=np.float32)
        for k, a in harmonics:
            sig += a * np.sin(2.0 * np.pi * freq * k * t).astype(np.float32)
        return (amp * env * sig).astype(np.float32)

    def _kick(dur_s: float, amp: float) -> Any:
        n = max(8, int(0.22 * sr))
        t = np.arange(n, dtype=np.float32) / sr
        freq = 140.0 * np.exp(-t * 22.0) + 38.0
        phase = np.cumsum(freq) * (2.0 * np.pi / sr)
        env = np.exp(-t * 16.0)
        click = np.exp(-t * 80.0) * np.sin(2.0 * np.pi * 900.0 * t)
        return (amp * env * np.sin(phase) + 0.12 * amp * click).astype(np.float32)

    def _snare(amp: float) -> Any:
        n = max(8, int(0.12 * sr))
        t = np.arange(n, dtype=np.float32) / sr
        env = np.exp(-t * 28.0)
        body = 0.7 * np.sin(2.0 * np.pi * 190.0 * t) + 0.35 * np.sin(2.0 * np.pi * 330.0 * t)
        return (amp * env * body).astype(np.float32)

    def _hat(amp: float) -> Any:
        n = max(8, int(0.035 * sr))
        t = np.arange(n, dtype=np.float32) / sr
        env = np.exp(-t * 90.0)
        metal = (
            np.sin(2.0 * np.pi * 2450.0 * t)
            + 0.6 * np.sin(2.0 * np.pi * 3170.0 * t)
            + 0.35 * np.sin(2.0 * np.pi * 4120.0 * t)
        )
        return (amp * env * metal).astype(np.float32)

    for tr in tracks:
        name = (tr.name or "").lower()
        ch = int(tr.channel)
        prog = 0 if tr.program is None else int(tr.program)
        role = name
        if ch == 9 or role == "drums":
            role = "drums"
        elif role not in {"bass", "guitar", "piano", "pad", "lead"}:
            if prog in {32, 33, 34, 36}:
                role = "bass"
            elif prog in {24, 25, 27, 29, 30}:
                role = "guitar"
            elif prog in {80, 81, 82}:
                role = "lead"
            elif prog in {88, 89, 90, 91, 92}:
                role = "pad"
            else:
                role = "piano"

        for n in tr.events:
            start_s = n.start_tick * sec_per_tick
            dur_s = max(0.03, n.duration_tick * sec_per_tick)
            vel = max(1, min(127, int(n.velocity))) / 127.0
            if role == "drums":
                p = int(n.pitch)
                if p <= 36:
                    _stamp(start_s, _kick(dur_s, 0.55 * vel))
                elif p <= 40:
                    _stamp(start_s, _snare(0.32 * vel))
                else:
                    _stamp(start_s, _hat(0.16 * vel))
                continue
            freq = _midi_hz(n.pitch)
            if role == "bass":
                sig = _tone(
                    freq,
                    dur_s,
                    0.38 * vel,
                    attack=0.006,
                    decay=0.28,
                    harmonics=[(1, 1.0), (2, 0.28), (3, 0.08)],
                )
            elif role == "lead":
                sig = _tone(
                    freq,
                    dur_s,
                    0.26 * vel,
                    attack=0.01,
                    decay=0.22,
                    harmonics=[(1, 1.0), (2, 0.45), (3, 0.22), (4, 0.12), (5, 0.07)],
                )
            elif role == "pad":
                sig = _tone(
                    freq * 0.997,
                    dur_s,
                    0.11 * vel,
                    attack=0.08,
                    decay=0.55,
                    harmonics=[(1, 1.0), (2, 0.2)],
                )
                sig2 = _tone(
                    freq * 1.003,
                    dur_s,
                    0.11 * vel,
                    attack=0.08,
                    decay=0.55,
                    harmonics=[(1, 1.0), (3, 0.12)],
                )
                nmin = min(len(sig), len(sig2))
                sig = sig[:nmin] + sig2[:nmin]
            elif role == "guitar":
                sig = _tone(
                    freq,
                    dur_s,
                    0.18 * vel,
                    attack=0.008,
                    decay=0.18,
                    harmonics=[(1, 1.0), (2, 0.35), (3, 0.18), (4, 0.08)],
                )
            else:
                sig = _tone(
                    freq,
                    dur_s,
                    0.20 * vel,
                    attack=0.004,
                    decay=0.32,
                    harmonics=[(1, 1.0), (2, 0.4), (3, 0.18), (4, 0.08), (6, 0.04)],
                )
            _stamp(start_s, sig)

    peak = float(np.max(np.abs(mix)) or 1.0)
    mix = np.clip(mix / peak * 0.88, -1.0, 1.0)
    pcm = (mix * 32767.0).astype("<i2")
    parent = os.path.dirname(os.path.abspath(wav_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return ok_result(
        path=os.path.abspath(wav_path),
        output_path=os.path.abspath(wav_path),
        preview=True,
        engine="numpy_synth",
        sr=sr,
    )
