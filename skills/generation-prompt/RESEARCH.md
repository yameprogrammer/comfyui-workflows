# generation-prompt research

- **Date**: 2026-07-16  
- **Scope:** Image + video prompt craft for agent_custom (not every SaaS model dialect)

---

## 1. Sources synthesized

| Source type | Takeaway |
|-------------|----------|
| Image prompt guides (LetsEnhance, Meta AI, Cliprise, Runway image) | Subject + action + setting + light + camera/style; specificity beats fluff |
| Structured “layers” templates (subject→action→env→light→camera) | Matches factory Rule 7.5 order |
| Video: Runway Gen-4 I2V guidance | Image defines scene; text defines **motion** |
| Kling / creator camera-motion guides | Plain-language camera moves; one motivated move; body physics |
| smixs/visual-skills style skills | Ban cinematic/masterpiece; force concrete details; thin SKILL + references |
| Factory `generation_prompt_craft.md` | Moody order, denoise table, insert face ban, I2V motion-only |
| video-direction v1.11 fields | Map SHOT columns → clauses |

---

## 2. Principles locked into skill

1. **Structure > poetry.**  
2. **Front-load subject/action** (models weight early tokens).  
3. **I2V ≠ second T2I.**  
4. **Banned fluff list** is mandatory.  
5. **Quality gates** block generate.  
6. **Factory-first** (Moody/Wan/IT); generic SaaS tips adapted not copy-pasted.

---

## 3. Out of scope v1

- Midjourney `--v` flag encyclopedia  
- LLM system prompts for chat  
- Audio/music gen prompts (separate later)  
