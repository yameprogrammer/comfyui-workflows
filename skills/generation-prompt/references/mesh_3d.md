# 3D mesh prompts (TRELLIS 2)

**CLI:** `generate_trellis_mesh` · related `process_mesh_glb`  
**Not:** `generate_hy3d_mesh` (Hunyuan3D KR Community License blocked).

TRELLIS 2 is **image-to-mesh**. The still is the prompt. Extra text is unused.

---

## Dialect

| DO | DON'T |
|----|--------|
| Feed a **clean orthographic-ish hero still** (front, full subject, simple bg) | Expect a 140w Krea essay to fix a messy photo |
| `--profile draft\|work\|hero` for quality, not for "more prompt" | Tag soup on the CLI |
| One subject, no heavy crop of feet/hands if you need them | Multi-character plates |
| Call `generate_trellis_mesh` | Call Hunyuan unless the user named it |

If a wrapper accepts `-p`, use **object nouns only**: `single mecha, complete limbs, no base`.

---

## Still that will mesh well (make this with Krea/Anima first)

- Subject centered, full body or full prop  
- Neutral or studio light, readable silhouette  
- No motion blur, no heavy rain streaks across the body  

---

## Gates

- [ ] Input image is the real "prompt"  
- [ ] Not treating TRELLIS like T2I
- [ ] Not calling Hunyuan unless the user named it  
