# Motion video prompts (I2V / SI2V)

Factory: Wan2.2 I2V · InfiniteTalk / LTX SI2V · episode_* batch  
SSOT: `docs/generation_prompt_craft.md` · video-direction camera + sound_to_picture

---

## 1. I2V — image defines scene

Industry (Runway Gen-4 etc.): **prompt = what moves**, not a second portrait.

### Template

```text
[ONE camera move], [body or prop action], continuous motion throughout
```

### Good

```text
slow push-in, subtle breathing, eyes lower then lift toward empty chair, continuous soft motion throughout
```

```text
static camera, fingers slowly rotate ceramic cup a quarter turn, continuous motion throughout
```

```text
locked tripod, rain streaks drift on window glass, subject almost still, continuous throughout
```

### Bad

```text
cinematic beautiful woman in cafe, masterpiece, detailed face, cream blouse, 8k, epic camera
```

### Negatives (default pack)

```text
warp, identity morph, freeze frame, flicker, extra limbs, face melt, whip pan, sudden cut, morphing hands
```

### Rules

1. **One** camera verb (static | slow push-in | pull-out | pan | tilt | track | handheld micro).  
2. Say **continuous / throughout** (anti freeze-pad).  
3. No wardrobe/face paragraph.  
4. 8–40 words.

---

## 2. SI2V — speech-driven

### Template

```text
natural speech mouth motion, [performance micro], [head stability], [optional hands anchor], continuous throughout
```

### By performance (align factory profiles)

| Profile | Motion clause |
|---------|----------------|
| neutral_calm | minimal head motion, soft blink, shoulders still |
| warm_greeting | small smile motion, tiny nod, open shoulders still |
| mild_unsatisfied | micro brow tighten, jaw set, no big lean |
| thoughtful | slight head tilt, eyes shift, still torso |
| cute_ask | soft smile, micro lean forward only |
| sip_business | (prefer i2v) sip action, not full speech |

### Good

```text
natural speech mouth motion, warm micro smile, tiny head nods, hands rest on cup, shoulders almost still, continuous throughout
```

### Bad

```text
walks across cafe while talking, dramatic hair flip, outfit description...
```

### Negatives

```text
closed mouth while talking, big lean, standing up, face morph, freeze pad, desync mouth, warp
```

---

## 3. Multi-model notes (generic, not SSOT)

| Family | Bias |
|--------|------|
| Wan / factory I2V | Short clear motion; one move |
| Kling-like | Body physics + camera plain language |
| Runway I2V | Motion-first; strong keyframe |
| T2V (if ever) | Need full still-like description — not default factory path |

Factory default remains **keyframe still → I2V/SI2V**.

---

## 4. Camera move lexicon (motion prompts)

| Intent | Phrase |
|--------|--------|
| Locked | static camera, locked tripod |
| Intensify | slow push-in, gentle dolly in |
| Reveal | slow pull-out |
| Follow | tracking shot left-to-right, subject paced |
| Unease | handheld micro shake (rare, subtle) |
| Product | slow orbit (rare; warp risk) |

Only **one** per prompt.

---

## 5. Sync with sound_to_picture

- Speech shot → si2v prompt + performance  
- Instrumental B-roll → i2v  
- Duration from audio → don’t pad in prompt (“freeze at end”)  
