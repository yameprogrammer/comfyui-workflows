# SHOT_DESIGN — skill_dryrun_rain_cafe_v1

## Recipe

```yaml
L0: M_hybrid
L1: R01
L2: [mod_insert_prop, mod_motif_trinity, mod_scroll_hook_1_5s]
```

## SIZE RHYTHM

```text
S01 LS → S02 MS → S03 Insert → S04 MCU → S05 LS → S06 OTS → S07 MCU → S08 ECU → S09 LS
```

## Visual Theme

```yaml
look_id: cinematic_moody_v1
palette: [warm wood amber, cool cyan glass, ceramic white, soft yellow straw]
lighting: soft warm key cam-left (lamp), cool window fill, neon rim optional
lens: 35 story / 50 insert / 85 face
film_look: clean digital light grain
motion_language: locked or slow push only
skin_policy: natural
```

## Beats (Gate 2) — ~40s

| Beat | t | Visual job | Motif |
|------|---|------------|-------|
| B0 | 0–3s | World + empty chair (hook) | rain, chair |
| B1 | 3–9s | Soft greeting / I’m fine | face |
| B2 | 9–13s | Prop truth (hands) | cup |
| B3 | 13–20s | Confession line 1 | cup+eyes |
| B4 | 20–24s | Geography breath | rain |
| B5 | 24–28s | Toward empty seat | chair |
| B6 | 28–34s | Smile crack line 2 | face |
| B7 | 34–37s | Condensation residue | cup |
| B8 | 37–40s | Weather residual | rain+chair |

## Shots

| id | dur | size | angle | move | lens | intent (camera) | composition | lighting | blocking | world/prop | action | risk | driver |
|----|-----|------|-------|------|------|-----------------|-------------|----------|----------|------------|--------|------|--------|
| S01 | 3.0 | LS | eye | static | 35 | establish world + hook emptiness | vertical stack; figure lower-third; huge rain glass neg space upper | cool window dominant + warm practical mid | alone at table; open seat left; eyeline to window then down | café LS anchors; empty chair; rain glass | sits still, slight breath, glance window | glass | i2v |
| S02 | 5.5 | MS | eye | static | 35 | trust talk; hospitality face | center-soft thirds; headroom tight 9:16; lead room none (to-cam) | soft warm key cam-left, gentle fill, face open | open stance to cam; hands on cup mid-table | cup full, straw straight | speaks greeting smile; micro nod | — | si2v |
| S03 | 3.5 | Insert | eye | static | 50 | motif hands truth | POI cup center-low; fingers frame; BG soft wood | soft top-side practical; no face light need | hands only both contact cup; straw turn | cup+straw hero; condensation | fingers rotate cup quarter-turn | hands | i2v |
| S04 | 6.0 | MCU | eye | slow_push | 85 | confession costs smile | eyes upper third; slight right; soft window bokeh left neg | warm key left, cool rim from window, skin open | head stable; eyeline down cup then up guest; cup edge bottom frame | cup rim in; rain bokeh | speaks; eyes path cup→up; smile holds | — | si2v |
| S05 | 3.5 | LS | high | static | 28 | smallness under weather | high map; table center; she small; rain weight | cooler overall; practicals dim | seated same mark; no stand | full café geography; chair empty | still; rain continuous | glass | i2v |
| S06 | 3.5 | OTS | eye | static | 35 | address the absence | dirty shoulder small left; far empty chair + her face right | key on her face; shoulder darker | she looks to empty chair; open to table axis | chair edge motif | turn head to empty seat; lips closed | — | i2v |
| S07 | 5.5 | MCU | eye | static | 85 | smile cracks then recovers | tighter than S04; less neg space = pressure | same key side as S04 (continuity) | head stable; micro brow; hands off frame | — | speaks final soft line; smile falters half-beat | — | si2v |
| S08 | 3.0 | ECU | eye | static | 50 | prop residue | fill frame condensation; abstract | soft specular on glass cup | no face | half-full cup; bent straw | droplet slide (micro) | — | i2v |
| S09 | 3.5 | LS | eye | static | 35 | residual weather pays hook | same family as S01; chair hero; she optional soft exit or gone | cool window; warm lamp low | empty seat; if she remains back 3/4 to cam | rain + empty chair payoff | hold; no new action | glass | i2v |

**Dialogue sketch (for si2v bind later — not full script):**

- S02: “어서 와요… 아, 저 괜찮아요.”  
- S04: “그냥… 별거 아닌데, 비가 오니까 좀 그런 거죠.”  
- S07: “웃으면 괜찮더라고요. 진짜로.”  

## Sample prompts (factory craft — not executed)

### S01 keyframe (still)

```text
Young Korean woman in short summer skirt seated alone at a wooden café table,
empty chair opposite, tall rain-streaked window dominating background,
lived-in sparse Seoul café, warm practical lamp mid-ground, cool overcast daylight through glass,
eye-level long shot, 35mm look, deep environmental read, locked camera framing,
natural skin, soft film contrast, vertical 9:16
```

### S04 I2V (motion only)

```text
slow push-in, subtle breathing, eyes lower then lift, continuous soft motion throughout, stable head
negative: warp, identity morph, freeze frame, extra limbs, whip pan, flicker
```

### S02 SI2V (motion only)

```text
natural speech mouth motion, micro head nod, shoulders almost still, hands rest on cup, continuous throughout
negative: big lean, stand up, face morph, freeze pad, whip
```

## R1–R6 self-audit

| Rule | Status | Note |
|------|--------|------|
| R1 adjacent size/angle | ✅ | LS-MS-Insert-MCU-LS-OTS-MCU-ECU-LS; angle changes high on S05 |
| R2 no triple same type | ✅ | no 3× MS or MCU row |
| R3 variety | ✅ | LS, MS, MCU, Insert, ECU, OTS, high |
| R4 axis | ✅ | table axis held S02–S07; S06 eyeline to chair |
| R5 motif returns | ✅ | cup S03→S08; rain S01→S05→S09; chair S01→S06→S09 |
| R6 hook event | ✅ | S01 size/space hook; S05 high jump mid; S09 residual |

## 13-thumbnail note

Distinct rectangles: tall glass map / talk MS / hands insert / push face / high map / OTS chair / tight MCU / ECU cup / residual LS. Pass.

## Coverage package

| Job | Shots |
|-----|--------|
| A Master | S01, S05, S09 |
| B Medium | S02 |
| C Close | S04, S07 |
| D Insert | S03, S08 |
| E Special | S05 high, S06 OTS |

## Continuity bible

| Item | State |
|------|--------|
| Seat | same table mark S01–S07 |
| Cup | full S02–S04 → half S08 |
| Straw | straight → bent S08 |
| Key side | warm cam-left throughout interior |
| Weather | rain continuous exterior glass |
| Wardrobe | short skirt summer set locked |
| Empty chair | always present left of her (cam ref) |

## Motion duration policy

All clips full designed length; **no freeze pad**. Split if si2v audio exceeds IT max (skill/factory length contract).

## Next factory steps (not run in dry-run)

```text
story_init → write these files into stories/<ep>/
→ assets approve → shot_compose per S0x
→ shot_qa_pack → record → approve
→ episode_tts + episode_s2v / episode_i2v
→ clip QA → assemble hybrid → export
```
