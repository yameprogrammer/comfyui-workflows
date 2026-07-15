# Costume, hair & makeup — character look for direction

- **Skill:** `video-direction`  
- **Job:** Episode **look decisions + continuity + shot readability** for clothes/hair/makeup  
- **Not this file:** Generating full character sheets (factory `character_full_sheet` / wardrobe lock)  
- **Factory:** `characters/<id>/bible` wardrobe · approved costume refs · QA K13  
- **Related:** [production_design.md](production_design.md) · [blocking.md](blocking.md) · [lighting_and_look.md](lighting_and_look.md)  
- **Research:** [costume_hair_makeup_research.md](costume_hair_makeup_research.md)

**Prime rule:** Costume / hair / makeup **narrate character** and must **survive the cut**.  
Pretty outfit that fights the set, or wet hair that teleports dry = fail.

```text
Character package = WHO they are (approved identity)
Episode CHM look   = HOW they appear in THIS story beat (states + intensity)
```

---

## 0. Decision order

```text
1) CHARACTER LOCK     character_id + wardrobe_locked bible / approved refs
2) EPISODE LOOK       default vs alt costume; accessories
3) SILHOUETTE         read in FS (dance/walk) vs MS talk
4) COLOR VS WORLD     separate from set (figure–ground)
5) HAIR STATE         style + wet/wind/loose continuity
6) MAKEUP INTENSITY   natural | soft glam | beauty | stylized MV | VFX
7) BEAT STATES        jacket on/off, smudge, rain-wet, undone
8) SHOT SIZE FIT      CU skin vs FS costume read
9) LIGHT INTERACTION  shimmer, oily skin, matte under key
10) AI PROMPT RULE    full CHM only on STILLS; I2V motion-only
```

CREATIVE / episode:

```yaml
character_ids: [sho_heroine_v3]
wardrobe_id: default          # or alt1 — from bible
silhouette: "summer mini, open shoulders, clean legs"
color_vs_set: "cream blouse vs warm wood; skirt mid-tone not camouflage"
hair_base: "long loose"
hair_states: [dry_interior, rain_damp_ends]
makeup_intensity: natural     # natural|soft_glam|beauty|mv_stylized
makeup_notes: "soft skin, matte lids, defined lashes; no glitter"
chm_continuity_risks: [wet_hair, cup_lip_contact, mascara_smudge]
```

SHOT_DESIGN:

```yaml
chm: "wardrobe default; hair damp ends; natural MU; jacket off"
# or continuity notes include chm_state
```

---

## 1. Emotion / story map

Craft + film-studies consensus (costume as character):

| Intent | Costume | Hair | Makeup |
|--------|---------|------|--------|
| **Trust / service** | Clean, approachable, tidy | Controlled soft | Natural, even skin |
| **Vulnerability** | Softer fabric, slightly undone | Loose, face-framing | Minimal, skin texture ok |
| **Power** | Sharp silhouette, structure | Sleek, up or precise | Defined features, controlled |
| **Youth / summer** | Short hem, light fabric | Loose, airy | Fresh, dewy carefully (not oily AI) |
| **Grief / rain** | Same costume + **wet state** | Damp clumps, frizz edges | Slight run risk only if beat needs |
| **Romance** | Color harmony with partner/set | Soft movement | Soft glam, healthy flush |
| **Comedy** | Slightly wrong/awkward detail | One comic strand | Clean readable face |
| **Thriller** | Dark or plain, mobility | Face partly obscured optional | Pale/controlled, reduce glow |
| **MV glamour** | Graphic silhouette, motif color | Sculpted | Higher glam — still one look family |
| **Doc / real** | Lived-in, imperfect ok | Natural movement | Near-bare, avoid beauty filter look |

---

## 2. Costume (wardrobe)

### 2.1 What costume does (mise-en-scène)

- Class, period, job, mood, **theme**  
- Grounds character in the world (StudioBinder / film intro texts)  
- Accessories count as costume (bag, jewelry, shoes)

### 2.2 Silhouette

| Check | Why |
|-------|-----|
| Readable in **FS** | Dance, walk, wide café |
| Not melting into set color | Figure–ground (with PD + light) |
| Motion-friendly | Skirt length vs sit; no constant wardrobe fight |

### 2.3 Color & pattern

- 1–2 dominant garment colors aligned with palette / motif  
- Busy pattern → avoid on talk CU (moire / noise)  
- Motif color on accessory better than full outfit scream  

### 2.4 Layers & states

| State | Use |
|-------|-----|
| Jacket / cardigan on–off | Status, temperature, time |
| Shoes visible / insert | Shorts dance or shoe story — feet risk |
| Bag held / hung | Entrance/exit geography |

### 2.5 Factory wardrobe lock

```text
character_set_wardrobe → bible wardrobe_default / alt / props + lock
```

Episode direction **picks** default vs alt; does not invent third wardrobe mid-shoot without promote path.

---

## 3. Hair

### 3.1 Base style

- Long/short, bangs, updo — fixed for episode identity  
- Must match approved head turns when possible  

### 3.2 Dynamic states (continuity critical)

| State | Continuity note |
|-------|-----------------|
| Dry interior | Default café |
| Rain damp / wet | Match exterior/interior wetness (set practice) |
| Wind-blown | Exterior only; reset indoor |
| Loose strand | Comic or intimate — track which side |
| Tied back | Work mode / later beat |

**Rule:** wetness **degree** must match across cuts of same moment (makeup/hair continuity teaching).

### 3.3 Face framing vs camera

- Hair over eye can kill SI2V lip read — pin or block intentionally  
- Backlight / rim makes flyaways glow — style for light  

---

## 4. Makeup

### 4.1 Intensity ladder (video)

| Level | Look | Use |
|-------|------|-----|
| **natural** | Even skin, soft definition, matte-friendly lids | R01 talk, story hybrid default |
| **soft_glam** | Slight eye/lip emphasis | Date, soft MV verse |
| **beauty** | Clean high polish | Beauty brand, some ads |
| **mv_stylized** | Graphic color, strong liner | R03 only if CREATIVE allows |
| **vfx / injury** | Continuity photos mandatory | Special episode |

### 4.2 Camera & light interaction (film MU craft)

- **Shimmer / glitter** → specular pops under key; usually avoid natural talk  
- **Matte lids** often safer for video natural look  
- Makeup checked under **same quality of light as shoot** (MU tutorial practice)  
- Heavy base can look mask-like on 85mm CU — prefer skin-like  

### 4.3 Continuity

Lipstick level, blush, under-eye, beauty marks, wounds — **match cut to cut**.  
Rain + mascara = only if story wants run; then all angles match.

---

## 5. Shot size × CHM

| Size | Prioritize |
|------|------------|
| ELS/LS | Silhouette, color block, wet coat read |
| FS | Full outfit + shoes if story; dance clearance |
| MS | Neckline, hands+sleeves, hair shoulders |
| MCU/CU | Skin, eyes, lip; hair not covering mouth |
| ECU | Skin texture / tear / makeup detail only |
| Insert | Hands+nails+jewelry — not wrong nail polish jump |

---

## 6. L1 defaults

| L1 | CHM bias |
|----|----------|
| R01 talking | natural MU; locked wardrobe; hair controlled |
| R02 drama | state changes on turn (undone jacket, smudge) |
| R03 MV | stronger silhouette; optional soft_glam/mv; still one family |
| R04 dance | FS silhouette; secure hair; sweat optional later |
| R05 hook | Max readable outfit block in 1.5s |
| R06 product | Hands/nails clean; outfit non-competing |
| R07 vlog | Lived-in ok; natural MU |
| R08 mood | Fabric texture hero; soft hair movement |
| R09 comedy | Clear face; one comic hair strand optional |
| R10 thriller | Desat wardrobe; pale/controlled MU |
| R11 explain | Clean broadcast natural |
| R12 one-take | Zero wardrobe teleport mid-chain |

---

## 7. AI / factory rules

| Rule | Why |
|------|-----|
| **Still prompts:** include wardrobe + hair state + MU intensity | Identity + world |
| **I2V/SI2V:** never re-essay face/wardrobe | Factory Rule 7.5 / skill identity |
| Prefer **approved costume ref** path in compose | Consistency |
| Wet hair: say `damp ends` / `rain-wet strands` consistently | Continuity |
| Avoid random outfit per shot | K13 fail |
| Short skirt sit: check blocking for modesty/anatomy | Risk |

**Still clause example:**

```text
wearing cream blouse and short summer skirt (wardrobe default),
long hair loose with rain-damp ends, natural soft makeup matte lids,
...
```

**Motion:** `subtle hair drift, continuous` — not re-describing dress.

---

## 8. Continuity bible (CHM)

| Item | Track |
|------|--------|
| Outfit id | default / alt1 |
| Outer layer | on/off |
| Hair wetness | dry / damp / wet + when changed |
| Hair side part / strand | left/right |
| Lip color intensity | same in reverse angles |
| Accessories | earrings, bag present/absent |
| Shoes | on in FS inserts |

Photos/notes in episode meta recommended for multi-day (set practice).

---

## 9. Anti-patterns

| ID | Pattern | Fix |
|----|---------|-----|
| CHM1 | New outfit every shot | Lock wardrobe_id |
| CHM2 | Dry hair after rain LS | Wetness bible |
| CHM3 | Glitter MU on soft talk | natural + matte |
| CHM4 | Hair covers mouth on si2v | Clear face |
| CHM5 | Outfit color = wall color | Contrast / regrade set |
| CHM6 | I2V rewrites wardrobe | Motion-only prompt |
| CHM7 | Alt wardrobe without bible | set_wardrobe or stay default |
| CHM8 | Injury/MU jump cut | Match or cutaway |

---

## 10. Micro recipes

**Rain café hybrid (R01):**  
default summer wardrobe; interior dry hair start → if exterior LS, damp ends only after exit beat; natural MU; cup may touch lip — watch lipstick continuity.

**MV chorus lift:**  
Same base outfit; optional jacket off; hair freer; soft_glam one step up from verse — not full new character.

**Thriller night:**  
Darker layer on; hair half-shadow face optional; desat lip; no beauty glow.

---

## 11. Stack position

| Layer | File |
|-------|------|
| Camera | camera_direction |
| Composition | composition |
| Light | lighting_and_look |
| Blocking | blocking |
| World / set | production_design |
| **Character surface** | **costume_hair_makeup** |

Incomplete design if wardrobe/hair/MU state blank on hero character shots.

---

## 12. Not in this file

- Sewing patterns, brand shopping lists  
- Full L3 LoRA training  
- Character cast pool / promote SOP (use character pipeline docs)  
