#!/usr/bin/env python3
"""One-off: remove black straw from S02 via targeted local inpaint."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter

src = r"stories/cafe_gomin_ep01/keyframes/S02_with_straw_bak.png"
out = r"stories/cafe_gomin_ep01/keyframes/S02_straw_mask_prep.png"
mask_out = r"stories/cafe_gomin_ep01/keyframes/S02_straw_mask.png"

im = Image.open(src).convert("RGB")
w, h = im.size
print("size", w, h)
px = im.load()

# From pixel scan: straw cluster ~x 236-252, y 240-401 (and into mouth)
mask = Image.new("L", (w, h), 0)
draw = ImageDraw.Draw(mask)

# Main straw body (glass rim up to mouth)
draw.rectangle((234, 250, 256, 345), fill=255)
# tip at lips
draw.ellipse((236, 318, 258, 348), fill=255)
# slightly thinner upper stem if any above lips
draw.rectangle((238, 300, 252, 340), fill=255)

# Also pick dark straw-like pixels in expanded ROI
mp = mask.load()
for y in range(240, 360):
    for x in range(230, 265):
        r, g, b = px[x, y]
        # dark gray/black tube (not hair which is larger / browner)
        if r < 115 and g < 105 and b < 110 and max(r, g, b) - min(r, g, b) < 40:
            # avoid painting large dark hair blocks — only thin vertical neighborhood
            if abs(x - 245) <= 12:
                for dy in range(-1, 2):
                    for dx in range(-2, 3):
                        xx, yy = x + dx, y + dy
                        if 0 <= xx < w and 0 <= yy < h:
                            mp[xx, yy] = 255

mask = mask.filter(ImageFilter.MaxFilter(3))
mask = mask.filter(ImageFilter.GaussianBlur(1.2))
mp = mask.load()

out_im = im.copy()
op = out_im.load()
for y in range(h):
    for x in range(w):
        if mp[x, y] < 30:
            continue
        samples = []
        for rad in range(3, 36, 2):
            # prefer horizontal samples (glass rim / skin / latte) over vertical
            for dx, dy in (
                (-rad, 0),
                (rad, 0),
                (-rad, 1),
                (rad, 1),
                (-rad, -1),
                (rad, -1),
                (0, rad),
                (0, -rad),
            ):
                xx, yy = x + dx, y + dy
                if 0 <= xx < w and 0 <= yy < h and mp[xx, yy] < 30:
                    samples.append(px[xx, yy])
            if len(samples) >= 8:
                break
        if samples:
            rs = sorted(s[0] for s in samples)
            gs = sorted(s[1] for s in samples)
            bs = sorted(s[2] for s in samples)
            mid = len(samples) // 2
            op[x, y] = (rs[mid], gs[mid], bs[mid])

# Soft composite
blurred = out_im.filter(ImageFilter.GaussianBlur(0.6))
out_im = Image.composite(blurred, out_im, mask)

out_im.save(out, quality=95)
mask.save(mask_out)
n = sum(1 for yy in range(h) for xx in range(w) if mask.getpixel((xx, yy)) > 40)
print("saved", out, "mask_pixels", n)
