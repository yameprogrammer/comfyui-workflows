# Idle + loop — AGENT_GUIDE

> **Toolbox shelf:** MOTION  
> **CLI:** `python scripts/generate_idle_loop.py`  
> **Alternatives:** single idle play only → `generate_camera_move --preset idle` · custom camera → `generate_camera_move --preset push_in` · FLF bridge only → `generate_flf2v`  
> **Catalog:** [docs/tool_catalog.md](../../../docs/tool_catalog.md)

**Role:** Subtle **idle** motion on a still, optionally packaged as a **loopable** clip.

**Not:** Style transfer; viewpoint still change; talking lip sync (use s2v).

---

## Modes

| mode | What you get | Loop quality |
|------|----------------|--------------|
| **`idle`** | One I2V clip with micro life | Single play |
| **`pingpong`** (default) | Forward + reverse | **Seamless** for loop players |
| **`roundtrip`** | Forward + FLF back to start still | Forward loop; possible soft seam |

```bash
python scripts/generate_idle_loop.py --list-modes
```

---

## CLI

```bash
# Reliable seamless idle loop (recommended default)
python scripts/generate_idle_loop.py -i key.png -o idle_loop.mp4 --mode pingpong --seed 42

# Single-play subtle motion only
python scripts/generate_idle_loop.py -i key.png -o idle.mp4 --mode idle

# Forward loop via return-to-start FLF
python scripts/generate_idle_loop.py -i key.png -o round.mp4 --mode roundtrip

# Other micro presets
python scripts/generate_idle_loop.py -i key.png -o wind_loop.mp4 \
  --mode pingpong --motion-preset wind_hair
```

**Needs:** Comfy (`generate_i2v` / FLF) + **ffmpeg** on PATH for pingpong/roundtrip.

---

## When / when not

| Use | Skip |
|-----|------|
| Waiting / breathing / ambient loop for UI or B-roll | Dialogue lip → `generate_s2v` |
| Seamless background character loop | One-shot push-in story beat → `generate_camera_move` |
| Hold a keyframe alive without big action | |

---

## Smoke

```bash
python scripts/generate_idle_loop.py --list-modes
# full run needs Comfy:
python scripts/generate_idle_loop.py -i still.png -o out.mp4 --mode idle --frames 33
```
