# Sound → picture — audio-driven visual choices

- **Skill:** `video-direction`  
- **Job:** How **speech, music, silence, and SFX** decide shot size, driver, cut points, performance, and mix — *before* generation.  
- **Not:** Full mix engineering, demucs science, or NLE automation (factory audio CLIs).  
- **Factory SSOT:** `docs/audio_motion_production_modes.md` · performance profiles · SI2V length contract  
- **Sibling:** [visual_pacing.md](visual_pacing.md) (time) · genre recipes L0  
- **Research:** [sound_to_picture_research.md](sound_to_picture_research.md)

**Prime rule:** Sound is not “BGM later.”  
**Picture serves the spine of sound** (dialogue, vocal, music section, or deliberate silence).

```text
production_mode  → what the work is (story / MV / hybrid / …)
motion_driver    → what moves this shot (i2v / si2v / still)
mix_policy       → which audio stems win at assemble
picture choices  → size, cut, performance intensity, B-roll vs lip hero
```

---

## 0. Decision order

```text
1) SPINE            dialogue | vocal/music | hybrid | silence/visual-only
2) MODE             production_mode + mix_policy
3) SECTION MAP      if music: intro/v/pre/ch… visual jobs (not lyric slides)
4) PER SHOT SOUND   speech? song? SFX? bed only? mute?
5) DRIVER           si2v if on-screen mouth must track audio; else i2v/still
6) PICTURE ROLE     lip hero | reaction | insert | geography | dance body
7) PERFORMANCE      intensity profile (warm_greeting, neutral_calm…)
8) CUT TO AUDIO     end of phrase, breath, beat accent, drop
9) LENGTH           audio duration → duration_sec / split shots (no freeze pad)
10) MIX NOTE        who ducks whom; clip mute vs bake
```

CREATIVE / episode:

```yaml
audio_spine: dialogue_plus_bgm_under   # dialogue|music_master|hybrid|video_only
production_mode: hybrid
mix_policy: dialogue_priority_bgm_under  # see factory audio doc / aliases
music_sections: null                     # or Intro/V/Ch map for MV
silence_as_tool: true                    # allow mute visual beats
```

SHOT:

```yaml
audio_role: speech|vocal|bed|sfx|silence
motion_driver: si2v|i2v|still
performance: warm_greeting        # if speech/vocal
audio_cut: "end of line"          # optional
driving_note: "tts bind / master slice 0:12-0:18"
```

---

## 1. Emotion / story map (sound → picture)

| Sound situation | Picture bias |
|-----------------|--------------|
| **Intimate confession** | MCU/CU si2v; soft push; insert cup between lines |
| **Bright service talk** | MS si2v; open stance; warm key |
| **Angry / tension line** | Slightly tighter; less smile; hold reaction after line |
| **Song chorus (on-cam vocal)** | Size/motion **event** + si2v lip heroes sparse |
| **Song chorus (no lip)** | Wide/insert event; i2v; music_locked |
| **Instrumental bed only** | Geography, texture, blocking business |
| **Hard silence** | Hold face / empty chair / residual LS — intentional |
| **SFX hit (door, glass)** | Insert or cut on hit; don’t bury in face CU |
| **Laugh / pause** | Comedy hold then reaction cut (visual_pacing) |
| **Breath before reveal** | Stretch shot or still; then size jump |

---

## 2. Spine types

| Spine | Picture obligation |
|-------|-------------------|
| **Dialogue** | Coverage for speech + inserts; si2v on speakers |
| **Music master** | Section visual jobs; cut density may rise on chorus |
| **Hybrid** | Dialogue islands + BGM; never fight vocals with loud bed in design notes |
| **Video only** | Pure visual pacing; optional later SFX |

L0 modes (`M_story`, `M_mv`, `M_hybrid`…) must match spine.

---

## 3. Motion driver from sound (factory-aligned)

| On-screen mouth? | Driver | Picture |
|------------------|--------|---------|
| Speaking / singing to cam or partner | **si2v** | Prefer stable head; micro performance |
| Closed mouth, body/world moves | **i2v** | Motion/camera prompt only |
| Pure hold, no motion needed | **still** | Label intentional; allow_freeze if static |
| VO only (mouth not on screen) | **i2v/still** | B-roll while VO plays — not si2v |

**Not** “si2v = story only.” On-cam vocal in MV is first-class si2v.

---

## 4. Lip hero policy

| Do | Don’t |
|----|--------|
| 1–3 strong lip shots per short | Every emotional line = face CU si2v |
| Match audio_scale / performance profile | Aggressive head thrash |
| Insert between lines for breath | Continuous 40s single si2v without split if audio long |

Performance profiles (factory): `neutral_calm`, `warm_greeting`, `mild_unsatisfied`, `thoughtful`, `cute_ask`, `sip_business`…  
Pick per speech shot; keep motion_prompt lip-aware (don’t still-override speak markers).

---

## 5. Music → picture

| Music moment | Visual |
|--------------|--------|
| Intro | World / motif introduce |
| Verse | Texture, medium, micro performance |
| Pre | Pressure: tighter size or push |
| **Chorus** | **Event** (R6): size/motion/motif jump |
| Bridge | Subtract, breath, residual |
| Outro | Residue or sudden stop |
| Drop / hit | Optional cut or push on accent — not every snare |

**Lyric slideshow ban** remains: jobs not word illustrations.

---

## 6. Cut to audio (direction-level J/L awareness)

| Technique (intent) | Meaning for planning |
|--------------------|----------------------|
| **Cut on phrase end** | Clean dialogue coverage |
| **L-cut feel** | Picture may continue while next line starts (note in assemble; design reaction hold) |
| **J-cut feel** | Hear next line before picture arrives (design incoming shot ready) |
| **Music accent cut** | Optional; don’t metronome entire ep |
| **SFX cut** | Insert on impact |

Full J/L execution is editorial; **shot list must leave room** (reaction tails, lead-ins).

---

## 7. Silence as a tool

| Silence use | Picture |
|-------------|---------|
| Weight after confession | Hold MCU 0.5–1.5s after line (inside clip or still) |
| Comedy beat | Hold setup face |
| Horror | Empty frame + soft ambient only |
| Residual outro | LS rain + no VO |

Don’t fill every gap with BGM design-wise if silence is the emotion.

---

## 8. Length from audio (hard)

```text
speech/vocal duration + tail → shot duration_sec or split S0xa/S0xb
```

- Factory: SI2V frames from audio; **hard fail** if over max without split/clamp policy.  
- Never freeze-pad to match VO.  
- Multi-line monologue → multiple shots with coverage variety.

---

## 9. Mix policy → picture implications

| Mix idea | Picture / plan note |
|----------|---------------------|
| **music_locked** | Master audio timeline; picture follows sections |
| **dialogue priority + BGM under** | Design soft bed; lip shots clean; don’t plan loud diegetic fight |
| **video_only** | No speech spine; pure visual pacing |
| Clip has temp audio | Assemble may mute/rebed — design stems in audio_refs |

Point to factory `audio_motion_production_modes.md` for exact enum names.

---

## 10. L1 × sound defaults

| L1 | Spine bias | Driver mix |
|----|------------|------------|
| R01 talking | dialogue + bed | si2v speak / i2v insert·geo |
| R02 drama | dialogue | si2v + reaction i2v |
| R03 MV | music master | sparse si2v vocal / i2v rest |
| R04 dance | music | i2v body; lip rare |
| R05 hook | any | picture-first 1.5s; sound can lag |
| R06 product | VO or bed | i2v; VO not force si2v if off-cam |
| R07 vlog | VO/talk mix | selective si2v |
| R08 mood | bed / silence | i2v/still |
| R09 comedy | dialogue + pause | hold then cut |
| R10 thriller | sparse SFX + silence | delay then event |
| R11 explain | VO/talk | si2v + insert; captions post |
| R12 one-take | dialogue continuous | chain + si2v segments |

---

## 11. SFX

| SFX | Picture |
|-----|---------|
| Door, cup clink, rain bed | Insert or wide supports diegesis |
| Whoosh spam | Avoid; not a substitute for cut energy |
| Planned sfx in shots.json | Design visible cause when possible |

---

## 12. Factory handoff

| Need | CLI / doc |
|------|-----------|
| Mode/driver/mix | audio_motion_production_modes.md |
| TTS + performance | episode_tts --performance |
| SI2V batch | episode_s2v · length contract |
| Drive prep | audio_prepare_driving / bind |
| Music stem | episode_bgm / audio.bgm |
| Captions | episode_subtitles (not AI type) |
| Status length health | episode_status SHORT/DRIVE_MISMATCH |

Direction fills **audio_role + driver + performance + duration**; ops run CLIs.

---

## 13. AI / QA

| Check | Fail |
|-------|------|
| Speak shot is si2v with driving audio | i2v mouth random |
| Long VO single clip pad | freeze / SHORT flag |
| Chorus without visual event | lyric flat |
| Every line face CU | coverage fail |
| BGM designed to bury dialogue | mix_policy conflict |
| Motion prompt re-describes wardrobe on si2v | identity noise |

---

## 14. Anti-patterns

| ID | Pattern | Fix |
|----|---------|-----|
| SND1 | BGM first, story later | Choose spine first |
| SND2 | si2v on silent B-roll | i2v |
| SND3 | i2v on talking face expecting lips | si2v + drive |
| SND4 | Freeze to match audio | split / longer gen |
| SND5 | Lyric word→image | section jobs |
| SND6 | No silence ever | design mute beats |
| SND7 | Performance still-override on speak | lip-aware profile |
| SND8 | Music_locked but free-timed random shots | section map |

---

## 15. Micro recipes

**Hybrid café 40s:**  
Spine dialogue+bgm under · S02/S04/S07 si2v + performance · inserts i2v between lines · residual silence-leaning LS.

**MV chorus:**  
music_locked · pre MCU short · chorus LS/FS event + 1–2 si2v lip · B-roll i2v on instrumental bars.

**Product VO:**  
off-cam VO · all i2v · cut on phrase ends · captions post.

---

## 16. Stack position

| # | Layer |
|---|--------|
| 1–7 | Picture craft |
| 8 | Visual pacing (time) |
| 9 | VFX / on-image text |
| **10** | **Sound → picture (this file)** |

Gate 0 (mode) + Gate 2–3 (driver, duration, performance) are primary consumers.

---

## 17. Not in this file

- EQ/compression recipes  
- Full stem routing UI  
- Demucs training  
- ADR stage management  
