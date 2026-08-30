# MiniMax H3 video+audio prompts

**CLI:** `generate_minimax_h3` (`--task t2v|i2v|r2v|flf|a2v|polish`)  
**Not:** LTX/Wan I2V dialect, Krea still paragraphs, or a one-line tag soup.

H3 was trained on a **labeled three-field prompt**. Local open weights do **not** run MiniMax Context-IR, so the agent writes this shape. A/B 2026-08-30 (elf checkout I2VA, same seed): official fields beat the short line on blocking, SFX count, and speaker eyeline. Dialogue text tied.

Do **not** load the Omni Prompt-Rewriter LoRA in the H3 graph on the 4090 (evicts DiT; invents BGM/cuts). Rewrite in this file, then `generate_minimax_h3`.

---

## Shared body (every T2V / I2V / FLF)

```text
integrated_multimodal_description: [Shot 1] <style>, <framing>. <camera with amplitude/speed>. <who is where>. <one action chain>. <speaker>: <d>[Korean] line.</d>
overall_soundscape: <ambience, one action sound, voices as written>
non_diegetic_music: N/A
```

- `[Shot 1]` has **no** timestamp. Later shots only if a cut is wanted: `[Shot 2] At 00:03.000, the camera cuts to …`
- One camera move. Locked hold: `locked tripod, no zoom, no dolly, no push-in, framing stays identical`.
- Speakers: `(S1)` / `(S2)`. Dialogue **only** inside `<d>[Korean] …</d>` (not `[한국어]`).
- Talking-head / no score: `non_diegetic_music: N/A` (blank ≠ off).
- Image owns look on I2V — do not re-essay face or wardrobe; say `preserve … from <Picture 1>`.

### Alignment line (first line + blank line, then the three fields)

| Task | First line |
|------|------------|
| T2V | *(none)* |
| I2V | `For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.` |
| FLF | `How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot N) aligns with the S.SS-second mark of the target video.` |
| last-only | Picture 1 aligns with the **end** mark, not 0.00 |

`S.SS` = H3 snapped duration (5s → ~5.17). FLF with **the same PNG** as first and last = zoom bulge. Use I2V for a hold.

---

## T2V

No alignment line. Open `[Shot 1]` with style + who + where + action + camera.

---

## I2V

Alignment line, then fields. Image is t=0. Prompt = motion + camera + sound + who speaks.

---

## R2V (multi-ref)

Ref2VA wants **six** sections when identity/motion/voice refs are attached. Minimum the agent must still do: name every `<Picture n>` / `<Video n>` / `<Audio n>` and its **one job**.

```text
subject_definitions: <Subject 1> is the person in <Picture 1>; preserve face, hair, outfit.
summary: [reference generation] S1 performs the action in the store from <Picture 1>.
retention_analysis: <Subject 1> (appears in [Shot 1]): fully_preserved - face, hair, wardrobe
detailed_description: [Shot 1] …
overall_soundscape: …
non_diegetic_music: N/A
```

R2V `-a` = **timbre only**. H3 still speaks the `<d>` line. Not a wav mux.

### V2V edit (motion plate)

`--ref-video plate.mp4` + identity still. `<Video 1>` = camera/motion/environment; `<Picture 1>` = who/what to swap. CLI resamples the plate to **24 fps**, trims to H3 length, letterboxes to the generation canvas. Omit `--duration` to follow the plate (capped 15s).

Complex actions must be restated in `detailed_description` even if they are in the plate. Source and output length must agree or the end of the action is dropped.

```text
subject_definitions: <Subject 1> is the person in <Picture 1>; preserve face, hair, outfit.
summary: [video editing] Replace the performer in <Video 1> with Subject 1; keep camera, pacing, and background.
retention_analysis: <Video 1> fully_preserved - camera path, timing, environment. <Subject 1> fully_preserved - identity.
detailed_description: [Shot 1] Subject 1 performs the same action chain as <Video 1>: …
overall_soundscape: match the physical action sounds of <Video 1>
non_diegetic_music: N/A
```

### Carry look (same room, next clip)

`--carry-from clip_a.mp4` takes the last **22 frames** (~0.9s, H3 grid) of clip A, silent, as `<Video 1>`. Pick a well-lit, readable tail — not a face in shadow or a whip pan. This is **not** FLF same-PNG (that zooms). Soundtrack does not carry.

```text
subject_definitions: <Subject 1> is <Picture 1>.
summary: [video editing] Same store as <Video 1>. Subject 1 walks from the counter to the right-hand shelves.
retention_analysis: <Video 1> fully_preserved - room layout, POS, window, shelves. <Subject 1> fully_preserved - identity.
detailed_description: [Shot 1] Hold the opening framing of <Video 1> for a beat (weight shift only), then Subject 1 turns and walks to the shelves. Locked-off or one motivated camera move. Do not rebuild the room.
overall_soundscape: quiet store, footsteps
non_diegetic_music: N/A
```

### Contact sheet (3-view still, not video)

Opt-in scout. Does **not** replace `character_full_sheet` / Qwen turnaround. Do **not** install toobusy. `--ref-image face.png --ref-image outfit.png` (order = Picture 1, Picture 2) + `--ref-image-size max`. Outfit still: mannequin or flat-lay — a worn-on donor body leaks into Subject 1. Pose photos as extra refs bleed; describe the pose in text instead.

```text
subject_definitions: <Subject 1> is the person in <Picture 1>; preserve face, age, skin, hair, and body build from <Picture 1>. <Picture 2> is outfit only — colors, materials, footwear, wearable accessories. Do not copy the outfit donor's face, age, gender, or body.
summary: [reference generation] One static still, not a video. One turnaround contact sheet of Subject 1 wearing the <Picture 2> costume.
retention_analysis: <Picture 1> fully_preserved - identity and body. <Picture 2> fully_preserved - costume design only. <Subject 1> partially_preserved - same person in every cell; pose changes per panel.
detailed_description: The target is one still image, not a video. Exactly three equal vertical photographs left to right on a neutral light-grey studio background. Photo 1: complete full-body front, relaxed A-pose, head and feet visible. Photo 2: complete full-body strict 90-degree right-side view. Photo 3: complete full-body back view. Same identity, body, costume, scale, ground line, and lighting in all three. No extra panel, no merged cells, no captions, no logos, no extra people, no motion.
overall_soundscape: silence
non_diegetic_music: N/A
```

Helper: `lib.minimax_h3_runner.build_contact_sheet_prompt`. Extra body/framing notes go in `extra=`. Take the first decoded frame of the clip as the sheet. `--duration 0.2` snaps to **5 frames**; `0.3` snaps to 22.

---

## A2V (audio + face)

Unofficial Deno mux. **Host talking-head banned.** If used at all (MV experiment):

```text
[reference generation + audio reference] Use <Picture 1> identity; lips sync <Audio 1>.
Small head motion, camera locked.
```

---

## polish

No creative prompt.

---

## Gates

- [ ] Three field names present (except banned A2V mux / polish)
- [ ] I2V/FLF starts with the alignment sentence
- [ ] R2V tags every `<Picture n>` / `<Video n>` + one role each
- [ ] Contact sheet: Picture 1 identity/body, Picture 2 outfit only; "still, not a video"; three named panels
- [ ] One camera move; holds use positive lock language
- [ ] Dialogue in `<d>[Korean] …</d>` with a named speaker
- [ ] `non_diegetic_music: N/A` when no score
- [ ] Not a Krea still paragraph
