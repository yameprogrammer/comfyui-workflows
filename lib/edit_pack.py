"""One-line EDIT pack: clips + optional title/stagger + look → timeline.

Hands after E1 EDIT_PLAN. Agents call scripts/edit_pack.py instead of
assemble_video concat when delivering a master.
"""

from __future__ import annotations

import os
from typing import Any

from lib.edit_look import compose_look
from lib.edit_motion import expand_stagger
from lib.edit_timeline import from_clips, timeline_duration, validate_timeline

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
) -> list[dict[str, Any]]:
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
            id_prefix="g0_",
        )
    ov: dict[str, Any] = {
        "id": "t1",
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


def pack_duration(tl: dict[str, Any]) -> float:
    return timeline_duration(tl)
