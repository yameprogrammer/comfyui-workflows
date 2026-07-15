# SHOT_DESIGN field → prompt clause map

| SHOT / Theme field | Still clause | I2V / SI2V |
|--------------------|--------------|------------|
| action | ACTION block | micro action only |
| blocking | stance, hands contact, eyeline target | same if motion |
| composition | thirds, lead room, FG | usually omit (in keyframe) |
| lighting | full light sentence | omit (in keyframe) |
| world | 2–4 anchors | omit or rain continuous |
| chm | wardrobe + hair state + MU | **omit** on motion |
| materials_hero / materials | materials list | omit |
| optical_feel | short end tag | omit |
| angle / shot_type / lens | CAMERA block | move only if changing |
| move | static for still | **the** motion verb |
| risk | constraint clause | negative extras |
| performance | expression soft in still | SI2V micro pack |
| audio_role=speech | mouth relaxed/smile ready | **si2v** speech motion |
| vfx | rain streaks etc. | continuous rain, no new flare spam |
| intent | do not paste abstract; convert to visible | — |
| emotion_feel | convert to face/body visible | micro expression motion |

## Assembly algorithm

1. Read all non-empty fields.  
2. Still: walk template slots; skip empty.  
3. Motion: keep only move + action + continuous + performance.  
4. Run quality gates.  
5. Emit PROMPT_PACK.  
