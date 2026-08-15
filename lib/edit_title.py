"""Title / caption PNG. Parts compose; named presets are shortcuts."""

from __future__ import annotations

import json
import os
from typing import Any

from lib.comfy_client import fail_result, ok_result
from lib.edit_fonts import known_font_names, list_fonts, resolve_font

# Independent placement families. Chrome (box/bubble/bar) is not locked to these.
LAYOUTS = ("caption", "title", "lower_third", "yeonung", "card")

# Named starting recipes. Agent may omit these and pass parts.
STYLES: dict[str, dict[str, Any]] = {
    "caption": {
        "layout": "caption",
        "size": "md",
        "color": "#FFFFFF",
        "outline": "#000000",
        "outline_width": 4,
        "weight": "regular",
    },
    "yt_hook": {
        "layout": "caption",
        "size": "xl",
        "color": "#FFFFFF",
        "outline": "#000000",
        "outline_width": 8,
        "weight": "bold",
    },
    "yt_pop": {
        "layout": "caption",
        "size": "lg",
        "color": "#FFE14A",
        "outline": "#111111",
        "outline_width": 7,
        "weight": "bold",
    },
    "yt_alert": {
        "layout": "caption",
        "size": "lg",
        "color": "#FF3B5C",
        "outline": "#FFFFFF",
        "outline_width": 6,
        "weight": "bold",
    },
    "yt_soft": {
        "layout": "caption",
        "size": "sm",
        "color": "#F4F4F4",
        "outline": "#000000",
        "outline_width": 3,
        "weight": "regular",
    },
    "yt_box": {
        "layout": "caption",
        "size": "md",
        "color": "#111111",
        "outline": None,
        "outline_width": 0,
        "weight": "bold",
        "box": "#FFE14A",
    },
    "title": {
        "layout": "title",
        "size": "xl",
        "color": "#FFFFFF",
        "outline": "#000000",
        "outline_width": 5,
        "weight": "bold",
    },
    "lower_third": {
        "layout": "lower_third",
        "size": "md",
        "color": "#FFFFFF",
        "outline": None,
        "outline_width": 0,
        "weight": "regular",
        "bar": True,
    },
    "card": {
        "layout": "card",
        "size": "lg",
        "color": "#FFFFFF",
        "outline": None,
        "outline_width": 0,
        "weight": "bold",
    },
    "yeonung": {
        "layout": "yeonung",
        "size": "xl",
        "color": "#FFE600",
        "outline": "#111111",
        "outline_width": 10,
        "weight": "bold",
        "tilt": -4,
    },
    "yeonung_shock": {
        "layout": "yeonung",
        "size": "xl",
        "color": "#FFFFFF",
        "outline": "#E10600",
        "outline_width": 9,
        "weight": "bold",
        "tilt": 5,
    },
    "yeonung_bubble": {
        "layout": "yeonung",
        "size": "lg",
        "color": "#111111",
        "outline": None,
        "outline_width": 0,
        "weight": "bold",
        "bubble": "#FFF8C8",
        "tilt": -3,
    },
    "yeonung_react": {
        "layout": "yeonung",
        "size": "lg",
        "color": "#FFFFFF",
        "outline": "#111111",
        "outline_width": 7,
        "weight": "bold",
        "react_color": "#FF7AD9",
        "tilt": -5,
    },
}

_SIZE_FRAC = {"sm": 0.032, "md": 0.045, "lg": 0.065, "xl": 0.09, "hook": 0.09}

_NAMED = {
    "white": (255, 255, 255, 255),
    "black": (0, 0, 0, 255),
    "yellow": (255, 225, 74, 255),
    "red": (255, 59, 92, 255),
    "pink": (255, 92, 168, 255),
    "cyan": (80, 220, 255, 255),
    "lime": (180, 255, 80, 255),
    "orange": (255, 140, 40, 255),
}

DEFAULT_STYLE: dict[str, Any] = {
    "layout": "caption",
    "size": "md",
    "color": "#FFFFFF",
    "outline": "#000000",
    "outline_width": 4,
    "weight": "regular",
}

_CLEAR = frozenset({"none", "off", "-", ""})


def list_styles() -> list[str]:
    return list(STYLES.keys())


def list_parts() -> dict[str, Any]:
    return {
        "layouts": list(LAYOUTS),
        "sizes": list(_SIZE_FRAC.keys()),
        "colors": list(_NAMED.keys()) + ["#RRGGBB"],
        "chrome": ["box", "bubble", "bar", "react_color", "subtext", "tilt"],
        "place": ["x", "y"],
        "place_note": "x/y are 0-1, center of the main text. Omit to use layout default.",
        "fonts": known_font_names(),
        "font_note": "aliases: --font yeonung|hook|soft|display|gothic|gothic_bold or a .ttf path. setup_edit_fonts.py",
        "presets": list_styles(),
        "preset_note": "shortcuts only. compose layout+paint+chrome+place without a preset.",
    }


def parse_color(value: str | None) -> tuple[int, int, int, int] | None:
    if not value:
        return None
    raw = str(value).strip().lower()
    if raw in {"none", "off", "-"}:
        return None
    if raw in _NAMED:
        return _NAMED[raw]
    if raw.startswith("#"):
        h = raw[1:]
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        if len(h) == 6:
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255
    raise ValueError(f"bad color {value!r} (use #RRGGBB or yellow/white/red/…)")


def _px_size(size: str | int | float, height: int) -> int:
    if isinstance(size, (int, float)) and not isinstance(size, bool):
        if float(size) > 3:
            return max(12, int(size))
        return max(12, int(height * float(size)))
    key = str(size).strip().lower()
    if key.isdigit():
        return max(12, int(key))
    frac = _SIZE_FRAC.get(key, _SIZE_FRAC["md"])
    return max(12, int(height * frac))


def _stroke_text(draw, xy, text, font, fill, outline, width: int) -> None:
    if outline and width > 0:
        x, y = xy
        for dx in range(-width, width + 1):
            for dy in range(-width, width + 1):
                if dx * dx + dy * dy > width * width:
                    continue
                draw.text((x + dx, y + dy), text, font=font, fill=outline)
    draw.text(xy, text, font=font, fill=fill)


def _clear_or_keep(value: Any) -> Any:
    """None = no override. 'none'/'' = strip. else the value."""
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in _CLEAR:
        return False
    return value


def _frac(value: float | None, name: str) -> float | None:
    if value is None:
        return None
    f = float(value)
    if f < 0.0 or f > 1.0:
        raise ValueError(f"{name} must be 0-1, got {value!r}")
    return f


def compose_style(
    *,
    preset: str | None = None,
    layout: str | None = None,
    color: str | None = None,
    outline: str | None = None,
    outline_width: int | None = None,
    size: str | int | float | None = None,
    tilt: float | None = None,
    weight: str | None = None,
    box: str | None = None,
    bubble: str | None = None,
    bar: bool | None = None,
    react_color: str | None = None,
    x: float | None = None,
    y: float | None = None,
) -> dict[str, Any]:
    """Merge a named shortcut with independent parts. Preset is optional."""
    raw = (preset or "").strip()
    if raw and raw.lower() not in {"none", "off", "custom", "-"}:
        if raw not in STYLES:
            known = ", ".join(list_styles())
            raise ValueError(f"unknown preset {raw!r}. Known: {known}")
        style = dict(STYLES[raw])
        style["_preset"] = raw
    else:
        style = dict(DEFAULT_STYLE)
        style["_preset"] = None

    if layout is not None:
        lay = str(layout).strip().lower()
        if lay not in LAYOUTS:
            raise ValueError(f"unknown layout {layout!r}. Known: {', '.join(LAYOUTS)}")
        style["layout"] = lay
    if color is not None:
        style["color"] = color
    if outline is not None:
        if str(outline).strip().lower() in _CLEAR:
            style["outline"] = None
            style["outline_width"] = 0
        else:
            style["outline"] = outline
    if outline_width is not None:
        style["outline_width"] = int(outline_width)
    if size is not None:
        style["size"] = size
    if tilt is not None:
        style["tilt"] = float(tilt)
    if weight is not None:
        w = str(weight).strip().lower()
        if w not in {"regular", "bold"}:
            raise ValueError("weight must be regular or bold")
        style["weight"] = w

    box_v = _clear_or_keep(box)
    if box_v is False:
        style.pop("box", None)
    elif box_v is not None:
        style["box"] = box_v
        style.pop("bubble", None)
    bubble_v = _clear_or_keep(bubble)
    if bubble_v is False:
        style.pop("bubble", None)
    elif bubble_v is not None:
        style["bubble"] = bubble_v
        style.pop("box", None)

    if bar is True:
        style["bar"] = True
    elif bar is False:
        style.pop("bar", None)
    if react_color is not None:
        if str(react_color).strip().lower() in _CLEAR:
            style.pop("react_color", None)
        else:
            style["react_color"] = react_color

    if x is not None:
        style["x"] = _frac(x, "x")
    if y is not None:
        style["y"] = _frac(y, "y")
    return style


def _anchor_xy(
    layout: str,
    w: int,
    h: int,
    tw: int,
    th: int,
    x_frac: float | None,
    y_frac: float | None,
) -> tuple[float, float]:
    if x_frac is not None:
        x = w * float(x_frac) - tw / 2
    elif layout == "lower_third":
        x = w * 0.06
    else:
        x = (w - tw) / 2

    if y_frac is not None:
        y = h * float(y_frac) - th / 2
    elif layout == "title":
        y = (h - th) / 2
    elif layout == "lower_third":
        bar_h = int(h * 0.16)
        bar_y = h - bar_h - int(h * 0.06)
        y = bar_y + int(bar_h * 0.22)
    elif layout == "yeonung":
        y = int(h * 0.62)
    elif layout == "card":
        y = (h - th) / 2
    else:
        y = h - th - int(h * 0.10)

    x = max(0.0, min(float(w - tw), float(x)))
    y = max(0.0, min(float(h - th), float(y)))
    return x, y


def render_title(
    text: str,
    output_path: str,
    *,
    preset: str | None = None,
    width: int = 1920,
    height: int = 1080,
    subtext: str = "",
    font: str | None = None,
    color: str | None = None,
    outline: str | None = None,
    outline_width: int | None = None,
    size: str | int | None = None,
    tilt: float | None = None,
    layout: str | None = None,
    weight: str | None = None,
    box: str | None = None,
    bubble: str | None = None,
    bar: bool | None = None,
    react_color: str | None = None,
    x: float | None = None,
    y: float | None = None,
    split: str | None = None,
) -> dict[str, Any]:
    try:
        style = compose_style(
            preset=preset,
            layout=layout,
            color=color,
            outline=outline,
            outline_width=outline_width,
            size=size,
            tilt=tilt,
            weight=weight,
            box=box,
            bubble=bubble,
            bar=bar,
            react_color=react_color,
            x=x,
            y=y,
        )
    except ValueError as e:
        msg = str(e)
        err = "BAD_PRESET" if "preset" in msg else "BAD_STYLE"
        return fail_result(error=err, message=msg)

    try:
        fill = parse_color(style.get("color"))
        stroke = parse_color(style.get("outline"))
        if style.get("box"):
            parse_color(str(style["box"]))
        if style.get("bubble"):
            parse_color(str(style["bubble"]))
        if style.get("react_color"):
            parse_color(str(style["react_color"]))
    except ValueError as e:
        return fail_result(error="BAD_COLOR", message=str(e))

    ow = int(style.get("outline_width") or 0)
    if stroke is None:
        ow = 0
    font_path = resolve_font(font, weight=str(style.get("weight") or "regular"))
    if not font_path:
        known = ", ".join(known_font_names())
        hint = font or "default"
        return fail_result(
            error="FONT_MISSING",
            message=f"font {hint!r} not found. aliases: {known}. or a .ttf path. python scripts/setup_edit_fonts.py",
        )
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return fail_result(error="PIL_MISSING", message="pip install Pillow")

    w, h = int(width), int(height)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    lay = str(style.get("layout") or "caption")
    if style.get("y") is None and h > w and lay in ("caption", "yeonung"):
        style["y"] = 0.82
    px = _px_size(style.get("size") or "md", h)
    font_o = ImageFont.truetype(font_path, px)
    bbox = ld.textbbox((0, 0), text, font=font_o)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x0, y0 = _anchor_xy(lay, w, h, tw, th, style.get("x"), style.get("y"))

    if lay == "card":
        ld.rectangle((0, 0, w, h), fill=(8, 8, 12, 220))
    if style.get("bar"):
        bar_h = int(h * 0.16)
        bar_y = h - bar_h - int(h * 0.06)
        ld.rectangle((0, bar_y, w, bar_y + bar_h), fill=(0, 0, 0, 160))

    plate = style.get("bubble") or style.get("box")
    if plate:
        pad_x = int(px * (0.55 if style.get("bubble") else 0.45))
        pad_y = int(px * (0.38 if style.get("bubble") else 0.28))
        radius = int(px * (0.35 if style.get("bubble") else 0.2))
        ld.rounded_rectangle(
            (x0 - pad_x, y0 - pad_y, x0 + tw + pad_x, y0 + th + pad_y),
            radius=radius,
            fill=parse_color(str(plate)),
        )

    if subtext:
        if lay == "lower_third" and style.get("bar"):
            font_s = ImageFont.truetype(font_path, max(16, int(px * 0.65)))
            ld.text((x0, y0 + int(th * 0.95)), subtext, font=font_s, fill=(230, 230, 230, 255))
        else:
            react = parse_color(str(style.get("react_color") or "#FF7AD9"))
            font_r = ImageFont.truetype(font_path, max(16, int(px * 0.55)))
            rb = ld.textbbox((0, 0), subtext, font=font_r)
            rw, rh = rb[2] - rb[0], rb[3] - rb[1]
            _stroke_text(
                ld,
                (x0 + (tw - rw) / 2, y0 - rh - int(px * 0.35)),
                subtext,
                font_r,
                react,
                (17, 17, 17, 255),
                max(3, ow // 2),
            )

    _stroke_text(ld, (x0, y0), text, font_o, fill, stroke, ow)
    angle = float(style.get("tilt") or 0.0)
    if abs(angle) > 0.1:
        layer = layer.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False)
    img = Image.alpha_composite(img, layer)

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    img.save(output_path, "PNG")
    composed = {k: v for k, v in style.items() if not str(k).startswith("_")}
    extra: dict[str, Any] = {}
    if (split or "").strip().lower() in {"glyph", "glyphs", "chars", "letters"}:
        extra = _write_glyphs(
            text,
            output_path,
            width=w,
            height=h,
            x0=x0,
            y0=y0,
            font=font_o,
            fill=fill,
            stroke=stroke,
            ow=ow,
            angle=angle,
        )
    return ok_result(
        tool="render_title",
        path=os.path.abspath(output_path),
        preset=style.get("_preset"),
        font=font_path,
        color=style.get("color"),
        size=style.get("size"),
        layout=lay,
        composed=composed,
        **extra,
    )


def _char_advance(font, ch: str) -> float:
    if hasattr(font, "getlength"):
        return float(font.getlength(ch))
    from PIL import Image, ImageDraw

    dummy = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    box = dummy.textbbox((0, 0), ch, font=font)
    return float(box[2] - box[0])


def _write_glyphs(
    text: str,
    output_path: str,
    *,
    width: int,
    height: int,
    x0: float,
    y0: float,
    font,
    fill,
    stroke,
    ow: int,
    angle: float,
) -> dict[str, Any]:
    from PIL import Image, ImageDraw

    stem = os.path.splitext(os.path.abspath(output_path))[0]
    glyphs: list[dict[str, Any]] = []
    cursor = 0.0
    gi = 0
    for ch in text:
        adv = _char_advance(font, ch)
        if ch.isspace():
            cursor += adv
            continue
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        _stroke_text(ld, (x0 + cursor, y0), ch, font, fill, stroke, ow)
        if abs(angle) > 0.1:
            layer = layer.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False)
        bbox = layer.getbbox()
        if not bbox:
            cursor += adv
            continue
        pad = 12
        box = (
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(width, bbox[2] + pad),
            min(height, bbox[3] + pad),
        )
        crop = layer.crop(box)
        g_path = f"{stem}_g{gi:02d}.png"
        crop.save(g_path, "PNG")
        glyphs.append(
            {
                "i": gi,
                "ch": ch,
                "path": os.path.abspath(g_path),
                "x": int(box[0]),
                "y": int(box[1]),
                "w": int(crop.size[0]),
                "h": int(crop.size[1]),
            }
        )
        gi += 1
        cursor += adv
    manifest = {
        "schema": "edit_glyphs.v1",
        "text": text,
        "full": os.path.abspath(output_path),
        "width": width,
        "height": height,
        "glyphs": glyphs,
    }
    man_path = stem + ".glyphs.json"
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return {"glyphs": man_path, "glyph_count": len(glyphs)}
