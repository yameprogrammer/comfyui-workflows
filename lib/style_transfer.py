"""
Style transfer orchestration (TRANSFORM shelf).

Research SSOT: docs/style_transfer_research.md

Default: Qwen multi-image / instruction edit (content preserve + style apply).
Optional: Lonecat soft I2I for photoreal-friendly light restyle.
"""

from __future__ import annotations

import os
from typing import Any

from lib.comfy_client import fail_result, ok_result, utc_now_iso, write_meta

# Named styles: agent-facing ids → dialect clauses (no tag-soup fluff)
STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "anime": {
        "label": "Anime / cel illustration",
        "clauses": (
            "Japanese anime cel-shaded illustration, clean lineart, vibrant flat colors, "
            "expressive eyes, soft cel gradients, studio anime key visual"
        ),
    },
    "oil_paint": {
        "label": "Oil painting",
        "clauses": (
            "classical oil painting on canvas, visible brush strokes, rich impasto texture, "
            " Rembrandt lighting, museum fine art"
        ),
    },
    "watercolor": {
        "label": "Watercolor",
        "clauses": (
            "delicate watercolor painting, soft wet-on-wet blooms, paper texture, "
            "translucent pigments, loose edges"
        ),
    },
    "comic": {
        "label": "Western comic / ink",
        "clauses": (
            "bold comic book ink lines, Ben-Day dots optional, graphic novel panel style, "
            "high contrast inks, dynamic shading"
        ),
    },
    "noir": {
        "label": "Film noir grade",
        "clauses": (
            "high-contrast black-and-white film noir still, deep shadows, hard key light, "
            "silver gelatin grain, 1940s cinema look"
        ),
    },
    "cyberpunk": {
        "label": "Cyberpunk neon",
        "clauses": (
            "cyberpunk aesthetic, neon magenta-cyan rim light, rainy night reflections, "
            "futuristic city mood, cinematic sci-fi still"
        ),
    },
    "3d_render": {
        "label": "Stylized 3D / CGI",
        "clauses": (
            "stylized 3D character render, subsurface skin, soft studio HDRI, "
            "Octane-like materials, clean CGI look"
        ),
    },
    "pixel": {
        "label": "Pixel art",
        "clauses": (
            "crisp pixel art, limited color palette, 16-bit game sprite aesthetic, "
            "clear pixel clusters, no blur"
        ),
    },
    "sketch": {
        "label": "Pencil sketch",
        "clauses": (
            "graphite pencil sketch on paper, cross-hatching, construction lines soft, "
            "monochrome drawing"
        ),
    },
    "line_art": {
        "label": "Clean line art",
        "clauses": (
            "clean black line art on white, inked contours, minimal fill, "
            "illustration outline style"
        ),
    },
    "ukiyo_e": {
        "label": "Ukiyo-e woodblock",
        "clauses": (
            "Japanese ukiyo-e woodblock print style, flat color fields, bold outlines, "
            "Edo period print texture"
        ),
    },
    "impressionist": {
        "label": "Impressionist",
        "clauses": (
            "impressionist oil painting, broken color, soft edges, outdoor light dapple, "
            "Monet-like atmosphere"
        ),
    },
    "clay": {
        "label": "Claymation / plasticine",
        "clauses": (
            "stop-motion claymation figure, plasticine texture, soft studio light, "
            "tactile handmade look"
        ),
    },
    "photoreal_clean": {
        "label": "Clean photoreal (de-stylize)",
        "clauses": (
            "clean photoreal cinematic still, natural skin texture, realistic lens, "
            "neutral color science, no illustration"
        ),
    },
    "vintage_film": {
        "label": "Vintage film still",
        "clauses": (
            "1970s color film still, halation, soft grain, muted primaries, "
            "anamorphic mild flare, analog cinema"
        ),
    },
    "ink_wash": {
        "label": "East Asian ink wash",
        "clauses": (
            "sumi-e ink wash painting, expressive black ink, sparse composition, "
            "rice paper texture"
        ),
    },
}

STRENGTH_PHRASES = {
    "soft": (
        "Apply a subtle restyle. Keep photoreal cues and fine identity detail where possible; "
        "shift medium only lightly."
    ),
    "medium": (
        "Balance stylization and identity: clearly show the target medium while keeping "
        "the same person and pose readable."
    ),
    "hard": (
        "Commit strongly to the target artistic medium. Bold stylization is OK as long as "
        "identity and pose remain recognizable."
    ),
}

MODES = ("ref", "preset", "look")
ENGINES = ("qwen", "i2i")


def list_style_ids() -> list[str]:
    return sorted(STYLE_PRESETS.keys())


def get_style_preset(style_id: str) -> dict[str, Any]:
    key = (style_id or "").strip().lower().replace(" ", "_").replace("-", "_")
    if key not in STYLE_PRESETS:
        known = ", ".join(list_style_ids())
        raise KeyError(f"Unknown style {style_id!r}. Known: {known}")
    out = dict(STYLE_PRESETS[key])
    out["id"] = key
    return out


def format_styles_help() -> str:
    lines = ["id                 label"]
    for sid in list_style_ids():
        lines.append(f"{sid:18s} {STYLE_PRESETS[sid]['label']}")
    return "\n".join(lines)


def build_ref_instruction(
    *,
    extra: str = "",
    strength: str = "medium",
    preserve_identity: bool = True,
) -> str:
    strength = (strength or "medium").lower()
    str_line = STRENGTH_PHRASES.get(strength, STRENGTH_PHRASES["medium"])
    id_line = (
        "Preserve facial identity, hair, body proportions, wardrobe silhouette, "
        "pose, and camera framing from image 1."
        if preserve_identity
        else "You may restyle form freely; keep overall composition from image 1."
    )
    base = (
        "Using image 1 as the CONTENT (subject, pose, composition) and image 2 ONLY as a "
        "STYLE reference: restyle image 1 to match the artistic medium, texture/brushwork, "
        "color palette, and lighting character of image 2. "
        "Do not copy people, faces, logos, or objects from image 2 — transfer style only. "
        f"{id_line} {str_line}"
    )
    extra = (extra or "").strip()
    if extra:
        return f"{base} Additional direction: {extra}"
    return base


def build_preset_instruction(
    style_id: str,
    *,
    extra: str = "",
    strength: str = "medium",
    preserve_identity: bool = True,
) -> str:
    st = get_style_preset(style_id)
    strength = (strength or "medium").lower()
    str_line = STRENGTH_PHRASES.get(strength, STRENGTH_PHRASES["medium"])
    id_line = (
        "Keep the same person identity, face structure, pose, composition, and camera framing."
        if preserve_identity
        else "Composition may stay similar; form can restyle freely."
    )
    base = (
        f"Restyle this image into {st['label']} ({st['id']}). "
        f"Style details: {st['clauses']}. "
        f"{id_line} Change medium, palette, and rendering only. {str_line}"
    )
    extra = (extra or "").strip()
    if extra:
        return f"{base} Additional direction: {extra}"
    return base


def build_look_instruction(
    look_core: str,
    *,
    extra: str = "",
    strength: str = "medium",
    preserve_identity: bool = True,
) -> str:
    strength = (strength or "medium").lower()
    str_line = STRENGTH_PHRASES.get(strength, STRENGTH_PHRASES["medium"])
    id_line = (
        "Keep the same person identity, pose, and framing."
        if preserve_identity
        else "Keep composition roughly; restyle freely."
    )
    core = (look_core or "").strip()
    base = (
        f"Restyle this image to match this look / grade dialect: {core}. "
        f"{id_line} Apply tone, palette, lighting character, and medium cues from the look. "
        f"{str_line}"
    )
    extra = (extra or "").strip()
    if extra:
        return f"{base} Additional: {extra}"
    return base


def load_look_positive_core(look_id: str) -> str:
    """Load looks/<id>/prompts/positive_core.txt from repo."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "looks", look_id, "prompts", "positive_core.txt")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"look positive_core missing: {path}")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()
    if not text:
        raise ValueError(f"empty look core: {path}")
    return text


def _run_qwen(
    *,
    content_image: str,
    instruction: str,
    style_image: str | None,
    output_path: str,
    seed: int | None,
    timeout_sec: int,
    meta_out: str | None,
    no_lightning: bool,
    raw_prompt: bool,
) -> dict[str, Any]:
    from generate_qwen_edit import generate_qwen_edit

    return generate_qwen_edit(
        content_image,
        instruction,
        input_image2_path=style_image,
        output_filename=output_path,
        seed=seed,
        timeout_sec=timeout_sec,
        meta_out=meta_out,
        lightning=not no_lightning,
        raw_prompt=raw_prompt,
    )


def _run_i2i(
    *,
    content_image: str,
    style_prompt: str,
    output_path: str,
    denoise: float,
    model_type: str,
    seed: int | None,
    timeout_sec: int,
    meta_out: str | None,
) -> dict[str, Any]:
    from generate_moody_i2i import generate_i2i_image

    # Soft identity phrase + style as change instruction
    instr = (
        f"same subject and composition, restyle: {style_prompt}"
    )
    return generate_i2i_image(
        content_image,
        instr,
        denoise_val=float(denoise),
        model_type=model_type,
        output_filename=output_path,
        seed=seed,
        timeout_sec=timeout_sec,
        meta_out=meta_out,
        negative_text=(
            "different person, identity morph, warped face, extra limbs, "
            "low quality, watermark"
        ),
    )


def run_style_transfer(
    *,
    content_image: str,
    output_path: str,
    mode: str = "preset",
    style: str | None = None,
    style_image: str | None = None,
    look_id: str | None = None,
    engine: str = "qwen",
    strength: str = "medium",
    extra: str = "",
    preserve_identity: bool = True,
    denoise: float | None = None,
    model_type: str = "pro",
    seed: int | None = None,
    timeout_sec: int = 600,
    meta_out: str | None = None,
    no_lightning: bool = False,
) -> dict[str, Any]:
    """
    mode:
      ref    — content + style_image via Qwen multi-ref (engine qwen only)
      preset — named STYLE_PRESETS id
      look   — looks/<look_id> positive_core
    engine:
      qwen — default instruction edit
      i2i  — Lonecat I2I (preset/look text only; ref falls back to qwen)
    """
    if not os.path.isfile(content_image):
        return fail_result(error="SOURCE_MISSING", message=content_image)

    mode = (mode or "preset").lower().strip()
    engine = (engine or "qwen").lower().strip()
    if mode not in MODES:
        return fail_result(error="BAD_MODE", message=f"mode must be one of {MODES}")
    if engine not in ENGINES:
        return fail_result(error="BAD_ENGINE", message=f"engine must be one of {ENGINES}")

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    instruction = ""
    style_meta: dict[str, Any] = {"mode": mode, "engine": engine, "strength": strength}

    if mode == "ref":
        if not style_image or not os.path.isfile(style_image):
            return fail_result(
                error="STYLE_IMAGE_REQUIRED",
                message="mode=ref needs --style-image existing file",
            )
        instruction = build_ref_instruction(
            extra=extra,
            strength=strength,
            preserve_identity=preserve_identity,
        )
        style_meta["style_image"] = os.path.abspath(style_image)
        # ref always qwen multi-image
        engine = "qwen"
    elif mode == "look":
        if not look_id:
            return fail_result(error="LOOK_ID_REQUIRED", message="mode=look needs --look-id")
        try:
            core = load_look_positive_core(look_id)
        except (OSError, ValueError) as e:
            return fail_result(error="LOOK_LOAD_FAILED", message=str(e))
        instruction = build_look_instruction(
            core,
            extra=extra,
            strength=strength,
            preserve_identity=preserve_identity,
        )
        style_meta["look_id"] = look_id
        style_meta["look_core_preview"] = core[:200]
    else:  # preset
        if not style:
            return fail_result(
                error="STYLE_REQUIRED",
                message="mode=preset needs --style (see --list-styles)",
            )
        try:
            st = get_style_preset(style)
        except KeyError as e:
            return fail_result(error="BAD_STYLE", message=str(e))
        instruction = build_preset_instruction(
            st["id"],
            extra=extra,
            strength=strength,
            preserve_identity=preserve_identity,
        )
        style_meta["style"] = st["id"]
        style_meta["style_label"] = st["label"]

    if engine == "i2i" and mode != "ref":
        d = float(denoise) if denoise is not None else (
            0.48 if strength == "soft" else 0.58 if strength == "medium" else 0.68
        )
        r = _run_i2i(
            content_image=content_image,
            style_prompt=instruction,
            output_path=output_path,
            denoise=d,
            model_type=model_type,
            seed=seed,
            timeout_sec=timeout_sec,
            meta_out=meta_out,
        )
        style_meta["denoise"] = d
    else:
        r = _run_qwen(
            content_image=content_image,
            instruction=instruction,
            style_image=style_image if mode == "ref" else None,
            output_path=output_path,
            seed=seed,
            timeout_sec=timeout_sec,
            meta_out=meta_out,
            no_lightning=no_lightning,
            # We already embed identity rules in instruction
            raw_prompt=True,
        )

    if not r.get("ok"):
        return r

    # Enrich meta
    meta_path = r.get("meta_path")
    base_meta = r.get("meta") or {}
    base_meta.update(
        {
            "style_transfer": style_meta,
            "style_instruction_preview": instruction[:400],
            "content_image": os.path.abspath(content_image),
            "tool": "generate_style_transfer",
            "research": "docs/style_transfer_research.md",
            "created_at": utc_now_iso(),
        }
    )
    out_abs = r.get("output_path") or os.path.abspath(output_path)
    if meta_path:
        write_meta(meta_path, base_meta)
    elif output_path:
        mp = os.path.splitext(output_path)[0] + ".json"
        write_meta(mp, base_meta)
        meta_path = mp

    return ok_result(
        output_path=out_abs,
        seed=r.get("seed"),
        prompt_id=r.get("prompt_id"),
        meta=base_meta,
        meta_path=meta_path,
        style_transfer=style_meta,
        instruction=instruction,
    )
