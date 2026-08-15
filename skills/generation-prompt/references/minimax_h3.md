# MiniMax H3 video+audio prompts

**CLI:** `generate_minimax_h3` (`--task t2v|i2v|r2v|a2v|polish`)  
**Not:** LTX/Wan I2V dialect blindly pasted. H3 wants **shot + camera + (optional) audio** in one string.

---

## T2V

```text
[subject + action], [setting], [one camera move], [light], [ambient or dialogue in quotes]
```

Length: one shot, 2–5 seconds of events. No 140w still.

---

## I2V

Image owns look. Prompt = what happens + camera.

```text
slow push-in, she turns her head, rain continues, no identity change
```

`--last` frame: prompt = bridge A→B (same as LTX FLF).

---

## R2V (multi-ref)

**Must tag pictures:**

```text
Use <Picture 1> as identity. Use <Picture 2> for wardrobe/style.
She walks through the wet street, locked wide, footsteps.
```

Never leave refs unmentioned.

---

## A2V (audio + face)

```text
[reference generation + audio reference] Use <Picture 1> identity; lips sync <Audio 1>.
Small head motion, camera locked.
```

---

## polish

No creative prompt. Do not invent a new shot description.

---

## Gates

- [ ] Task matches string (T2V has subject; I2V does not re-paint the face)  
- [ ] R2V/A2V use `<Picture n>` / `<Audio n>`  
- [ ] One camera move  
- [ ] Not Krea still paragraph  
