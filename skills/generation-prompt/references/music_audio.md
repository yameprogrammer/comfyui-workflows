# Music / SFX captions (not image prompts)

**CLI:** `generate_minimax_music` · `generate_stable_audio` · `generate_bgm`  
**Not:** I2V motion strings. Not Danbooru. Not Krea paragraphs.

---

## MiniMax Music 3 (`--caption` + optional `--lyrics`)

Caption = **genre + vocal + arrangement**, not a movie scene.

```text
K-Pop, mid-tempo emotional ballad, female vocal, warm acoustic guitar and piano,
tight modern chorus, 90 BPM, radio mix, no rap
```

| DO | DON'T |
|----|--------|
| Genre, BPM, instruments, vocal sex/tone | `cinematic masterpiece, 8k, a woman stands in rain` |
| Lyrics in `--lyrics` (structure `[Verse]` `[Chorus]`) | Put full lyrics inside caption |
| `--mode bgm` for no vocal | Ask Music 3 to lock a MIDI melody (it will not) |

---

## Stable Audio 3 (`--prompt`)

**instrumental**
```text
Emotional solo grand piano, neo-classical, intimate room, 80 BPM, no drums, no vocal
```

**sfx** (`--mode sfx`)
```text
Close thunder crack then rain on metal roof, stereo, 3 seconds, no music
```

Name **source + space + duration feel**. Ban visual adjectives (`beautiful`, `4k`).

---

## ACE-Step / `generate_bgm`

Same as instrumental caption: style, mood, instruments, BPM. Short.

---

## Gates

- [ ] No photoreal still language  
- [ ] Vocal vs instrumental vs SFX matches CLI/mode  
- [ ] Lyrics not stuffed into caption  
