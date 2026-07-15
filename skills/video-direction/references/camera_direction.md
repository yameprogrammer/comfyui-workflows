# Camera direction — design guide (agent_custom)

- **Skill:** `video-direction`  
- **Role:** Director / DP camera decisions **before** pixels  
- **Depth:** Practical design (when / why / how), not gear manuals  
- **Research provenance:** [camera_direction_research.md](camera_direction_research.md)  
- **Companion:** short codes in [shot_grammar.md](shot_grammar.md) · prompts in `docs/generation_prompt_craft.md`

**Prime rule:** Every shot is a **motivation package**:  
`size + angle + move(1) + lens_feel + subject + why_this_shot`.  
No “cinematic shot” without those fields.

---

## 0. Decision order (design, don’t shop)

```text
1) INTENT     What should the viewer understand/feel in this cut?
2) SIZE       How much body/world in frame? (coverage job)
3) ANGLE      Power / vulnerability / geometry
4) LENS FEEL  Space vs face compression (storytelling distance)
5) MOVE       ONE primary motion (AI I2V collapses multi-moves)
6) FOCUS      What must be sharp? (optional note)
7) AXIS       Continuous space? keep eyeline/screen direction
8) FORMAT     9:16 vs 16:9 changes vertical real estate
9) RISK       hands / feet / glass / car / text
10) PROMPT    Still: full visual · I2V: motion/camera only
```

If two of {size, angle, lens, move} change wildly on every cut without intent → rhythm noise, not style.

---

## 1. Shot size (subject scale) — design, not labels only

Industry ladder (StudioBinder / film language consensus; codes match factory):

| Code | Frame guide | Story job | Abuse |
|------|-------------|-----------|--------|
| **ELS** | Subject tiny / pure landscape | Scale, loneliness, world rules | Lose character |
| **LS / Wide** | Full body + environment | Geography, relationships in space | Emotion diluted if overused |
| **FS** | Head to toe | Walk, costume, dance silhouette | |
| **MLS** | Knees-up | Performer medium | |
| **MS** | Waist-up | Dialogue default, gesture+face | **3× row ban** |
| **MCU** | Chest-up | Emotional approach | |
| **CU** | Face / object hero | Confession, lip hero | Face-CU spam |
| **ECU** | Eyes, mouth, motif detail | Peak intimacy / texture | Identity melt risk (AI) |
| **Insert** | Prop/detail, often no full face | Time, motif, product, proof | Never replace requested insert with face |
| **POV** | Character optical view | Subjectivity | Anatomy / horizon mess |
| **OTS** | Over-shoulder | Dialogue axis, conflict | Dirty shoulder too big |
| **Two-shot** | Two people | Relationship beat | |

### Size design rules

1. **Coverage first, beauty second** — if the edit cannot cut, hero angles are useless.  
2. **Adjacent cuts:** change size **or** angle (skill R1).  
3. **Chorus / hook event:** often **size jump** (MS→LS or MCU→LS), not more CU.  
4. **Talking shorts:** need ≥1 wide geography + ≥1 insert; not MS wall.  
5. **AI safety:** ECU faces and inserts of hands/feet = high risk → shorter duration, clear action, QA.

---

## 2. Camera angle — psychology + when to use

| Angle | Viewer relation | Use when | Avoid when |
|-------|-----------------|----------|------------|
| **Eye level** | Empathy, parity | Dialogue, service, default | Every shot (flat) |
| **Low** | Power, hero, threat from below | Chorus hero, standing up to rain/city | Random “cool” on soft dialogue |
| **High** | Smallness, surveillance, map | Overwhelm, flood, vulnerability | Accidental laptop-cam look |
| **Dutch / canted** | Unease, intoxication, chaos | Thriller beat, rare | Whole episode (nausea) |
| **Top-down / bird** | Ritual, pattern, feet/water | Motif plates, dance formation | Talking heads |
| **Worm’s-eye** | Extreme low | Epic / horror | Continuous realism talk |
| **Shoulder-level** | Intimate walk-and-talk | One-take feel | |

**Angle is motivation, not decoration.** Write `intent`: “low = she owns the café doorway.”

---

## 3. Camera movement — one primary verb

Consensus move vocabulary (Boords / StudioBinder / DP practice):

| Move | What it does | Story use | AI note |
|------|--------------|-----------|---------|
| **Static / locked** | Observer | Hold, power of cut | Most stable I2V |
| **Push-in (dolly in)** | Intensity, realization | Line land, hook | Prefer **slow** |
| **Pull-out** | Reveal context, isolation | End of scene | |
| **Pan** | Horizontal attention | Follow gesture, space | Horizon level |
| **Tilt** | Vertical reveal | Body→face, building | |
| **Track / truck** | Lateral follow | Walk parallel | |
| **Dolly / follow** | Depth follow | Walk toward/away | |
| **Handheld micro** | Human pulse | Anxiety, doc | Not “earthquake” |
| **Orbit / arc** | 3D glamour | Product, transformation | Rare; AI warp risk |
| **Crane / jib** (feel) | Rise/fall status | Epic open/close | Prompt as “crane up feel” |
| **Zoom** | Optical attention | Intentional 70s/horror | Distinct from dolly; use sparingly |
| **Rack focus** (focus move) | Shift subject | Two-plane story | Still-friendly; I2V hard |

### Move rules (hard for this factory)

1. **One primary move per shot** — multi-move prompts → identity/warp fail.  
2. Move should **serve intent** (closer to feeling ≠ always push-in).  
3. If dialogue lip is hero → prefer **static or micro push**, not orbit.  
4. Dance: favor **clear body read** over fancy orbit unless wide FS.  
5. I2V negative: `warp, morph, flicker, sudden whip, dutch spin`.

---

## 4. Lens feel — storytelling distance (not EXIF)

Full-frame-equivalent *feel* used in prompts and SHOT_DESIGN:

| Feel | Spatial effect | Face | Typical jobs |
|------|----------------|------|--------------|
| **24–28mm** | Big space, stretch edges | Unflattering if too close | Establishing, flood, environment MV, dance full body in room |
| **35–40mm** | “Storyteller” — context + person | Natural medium | Walk, café two-shot, doc, most dialogue MS |
| **50mm** | Neutral perspective | Balanced | Inserts, product, calm singles |
| **85mm** | Compression, isolation | Flattering CU | MCU/CU portraits, lip hero, bokeh night |
| **100–135mm feel** | Strong isolation | Beauty CU | Sparse hero only; AI face melt risk |

### Lens design rules

1. **Closer shot ≠ always longer lens** — wide CU feels invasive; long CU feels admired.  
2. **Don’t leave lens to chance** — Kenworthy / DP practice: director should intend lens class.  
3. **Match adjacent lenses** roughly in continuous dialogue (jump 28→85 only as event).  
4. **9:16 + ultra-wide:** watch edge stretch on faces near frame border.  
5. Prompt language: `35mm look, natural perspective` / `85mm compression, shallow DOF` — not fake EXIF spam.

---

## 5. Focus & depth (optional field `focus_note`)

| Choice | Meaning |
|--------|---------|
| Deep focus | Space readable (wide masters) |
| Shallow | Subject pop (CU, product) |
| Rack (planned) | A sharp → B sharp (still I2I friendly; motion hard) |

AI: shallow is easy to overdo → “soft smear”. Prefer `shallow but eyes sharp` on CU.

---

## 6. Continuity optics (axis & screen direction)

From continuity / coverage teaching (film school + set practice):

| Rule | Practice |
|------|----------|
| **180° line** | Keep cameras on one side of action line for dialogue |
| **Eyeline** | Matching heights for who looks at whom |
| **Screen direction** | Exit right → enter left (or motivate break) |
| **30° / size jump** | If angle change is tiny, change size more (avoid jump-cut twin) |
| **Clean entrances** | Let body complete gesture before cut when possible |

Break 180° only as **event** (disorientation) and note in SHOT_DESIGN.

---

## 7. Coverage design (camera package per beat)

Classic package (compressed for shorts):

```text
A. Master / establishing (LS–FS) — where are we?
B. Medium coverage (MS/MCU) — what happens between people?
C. Close (CU) — what does it cost emotionally?
D. Insert — what object/time proves it?
E. Special — hero angle you waited for (low 24mm, top-down motif…)
```

**Shorts budget:** you may not shoot all five *physically*, but the **edit must still think** A–D.  
Missing B or D is why AI episodes feel like “face slideshow”.

---

## 8. Format: 9:16 vertical camera direction

Contemporary vertical practice (creator + festival vertical tips):

| Topic | Guidance |
|-------|----------|
| **Compose native 9:16** | Prefer true vertical canvas, not lazy center-crop of 16:9 masters for hero work |
| **Vertical real estate** | Height is the feature: standing FS, stacked layers, rain depth |
| **Eye line** | Place dominant eye in upper third; avoid chin-only bottom weight |
| **UI safe** | Keep critical face/motif out of extreme top/bottom UI chrome zones when known |
| **Sideways symmetry** | Not everything centered — left/right tension still works tall |
| **Wide in vertical** | ELS is “tall world”, not letterboxed landscape |
| **Talking distance** | MS often shows sternum-up; leave headroom |

Factory: episode `format` drives work size — camera notes must match.

---

## 9. Genre → camera defaults (with L1 recipes)

| L1 | Size bias | Angle bias | Move bias | Lens bias |
|----|-----------|------------|-----------|-----------|
| R01 talking | MS + insert + 1 wide | eye | static / micro push | 35–50; CU 85 |
| R02 mini-drama | full coverage ladder | motivated | static + 1 push | 35 + 85 |
| R03 MV | size jumps on chorus | low on chorus | push / orbit rare | 24 env + 85 face |
| R04 dance | FS/MLS | eye / top for formation | track, locked wide | 24–35 |
| R05 hook | S01 strongest size | bold angle OK | push-in common | any, readable |
| R06 product | ECU product + hands | top/eye | slow orbit OR static | 50–85 |
| R07 vlog/doc | LS + insert | eye / high map | handheld micro | 35 |
| R08 mood | LS/insert heavy | high/low motif | slow push / still | 24–35 |
| R09 comedy | MS + reaction CU | eye | static (timing) | 35–50 |
| R10 thriller | insert clues late | dutch rare, high | slow push | 35; long for voyeur |
| R11 explain | MS + diagram insert | eye | static | 35–50 |
| R12 one-take feel | evolving sizes | continuous axis | motivated track | single lens family |

---

## 10. AI factory constraints (this repo)

| Constraint | Camera implication |
|------------|-------------------|
| I2V/SI2V short clips | Design **full motion length**; no freeze pad |
| Multi-move prompts fail | **One move** |
| Identity drift | Don’t re-describe face in motion prompt; lock size/angle across si2v chain |
| Anatomy risk | Insert hands/feet = risk tag + careful size |
| Glass/car | Avoid complex reflective geometry unless hero still |
| Moody stills | Strong light+lens language in T2I; then motion-only I2V |

**Still prompt (camera clause example):**  
`medium shot, eye level, 35mm look, shallow environmental depth, locked camera framing`

**I2V prompt example:**  
`slow push-in, subtle breathing, continuous motion throughout, locked eyeline`  
`negative: warp, whip pan, face morph, freeze frame`

---

## 11. SHOT_DESIGN camera block (required fields)

Per shot minimum:

```yaml
shot_id: S03
shot_type: MCU          # size code
angle: eye              # eye|low|high|dutch|top|worm
move: slow_push         # ONE
lens_feel: "85mm"       # 24-28|35-40|50|85|100+
intent: "admission costs her smile"
focus_note: "eyes sharp, background soft"   # optional
axis_note: "keep 180 with S02"                # if continuous
format_note: "9:16 headroom OK"               # if needed
```

Self-audit:

- [ ] 13-thumbnail distinct?  
- [ ] R1–R2 size/angle rhythm?  
- [ ] One move only?  
- [ ] Lens matches intimacy level?  
- [ ] Coverage jobs A–D present in episode?  
- [ ] Vertical framing considered?

---

## 12. Anti-patterns (camera-specific)

| ID | Pattern | Fix |
|----|---------|-----|
| CAM1 | All eye-level MS | Force wide + insert + angle change |
| CAM2 | Orbit on lip line | Static / micro push |
| CAM3 | Ultra-wide CU face | 50–85 feel, step back |
| CAM4 | Dutch whole episode | One beat max |
| CAM5 | Size only changes by crop spam | Redesign intent |
| CAM6 | I2V “cinematic camera moves” soup | One verb |
| CAM7 | 16:9 compose then hope 9:16 | Native vertical intent |
| CAM8 | Hero low angle every chorus of every song | Earn it |

---

## 13. Quick recipes (copy patterns)

**Café confession (R01):**  
S01 LS eye 35 static establish → S02 MS 35 static talk → S03 insert 50 cup → S04 MCU 85 micro-push land line → S05 LS rain window hold.

**MV chorus event (R03):**  
Pre: MCU 85 static → **Chorus: FS low 24 slow push or track** → Insert motif ECU → Back MCU 85.

**Product hero (R06):**  
ECU 50 static texture → hands MLS 35 → product orbit slow 50 (if AI allows) → face MCU 85 reaction once.

**Thriller delay (R10):**  
Insert door handle ECU → high LS empty room → OTS hallway → **reveal** low MS.

---

## 14. What this file is not

- Lighting design (next: `lighting_and_look.md`)  
- **Composition** (POI, thirds, lead room, balance, depth) → **[composition.md](composition.md)**  
- Grip gear lists, sensor crop math  
- Full feature coverage shooting schedule  

Camera direction **stops at motivated optics + framing scale + motion**.  
Composition places mass inside the rectangle; light and set dress complete the image.