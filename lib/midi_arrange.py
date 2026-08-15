"""Rule-based genre arrangement from a harmonic skeleton."""

from __future__ import annotations

from typing import Any

from lib.midi_smf import MidiNote, MidiTrack
from lib.music_theory import gm_program, parse_chord, transpose_symbol, voicing_midis

GENRES: tuple[str, ...] = (
    "acoustic_ballad",
    "lofi_hiphop",
    "band_rock",
    "edm_pulse",
    "piano_pop",
)

KEEP_MODES: tuple[str, ...] = ("harmony_only", "contour")

ARRANGEMENT_SCHEMA = "midi_arrangement.v1"

_GENRE_INSTRUMENTS: dict[str, list[str]] = {
    "acoustic_ballad": ["drums", "bass", "guitar", "pad"],
    "lofi_hiphop": ["drums", "bass", "pad"],
    "band_rock": ["drums", "bass", "guitar"],
    "edm_pulse": ["drums", "bass", "pad", "piano"],
    "piano_pop": ["drums", "bass", "piano"],
}

_KICK = 36
_SNARE = 38
_HAT = 42


def validate_arrangement(arr: dict) -> dict:
    if not isinstance(arr, dict):
        raise ValueError("arrangement must be an object")
    genre = str(arr.get("genre") or "piano_pop").strip()
    if genre not in GENRES:
        raise ValueError(f"Unknown genre {genre!r}. Known: {', '.join(GENRES)}")
    keep = str(arr.get("keep") or "harmony_only").strip()
    if keep not in KEEP_MODES:
        raise ValueError(f"Unknown keep {keep!r}. Known: {', '.join(KEEP_MODES)}")
    bpm = float(arr.get("bpm") or 96)
    if bpm <= 0:
        raise ValueError("bpm must be positive")
    bars = int(arr.get("bars") or 8)
    if bars < 1:
        raise ValueError("bars must be >= 1")
    instruments = arr.get("instruments")
    if not instruments:
        instruments = list(_GENRE_INSTRUMENTS[genre])
    else:
        instruments = [str(x).strip() for x in instruments if str(x).strip()]
    out = dict(arr)
    out["schema"] = ARRANGEMENT_SCHEMA
    out["genre"] = genre
    out["keep"] = keep
    out["bpm"] = bpm
    out["key"] = str(arr.get("key") or "C")
    out["transpose"] = int(arr.get("transpose") or 0)
    out["bars"] = bars
    out["density"] = str(arr.get("density") or "sparse")
    out["instruments"] = instruments
    out["human_brief"] = str(arr.get("human_brief") or "")
    return out


def default_arrangement(
    *,
    genre: str,
    bpm: float,
    key: str,
    bars: int,
    keep: str = "harmony_only",
) -> dict:
    return validate_arrangement(
        {
            "schema": ARRANGEMENT_SCHEMA,
            "genre": genre,
            "keep": keep,
            "bpm": bpm,
            "key": key,
            "transpose": 0,
            "bars": bars,
            "density": "sparse",
            "instruments": list(_GENRE_INSTRUMENTS.get(genre, _GENRE_INSTRUMENTS["piano_pop"])),
            "human_brief": "",
        }
    )


def chords_from_skeleton(skeleton: dict, *, transpose: int = 0) -> list[dict]:
    raw = list(skeleton.get("chords") or [])
    out: list[dict] = []
    for item in raw:
        symbol = str(item.get("symbol") or "")
        parsed = parse_chord(symbol)
        if transpose:
            symbol = transpose_symbol(symbol, transpose)
            parsed = parse_chord(symbol)
        row = dict(item)
        row["symbol"] = symbol
        row["root"] = parsed["root"]
        row["quality"] = parsed["quality"]
        out.append(row)
    return out


def _sec_to_tick(sec: float, bpm: float, tpq: int) -> int:
    return max(0, int(round(float(sec) * float(bpm) / 60.0 * tpq)))


def _expand_chords(
    chords: list[dict],
    *,
    bpm: float,
    bars: int,
    tpq: int,
) -> list[dict]:
    bar_ticks = 4 * tpq
    target = bars * bar_ticks
    if not chords:
        raise ValueError("skeleton has no chords")
    timed: list[dict] = []
    if all("start_sec" in c and "end_sec" in c for c in chords):
        for c in chords:
            start = _sec_to_tick(c["start_sec"], bpm, tpq)
            end = _sec_to_tick(c["end_sec"], bpm, tpq)
            if end <= start:
                end = start + bar_ticks
            row = dict(c)
            row["start_tick"] = start
            row["end_tick"] = end
            timed.append(row)
    else:
        cursor = 0
        for c in chords:
            row = dict(c)
            row["start_tick"] = cursor
            row["end_tick"] = cursor + bar_ticks
            timed.append(row)
            cursor += bar_ticks
    span = timed[-1]["end_tick"] - timed[0]["start_tick"]
    if span <= 0:
        span = bar_ticks
    origin = timed[0]["start_tick"]
    expanded: list[dict] = []
    while True:
        for c in timed:
            start = origin + (c["start_tick"] - timed[0]["start_tick"])
            end = origin + (c["end_tick"] - timed[0]["start_tick"])
            if start >= target:
                return expanded
            row = dict(c)
            row["start_tick"] = start
            row["end_tick"] = min(end, target)
            expanded.append(row)
            if row["end_tick"] >= target:
                return expanded
        origin += span
        if origin >= target:
            return expanded


def _add_note(events: list[MidiNote], pitch: int, start: int, dur: int, vel: int = 80) -> None:
    if dur <= 0:
        return
    events.append(MidiNote(pitch=int(pitch), start_tick=int(start), duration_tick=int(dur), velocity=int(vel)))


def _pattern_drums(genre: str, start: int, end: int, tpq: int) -> list[MidiNote]:
    evs: list[MidiNote] = []
    bar = 4 * tpq
    eighth = tpq // 2
    sixteenth = tpq // 4
    t = start
    while t < end:
        bar_end = min(t + bar, end)
        if genre == "edm_pulse":
            q = t
            while q < bar_end:
                _add_note(evs, _KICK, q, min(eighth, bar_end - q), 100)
                q += tpq
            h = t
            while h < bar_end:
                _add_note(evs, _HAT, h, min(sixteenth, bar_end - h), 50)
                h += sixteenth
        elif genre == "lofi_hiphop":
            _add_note(evs, _KICK, t, eighth, 96)
            late = t + tpq + eighth + (eighth // 2)
            if late < bar_end:
                _add_note(evs, _KICK, late, eighth, 88)
            _add_note(evs, _SNARE, t + tpq, eighth, 100)
            _add_note(evs, _SNARE, t + 3 * tpq, eighth, 100)
            h = t
            while h < bar_end:
                _add_note(evs, _HAT, h, min(eighth, bar_end - h), 45)
                h += eighth
        elif genre == "piano_pop":
            _add_note(evs, _KICK, t, eighth, 92)
            _add_note(evs, _SNARE, t + 2 * tpq, eighth, 96)
            h = t
            while h < bar_end:
                _add_note(evs, _HAT, h, min(eighth, bar_end - h), 48)
                h += eighth
        else:
            # acoustic_ballad / band_rock
            _add_note(evs, _KICK, t, eighth, 94)
            _add_note(evs, _KICK, t + 2 * tpq, eighth, 90)
            if genre == "band_rock":
                _add_note(evs, _SNARE, t + tpq, eighth, 104)
                _add_note(evs, _SNARE, t + 3 * tpq, eighth, 104)
            h = t
            vel = 32 if genre == "acoustic_ballad" else 55
            while h < bar_end:
                _add_note(evs, _HAT, h, min(eighth, bar_end - h), vel)
                h += eighth
        t += bar
    return evs


def _pattern_bass(genre: str, symbol: str, start: int, end: int, tpq: int) -> list[MidiNote]:
    evs: list[MidiNote] = []
    parsed = parse_chord(symbol)
    from lib.music_theory import NOTE_TO_PC

    root = 36 + NOTE_TO_PC[parsed["root"]]
    fifth = root + 7
    eighth = tpq // 2
    if genre in {"band_rock", "edm_pulse"}:
        t = start
        while t < end:
            _add_note(evs, root, t, min(eighth - 8, end - t), 92)
            t += eighth
    elif genre == "lofi_hiphop":
        mid = start + (end - start) // 2
        _add_note(evs, root, start, max(1, mid - start - 10), 88)
        if mid < end:
            _add_note(evs, fifth, mid, max(1, end - mid - 10), 80)
    else:
        # acoustic / piano_pop: root on 1 and 3 if the span is long enough
        _add_note(evs, root, start, min(tpq, end - start), 86)
        third = start + 2 * tpq
        if third < end:
            _add_note(evs, root, third, min(tpq, end - third), 80)
    return evs


def _pattern_comp(
    genre: str,
    symbol: str,
    start: int,
    end: int,
    tpq: int,
    *,
    instrument: str,
) -> list[MidiNote]:
    evs: list[MidiNote] = []
    octave = 3 if instrument == "pad" else 4
    notes = voicing_midis(symbol, octave=octave)
    eighth = tpq // 2
    if instrument == "pad" or genre == "lofi_hiphop":
        dur = max(1, end - start - 8)
        vel = 48 if instrument == "pad" else 56
        for p in notes[:3]:
            _add_note(evs, p, start, dur, vel)
        return evs
    if genre == "acoustic_ballad":
        t = start
        while t < end:
            for p in notes[:3]:
                _add_note(evs, p, t, min(tpq - 12, end - t), 62)
            t += tpq
        return evs
    if genre == "band_rock":
        t = start
        while t < end:
            for p in notes[:3]:
                _add_note(evs, p, t, min(eighth - 10, end - t), 78)
            t += eighth
        return evs
    if genre == "edm_pulse" and instrument == "piano":
        t = start + eighth
        while t < end:
            _add_note(evs, notes[0], t, min(eighth - 8, end - t), 70)
            t += tpq
        return evs
    # piano_pop broken triad
    cycle = notes[:3] or [60]
    t = start
    i = 0
    while t < end:
        _add_note(evs, cycle[i % len(cycle)], t, min(eighth - 6, end - t), 72)
        t += eighth
        i += 1
    return evs


def _lead_from_contour(skeleton: dict, *, bpm: float, tpq: int, transpose: int) -> list[MidiNote]:
    evs: list[MidiNote] = []
    for item in skeleton.get("melody_contour") or []:
        start = _sec_to_tick(float(item.get("t") or 0.0), bpm, tpq)
        dur = _sec_to_tick(float(item.get("dur") or 0.25), bpm, tpq)
        pitch = int(item.get("midi") or 60) + int(transpose)
        _add_note(evs, pitch, start, max(1, dur), 110)
    return evs


def arrange(
    skeleton: dict,
    arrangement: dict,
    *,
    ticks_per_beat: int = 480,
) -> list[MidiTrack]:
    spec = validate_arrangement(arrangement)
    bpm = float(skeleton.get("bpm") or spec["bpm"])
    spec["bpm"] = float(spec.get("bpm") or bpm)
    bpm = float(spec["bpm"])
    tpq = int(ticks_per_beat)
    chords = _expand_chords(
        chords_from_skeleton(skeleton, transpose=int(spec["transpose"])),
        bpm=bpm,
        bars=int(spec["bars"]),
        tpq=tpq,
    )
    genre = spec["genre"]
    wanted = set(spec["instruments"])
    tracks: list[MidiTrack] = []

    if "drums" in wanted:
        drum_notes: list[MidiNote] = []
        span_start = chords[0]["start_tick"]
        span_end = chords[-1]["end_tick"]
        drum_notes.extend(_pattern_drums(genre, span_start, span_end, tpq))
        tracks.append(MidiTrack("drums", 9, None, drum_notes))

    if "bass" in wanted:
        bass_notes: list[MidiNote] = []
        for c in chords:
            bass_notes.extend(_pattern_bass(genre, c["symbol"], c["start_tick"], c["end_tick"], tpq))
        tracks.append(MidiTrack("bass", 1, gm_program("bass"), bass_notes))

    if "guitar" in wanted:
        g_notes: list[MidiNote] = []
        for c in chords:
            g_notes.extend(
                _pattern_comp(genre, c["symbol"], c["start_tick"], c["end_tick"], tpq, instrument="guitar")
            )
        tracks.append(MidiTrack("guitar", 2, gm_program("guitar"), g_notes))

    if "piano" in wanted:
        p_notes: list[MidiNote] = []
        for c in chords:
            p_notes.extend(
                _pattern_comp(genre, c["symbol"], c["start_tick"], c["end_tick"], tpq, instrument="piano")
            )
        tracks.append(MidiTrack("piano", 3, gm_program("piano"), p_notes))

    if "pad" in wanted:
        pad_notes: list[MidiNote] = []
        for c in chords:
            pad_notes.extend(
                _pattern_comp(genre, c["symbol"], c["start_tick"], c["end_tick"], tpq, instrument="pad")
            )
        tracks.append(MidiTrack("pad", 4, gm_program("pad"), pad_notes))

    if spec["keep"] == "contour":
        lead = _lead_from_contour(skeleton, bpm=bpm, tpq=tpq, transpose=int(spec["transpose"]))
        if lead:
            tracks.append(MidiTrack("lead", 5, gm_program("square"), lead))

    if not tracks:
        raise ValueError("arrangement produced no tracks")
    return tracks
