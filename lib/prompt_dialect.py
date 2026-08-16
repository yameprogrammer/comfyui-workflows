"""Still-model prompt dialects — official recipes agents must apply before generate_*.

Discovery only. No Comfy. Pair with tool_intent (which CLI) then this (how to write -p).
"""

from __future__ import annotations

from typing import Any

# One card per still family the factory actually exposes.
# `ref` is the SSOT markdown (do not copy the full recipe here).
DIALECTS: list[dict[str, Any]] = [
    {
        "id": "krea",
        "cli": "generate_krea",
        "scripts": ["generate_krea.py", "generate_krea_nsfw.py", "generate_krea_draft.py"],
        "when": "시네·패션·실사 키프레임 기본",
        "when_not": "애니 태그 · 타이포 히어로 · 마스크 인페",
        "official": "krea-ai/krea-2 docs/prompting.md — Qwen3-VL reads NL prose, not CLIP tags",
        "form": "one English paragraph 90–140w",
        "order": "Medium → shot/angle → subject+pose → wardrobe/materials → props → setting → light/grade",
        "template": (
            "Photoreal cinematic film still, [shot size + angle]. "
            "A solitary [subject + concrete pose]. [fabrics by name]. "
            "[props + spatial lock]. [real setting]. [light], natural skin texture, sharp focus on [POI]."
        ),
        "example": (
            "Photoreal cinematic film still, medium shot waist-up at slight low angle. "
            "A solitary mid-20s Korean woman stands under one yellow nylon parasol; she occupies the right third. "
            "Cream knit rib cardigan over white cotton blouse, wet dark asphalt, overcast soft key, natural skin texture."
        ),
        "dont": "Danbooru soup · masterpiece/8k · NO-spam in positive · casting-plate merge",
        "negative": "optional short slot only (twins, plastic skin, logos) — never in -p",
        "ref": "skills/generation-prompt/references/krea2_still_prompts.md",
        "keywords": ["krea", "krea2", "시네", "실사", "키프레임", "generate_krea"],
    },
    {
        "id": "zimage",
        "cli": "generate_moody",
        "scripts": ["generate_moody.py", "generate_moody_i2i.py", "generate_moody_controlnet.py"],
        "when": "Z-Image I2I/실험 · 절 스택 실사",
        "when_not": "시네 기본(Krea) · 애니 XL",
        "official": "Tongyi-MAI/Z-Image-Turbo HF PROMPTING — long detailed; LLM enhance; ~512 token cap; Turbo often ignores negatives",
        "form": "English clause stack 40–120w (hero 80–250w OK if precise)",
        "order": "look → identity → wardrobe → SHOT → ACTION → SETTING → LIGHT → MATERIALS",
        "template": (
            "[look], [identity short], [wardrobe], [shot size, angle, lens], [concrete action], "
            "[setting], [light], [2–4 materials], photoreal film still, sharp focus on [POI]"
        ),
        "example": (
            "cinematic photoreal film still, mid-20s Korean woman freckles, cream knit cardigan, "
            "medium shot 35mm eye level, standing under yellow parasol, wet Seoul asphalt, overcast, natural skin"
        ),
        "dont": "rely on negatives · masterpiece soup · Krea 140w essay",
        "negative": "weak on Turbo — put constraints in POSITIVE (solitary, feet planted)",
        "ref": "skills/generation-prompt/references/moody_zimage.md",
        "keywords": ["zimage", "z-image", "moody", "lonecat", "generate_moody"],
    },
    {
        "id": "illustrious",
        "cli": "generate_illustrious_standard",
        "scripts": [
            "generate_illustrious_standard.py",
            "generate_illustrious_advanced.py",
            "generate_illustrious_detailer.py",
        ],
        "when": "애니/일루스 Danbooru XL",
        "when_not": "실사 키프레임 · SDXL Juggernaut",
        "official": "Illustrious/NoobAI + Animagine-style tag order — quality tags ARE required",
        "form": "comma Danbooru tags, quality prefix first",
        "order": "quality → count/id → hair/eyes/clothes → framing/angle/action → background/light/style",
        "template": (
            "masterpiece, best quality, newest, absurdres, 1girl, solo, [hair], [eyes], [outfit], "
            "cowboy shot, [action], [setting], anime coloring"
        ),
        "example": (
            "masterpiece, best quality, newest, absurdres, 1girl, solo, dark wavy hair, brown eyes, "
            "school uniform, cowboy shot, from below, holding umbrella, rainy street, cel shading"
        ),
        "dont": "Krea paragraph · close-up + full body together · skip quality tags",
        "negative": "worst quality, low quality, extra limbs, photoreal, 3d",
        "ref": "skills/generation-prompt/references/illustrious_tags.md",
        "keywords": ["illustrious", "danbooru", "noobai", "fabricated", "generate_illustrious"],
    },
    {
        "id": "anima",
        "cli": "generate_anima",
        "scripts": ["generate_anima.py"],
        "when": "2D 애니/만화/웹툰 초고속",
        "when_not": "실사 · CLI 기본 soup 그대로 제출",
        "official": "CircleStone Anima — hybrid Danbooru + short NL; anime-specialized 2B",
        "form": "quality tags + count + look + short pose NL",
        "order": "quality → count → character → hair/eyes/outfit → pose → setting → style",
        "template": (
            "masterpiece, best quality, anime illustration, 1girl, solo, [hair], [eyes], [outfit], "
            "[pose], [location], clean lineart, cel shading"
        ),
        "example": (
            "masterpiece, best quality, anime illustration, 1girl, solo, silver bob, red eyes, "
            "black sailor uniform, standing on rooftop at dusk, cel shading, detailed eyes"
        ),
        "dont": "photoreal/8k/raw photo · ship factory default soup",
        "negative": "worst quality, photoreal, 3d, extra limbs, bad hands",
        "ref": "skills/generation-prompt/references/anima_2d.md",
        "keywords": ["anima", "lllite", "웹툰", "셀채색", "generate_anima"],
    },
    {
        "id": "flux1",
        "cli": "generate_flux",
        "scripts": ["generate_flux.py"],
        "when": "Flux.1 프롬프트 추종 · 짧은 화면 글자 · 일러스트",
        "when_not": "시네 기본(Krea) · 타이포 히어로(Ideogram)",
        "official": "Black Forest Labs FLUX Prompting Guide — NL; Subject+Action+Style+Context; no negatives",
        "form": "natural English 30–80w (short 10–30 scout; 80+ only if every clause earns it)",
        "order": "Subject → Action → Style → Context (front-load what matters)",
        "template": (
            "[subject doing action], [style/medium], [setting + time], "
            "shot on [camera/lens], [lighting], [palette]. "
            "On-image text in quotes: the sign reads \"OPEN\"."
        ),
        "example": (
            "A red bicycle leaning on a wet brick alley wall at night, cinematic still, "
            "neon puddle reflections, low angle 35mm, shallow depth of field, shot on Kodak Portra 400"
        ),
        "dont": "Danbooru soup · negative lists · masterpiece/8k · Krea 140w essay",
        "negative": "FLUX.1: leave empty. Describe what you WANT (empty street, not no people)",
        "ref": "skills/generation-prompt/references/flux_still.md",
        "keywords": ["flux", "flux1", "flux.1", "generate_flux"],
    },
    {
        "id": "flux_fill",
        "cli": "generate_flux_fill",
        "scripts": ["generate_flux_fill.py"],
        "when": "실사/일반 마스크 인페",
        "when_not": "마스크 없이 지시(Qwen) · 애니 인페(Anima)",
        "official": "FLUX.1 Fill / BFL Tools — prompt = contents of the hole only",
        "form": "short NL of the replacement + match surrounding light",
        "order": "what appears in the white mask → match light/material",
        "template": "[object/material in the hole], matching surrounding light and color, keep unmasked pixels",
        "example": "smooth ceramic cup lid, no straw, same cafe lighting and condensation",
        "dont": "re-essay the whole frame · Qwen mega-edit language",
        "negative": "empty",
        "ref": "skills/generation-prompt/references/flux_still.md",
        "keywords": ["flux fill", "flux inpaint", "generate_flux_fill"],
    },
    {
        "id": "flux2_klein",
        "cli": "generate_flux2_klein",
        "scripts": ["generate_flux2_klein.py"],
        "when": "Flux.2 Klein 빠른 T2I/I2I",
        "when_not": "시네 기본 · Qwen 지시 편집 (edit 가중치 없음)",
        "official": "BFL FLUX.2 guide + Klein note: no prompt upsampling — write the detail yourself; Qwen3-8B NL",
        "form": "NL 30–80w; I2I = change-first + keep rest",
        "order": "T2I: Subject→Action→Style→Context. I2I: CHANGE then keep [identity/framing]",
        "template": (
            "T2I: [subject+action], [style], [setting+light+camera]. "
            "I2I: [one change]. Keep the same [face/wardrobe/framing]."
        ),
        "example": (
            "T2I: vintage motorcycle parked at a retro diner sunset, 80s vintage photo, film grain, warm cast. "
            "I2I: replace the sky with overcast coastal sunset. Keep the motorcycle and diner."
        ),
        "dont": "treat I2I as Qwen edit · expect auto-upsample · hex/JSON unless you really need brand color",
        "negative": "FLUX.2 has no negatives — describe empty/sharp instead of no people/no blur",
        "ref": "skills/generation-prompt/references/flux_still.md",
        "keywords": ["klein", "flux2", "flux 2", "generate_flux2_klein"],
    },
    {
        "id": "sdxl",
        "cli": "generate_sdxl",
        "scripts": ["generate_sdxl.py"],
        "when": "클래식 SDXL 실사 / Lightning 스카우트 / Pony",
        "when_not": "시네 기본(Krea) · Illustrious 애니 XL",
        "official": "RunDiffusion Juggernaut — Natural language OR tagging; Ragnarok accepts both. Pony = score tags",
        "form": "juggernaut/nsfw: short NL 20–50w · lightning: even shorter · pony: score + tags",
        "order": "subject → wardrobe → light → lens  |  pony: score_9… then 1girl, solo, …",
        "template": (
            "juggernaut: cinematic portrait of [subject], [wardrobe], [light], [lens], film grain. "
            "pony: (auto score_9) 1girl, solo, [look], [outfit], [framing], looking at viewer"
        ),
        "example": "cinematic portrait of a Korean woman, wool coat, window light, 85mm, film grain",
        "dont": "Illustrious quality soup on Juggernaut · 200-token NO-list · episode default keyframe",
        "negative": "factory default is enough (lowres, extra fingers). Don't dump novels.",
        "ref": "skills/generation-prompt/references/sdxl_still.md",
        "keywords": ["sdxl", "juggernaut", "dreamshaper", "pony", "generate_sdxl"],
    },
    {
        "id": "qwen_edit",
        "cli": "generate_qwen_edit",
        "scripts": ["generate_qwen_edit.py", "generate_qwen_inpaint.py", "generate_qwen_angle.py"],
        "when": "문장 편집 / 마스크 부위 / 멀티앵글",
        "when_not": "빈 화면 T2I (베이스 가중치 없음)",
        "official": "Qwen-Image-Edit — imperative one change; keep everything else unchanged; chain small edits",
        "form": "imperative English, one verb",
        "order": "CHANGE. Keep the same [identity/framing/wardrobe].",
        "template": "[Verb the change]. Keep the same [face, wardrobe, framing]. Photoreal.",
        "example": "Remove the plastic straw from the iced drink. Keep the same cup, woman, and framing.",
        "dont": "mega multi-change · make it better only · inpaint prompt about unmasked area",
        "negative": "usually unused",
        "ref": "skills/generation-prompt/references/qwen_edit.md",
        "keywords": ["qwen", "edit", "inpaint", "angle", "generate_qwen"],
    },
    {
        "id": "ideogram",
        "cli": "generate_ideogram4",
        "scripts": ["generate_ideogram4.py", "generate_boogu_typo.py"],
        "when": "화면에 읽을 글자가 히어로",
        "when_not": "글자 없는 인물 스틸",
        "official": "Ideogram 4 prompting.md — structured JSON captions; text=literal glyphs",
        "form": "factory --slot + --text  |  Boogu: exactly reading \"TITLE\"",
        "order": "literal string in --text / quotes; scene in --scene",
        "template": 'generate_ideogram4 --slot title_card --text "에피소드 제목" --scene "rainy Seoul night"',
        "example": 'masthead text exactly reading "LUXE", subtitle exactly reading "RAIN ISSUE"',
        "dont": "hope free prose spells a brand · use Ideogram for no-text Krea shots",
        "negative": "n/a",
        "ref": "skills/generation-prompt/references/ideogram4_typography.md",
        "keywords": ["ideogram", "boogu", "타이포", "간판", "포스터"],
    },
]


def get_dialect(name: str) -> dict[str, Any] | None:
    key = (name or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "krea2": "krea",
        "generate_krea": "krea",
        "generate_krea_nsfw": "krea",
        "moody": "zimage",
        "z_image": "zimage",
        "generate_moody": "zimage",
        "illustrious_standard": "illustrious",
        "generate_illustrious_standard": "illustrious",
        "generate_anima": "anima",
        "flux": "flux1",
        "flux_dev": "flux1",
        "generate_flux": "flux1",
        "generate_flux_fill": "flux_fill",
        "fill": "flux_fill",
        "klein": "flux2_klein",
        "flux2": "flux2_klein",
        "generate_flux2_klein": "flux2_klein",
        "generate_sdxl": "sdxl",
        "juggernaut": "sdxl",
        "pony": "sdxl",
        "qwen": "qwen_edit",
        "generate_qwen_edit": "qwen_edit",
        "generate_qwen_inpaint": "qwen_edit",
        "generate_ideogram4": "ideogram",
        "boogu": "ideogram",
    }
    key = aliases.get(key, key)
    for d in DIALECTS:
        if d["id"] == key or d["cli"] == key:
            return d
        if key in [s.replace(".py", "") for s in d["scripts"]]:
            return d
    return None


def search_dialects(query: str, *, limit: int = 4) -> list[dict[str, Any]]:
    tokens = [t.lower() for t in (query or "").replace("/", " ").split() if t.strip()]
    if not tokens:
        return list(DIALECTS)[:limit]
    scored: list[tuple[float, dict[str, Any]]] = []
    for d in DIALECTS:
        blob = " ".join(
            [
                d["id"],
                d["cli"],
                d["when"],
                d["when_not"],
                " ".join(d.get("keywords") or []),
            ]
        ).lower()
        score = 0.0
        for t in tokens:
            if t in (d.get("keywords") or []):
                score += 3.0
            elif t in blob:
                score += 1.2
            if t == d["id"]:
                score += 5.0
        q = " ".join(tokens)
        if d["id"] == "flux_fill" and "fill" in q:
            score += 4.0
        if d["id"] == "flux1" and "fill" in q:
            score -= 2.0
        if score > 0:
            row = dict(d)
            row["score"] = round(score, 2)
            scored.append((score, row))
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored[: max(1, int(limit))]]


def format_card(d: dict[str, Any], *, verbose: bool = True) -> str:
    lines = [
        f"[{d['id']}] {d['cli']}",
        f"  when: {d['when']}",
        f"  not:  {d['when_not']}",
        f"  official: {d['official']}",
        f"  form: {d['form']}",
        f"  order: {d['order']}",
    ]
    if verbose:
        lines.extend(
            [
                f"  template: {d['template']}",
                f"  example:  {d['example']}",
                f"  don't:    {d['dont']}",
                f"  negative: {d['negative']}",
                f"  ref:      {d['ref']}",
            ]
        )
    else:
        lines.append(f"  ref: {d['ref']}")
    return "\n".join(lines)
