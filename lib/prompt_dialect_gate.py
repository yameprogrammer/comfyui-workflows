"""Fail-loud prompt dialect checks so agents cannot skip generation-prompt.

  from lib.prompt_dialect_gate import refuse_or_hint, check_anima_prompt, check_music_caption
"""

from __future__ import annotations

from typing import Any

from lib.clip_quality import check_i2v_prompt

DIALECT_HINT = {
    "generate_anima": "skills/generation-prompt/references/anima_2d.md",
    "generate_i2v": "skills/generation-prompt/references/ltx23_video.md",
    "generate_camera_move": "skills/generation-prompt/references/camera_move.md",
    "generate_minimax_music": "skills/generation-prompt/references/music_audio.md",
    "generate_krea": "skills/generation-prompt/references/krea2_still_prompts.md",
    "generate_flux": "skills/generation-prompt/references/flux_still.md",
    "generate_flux_fill": "skills/generation-prompt/references/flux_still.md",
    "generate_flux2_klein": "skills/generation-prompt/references/flux_still.md",
    "generate_sdxl": "skills/generation-prompt/references/sdxl_still.md",
}

ANIMA_SOUP = "1girl, anime masterpiece, exquisite face, detailed lighting, rich colors, studio quality, 8k render"

_MUSIC_VISUAL = (
    "photoreal",
    "8k",
    "4k",
    "medium shot",
    "film still",
    "a woman stands",
    "a man stands",
    "cinematic portrait",
    "depth of field",
    "bokeh",
    "masterpiece",
)


def matrix_hint(cli: str) -> str:
    ref = DIALECT_HINT.get(cli, "skills/generation-prompt/references/model_prompt_matrix.md")
    return (
        f"Write a dialect-correct prompt (generation-prompt). "
        f"See {ref} · skills/generation-prompt/references/model_prompt_matrix.md. "
        f"Debug only: --force-prompt"
    )


def check_anima_prompt(prompt: str | None) -> dict[str, Any]:
    text = (prompt or "").strip()
    low = text.lower()
    if not text or text == ANIMA_SOUP:
        return {
            "ok": False,
            "error": "PROMPT_DIALECT",
            "message": "Anima default soup refused. Write 2D tags (count, hair, pose, setting). " + matrix_hint("generate_anima"),
        }
    soup_hits = sum(1 for t in ("anime masterpiece", "8k render", "exquisite face") if t in low)
    if soup_hits >= 2 and "1girl" in low and len(text) < 120:
        return {
            "ok": False,
            "error": "PROMPT_DIALECT",
            "message": "Anima prompt looks like the factory default soup. " + matrix_hint("generate_anima"),
        }
    if any(t in low for t in ("photoreal", "raw photo", "35mm film still", "dslr")):
        return {
            "ok": False,
            "error": "PROMPT_DIALECT",
            "message": "Photoreal language on Anima (2D). Use generate_krea or rewrite as anime tags. " + matrix_hint("generate_anima"),
        }
    return {"ok": True}


def check_music_caption(caption: str | None) -> dict[str, Any]:
    text = (caption or "").strip()
    if not text:
        return {
            "ok": False,
            "error": "PROMPT_DIALECT",
            "message": "MiniMax --caption required (Global Metadata / Vocal Details / Arrangement). " + matrix_hint("generate_minimax_music"),
        }
    low = text.lower()
    hits = [t for t in _MUSIC_VISUAL if t in low]
    if hits:
        return {
            "ok": False,
            "error": "PROMPT_DIALECT",
            "message": "Caption looks like an image prompt ("
            + ", ".join(hits[:4])
            + "). Use genre/BPM/instruments. "
            + matrix_hint("generate_minimax_music"),
        }
    return {"ok": True}


def check_motion_prompt(prompt: str | None) -> dict[str, Any]:
    dq = check_i2v_prompt(prompt or "")
    if dq.get("ok"):
        return {"ok": True, "detail": dq}
    msg = "; ".join(dq.get("warnings") or ["bad I2V prompt"])
    return {
        "ok": False,
        "error": "PROMPT_DIALECT",
        "message": msg + ". " + matrix_hint("generate_i2v"),
        "detail": dq,
    }


def refuse_or_hint(check: dict[str, Any], *, force: bool, stream) -> bool:
    """Print fail or warn. Return True if caller should abort."""
    if check.get("ok"):
        return False
    line = f"[{check.get('error', 'PROMPT_DIALECT')}] {check.get('message')}"
    if force:
        print(f"[WARN] {line}", file=stream)
        return False
    print(f"[FAILED] {line}", file=stream)
    return True
