# Wan Animate — motion transfer prompts

**CLI:** `generate_wan_animate2` (no pose extract) · `generate_wan22_animate` (ViTPose path)  
**Not:** `generate_yaw_wan22` I2V (that is `wan22_i2v.md`).

Driving video owns **timing and body**. Still owns **identity**. Prompt owns **look leftovers + background/camera**, not a second choreography.

---

## Wan-Animate-2 (`generate_wan_animate2`)

Split fields. Do not dump one essay into `-p`.

| Flag | Content |
|------|---------|
| `--look` | Appearance only: hair, outfit, species. **No motion verbs.** |
| `--background` | Set + light of the **output** (generated; not copied from still) |
| `--pose-prompt` | One line of what the **drive** is doing (`energetic street dance, background stationary`) |
| `-p` | Full positive only if you are not using the split flags |

```text
--look "pink hair, black racing jacket, silver hoops"
--background "wet neon rooftop at night, magenta and cyan signs, rain"
--pose-prompt "sharp hip-hop choreography, camera locked wide"
```

| DO | DON'T |
|----|--------|
| Short look + short set | Re-describe the dance move-by-move (the video already has it) |
| `background stationary` if you want locked set | Face essay + full MV shot list in `--look` |
| One camera note in pose-prompt | Fight the drive with a different dance in text |

---

## Wan 2.2 Animate (`generate_wan22_animate`)

`-p` optional. Prefer **motion/look notes**, not a new T2I.  
Pose comes from extracted skeleton. Prompt = lighting/set if the plate is empty, or leave blank.

---

## Negative

```text
identity morph, extra limbs, background boil, face melt, wrong dance
```

---

## Gates

- [ ] Look has no verbs of travel/dance (Animate-2)  
- [ ] Pose-prompt is one clause  
- [ ] Not using Krea still paragraph as `-p`  
