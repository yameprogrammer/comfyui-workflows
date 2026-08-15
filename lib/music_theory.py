"""Chord symbols, transposition, GM helpers. No I/O."""

from __future__ import annotations

import re
from typing import Any

NOTE_TO_PC: dict[str, int] = {
    "C": 0,
    "B#": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "Fb": 4,
    "F": 5,
    "E#": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
    "Cb": 11,
}
PC_TO_NOTE = {
    0: "C",
    1: "C#",
    2: "D",
    3: "Eb",
    4: "E",
    5: "F",
    6: "F#",
    7: "G",
    8: "Ab",
    9: "A",
    10: "Bb",
    11: "B",
}

_CHORD_RE = re.compile(
    r"^\s*([A-G](?:#|b)?)"
    r"(maj7|min7|mmaj7|maj|min|dim|aug|sus4|sus2|add9|m7|m|7)?"
    r"(?:/([A-G](?:#|b)?))?\s*$",
    re.I,
)

GM_PROGRAMS = {
    "piano": 0,
    "guitar": 24,
    "steel_guitar": 25,
    "bass": 33,
    "slap_bass": 36,
    "pad": 88,
    "square": 80,
    "drums": 0,
}

_VOICINGS = {
    "maj": (0, 4, 7),
    "min": (0, 3, 7),
    "dim": (0, 3, 6),
    "aug": (0, 4, 8),
    "7": (0, 4, 7, 10),
    "maj7": (0, 4, 7, 11),
    "min7": (0, 3, 7, 10),
    "sus2": (0, 2, 7),
    "sus4": (0, 5, 7),
}

_SUFFIX_QUALITY = {
    "": "maj",
    "maj": "maj",
    "add9": "maj",
    "m": "min",
    "min": "min",
    "7": "7",
    "maj7": "maj7",
    "m7": "min7",
    "min7": "min7",
    "mmaj7": "min",
    "dim": "dim",
    "aug": "aug",
    "sus2": "sus2",
    "sus4": "sus4",
}

_QUALITY_SUFFIX = {
    "maj": "",
    "min": "m",
    "7": "7",
    "maj7": "maj7",
    "min7": "m7",
    "dim": "dim",
    "aug": "aug",
    "sus2": "sus2",
    "sus4": "sus4",
}


def _norm_note(name: str) -> str:
    n = (name or "").strip()
    if not n:
        raise ValueError("empty note name")
    if len(n) >= 2 and n[1] in "#b":
        letter = n[0].upper() + n[1]
    else:
        letter = n[0].upper()
    if letter not in NOTE_TO_PC:
        raise ValueError(f"Unknown note {name!r}")
    return letter


def parse_chord(symbol: str) -> dict[str, Any]:
    raw = (symbol or "").strip()
    if not raw:
        raise ValueError("empty chord symbol")
    m = _CHORD_RE.match(raw)
    if not m:
        raise ValueError(f"Unparseable chord {symbol!r}")
    root = _norm_note(m.group(1))
    suf = (m.group(2) or "").lower()
    quality = _SUFFIX_QUALITY.get(suf)
    if quality is None:
        raise ValueError(f"Unknown chord quality in {symbol!r}")
    bass = _norm_note(m.group(3)) if m.group(3) else None
    return {
        "root": root,
        "quality": quality,
        "bass": bass,
        "symbol": raw.replace(" ", ""),
    }


def transpose_root(root: str, semitones: int) -> str:
    pc = NOTE_TO_PC[_norm_note(root)]
    return PC_TO_NOTE[(pc + int(semitones)) % 12]


def transpose_symbol(symbol: str, semitones: int) -> str:
    c = parse_chord(symbol)
    root = transpose_root(c["root"], semitones)
    out = root + _QUALITY_SUFFIX.get(c["quality"], "")
    if c["bass"]:
        out += "/" + transpose_root(c["bass"], semitones)
    return out


def voicing_midis(symbol: str, *, octave: int = 4) -> list[int]:
    c = parse_chord(symbol)
    root_pc = NOTE_TO_PC[c["root"]]
    # Scientific pitch: MIDI 60 = C4 → 12 * (octave + 1) + pc
    base = 12 * (int(octave) + 1) + root_pc
    ivs = _VOICINGS.get(c["quality"], (0, 4, 7))
    notes = [base + i for i in ivs]
    if c["bass"]:
        bass = 12 * int(octave) + NOTE_TO_PC[c["bass"]]
        notes = [bass] + notes
    return notes


def gm_program(name: str) -> int:
    key = (name or "piano").strip().lower()
    if key not in GM_PROGRAMS:
        known = ", ".join(sorted(GM_PROGRAMS))
        raise KeyError(f"Unknown GM instrument {name!r}. Known: {known}")
    return GM_PROGRAMS[key]
