# 3D mesh prompts (Hunyuan3D / TRELLIS)

**CLI:** `generate_hy3d_mesh` · related `process_mesh_glb`  
Hy3D is **image-to-mesh**. The still is the prompt. Extra text is usually unused or weak.

---

## Dialect

| DO | DON'T |
|----|--------|
| Feed a **clean orthographic-ish hero still** (front, full subject, simple bg) | Expect a 140w Krea essay to fix a messy photo |
| `--profile draft\|work\|hero` for quality, not for "more prompt" | Tag soup on the CLI  
| One subject, no heavy crop of feet/hands if you need them | Multi-character plates |

If a wrapper accepts `-p`, use **object nouns only**: `single mecha, complete limbs, no base`.

---

## Still that will mesh well (make this with Krea/Anima first)

- Subject centered, full body or full prop  
- Neutral or studio light, readable silhouette  
- No motion blur, no heavy rain streaks across the body  

---

## Gates

- [ ] Input image is the real "prompt"  
- [ ] Not treating Hy3D like T2I  
