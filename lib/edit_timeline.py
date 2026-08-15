"""edit_timeline.v1 — load, save, validate, duration, from-clips."""

from __future__ import annotations

import json
import os
from typing import Any

from lib.comfy_client import fail_result, ok_result
from lib.edit_motion import compose_motion
from lib.ffmpeg_util import probe_duration

SCHEMA = "edit_timeline.v1"
FITS = ("cover", "contain", "stretch")
TRANS_TYPES = ("cut", "crossfade")
OVERLAY_KINDS = ("title", "lower_third", "caption", "card")
OVERLAY_MOTIONS = ("none", "fade", "pop", "slide", "slide_up", "slide_down", "custom")


def empty_timeline(
    *,
    fps: int = 24,
    width: int = 1920,
    height: int = 1080,
    sample_rate: int = 48000,
    background: str = "#000000",
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "fps": int(fps),
        "width": int(width),
        "height": int(height),
        "sample_rate": int(sample_rate),
        "background": background,
        "clips": [],
        "overlays": [],
        "audio": [],
        "transitions": [],
    }


def play_dur(clip: dict) -> float:
    inn = float(clip.get("in") or 0.0)
    out = clip.get("out")
    if out is None:
        raise ValueError(f"clip {clip.get('id')} missing out")
    speed = float(clip.get("speed") or 1.0) or 1.0
    return max(0.0, (float(out) - inn) / speed)


def timeline_duration(tl: dict) -> float:
    ends = [0.0]
    for c in tl.get("clips") or []:
        ends.append(float(c.get("start") or 0.0) + play_dur(c))
    for o in tl.get("overlays") or []:
        ends.append(float(o.get("end") or 0.0))
    for a in tl.get("audio") or []:
        start = float(a.get("start") or 0.0)
        inn = float(a.get("in") or 0.0)
        out = a.get("out")
        if out is None:
            continue
        ends.append(start + max(0.0, float(out) - inn))
    return max(ends)


def save_timeline(tl: dict, path: str) -> str:
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tl, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return os.path.abspath(path)


def load_timeline(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("timeline must be an object")
    return validate_timeline(data)


def validate_timeline(tl: dict) -> dict[str, Any]:
    if tl.get("schema") not in (None, SCHEMA):
        raise ValueError(f"unsupported schema {tl.get('schema')!r}")
    tl = dict(tl)
    tl["schema"] = SCHEMA
    tl.setdefault("fps", 24)
    tl.setdefault("width", 1920)
    tl.setdefault("height", 1080)
    tl.setdefault("sample_rate", 48000)
    tl.setdefault("background", "#000000")
    tl.setdefault("clips", [])
    tl.setdefault("overlays", [])
    tl.setdefault("audio", [])
    tl.setdefault("transitions", [])
    ids = set()
    for c in tl["clips"]:
        cid = str(c.get("id") or "")
        if not cid:
            raise ValueError("clip missing id")
        if cid in ids:
            raise ValueError(f"duplicate clip id {cid}")
        ids.add(cid)
        if float(c.get("start") or 0.0) < 0 or float(c.get("in") or 0.0) < 0:
            raise ValueError(f"negative time on {cid}")
        fit = (c.get("transform") or {}).get("fit") or "cover"
        if fit not in FITS:
            raise ValueError(f"bad fit {fit}")
        if c.get("out") is not None and float(c["out"]) < float(c.get("in") or 0):
            raise ValueError(f"out < in on {cid}")
    oids = {str(o.get("id")) for o in tl["overlays"] if o.get("id")}
    for o in tl["overlays"]:
        kind = str(o.get("kind") or "caption")
        if kind not in OVERLAY_KINDS:
            raise ValueError(f"bad overlay kind {kind}")
        if float(o.get("end") or 0) < float(o.get("start") or 0):
            raise ValueError(f"overlay {o.get('id')} end < start")
        resolved = compose_motion(
            o,
            width=int(tl.get("width") or 1920),
            height=int(tl.get("height") or 1080),
        )
        o["motion"] = resolved["name"]
        if resolved.get("warning"):
            o["warning"] = resolved["warning"]
    for t in tl["transitions"]:
        typ = str(t.get("type") or "cut")
        if typ not in TRANS_TYPES:
            t["type"] = "cut"
            t["warning"] = f"downgraded {typ} to cut"
        fr, to = t.get("from"), t.get("to")
        if fr not in ids or to not in ids:
            raise ValueError(f"transition bad id {fr}->{to}")
        if typ == "crossfade" and float(t.get("dur") or 0) <= 0:
            raise ValueError("crossfade dur must be > 0")
    return tl


def resolve_media_path(path: str, *, timeline_path: str | None) -> str:
    if os.path.isabs(path) and os.path.isfile(path):
        return os.path.abspath(path)
    if timeline_path:
        cand = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(timeline_path)), path))
        if os.path.isfile(cand):
            return cand
    if os.path.isfile(path):
        return os.path.abspath(path)
    return path


def from_clips(
    paths: list[str],
    *,
    xfade: float = 0.0,
    width: int = 1920,
    height: int = 1080,
    fps: int = 24,
    durations: list[float] | None = None,
) -> dict[str, Any]:
    if not paths:
        raise ValueError("at least one clip path")
    tl = empty_timeline(fps=fps, width=width, height=height)
    t = 0.0
    xf = max(0.0, float(xfade))
    for i, raw in enumerate(paths):
        dur = None
        if durations and i < len(durations):
            dur = float(durations[i])
        else:
            dur = probe_duration(raw)
        if not dur or dur <= 0:
            raise ValueError(f"cannot probe duration: {raw}")
        cid = f"c{i + 1}"
        tl["clips"].append(
            {
                "id": cid,
                "path": raw,
                "track": "V1",
                "start": round(t, 4),
                "in": 0.0,
                "out": round(dur, 4),
                "speed": 1.0,
                "opacity": 1.0,
                "transform": {"fit": "cover"},
            }
        )
        if xf > 0 and i < len(paths) - 1:
            if xf >= dur:
                raise ValueError(f"xfade {xf} >= clip duration {dur}")
            tl["transitions"].append(
                {
                    "id": f"x{i + 1}",
                    "from": cid,
                    "to": f"c{i + 2}",
                    "type": "crossfade",
                    "dur": xf,
                }
            )
            t += dur - xf
        else:
            t += dur
    return validate_timeline(tl)
