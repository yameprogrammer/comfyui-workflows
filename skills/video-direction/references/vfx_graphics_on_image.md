# VFX, composite risk & on-image graphics

- **Skill:** `video-direction`  
- **Job:** **Whether / when / how much** effect and text appear on the picture — direction decisions + AI risk + factory handoff.  
- **Not:** Full Comfy VFX graphs, AE preset encyclopedias, 3D pipelines.  
- **Overlaps:** env FX in [production_design](production_design.md) · flare/haze in [texture_material_optical](texture_material_optical.md) · subtitles factory CLI  
- **Research:** [vfx_graphics_on_image_research.md](vfx_graphics_on_image_research.md)

**Prime rule:** Effects are **seasoning or story**, never default noise.  
**On-image text is guilty until proven intentional.** Prefer post burn-in / SRT for dialogue.

---

## 0. Decision order

```text
1) NEED?              does the beat fail without this effect/text?
2) CLASS              env | optical | composite | text_on_image | overlay_ui
3) INTENSITY          none | subtle | medium | hero
4) TIMING             whole shot vs peak only vs residual
5) READABILITY        face/POI still clear?
6) AI RISK            glass, smoke limbs, gibberish type
7) CONTINUITY         density/state match neighbors
8) HANDOFF            prompt still | factory subtitle | Ideogram typography shot
9) BAN LIST           rainbow flare spam, fake Hangul menus, freeze+VFX cover
```

CREATIVE / episode:

```yaml
vfx_policy: minimal              # none|minimal|selective|hero_mv
graphics_policy: soft_blur_signage  # none|soft_blur|readable_intentional
subtitle_policy: soft_burn_post   # none|soft_burn_post|hard_burn|in_frame_ai_forbid
allowed_vfx: [rain_on_glass, light_steam]
forbidden_vfx: [rainbow_lens_flare_spam, heavy_particles_face]
typography_shots: []             # shot ids that may use Ideogram / readable type
```

SHOT:

```yaml
vfx: "rain streaks glass only; no flare"
text_on_image: none              # none|soft_bg_signage|hero_title|ui_overlay
```

---

## 1. Taxonomy

| Class | Examples | Default |
|-------|----------|---------|
| **Env / atmosphere** | rain, steam, dust, fog breath, smoke | subtle when world needs |
| **Optical** | flare, bloom, haze, rain-on-lens | rare; see texture_material_optical |
| **Composite risk** | mirrors, glass double, green-screen edges, extra limbs in fog | avoid or still-hero only |
| **In-world graphics** | menus, neon signs, posters | soft_blur unless typography shot |
| **On-image text (post)** | captions, titles, CTA | factory subtitles / title cards |
| **UI overlay** | phone UI, app chrome | product/demo only; designed |

---

## 2. Emotion map

| Intent | VFX / graphics |
|--------|----------------|
| **Trust talk** | almost none; clean face |
| **Lonely rain** | rain glass, wet specular — not particle storm |
| **Mystery** | light haze, sparse practical glow |
| **Energy MV** | selective flare/bloom on chorus only |
| **Horror** | sparse; underexposure > particle spam |
| **Comedy** | clean; gag prop > VFX |
| **Product** | clean; optional soft specular; no dirt FX |
| **Explain** | no in-frame AI text; post captions if needed |
| **Hook** | max clarity; VFX must not hide POI |

---

## 3. Intensity scale

| Level | Meaning |
|-------|---------|
| **none** | World materials only |
| **subtle** | Env readable in BG (rain streaks) |
| **medium** | Effect part of mood (steam + rain) |
| **hero** | Effect *is* the shot (title card, storm plate) — rare |

Rule: hero VFX ≤ 1–2 shots per short unless MV spectacle brief.

---

## 4. Text-on-image policy (hard)

| Mode | Use | Tool |
|------|-----|------|
| **in_frame_ai_forbid** | Default for dialogue/story | Do not ask T2I for readable Korean/English soup |
| **soft_blur_signage** | BG menus/signs | Prompt unreadable / soft |
| **readable_intentional** | One title, shop name hero, menu insert | `generate_ideogram4` / typography doc — dedicated shot |
| **soft_burn_post** | Captions, lyrics, CTA | `episode_subtitles` SRT + soft burn |
| **hard_burn** | Final deliverable burn | assemble/export path only when required |

**Never:** random neon Hangul, “Lorem” logos, AI-generated app UI text for real product claims.

---

## 5. Composite / AI failure zones

| Risk | Why | Direction fix |
|------|-----|----------------|
| Multi-mirror / shop window | Physics break | Avoid or insert still only |
| Thick smoke/fog on face | Extra limbs, melt | Keep face clear zone |
| Particles through body | Mesh nonsense | Behind subject only |
| Fake glass refraction | Warped identity | Simple streaks > complex refraction |
| Speed ramp soup | Temporal junk | One intentional ramp max |
| VFX to hide bad face | Covers fail | Fix keyframe / CHM instead |

Tag SHOT `risk: glass` / `risk: particles` when present.

---

## 6. L1 defaults

| L1 | vfx_policy | text |
|----|------------|------|
| R01 talking | minimal (rain glass ok) | soft_burn_post if captions; no in-frame AI |
| R02 drama | minimal–selective | same |
| R03 MV | selective; hero on chorus ok | titles via typography shot; lyrics post often |
| R04 dance | minimal; clean body | captions post optional |
| R05 hook | none–subtle | no text covering POI first 1.5s |
| R06 product | none | UI only if designed; no AI fake UI |
| R07 vlog | subtle real-world | soft signs |
| R08 mood | selective atmosphere | little text |
| R09 comedy | none | punchline text post if any |
| R10 thriller | sparse haze/practical | no spam |
| R11 explain | none | **subtitles post**; diagrams not random type |
| R12 one-take | continuous env only | no late overlay spam |

---

## 7. Timing

| Pattern | Use |
|---------|-----|
| Whole-shot env | Rain always on glass in café |
| Peak-only optical | Flare on chorus hit |
| Residual still + soft particle | Outro (careful AI) |
| Text after picture locks | Burn captions post-approve |

Don’t use VFX to **extend** duration (not a substitute for motion).

---

## 8. Factory handoff

| Need | Where |
|------|--------|
| Rain/steam in still | Moody prompt (env materials) |
| Episode captions | `episode_subtitles.py` · docs/shorts_subtitles.md |
| Intentional signage/title | `generate_ideogram4.py` · ideogram4_typography_tool.md |
| Assemble burn | assemble / deliver path |
| Heavy VFX | Out of scope unless new workflow promoted to agent/ |

Direction writes **policy + shot notes**; does not invent new Comfy graphs mid-episode.

---

## 9. Continuity

| Item | Track |
|------|--------|
| Rain density | light/medium — same scene |
| Steam on/off | machine state |
| Sign content | if readable, exact same |
| Subtitle style | one style guide per ep |
| Flare presence | which shots only |

---

## 10. AI / prompt

**Still (subtle rain):**

```text
… rain-streaked window glass in background, soft condensation,
no readable text on menus, no lens flare …
```

**Still (forbid junk type):**

```text
… clean surfaces, unreadable soft signage, no logos, no posters with legible text …
```

**I2V:** do not add “particles increasing” to fake energy; keep motion prompt motion-only.

**QA:**

- [ ] Face free of particle mud on talk/lip?  
- [ ] Any accidental readable gibberish?  
- [ ] VFX intensity matches policy?  
- [ ] Text planned via post, not AI soup?  

---

## 11. Anti-patterns

| ID | Pattern | Fix |
|----|---------|-----|
| VFX1 | Flare every shot | Peak only or ban |
| VFX2 | AI Hangul menu wallpaper | soft_blur / none |
| VFX3 | Smoke hides identity fail | Regen still |
| VFX4 | Captions burned in generate | use episode_subtitles |
| VFX5 | Particle storm on CU | Clear face |
| VFX6 | VFX as freeze-pad cover | Full motion regen |
| VFX7 | Fake app UI for real product | Designed assets only |
| VFX8 | Mirror world break | Avoid angle / still insert |

---

## 12. Micro recipes

**Rain café talk:**  
`vfx_policy: minimal` · rain_on_glass only · `graphics_policy: soft_blur_signage` · dialogue captions post if needed.

**MV chorus:**  
subtle bloom/flare **one** chorus hero; verse clean; titles as separate typography still if needed.

**Explain short:**  
zero env spam; all text via SRT soft burn; demo prop insert not AI labels.

---

## 13. Stack position

| # | Layer |
|---|--------|
| 1–7 | Picture craft |
| 8 | Visual pacing |
| **9** | **VFX / on-image graphics (this file)** |

---

## 14. Not in this file

- Node graphs, AE expressions  
- Full color key / roto SOP  
- Font licensing catalogs  
