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
- Face-source CN: pipeline OK, **portrait lock** (failure). Stick lines can artifact.

### Full-body source CN pass (2026-07-11, seeds 70001–70004) — improved
- Generated clothed full-body master `s60011` → `approved/master_full.png`
- CN from **master_full**:
  - **front**: usable full-body (some pose-template grid lines on clothes)
  - **side**: full-body kept, angle only mild (not true profile)
  - **back**: still mostly front-facing + stick artifacts
- Root cause update: portrait VAEEncode was the main composition killer; full-body source fixes framing. **View angle** still needs better pose maps / higher structural control.

**Next technical steps**
1. Better pose maps (OpenPose/real photo silhouettes) for true side/back
2. Tune denoise/strength per view; optional `controlnet_empty` + LoRA for hard angles
3. Quarantine old failed face-source turnaround files under `refs/turnaround`

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
