# LTX 2.3 video prompts (I2V / FLF / V2V / T2V / audio)

**CLI:** `generate_i2v` (default LTX AIO), `generate_flf2v`, `generate_s2v`, `generate_v2v`,  
`generate_ltx23_latentheart`, `generate_ltx23_redmix_i2v`  
**Also:** Comfy LTX-2.3 docs · LTX open-source I2V guide · Prompt Relay (multi-event)

---

## Research notes (2026-07-17)

| Source | Takeaway |
|--------|----------|
| Comfy LTX-2.3 prompting tips | **Core actions over time** · visual details if needed · **audio** (sounds/dialogue) |
| Official LTX I2V guide | Image owns appearance; prompt = **what comes next** — motion, camera, audio |
| Community guides | Start subject + key action, then camera + mood; chronological |
| Kijai Prompt Relay | Multi-event: segment prompts by time for multi-beat clips |
| Factory A/B | LTX often default quality I2V vs Wan; keep motion discipline |

---

## I2V (primary)

**Image = look identity.** Prompt = temporal behavior.

### Simple (factory 8–40w — preferred for MV single-beat)

```text
[ONE camera move], [body/prop micro-action], continuous motion throughout
```

Same hard rules as shared `motion_video_prompts.md`.

### Chronological (richer LTX dialect)

When the shot needs a short sequence (still one intent):

```text
[0–2s beat]. [2–4s beat]. [camera throughout]. [optional ambient audio].
```

Or single flowing paragraph of **events in order**:

```text
She stands still under the yellow parasol, then slowly lifts her gaze to the right as rain continues;
static medium shot, continuous soft motion, distant rain ambience.
```

**Do not** re-list face shape, freckles, full wardrobe (already in frame).

### Official-style focus

1. Core actions as they occur  
2. Only visual details that **change** or must be emphasized  
3. Audio if backend uses it: `"dialogue in quotes"`, soft rain, footsteps  

---

## FLF (first–last frame)

Prompt = **bridge motion** from A→B, not a third composition.

```text
smooth transition, [how pose/camera interpolates], continuous, no teleport, keep identity
```

Avoid inventing new characters mid-bridge.

---

## V2V

```text
[what changes: pace / weather density / performance energy], keep composition and identity, continuous
```

---

## T2V (no still)

Closer to full scene caption + motion (longer OK). Still one primary action thread.

```text
[subject + setting], [action over time], [camera], [light], [audio if any]
```

---

## Multi-event (Prompt Relay / long clips)

If using timed segments:

| Segment | Prompt |
|---------|--------|
| 0–2s | hold + micro breath |
| 2–5s | head turn right |
| 5–8s | slow push-in |

Factory default MV shots: **prefer single-beat** unless user asks multi-event.

---

## SI2V pointer

Speech-driven: use `motion_video_prompts.md` §SI2V — mouth + micro performance only.  
Audio is driver; don’t fight lips with “closed mouth smile” unless intentional mute.

---

## Negatives

```text
warp, identity morph, freeze frame, flicker, extra limbs, face melt, whip pan, sudden cut
```

---

## Gates

FAIL if:

- [ ] Full still-prompt paste into I2V  
- [ ] Multiple competing story beats without time structure  
- [ ] No motion verbs  
- [ ] Camera + run + orbit + whip all at once  
- [ ] FLF without bridge language  
