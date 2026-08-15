# Camera-move / idle / dance-ref prompts

**CLI:** `generate_camera_move` · `generate_idle_loop` · `generate_dance_ref` · `generate_i2v --motion-preset` · `episode_i2v --motion-preset`  
**Backends:** same as I2V (default LTX). Still image owns look.

---

## Dialect

**Preset first.** Do not rewrite a 140w still as motion.

```bash
python scripts/generate_camera_move.py -i key.png --preset push_in --extra "hair drifts, rain continuous" -o clip.mp4
```

`--extra` / `-p` = **additional action only** (prop, weather, body micro).  
Never face beauty, wardrobe list, masterpiece.

| DO | DON'T |
|----|--------|
| `--list-presets` then pick one id | Invent a second camera move that fights the preset |
| extra: `hair drift, puddle ripple` | extra: full character essay |
| idle for locked life | idle + `orbit` + `push-in` |

---

## Extra template

```text
[one body/prop beat], continuous, no warp
```

If extra is empty, preset language is enough.

---

## Dance ref (`generate_dance_ref`)

Prompt (if any) = **what the reference dance should show**, not identity.  
Identity still = `-i`. Motion = video / preset.

---

## Idle loop

Treat as `idle` preset: breathing, micro face, **camera locked**. No travel.

---

## Gates

- [ ] A preset id was chosen (unless listing)  
- [ ] Extra has no face/wardrobe re-essay  
- [ ] One camera family only  
- [ ] Dialect of the **I2V backend** still applies (LTX time / Wan camera lexicon)  
