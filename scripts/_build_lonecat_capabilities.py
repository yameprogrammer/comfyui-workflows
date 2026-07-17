"""Build agent-facing Lonecat AIO capability map from UI workflow JSON."""
from __future__ import annotations

import json
from pathlib import Path

UI = Path(
    r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows"
    r"\Lonecat's AIO Z-Image ver 17.json"
)
OUT_JSON = Path(
    r"F:\ComfyUI_workflows\agent_custom\workflows\human"
    r"\Lonecat_AIO_Z-Image_ver17_CAPABILITIES.json"
)
OUT_MD = Path(
    r"F:\ComfyUI_workflows\agent_custom\workflows\human"
    r"\Lonecat_AIO_Z-Image_ver17_AGENT_GUIDE.md"
)
OUT_PRESETS = Path(
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


def main() -> None:
    ui = json.loads(UI.read_text(encoding="utf-8"))
    nodes = ui["nodes"]
    groups = ui.get("groups") or []
    links = ui.get("links") or []

    ginfo = []
    for gi, g in enumerate(groups):
        if not isinstance(g, dict):
            continue
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
            if mt and mt in title:
                matched.append(
                    {
                        "title": title,
                        "color": g["color"],
                        "member_count": g["member_count"],
                        "key_types": g["types"][:20],
                    }
                )
        bypassers.append(
            {
                "id": n["id"],
                "type": t,
                "title": n.get("title") or "",
                "matchTitle": mt,
                "matchColors": props.get("matchColors") or "",
                "toggleRestriction": props.get("toggleRestriction") or "default",
                "matched_groups": matched,
            }
        )

    switches = []
    for n in nodes:
        t = n.get("type") or ""
        title = n.get("title") or ""
        if "Switch" not in t and "switch" not in title and t != "BooleanSwitchNode":
            continue
        linked = []
        for inp in n.get("inputs") or []:
            if inp.get("link") is not None:
                linked.append(inp.get("name"))
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

    loaders = []
    for n in nodes:
        t = n.get("type") or ""
        if "Loader" not in t and t not in (
            "UNETLoader",
            "UnetLoaderGGUF",
            "CLIPLoader",
            "ClipLoaderGGUF",
            "VAELoader",
        ):
            continue
        loaders.append(
            {
                "id": n["id"],
                "type": t,
                "title": n.get("title"),
                "mode": n.get("mode"),
                "widgets": n.get("widgets_values"),
            }
        )

    # Feature catalog for agents (curated from matchTitle + groups)
    features = [
        {
            "feature_id": "model_diffusion",
            "name": "Diffusion UNET (safetensors ZIT/Moody)",
            "category": "model",
            "bypasser_id": 1329,
            "bypasser_title": "Model selector",
            "matchTitle": "Model",
            "restriction": "always one",
            "select": "Enable group whose title contains Diffusion Model; disable GGUF Model & Checkpoint Model",
            "groups_on": ["Diffusion Model"],
            "groups_off": ["GGUF Model", "Checkpoint Model"],
            "api_loader": {"node_role": "unet", "class_type": "UNETLoader", "ui_id": 1323},
            "model_switch_slot": "any_01",
            "clip_switch_slot": "any_01",
            "agent_preset": "lonecat_t2i_turbo",
            "when_to_use": "Default high-quality Z-Image Turbo / Moody mixes (.safetensors)",
        },
        {
            "feature_id": "model_gguf",
            "name": "GGUF UNET (low VRAM)",
            "category": "model",
            "bypasser_id": 1329,
            "bypasser_title": "Model selector",
            "matchTitle": "Model",
            "restriction": "always one",
            "select": "Enable GGUF Model group only",
            "groups_on": ["GGUF Model"],
            "groups_off": ["Diffusion Model", "Checkpoint Model"],
            "api_loader": {
                "node_role": "unet",
                "class_type": "UnetLoaderGGUF",
                "ui_id": 1678,
            },
            "paired_clip": {
                "class_type": "ClipLoaderGGUF",
                "ui_id": 1670,
                "note": "UI pairs ClipLoaderGGUF; some GGUF unets also work with CLIPLoader qwen_3_4b lumina2",
            },
            "model_switch_slot": "any_02",
            "clip_switch_slot": "any_02",
            "agent_preset": "lonecat_t2i_gguf",
            "when_to_use": "VRAM tight; Q4 GGUF e.g. ZImageTurbo\\\\z-image-turbo-Q4_K_M.gguf",
            "caveats": [
                "ModelSamplingAuraFlow may break some GGUF weights (unpack error) — GGUF preset skips AuraFlow",
                "UI default GGUF filename may differ from files on disk",
            ],
        },
        {
            "feature_id": "model_checkpoint",
            "name": "Checkpoint (merged AIO ckpt)",
            "category": "model",
            "bypasser_id": 1329,
            "bypasser_title": "Model selector",
            "matchTitle": "Model",
            "restriction": "always one",
            "select": "Enable Checkpoint Model group only",
            "groups_on": ["Checkpoint Model"],
            "groups_off": ["Diffusion Model", "GGUF Model"],
            "api_loader": {
                "node_role": "checkpoint",
                "class_type": "Checkpoint Loader with Name (Image Saver)",
                "ui_id": 1561,
            },
            "model_switch_slot": "any_03",
            "clip_switch_slot": "any_03",
            "agent_preset": None,
            "when_to_use": "Merged checkpoint workflows; ensure ckpt path exists",
            "status": "preset_pending",
        },
        {
            "feature_id": "prompt_qwen_enhancer",
            "name": "Qwen VL prompt enhancer",
            "category": "prompt",
            "bypasser_id": 1867,
            "matchTitle": "Prompt",
            "select": "Turn ON groups matching Prompt (Qwen Prompt Enhancer, Img Prompt)",
            "groups_on": ["#   Qwen Prompt Enhancer", "#     📝 Img Prompt"],
            "agent_preset": None,
            "when_to_use": "Expand short prompts; needs llama_cpp + GGUF VL weights",
            "default_for_smoke": "OFF",
            "status": "optional_heavy",
        },
        {
            "feature_id": "load_image_i2i",
            "name": "Load image + I2I",
            "category": "i2i",
            "bypasser_id": 2028,
            "matchTitle": "!",
            "select": "Enable groups with ! (Load Image, I2I, Remove Background, …)",
            "groups_on": [
                "#      🖼️Load Image!",
                "#     I2I 🖼️!",
                "#      Remove Background!",
            ],
            "related_switch": {
                "id": 1800,
                "title": "Latent Switch",
                "t2i": "EmptyLatent (any_02)",
                "i2i": "VAEEncode of loaded image (any_01)",
            },
            "agent_preset": None,
            "when_to_use": "Image-to-image keyframes / identity",
            "status": "phase1_target",
        },
        {
            "feature_id": "controlnet",
            "name": "ControlNet",
            "category": "control",
            "bypasser_id": 2034,
            "matchTitle": "🥅",
            "groups_on": ["#   🥅Controlnet"],
            "when_to_use": "Pose/structure lock from reference image",
            "status": "phase2_target",
        },
        {
            "feature_id": "inpaint",
            "name": "Inpaint (Klein)",
            "category": "edit",
            "bypasser_id": 1866,
            "matchTitle": "Klein Inpaint",
            "groups_on": ["# Klein Inpaint 🖌️", "Inpaint"],
            "related": {"bypasser_id": 2031, "title": "Picture or Mask?", "matchTitle": "'"},
            "when_to_use": "Local edit with mask",
            "status": "phase2_target",
        },
        {
            "feature_id": "detailers",
            "name": "Face/Eyes/Hands detailers",
            "category": "refine",
            "bypasser_id": 2094,
            "matchTitle": "::",
            "groups_on": [
                "🔎 Detailers",
                "# ::Face 🙂",
                "# ::Eyes 👀",
                "# ::Hands ✋",
                "# ::Spare 🛞",
            ],
            "when_to_use": "After base gen, refine anatomy",
            "status": "phase1_optional",
        },
        {
            "feature_id": "hires_upscale",
            "name": "Hi-res / Ultimate SD upscale",
            "category": "upscale",
            "bypasser_id": 2046,
            "matchTitle": "Hi Rez Fix/ Upscale",
            "groups_on": ["#  Hi Rez Fix/ Upscale", "Hi Rez fix & Upscale"],
            "when_to_use": "2x quality upscale after still",
            "status": "phase2_target",
        },
        {
            "feature_id": "seed_vr2",
            "name": "SeedVR2 upscale",
            "category": "upscale",
            "bypasser_id": 1863,
            "matchTitle": "#  Seed",
            "groups_on": ["#   Seed Variance", "#  Seed VR2 Upscale", "Seed VR2 (ver 6.0 math node update)"],
            "when_to_use": "Heavy 4K upscale; high VRAM/time",
            "status": "phase2_target",
        },
        {
            "feature_id": "post_optical_crop",
            "name": "Post: Optical Realism + Crop",
            "category": "post",
            "bypasser_id": 1872,
            "matchTitle": "📷",
            "groups_on": ["Optical Realism 📷", "✂️Crop 📷"],
            "related_switches": ["Optical Real switch", "crop bypass Switch", "Color match bypass switch"],
            "when_to_use": "Grade / crop polish",
            "status": "optional",
        },
        {
            "feature_id": "save_meta",
            "name": "Save with metadata / folders",
            "category": "io",
            "bypasser_id": 1708,
            "bypasser_title": "Meta 📂📅+",
            "groups_on": ["💾 Save Group", "#Save w/Metadata🗒️", "#Create Subfolder📂", "#Save Draft 📐"],
            "when_to_use": "Organized delivery outputs",
            "status": "optional",
        },
        {
            "feature_id": "llm_instruct",
            "name": "LLM system instruct presets",
            "category": "prompt",
            "bypasser_id": 2100,
            "bypasser_title": "LLM Prompt Instructions",
            "groups_on": ["Instruct (Beta)"],
            "when_to_use": "With Qwen enhancer — Realistic/Photographic/NSFW system prompts",
            "default_for_smoke": "OFF",
            "status": "optional_heavy",
        },
        {
            "feature_id": "hash_options_master",
            "name": "Master toggle for # option groups",
            "category": "meta",
            "bypasser_id": 1318,
            "bypasser_title": "Bypasser",
            "matchTitle": "#",
            "when_to_use": "Bulk enable/disable many optional # groups — use carefully",
            "status": "advanced",
        },
    ]

    # Agent selection policy
    policy = {
        "default_still_t2i": "lonecat_t2i_turbo",
        "default_still_t2i_low_vram": "lonecat_t2i_gguf",
        "default_still_i2i": "lonecat_i2i_identity",  # phase1
        "selection_rules": [
            "Prefer catalog agent_preset over raw UI when available",
            "Never convert_ui_to_api full AIO; use exported .api.json presets",
            "Model family: safetensors ZIT/Moody → model_diffusion; .gguf unet → model_gguf",
            "Krea2-named mixes need krea2 CLIP — not ZIT presets",
            "Smoke/batch: Qwen enhancer OFF, SeedVR2 OFF unless requested",
            "I2I: load_image_i2i ON + Latent Switch encode + denoise 0.4-0.65",
            "T2I: load_image_i2i OFF + EmptyLatent + denoise 1.0",
            "One Model selector path only (always one)",
        ],
        "port_patch_only": True,
        "workflow_ui": str(UI),
        "docs": {
            "usage": "workflows/human/Lonecat_AIO_Z-Image_ver17_USAGE.md",
            "agent_guide": "workflows/human/Lonecat_AIO_Z-Image_ver17_AGENT_GUIDE.md",
            "capabilities_json": "workflows/human/Lonecat_AIO_Z-Image_ver17_CAPABILITIES.json",
            "feature_presets": "workflows/agent/presets/lonecat_feature_presets.json",
        },
    }

    capabilities = {
        "workflow": "Lonecat's AIO Z-Image ver 17",
        "version": 1,
        "features": features,
        "agent_policy": policy,
        "bypassers": bypassers,
        "switches": switches,
        "groups_summary": [
            {
                "title": g["title"],
                "color": g["color"],
                "member_count": g["member_count"],
                "types": g["types"][:25],
            }
            for g in ginfo
        ],
        "loaders": loaders,
        "model_switch": {
            "id": 1330,
            "title": "Model switch",
            "slots": {
                "any_01": "UNETLoader (Diffusion)",
                "any_02": "UnetLoaderGGUF (GGUF)",
                "any_03": "Checkpoint Loader",
            },
        },
        "clip_switch": {
            "id": 1331,
            "title": "Clip switch",
            "slots": {
                "any_01": "CLIPLoader",
                "any_02": "ClipLoaderGGUF",
                "any_03": "Checkpoint CLIP",
            },
        },
        "latent_switch": {
            "id": 1800,
            "title": "Latent Switch",
            "slots": {"any_01": "VAEEncode I2I", "any_02": "EmptyLatent T2I"},
        },
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(capabilities, ensure_ascii=False, indent=2), encoding="utf-8")

    feature_presets = {
        "version": 1,
        "description": "Agent selects feature_id or agent_preset; runner loads matching .api.json",
        "presets": {
            "lonecat_t2i_turbo": {
                "feature_ids": ["model_diffusion"],
                "file": "presets/lonecat_t2i_turbo.api.json",
                "ports": "presets/lonecat_t2i_turbo.ports.json",
                "status": "ready",
            },
            "lonecat_t2i_gguf": {
                "feature_ids": ["model_gguf"],
                "file": "presets/lonecat_t2i_gguf.api.json",
                "ports": "presets/lonecat_t2i_gguf.ports.json",
                "status": "ready",
                "notes": "AuraFlow bypassed for Q4 GGUF stability",
            },
            "lonecat_i2i_identity": {
                "feature_ids": ["model_diffusion", "load_image_i2i"],
                "file": "presets/lonecat_i2i_identity.api.json",
                "ports": "presets/lonecat_i2i_identity.ports.json",
                "status": "planned_phase1",
            },
            "lonecat_i2i_detailer": {
                "feature_ids": ["model_diffusion", "load_image_i2i", "detailers"],
                "status": "planned_phase1",
            },
            "lonecat_t2i_detailer_upscale": {
                "feature_ids": ["model_diffusion", "detailers", "hires_upscale"],
                "status": "planned",
            },
            "lonecat_controlnet": {
                "feature_ids": ["model_diffusion", "load_image_i2i", "controlnet"],
                "status": "planned",
            },
            "lonecat_inpaint": {
                "feature_ids": ["model_diffusion", "inpaint"],
                "status": "planned",
            },
        },
        "select_preset": {
            "t2i_default": "lonecat_t2i_turbo",
            "t2i_low_vram": "lonecat_t2i_gguf",
            "i2i_default": "lonecat_i2i_identity",
            "by_extension": {
                ".safetensors": "lonecat_t2i_turbo",
                ".gguf": "lonecat_t2i_gguf",
            },
        },
    }
    OUT_PRESETS.parent.mkdir(parents=True, exist_ok=True)
    OUT_PRESETS.write_text(
        json.dumps(feature_presets, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Markdown agent guide
    lines = [
        "# Lonecat AIO Z-Image ver 17 — Agent 선택 가이드",
        "",
        "에이전트는 **UI에서 스위치를 클릭하지 않는다.**",
        "대신 **feature_id / agent_preset** 을 고르고, 준비된 `*.api.json` 을",
        "`run_workflow_api` / `workflow_api_runner` 로 호출한다.",
        "",
        "기계 가독 SSOT:",
        f"- `{OUT_JSON.as_posix()}`",
        f"- `{OUT_PRESETS.as_posix()}`",
        "- 사람용 상세: `Lonecat_AIO_Z-Image_ver17_USAGE.md`",
        "",
        "---",
        "",
        "## 1. 선택 흐름 (에이전트)",
        "",
        "```text",
        "1) 작업 종류 판별: T2I | I2I | edit | upscale | controlnet | inpaint",
        "2) 모델 파일 확장자: .safetensors → model_diffusion | .gguf → model_gguf",
        "3) feature_presets.json → agent_preset 이름",
        "4) run_workflow_api -p <preset> --positive ... [--port unet_name=...]",
        "```",
        "",
        "### 기본 프리셋",
        "",
        "| 상황 | preset |",
        "|------|--------|",
        "| 일반 T2I (권장) | `lonecat_t2i_turbo` |",
        "| 저VRAM / GGUF | `lonecat_t2i_gguf` |",
        "| I2I 아이덴티티 (예정) | `lonecat_i2i_identity` |",
        "",
        "---",
        "",
        "## 2. Bypasser = 기능 스위치 (UI 분석)",
        "",
        "rgthree **Fast Groups Bypasser** 는 `matchTitle` 문자열이 **그룹 제목에 포함**되면 그 그룹을 통째로 on/off 한다.",
        "",
        "| id | UI 제목 | matchTitle | restriction | 켜면 (매칭 그룹) | feature_id |",
        "|----|---------|------------|-------------|------------------|------------|",
    ]
    feat_by_bp = {f.get("bypasser_id"): f for f in features if f.get("bypasser_id")}
    for b in sorted(bypassers, key=lambda x: x["id"]):
        fid = ""
        for f in features:
            if f.get("bypasser_id") == b["id"]:
                fid = f["feature_id"]
                break
        groups = ", ".join(g["title"][:40] for g in b["matched_groups"][:6]) or "—"
        title = (b["title"] or "—").replace("|", "/")
        lines.append(
            f"| {b['id']} | {title} | `{b['matchTitle']}` | {b['toggleRestriction']} | {groups} | `{fid}` |"
        )

    lines += [
        "",
        "### Model selector (id 1329) — always one",
        "",
        "```text",
        "Diffusion Model  → UNETLoader      → Model switch any_01",
        "GGUF Model       → UnetLoaderGGUF  → Model switch any_02  (+ ClipLoaderGGUF → Clip switch any_02)",
        "Checkpoint Model → Checkpoint      → Model switch any_03",
        "```",
        "",
        "**에이전트:** 파일 확장자로 diffusion vs gguf 프리셋을 고른다. 한 요청에 두 모델 경로를 섞지 않는다.",
        "",
        "### Latent Switch (id 1800)",
        "",
        "| 모드 | 슬롯 | denoise |",
        "|------|------|---------|",
        "| T2I | EmptyLatent | 1.0 |",
        "| I2I | VAEEncode(LoadImage) | 0.4–0.65 |",
        "",
        "---",
        "",
        "## 3. Feature 목록 (에이전트 체크리스트)",
        "",
    ]
    for f in features:
        lines.append(f"### `{f['feature_id']}` — {f['name']}")
        lines.append("")
        lines.append(f"- **category:** {f.get('category')}")
        lines.append(f"- **when:** {f.get('when_to_use')}")
        lines.append(f"- **preset:** `{f.get('agent_preset')}`")
        lines.append(f"- **status:** {f.get('status', 'documented')}")
        if f.get("select"):
            lines.append(f"- **UI select:** {f['select']}")
        if f.get("caveats"):
            for c in f["caveats"]:
                lines.append(f"- ⚠️ {c}")
        lines.append("")

    lines += [
        "---",
        "",
        "## 4. 에이전트 의사결정 트리",
        "",
        "```text",
        "요청이 still 이미지인가?",
        "  NO → video 프리셋(별도) / 범위 외",
        "  YES ↓",
        "입력 이미지 있는가?",
        "  NO  → T2I",
        "        unet이 .gguf? → lonecat_t2i_gguf",
        "        else          → lonecat_t2i_turbo",
        "        (+ detailer/upscale 요청 시 해당 프리셋 또는 후처리 프리셋)",
        "  YES → I2I",
        "        → lonecat_i2i_identity (준비되면)",
        "        denoise 0.4~0.65, ports.input_image=경로",
        "부분 수정/마스크? → inpaint 프리셋",
        "포즈 고정? → controlnet 프리셋",
        "프롬프트 자동 확장? → qwen enhancer (무거움, 기본 OFF)",
        "```",
        "",
        "---",
        "",
        "## 5. 구현 규칙 (강제)",
        "",
        "1. **port patch only** — API JSON 노드 id/키는 `*.ports.json` SSOT.",
        "2. **기능 추가** = UI에서 바이패서 조합 고정 → `graphToPrompt` → `presets/<name>.api.json` + ports + feature_presets 등록.",
        "3. **금지:** full AIO에 convert_ui_to_api, IPAdapter 런타임 inject, 바이패서를 코드로 흉내 내기.",
        "4. 생성 메타에 `workflow_api`, `feature_ids`, `preset` 기록.",
        "5. 불명확하면 USAGE.md + CAPABILITIES.json 의 features[] 를 읽고 preset status=ready 인 것만 사용.",
        "",
        "---",
        "",
        f"*Generated from {UI.name} by _build_lonecat_capabilities.py*",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print("Wrote", OUT_JSON)
    print("Wrote", OUT_MD)
    print("Wrote", OUT_PRESETS)
    print("features", len(features), "bypassers", len(bypassers), "switches", len(switches))


if __name__ == "__main__":
    main()
