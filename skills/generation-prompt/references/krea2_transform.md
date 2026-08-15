# Krea2 transform / control / detailer prompts

**CLI:** `generate_krea2_style` · `generate_krea2_control` · `generate_krea2_identity_edit` · `generate_krea2_face/eyes/hand/anatomy/region_detail` · `generate_krea2_color_match` · `generate_krea2_post` · `generate_krea_draft`  
**Still T2I body:** `krea2_still_prompts.md` (90–140w paragraph). This file is **change / lock / polish** only.

---

## Shared

Image already owns identity. Prompt = **what this pass does**.  
Do not paste a full casting-plate or a second location essay.

---

## Style (`generate_krea2_style`)

`-i` = style ref. `-p` = **content scene** in Krea NL (subject → action → set → light → camera).  
Do not describe the style image's subject. Name medium only if needed (`oil paint grain`, `editorial flash`).

```text
[same person/scene you want], [action], [setting], [light], [lens], materials named
```

---

## Control (`generate_krea2_control`)

Structure comes from the control image. Prompt = **materials, light, wardrobe, mood**.  
Do not fight the pose/depth map with a different pose in text.

---

## Identity edit (`generate_krea2_identity_edit`)

Qwen-like: **one change**, keep face/framing.

```text
Change only [X]. Keep the same face, hair, wardrobe, and camera.
```

Chain edits. Never wardrobe + pose + location in one string.

---

## Detailers (face / eyes / hand / anatomy / region)

Prompt is **local**: the part being refined.

| Region | Prompt talks about |
|--------|-------------------|
| face | skin pores, catchlight, expression hold — no new identity |
| eyes | iris, wetline, catchlight |
| hand | finger count, knuckles, contact with prop |
| region + `--sam-prompt` | the object name only (`necklace`, `earring`) |

Do not re-prompt the whole shot.

---

## Color match / post

Color match: lighting/grade language only. Post: grain/contrast/finish, not a new scene.

---

## Draft (`generate_krea_draft`)

Same dialect as hero T2I but shorter (40–80w). Still NL, still no tag soup.

---

## Gates

- [ ] Pass type matches CLI (style vs control vs edit vs detail)  
- [ ] No second full still essay on a lock/detail pass  
- [ ] Identity edit = one change  
