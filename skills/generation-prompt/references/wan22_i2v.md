# Wan 2.2 I2V / T2V motion prompts

**CLI:** `generate_yaw_wan22`, Wan paths via `generate_i2v` when backend=wan  
**Also:** `motion_video_prompts.md` (shared rules) · `docs/wan22_i2v_speed_research.md`

---

## Research notes (2026-07-17)

| Source | Takeaway |
|--------|----------|
| Wan 2.2 creator guides (InstaSD, wan27.org, VEED, Segmind) | Video-trained: understands **motion, camera, sequence**; lead with what matters |
| Structure | **Subject → Action/Motion → Camera → Scene/Lighting** (T2V); I2V = motion+camera first (image owns look) |
| Camera | First-class: `static camera`, `slow dolly in`, `medium shot`, `no pan no zoom` |
| Motion modifiers | slowly/gradually; head turns; glances; continuous |
| Community | One clear camera intent; competing moves → chaos; I2V: animate only what’s in the image |

---

## I2V dialect (factory default for Wan keyframe→clip)

Image already has face, wardrobe, set. Prompt = **what happens**.

```text
[primary subject motion], [ONE camera move], [env micro-motion], continuous throughout
```

**Length:** 8–40 words typical; up to ~60 if one sequence is clear.  
**Order tip:** motion verb early; camera explicit; end with continuous/stability.

### Good

```text
slow push-in, she blinks and shifts gaze slightly right, subtle breathing, continuous soft motion throughout
```

```text
static camera eye level, rain beads drip from yellow parasol edge onto sneaker toe, continuous throughout
```

```text
steady walk away from camera three-quarter back, gentle track following, puddle reflections, continuous
```

### Bad

```text
beautiful cinematic Korean woman cream cardigan freckles masterpiece 8k detailed face cafe rainy mood
```

---

## T2V dialect (no image / green T2V switch)

Longer structured caption OK (~80–120 words community tip):

```text
[subject], [action over time], [camera size/move], [setting], [light], [pace]
```

Still **one primary action thread** — not a full short film.

---

## Camera lexicon (Wan-friendly)

| Intent | Phrases |
|--------|---------|
| Locked | `static camera`, `locked tripod`, `no pan no zoom no orbit` |
| Push | `slow push-in`, `gentle dolly in` |
| Pull | `slow pull-back`, `dolly out` |
| Lateral | `gentle track left`, `lateral follow` |
| Orbit | `slow orbit clockwise` (harder — use sparingly) |
| Handheld | `subtle handheld micro-shake` (can destabilize faces) |

**One move only** per shot (video-direction camera rule).

---

## Motion lexicon

| Speed | Body | Env |
|-------|------|-----|
| slowly, gradually, subtle | blinks, head turns, breathing, walks, steps | rain streaks, puddle ripple, hair drift, cloth settle |

Avoid abstract: `dynamic energy`, `epic motion`.

---

## Negatives

```text
warp, identity morph, freeze frame, flicker, extra limbs, face melt, whip pan, sudden cut, morphing hands, teleport
```

---

## Gates

FAIL if:

- [ ] Face/wardrobe full re-description on I2V  
- [ ] More than one primary camera move  
- [ ] No continuous/throughout (freeze-pad risk)  
- [ ] Empty “cinematic motion” only  
- [ ] Motions that require objects not in the keyframe  
