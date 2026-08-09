# Hy3D mesh toolbox — agent guide

**Shelf:** MESH  
**Status:** `generate_hy3d_mesh` = **ready** · Blender steps = **ready_experimental**

Image → 3D mesh (GLB) for character / prop assets, then optional Blender clean / VRM.

## When / when not

| Use | Skip |
|-----|------|
| 2D front (or clear single-subject still) → GLB mesh | Video I2V / 2D still only jobs |
| Prototype avatar mesh for inspection / light VRM | Production Warudo humanoid QA (manual re-rig) |
| Mecha / character figure from master front | Multi-view identity without refs (use better front still first) |

## Prerequisites

### Mesh generation (Comfy)

1. ComfyUI running (`127.0.0.1:8188`)
2. Custom node: **ComfyUI-Hunyuan3DWrapper** (Kijai)
3. DiT weights: `hy3dgen\hunyuan3d-dit-v2-0-fp16.safetensors` (via `extra_model_paths` / `F:\model`)
4. Optional texture path: delight + paint models (`hunyuan3d-delight-v2-0`, `hunyuan3d-paint-v2-0`)

### Blender post (optional)

1. Blender running with **MCP server** (default `127.0.0.1:9876`)
2. For VRM: **VRM addon** enabled (`export_scene.vrm`)

```bash
python scripts/process_mesh_glb.py --probe
python scripts/export_mesh_vrm.py --probe
```

## CLI

### 1) Image → GLB (mainline)

```bash
python scripts/generate_hy3d_mesh.py -i front.png -o out.glb --seed 42
python scripts/generate_hy3d_mesh.py -i front.png -o scout.glb --profile draft
python scripts/generate_hy3d_mesh.py -i front.png -o hero.glb --profile hero
python scripts/generate_hy3d_mesh.py -i front.png -o tex.glb --profile hero --texture
python scripts/generate_hy3d_mesh.py --list-profiles
```

| Profile | Steps | Octree | Faces | Role |
|---------|-------|--------|-------|------|
| draft | 25 | 256 | 40k | scout |
| **work** | 45 | 384 | 80k | **default** |
| hero | 50 | 512 | 120k | heavy geo / texture |

### 2) Clean / light rig (Blender MCP)

```bash
python scripts/process_mesh_glb.py -i out.glb -o clean.glb
python scripts/process_mesh_glb.py -i out.glb -o rigged.glb --auto-rig
```

### 3) Export VRM (Blender MCP + VRM addon)

```bash
python scripts/export_mesh_vrm.py -i clean.glb -o avatar.vrm
```

Also writes a sidecar `.glb` next to the VRM when export succeeds.

## Recommended agent recipe

```text
front still (Krea / character_consistent)
  → generate_hy3d_mesh  (-o mesh.glb, profile work)
  → process_mesh_glb    (clean; optional --auto-rig)
  → export_mesh_vrm     (if VTuber / Warudo prototype needed)
  → open files in Blender / Warudo for visual QA
```

## Alternatives

| If | Use |
|----|-----|
| Need better still first | `generate_krea` / `generate_character_consistent` |
| Legacy one-off Hy3D scripts | `scripts/generate_hy3d_quality_pipeline.py` (prefer this pack) |
| Full custom Blender surgery | open mesh in Blender manually — do not invent new factory scripts mid-job |

## Limits (honest)

- Auto-rig is **not** production humanoid retarget quality.
- Texture path is VRAM-heavy and may fail on some node/version combos — fall back to geo-only.
- Hardcoded mecha project scripts under `scripts/fix_*` / `export_patlabor_*` are **not** the agent SSOT; use this pack.

## Caps

See [CAPABILITIES.json](CAPABILITIES.json).
