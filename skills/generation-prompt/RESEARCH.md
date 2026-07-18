# generation-prompt research

- **v1:** 2026-07-16 — general still/motion craft  
- **v1.1:** 2026-07-17 — Krea2 dialect  
- **v1.2:** 2026-07-17 — full factory model matrix (tool_catalog CLIs)

**Scope:** Prompt dialects for agent_custom Comfy stack. Not every SaaS model.

---

## 1. Principles (all versions)

1. Structure > fluff poetry  
2. Front-load what the model weights  
3. I2V ≠ second T2I  
4. Banned fluff on photoreal paths  
5. Quality gates block generate  
6. **Per-model dialect** (v1.2) — one skill, many templates  

---

## 2. Factory inventory mapped (2026-07-17)

From `docs/tool_catalog.md`, `scripts/generate_*.py`, `workflows/agent/presets`:

| Family | CLI examples | Dialect file |
|--------|--------------|--------------|
| Krea2 | generate_krea, generate_krea_nsfw | krea2_still_prompts.md |
| Z-Image / Lonecat | generate_moody* | moody_zimage.md |
| Illustrious XL | generate_illustrious_standard | illustrious_tags.md |
| Qwen Edit | generate_qwen_edit / inpaint / angle | qwen_edit.md |
| Ideogram4 / Boogu | generate_ideogram4, generate_boogu_typo | ideogram4_typography.md |
| LTX 2.3 | generate_i2v, flf2v, s2v, v2v, latentheart, redmix | ltx23_video.md |
| Wan 2.2 | generate_yaw_wan22, wan I2V | wan22_i2v.md |
| Shared motion | — | motion_video_prompts.md |
| Routing | — | model_prompt_matrix.md |

---

## 3. Source notes by family

### 3.1 Krea2

- Official prompting.md: natural language, long detailed best  
- expansion.txt: faithfulness, one paragraph  
- fal guide: materials, camera, Large≈photoreal  
- Reddit: specificity, ~512 token caution, turbo+raw experiments  
→ Skill: krea2_still_prompts.md  

### 3.2 Z-Image Turbo (Moody)

- HF Tongyi PROMPTING: long detailed; LLM enhance; token max caution  
- Community: Turbo often **ignores negatives**  
- Comfy docs: photoreal + optional PE  
→ Skill: moody_zimage.md + still_image_prompts.md  

### 3.3 Wan 2.2

- InstaSD / wan27 / VEED / Segmind: Subject→Motion→Camera→Scene  
- Camera language first-class; one move; continuous modifiers  
- I2V: animate visible elements only  
→ Skill: wan22_i2v.md  

### 3.4 LTX 2.3

- Comfy LTX-2.3: actions over time, visual details, audio  
- Official I2V: image owns look; prompt = what next  
- Prompt Relay: multi-event timed segments  
→ Skill: ltx23_video.md  

### 3.5 Qwen Image Edit

- Reddit playbook: imperative; keep everything else; chain edits  
- Text edits: preserve font/perspective  
- Multi-ref: declare image roles  
→ Skill: qwen_edit.md  

### 3.6 Illustrious / NoobAI

- Civitai / HF: Danbooru tags; masterpiece/best quality expected  
- Composition: upper body / cowboy shot / full body — don’t conflict  
- NL only lightly on Illustrious 2.0+  
→ Skill: illustrious_tags.md (exception to global quality-tag ban)  

### 3.7 Ideogram 4

- Official JSON captions; type text vs obj  
- bbox 0–1000 yx order  
- Factory lib/ideogram4_prompt.py encodes schema  
→ Skill: ideogram4_typography.md  

---

## 4. Cross-model failure modes (observed + research)

| Failure | Cause | Fix in skill |
|---------|-------|--------------|
| Dual person / poster faces | Wrong still dialect / NO-spam | Krea positive locks |
| I2V identity melt + freeze | Still essay / no continuous | motion gates |
| Edit drift | Mega multi-change Qwen | one-change + chain |
| Bad on-image spelling | Free prose typography | Ideogram text elements |
| Anime tags on photoreal | Dialect contamination | matrix + banned §6 |
| Empty quality soup | Fluff only | banned_and_weak |

---

## 5. Out of scope

- Midjourney flag encyclopedia  
- Audio-only BGM prompts (ACE-Step — separate doc)  
- Training LoRAs  
- Non-factory SaaS APIs beyond Grok hybrid notes  

---

## 6. Maintenance

When adding a new `generate_*` CLI:

1. Add row to `model_prompt_matrix.md`  
2. Add or extend a references/*.md dialect  
3. Bump SKILL version + RESEARCH date  
4. Sync to `.grok/skills/generation-prompt` and consumer project copies if used  
