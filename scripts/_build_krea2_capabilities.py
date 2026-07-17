"""Extract Krea2 v10 switches, bypassers, notes → agent capability map + guide."""
from __future__ import annotations

import json
import re
from pathlib import Path

UI = Path(r"F:\ComfyUI_workflows\krea2SFWNSFWUncensoredImageTo_v10.json")
# prefer longer/full copy if same structure
if not UI.exists():
    UI = Path(
        r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows"
        r"\krea2SFWNSFWUncensoredImageTo_v10.json"
    )

OUT_JSON = Path(
    r"F:\ComfyUI_workflows\agent_custom\workflows\human"
    r"\Krea2_SFW_NSFW_v10_CAPABILITIES.json"
)
OUT_MD = Path(
    r"F:\ComfyUI_workflows\agent_custom\workflows\human"
    r"\Krea2_SFW_NSFW_v10_AGENT_GUIDE.md"
)
FEATURE_PRESETS = Path(
    r"F:\ComfyUI_workflows\agent_custom\workflows\agent\presets"
    r"\lonecat_feature_presets.json"
)


def in_group(x: float, y: float, bb: list) -> bool:
    if not bb or len(bb) < 4:
        return False
    gx, gy, gw, gh = bb[0], bb[1], bb[2], bb[3]
    return gx <= x <= gx + gw and gy <= y <= gy + gh


def node_xy(n: dict) -> tuple[float, float]:
    pos = n.get("pos") or [0, 0]
    if isinstance(pos, dict):
        return float(pos.get(0, 0)), float(pos.get(1, 0))
    return float(pos[0]), float(pos[1])


def note_text(n: dict) -> str:
    w = n.get("widgets_values")
    if isinstance(w, list) and w:
        return str(w[0] if not isinstance(w[0], dict) else w)
    if isinstance(w, str):
        return w
    return ""


def main() -> None:
    ui = json.loads(UI.read_text(encoding="utf-8"))
    nodes = ui["nodes"]
    groups = [g for g in (ui.get("groups") or []) if isinstance(g, dict)]
    links = ui.get("links") or []

    # groups + members
    ginfo = []
    for gi, g in enumerate(groups):
        bb = g.get("bounding") or []
        members = []
        for n in nodes:
            x, y = node_xy(n)
            if in_group(x, y, bb):
                members.append(
                    {
                        "id": n["id"],
                        "type": n.get("type"),
                        "title": n.get("title"),
                        "mode": n.get("mode"),
                    }
                )
        ginfo.append(
            {
                "index": gi,
                "title": g.get("title") or "",
                "color": g.get("color"),
                "bounding": bb,
                "member_count": len(members),
                "members": members,
                "types": sorted({m["type"] for m in members if m.get("type")}),
            }
        )

    # bypassers
    bypassers = []
    for n in nodes:
        t = n.get("type") or ""
        if "Bypass" not in t and "Muter" not in t:
            continue
        props = n.get("properties") or {}
        mt = props.get("matchTitle") or ""
        matched = []
        for g in ginfo:
            title = g["title"] or ""
            if not mt:
                continue
            # regex matchTitle (Krea uses regex for Prompt groups)
            try:
                if mt.startswith("^") or ".*" in mt or "(?" in mt:
                    if re.search(mt, title, flags=re.I):
                        matched.append(title)
                elif mt.lower() in title.lower() or mt in title:
                    matched.append(title)
            except re.error:
                if mt in title:
                    matched.append(title)
        bypassers.append(
            {
                "id": n["id"],
                "type": t,
                "title": n.get("title") or "",
                "matchTitle": mt,
                "matchColors": props.get("matchColors") or "",
                "toggleRestriction": props.get("toggleRestriction") or "default",
                "matched_groups": matched,
                "mode": n.get("mode"),
            }
        )

    # switches
    switches = []
    for n in nodes:
        t = n.get("type") or ""
        title = n.get("title") or ""
        if "Switch" not in t and "switch" not in title and t not in (
            "BooleanSwitchNode",
            "ComfySwitchNode",
            "ComfyOrNode",
            "ImpactIfNone",
        ):
            continue
        linked = [inp.get("name") for inp in (n.get("inputs") or []) if inp.get("link") is not None]
        switches.append(
            {
                "id": n["id"],
                "type": t,
                "title": title,
                "linked_inputs": linked,
                "widgets": n.get("widgets_values"),
                "mode": n.get("mode"),
            }
        )

    # text description nodes
    notes = []
    for n in nodes:
        t = n.get("type") or ""
        if t not in (
            "MarkdownNote",
            "Note",
            "Label (rgthree)",
            "easy string",
            "PrimitiveStringMultiline",
        ):
            # also Labels always
            if t != "Label (rgthree)":
                continue
        text = note_text(n)
        title = n.get("title") or ""
        if t == "Label (rgthree)" and not title and not text:
            continue
        if t in ("MarkdownNote", "Note") and len(text.strip()) < 3 and not title:
            continue
        # skip huge prompt bodies as "notes" if title is POSITIVE PROMPT - still record short
        entry = {
            "id": n["id"],
            "type": t,
            "title": title,
            "text": text if len(text) < 4000 else text[:4000] + "\n…(truncated)…",
            "mode": n.get("mode"),
        }
        notes.append(entry)

    # key functional nodes
    key_nodes = []
    for n in nodes:
        t = n.get("type") or ""
        title = n.get("title") or ""
        if any(
            k in t
            for k in (
                "UNET",
                "CLIP",
                "VAE",
                "LoadImage",
                "EmptyLatent",
                "KSampler",
                "Clown",
                "Seed",
                "Krea",
                "Save",
                "Florence",
                "TextGenerate",
            )
        ) or title in ("POSITIVE PROMPT", "Reference image", "System prompt"):
            w = n.get("widgets_values")
            if isinstance(w, list) and len(repr(w)) > 200:
                wshow = repr(w)[:200] + "…"
            else:
                wshow = w
            key_nodes.append(
                {
                    "id": n["id"],
                    "type": t,
                    "title": title,
                    "mode": n.get("mode"),
                    "widgets": wshow,
                }
            )

    # curated features for agents
    features = [
        {
            "feature_id": "krea2_t2i",
            "name": "Krea2 Text-to-Image (core)",
            "category": "t2i",
            "ui_groups_on": ["Models", "Main settings", "Prompt", "Main sampler", "Resolution"],
            "ui_groups_off": ["Image to prompt", "Prompt enhancer", "SeedVR2 upscaler"],
            "bypassers": [
                {"id": 43, "matchTitle": "Image to prompt", "set": "bypass/off for pure T2I"},
                {"id": 47, "matchTitle": "prompt enhancer", "set": "bypass/off for smoke"},
                {"id": 16, "matchTitle": "SeedVR2 upscaler", "set": "off unless 4K needed"},
            ],
            "agent_preset": "krea2_t2i_v10",
            "status": "ready",
            "when_to_use": "Default Krea2 photoreal T2I; CLIP type must be krea2",
            "ports": "presets/krea2_t2i_v10.ports.json",
        },
        {
            "feature_id": "krea2_img2prompt",
            "name": "Image to prompt (reference → caption)",
            "category": "prompt",
            "ui_groups_on": ["Image to prompt"],
            "bypassers": [{"id": 43, "matchTitle": "Image to prompt", "set": "ON"}],
            "ui_nodes": [{"id": 44, "type": "LoadImage", "title": "Reference image", "mode_when_off": 4}],
            "agent_preset": None,
            "status": "planned",
            "when_to_use": "Derive prompt from a reference still before generation",
        },
        {
            "feature_id": "krea2_prompt_enhancer",
            "name": "Prompt enhancer",
            "category": "prompt",
            "ui_groups_on": ["Prompt enhancer"],
            "bypassers": [{"id": 47, "matchTitle": "prompt enhancer", "set": "ON"}],
            "agent_preset": None,
            "status": "planned",
            "when_to_use": "Expand short prompts; may need extra models / slower",
            "default_for_batch": "OFF",
        },
        {
            "feature_id": "krea2_resolution_simple",
            "name": "Simple image size",
            "category": "resolution",
            "ui_groups_on": ["Simple image size"],
            "bypassers": [
                {"id": 18, "matchTitle": "image size", "restriction": "max one", "set": "Simple image size"}
            ],
            "status": "documented",
            "when_to_use": "Quick fixed resolutions",
        },
        {
            "feature_id": "krea2_resolution_advanced",
            "name": "Advanced image size",
            "category": "resolution",
            "ui_groups_on": ["Advanced image size"],
            "bypassers": [
                {"id": 18, "matchTitle": "image size", "restriction": "max one", "set": "Advanced image size"}
            ],
            "status": "documented",
            "when_to_use": "Custom / calculated sizes",
        },
        {
            "feature_id": "krea2_2nd_pass",
            "name": "2nd pass refine",
            "category": "refine",
            "ui_groups_on": ["2nd pass"],
            "bypassers": [
                {"id": 14, "title": "2nd pass", "matchTitle": "2nd pass", "set": "ON"},
                {"id": 95, "matchTitle": "2nd pass", "set": "ON"},
            ],
            "status": "planned",
            "when_to_use": "Second sampling pass for detail",
        },
        {
            "feature_id": "krea2_seedvr2",
            "name": "SeedVR2 upscaler",
            "category": "upscale",
            "ui_groups_on": ["SeedVR2 upscaler"],
            "bypassers": [
                {"id": 16, "title": "Upscaler", "matchTitle": "SeedVR2 upscaler", "set": "ON"},
                {"id": 88, "matchTitle": "SeedVR2 upscaler", "set": "ON"},
            ],
            "status": "planned",
            "when_to_use": "4K upscale; high VRAM",
            "default_for_batch": "OFF",
        },
        {
            "feature_id": "krea2_post_noise_color_sharpen",
            "name": "Post: Noise / Color / Sharpen",
            "category": "post",
            "ui_groups_on": ["Noise", "Color correction", "Sharpen"],
            "bypassers": [
                {"id": 15, "title": "Extra nodes", "set": "controls extra post groups"},
                {"id": 89, "title": "Extra nodes", "set": "duplicate Extra nodes control"},
            ],
            "status": "documented",
            "when_to_use": "Film grain, grade, sharpen polish",
        },
        {
            "feature_id": "krea2_civitai_metadata",
            "name": "CivitAI metadata save",
            "category": "io",
            "ui_groups_on": ["CivitAI metadata"],
            "status": "documented",
            "when_to_use": "Embed hashes for CivitAI; WidgetToString may break pure API — agent T2I uses SaveImage instead",
            "agent_note": "krea2_t2i_v10 strips this path for reliability",
        },
        {
            "feature_id": "krea2_krea2t_enhancer",
            "name": "ComfyUI-Krea2T-Enhancer (model patch)",
            "category": "model",
            "ui_nodes": [{"id": 4, "type": "ComfyUI-Krea2T-Enhancer"}],
            "status": "ready_in_t2i_preset",
            "when_to_use": "On by default in main model chain; strength widget on node 4",
        },
    ]

    policy = {
        "default_t2i": "krea2_t2i_v10",
        "family": "krea2",
        "source_workflow": "krea2SFWNSFWUncensoredImageTo_v10",
        "selection_rules": [
            "Use family=krea2 or -p krea2_t2i_v10 for Krea2; never put Krea2 UNET into Lonecat (CLIP type mismatch)",
            "CLIPLoader type must be krea2",
            "T2I batch: Image-to-prompt OFF, Prompt enhancer OFF, SeedVR2 OFF unless user asks",
            "Resolution: Simple vs Advanced via image size bypasser (max one)",
            "New feature combo = UI bypassers fixed → graphToPrompt → presets/*.api.json + ports + status ready",
            "Port patch only; no convert_ui_to_api on full graph for production",
        ],
        "clip_type": "krea2",
        "default_unet": r"Krea2Turbo\krea2_turbo_fp8_scaled.safetensors",
        "default_clip": "Huihui-Qwen3-VL-4B-Instruct-abliterated-fp8_scaled.safetensors",
        "default_vae": "qwen_image_vae.safetensors",
    }

    cap = {
        "workflow": "krea2SFWNSFWUncensoredImageTo_v10",
        "version": 1,
        "source_ui": str(UI),
        "node_count": len(nodes),
        "group_count": len(groups),
        "features": features,
        "agent_policy": policy,
        "bypassers": bypassers,
        "switches": switches,
        "notes_and_labels": notes,
        "groups": [
            {
                "title": g["title"],
                "color": g["color"],
                "member_count": g["member_count"],
                "types": g["types"][:30],
            }
            for g in ginfo
        ],
        "key_nodes": key_nodes,
        "ready_presets": ["krea2_t2i_v10"],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(cap, ensure_ascii=False, indent=2), encoding="utf-8")

    # Update multi-family feature presets file
    if FEATURE_PRESETS.exists():
        fp = json.loads(FEATURE_PRESETS.read_text(encoding="utf-8"))
    else:
        fp = {"version": 1, "presets": {}, "select_preset": {}}
    fp.setdefault("presets", {})["krea2_t2i_v10"] = {
        "feature_ids": ["krea2_t2i", "krea2_krea2t_enhancer"],
        "file": "presets/krea2_t2i_v10.api.json",
        "ports": "presets/krea2_t2i_v10.ports.json",
        "family": "krea2",
        "status": "ready",
        "source_workflow": "krea2SFWNSFWUncensoredImageTo_v10",
        "bypass_state_summary": {
            "Image to prompt": "off",
            "Prompt enhancer": "off (stripped in API for stability)",
            "SeedVR2": "off",
            "CivitAI metadata": "replaced with SaveImage",
        },
    }
    for fid, status in [
        ("krea2_i2i", "planned"),
        ("krea2_img2prompt", "planned"),
        ("krea2_prompt_enhancer", "planned"),
        ("krea2_2nd_pass", "planned"),
        ("krea2_seedvr2", "planned"),
    ]:
        key = fid.replace("krea2_", "krea2_")
        # store planned feature stubs under presets only when full api exists
        pass
    fp.setdefault("select_preset", {})["t2i_krea2"] = "krea2_t2i_v10"
    fp["select_preset"]["by_family"] = {
        **(fp.get("select_preset", {}).get("by_family") or {}),
        "krea2": "krea2_t2i_v10",
        "krea": "krea2_t2i_v10",
        "zimage": "lonecat_t2i_turbo",
        "lonecat": "lonecat_t2i_turbo",
    }
    fp.setdefault("families", {})["krea2"] = {
        "default_t2i": "krea2_t2i_v10",
        "guide": "workflows/human/Krea2_SFW_NSFW_v10_AGENT_GUIDE.md",
        "capabilities": "workflows/human/Krea2_SFW_NSFW_v10_CAPABILITIES.json",
        "source_workflow": "krea2SFWNSFWUncensoredImageTo_v10",
    }
    FEATURE_PRESETS.write_text(json.dumps(fp, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown guide
    lines = [
        "# krea2SFWNSFWUncensoredImageTo_v10 — Agent 선택 가이드",
        "",
        f"**원본:** `{UI}`  ",
        f"**기계 가독:** `{OUT_JSON.name}`  ",
        f"**ready 프리셋:** `krea2_t2i_v10`",
        "",
        "에이전트는 UI 스위치를 누르지 않고 **feature_id / preset** 으로 고른다.",
        "",
        "```text",
        "python scripts/run_workflow_api.py -p krea2_t2i_v10 --positive \"...\" --seed 42",
        "python scripts/run_workflow_api.py --family krea2 --positive \"...\"",
        "python scripts/run_workflow_api.py --list-features",
        "```",
        "",
        "---",
        "",
        "## 1. 그룹 맵 (15)",
        "",
        "| 그룹 | 역할 (노트·구조 기준) |",
        "|------|----------------------|",
    ]
    role_hint = {
        "Models": "UNET / CLIP(krea2) / VAE 로드",
        "Main settings": "시드·글로벌 시드",
        "Resolution": "해상도 상위",
        "Simple image size": "간단 해상도",
        "Advanced image size": "고급 해상도",
        "Prompt": "POSITIVE PROMPT 입력",
        "Image to prompt": "Reference image → 캡션",
        "Prompt enhancer": "프롬프트 강화/LLM",
        "Main sampler": "1st Clownshark pass",
        "2nd pass": "2nd sampling pass",
        "Noise": "그레인",
        "Color correction": "밝기/대비",
        "Sharpen": "샤픈",
        "SeedVR2 upscaler": "SeedVR2 4K",
        "CivitAI metadata": "메타·해시 저장",
    }
    for g in ginfo:
        t = g["title"]
        lines.append(f"| **{t}** | {role_hint.get(t, '—')} · members={g['member_count']} |")

    lines += [
        "",
        "---",
        "",
        "## 2. Fast Groups Bypasser (기능 스위치)",
        "",
        "matchTitle 이 **그룹 제목과 매칭**(일부는 정규식)되면 해당 그룹 on/off.",
        "",
        "| id | title | matchTitle | restriction | 매칭 그룹 |",
        "|----|-------|------------|-------------|-----------|",
    ]
    for b in sorted(bypassers, key=lambda x: x["id"]):
        mg = ", ".join(b["matched_groups"][:5]) or "—"
        lines.append(
            f"| {b['id']} | {(b['title'] or '—').replace('|','/')} | `{b['matchTitle']}` | {b['toggleRestriction']} | {mg} |"
        )

    lines += [
        "",
        "### 선택 요약 (에이전트)",
        "",
        "| 하고 싶은 일 | Bypasser 설정 (UI export 시) | preset |",
        "|--------------|------------------------------|--------|",
        "| **순수 T2I** | Image to prompt OFF, enhancer OFF, SeedVR2 OFF | `krea2_t2i_v10` ✅ |",
        "| 이미지→프롬프트 | Image to prompt ON + Reference image | planned |",
        "| 프롬프트 강화 | prompt enhancer ON | planned |",
        "| 2nd pass | 2nd pass ON | planned |",
        "| 4K | SeedVR2 / Upscaler ON | planned |",
        "| 간단 해상도 | image size → Simple (max one) | documented |",
        "| 고급 해상도 | image size → Advanced (max one) | documented |",
        "",
        "---",
        "",
        "## 3. 설명 노드 (Note / Markdown / Label) — 워크플로우 작성자 가이드",
        "",
    ]
    for n in notes:
        title = n.get("title") or ""
        text = (n.get("text") or "").strip()
        # Labels: title is the instruction
        if n["type"] == "Label (rgthree)":
            if title:
                lines.append(f"- **Label id={n['id']}:** {title}")
            continue
        if n["type"] == "PrimitiveStringMultiline" and title == "POSITIVE PROMPT":
            lines.append(f"- **POSITIVE PROMPT (id={n['id']}):** 메인 유저 프롬프트 슬롯 (에이전트 port `positive`)")
            continue
        if n["type"] == "PrimitiveStringMultiline" and "System" in title:
            lines.append(f"- **{title} (id={n['id']}):** 시스템/엔지니어 프롬프트 (enhancer 경로)")
            continue
        if n["type"] in ("MarkdownNote", "Note"):
            lines.append(f"### id={n['id']} — {title or n['type']}")
            lines.append("")
            lines.append("```")
            lines.append(text[:3000] if text else "(empty)")
            lines.append("```")
            lines.append("")

    lines += [
        "---",
        "",
        "## 4. feature_id 목록",
        "",
    ]
    for f in features:
        lines.append(f"### `{f['feature_id']}` — {f['name']}")
        lines.append("")
        lines.append(f"- **status:** {f.get('status')}")
        lines.append(f"- **when:** {f.get('when_to_use')}")
        if f.get("agent_preset"):
            lines.append(f"- **preset:** `{f['agent_preset']}`")
        if f.get("default_for_batch"):
            lines.append(f"- **batch default:** {f['default_for_batch']}")
        lines.append("")

    lines += [
        "---",
        "",
        "## 5. Any Switch / 기타 분기",
        "",
        "| id | type | title | linked |",
        "|----|------|-------|--------|",
    ]
    for s in switches:
        lines.append(
            f"| {s['id']} | `{s['type']}` | {(s['title'] or '—').replace('|','/')} | {', '.join(s['linked_inputs'] or []) or '—'} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 6. 모델·CLIP (필수)",
        "",
        "| | 값 |",
        "|--|-----|",
        f"| UNET | `{policy['default_unet']}` (alt: `Krea2Turbo\\\\krea2_turbo_int8_convrot.safetensors`) |",
        f"| CLIP | `{policy['default_clip']}` **type=krea2** |",
        f"| VAE | `{policy['default_vae']}` |",
        "",
        "Lonecat/Z-Image 프리셋과 **섞지 말 것.**",
        "",
        "---",
        "",
        "## 7. 에이전트 규칙",
        "",
    ]
    for r in policy["selection_rules"]:
        lines.append(f"1. {r}" if False else f"- {r}")
    lines += [
        "",
        f"*Generated from {UI.name} by _build_krea2_capabilities.py*",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print("Wrote", OUT_JSON)
    print("Wrote", OUT_MD)
    print("bypassers", len(bypassers), "notes", len(notes), "features", len(features))


if __name__ == "__main__":
    main()
