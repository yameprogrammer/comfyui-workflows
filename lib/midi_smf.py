"""Minimal SMF Type-1 writer. No external MIDI library."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class MidiNote:
    pitch: int
    start_tick: int
    duration_tick: int
    velocity: int = 80


@dataclass
class MidiTrack:
    name: str
    channel: int
    program: int | None
    events: list[MidiNote] = field(default_factory=list)


def _vlq(value: int) -> bytes:
    value = max(0, int(value))
    buf = [value & 0x7F]
    value >>= 7
    while value:
        buf.append(0x80 | (value & 0x7F))
        value >>= 7
    return bytes(reversed(buf))


def _chunk(tag: bytes, payload: bytes) -> bytes:
    return tag + len(payload).to_bytes(4, "big") + payload


def _meta(delta: int, meta_type: int, data: bytes) -> bytes:
    return _vlq(delta) + bytes([0xFF, meta_type, len(data)]) + data


def _encode_track(raw_events: list[bytes]) -> bytes:
    body = b"".join(raw_events) + _meta(0, 0x2F, b"")
    return _chunk(b"MTrk", body)


def write_smf(
    path: str,
    tracks: list[MidiTrack],
    *,
    bpm: float,
    ticks_per_beat: int = 480,
) -> str:
    if not tracks:
        raise ValueError("write_smf requires at least one track")
    us = max(1, int(round(60_000_000 / float(bpm))))
    tempo_track = [
        _meta(0, 0x51, us.to_bytes(3, "big")),
        _meta(0, 0x58, bytes([4, 2, 24, 8])),
    ]
    encoded = [_encode_track(tempo_track)]
    for tr in tracks:
        ch = int(tr.channel) & 0x0F
        evs: list[tuple[int, int, bytes]] = []
        if tr.name:
            name = tr.name.encode("ascii", "replace")[:32]
            evs.append((0, 0, bytes([0xFF, 0x03, len(name)]) + name))
        if tr.program is not None and ch != 9:
            evs.append((0, 1, bytes([0xC0 | ch, int(tr.program) & 0x7F])))
        for n in tr.events:
            p = max(0, min(127, int(n.pitch)))
            v = max(1, min(127, int(n.velocity)))
            on = int(n.start_tick)
            off = on + max(1, int(n.duration_tick))
            evs.append((on, 2, bytes([0x90 | ch, p, v])))
            evs.append((off, 3, bytes([0x80 | ch, p, 0])))
        evs.sort(key=lambda item: (item[0], item[1]))
        raw: list[bytes] = []
        last = 0
        for tick, _ord, payload in evs:
            raw.append(_vlq(tick - last) + payload)
            last = tick
        encoded.append(_encode_track(raw))
    header = _chunk(
        b"MThd",
        bytes([0, 1])
        + len(encoded).to_bytes(2, "big")
        + int(ticks_per_beat).to_bytes(2, "big"),
    )
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as f:
        f.write(header + b"".join(encoded))
    return os.path.abspath(path)


def _read_vlq(data: bytes, i: int) -> tuple[int, int]:
    value = 0
    while i < len(data):
        b = data[i]
        i += 1
        value = (value << 7) | (b & 0x7F)
        if b < 0x80:
            return value, i
    return value, i


def read_smf(path: str) -> tuple[list[MidiTrack], float, int]:
    """Parse a Type-0/1 SMF written by this module (and typical note/program/tempo)."""
    raw = open(path, "rb").read()
    if raw[:4] != b"MThd" or len(raw) < 14:
        raise ValueError(f"not an SMF: {path}")
    hdr_len = int.from_bytes(raw[4:8], "big")
    fmt = int.from_bytes(raw[8:10], "big")
    ntrks = int.from_bytes(raw[10:12], "big")
    tpq = int.from_bytes(raw[12:14], "big")
    if tpq <= 0:
        raise ValueError("bad ticks_per_beat")
    i = 8 + hdr_len
    bpm = 120.0
    tracks: list[MidiTrack] = []
    for _ in range(ntrks):
        if i + 8 > len(raw) or raw[i : i + 4] != b"MTrk":
            break
        tlen = int.from_bytes(raw[i + 4 : i + 8], "big")
        body = raw[i + 8 : i + 8 + tlen]
        i += 8 + tlen
        name = ""
        program: int | None = None
        channel = 0
        tick = 0
        pending: dict[tuple[int, int], tuple[int, int]] = {}
        notes: list[MidiNote] = []
        j = 0
        status = 0
        while j < len(body):
            delta, j = _read_vlq(body, j)
            tick += delta
            if j >= len(body):
                break
            b0 = body[j]
            if b0 >= 0x80:
                status = b0
                j += 1
            if status == 0xFF:
                if j + 1 > len(body):
                    break
                meta = body[j]
                j += 1
                mlen, j = _read_vlq(body, j)
                data = body[j : j + mlen]
                j += mlen
                if meta == 0x2F:
                    break
                if meta == 0x51 and len(data) == 3:
                    us = int.from_bytes(data, "big")
                    if us:
                        bpm = 60_000_000 / us
                elif meta == 0x03:
                    name = data.decode("ascii", "replace")
                continue
            if status == 0xF0 or status == 0xF7:
                slen, j = _read_vlq(body, j)
                j += slen
                continue
            hi, lo = status & 0xF0, status & 0x0F
            if hi in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
                if j + 2 > len(body):
                    break
                d1, d2 = body[j], body[j + 1]
                j += 2
                if hi == 0x90 and d2 > 0:
                    pending[(lo, d1)] = (tick, d2)
                    channel = lo
                elif hi in (0x80, 0x90):
                    key = (lo, d1)
                    if key in pending:
                        st, vel = pending.pop(key)
                        notes.append(MidiNote(d1, st, max(1, tick - st), vel))
                    channel = lo
            elif hi in (0xC0, 0xD0):
                if j + 1 > len(body):
                    break
                d1 = body[j]
                j += 1
                if hi == 0xC0:
                    program = int(d1)
                    channel = lo
            else:
                break
        if notes or name:
            tracks.append(MidiTrack(name or f"ch{channel}", channel, program, notes))
    if fmt == 0 and not tracks:
        raise ValueError("SMF has no playable tracks")
    return tracks, float(bpm), int(tpq)
