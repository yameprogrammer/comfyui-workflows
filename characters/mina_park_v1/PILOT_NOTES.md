# mina_park_v1 — Pilot E2E notes (2026-07-11)

## Run summary

| Step | Result |
|------|--------|
| create (4 masters, pro, seed 10001–10004) | ✅ success |
| approve master | ✅ `s10002__c02` → `approved/master_front.png` |
| expand all_mvp (12 × 1 cand, seed 20001–20012) | ✅ 12/12 |
| approve MVP set | ✅ `missing_mvp=[]`, `status=approved`, `level=L2` |

## Quality assessment (important)

### Worked well
- **Master hero**: clean frontal studio, identity usable
- **Expression sheet**: joy/sad/etc. clearly change while face stays in-family (soft lock OK)
- **Pipeline plumbing**: package paths, meta JSON, presets, approve aliases all worked end-to-end

### Weak / failed intent (expected L2 soft I2I limits)
- **Turnaround angles** (side/back/full body): mostly stayed **upper-body front portraits**. High denoise (0.82–0.85) was not enough to break master composition attractor.
- **Costume full-body**: framing stayed portrait; wardrobe only partially applied (e.g. denim straps vs black tee + jeans).
- **Mole laterality** can flip between frames (feature drift under I2I).

### Implication
L2 Soft Factory is **validated as a tool pipeline**, not as pro-grade multi-view model sheets yet.

### ControlNet turnaround pass (2026-07-11, seeds 30001–30004)
- Command: `character_expand_sheets.py --sheets turnaround --engine controlnet --candidates 1`
- Result: **pipeline OK (4/4)**, **view change NOT OK** — still upper-body portraits; stick-figure edge lines can bleed into face (thin vertical artifacts).
- denoise 0.95 + strength 0.9 retest (`cn_test_side_d95.png`) still portrait.
- Root cause: `I2I-ControlNet-moody` VAEEncodes the face ref as latent base → composition attractor dominates ControlNet pose.

**Next technical steps**
1. Empty-latent (or SD3 empty) + ControlNet pose workflow (identity via prompt/LoRA, not portrait VAEEncode)
2. True full-body master T2I (prompt must say full body, not close-up) as CN source
3. Stronger OpenPose/depth templates if available in Comfy install

## Paths

```text
characters/mina_park_v1/
  approved/master_front.png   # primary
  approved/turn_*.png
  approved/expr_*.png
  approved/costume_*.png
  refs/master|turnaround|expression|costume/
  meta/*.json
  bible.json / manifest.json
```
