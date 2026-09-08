---
name: camera-previz
version: 1.2.0
description: >
  Lock camera in Blender block previz, then MiniMax H3 R2V --ref-video follows
  that path. Use for previz, 프리비즈, playblast, Blender camera, 카메라 경로
  잠금, 급카메라, 커스텀 장면, 테니스공/오토바이 같은 물체 히어로, from-scene,
  or /camera-previz. Not text-only camera_move, locked talking-head, or
  Higgsfield/Claude Desktop.
---

# camera-previz — 3D plate → H3 follows the camera

Lock **camera (and proxy motion) in Blender**, then H3 follows `<Video 1>`. Do not invent that camera in an I2V prompt.

**Factory CLI:** `F:\Agent_media_tools`  
**Not:** Higgsfield Blender plugin, Claude Desktop connector, Seedance credits.

---

## 0. Equip

Blender 5.2 **open**, MCP on `localhost:9876`, **Allow Online Access**.

```bash
python scripts/generate_previz.py --probe
```

Offline → ask the user to open Blender. Also load `generation-prompt` (H3 R2V V2V) and `output-review` after H3.

---

## 1. Pick a branch

| Shot | Branch |
|------|--------|
| Follow / push / orbit / side-track in a simple set | **A — preset** |
| City fly, rapid camera, custom blocking, “테니스공이 빌딩 사이” | **B — custom bpy** |
| Shot list with 2+ cuts | **B**, cameras `Shot_A` / `Shot_B` / … then `--camera` per plate |
| Named I2V guess only | `generate_camera_move` — not this skill |
| Locked talking-head | H3 `--task i2v` + lock language |

Default length **5s**. H3 cap **15s**. A 20s oner is not local H3 — cut the plate or say so.

Iterate **in Blender** until the plate is right. Failed previz is cheap; failed H3 is not.

---

## 2A. Preset

```bash
python scripts/generate_previz.py --list-presets
python scripts/generate_previz.py --preset corridor_follow -o "%AGENT_WORKSPACE%/plates/follow.mp4" --write-h3-prompt "%AGENT_WORKSPACE%/plates/h3_r2v.txt" --save-blend "%AGENT_WORKSPACE%/plates/follow.blend"
```

| id | Camera |
|----|--------|
| `corridor_follow` | Behind → 3/4 **inside walls** → closer |
| `push_in` | Dolly in on a static block |
| `orbit` | 90° orbit, radius clear of the block |
| `side_track` | Left-side track, x stays inside corridor |

Camera keys **inside** geometry. Gray fill = path bug, not H3. CLI bakes `TRACK_TO` and sets `clip_start=0.1` before the playblast.

---

## 2B. Custom scene (Deno-style)

1. Write bpy that builds **proxy geometry + camera keys** (cubes/spheres OK). Hero may be a ball, bike, or box — not only a person.
2. Shot list with several cuts → one camera per cut, named `Shot_A`, `Shot_B`, … Do not jam the episode into one `PrevizCam`.
3. `--exec-file` injects `PREVIZ_COLORS` and `PREVIZ_CLIP_START`. Use those materials. Keep the camera out of walls.

```bash
python scripts/generate_previz.py --exec-file "%AGENT_WORKSPACE%/plates/build.py" -o "%AGENT_WORKSPACE%/plates/shot_a.mp4" --seconds 5 --camera Shot_A --save-blend "%AGENT_WORKSPACE%/plates/scene.blend"
python scripts/generate_previz.py --from-scene --camera Shot_B -o "%AGENT_WORKSPACE%/plates/shot_b.mp4"
python scripts/generate_previz.py --list-cameras
```

`--exec-file` does **not** clear the scene first. `--preset` **does** wipe.

Language revisions (“too flat, add a street canyon”) → edit bpy → plate again → only then H3.

Same custom blocking a second time → promote it to a named preset/helper. Do not leave the bpy only in chat.

---

## 2C. Color = role

| Role | Color (RGB) | Name prefix | H3 |
|------|-------------|-------------|-----|
| Hero | orange `(1.0, 0.38, 0.05)` | `Hero*` | `<Picture 1>` person |
| Extra | blue `(0.12, 0.42, 0.95)` | `Extra*` / `Crowd*` / `Npc*` | not Picture 1 |
| Prop | green `(0.08, 0.72, 0.42)` | `Prop*` / `Ball*` / `Vehicle*` | `<Picture 1>` if `--hero object` |
| Set | gray `(0.55, 0.55, 0.58)` | `Wall*` / `Ceil*` | space only |
| Floor | dark gray `(0.22, 0.22, 0.24)` | `Floor*` | space only |
| Mark | yellow `(0.85, 0.78, 0.22)` | `Mark*` | gizmo only |

Plate **FAIL** if two roles share a color, if a wall wears hero orange, or if extras use marker yellow. One hero-orange mesh for a person plate.

---

## 2D. Playblast vs editable file

| Output | What it is |
|--------|------------|
| `-o plate.mp4` | H3 `<Video 1>`. Required. |
| `--save-blend scene.blend` | Copy of the baked scene so you can change lens/angle without regenerating from a prompt. |

mp4-only means the next angle change becomes a prompt rewrite. Save the blend when the blocking should be restaged.

CLI bakes visual loc/rot, **removes camera constraints**, sets `clip_start=0.1`. Gray fill or a clipped foreground is **PLATE_QA**, not an H3 miss.

---

## 3. H3

`<Video 1>` = camera, timing, space.  
`<Picture 1>` = person **or** object look. Do not re-essay wardrobe.

```bash
# person
python scripts/generate_minimax_h3.py --task r2v -i hero_full.png --ref-video plate.mp4 --profile work --prompt-file h3.txt -o clip.mp4
# object (ball, vehicle)
python scripts/generate_previz.py --write-h3-prompt h3_obj.txt --hero object
python scripts/generate_minimax_h3.py --task r2v -i object.png --ref-video plate.mp4 --profile work --prompt-file h3_obj.txt -o clip.mp4
```

Person plates: pack `approved/master_full.png`. Face CU on a wide follow will fail identity.  
`--ref-image-size max` on person R2V. Stock prompt alone leaves the orange proxy as a cardboard cutout (`FN-20260908-006`). Prompt must discard the orange volume.  
Omit `--duration` (cap 15s). First smoke: `--profile work`.

Optional A/B when claiming previz helped: same seed/prompt **without** `--ref-video`. Keep the plate run if cameras diverge.

---

## 4. Review

Open plate first/mid/last, then H3 first/mid/last (C1–C5). Fail if camera ignores the plate, proxy remains, or the camera is inside a wall.

Plate QA (CLI already fail-closed): camera in geo, `clip_start` too large, leftover constraint, color collision, missing `Shot_*`. Do not send a QA-fail plate to H3.

---

## 5. Hard bans

- Higgsfield / Claude Desktop as the agent path
- `generate_camera_move` when the user asked to **lock** a 3D path
- H3 T2V/I2V hoping the prompt recreates a rapid orbit
- Native/hero H3 on a first smoke
- 20s local H3 oner
- One camera for a multi-shot list
- Skipping `--save-blend` when the user will restage angle/lens
