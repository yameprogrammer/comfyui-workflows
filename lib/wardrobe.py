"""Wardrobe / props lock helpers for character sheets.

SSOT lives in bible.appearance:
  wardrobe_default, wardrobe_alt1, props_default, props_notes
  wardrobe_locked (bool), wardrobe_locked_at

Process stage B2: lock wardrobe+props AFTER face promote, BEFORE master_full / full_pack.
"""

from __future__ import annotations

from typing import Any

from lib.comfy_client import utc_now_iso

# Generic placeholders that should NOT count as a production lock
_GENERIC_WARDROBE_MARKERS = (
    "black crew-neck",
    "black crew neck",
    "black t-shirt",
    "black tee",
)

MIN_WARDROBE_LEN = 12
MIN_PROPS_LEN = 4


def appearance_block(bible: dict) -> dict:
    return bible.setdefault("appearance", {})


def get_wardrobe_default(bible: dict, *, fallback: str | None = None) -> str:
    w = (appearance_block(bible).get("wardrobe_default") or "").strip()
    if w:
        return w
    return (fallback or "").strip()


def get_wardrobe_alt1(bible: dict, *, fallback: str | None = None) -> str:
    w = (appearance_block(bible).get("wardrobe_alt1") or "").strip()
    if w:
        return w
    return (fallback or "").strip()


def get_props_default(bible: dict, *, fallback: str | None = None) -> str:
    p = (appearance_block(bible).get("props_default") or "").strip()
    if p:
        return p
    return (fallback or "").strip()


def is_generic_wardrobe(text: str) -> bool:
    low = (text or "").strip().lower()
    if not low:
        return True
    return any(m in low for m in _GENERIC_WARDROBE_MARKERS) and len(low) < 80


def wardrobe_status(bible: dict) -> dict[str, Any]:
    app = appearance_block(bible)
    default = (app.get("wardrobe_default") or "").strip()
    alt1 = (app.get("wardrobe_alt1") or "").strip()
    props = (app.get("props_default") or "").strip()
    locked_flag = bool(app.get("wardrobe_locked"))
    has_default = len(default) >= MIN_WARDROBE_LEN
    has_props = len(props) >= MIN_PROPS_LEN
    generic = is_generic_wardrobe(default) if default else True
    # Production lock: explicit flag OR (non-empty non-generic default)
    locked = locked_flag and has_default
    if not locked_flag and has_default and not generic:
        # treat detailed non-generic text as soft-locked for expand warnings
        soft_locked = True
    else:
        soft_locked = False
    return {
        "wardrobe_default": default,
        "wardrobe_alt1": alt1,
        "props_default": props,
        "props_notes": (app.get("props_notes") or "").strip(),
        "wardrobe_locked": locked,
        "soft_locked": soft_locked,
        "has_default": has_default,
        "has_alt1": len(alt1) >= MIN_WARDROBE_LEN,
        "has_props": has_props,
        "is_generic": generic,
        "locked_at": app.get("wardrobe_locked_at"),
        "ok_for_full_sheet": locked or (has_default and not generic),
    }


def apply_consistency_for_locked_wardrobe(bible: dict) -> None:
    """Default-look sheets: keep face/hair/wardrobe; outfit not free-floating."""
    rules = bible.setdefault("consistency_rules", {})
    must = list(rules.get("must_keep") or [])
    may = list(rules.get("may_change") or [])
    for item in (
        "face identity",
        "hair color and length",
        "default wardrobe",
        "body proportions",
    ):
        if item not in must:
            must.append(item)
    # Remove free outfit drift on default path; alt1 is intentional variant
    may = [m for m in may if m not in ("outfit", "wardrobe", "clothing")]
    for item in ("lighting", "background", "pose", "expression", "camera angle"):
        if item not in may:
            may.append(item)
    if "wardrobe_alt1 intentional only" not in may:
        may.append("wardrobe_alt1 intentional only")
    rules["must_keep"] = must
    rules["may_change"] = may


def set_wardrobe(
    bible: dict,
    *,
    wardrobe_default: str | None = None,
    wardrobe_alt1: str | None = None,
    props_default: str | None = None,
    props_notes: str | None = None,
    lock: bool = True,
) -> dict[str, Any]:
    app = appearance_block(bible)
    if wardrobe_default is not None:
        app["wardrobe_default"] = wardrobe_default.strip()
    if wardrobe_alt1 is not None:
        app["wardrobe_alt1"] = wardrobe_alt1.strip()
    if props_default is not None:
        app["props_default"] = props_default.strip()
    if props_notes is not None:
        app["props_notes"] = props_notes.strip()
    if lock:
        app["wardrobe_locked"] = True
        app["wardrobe_locked_at"] = utc_now_iso()
        apply_consistency_for_locked_wardrobe(bible)
    bible["updated_at"] = utc_now_iso()
    return wardrobe_status(bible)


def wearing_clause(wardrobe: str) -> str:
    w = (wardrobe or "").strip()
    if not w:
        return "fully clothed"
    if w.lower().startswith("wearing "):
        return f"{w}, fully clothed"
    return f"wearing {w}, fully clothed"


def inject_instruction_for_preset(
    preset_id: str,
    preset: dict,
    instruction: str,
    bible: dict,
) -> str:
    """Rewrite sheet instructions to lock wardrobe/props from bible."""
    sheet = str(preset.get("sheet") or "")
    default = get_wardrobe_default(bible)
    alt1 = get_wardrobe_alt1(bible)
    props = get_props_default(
        bible,
        fallback="simple closed black umbrella held in one hand at realistic scale",
    )
    wear = wearing_clause(default) if default else "fully clothed"
    base = (instruction or "").strip()

    # --- off-body design plates (no person) ---
    if preset_id == "costume.flat_front":
        if default:
            return (
                f"costume design flat lay FRONT view, empty clothing only NO person NO face, "
                f"garments arranged: {default}, laid flat on seamless gray surface, "
                f"product catalog photo, shoes beside outfit if applicable"
            )
        return base

    if preset_id == "costume.flat_back":
        if default:
            return (
                f"costume design flat lay BACK view, empty clothing only NO person NO face, "
                f"back of garments: {default}, laid flat, seams and back construction visible, "
                f"product catalog photo"
            )
        return base

    if preset_id == "costume.callout":
        if default:
            return (
                f"costume construction CALLOUT design sheet for wardrobe: {default}, "
                f"multiple close-up panels of fabric collar sleeve cuff buttons hem footwear accessory, "
                f"NO person NO face, product macro design reference"
            )
        return base

    def _prop_object_only(text: str) -> str:
        """Strip on-model holding phrases for empty prop product plates."""
        t = (text or "").strip()
        for frag in (
            "held in the right hand",
            "held in the left hand",
            "held in one hand",
            "held in hand",
            "at realistic human scale",
            "clear hand grip",
            "in the right hand",
            "in the left hand",
        ):
            t = t.replace(frag, "")
        return " ".join(t.split()).strip(" ,")

    if preset_id == "props.hero":
        pobj = _prop_object_only(props) or props
        return (
            f"hero product photograph of prop object alone: {pobj}, "
            f"no person, no hands, no fingers, centered on seamless gray background, "
            f"sharp material detail, character prop design sheet"
        )

    if preset_id == "props.turn_3view":
        pobj = _prop_object_only(props) or props
        return (
            f"prop turnaround design sheet, three views left-to-right FRONT | SIDE | BACK "
            f"of the same prop object: {pobj}, empty product only no person no hands, "
            f"orthographic prop model sheet, consistent scale"
        )

    if preset_id == "costume.default" or (
        sheet == "costume" and str(preset.get("variant") or "") == "default_outfit"
    ):
        if default:
            return (
                f"same exact person, full body standing costume sheet, {wear}, "
                f"default wardrobe locked: {default}, match approved costume design flat colors "
                f"and construction, head-to-toe visible, plain studio"
            )
        return base

    if preset_id == "costume.alt1" or (
        sheet == "costume" and "alt1" in str(preset.get("variant") or "")
    ):
        outfit = alt1 or default
        if outfit:
            return (
                f"same exact person, full body standing costume sheet, alternate outfit: "
                f"{outfit}, fully clothed, head-to-toe visible, plain studio"
            )
        return base

    if preset_id == "costume.detail_upper":
        if default:
            return (
                f"same exact person, costume DETAIL plate, tight crop waist-up, "
                f"focus on collar fabric weave sleeves and fit of: {default}, "
                f"garment construction clear, face partially visible for identity, "
                f"not a distant full-body shot"
            )
        return base

    if preset_id == "costume.detail_footwear":
        if default:
            return (
                f"same character costume FOOTWEAR detail plate, tight crop lower legs and shoes only, "
                f"footwear and hem from wardrobe: {default}, product-photo construction detail, "
                f"no full-body portrait, face not required"
            )
        return base

    if preset_id == "costume.detail_accessories":
        if default:
            return (
                f"same exact person, ACCESSORIES detail plate, close crop ears neck wrists hands, "
                f"accessories and jewelry from wardrobe: {default}, still fully clothed in that outfit, "
                f"identity consistent, not nude, not bare-shoulder fashion crop unless wardrobe says so"
            )
        return base

    if preset_id == "props.hand_item" or (
        sheet == "props" and str(preset.get("variant") or "") == "hand_item"
    ):
        return (
            f"same exact person, prop scale reference, waist-up or half body, "
            f"{wear}, holding or interacting with prop: {props}, "
            f"match prop_hero design if available, clear hand-prop contact and realistic scale, "
            f"model sheet prop plate"
        )

    if sheet == "props" or preset_id.startswith("props."):
        return (
            f"prop design plate: {props}, product photography, "
            f"no person unless specified"
        )

    if sheet in ("pose", "turnaround") or preset_id.startswith("pose."):
        # Keep original action wording; append wardrobe lock
        if default:
            if "wearing" not in base.lower() and default.lower() not in base.lower():
                return f"{base}, {wear}".strip(", ")
        return base or f"same exact person, full body, {wear}"

    if sheet == "head":
        return base  # face-only; wardrobe optional

    return base


def prefer_dressed_fullbody_path(pkg) -> str | None:
    """Prefer approved costume_default → master_full for body sheets."""
    import os

    for rel in (
        ("approved", "costume_default.png"),
        ("approved", "master_full.png"),
        ("approved", "master_full_body.png"),
    ):
        p = pkg.path(*rel)
        if os.path.isfile(p):
            return p
    # latest costume default ref
    root = pkg.path("refs", "costume")
    if os.path.isdir(root):
        cands = []
        for name in os.listdir(root):
            low = name.lower()
            if not low.endswith((".png", ".jpg", ".jpeg", ".webp")):
                continue
            if "default" in low or "default_outfit" in low:
                cands.append((os.path.getmtime(os.path.join(root, name)), os.path.join(root, name)))
        if cands:
            cands.sort(reverse=True)
            return cands[0][1]
    return None
