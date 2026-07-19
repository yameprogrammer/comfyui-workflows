# Character consistency research → factory mapping

**Date:** 2026-07-18  
**Purpose:** Distill public ComfyUI / Stable Diffusion practices into an agent-callable tool (`generate_character_consistent`).  
**Not** a copy of any single paid workflow JSON; a **policy + orchestration** layer on top of our validated backends.

---

## 1. Sources (web + YouTube ecosystem)

| Source | What it teaches | Use in factory |
|--------|-----------------|----------------|
| [Mickmumpitz — Consistent characters from input image (Flux/ComfyUI)](https://www.youtube.com/watch?v=Uls_jXy9RuU) | One reference → multi-angle / expression / environment sheet | `pack` + `angle` modes |
| [Mickmumpitz — Endless consistent characters](https://www.youtube.com/watch?v=grtmiWbmvv0) | Pose sheet + denoise/ControlNet strength tradeoffs; fixed seed on face refine | denoise ladder; fixed seed on identity pass |
| [ThinkDiffusion Flux character sheet guide](https://learn.thinkdiffusion.com/consistent-character-creation-with-flux-comfyui/) | Pose sheet → CN → upscale → **Face Detailer with fixed seed** | Documented; face refine optional later |
| [Stable Diffusion Art — consistent face methods](https://stable-diffusion-art.com/consistent-face/) | Celebrity mix, Reactor, Dreambooth, LoRA, **IP-Adapter Face / ControlNet** ladder | Identity ladder section |
| Community (Reddit / FB ComfyUI) | InstantID, Reactor, IPAdapter-FaceID still common; Flux pure text weak for ID | Prefer **image ref**; don’t rely on text alone |
| This repo Rule 7.5 / casting pipeline | I2I denoise 0.42–0.58 for face; change-only prompts; full sheet process | Default `lock` denoise caps |

---

## 2. Consensus techniques (ranked for agents)

### Tier A — always do (no extra models)

1. **One master reference** (front face or clear portrait). Never free-T2I every shot hoping text holds ID.
2. **I2I / img2img identity path** with **low denoise** when face must match (~0.40–0.55).
3. **Change-only prompts** on I2I: pose, wardrobe, lighting, location — not a full re-description of the face.
4. **Identity lock phrase** + negative “different person / face morph”.
5. **Fixed seed** when iterating small variants of the same composition.
6. **Character sheet**: multi-view + multi-expression SSOT before mass production (Mickmumpitz pattern).

### Tier B — structure without killing face

7. **ControlNet / pose sheet** for body pose; keep identity via ref + moderate denoise (community + ThinkDiffusion).
8. **Multi-angle instruction models** (our Qwen angle stack) instead of “side view” pure T2I.
9. **Two-pass refine**: base consistency → optional face detailer with **fixed** seed (ThinkDiffusion).

### Tier C — heavy / specialized (not default CLI)

10. **IP-Adapter FaceID / InstantID / PuLID** — strong face transfer; model/node heavy; this factory keeps IPA experimental.
11. **Character LoRA / Dreambooth** — best long-term identity; training pipeline separate from one-shot tools.
12. **Reactor / face swap** — last-mile face paste; can look plastic; use sparingly.

---

## 3. Denoise ladder (photoreal Z-Image / Lonecat I2I)

| Goal | Denoise | Mode |
|------|---------|------|
| Micro edit (expression, light) | 0.38–0.48 | `lock` soft |
| **Default identity scene** | **0.48–0.55** | `lock` |
| Wardrobe / medium scene | 0.55–0.62 | `remix` |
| Hard pose/env change (ID risk) | 0.62–0.72 | `remix` + accept risk or use `pose`/`angle` |
| Pure new face (no ref) | 1.0 T2I | `anchor` only |

Community pattern: **higher denoise needs stronger ID conditioning** (IPA / lock phrase / lower face crop denoise). Our default stack uses **Lonecat I2I identity + lock phrase** without SD1.5 IPA inject.

---

## 4. Factory mapping (what the tool actually runs)

| Research step | Our backend |
|---------------|-------------|
| Master face / anchor | `generate_moody` (`lonecat_t2i_turbo`) |
| Same person, new action/scene | `generate_moody_i2i_lock` → `lonecat_i2i_identity` |
| Stronger scene change | same path, higher denoise cap (`remix`) |
| Multi-view sheet | `generate_qwen_angle` |
| Pose from stick/photo | `generate_moody_controlnet` + identity-aware prompt |
| Mini expression/wardrobe pack | repeated `lock` with preset instructions + contact sheet |
| Full character pipeline A→B→C | still `character_cast_pool` / `character_full_sheet` (package SSOT) |

**This tool is for ad-hoc “keep this face while generating images”.**  
Long-form cast packages remain under `characters/` + casting docs.

---

## 5. Hard bans (from research + our failure notes)

| Ban | Why |
|-----|-----|
| New T2I every shot with only adjectives | Face drifts every seed |
| Tag-soup + re-essay full face on I2I | Model fights the latent identity |
| Denoise ≥ 0.75 on face without angle/CN/IPA | Identity lottery |
| Mass-approve without opening files | Factory QA rule |
| Treating Reactor as only consistency | Uncanny / lighting mismatch |

---

## 6. Recommended agent flow

```text
[optional] anchor  →  approve master face
      ↓
lock / remix  for each story still  (ref = master)
      ↓
angle or pose when framing must change strongly
      ↓
pack when you need a quick expression/wardrobe board
      ↓
(optional) promote into characters/<id>/ for episode reuse
```

CLI: `python scripts/generate_character_consistent.py --help`  
Guide: [workflows/human/character_consistency/AGENT_GUIDE.md](../workflows/human/character_consistency/AGENT_GUIDE.md)
