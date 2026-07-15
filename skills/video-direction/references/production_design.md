# Production design & motif staging

- **Skill:** `video-direction`  
- **Scope:** What is **put in front of the camera** to build the world: setting, set dressing, props, costume/hair continuity, environmental effects — staged for story and motif.  
- **Overlaps (do not re-teach):** lighting → `lighting_and_look.md` · body path → `blocking.md` · frame geometry → `composition.md` · lens/angle → `camera_direction.md`  
- **Factory:** `locations/` · `characters/` wardrobe · CREATIVE motifs · `looks/`  
- **Research:** [production_design_research.md](production_design_research.md)

**Prime rule (mise-en-scène craft):** Everything visible is a **choice that narrates**.  
Empty “nice café BG” is not design. Design answers: *Whose world? What period/class/mood? Which 3 motifs return?*

---

## 0. Decision order

```text
1) WORLD ONE-LINER     place + class + time + weather + emotion
2) LOCATION PACKAGE    locations/<id> approved refs (no improvised BG)
3) DRESSING DENSITY    sparse luxury / lived-in / chaotic / sterile
4) HERO PROPS          held + story-critical (hand props)
5) SET DRESSING        BG furniture, clutter, wall life
6) MOTIFS ×3           place + recycle across shots (match-cut ready)
7) COSTUME / HAIR      character package + continuity states
8) GRAPHICS IN WORLD   signs, menus, screens — readable or abstract?
9) ENVIRONMENT FX      rain, steam, dust, reflections
10) CONTINUITY BIBLE   open/closed, wet/dry, full/empty, day/night
11) SHOT STAGING       what must read in THIS size (insert vs LS)
```

CREATIVE / episode fields:

```yaml
world_one_liner: "rain-soaked Seoul café, soft service economy loneliness"
location_id: cafe_seoul_v1
dressing_density: lived-in_sparse   # sterile|lived-in_sparse|cluttered|opulent|decay
motifs:
  - yellow umbrella
  - iced americano + straw
  - wet window neon
hero_props: [cup, umbrella, receipt]
set_dressing_notes: "steam from machine mid-BG; one empty chair motif"
graphics_policy: soft_blur_signage   # readable|soft_blur|none
env_fx: rain_on_glass
```

SHOT_DESIGN optional:

```yaml
world: "same café SC01; umbrella closed on hook; cup half-full"
prop_state: "straw bent, condensation"
```

---

## 1. Emotion map (world → feel)

| Feel | Design levers |
|------|----------------|
| **Loneliness** | Empty chair, single place setting, large window void, sparse tables |
| **Warm service** | Soft practicals, menu board soft, steam, tidy bar, open stools |
| **Wealth / luxury** | Sparse high-end materials, negative space, few perfect objects |
| **Chaos / stress** | Clutter, stacked cups, harsh signage, competing colors |
| **Nostalgia** | Period props, paper menus, warm wood, soft wear |
| **Threat** | Corridor depth, blocked exits, harsh practicals, empty street wet |
| **Romance** | Shared dessert, two cups, soft textiles, close table gap |
| **Youth / trend** | Phone, stickers, neon, brand-ish but not logo spam |
| **Decay / noir** | Wear, dirt edges, flickering practical feel, sparse life |
| **Sacred / ritual** | Symmetry in set, centered object, clear altar-like prop |

---

## 2. Layers of the world (what PD owns)

### 2.1 Setting / location

- Geography that **reads in LS** (where are we in 1 second?).  
- Factory: **`location_id` + approved refs** — no random invented street if episode locks a pack.  
- Angle variety still uses same world physics (door side, window side).

### 2.2 Set dressing (background life)

- Furniture, wall art, shelves, plants, other customers (soft), machines.  
- **Density** controls class and calm.  
- Dress for **depth** (FG glass, mid table, BG bar) — helps composition layers.  
- AI: name 2–3 dressing anchors, not 20 objects (clutter → mush).

### 2.3 Props (handled)

| Type | Role |
|------|------|
| **Hero prop** | Story/motif (umbrella, cup, letter) |
| **Business prop** | Anchors blocking (phone, pen) |
| **Atmosphere prop** | BG only (other cups, books) |

Hero props need: **state** (open/closed, full/empty), **scale**, **hand contact**, continuity across cuts.

### 2.4 Costume, hair, makeup (character surface)

Deep guide: **[costume_hair_makeup.md](costume_hair_makeup.md)**.

- Factory character bible: wardrobe_default / alt / props + lock.  
- Episode **states:** wet hair, jacket on/off, MU intensity.  
- Color of wardrobe vs set (figure–ground).  
- Don’t invent unlocked outfits mid-episode.

### 2.5 Graphics & text in world

Deep policy (VFX + captions + AI type risk): **[vfx_graphics_on_image.md](vfx_graphics_on_image.md)**.

| Policy | When |
|--------|------|
| **soft_blur / unreadable** | Default — avoid AI gibberish logos |
| **readable intentional** | Title/menu hero → Ideogram / typography tool |
| **none** | Abstract mood sets |

### 2.6 Environment FX

Rain glass, steam, haze feel, dust motes, puddle reflections, fog breath.  
Must match **weather continuity** and lighting (wet speculars).  
AI risk: glass/mirror logic — tag `risk: glass`.

### 2.7 Color & material of the world

Materials: wood, wet asphalt, chrome, ceramic, fabric.  
Supports look_id palette; motif color appears sparingly pure (CREATIVE).

---

## 3. Motif staging (hero of this file)

CREATIVE requires **motifs ×3**. Production design **places and recycles** them.

| Stage | What to do |
|-------|------------|
| **Introduce** | First clear read (often insert or LS with flag) |
| **Vary** | New size/angle/context (hand → street → reflection) |
| **Payoff** | Chorus/climax return (match-cut shape/color) |
| **Residue** | Outro still life of motif alone |

**Rules:**

1. Motif must be **photographable** (specific object, not abstract “sadness”).  
2. At least **two sizes** across episode (e.g. ECU logo on cup + LS yellow umbrella in rain).  
3. Don’t show all three motifs every shot — **rhythm**, not spam.  
4. Match-cut friendly: similar shape/color across cuts (R5).  
5. If motif is handheld → blocking contact rules apply.

---

## 4. Dressing density scale

| Code | Look | Use |
|------|------|-----|
| `sterile` | Minimal, empty surfaces | Luxury, lab, unease |
| `lived-in_sparse` | Few true details | Default café/talk quality |
| `cluttered` | Busy shelves, mess | Stress, comedy, poverty story |
| `opulent` | Rich materials, controlled plenty | Brand, fantasy |
| `decay` | Wear, dust, broken practicals | Noir, thriller |

AI: sparse well-named > dense junk list.

---

## 5. Staging for shot size

| Size | World must show |
|------|-----------------|
| ELS/LS | Architecture + weather + one motif flag |
| MS | Table relationship + hero prop + light practical |
| CU | Face + maybe prop edge; BG soft dressing only |
| Insert | Prop material + hand scale; BG simplified |
| OTS | Near shoulder costume texture + far face + table |

**Insert fails** when world design never planned a clean prop angle — design prop for insert early.

---

## 6. L1 defaults

| L1 | World bias |
|----|------------|
| R01 talking | Lived-in_sparse café/desk; hero cup; steam/window |
| R02 drama | Dressing supports status (whose home cleaner?) |
| R03 MV | Motif-forward; section color/set shifts optional but continuous identity |
| R04 dance | Clear floor; minimal trip hazards; costume read FS |
| R05 hook | One iconic object/world hit in frame 1 |
| R06 product | Hero product perfect; BG sterile or lifestyle sparse |
| R07 vlog | Real clutter ok if readable; location truth |
| R08 mood | Sparse + texture materials; motif still life |
| R09 comedy | Gag prop ready; clean sightline |
| R10 thriller | Corridor/door practicals; sparse threat space |
| R11 explain | Clean desk; demo prop only |
| R12 one-take | Single geography fully dressed once; no teleport set |

---

## 7. Continuity bible (world)

Track across shots:

| Item | States |
|------|--------|
| Prop open/closed | umbrella, laptop, door |
| Liquid level | cup full → half |
| Weather wetness | glass, hair, coat, street |
| Time of day | practicals on/off |
| Wardrobe layers | jacket, bag |
| Seat position | who sits where |
| Damage | bent straw, smudge — only if intentional |

Factory QA: K13 wardrobe, K14 weather, prop continuity.

---

## 8. AI / factory constraints

| Risk | Design fix |
|------|------------|
| Gibberish signage | `graphics_policy: soft_blur` or dedicated typography shot |
| Location drift | Force `location_id` + approved ref language |
| Prop scale | Explicit; insert hero |
| Glass/mirror nonsense | Avoid multi-reflection; risk tag |
| Clutter mush | Max 3 named dressing anchors per prompt |
| Motif forgotten | Motif checklist in SHOT_DESIGN audit |

**Still prompt world clause example:**

```text
seoul café interior, lived-in sparse, wooden counter mid-ground,
warm practical lamp, rain-streaked window background,
iced americano with straw on table, condensation, correct hand scale
```

**I2V:** do not re-list entire set; motion of people/props only.

---

## 9. Anti-patterns

| ID | Pattern | Fix |
|----|---------|-----|
| PD1 | Random BG every shot | location_id + anchors |
| PD2 | Motif only once | introduce/vary/payoff |
| PD3 | Logo salad | blur policy / one readable graphic |
| PD4 | Prop teleport state | continuity bible |
| PD5 | Overdress AI junk | density down, 3 anchors |
| PD6 | Costume fights set (camouflage) | contrast wardrobe |
| PD7 | Weather amnesia | wet/dry list |
| PD8 | Product wrong scale | insert + measure language |

---

## 10. Micro recipes

**Rain café hybrid:**  
Window rain streaks BG, one empty chair LS motif, cup hero MS, umbrella on hook (closed) → later open on street. Density lived-in_sparse. Soft blur menu board.

**MV chorus motif payoff:**  
Verse: ECU yellow umbrella fabric texture → Chorus: LS figure under umbrella in flood street (same yellow pure).

**Thriller corridor:**  
Single hanging practical, scuff marks, no clutter, door handle insert hero, wet floor optional.

**Product desk:**  
Sterile surface, one plant soft BG, product center, cable managed, no brand spam.

---

## 11. Full visual stack checklist

| Layer | File | Question |
|-------|------|----------|
| Camera | camera_direction | How do we look? |
| Composition | composition | How is the rectangle organized? |
| Light | lighting_and_look | How is form revealed? |
| Blocking | blocking | What do bodies/hands do? |
| **World** | **production_design** | **What world/objects/motifs exist?** |

All five for production keyframes.

---

## 12. Not in this file

- Full architecture build specs  
- Historical period research dumps  
- Character sheet generation SOP (character_casting pipeline)  
- Location full_sheet CLI (use factory scripts)  
