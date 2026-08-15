"""One-line EDIT pack: clips + optional title/stagger + look → timeline.

Hands after E1 EDIT_PLAN. Agents call scripts/edit_pack.py instead of
assemble_video concat when delivering a master.
"""

from __future__ import annotations

import os
from typing import Any

from lib.edit_look import compose_look
from lib.edit_motion import expand_stagger
from lib.edit_timeline import from_clips, resolve_media_path, timeline_duration, validate_timeline

DEFAULT_BED_FADE_IN = 0.20
DEFAULT_BED_FADE_OUT = 0.35
DEFAULT_DUCK = 0.28

LAYOUT_KIND = {
    "caption": "caption",
    "yeonung": "caption",
    "lower_third": "lower_third",
    "title": "title",
    "card": "card",
}


def sidecar_paths(output_mp4: str) -> dict[str, str]:
    """Sibling layout next to the master. Agent writes all of this outside the toolbox."""
    abs_out = os.path.abspath(output_mp4)
    base = os.path.dirname(abs_out)
    titles = os.path.join(base, "titles")
    return {
        "master": abs_out,
        "timeline": os.path.join(base, "timeline.json"),
        "title": os.path.join(titles, "t1.png"),
        "glyphs": os.path.join(titles, "t1.glyphs.json"),
        "qa": os.path.join(base, "qa"),
        "plan": os.path.join(base, "EDIT_PLAN.md"),
        "titles_dir": titles,
    }


def title_sidecar(output_mp4: str, index: int) -> dict[str, str]:
    i = max(1, int(index))
    folder = sidecar_paths(output_mp4)["titles_dir"]
    return {
        "title": os.path.join(folder, f"t{i}.png"),
        "glyphs": os.path.join(folder, f"t{i}.glyphs.json"),
    }


def plan_warning(output_mp4: str) -> str | None:
    plan = sidecar_paths(output_mp4)["plan"]
    if os.path.isfile(plan):
        return None
    return "EDIT_PLAN.md missing next to master — E1 not done (skill video-edit)"


def default_title_window(duration: float) -> tuple[float, float]:
    """Agent-facing defaults. Do not ask the user for seconds."""
    dur = max(0.0, float(duration))
    if dur <= 0:
        return 0.40, 2.40
    start = 0.40 if dur >= 1.6 else min(0.12, dur * 0.15)
    hold = min(2.8, max(1.2, dur * 0.40))
    end = min(max(0.0, dur - 0.15), start + hold)
    if end <= start:
        end = min(dur, start + 0.80) if dur > 0 else start + 0.80
        if end <= start:
            end = start + 0.05
    return round(start, 4), round(end, 4)


def resolve_title_window(
    duration: float,
    *,
    start: float | None = None,
    end: float | None = None,
) -> tuple[float, float]:
    d_start, d_end = default_title_window(duration)
    s = d_start if start is None else float(start)
    e = d_end if end is None else float(end)
    if e <= s:
        raise ValueError(f"title end {e} must be > start {s}")
    return round(s, 4), round(e, 4)


def title_windows(duration: float, count: int) -> list[tuple[float, float]]:
    """Sequential caption windows. Agent does not pick seconds."""
    n = max(1, int(count))
    if n == 1:
        return [default_title_window(duration)]
    dur = max(0.0, float(duration))
    first = 0.40 if dur >= 1.6 else min(0.12, dur * 0.15)
    tail = 0.15
    gap = 0.18
    usable = max(0.25, dur - first - tail - gap * (n - 1))
    hold = min(2.4, max(0.65, usable / n))
    out: list[tuple[float, float]] = []
    t = first
    for _ in range(n):
        end = min(dur - tail if dur > tail else dur, t + hold)
        if end <= t:
            end = min(dur, t + 0.40) if dur > 0 else t + 0.40
            if end <= t:
                end = t + 0.05
        out.append((round(t, 4), round(end, 4)))
        t = end + gap
    return out


def title_kind(layout: str | None) -> str:
    key = str(layout or "caption").strip().lower()
    return LAYOUT_KIND.get(key, "caption")


def build_title_overlays(
    *,
    path: str,
    text: str,
    start: float,
    end: float,
    motion: str | None = "pop",
    kind: str = "caption",
    stagger: float | None = None,
    glyphs: dict[str, Any] | None = None,
    fade_in: float | None = None,
    fade_out: float | None = None,
    move: float | None = None,
    scale_from: float | None = None,
    scale_to: float | None = None,
    direction: str | None = None,
    distance: float | None = None,
    dx: float | None = None,
    dy: float | None = None,
    index: int = 1,
) -> list[dict[str, Any]]:
    idx = max(1, int(index))
    if stagger is not None:
        if not glyphs or not glyphs.get("glyphs"):
            raise ValueError("stagger requires glyphs from render_title --split glyphs")
        return expand_stagger(
            glyphs,
            start=start,
            end=end,
            stagger=float(stagger),
            motion=motion,
            fade_in=fade_in,
            fade_out=fade_out,
            move=move,
            scale_from=scale_from,
            scale_to=scale_to,
            direction=direction,
            distance=distance,
            dx=dx,
            dy=dy,
            id_prefix=f"g{idx}_",
        )
    ov: dict[str, Any] = {
        "id": f"t{idx}",
        "kind": kind if kind in ("title", "lower_third", "caption", "card") else "caption",
        "path": path,
        "text": text,
        "start": float(start),
        "end": float(end),
    }
    if motion:
        ov["motion"] = motion
    for key, val in (
        ("fade_in", fade_in),
        ("fade_out", fade_out),
        ("move", move),
        ("scale_from", scale_from),
        ("scale_to", scale_to),
        ("direction", direction),
        ("distance", distance),
        ("dx", dx),
        ("dy", dy),
    ):
        if val is not None:
            ov[key] = val
    return [ov]


def apply_look(
    tl: dict[str, Any],
    *,
    name: str | None = None,
    contrast: float | None = None,
    saturation: float | None = None,
    brightness: float | None = None,
    gamma: float | None = None,
    temperature: float | None = None,
    amount: float | None = None,
    lut: str | None = None,
) -> dict[str, Any]:
    src: dict[str, Any] = {}
    if name is not None:
        src["name"] = name
    for key, val in (
        ("contrast", contrast),
        ("saturation", saturation),
        ("brightness", brightness),
        ("gamma", gamma),
        ("temperature", temperature),
        ("amount", amount),
        ("lut", lut),
    ):
        if val is not None:
            src[key] = val
    if src:
        tl["look"] = compose_look(src)
    return tl


def build_pack(
    clips: list[str],
    *,
    xfade: float = 0.25,
    width: int = 1920,
    height: int = 1080,
    fps: int = 24,
    durations: list[float] | None = None,
    look: str | None = None,
    contrast: float | None = None,
    saturation: float | None = None,
    brightness: float | None = None,
    gamma: float | None = None,
    temperature: float | None = None,
    amount: float | None = None,
    lut: str | None = None,
    overlays: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not clips:
        raise ValueError("at least one clip path")
    tl = from_clips(
        clips,
        xfade=xfade,
        width=width,
        height=height,
        fps=fps,
        durations=durations,
    )
    apply_look(
        tl,
        name=look,
        contrast=contrast,
        saturation=saturation,
        brightness=brightness,
        gamma=gamma,
        temperature=temperature,
        amount=amount,
        lut=lut,
    )
    if overlays:
        tl.setdefault("overlays", []).extend(overlays)
    return validate_timeline(tl)


def attach_mix(
    tl: dict[str, Any],
    *,
    audio: str | None = None,
    vo: str | None = None,
    duck: float | None = None,
    fade_in: float | None = None,
    fade_out: float | None = None,
    audio_volume: float | None = None,
    vo_volume: float | None = None,
    vo_start: float = 0.0,
) -> dict[str, Any]:
    """Bed + optional VO. Duck only when both are present. Seconds are agent-chosen defaults."""
    if not audio and not vo:
        return tl
    items: list[dict[str, Any]] = []
    if audio:
        bed: dict[str, Any] = {
            "id": "bed",
            "path": audio,
            "start": 0.0,
            "in": 0.0,
            "out": None,
            "volume": 1.0 if audio_volume is None else float(audio_volume),
            "role": "master",
            "fade_in": DEFAULT_BED_FADE_IN if fade_in is None else float(fade_in),
            "fade_out": DEFAULT_BED_FADE_OUT if fade_out is None else float(fade_out),
        }
        if vo:
            bed["duck"] = DEFAULT_DUCK if duck is None else float(duck)
        elif duck is not None:
            bed["duck"] = float(duck)
        items.append(bed)
    if vo:
        items.append(
            {
                "id": "vo",
                "path": vo,
                "start": float(vo_start or 0.0),
                "in": 0.0,
                "out": None,
                "volume": 1.0 if vo_volume is None else float(vo_volume),
                "role": "vo",
            }
        )
    tl.setdefault("audio", []).extend(items)
    return validate_timeline(tl)


def refuse_frozen_clips(
    tl: dict[str, Any],
    *,
    timeline_path: str | None = None,
    allow_freeze: bool = False,
    sample_root: str | None = None,
) -> dict[str, Any]:
    """Fail-loud if any V1 clip looks freeze-padded. Intentional still: allow_freeze."""
    if allow_freeze:
        return {"ok": True, "skipped": True, "allowed": True, "hits": []}
    from lib.visual_qa import gate_work_clip_no_freeze

    hits: list[dict[str, Any]] = []
    for c in tl.get("clips") or []:
        raw = str(c.get("path") or "")
        if not raw:
            continue
        path = resolve_media_path(raw, timeline_path=timeline_path)
        sample_dir = None
        if sample_root:
            sample_dir = os.path.join(sample_root, str(c.get("id") or "clip"))
        gate = gate_work_clip_no_freeze(path, sample_dir=sample_dir, allow_still=False)
        if gate.get("ok"):
            continue
        hits.append(
            {
                "id": c.get("id"),
                "path": path,
                "error": gate.get("error"),
                "kind": gate.get("kind"),
                "message": gate.get("message"),
            }
        )
    if not hits:
        return {"ok": True, "hits": []}
    first = hits[0]
    return {
        "ok": False,
        "error": first.get("error") or "FREEZE_PAD_SUSPECT",
        "hits": hits,
        "message": first.get("message") or f"frozen clip {first.get('id')}",
    }


def pack_duration(tl: dict[str, Any]) -> float:
    return timeline_duration(tl)
