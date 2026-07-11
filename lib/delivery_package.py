"""Build a user-facing handoff package for one episode."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import zipfile
from datetime import datetime, timezone
from typing import Any

from lib.comfy_client import WORKSPACE_ROOT, utc_now_iso
from lib.story_package import StoryPackage

DELIVERIES_DIR = os.path.join(WORKSPACE_ROOT, "deliveries")


def _sha256(path: str, max_bytes: int = 0) -> str | None:
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        if max_bytes > 0:
            h.update(f.read(max_bytes))
        else:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
    return h.hexdigest()


def _copy_file(src: str, dest: str) -> bool:
    if not os.path.isfile(src):
        return False
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy2(src, dest)
    return True


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def resolve_clip(story: StoryPackage, shot: dict, stage: str) -> tuple[str | None, str]:
    """Return (abs_path or None, stage_used)."""
    sid = shot.get("shot_id")
    deliver_rel = shot.get("clip_deliver") or f"clips/deliver/{sid}.mp4"
    work_rel = shot.get("clip_work") or f"clips/work/{sid}.mp4"
    deliver = story.path(*deliver_rel.replace("\\", "/").split("/"))
    work = story.path(*work_rel.replace("\\", "/").split("/"))
    if stage == "deliver":
        return (deliver if os.path.isfile(deliver) else None), "deliver"
    if stage == "work":
        return (work if os.path.isfile(work) else None), "work"
    if os.path.isfile(deliver):
        return deliver, "deliver"
    if os.path.isfile(work):
        return work, "work"
    return None, "missing"


def collect_asset_refs(story: StoryPackage) -> dict[str, Any]:
    """Lightweight index of char/loc/look used — not full package copies."""
    chars: set[str] = set()
    locs: set[str] = set()
    for s in story.shots():
        for c in s.get("character_ids") or []:
            chars.add(str(c))
        lid = s.get("location_id")
        if lid:
            locs.add(str(lid))
    look_id = story.look_id()
    return {
        "look_id": look_id,
        "look_path": f"looks/{look_id}/",
        "character_ids": sorted(chars),
        "location_ids": sorted(locs),
        "note": (
            "Full character/location packages stay in the workspace under "
            "characters/ and locations/. This handoff only lists ids for continuity."
        ),
    }


def build_handoff_readme(
    *,
    episode_id: str,
    package_name: str,
    final_name: str | None,
    clip_count: int,
    still_count: int,
    format_id: str,
    look_id: str,
    stage: str,
) -> str:
    return f"""# Delivery package: {episode_id}

- **Package**: `{package_name}`
- **Created (UTC)**: {utc_now_iso()}
- **Format**: `{format_id}`
- **Look**: `{look_id}`
- **Clip stage used**: `{stage}` (auto prefers deliver over work)

## Contents

| Folder | What |
|--------|------|
| `FINAL/` | Assembled master video (if available) |
| `STILLS/` | Production keyframes per shot |
| `CLIPS/` | Per-shot video clips used in the cut |
| `MANIFEST/` | shots.json + delivery_manifest.json + asset_refs.json |
| `META/` | Selected generation meta (if present) |

## Quick open

1. Play `FINAL/{final_name or "(missing — run assemble_video first)"}`
2. Review stills in `STILLS/` for continuity
3. Machine details in `MANIFEST/delivery_manifest.json`

## Shots included

- Stills: **{still_count}**
- Clips: **{clip_count}**

## Note for the client

Character and location **source packs** are not fully duplicated here (they are large shared assets).
Ids are listed under `MANIFEST/asset_refs.json`. Ask the agent for full packs if you need re-generation.
"""


def package_episode_delivery(
    episode_id: str,
    *,
    stage: str = "auto",
    include_work_clips: bool = False,
    include_meta: bool = True,
    make_zip: bool = True,
    package_name: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Build deliveries/<package_name>/ handoff tree.

    Returns paths and file counts.
    """
    story = StoryPackage.load(episode_id)
    name = package_name or f"{episode_id}__{_stamp()}"
    root = os.path.join(DELIVERIES_DIR, name)

    final_src = None
    fe = story.doc.get("final_export") or {}
    if fe.get("path"):
        cand = story.path(*str(fe["path"]).replace("\\", "/").split("/"))
        if os.path.isfile(cand):
            final_src = cand
    # also try default assemble path
    default_final = story.path("exports", "final", f"{episode_id}_final.mp4")
    if final_src is None and os.path.isfile(default_final):
        final_src = default_final

    shots = sorted(story.shots(), key=lambda s: s.get("order", 0))
    stills: list[dict[str, Any]] = []
    clips: list[dict[str, Any]] = []

    for s in shots:
        sid = s.get("shot_id")
        kf_rel = s.get("keyframe") or f"keyframes/{sid}.png"
        kf = story.path(*kf_rel.replace("\\", "/").split("/"))
        if os.path.isfile(kf):
            stills.append({"shot_id": sid, "src": kf, "name": f"{sid}.png"})

        path, used = resolve_clip(story, s, stage)
        if path:
            clips.append(
                {
                    "shot_id": sid,
                    "src": path,
                    "stage": used,
                    "name": f"{sid}.mp4",
                }
            )
        elif include_work_clips:
            # already handled by stage=work/auto
            pass

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "package_dir": root,
            "package_name": name,
            "final": final_src,
            "stills": len(stills),
            "clips": len(clips),
            "zip": f"{root}.zip" if make_zip else None,
        }

    # build tree
    for sub in ("FINAL", "STILLS", "CLIPS", "MANIFEST", "META"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)

    final_name = None
    if final_src:
        final_name = f"{episode_id}_final.mp4"
        _copy_file(final_src, os.path.join(root, "FINAL", final_name))

    still_count = 0
    for st in stills:
        if _copy_file(st["src"], os.path.join(root, "STILLS", st["name"])):
            still_count += 1

    clip_count = 0
    for cl in clips:
        if _copy_file(cl["src"], os.path.join(root, "CLIPS", cl["name"])):
            clip_count += 1

    # shots.json copy
    shots_src = story.shots_path
    _copy_file(shots_src, os.path.join(root, "MANIFEST", "shots.json"))

    asset_refs = collect_asset_refs(story)
    with open(os.path.join(root, "MANIFEST", "asset_refs.json"), "w", encoding="utf-8") as f:
        json.dump(asset_refs, f, ensure_ascii=False, indent=2)
        f.write("\n")

    if include_meta:
        meta_dir = story.path("meta")
        if os.path.isdir(meta_dir):
            for fn in sorted(os.listdir(meta_dir)):
                if fn.lower().endswith(".json"):
                    _copy_file(
                        os.path.join(meta_dir, fn),
                        os.path.join(root, "META", fn),
                    )

    manifest = {
        "schema": "agent_custom.delivery_manifest.v1",
        "episode_id": episode_id,
        "package_name": name,
        "created_at": utc_now_iso(),
        "format": story.format_id(),
        "look_id": story.look_id(),
        "stage_preference": stage,
        "final": {
            "included": bool(final_src),
            "filename": final_name,
            "sha256": _sha256(os.path.join(root, "FINAL", final_name)) if final_name else None,
        },
        "stills": [
            {
                "shot_id": st["shot_id"],
                "filename": st["name"],
                "sha256": _sha256(os.path.join(root, "STILLS", st["name"])),
            }
            for st in stills
            if os.path.isfile(os.path.join(root, "STILLS", st["name"]))
        ],
        "clips": [
            {
                "shot_id": cl["shot_id"],
                "filename": cl["name"],
                "stage": cl["stage"],
                "sha256": _sha256(os.path.join(root, "CLIPS", cl["name"])),
            }
            for cl in clips
            if os.path.isfile(os.path.join(root, "CLIPS", cl["name"]))
        ],
        "asset_refs": asset_refs,
        "workspace_sources": {
            "episode": f"stories/{episode_id}/",
            "note": "Working tree remains in stories/; this package is a client handoff snapshot.",
        },
    }
    with open(os.path.join(root, "MANIFEST", "delivery_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")

    readme = build_handoff_readme(
        episode_id=episode_id,
        package_name=name,
        final_name=final_name,
        clip_count=clip_count,
        still_count=still_count,
        format_id=story.format_id(),
        look_id=story.look_id(),
        stage=stage,
    )
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme)

    zip_path = None
    if make_zip:
        zip_path = root + ".zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for dirpath, _dirnames, filenames in os.walk(root):
                for fn in filenames:
                    abs_f = os.path.join(dirpath, fn)
                    arc = os.path.relpath(abs_f, os.path.dirname(root))
                    zf.write(abs_f, arcname=arc)

    # record on episode
    story.doc["last_delivery"] = {
        "package_name": name,
        "package_dir": os.path.relpath(root, WORKSPACE_ROOT).replace("\\", "/"),
        "zip": os.path.relpath(zip_path, WORKSPACE_ROOT).replace("\\", "/") if zip_path else None,
        "created_at": utc_now_iso(),
    }
    story.save()

    return {
        "ok": True,
        "package_dir": root,
        "package_name": name,
        "zip_path": zip_path,
        "final_included": bool(final_src),
        "stills": still_count,
        "clips": clip_count,
        "manifest": os.path.join(root, "MANIFEST", "delivery_manifest.json"),
    }
