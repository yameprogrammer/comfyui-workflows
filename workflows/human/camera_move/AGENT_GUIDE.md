# Camera move (motion-intent I2V) — AGENT_GUIDE

> **Toolbox shelf:** MOTION  
> **CLI:** `python scripts/generate_camera_move.py`  
> **Example:** `python scripts/generate_camera_move.py -i key.png --preset push_in -o clip.mp4 --seed 42`  
> **Alternatives:** free-form motion → `generate_i2v -p "…"` · still high/low → `generate_viewpoint` · idle loop → `generate_idle_loop --mode pingpong` · crop → `generate_reframe`  
> **Catalog:** [docs/tool_catalog.md](../../../docs/tool_catalog.md) · card standard: [toolbox_card_standard.md](../../../docs/toolbox_card_standard.md)  
> **Presets lib:** `lib/motion_presets.py`

**Role:** One-shot **image → video** with a named **camera / motion intent** (push-in, pan, idle, talk…).

**Not:** Still reframing; multi-angle turn table (`qwen_angle`); episode batch (use `episode_i2v --motion-preset`).

---

## When / when not

| Use | Use something else |
|-----|---------------------|
| Keyframe needs a clear camera move | Static still only → no I2V |
| Agent should not invent motion prose | Custom motion essay → `generate_i2v -p` |
| Same presets as episode shots | Batch over `stories/` → `episode_i2v` |

---

## Presets

```bash
python scripts/generate_camera_move.py --list-presets
```

| id | Intent |
|----|--------|
| `idle` | Locked cam, micro life |
| `push_in` / `pull_out` | Dolly in / out |
| `pan_left` / `pan_right` | Gentle pan |
| `orbit_subtle` | Small arc |
| `talk_gesture` | Dialogue + light body (cam mostly locked) |
| `smile_turn` / `look_away` / `walk_toward` / `wind_hair` / `product_orbit` | Subject/atmosphere |

Same ids work on `generate_i2v --motion-preset` and `episode_i2v --motion-preset` / shot.`motion_preset`.

---

## CLI

```bash
python scripts/generate_camera_move.py \
  -i keyframe.png --preset push_in -o clip.mp4 --seed 42

# Extra subject action (not face re-essay)
python scripts/generate_camera_move.py \
  -i key.png --preset talk_gesture -p "holding ceramic cup" -o talk.mp4

# Prompt only (no Comfy)
python scripts/generate_camera_move.py -i key.png --preset idle -o x.mp4 --dry-run

# Backend / format passthrough (same as generate_i2v)
python scripts/generate_camera_move.py -i key.png --preset pan_left -o out.mp4 \
  --backend ltx23_aio_i2v --format shorts_9x16 --frames 49
```

---

## Backend

ComfyUI I2V via `generate_i2v` (default backend from `video_backends.json`, often LTX AIO).  
Requires Comfy at `127.0.0.1:8188` unless `--dry-run`.

---

## Smoke

```bash
python scripts/generate_camera_move.py --list-presets
python scripts/generate_camera_move.py -i still.png --preset push_in -o out.mp4 --dry-run
```
