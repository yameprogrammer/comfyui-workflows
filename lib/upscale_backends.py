"""Upscale backend + deliver-size presets (upscale_backends.json).

Agent selection: recommend_upscale() / format_recommendation() /
list_agent_matrix() — see scripts/upscale_recommend.py.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

from lib.comfy_client import WORKSPACE_ROOT
from lib.video_backends import get_format, load_video_backends

DEFAULT_CONFIG_PATH = os.path.join(WORKSPACE_ROOT, "upscale_backends.json")

# Valid agent selectors (normalized)
MEDIA_IDS = ("image", "video")
GOAL_IDS = ("preview", "batch", "delivery", "hero", "master_4k", "face_fix")
DOMAIN_IDS = ("photo", "anime", "general")
SOURCE_IDS = ("clean", "normal", "blurry", "ai_artifacts")


@lru_cache(maxsize=4)
def load_upscale_backends(path: str | None = None) -> dict[str, Any]:
    cfg_path = path or DEFAULT_CONFIG_PATH
    if not os.path.isfile(cfg_path):
        raise FileNotFoundError(f"upscale_backends.json not found: {cfg_path}")
    with open(cfg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("upscale_backends.json must be an object")
    return data


def clear_upscale_backends_cache() -> None:
    load_upscale_backends.cache_clear()


def list_upscale_backend_ids(cfg: dict[str, Any] | None = None) -> list[str]:
    doc = cfg or load_upscale_backends()
    return sorted((doc.get("backends") or {}).keys())


def list_upscale_preset_ids(cfg: dict[str, Any] | None = None) -> list[str]:
    doc = cfg or load_upscale_backends()
    return sorted((doc.get("presets") or {}).keys())


def list_upscale_style_ids(cfg: dict[str, Any] | None = None) -> list[str]:
    doc = cfg or load_upscale_backends()
    return sorted((doc.get("styles") or {}).keys())


def get_upscale_style(style_id: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = cfg or load_upscale_backends()
    styles = doc.get("styles") or {}
    sid = (style_id or "").strip()
    if sid not in styles:
        known = ", ".join(sorted(styles.keys())) or "(none)"
        raise KeyError(f"Unknown upscale style {style_id!r}. Known: {known}")
    entry = dict(styles[sid])
    entry["id"] = sid
    if not entry.get("model"):
        raise ValueError(f"Style {sid!r} missing model")
    return entry


def resolve_esrgan_model(
    *,
    style: str | None = None,
    esrgan_model: str | None = None,
    cfg: dict[str, Any] | None = None,
) -> str:
    """Resolve CNN upscale model filename from --style or explicit --esrgan-model."""
    doc = cfg or load_upscale_backends()
    if esrgan_model:
        return str(esrgan_model).strip()
    if style:
        return str(get_upscale_style(style, doc)["model"])
    default_style = str(doc.get("default_style") or "photo")
    styles = doc.get("styles") or {}
    if default_style in styles:
        return str(styles[default_style]["model"])
    be = get_upscale_backend("esrgan", doc)
    return str(be.get("model_name") or "4x-UltraSharp.pth")


def get_upscale_backend(backend_id: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = cfg or load_upscale_backends()
    backends = doc.get("backends") or {}
    if backend_id not in backends:
        known = ", ".join(sorted(backends.keys())) or "(none)"
        raise KeyError(f"Unknown upscale backend {backend_id!r}. Known: {known}")
    entry = dict(backends[backend_id])
    entry["id"] = backend_id
    return entry


def normalize_deliver_tier(preset_id: str) -> str:
    """Map legacy aspect-specific deliver IDs to short-edge tiers."""
    pid = (preset_id or "").strip()
    try:
        from lib.video_backends import load_video_backends

        aliases = load_video_backends().get("deliver_aliases") or {}
        return str(aliases.get(pid, pid))
    except Exception:
        # offline fallback
        legacy = {
            "deliver_16x9_1080": "deliver_1080",
            "deliver_9x16_1080": "deliver_1080",
            "deliver_4x3_1080": "deliver_1080",
            "deliver_3x4_1080": "deliver_1080",
            "deliver_1x1_1080": "deliver_1080",
            "deliver_16x9_2160": "deliver_2160",
            "deliver_9x16_2160": "deliver_2160",
        }
        return legacy.get(pid, pid)


def get_upscale_preset(preset_id: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = cfg or load_upscale_backends()
    presets = doc.get("presets") or {}
    pid = normalize_deliver_tier(preset_id)
    if pid not in presets:
        known = ", ".join(sorted(presets.keys())) or "(none)"
        raise KeyError(f"Unknown upscale preset {preset_id!r} (normalized {pid!r}). Known: {known}")
    entry = dict(presets[pid])
    entry["id"] = pid
    if "short_edge" not in entry:
        raise ValueError(f"Preset {pid!r} missing short_edge")
    return entry


def parse_aspect(aspect: str) -> tuple[int, int]:
    """Return (w_ratio, h_ratio) for strings like '16:9'."""
    parts = aspect.replace("x", ":").split(":")
    if len(parts) != 2:
        raise ValueError(f"Bad aspect {aspect!r}")
    return int(parts[0]), int(parts[1])


def size_from_short_edge(aspect: str, short_edge: int) -> tuple[int, int]:
    """
    Compute even (width, height) so the shorter side == short_edge.
    Landscape: height=short_edge; portrait: width=short_edge; square: both.
    """
    wr, hr = parse_aspect(aspect)
    short_edge = int(short_edge)
    if wr == hr:
        s = short_edge - (short_edge % 2)
        return s, s
    if wr > hr:
        # landscape: short = height
        h = short_edge - (short_edge % 2)
        w = int(round(h * wr / hr))
        w = w - (w % 2)
        return max(w, 2), max(h, 2)
    # portrait: short = width
    w = short_edge - (short_edge % 2)
    h = int(round(w * hr / wr))
    h = h - (h % 2)
    return max(w, 2), max(h, 2)


def resolve_target_size(
    *,
    preset: str | None = None,
    format_id: str | None = None,
    aspect: str | None = None,
    width: int | None = None,
    height: int | None = None,
    short_edge: int | None = None,
    config_path: str | None = None,
) -> dict[str, Any]:
    """
    Resolve final pixel size for upscale.

    Priority:
      1. explicit width+height
      2. short_edge + aspect/format
      3. preset short_edge + aspect/format
    """
    cfg = load_upscale_backends(config_path)
    raw_preset = (preset or cfg.get("default_preset") or "deliver_1080").strip()
    pr = get_upscale_preset(raw_preset, cfg)
    preset_id = str(pr.get("id") or normalize_deliver_tier(raw_preset))

    resolved_aspect = aspect
    resolved_format = format_id
    if not resolved_aspect:
        if format_id:
            try:
                fmt = get_format(format_id)
                resolved_aspect = str(fmt.get("aspect") or "16:9")
                resolved_format = format_id
            except Exception:
                resolved_aspect = "16:9"
        else:
            # fall back to video_backends default format
            try:
                vcfg = load_video_backends()
                fid = str(vcfg.get("default_format") or "cinematic_16x9")
                fmt = get_format(fid)
                resolved_aspect = str(fmt.get("aspect") or "16:9")
                resolved_format = fid
            except Exception:
                resolved_aspect = "16:9"

    if width is not None and height is not None:
        w, h = int(width), int(height)
        se = min(w, h)
    else:
        se = int(short_edge) if short_edge is not None else int(pr["short_edge"])
        w, h = size_from_short_edge(resolved_aspect, se)

    return {
        "preset_id": preset_id,
        "preset": pr,
        "format_id": resolved_format,
        "aspect": resolved_aspect,
        "width": w,
        "height": h,
        "short_edge": min(w, h),
        "long_edge": max(w, h),
    }


def aspect_from_image(path: str) -> str:
    """Best-effort W:H aspect string from an image file (even integers, simplified)."""
    try:
        from PIL import Image
    except ImportError as e:
        raise RuntimeError("Pillow required to infer image aspect") from e
    with Image.open(path) as im:
        w, h = im.size
    if w <= 0 or h <= 0:
        raise ValueError(f"Bad image size {w}x{h} for {path}")
    # reduce by gcd for a stable ratio label
    a, b = int(w), int(h)
    while b:
        a, b = b, a % b
    g = max(a, 1)
    return f"{w // g}:{h // g}"


def resolve_upscale_job(
    *,
    backend: str | None = None,
    preset: str | None = None,
    format_id: str | None = None,
    aspect: str | None = None,
    width: int | None = None,
    height: int | None = None,
    short_edge: int | None = None,
    style: str | None = None,
    esrgan_model: str | None = None,
    source_path: str | None = None,
    config_path: str | None = None,
    allow_optional_backend: bool = False,
) -> dict[str, Any]:
    cfg = load_upscale_backends(config_path)
    backend_id = (backend or cfg.get("default_backend") or "esrgan").strip()
    be = get_upscale_backend(backend_id, cfg)
    status = (be.get("status") or "ready").lower()
    if status not in ("ready", "ready_experimental") and not (
        allow_optional_backend and status == "optional"
    ):
        if status == "optional":
            raise RuntimeError(
                f"Upscale backend {backend_id!r} is optional/unavailable "
                f"(status={status}). Use esrgan or seedvr2."
            )
        raise RuntimeError(f"Upscale backend {backend_id!r} status={be.get('status')}")

    # Preserve source aspect for stills when caller did not pin format/aspect/size
    resolved_aspect = aspect
    if (
        resolved_aspect is None
        and format_id is None
        and width is None
        and height is None
        and source_path
        and os.path.isfile(source_path)
    ):
        try:
            resolved_aspect = aspect_from_image(source_path)
        except Exception:
            resolved_aspect = None

    target = resolve_target_size(
        preset=preset,
        format_id=format_id,
        aspect=resolved_aspect,
        width=width,
        height=height,
        short_edge=short_edge,
        config_path=config_path,
    )

    model = None
    style_id = (style or "").strip() or None
    if backend_id == "esrgan" or esrgan_model or style_id:
        try:
            model = resolve_esrgan_model(style=style_id, esrgan_model=esrgan_model, cfg=cfg)
        except Exception:
            if backend_id == "esrgan":
                raise
            model = None

    return {
        "backend_id": backend_id,
        "backend": be,
        "config": cfg,
        "style": style_id or cfg.get("default_style"),
        "esrgan_model": model,
        **target,
    }


# ---------------------------------------------------------------------------
# Agent-facing classification + recommendation
# ---------------------------------------------------------------------------


def _norm_token(value: str | None, allowed: tuple[str, ...], default: str) -> str:
    v = (value or default).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "still": "image",
        "img": "image",
        "pic": "image",
        "clip": "video",
        "movie": "video",
        "fast": "preview",
        "quick": "preview",
        "episode": "batch",
        "deliver": "delivery",
        "deliver_1080": "delivery",
        "quality": "hero",
        "master": "master_4k",
        "4k": "master_4k",
        "2160": "master_4k",
        "face": "face_fix",
        "smear": "face_fix",
        "photoreal": "photo",
        "real": "photo",
        "illustrious": "anime",
        "cel": "anime",
        "linework": "anime",
        "sharp": "normal",
        "ok": "normal",
        "good": "clean",
        "muddy": "blurry",
        "blur": "blurry",
        "artifact": "ai_artifacts",
        "artifacts": "ai_artifacts",
        "ai": "ai_artifacts",
    }
    v = aliases.get(v, v)
    if v not in allowed:
        raise ValueError(f"Unknown value {value!r}. Allowed: {', '.join(allowed)}")
    return v


def list_backend_cards(cfg: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Per-backend agent cards (lane, ranks, when/when_not)."""
    doc = cfg or load_upscale_backends()
    cards: list[dict[str, Any]] = []
    for bid, raw in sorted((doc.get("backends") or {}).items()):
        be = dict(raw)
        agent = dict(be.get("agent") or {})
        cards.append(
            {
                "id": bid,
                "status": be.get("status"),
                "media": list(be.get("media") or []),
                "kind": be.get("kind"),
                "speed": be.get("speed"),
                "quality": be.get("quality"),
                "lane": agent.get("lane") or "?",
                "rank_speed": agent.get("rank_speed"),
                "rank_quality": agent.get("rank_quality"),
                "rank_restore": agent.get("rank_restore"),
                "latency_class": agent.get("latency_class"),
                "vram_note": agent.get("vram_note"),
                "domains": list(agent.get("domains") or []),
                "source_pref": list(agent.get("source_pref") or []),
                "when": agent.get("when") or be.get("notes"),
                "when_not": agent.get("when_not"),
                "best_for": list(agent.get("best_for") or []),
                "avoid_for": list(agent.get("avoid_for") or []),
                "notes": be.get("notes"),
            }
        )
    return cards


def list_agent_matrix(cfg: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    doc = cfg or load_upscale_backends()
    return [dict(row) for row in (doc.get("agent_matrix") or [])]


def list_agent_goals(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = cfg or load_upscale_backends()
    return dict(doc.get("agent_goals") or {})


def _style_for_domain(domain: str, *, prefer_fast: bool = False) -> str | None:
    if domain == "anime":
        return "anime_fast" if prefer_fast else "anime"
    if domain == "general":
        return "general"
    return "photo"


def _score_matrix_row(
    row: dict[str, Any],
    *,
    media: str,
    goal: str,
    domain: str,
    source: str,
) -> float:
    if str(row.get("media")) != media:
        return -1.0
    score = 0.0
    if str(row.get("goal")) == goal:
        score += 10.0
    else:
        # related goals still useful as soft matches
        related = {
            "preview": {"batch", "delivery"},
            "batch": {"delivery", "preview"},
            "delivery": {"batch", "hero"},
            "hero": {"delivery", "master_4k"},
            "master_4k": {"hero"},
            "face_fix": set(),
        }
        if str(row.get("goal")) in related.get(goal, set()):
            score += 3.0
        else:
            return -1.0
    if str(row.get("domain")) == domain:
        score += 4.0
    elif domain == "general" or str(row.get("domain")) == "general":
        score += 1.0
    else:
        score -= 1.0
    rs = str(row.get("source") or "normal")
    if rs == source:
        score += 5.0
    elif source == "ai_artifacts" and rs in ("blurry", "ai_artifacts"):
        score += 3.0
    elif source == "blurry" and rs in ("blurry", "normal"):
        score += 2.0
    elif source == "clean" and rs in ("clean", "normal"):
        score += 2.0
    elif source == "normal":
        score += 1.0
    return score


def _fallback_pick(
    *,
    media: str,
    goal: str,
    domain: str,
    source: str,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    """Rule engine when matrix miss — mirrors heuristics + research policy."""
    heuristics = cfg.get("heuristics") or {}
    goals_meta = (cfg.get("agent_goals") or {}).get(goal) or {}
    prefer_speed = bool(goals_meta.get("prefer_speed"))
    preset = goals_meta.get("default_preset") or cfg.get("default_preset") or "deliver_1080"

    if goal == "face_fix":
        return {
            "backend": str(heuristics.get("face_smear_after_i2v") or "wan22_face_enhance"),
            "style": None,
            "preset": None,
            "two_pass": False,
            "why": "I2V face smear — refine face, then upscale resolution separately",
        }

    if goal == "master_4k":
        be = str(heuristics.get("hero_max_quality") or "seedvr2_max")
        if media == "video":
            be = str(heuristics.get("hero_or_4k") or "seedvr2")
        return {
            "backend": be,
            "style": None,
            "preset": "deliver_2160",
            "two_pass": media == "video" or be.startswith("seedvr2"),
            "why": "4K master — gradual 1080→2160 preferred for seedvr2 family",
        }

    if goal == "hero" or source in ("blurry", "ai_artifacts"):
        return {
            "backend": str(heuristics.get("hero_or_4k") or "seedvr2"),
            "style": None,
            "preset": preset if preset != "deliver_720" else "deliver_1080",
            "two_pass": False,
            "why": "Hero / restore lane — SeedVR2 opt-in",
        }

    # speed / batch / delivery default
    backend = str(heuristics.get("default_delivery") or "esrgan")
    if goal == "preview":
        backend = str(heuristics.get("preview") or "esrgan")
        preset = preset or "deliver_720"
    if media == "video" and source == "clean" and goal == "preview":
        # prefer esrgan as always-ready; mention rtx as alt
        backend = str(heuristics.get("clean_source_fast") or "esrgan")
    style = _style_for_domain(domain, prefer_fast=prefer_speed and domain == "anime")
    return {
        "backend": backend,
        "style": style,
        "preset": preset,
        "two_pass": False,
        "why": f"Default FAST lane for goal={goal} domain={domain}",
    }


def build_upscale_cli(
    *,
    media: str,
    backend: str,
    style: str | None,
    preset: str | None,
    input_placeholder: str | None = None,
    output_placeholder: str | None = None,
    two_pass: bool = False,
    format_id: str | None = None,
) -> str:
    """One-line copy-paste CLI for the recommendation."""
    if backend == "wan22_face_enhance":
        return (
            "python scripts/generate_wan22_face_enhance.py -i "
            f"{input_placeholder or 'work.mp4'} -o "
            f"{output_placeholder or 'face_fixed.mp4'}"
        )
    if backend == "wan22_upscale":
        return (
            "python scripts/generate_wan22_upscale.py -i "
            f"{input_placeholder or 'work.mp4'} -o "
            f"{output_placeholder or 'out.mp4'}  # experimental; check --help"
        )

    script = "upscale_image.py" if media == "image" else "upscale_video.py"
    inp = input_placeholder or ("key.png" if media == "image" else "work.mp4")
    out = output_placeholder or (
        "key_out.png" if media == "image" else "deliver.mp4"
    )
    parts = [f"python scripts/{script}", f"-i {inp}", f"-o {out}"]
    if backend and backend != "esrgan":
        parts.append(f"--backend {backend}")
    if style and backend == "esrgan":
        parts.append(f"--style {style}")
    if preset:
        parts.append(f"--preset {preset}")
    if format_id:
        parts.append(f"--format {format_id}")
    if two_pass and media == "video":
        parts.append("--two-pass")
    return " ".join(parts)


def recommend_upscale(
    *,
    media: str = "image",
    goal: str = "delivery",
    domain: str = "photo",
    source: str = "normal",
    batch_count: int | None = None,
    allow_optional: bool = False,
    format_id: str | None = None,
    input_path: str | None = None,
    output_path: str | None = None,
    config_path: str | None = None,
) -> dict[str, Any]:
    """
    Pick backend/style/preset for the agent's media job.

    Returns structured recommendation with cli, alternatives, warnings.
    """
    cfg = load_upscale_backends(config_path)
    media_n = _norm_token(media, MEDIA_IDS, "image")
    goal_n = _norm_token(goal, GOAL_IDS, "delivery")
    domain_n = _norm_token(domain, DOMAIN_IDS, "photo")
    source_n = _norm_token(source, SOURCE_IDS, "normal")

    # batch pressure: force FAST unless hero/master/face
    if batch_count is not None and batch_count >= 8 and goal_n in ("delivery", "batch", "preview"):
        goal_n = "batch"

    matrix = list_agent_matrix(cfg)
    best_row: dict[str, Any] | None = None
    best_score = -1.0
    for row in matrix:
        sc = _score_matrix_row(
            row, media=media_n, goal=goal_n, domain=domain_n, source=source_n
        )
        if sc > best_score:
            best_score = sc
            best_row = row

    if best_row is not None and best_score >= 8.0:
        pick = {
            "backend": str(best_row["backend"]),
            "style": best_row.get("style"),
            "preset": best_row.get("preset"),
            "two_pass": bool(best_row.get("two_pass")),
            "why": str(best_row.get("why") or "matrix match"),
            "matrix_id": best_row.get("id"),
            "alt_backend": best_row.get("alt_backend"),
        }
    else:
        pick = _fallback_pick(
            media=media_n, goal=goal_n, domain=domain_n, source=source_n, cfg=cfg
        )
        pick["matrix_id"] = None
        pick["alt_backend"] = None

    backend_id = str(pick["backend"])
    be = get_upscale_backend(backend_id, cfg)
    status = str(be.get("status") or "ready").lower()
    warnings: list[str] = []

    if status == "planned":
        warnings.append(f"Backend {backend_id} is planned — falling back to seedvr2/esrgan.")
        backend_id = "seedvr2" if goal_n in ("hero", "master_4k") else "esrgan"
        be = get_upscale_backend(backend_id, cfg)
        status = str(be.get("status") or "ready")
        if backend_id == "esrgan" and not pick.get("style"):
            pick["style"] = _style_for_domain(domain_n)

    if status == "optional" and not allow_optional:
        alt = pick.get("alt_backend")
        warnings.append(
            f"{backend_id} is optional (node may be missing). "
            f"Using esrgan unless you pass allow_optional."
        )
        if backend_id == "rtx_vsr":
            backend_id = "esrgan"
            be = get_upscale_backend(backend_id, cfg)
            pick["style"] = pick.get("style") or _style_for_domain(domain_n)
            pick["alt_backend"] = "rtx_vsr"

    if status == "ready_experimental":
        warnings.append(f"{backend_id} is experimental — verify output carefully.")

    # hard rule reminder
    hard = list(cfg.get("agent_hard_rules") or [])
    if source_n in ("blurry", "ai_artifacts") and backend_id == "esrgan":
        warnings.append(
            "Source is blurry/artifacts but FAST esrgan chosen — "
            "consider --goal hero for SeedVR2 restore."
        )

    style = pick.get("style")
    if backend_id == "esrgan" and not style:
        style = _style_for_domain(domain_n)
    if backend_id != "esrgan":
        style = None  # style only applies to CNN lane

    preset = pick.get("preset")
    two_pass = bool(pick.get("two_pass"))
    if goal_n == "master_4k" and backend_id.startswith("seedvr2"):
        two_pass = True
        preset = preset or "deliver_2160"

    inp = input_path
    out = output_path
    cli = build_upscale_cli(
        media=media_n,
        backend=backend_id,
        style=style,
        preset=preset,
        input_placeholder=inp,
        output_placeholder=out,
        two_pass=two_pass and media_n == "video",
        format_id=format_id,
    )

    agent = dict(be.get("agent") or {})
    alternatives: list[dict[str, str]] = []

    # structured alternatives for agent pivot
    if backend_id == "esrgan":
        alternatives.append(
            {
                "if": "hero detail / blurry restore needed",
                "use": "seedvr2",
                "cli": build_upscale_cli(
                    media=media_n,
                    backend="seedvr2",
                    style=None,
                    preset=preset or "deliver_1080",
                    input_placeholder=inp,
                    output_placeholder=out,
                    format_id=format_id,
                ),
            }
        )
        if media_n == "image" and domain_n == "photo":
            alternatives.append(
                {
                    "if": "want sharper photo model",
                    "use": "esrgan photo_sharp",
                    "cli": build_upscale_cli(
                        media="image",
                        backend="esrgan",
                        style="photo_sharp",
                        preset=preset or "deliver_1080",
                        input_placeholder=inp,
                        output_placeholder=out,
                        format_id=format_id,
                    ),
                }
            )
        if media_n == "video" and source_n == "clean":
            alternatives.append(
                {
                    "if": "RTX VSR node available and source is clean",
                    "use": "rtx_vsr",
                    "cli": build_upscale_cli(
                        media="video",
                        backend="rtx_vsr",
                        style=None,
                        preset=preset or "deliver_1080",
                        input_placeholder=inp,
                        output_placeholder=out,
                        format_id=format_id,
                    ),
                }
            )
    elif backend_id.startswith("seedvr2"):
        alternatives.append(
            {
                "if": "batch / time budget / good-enough 1080",
                "use": "esrgan",
                "cli": build_upscale_cli(
                    media=media_n,
                    backend="esrgan",
                    style=_style_for_domain(domain_n),
                    preset="deliver_1080",
                    input_placeholder=inp,
                    output_placeholder=out,
                    format_id=format_id,
                ),
            }
        )
        if backend_id == "seedvr2" and goal_n == "master_4k":
            alternatives.append(
                {
                    "if": "max quality 4K still/clip",
                    "use": "seedvr2_max",
                    "cli": build_upscale_cli(
                        media=media_n,
                        backend="seedvr2_max",
                        style=None,
                        preset="deliver_2160",
                        input_placeholder=inp,
                        output_placeholder=out,
                        two_pass=media_n == "video",
                        format_id=format_id,
                    ),
                }
            )
    elif backend_id == "wan22_face_enhance":
        alternatives.append(
            {
                "if": "face OK — only need resolution",
                "use": "esrgan or seedvr2",
                "cli": build_upscale_cli(
                    media="video",
                    backend="esrgan",
                    style="photo",
                    preset="deliver_1080",
                    input_placeholder=inp,
                    output_placeholder=out,
                    format_id=format_id,
                ),
            }
        )

    alternatives.append(
        {
            "if": "hands/identity/anatomy broken",
            "use": "edit first (not upscale)",
            "cli": (
                'python scripts/generate_qwen_edit.py -i img.png -p "fix hands, keep identity" -o fixed.png'
                if media_n == "image"
                else "fix frames / re-I2V before upscale_video"
            ),
        }
    )

    return {
        "ok": True,
        "media": media_n,
        "goal": goal_n,
        "domain": domain_n,
        "source": source_n,
        "batch_count": batch_count,
        "backend": backend_id,
        "style": style,
        "preset": preset,
        "two_pass": two_pass,
        "status": status,
        "lane": agent.get("lane") or be.get("kind"),
        "speed": be.get("speed"),
        "quality": be.get("quality"),
        "latency_class": agent.get("latency_class"),
        "why": pick.get("why"),
        "matrix_id": pick.get("matrix_id"),
        "cli": cli,
        "alternatives": alternatives,
        "warnings": warnings,
        "hard_rules": hard,
        "when": agent.get("when"),
        "when_not": agent.get("when_not"),
        "backend_notes": be.get("notes"),
    }


def format_recommendation(rec: dict[str, Any], *, verbose: bool = True) -> str:
    """Human-readable recommendation block for CLI / agent logs."""
    lines = [
        f"RECOMMEND  media={rec.get('media')}  goal={rec.get('goal')}  "
        f"domain={rec.get('domain')}  source={rec.get('source')}",
        f"  → backend={rec.get('backend')}  lane={rec.get('lane')}  "
        f"style={rec.get('style') or '-'}  preset={rec.get('preset') or '-'}"
        + (f"  two_pass={rec.get('two_pass')}" if rec.get("two_pass") else ""),
        f"  speed={rec.get('speed')}  quality={rec.get('quality')}  "
        f"latency={rec.get('latency_class')}  status={rec.get('status')}",
        f"  why: {rec.get('why')}",
        f"  cli: {rec.get('cli')}",
    ]
    if verbose:
        if rec.get("when"):
            lines.append(f"  when: {rec['when']}")
        if rec.get("when_not"):
            lines.append(f"  when_not: {rec['when_not']}")
        if rec.get("matrix_id"):
            lines.append(f"  matrix: {rec['matrix_id']}")
        for w in rec.get("warnings") or []:
            lines.append(f"  WARN: {w}")
        alts = rec.get("alternatives") or []
        if alts:
            lines.append("  alternatives:")
            for a in alts:
                lines.append(f"    · if {a.get('if')}: use {a.get('use')}")
                lines.append(f"      {a.get('cli')}")
        rules = rec.get("hard_rules") or []
        if rules:
            lines.append("  hard_rules:")
            for r in rules[:4]:
                lines.append(f"    · {r}")
    return "\n".join(lines)


def format_backend_matrix_table(cfg: dict[str, Any] | None = None) -> str:
    """Compact performance/feature table for agents."""
    cards = list_backend_cards(cfg)
    lines = [
        f"{'backend':18s} {'lane':10s} {'status':18s} {'media':12s} "
        f"{'spd':4s} {'q':4s} {'rst':4s}  latency",
        "-" * 88,
    ]
    for c in cards:
        media = ",".join(c.get("media") or [])[:12]
        lines.append(
            f"{c['id']:18s} {str(c.get('lane') or '?'):10s} "
            f"{str(c.get('status') or ''):18s} {media:12s} "
            f"{str(c.get('rank_speed') or '-'):4s} "
            f"{str(c.get('rank_quality') or '-'):4s} "
            f"{str(c.get('rank_restore') or '-'):4s}  "
            f"{c.get('latency_class') or '-'}"
        )
    lines.append("")
    lines.append("spd/q/rst = rank 1–5 (higher = faster / better quality / better restore)")
    lines.append("Pick: python scripts/upscale_recommend.py --media image --goal delivery --domain photo")
    return "\n".join(lines)

