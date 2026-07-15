# Anti-patterns (instant redesign / reject)

From factory failure notes + community AI video fails + director skill hard bans.

| ID | Pattern | Fix |
|----|---------|-----|
| AP1 | Lyric/dialogue slideshow | Metaphor + motif; mute test |
| AP2 | Face CU spam / same framing | Size rhythm; insert/wide quota |
| AP3 | Triple identical shot_type | Change size or angle |
| AP4 | Freeze pad / tpad clone | Full-length regen or split shot |
| AP5 | Insert request → face result | Lock insert framing in prompt + QA fail |
| AP6 | Mass approve w/o open | shot_qa_pack + record (exit 23) |
| AP7 | I2V re-describes wardrobe/face | Motion-only prompt |
| AP8 | Cast drift across shots | identity sheet + approved refs |
| AP9 | Anatomy feet/hands collapse | risk tag + regenerate |
| AP10 | Car/glass/mirror nonsense | risk clause + reject |
| AP11 | Chorus without visual event | Force R6 jump |
| AP12 | Generate before CREATIVE/SHOT_DESIGN | Return to Gate 1–3 |

On user rejection or QA fail:

```bash
python scripts/failure_note.py add --stage ... --tags ... \
  --symptom "..." --cause "..." --fix "..." --prevention "..."
```
