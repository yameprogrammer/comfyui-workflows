# Music / SFX captions (not image prompts)

**CLI:** `generate_minimax_music` · `generate_stable_audio` · `generate_bgm`  
**Not:** I2V motion strings. Not Danbooru. Not Krea paragraphs.

---

## MiniMax Music 3 (`--caption` + `--lyrics`)

Caption is **English**, three headings, in this order. Lyrics stay in `--lyrics`.

```text
Global Metadata:
Genre: K-pop emotional acoustic ballad. 84 BPM, A major.
Emotional progression: hushed verse, lift in the pre-chorus, wide chorus, piano outro.
Production: intimate Korean radio mix, close vocal, no rap.

Vocal Details:
Clear Korean female lead, warm mid register, restrained vibrato, close-mic.
Soft stacked harmonies on the chorus only. No rap, no English ad-libs.

Arrangement:
Intro: nylon guitar and quiet piano. Verse: guitar + light keys, kick enters late.
Pre-chorus: pads lift. Chorus: full drums, bass, doubled vocal, wider stereo.
Bridge: strip to piano. Final chorus: extra harmony then fade.
```

A one-line genre string still runs. Expand to this 3-part form before a production take.

| Field | Put here | Not here |
|-------|----------|----------|
| Genre, BPM, key, mood arc, mix | Global Metadata | Lyrics box |
| Lead / harmony / effects (or instrumental only) | Vocal Details | Caption as a movie scene |
| Section-by-section instrument entries | Arrangement | Static equipment list only |
| Words to sing + `[Verse]` `[Chorus]` tags | `--lyrics` | Inside caption |

**Lyrics tags (executable structure):** `[Intro]` `[Verse]` `[Pre-Chorus]` `[Chorus]` `[Post-Chorus]` `[Bridge]` `[Instrumental]` `[Solo]` `[Outro]`. Tags on their own lines. Korean lyric text is fine; do not quote those lines in the caption.

**`--duration` is a ceiling**, not exact length. Song default 180s, BGM 60s, max 300s. If the tagged form is longer than the cap, raise `--duration`.

**Sampler (do not use image CFG):** steps 30, CFG 1.7, euler, simple. `--tiled-decode` auto-on at duration ≥ 240s.

`--mode bgm` → Vocal Details must say instrumental / no vocals.

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
- [ ] Production Music 3 caption has the three headings  
- [ ] `--duration` ≥ expected song length  
