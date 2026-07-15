# Factory handoff map

## Artifacts

| Artifact | Path |
|----------|------|
| Creative Pack | `stories/<ep>/CREATIVE.md` |
| Shot design | `stories/<ep>/SHOT_DESIGN.md` |
| Machine shots | `stories/<ep>/shots.json` |
| Keyframes | `stories/<ep>/keyframes/Sxx.png` |
| QA packs | `stories/<ep>/boards/qa/` |
| Visual QA JSON | `stories/<ep>/meta/visual_qa/` |
| Work clips | `stories/<ep>/clips/work/` |
| QA log | `stories/<ep>/QA_LOG.md` |

## CLI order (minimal)

```text
skill equipped
→ CREATIVE + SHOT_DESIGN
→ assets (char/loc/look) approved
→ shot_compose
→ shot_qa_pack → open → shot_qa_record → shot_approve
→ episode_identity_sheet (3+ kf)
→ episode_tts / bind (if si2v)
→ episode_i2v | episode_s2v   # freeze gate ON
→ shot_qa_record clip → shot_approve --clip
→ assemble_video
→ export_episode_to_workspace
```

## Exit codes agents must respect

| Code | Meaning |
|------|---------|
| 22 | clip gate / assemble unapproved |
| 23 | visual QA missing/fail on approve |
| freeze fail | post-gen FREEZE_PAD_SUSPECT |

## Tool split (Rule 8)

| Job | Tool |
|-----|------|
| Concept stills | Grok image_gen OK |
| Surgical still fix | image_edit or shot_keyframe_edit |
| Production keyframe | shot_compose |
| Lips | episode_s2v only |
| Preview motion | native video optional; not assemble |
| Deliver | factory assemble + upscale + export |
