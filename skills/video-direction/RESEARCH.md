# Research notes — video-direction skill v1

- **Date**: 2026-07-16  
- **Goal**: Build a high-performance *direction* skill (story + shot grammar + gates), not another generic “AI video prompt dump”.  
- **Method**: Survey public agent skills (GitHub), industry shot-list practice, community AI-filmmaking workflows; synthesize into factory-native skill.

---

## 1. High-signal public skills / systems reviewed

| Source | Why it scored high | What we took |
|--------|-------------------|--------------|
| [hoodini/ai-agents-skills **director**](https://github.com/hoodini/ai-agents-skills/blob/master/skills/director/SKILL.md) | Explicit **gated pipeline**; “no pixels before story locked”; Pixar 22 rules working set; want/need/wound/stakes; 13-thumbnail test; shot fields mandatory | **Hard gates** before compose; story spine tests; per-shot size/angle/move/light; progressive disclosure |
| [aicontentskills **ai-video-storyboard**](https://github.com/aicontentskills/ai-video-storyboard-skill) | Multi-shot >15s problem; **visual consistency layer** before per-shot prompts; platform cadences; concrete prompt anatomy | Visual Theme lock; ~5s AI-clip cadence; Hook/Build/Payoff; shared palette/lighting/lens |
| [BayramAnnakov **remotion-video-director**](https://github.com/BayramAnnakov/remotion-video-director) | Creative brief + expert panel + scene focus rule; interactive WAIT gates | One idea per beat; confirm brief before production; quality scorecard idea |
| [coreyhaines31 **marketingskills/video**](https://github.com/coreyhaines31/marketingskills/blob/main/skills/video/SKILL.md) | Tool routing matrix; prompt = subject+action+camera+style | Platform/tool choice table (adapted to **this factory**, not SaaS video APIs) |
| [rediumvex / Seedance cinematographer skills](https://github.com/rediumvex/ai-video-generator-claude) | Production-grade timed prompts, camera+light+sound | Timing + camera + light discipline in prompts (mapped to Moody/I2V craft) |
| StudioBinder shot-list practice | Industry SSOT for coverage, shot list fields, MV shot listing | Coverage ladder; shot list columns; chorus as visual event (via our master persona) |
| VirtualFilmStudio / VDS research (camera scripts) | Controllable camera scripts + propose–simulate | Camera script fields on every shot |
| Mira AI “AI filmmaking team” pattern | Role split: director (judgment) vs generator | Director skill ≠ generator CLI |

**Not copied:** marketing-only Hyperframes/Remotion product-demo stacks as our mainline (this factory is Comfy keyframe→I2V/SI2V). We **compose** their process wisdom with our production gates.

---

## 2. Failure modes research → skill rules

| Observed failure (community + our `failures/`) | Skill rule |
|-----------------------------------------------|------------|
| Generate before story/shot design | Gate 1–3 hard stop |
| Lyric slideshow / face CU spam | Anti-list + size rhythm R1–R6 |
| Inconsistent cast across shots | Identity sheet + approved refs |
| Freeze pad to fake length | Ban + detect (factory VQ-2) |
| Six gorgeous mismatched clips | Visual Theme lock first |
| Mass approve without open | Rule 7.3 visual QA JSON |

---

## 3. Academic / craft pillars (compressed, not paper dumps)

| Pillar | Operational form in skill |
|--------|---------------------------|
| Continuity editing / 180° | Axis note on multi-shot same space |
| Coverage (master→medium→CU→insert) | Mandatory variety quota |
| Montage / motif | Motifs×3 + match-cut language |
| Peak-end rule | Engineer emotional peak + ending |
| But/therefore causal chain | Beat sheet test |
| Visual complexity variation | Size/angle/subject/motif change |

---

## 4. Factory-native additions (our differentiator)

1. Output **CREATIVE.md + SHOT_DESIGN.md** into `stories/<ep>/`  
2. Map shots → `shots.json` fields + `motion_driver` (i2v/si2v)  
3. Hand off to **shot_qa_pack / shot_qa_record / freeze gate / assemble**  
4. Prompt craft: [docs/generation_prompt_craft.md](../../docs/generation_prompt_craft.md)  
5. Equip contract: [skills/README.md](../README.md)

---

## 5. Genre taxonomy research (v1.1)

See **`references/genre_research.md`** + **`references/genre_recipes.md`**.

| Input | Use |
|-------|-----|
| Academic (narrative/doc/experimental; Bordwell–Thompson conventions; hybridization; Screenwriters Taxonomy super-genres) | L0/L2 thinking; do not explode L1 |
| Social short-form practice (talk, dance, tips, UGC, lifestyle, comedy, music) | Primary L1 coverage |
| Factory modes | L0 ↔ production_mode |

**Minimal L1 set = 12 recipes (R01–R12).** Theme genres attach as modules.

## 6. Camera direction pack (v1.2)

See **`references/camera_direction.md`** + **`references/camera_direction_research.md`**.

Synthesized from: StudioBinder / B&H / Boords shot language, Master Shots lens-motivation practice, continuity 180°/coverage, lens storytelling (35/50/85 culture), vertical 9:16 creator+festival practice, MV chorus camera events, AI one-move constraints.

## 7. Composition pack (v1.3)

See **`references/composition.md`** + **`references/composition_research.md`**.

Synthesized from: StudioBinder composition rules, Filmmakers Academy negative space/balance, photo/film composition teaching (thirds, lines, depth), symmetry/asymmetry power dynamics, vertical creator framing practice, AI placement-prompt constraints. Emotion map = craft consensus defaults.

## 8. Lighting & look pack (v1.4)

See **`references/lighting_and_look.md`** + **`references/lighting_and_look_research.md`**.

Synthesized from: three-point + motivated/practical tradition, talking-head pro setups (off-axis key, neg fill, rim), high/low key, mixed color temperature cinema practice, grade/palette/skin policy, factory `looks/` lock, AI prompt light clauses.

## 9. Blocking pack (v1.5)

See **`references/blocking.md`** + **`references/blocking_research.md`**.

Synthesized from: directing open/closed stance & status, dialogue 180°/OTS, proxemics, prop-as-anchor for talk, gesture vs shot size, SI2V micro-performance, factory anatomy/prop-scale fails.

## 10. Production design pack (v1.6)

See **`references/production_design.md`** + **`references/production_design_research.md`**.

Synthesized from: mise-en-scène (setting/props/costume), PD role (dress vs prop), MV motif-forward design, density scales, factory location packs + graphics/weather fails.

## 11. Costume / hair / makeup pack (v1.7)

See **`references/costume_hair_makeup.md`** + research notes.

Synthesized from: mise-en-scène costume/MU as character, set continuity (wet hair, MU match), video MU matte vs shimmer, wardrobe silhouette/color vs world, factory wardrobe_lock + I2V no re-essay.

## 12. Texture / material / optical pack (v1.8)

See **`references/texture_material_optical.md`** + research notes.

Synthesized from: surface response under light, grain/optical character craft, DOF/bokeh isolation, AI material-noun prompting vs tag-soup, factory Materials slot + still-first texture.

## 13. Visual pacing pack (v1.9)

See **`references/visual_pacing.md`** + research notes.

Synthesized from: editing pacing/emotion via shot length, peak-end, short-form hook, MV section density, factory freeze-pad ban + length contracts; complements existing R1–R6/SIZE RHYTHM.

## 14. VFX / on-image graphics pack (v1.10)

See **`references/vfx_graphics_on_image.md`** + research notes.

Synthesized from: direction restraint on effects, post-caption discipline, AI gibberish-text/particle/glass failures, factory subtitles + Ideogram handoff; links PD graphics_policy + optical FX.

## 15. Sound → picture pack (v1.11)

See **`references/sound_to_picture.md`** + research notes.

Synthesized from: phrase/J-L cut intent, silence as tool, MV section vs lyric ban, factory production_mode×driver×mix + SI2V/performance/length contract.

## 16. Version backlog

- v2.0: channel-specific world bibles / recipe packs  
- Optional: refresh dryrun with full 1–10 stack fields
