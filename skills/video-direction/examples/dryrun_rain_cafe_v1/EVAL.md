# Dry-run evaluation — video-direction v1.6

**Episode example:** `dryrun_rain_cafe_v1`  
**Scope:** Gate 0–3 only (no Comfy generation)  
**Evaluator:** agent (self) + open for user review  

---

## 1. Did the skill “run”?

| Gate | Done? | Artifact |
|------|-------|----------|
| Equip | ✅ | Skill v1.6 identity + visual craft map used |
| 0 Intake + L0/L1/L2 | ✅ | Type B → M_hybrid + R01 + modules |
| 1 CREATIVE | ✅ | `CREATIVE.md` all sections + tests |
| 2 Beats | ✅ | B0–B8 in SHOT_DESIGN |
| 3 SHOT_DESIGN + 5 craft layers | ✅ | 9 shots fully fielded |
| 4–7 Factory | ⏭ | Intentionally not run |

**Verdict:** Skill **functions as a planning machine** for keyword → shippable shot bible.

---

## 2. Checklist (skill §9)

| Item | Pass |
|------|------|
| CREATIVE complete + concept tests | ✅ |
| SIZE RHYTHM line | ✅ |
| Motivated angle + one move + lens + intent | ✅ |
| Composition notes | ✅ |
| Lighting + look_id | ✅ |
| Blocking fits size/driver | ✅ |
| World lock + motifs staged | ✅ |
| Coverage A–D | ✅ |
| R1–R6 audit | ✅ |
| No freeze-pad plan | ✅ |

---

## 3. Quality judgment (honest)

### Strengths (skill forced good behavior)

1. **No face-CU wall** — insert + high LS + OTS + ECU prop broke R01 failure mode.  
2. **Motif pipeline** — cup/rain/chair have introduce/vary/payoff, not pitch-only.  
3. **Hybrid drivers** — si2v only on speak; i2v on world/prop (factory-aligned).  
4. **5-layer fields** — camera/comp/light/block/world each non-empty (visual craft map works).  
5. **Hook without dialogue** — S01 mute-readable.  
6. **Continuity bible** — key side, cup level, straw bend — would catch real pipeline bugs.

### Weaknesses / skill gaps observed in dry-run

| Gap | Severity | Note |
|-----|----------|------|
| **Dialogue is thin** | med | Skill asks performance grammar but not a mini-script template; agent freehanded 3 lines |
| **Format ID fuzzy** | low | “9:16 shorts” not exact `video_backends.json` format key — handoff could require SSOT id |
| **Guest invisible** | low | Empty-chair story works; if user wanted 2-hand cast, skill didn’t force second character_id |
| **Length vs IT frames** | med | 5.5–6s si2v ok-ish; skill mentions contract but dry-run didn’t compute frames |
| **No failure_note pre-search** | low | Rule 7.4 pre-gen search not simulated |
| **Prompt quality** | med | Only 3 sample prompts; full per-shot prompt pack not mandatory in Gate 3 |
| **Cannot prove generation quality** | — | Dry-run cannot test QA/freeze/identity gates |

### Skill friction

- Gate 3 table is **wide** (many columns) — good for quality, heavy for tiny 15s ads; skill might allow “thin mode” later.  
- Progressive disclosure worked: didn’t need full research files once maps internalized.

---

## 4. Scores (1–5)

| Dimension | Score | Comment |
|-----------|------:|---------|
| Trigger clarity | 5 | Keyword brief → skill path obvious |
| Gate discipline | 5 | Stopped before pixels |
| Recipe classification | 5 | R01+hybrid correct |
| Creative pack richness | 4 | Strong pitch/paradox; dialogue thin |
| Shot grammar / rhythm | 5 | R1–R6 clean |
| Camera layer | 4 | Solid; no dutch/orbit abuse |
| Composition layer | 4 | Vertical space used well |
| Lighting layer | 4 | Consistent key side |
| Blocking layer | 4 | Cup anchor + eyeline path |
| Production design | 5 | Motifs staged properly |
| Factory handoff readiness | 4 | Needs exact format_id + char verify |
| **Overall dry-run** | **4.4** | Ready for Gate 4 with minor handoff tighten |

---

## 5. Recommendation

| Next | Why |
|------|-----|
| User reads CREATIVE + SHOT_DESIGN | Human taste check |
| Optional: add `shots.json` sketch | Closer to factory |
| Optional: real `story_init` + 1 keyframe smoke | Tests handoff beyond words |
| Skill tweak candidates | Mini-dialogue template; require `format` enum from backends; optional Gate3 prompt appendix |

---

## 6. User review prompts

When you open the files, ask yourself:

1. Does S01 stop the scroll without a face?  
2. Is the paradox visible without dialogue?  
3. Would you cut any MCU as redundant?  
4. Is empty-chair story clear enough vs needing a second actor?  
5. Any shot that still feels “AI default pretty”?  

Reply with rejects → we revise SHOT_DESIGN (skill says iterate in words is cheap).
