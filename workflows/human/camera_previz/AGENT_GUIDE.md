# Camera previz (Blender plate → H3 R2V) — AGENT_GUIDE

> **Toolbox shelf:** MOTION  
> **CLI:** `python scripts/generate_previz.py`  
> **Then:** `python scripts/generate_minimax_h3.py --task r2v --ref-video plate.mp4`  
> **Skill:** [skills/camera-previz/SKILL.md](../../../skills/camera-previz/SKILL.md)  
> **Catalog:** [docs/tool_catalog.md](../../../docs/tool_catalog.md) §2.4  
> **Requires:** Blender MCP `127.0.0.1:9876` (not Higgsfield)

**Role:** Playblast a **locked camera** (preset or live scene), then H3 follows that path.

**Not:** `generate_camera_move`; talking-head hold; Higgsfield/Claude Desktop.

---

## When / when not

| Use | Use something else |
|-----|---------------------|
| Camera path must match a 3D move | Preset I2V guess → `generate_camera_move` |
| Custom blocking / rapid camera / object hero | `--exec-file` / `--from-scene`, then H3 |
| Several cuts in one set | Cameras `Shot_A`/`Shot_B` + `--camera` per mp4 |
| User said 프리비즈 / previz / playblast | Locked lips → H3 I2V or `s2v` |
| 20s oner | Cut to ≤15s or say H3 cannot |

Iterate the plate in Blender before H3. Plate QA fails closed (color, clip, camera-in-geo). Gray fill is the plate, not H3.

---

## CLI

```bash
python scripts/generate_previz.py --probe
python scripts/generate_previz.py --list-presets
python scripts/generate_previz.py --preset corridor_follow -o plate.mp4 --save-blend scene.blend
python scripts/generate_previz.py --from-scene --camera Shot_A -o plate_a.mp4
python scripts/generate_previz.py --exec-file build.py -o plate.mp4 --seconds 5 --camera Shot_A
python scripts/generate_previz.py --list-cameras
python scripts/generate_previz.py --write-h3-prompt h3.txt --hero object

python scripts/generate_minimax_h3.py --task r2v -i hero.png --ref-video plate.mp4 \
  --profile work --prompt-file h3.txt -o clip.mp4 --seed 42
```

Presets wipe the scene. `--from-scene` / `--exec-file` do not. Default 5s / 24fps / 1280×720. Max 15s.

mp4 = H3 plate. `--save-blend` = editable copy after bake. Keep the camera **inside** the set.

Color contract: hero orange, extra blue, prop green, set gray, mark yellow. `--exec-file` injects `PREVIZ_COLORS`.

---

## Smoke

```bash
python scripts/generate_previz.py --probe
python scripts/generate_previz.py --list-presets
python scripts/generate_previz.py --preset corridor_follow -o out.mp4
```
