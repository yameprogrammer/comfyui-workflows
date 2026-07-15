# Blocking — body, path, eyeline, props in the frame

- **Skill:** `video-direction`  
- **Pairs with:** [camera_direction.md](camera_direction.md) · [composition.md](composition.md) · [lighting_and_look.md](lighting_and_look.md)  
- **Research:** [blocking_research.md](blocking_research.md)

**Prime rule:** Blocking is **where people and props are, which way they face, and how they move** so camera, light, and story all work.  
Empty “action: standing” is not blocking.

```text
Camera = how we look
Composition = how the rectangle is organized
Light = how form is revealed
Blocking = what bodies/props do in space  ← this file
```

---

## 0. Decision order

```text
1) BEAT INTENT     what changes in this shot? (status, info, emotion)
2) WHO IS POI      whose body/face owns the beat?
3) RELATION        distance / height / who faces whom
4) ORIENTATION     face/chest toward camera, key light, partner
5) PATH            enter / stay / exit / micro gesture only
6) HANDS & PROPS   scale, contact, silhouette
7) EYELINE         where eyes go (matches lead room + OTS)
8) CAMERA SIDE     dirty shoulder, 180°, open vs closed stance
9) LIGHT SIDE      face the key (or intentionally silhouette)
10) RISK           feet/hands/glass — simplify path if AI-risky
```

SHOT_DESIGN fields:

```yaml
action: "sits, turns cup a quarter turn, eyes down then to partner"
blocking: "open stance cam-right of table; partner OTS left; key on her face"
eyeline: "to partner / off-left window"
prop: "iced americano, straw, correct hand scale"
```

---

## 1. Emotion map (body in space → feel)

Craft consensus from directing/blocking practice:

| Feel | Blocking levers |
|------|-----------------|
| **Connection / trust** | Open shoulders to partner/cam; equal distance; shared eyeline |
| **Conflict** | Closed stance, 180° oppose, unequal distance/height, turn away |
| **Power** | Higher seat/stand, larger frame share, others face them; advance into space |
| **Submission / retreat** | Smaller, sit lower, back up, eyes down, prop as shield |
| **Isolation** | Alone in large space, back half-turned, distance from practical “life” |
| **Intimacy** | Close proximity, shared prop, soft lean-in, micro head turn |
| **Anxiety** | Fidget prop, closed arms, tight path, glance off-screen |
| **Comedy** | Hold still before punch; delayed reaction body; prop timing |
| **Mystery** | Face withheld, body first; reveal turn into key light |
| **Service / hospitality** | Open chest to guest, hands free or prop-offer, approach path clear |

---

## 2. Core tools

### 2.1 Open vs closed stance

| | Open | Closed |
|--|------|--------|
| Body | Chest/shoulders readable to cam or partner | Angled away, barrier arms |
| Feel | Honesty, welcome, performance | Guard, secret, cold |
| Talk shorts | Default open to lens or guest | Use for conflict beat |

### 2.2 Distance (proxemics)

| Distance | Story |
|----------|--------|
| Far (LS) | Social map, loneliness |
| Conversational | Default dialogue |
| Intimate | Secret, romance, threat |
| Crowding | Comedy awkward / aggression |

Change distance **on the turn** of a beat, not randomly.

### 2.3 Height

Stand over sit, step on platform, kneel — **status**.  
Match camera height (camera_direction) to height story: low cam + standing subject = power stack.

### 2.4 Eyeline

- Eyes lead audience (composition lead room).  
- Dialogue: consistent 180° eyelines.  
- Off-screen look must match next POV or motivate break.  
- SI2V lip heroes: stable head; micro nods only (performance profiles).

### 2.5 180° & camera side (body side)

- Keep both people on one side of the axis for continuous dialogue.  
- **Clean single** vs **OTS dirty shoulder** — shoulder size controls intimacy.  
- Crossing axis = disorientation event (note in SHOT_DESIGN).

### 2.6 Facing the key

- Prefer key light on the storytelling face (lighting_and_look).  
- Turn into light on emotional open; turn to shadow on hide/shame.  
- Don’t block face with prop unless intentional (menu, hair, cup).

### 2.7 Path & entrances

| Path | Use |
|------|-----|
| Enter frame | New info, energy |
| Exit | End of beat, rejection |
| Cross | Power claim, scene geography |
| Orbit around furniture | Café realism — keep axis |
| Micro only | SI2V speak; avoid large lean (identity/warp) |

**One-take feel (R12):** path continuous; size changes via camera/subject approach, not teleport.

### 2.8 Hands, arms, gesture scale

- Gesture must fit **shot size** (CU: finger; MS: hand; FS: arm).  
- Closed arms = barrier; open palms = offer.  
- AI risk: complex finger work → simplify or insert-only.

### 2.9 Props as blocking partners

| Prop job | Example |
|----------|---------|
| Anchor | Hands on cup = still torso for SI2V |
| Shield | Menu, phone between people |
| Status | Who pours, who pays |
| Motif | Umbrella open/closed continuity |
| Timer | Sip = beat punctuation (i2v) |

**Scale honesty:** prop size vs hand (factory fail: giant cup / tiny umbrella).  
Write prop in blocking + risk if hands/feet.

### 2.10 Sit / stand / lean furniture

- Chair distance from table = openness.  
- Lean on counter = casual power.  
- Edge-of-seat = urgency.  
- Don’t let furniture hide the story handoff (cup below frame).

### 2.11 Group / two-person geometry

| Pattern | Read |
|---------|------|
| 50/50 two-shot | Equality |
| Favor one (more face) | Power / POI |
| Stacked depth (near/far) | Hierarchy, eavesdrop |
| Parallel walk | Bond or false bond |
| One seated one standing | Status |

### 2.12 Background people / extras (if any)

- Soft motion only; never steal POI.  
- Clear lane for hero path.

---

## 3. Shot size × blocking

| Size | Blocking focus |
|------|----------------|
| ELS/LS | Path through space, silhouette, who owns geography |
| FS | Full walk cycle, costume read, dance clear feet |
| MS | Gesture + prop + torso open/closed |
| MCU | Head turn, eyeline, micro shoulder; hands if in frame |
| CU | Eyes, mouth; minimal head thrash for SI2V |
| ECU | Single feature; body mostly still |
| Insert | Hands+prop only; face out |
| OTS | Near shoulder stable; far face + eyeline |

---

## 4. Motion driver × blocking

| Driver | Blocking policy |
|--------|-----------------|
| **si2v** | Head stable, micro performance; prop can anchor hands; no big stand-up mid-line |
| **i2v** | Clear single action (sip, walk start, turn); continuous path |
| **still** | Pose hold; intentional; label allow_freeze |
| **chain one-take** | Exit pose = next entrance; no teleport wardrobe |

Performance profiles (`warm_greeting`, etc.) = **gesture intensity**, not new geography every line.

---

## 5. L1 defaults

| L1 | Blocking bias |
|----|----------------|
| R01 talking | Seated open to guest/cam; prop sip punctuation; inserts for hands |
| R02 drama | Distance/height changes on turn; OTS pairs |
| R03 MV | Choreographed poses; chorus bigger body; verse micro |
| R04 dance | Full body clearance; feet free; formation readable |
| R05 hook | Strongest readable body pose frame 1 |
| R06 product | Hands hero; face secondary; prop scale exact |
| R07 vlog | Natural path through location; glance to cam optional |
| R08 mood | Minimal move; pose + environment |
| R09 comedy | Hold → reaction body; prop gag timing |
| R10 thriller | Approach/retreat; hide face; reveal turn |
| R11 explain | Stable address to cam; hand demo inserts |
| R12 one-take | Continuous path + seat geography |

---

## 6. AI / factory constraints

| Risk | Blocking fix |
|------|----------------|
| Extra fingers | Fewer complex grips; open hand or simple hold |
| Feet deform | Prefer insert shoes or FS with simple stance; avoid raised complex feet |
| Identity morph | No violent lean/spin on SI2V |
| Prop giant/tiny | Explicit scale; separate insert |
| Glass/mirror | Avoid body through glass complexity |
| Same face spam | Insert/prop/wide geography blocks |

**Prompt still:** include body + hands + prop contact.  
**I2V:** motion of body only — `slow turn of cup, subtle nod, continuous` — not re-outfit.

**QA:**  
- Hands attached and scaled?  
- Eyeline matches partner/window?  
- Prop continuity open/closed?  
- Action matches shot size?  
- SI2V head not thrashing?

---

## 7. Anti-patterns

| ID | Pattern | Fix |
|----|---------|-----|
| BLK1 | Mannequin face CU only | Add hands/prop/geography |
| BLK2 | Gesture too big for CU | Crop out or go MS |
| BLK3 | Eyeline float | Aim at concrete target |
| BLK4 | Prop never contacts hand | Contact or drop prop |
| BLK5 | Cross axis every cut | Hold 180° |
| BLK6 | Stand-up mid si2v line | Split shot or i2v |
| BLK7 | Insert requested → face | Re-block hands only |
| BLK8 | Wet world dry prop | Continuity |

---

## 8. Micro recipes

**Café order (R01):**  
Seated open to partner, cup both hands mid-table, eyeline partner → insert hands turn cup → MCU eyes down (shame) then up.

**Power stand (drama):**  
She stands, he remains seated; she owns upper frame; eyeline down to him; key on her face.

**MV chorus:**  
Step into FS mark, open chest to cam/low angle, arms clear of face, motif prop raised — then hold for lip if si2v.

**Thriller listen:**  
Back 3/4 to cam, ear toward door, hand on handle insert, no face until reveal turn into key.

**Product handoff:**  
Two hands enter lower third, prop center, face soft BG or out; scale reference finger joints.

---

## 9. Integration checklist (full visual stack)

Per shot, agents should be able to answer:

| Layer | Question |
|-------|----------|
| Camera | Size/angle/move/lens? |
| Composition | POI and space? |
| Light | Key side and separation? |
| **Blocking** | **Body path, face, hands, prop?** |

If any blank → incomplete SHOT_DESIGN.

---

## 10. Not in this file

- Full choreography notation (dance pipe doc)  
- Acting method psychology deep dive  
- Lighting fixture plots  
- Composition thirds theory (see composition.md)  
- Set dressing / motif world → **[production_design.md](production_design.md)**  
