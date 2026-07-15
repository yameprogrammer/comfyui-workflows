# Composition — frame design for emotion & clarity

- **Skill:** `video-direction`  
- **Pairs with:** [camera_direction.md](camera_direction.md) (size/angle/move/lens)  
- **Job of composition:** *Where things sit in the frame* so the eye knows what matters and the body feels stable, tense, lonely, powerful…  
- **Research:** [composition_research.md](composition_research.md)

**Prime rule:** Composition is **attention + emotion**, not decoration.  
Every shot: `what is the primary point of interest?` → place it on purpose.

Camera fields answer *how the camera is set*.  
Composition fields answer *how the rectangle is organized*.

---

## 0. Decision order (after camera intent)

```text
1) POI          Primary point of interest (face / prop / motif)
2) WEIGHT       Where does visual mass live? (balance)
3) SPACE        Negative space, headroom, lead room
4) LINES        Leading / diagonal / horizon
5) DEPTH        Foreground–mid–background layers
6) FRAMES       Frame-in-frame, occluders
7) FORMAT       9:16 vs 16:9 changes which “thirds” matter
8) EMOTION      stability | tension | isolation | power | intimacy
9) PROMPT       Concrete placement language (not “beautiful composition”)
```

Write optional SHOT_DESIGN field:

```yaml
composition: "thirds-right, lead room left, rain FG layer, balanced asym"
emotion_feel: "isolation"   # stability|tension|isolation|power|intimacy|awe|unease
```

---

## 1. Emotion map (what viewers tend to feel)

Synthesized from film composition practice + visual perception teaching (not a lab paper dump):

| Feel you want | Composition levers (typical) |
|---------------|------------------------------|
| **Stability / calm / order** | Symmetry, level horizon, balanced mass, center or mild thirds, deep readable space |
| **Equality / standoff** | Two equal masses, split frame, balanced two-shot |
| **Tension / unease** | Asymmetry, diagonal lines, imbalance, Dutch (with camera angle), subject near edge |
| **Isolation / loneliness** | Large negative space, subject small or on far third, empty half of frame |
| **Power / dominance** | Subject large, higher in frame or low camera *plus* occupying strong mass; others smaller |
| **Vulnerability** | High angle + more headroom above / or tiny in ELS with void |
| **Intimacy** | Tight positive space, shallow depth, POI large, minimal competing mass |
| **Anticipation / motion** | Lead room in direction of look/move |
| **Trapped / pressured** | Frame-in-frame tight, little negative space, heavy FG occlusion |
| **Awe / scale** | ELS, horizon low or high extreme, tiny figure, strong environment lines |
| **Mystery** | POI partial, dark negative space, off-screen room, occluded faces |
| **Sacred / formal** | Dead center, vertical symmetry, ritual top-down geometry |

**Break rules only with intent** — centered “wrong” can mean confrontation, icon, or web-to-camera direct address.

---

## 2. Core tools (grammar)

### 2.1 Rule of thirds

- Divide frame 3×3; place POI on **lines or intersections**.  
- Feels **natural, story-ready, room to breathe**.  
- Emotion: open, conversational, less confrontational than dead center.  
- **Break:** center for icon, confession to lens, Wes-Anderson formal, product hero.

### 2.2 Center composition

- POI on optical center (or vertical center line).  
- Emotion: **authority, confrontation, ritual, direct address**, sometimes emptiness if scale tiny.  
- Shorts talking-to-camera: center vertical is often **correct**, not lazy.

### 2.3 Balance: symmetrical vs asymmetrical

| Type | Feel | Use |
|------|------|-----|
| **Symmetrical balance** | Harmony, control, calm, formality | Architecture, ritual, brand mood, “perfect day” irony |
| **Asymmetrical balance** | Interest, tension, relationship power | One large mass vs several small; dialogue power (who owns frame) |
| **Unbalanced / dynamic** | Chaos, instability | Thriller beat, comedy shock — short duration |

StudioBinder / FA practice: asymmetry can still *balance* while implying **who has power**.

### 2.4 Negative space

- Empty (or low-detail) area that is still “designed”.  
- Emotion: isolation, calm, luxury minimal, dread (void).  
- **Looking room / lead room:** space in the direction subject looks or moves → anticipation.  
- **Starve lead room** (nose to frame edge) → blocked future, anxiety, comic claustrophobia.

### 2.5 Headroom

- Space above head.  
- Too much: floaty, weak, “amateur vertical”.  
- Too little: cramped, aggressive crop.  
- Emotion: correct headroom = competence; extreme = style (fashion vs panic).

### 2.6 Leading lines

- Roads, counters, rails, light edges, hallways → **eye path to POI**.  
- Emotion: inevitability, journey, focus, sometimes threat (corridor).  
- AI: name the line (`café counter leading to her hands`).

### 2.7 Diagonals

- Dynamic energy, instability, speed.  
- Emotion: tension, action, unease (with Dutch).  
- Calm dialogue: prefer level horizontals.

### 2.8 Depth layers (FG / MG / BG)

- Foreground occlusion, mid subject, background context.  
- Emotion: immersion, secrecy (FG blur), world-building.  
- Shorts: one clear FG motif (rain glass, cup rim) elevates cheap space.

### 2.9 Frame within frame

- Doors, windows, mirrors, shelves, phone UI (careful).  
- Emotion: trapped, observed, intimate portal, storybook.  
- Risk: mirror/glass logic fails in AI — tag risk.

### 2.10 Patterns, texture, rhythm

- Repeating shapes; break pattern with subject.  
- Emotion: order then disruption = story beat.

### 2.11 Figure–ground / contrast

- Subject separates via luminance, color, size, focus.  
- If figure melts into ground → composition fail even if “rule of thirds”.

### 2.12 Eye line & gaze

- Viewers follow eyes. Place gaze path with lead room.  
- OTS: dirty shoulder weight controls intimacy vs distance.

### 2.13 Golden ratio / dynamic symmetry (optional)

- Advanced grids (phi, armatures).  
- Use when refining hero stills; **don’t block AI with geometry jargon**. Prefer: thirds, diagonals, clear POI.

---

## 3. Format: 9:16 vertical composition

Vertical is not “horizontal thirds rotated only”.

| Topic | Practice |
|-------|----------|
| **Vertical weight** | Stack layers top→bottom; height is the luxury |
| **Center spine** | Many creators treat **central vertical axis** as primary balance for talk/B-roll (especially product + face) |
| **Thirds still work** | Horizontal thirds for **eye line / head** placement; vertical thirds for left-right tension |
| **Eye line** | Dominant eye often upper-third zone; avoid chin-only lower third |
| **Headroom** | Tighter than 16:9 instinct; don’t “sky dump” above head |
| **UI safe** | Keep POI out of extreme top/bottom chrome when known |
| **Wide in tall** | ELS = tall world + small figure, not letterbox landscape |
| **Two-shot vertical** | Stack or stagger depth; pure side-by-side often cramped |

Factory: match episode `format` work canvas when writing placement.

---

## 4. Shot size × composition (quick)

| Size | Composition bias |
|------|------------------|
| ELS | Environment geometry, tiny figure, horizon placement = mood |
| LS/FS | Full body + ground plane; leave walk lead room |
| MS | Thirds or center; hands must read |
| MCU/CU | Eyes on upper third; nose room; shallow ok |
| ECU | Abstract texture; center or extreme edge for unease |
| Insert | Fill with material; watch scale honesty |
| OTS | Shoulder ≤ ~1/3 unless style; eyes of far person clear |

---

## 5. Genre / L1 defaults (with camera_direction)

| L1 | Composition bias | Emotion target |
|----|------------------|----------------|
| R01 talking | Center or mild thirds; clean headroom; insert thirds | Trust, calm service |
| R02 drama | Asym power in two-shots; lead room on turns | Relation tension |
| R03 MV | Bold center icons + wide void; chorus mass change | Event, glamour |
| R04 dance | Full body clearance; top-down pattern | Energy, read limbs |
| R05 hook | Max POI clarity first frame; high contrast figure-ground | Stop scroll |
| R06 product | Center/product thirds; hands scale; clean neg space | Desire, clarity |
| R07 vlog/doc | Deep layers; imperfect balance ok | Observational |
| R08 mood | Huge neg space; symmetry or soft thirds | Lonely beauty |
| R09 comedy | Hold composition for punch; reaction CU clean | Timing |
| R10 thriller | Imbalance, edge placement, corridor lines | Dread |
| R11 explain | Center speaker; insert full-frame readable | Clarity |
| R12 one-take feel | Continuous lead room as they move | Flow |

---

## 6. AI / factory prompt language

**Do (concrete):**

```text
subject on right third, looking left with lead room,
large empty window negative space on left,
foreground bokeh rain on glass, mid-ground figure, soft neon background,
eye-level, medium close-up, 85mm look
```

**Don’t:**

```text
perfect composition, masterpiece framing, rule of thirds, 8k
```

**I2V:** composition is mostly locked by keyframe — motion prompt should not re-layout the frame; preserve “slow push, hold eyeline”.

**QA (keyframe):**  
- POI clear in 0.5s glance?  
- Headroom ok for format?  
- Lead room matches look/move?  
- Accidental edge amputation (hands/chin)?  
- Same composition 3× in a row? → redesign (ties R1/R2).

---

## 7. Anti-patterns

| ID | Pattern | Feel / fail | Fix |
|----|---------|-------------|-----|
| CMP1 | Dead center everything by accident | Flat, PPT | Thirds or intentional center note |
| CMP2 | No lead room (nose to edge) | Anxious or amateur | Add looking room unless trapped intent |
| CMP3 | Excess headroom | Weak, float | Raise subject / reframe |
| CMP4 | Subject merges into background | Invisible hero | Contrast, light, depth |
| CMP5 | Two equal faces fight | Confused POI | Asym power or OTS |
| CMP6 | 16:9 brain on 9:16 | Cropped limbs, side voids | Redesign vertical stack |
| CMP7 | Insert becomes face | Motif lost | Reframe prop full |
| CMP8 | Busy corners | Eye leak | Simplify mass |

---

## 8. Micro recipes

**Lonely café (isolation):** MCU on right third, left 60% empty wet window, soft interior practicals, eye level.  

**Power entrance (power):** Low angle FS, subject large lower-center mass, ceiling lines leading down, small doorway frame.  

**Confession (intimacy):** CU center or slight thirds, minimal neg space, eyes upper third, soft BG.  

**Thriller hall (unease):** Subject small on far third, long corridor leading lines, heavy FG door edge, high or dutch light.  

**Product (desire):** Center or lower-third product ECU, clean neg space, hands enter from bottom third.  

**Hook 1.5s (attention):** Single POI max size, high figure-ground, no competing text in frame.

---

## 9. SHOT_DESIGN checklist (composition)

- [ ] POI named  
- [ ] Balance type chosen (sym / asym / tense)  
- [ ] Headroom + lead room intentional  
- [ ] Depth layer at least one (FG or BG) when possible  
- [ ] Emotion_feel one word matches CREATIVE  
- [ ] Adjacent shots not same rectangle (13-thumbnail)  
- [ ] Format-specific (9:16 spine vs 16:9 width)  

---

## 10. Not in this file

- Lighting ratios / color / look → **[lighting_and_look.md](lighting_and_look.md)**  
- Blocking paths → **[blocking.md](blocking.md)**  
- Camera size/angle/move/lens mechanics → `camera_direction.md`  
