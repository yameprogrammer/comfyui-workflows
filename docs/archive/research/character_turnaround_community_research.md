> **ARCHIVED (2026-07-14)** — 운영 SSOT 아님. 인덱스: [../../README.md](../../README.md). 활성 백로그: [../../agent_video_tooling_todo.md](../../agent_video_tooling_todo.md).

# Character Sheet Turn (Head / Body) — Community Research Notes

- **Date**: 2026-07-12  
- **Purpose**: Fix our turn results that feel like “pretty portraits at random angles” rather than **production model-sheet turns**.

---

## 1. What “character sheet turn” means (industry + AI community)

| Trait | Model-sheet turn (expected) | What we often got |
|-------|----------------------------|-------------------|
| Camera | **Orthographic / flat** technical view | Beauty portrait camera |
| Pose | Neutral **A-pose / relaxed stand**, same pose every angle | Variable fashion posing |
| Layout | Front → 3/4 → side → back as a **set** | Isolated one-offs |
| Background | Plain white/grey, **flat even lighting** | OK (we already do) |
| Goal of image | Evaluate **silhouette, proportions, costume construction** | Pretty face only |
| Consistency language | “same character / consistent … across all views” | Weak or missing |
| Structure guide | **OpenPose / multi-view template** (preprocessor often **None**) | Front I2I attractor fights text |

Classic views: **front, three-quarter, side profile, back** (sometimes 8-point).

---

## 2. What the community actually does (sources)

### A. Multi-view OpenPose template (Reddit r/StableDiffusion classic)
- One **wide image** with several OpenPose skeletons (front | side | back …).  
- ControlNet: **OpenPose model**, preprocessor **None** (map already drawn).  
- Prompt tags: `character turnaround`, `multiple views`, `reference sheet`, `simple background`, `1girl` / `solo`.  
- Aspect ~**2:1** (e.g. 1024×512).  
- Hard part is **detail consistency** without LoRA/inpaint — keywords help a little.

### B. Prompt-as-document (Kalon / Nano / “design sheet” prompts)
- Name the document: `character design reference sheet`, `character design turnaround sheet`.  
- **Layout as instruction**: “arranged left to right — front, three-quarter, side profile”.  
- Repeat consistency: face / hair / outfit / proportions **each**.  
- Pose: “neutral relaxed standing” or **A-pose / T-pose**.  
- Lighting: **flat even**, no dramatic shadows.  
- Negative sheet-specific: merged views, different face between views, scenic BG, single view only.

Example skeleton (adapted):

```text
character design turnaround sheet, white background,
same character shown in full-body standing views,
front view, three-quarter view, side profile, back view,
orthographic camera, A-pose or relaxed stand,
consistent facial features, consistent proportions, consistent outfit,
flat even studio lighting, clean spacing, professional concept art reference
```

### C. ComfyUI multi-view workflows (YouTube / Flux Kontext turnaround LoRA)
- Dedicated **turnaround LoRA** or multi-view pipeline from **one** input.  
- Or generate **9 views** with category breakdown (full body / close-up / half).  
- Identity often needs **LoRA / IP-Adapter / Kontext** — pure front I2I is known-weak for rotation.

### D. Z-Image Turbo + ControlNet Union
- Pose / DWPose / Depth preprocessors recommended for structure.  
- Pose map → CN (not Canny of sticks).  
- Community: CN good for **new poses**; identity still needs strong prompt/LoRA/ref.

### E. Traditional art turnaround (non-AI)
- Front → 3/4 → side → back; **same stance**; evaluate silhouette; often align head heights across panels.

---

## 3. Gap analysis (our agent_custom pipeline)

| Our approach | Community | Gap |
|--------------|-----------|-----|
| One image per angle, separate jobs | Often **one multi-view sheet** or LoRA turnaround | Missing “sheet document” framing |
| Head turn = front face **I2I** + text | OpenPose / 3D-driven openpose / multi-view | Front latent kills rotation |
| Body turn = I2I fullbody + weak OpenPose or empty-latent | OpenPose template + T2I/empty + **clothed A-pose** language | Empty latent → nude; I2I → front stickiness |
| Prompt: “STRICT SIDE PROFILE…” only | + **orthographic, turnaround sheet, A-pose, consistent** | Missing production vocabulary |
| Negatives often meta-only on Moody | Community relies on **layout + CN** more than neg | Negatives weak on ZIT |

**Conclusion:** Not “a bit more denoise” — we need **model-sheet language + multi-view OpenPose structure + avoid front-I2I for hard angles + force clothed A-pose**.

---

## 4. Reflection plan (implement)

1. **Prompt pack** for head/body turns (orthographic, A-pose, design sheet).  
2. **Multi-view OpenPose strips** (body + head) for “sheet feel” generation.  
3. **Per-view export**: generate multi-view sheet → crop panels into `refs/`.  
4. Hard angles: **empty latent + OpenPose strip/panel** with **wardrobe locked** in prompt.  
5. Keep expressions as separate I2I (community also separates expression charts).

---

## 5. Prompt pack (to use in presets)

### Body turn (per panel or multi-view)
```text
character design turnaround sheet, orthographic camera, model sheet,
full body, neutral A-pose or relaxed standing, arms slightly away from body,
flat even studio lighting, plain light gray background,
{view}: front | three-quarter | side profile | back view,
fully clothed {wardrobe}, consistent proportions,
professional animation/game character reference, clean silhouette
```

### Head turn
```text
character head turnaround reference, orthographic head-and-shoulders,
same haircut and face structure, flat even lighting, plain background,
{view}: front face | three-quarter face | strict side profile | back of head only,
no beauty portrait posing, technical model sheet head rotation
```

---

## 6. References (search session 2026-07-12)

- Reddit: OpenPose character turnaround templates (preprocessor None, multi-view strip)  
- Kalon: AI character sheet prompts (layout + consistency tags)  
- Z-Image ControlNet Union: Pose/DWPose as control  
- Flux Kontext / multi-view Comfy tutorials: dedicated turnaround tooling + single-ref identity  
- Traditional: front / 3/4 / side / back same stance

