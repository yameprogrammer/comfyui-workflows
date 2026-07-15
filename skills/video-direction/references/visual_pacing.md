# Visual pacing — time, rhythm, cut energy

- **Skill:** `video-direction`  
- **Job:** How the **image changes over time** — shot lengths, peaks, holds, motif return, sync with speech/music.  
- **Not:** Full NLE craft, transition plugin catalogs, loudness mix (factory assemble).  
- **Already related:** R1–R6 size rhythm · SIZE RHYTHM line · freeze ban · genre hooks · motif introduce/vary/payoff  
- **Research:** [visual_pacing_research.md](visual_pacing_research.md)

**Prime rule:** Duration is a **design choice**, not a leftover.  
Every shot has a **job + length + energy**. Padding with freeze is banned.

```text
Picture craft (layers 1–7) = what one frame feels like
Visual pacing (this file)  = how the sequence of frames feels over time
```

---

## 0. Decision order

```text
1) TOTAL LENGTH     target seconds (platform)
2) BEAT BUDGET      ~1 visual beat / 2–4s (skill story_craft)
3) ENERGY CURVE     open → build → peak → release (or hook-first)
4) PEAK PLACEMENT   where is the visual event? (chorus / confession / product)
5) SHOT LENGTH MAP  short/medium/hold per shot
6) SIZE RHYTHM      implement R1–R6 over time (not only adjacency)
7) AUDIO ALIGN      speech ends, BGM swell, silence — visual event optional
8) MOTIF TIMING     introduce / vary / payoff spacing
9) STILL vs MOTION  intentional hold labeled; no freeze pad
10) SPLIT IF NEEDED full-length gen per duration_sec
11) SOUND SPINE     align with sound_to_picture.md (driver, phrase cuts)
```

Deep audio→picture: **[sound_to_picture.md](sound_to_picture.md)**.

CREATIVE / episode:

```yaml
target_duration_sec: 40
pacing_curve: hook_build_peak_residual
# hook_build_peak_residual | slow_burn | comedy_hold_punch | mv_section_map | one_take_flow
peak_at_sec: 28
hook_sec: 1.5
avg_shot_sec_hint: 3.5–5
```

SHOT_DESIGN header:

```text
PACING: hook 0–3 | build 3–24 | peak 24–34 | residual 34–40
SIZE RHYTHM: LS → MS → Insert → …
```

Per shot: `duration_sec` is mandatory (already). Optional:

```yaml
energy: low|mid|high|peak|residual
cut_reason: "end of line" | "motif insert" | "geography breath"
```

---

## 1. Emotion map (time feel)

| Feel | Pacing levers |
|------|----------------|
| **Urgency / anxiety** | Shorter shots, quicker size jumps, less hold |
| **Calm / melancholy** | Longer holds, fewer cuts, slow push only |
| **Comedy** | Hold on setup → cut on reaction; don’t rush punch |
| **Romance / intimacy** | Medium holds, slow push, delay cut after look |
| **Power / hero** | Build then **longer or bigger** peak shot |
| **Mystery** | Withhold insert; late reveal; stretch before turn |
| **Hook / scroll** | Max energy first 1–2s; clarity over beauty |
| **Exhaustion / residual** | Final short quiet hold (intentional still ok if labeled) |

---

## 2. Core tools

### 2.1 Beat budget

- ~**1 visual beat per 2–4 seconds** (short-form story_craft).  
- 40s → roughly **10–16 beats max**; fewer is fine if holds are intentional.  
- 9 shots @ ~40s → ~4.4s average — healthy for hybrid talk.

### 2.2 Shot length classes

| Class | Seconds (hint) | Use |
|-------|----------------|-----|
| **Flash** | 1–2 | Hook fragment, reaction accent |
| **Short** | 2–3.5 | Insert, ECU motif, breath |
| **Medium** | 3.5–6 | Default talk / action unit |
| **Hold** | 6–10 | Mood, one-take segment, careful AI length |
| **Long** | 10+ | True long take; split for AI models if needed |

Hints, not laws — dialogue audio may force si2v length (factory length contract).

### 2.3 Energy curve templates

| Curve id | Shape | L1 fit |
|----------|-------|--------|
| `hook_build_peak_residual` | high open → mid → peak → soft end | R01, R05, R02 |
| `slow_burn` | low → gradual → late peak | R08, R10 |
| `comedy_hold_punch` | hold → snap cut → tag | R09 |
| `mv_section_map` | section jobs; chorus peak density | R03 |
| `product_reveal` | problem → demo → hero hold → CTA | R06 |
| `one_take_flow` | continuous energy, soft peaks | R12 |
| `edu_list` | hook → point×N equal-ish → CTA | R11 |

### 2.4 Peak / event

Visual peak = **R6** (size↑ or motion↑ or motif payoff) and/or performance peak.  
Place peak **before** final residual (peak-end memory: peak + end both matter).

### 2.5 Breath / valley

After dense talk or chorus, insert **geography or prop breath** (short LS/insert) so viewer resets.  
Valley is designed, not “I ran out of ideas.”

### 2.6 Motif timing

| Stage | Timing sense |
|-------|----------------|
| Introduce | Early (first 20–30%) |
| Vary | Mid |
| Payoff | Near peak or residual |
| Avoid | Same motif every single cut (spam) |

### 2.7 Cut motivation (director, not only editor)

Prefer cuts that change **information or emotion**:

- New size/angle (coverage)  
- End of speech unit  
- Prop truth insert  
- Eyeline / look off  
- Music accent (if music-led)  

Avoid cut only because “3 seconds passed.”

### 2.8 Intentional still vs freeze pad

| Allowed | Banned |
|---------|--------|
| `motion_driver=still` + labeled hold | Short I2V + clone pad to fake length |
| Outro residual 1 hold | Every shot freezes last 40% |
| Performance pause inside continuous clip | tpad to match dialogue without regen |

### 2.9 Audio alignment (direction level)

| Audio | Visual option |
|-------|----------------|
| Line ends | Cut or micro push settle |
| BGM drop / chorus in | Size/motion event |
| Silence | Hold face or empty chair |
| SI2V long line | Split S0xa/S0xb full motion each |

---

## 3. Platform / length priors

| Context | Hint |
|---------|------|
| 15–30s social | Strong hook; fewer shots; faster average |
| ~40–60s hybrid talk | 8–12 shots; medium avg |
| MV to track | Section map owns pacing, not arbitrary ASL |
| One-take feel | Fewer cuts; length inside shot via camera/subject |

Vertical scroll: **first 1–1.5s** = highest risk of swipe — spend a dedicated short/LS or strong POI (R05 module).

---

## 4. L1 pacing defaults

| L1 | Curve | Avg length bias |
|----|-------|-----------------|
| R01 talking | hook_build_peak_residual | medium talk, short inserts |
| R02 drama | slow_burn or hook_build | medium; hold on turn |
| R03 MV | mv_section_map | chorus denser/shorter or bigger event |
| R04 dance | phrase / 8-count | phrase-aligned lengths |
| R05 hook | hook first | flash–short open |
| R06 product | product_reveal | short problem, hold product |
| R07 vlog | loose | mixed; don’t metronome |
| R08 mood | slow_burn | holds longer |
| R09 comedy | comedy_hold_punch | hold then snap |
| R10 thriller | slow_burn + late peak | stretch before reveal |
| R11 explain | edu_list | even points |
| R12 one-take | one_take_flow | long segments, few cuts |

---

## 5. Relationship to SIZE RHYTHM

SIZE RHYTHM is **spatial** rhythm over the timeline.  
Visual pacing also assigns **seconds** and **energy**.

Bad: great size variety but all 8s → soggy.  
Bad: snappy lengths but all MS → flat.  
Good: size **and** duration both curve toward peak.

---

## 6. AI / factory

| Constraint | Pacing response |
|------------|-----------------|
| Model max clip length | Split beats; never freeze pad |
| SI2V audio length | frames from audio contract; split dialogue |
| I2V cost | Don’t overcut into 1s spam if identity suffers |
| Approve per clip | Each duration must be watchable full motion |

**QA pacing:**

- [ ] Sum(duration) ≈ target?  
- [ ] Hook < 2s has clear POI?  
- [ ] Peak not last frame only?  
- [ ] Residual exists or hard stop intentional?  
- [ ] Any shot longer than content justifies?  
- [ ] No planned freeze pad?  

---

## 7. Anti-patterns

| ID | Pattern | Fix |
|----|---------|-----|
| PAC1 | Metronome equal lengths | Vary short/medium/hold |
| PAC2 | Peak at end then hard cut out | Add residual or end on peak image |
| PAC3 | Hook buried at 5s | Move event to 0–1.5s |
| PAC4 | Freeze pad | Regen full length / split |
| PAC5 | All high energy | Design valleys |
| PAC6 | Cut mid-word without intent | Align to phrase |
| PAC7 | Motif every cut | Space introduce/vary/payoff |
| PAC8 | 12 identical 3s faces | Size rhythm + inserts |

---

## 8. Micro recipes

**40s rain café hybrid (R01):**  
0–3 LS hook → 5–6s talk → 3s insert → 6s MCU → 3s high breath → 3s OTS → 5s MCU peak → 3s ECU → 3s residual LS.  
Curve: `hook_build_peak_residual`, peak ~S07.

**15s product:**  
1.5s problem flash → 4s demo hands → 5s product hold → 4s CTA face/pack.  
Curve: `product_reveal`.

**MV chorus entry:**  
Pre last shot short MCU → chorus open **longer or wider** event → density of inserts up for 8–12s → verse lengthens again.

---

## 9. SHOT_DESIGN checklist

- [ ] target_duration + pacing_curve set  
- [ ] SIZE RHYTHM + duration column filled  
- [ ] Peak shot identified  
- [ ] Hook shot ≤ ~2–3s or justified hold  
- [ ] At least one valley/breath if >25s  
- [ ] Motif timing not spam  
- [ ] SI2V lengths vs audio feasible  
- [ ] R1–R6 still pass  

---

## 10. Stack position

| # | Layer |
|---|--------|
| 1–7 | Single-image craft |
| **8** | **Visual pacing (time)** |

Gate 2 (beats) + Gate 3 (durations) are the main consumers of this file.

---

## 11. Not in this file

- Premiere/Resolve how-to  
- Transition plugin lists  
- Full sound design  
- Frame-accurate score to picture (music department depth)  
