# Anima & Anima-LLLite — Agent Guide

> **One-stop CLI:** `python scripts/generate_anima.py`  
> **Backend:** Anima DiT 2B + Qwen Text Encoder + Anima-LLLite ControlNet adapters  
> **Specialty:** Lightweight, ultra-fast, state-of-the-art 2D anime, manga, and cel-shaded illustration.

---

## When to use

| Goal | Tool / Mode | When NOT to use |
|------|-------------|-----------------|
| **2D Anime / Manga / Cel-shaded T2I** | `python scripts/generate_anima.py -p "..."` | Photorealistic humans (use Krea2 / Z-Image) |
| **Lineart / Sketch Auto-Coloring** | `python scripts/generate_anima.py --mode lineart -i sketch.png -p "..."` | Heavy photoreal texture transfer |
| **Spatial / 3D Depth Guidance** | `python scripts/generate_anima.py --mode depth -i depth.png -p "..."` | Freeform unconstrained angles |
| **OpenPose Character Pose Lock** | `python scripts/generate_anima.py --mode pose -i pose.png -p "..."` | Loose freestyle poses |
| **4-Channel Anime Inpainting** | `python scripts/generate_anima.py --mode inpaint -i img.png -m mask.png -p "..."` | Full image redesign |
| **Multi-Control (Lineart+Depth+Pose)** | `python scripts/generate_anima.py --mode all-control ...` | Simple single-condition tasks |
| **2K/4K Anime Hi-Res Upscale** | `python scripts/generate_anima.py --mode hires -p "..."` | Real-world photo enhancement |

---

## Key CLI Examples

```bash
# 1. Standard Text to Image (Default 832x1216, 28 steps, euler/simple)
python scripts/generate_anima.py \
  -p "1girl, silver hair, blue eyes, anime masterpiece, dynamic lighting, 8k" \
  -o workspace/anime_hero.png

# 2. Ultra-Fast Turbo LoRA Mode (8 steps, ~1.5s generation)
python scripts/generate_anima.py \
  --turbo \
  -p "1boy, futuristic ninja, cyber katana, neon rain, anime style" \
  -o workspace/turbo_ninja.png

# 3. Lineart / Manga Coloring
python scripts/generate_anima.py \
  --mode lineart \
  -i path/to/sketch.png \
  -p "1girl, vibrant pastel coloring, sunny classroom, studio anime quality" \
  --control-strength 0.95 \
  -o workspace/colored_sketch.png

# 4. Depth Control (Composition & Perspective)
python scripts/generate_anima.py \
  --mode depth \
  -i path/to/depth_map.png \
  -p "sci-fi anime corridor, dramatic perspective, volumetric lighting" \
  --control-strength 0.85 \
  -o workspace/depth_corridor.png

# 5. Pose Control (OpenPose Skeleton)
python scripts/generate_anima.py \
  --mode pose \
  -i path/to/openpose_stick.png \
  -p "magical girl casting spell, floating hair, glowing wand, dynamic action" \
  --control-strength 0.9 \
  -o workspace/pose_magical_girl.png

# 6. Anime Inpainting
python scripts/generate_anima.py \
  --mode inpaint \
  -i path/to/character.png \
  -m path/to/mask.png \
  -p "smiling face with blushing cheeks, sparkling eyes" \
  --denoise 0.75 \
  -o workspace/inpainted_face.png

# 7. Hi-Res 2K Upscale & Detailer
python scripts/generate_anima.py \
  --mode hires \
  -p "1girl, elaborate kimono, cherry blossom blizzard, ultra fine details" \
  --width 832 --height 1216 \
  -o workspace/hires_masterpiece.png
```

---

## Model Layout & Dependencies

```
📂 ComfyUI/models/
├── 📂 diffusion_models/
│   └── 📄 anima-base-v1.0.safetensors
├── 📂 text_encoders/
│   └── 📄 qwen_3_06b_base.safetensors
├── 📂 vae/
│   └── 📄 qwen_image_vae.safetensors
├── 📂 model_patches/
│   ├── 📄 anima-lllite-inpainting-v2.safetensors
│   ├── 📄 anima-lllite-depth-1.safetensors
│   ├── 📄 anima-lllite-lineart-1.safetensors
│   ├── 📄 anima-lllite-pose-1.safetensors
│   ├── 📄 anima-lllite-scribble-1.safetensors
│   └── 📄 anima-lllite-any-test-like-v2.safetensors
└── 📂 loras/
    └── 📄 anima-turbo-lora-v0.2.safetensors
```

---

## Agent Rule of Thumb
- For **2D anime, manga lineart, comic panels, or VTuber/Game 2D concept art**, choose `generate_anima` first over generic SDXL/Pony models.
- If speed is paramount (e.g. rapid draft iterations), supply `--turbo` for sub-2-second generations on RTX 4090.
