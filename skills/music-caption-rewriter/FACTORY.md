# Factory overlay

Upstream: [MiniMax-AI/MiniMax-Music3](https://github.com/MiniMax-AI/MiniMax-Music3) `skills/music-caption-rewriter` at `945655064d59b98004dd70002e7eb5c8c6e11373` (2026-08-14). That repo publishes no LICENSE file. This copy is the text skill only (router, 18 family indexes, 1,000 templates).

Factory SSOT: `skills/music-caption-rewriter/`. Agents working in this toolbox discover it here:

```bash
python scripts/skill_equip.py list
python scripts/skill_equip.py install music-caption-rewriter --target all
```

Follow `SKILL.md`. Read the genre router, then one family index (a second only for an explicit fusion), then at most three template files. Do not scan the template folder.

The skill writes the caption. `generate_minimax_music` renders the audio. Put the finished file outside this repo (`-o` or `AGENT_WORKSPACE`).
