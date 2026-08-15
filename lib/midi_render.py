"""MIDI → WAV. FluidSynth + soundfont if present, else built-in electronic synth."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any

from lib.comfy_client import WORKSPACE_ROOT, fail_result, ok_result
from lib.midi_smf import MidiTrack, read_smf
from lib.midi_synth import synth_render_tracks


def _third_party(*parts: str) -> str:
    return os.path.join(WORKSPACE_ROOT, "third_party", *parts)


def find_fluidsynth() -> str | None:
    env = os.environ.get("FLUIDSYNTH") or os.environ.get("FLUIDSYNTH_PATH")
    if env and os.path.isfile(env):
        return env
    which = shutil.which("fluidsynth")
    if which:
        return which
    root = _third_party("fluidsynth")
    if os.path.isdir(root):
        for dirpath, _dirs, files in os.walk(root):
            if "fluidsynth.exe" in files:
                return os.path.join(dirpath, "fluidsynth.exe")
    return None


def resolve_soundfont(explicit: str | None = None) -> str | None:
    if explicit and os.path.isfile(explicit):
        return os.path.abspath(explicit)
    env = os.environ.get("SOUNDFONT") or os.environ.get("SF2")
    if env and os.path.isfile(env):
        return os.path.abspath(env)
    sf_dir = _third_party("soundfonts")
    if os.path.isdir(sf_dir):
        named = (
            "GeneralUser-GS.sf2",
            "GeneralUser_GS.sf2",
            "FluidR3_GM.sf2",
            "TimGM6mb.sf2",
        )
        for name in named:
            p = os.path.join(sf_dir, name)
            if os.path.isfile(p):
                return os.path.abspath(p)
        for name in sorted(os.listdir(sf_dir)):
            if name.lower().endswith((".sf2", ".sf3")):
                return os.path.abspath(os.path.join(sf_dir, name))
    return None


def preview_render_tracks(
    tracks: list[MidiTrack],
    wav_path: str,
    *,
    bpm: float,
    ticks_per_beat: int = 480,
    sr: int = 44100,
) -> dict[str, Any]:
    return synth_render_tracks(
        tracks,
        wav_path,
        bpm=bpm,
        ticks_per_beat=ticks_per_beat,
        sr=sr,
    )


def render_midi(
    midi_path: str,
    wav_path: str,
    *,
    soundfont: str | None = None,
    engine: str = "auto",
) -> dict[str, Any]:
    if not os.path.isfile(midi_path):
        return fail_result(error="MIDI_MISSING", message=midi_path)
    engine = (engine or "auto").strip().lower()
    if engine not in {"auto", "fluidsynth", "synth"}:
        return fail_result(error="BAD_ENGINE", message=engine)

    if engine in {"auto", "fluidsynth"}:
        exe = find_fluidsynth()
        sf = resolve_soundfont(soundfont)
        if exe and sf:
            parent = os.path.dirname(os.path.abspath(wav_path))
            if parent:
                os.makedirs(parent, exist_ok=True)
            # FluidSynth 2.6: options first, then soundfont, then MIDI.
            cmd = [
                exe,
                "-ni",
                "-F",
                wav_path,
                "-T",
                "wav",
                "-r",
                "44100",
                "-g",
                "0.5",
                sf,
                midi_path,
            ]
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=180,
                )
            except FileNotFoundError as e:
                if engine == "fluidsynth":
                    return fail_result(error="FLUIDSYNTH_MISSING", message=str(e))
            except subprocess.TimeoutExpired:
                return fail_result(error="FLUIDSYNTH_TIMEOUT", message=">180s")
            else:
                if proc.returncode == 0 and os.path.isfile(wav_path):
                    return ok_result(
                        path=os.path.abspath(wav_path),
                        output_path=os.path.abspath(wav_path),
                        engine="fluidsynth",
                        cmd=cmd,
                    )
                if engine == "fluidsynth":
                    err = (proc.stderr or proc.stdout or "")[-500:]
                    return fail_result(error="RENDER_FAILED", message=err or "fluidsynth produced no wav")
        elif engine == "fluidsynth":
            if not exe:
                return fail_result(error="FLUIDSYNTH_MISSING", message="fluidsynth not on PATH")
            return fail_result(error="SOUNDFONT_MISSING", message="pass --soundfont or set SOUNDFONT")

    try:
        tracks, bpm, tpq = read_smf(midi_path)
    except Exception as e:
        return fail_result(error="MIDI_PARSE", message=str(e)[:400])
    return synth_render_tracks(tracks, wav_path, bpm=bpm, ticks_per_beat=tpq)
