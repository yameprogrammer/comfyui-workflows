# TRELLIS 2 mesh toolbox — agent guide

**Shelf:** MESH  
**Status:** `generate_trellis_mesh` = **ready** (agent default) · Blender steps = **ready_experimental**

Image → 3D mesh (GLB) via Microsoft TRELLIS 2. MIT weights. Not Hunyuan3D.

Hunyuan3D-2 Community License **excludes Korea**. Do **not** call `generate_hy3d_mesh` unless the user names Hunyuan / Hy3D.

## When / when not

| Use | Skip |
|-----|------|
| 2D front still → GLB (prop, mecha, graybox) | Video I2V / 2D-only jobs |
| Game-prop scout, environment filler | Hero character / production skin / quad topology |
| Optional Blender clean / light VRM after | Paid Tripo/Meshy when you need remesh control |

## Prerequisites

### Mesh generation (Comfy)

1. ComfyUI running (`127.0.0.1:8188`)
2. Custom node: **ComfyUI-TRELLIS2** (PozzettiAndrea)
3. Weights: `ComfyUI/models/trellis2/ckpts/` + `models/dinov3/model.safetensors`

### Blender post (optional)

1. Blender MCP (`127.0.0.1:9876`)
2. VRM addon for `export_mesh_vrm`

```bash
python scripts/process_mesh_glb.py --probe
python scripts/export_mesh_vrm.py --probe
```

## CLI

```bash
python scripts/generate_trellis_mesh.py -i front.png -o out.glb --seed 42
python scripts/generate_trellis_mesh.py -i front.png -o scout.glb --profile draft
python scripts/generate_trellis_mesh.py -i front.png -o geo.glb --profile work --no-texture
python scripts/generate_trellis_mesh.py -i front.png -o hero.glb --profile hero
python scripts/generate_trellis_mesh.py --list-profiles
```

| Profile | Resolution | PBR | Faces | Role |
|---------|------------|-----|-------|------|
| draft | 512 | no | 40k | scout geo |
| **work** | 1024_cascade | yes | 80k | **default** |
| hero | 1024_cascade | yes | 200k | heavier; still not a hero rig |

Human UI graphs (same pack, not the agent API):

- `01_TRELLIS2_Image_to_3D_PBR_Mesh_GLB.json`
- `02_TRELLIS2_Geometry_Only_1024_Mesh.json`

Also under `F:\ComfyUI_workflows\04_3D_Models\TRELLIS\`.

## Recipe

```text
front still (Krea / character_consistent)
  → generate_trellis_mesh  (-o mesh.glb, profile work)
  → process_mesh_glb       (clean; optional --auto-rig)
  → export_mesh_vrm        (if VTuber / Warudo prototype needed)
```

Input still: subject centered, simple/transparent background, full object visible. The image **is** the prompt.

## License

- TRELLIS 2 weights: MIT.
- This agent path uses ComfyUI-TRELLIS2. Commercial GLB: prefer native Comfy 0.34+ when it lands; confirm a given pack did not route through NVIDIA nvdiffrast/nvdiffrec.
- Hunyuan3D-2 / 2mv / Paint 2.1: **pass** for KR commercial.
