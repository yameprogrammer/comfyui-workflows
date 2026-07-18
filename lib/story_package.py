"""Episode / shots.json helpers for storyboard pipeline."""

from __future__ import annotations

import json
import os
import re
import shutil
from typing import Any

from lib.comfy_client import WORKSPACE_ROOT, utc_now_iso
from lib.prompt_assembly import load_text
from lib.video_backends import get_format, get_preset, load_video_backends

STORIES_DIR = os.path.join(WORKSPACE_ROOT, "stories")
TEMPLATE_DIR = os.path.join(STORIES_DIR, "_template")
LOOKS_DIR = os.path.join(WORKSPACE_ROOT, "looks")
SHOT_TYPES_PATH = os.path.join(STORIES_DIR, "shot_type_presets.json")

ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_episode_id(episode_id: str) -> bool:
    return bool(ID_RE.match(episode_id))


def package_dir(episode_id: str) -> str:
    return os.path.join(STORIES_DIR, episode_id)


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: dict) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def copy_template(episode_id: str, force: bool = False) -> str:
    dest = package_dir(episode_id)
    if os.path.exists(dest):
        if not force:
            raise FileExistsError(dest)
        shutil.rmtree(dest)
    if not os.path.isdir(TEMPLATE_DIR):
        raise FileNotFoundError(TEMPLATE_DIR)
    shutil.copytree(TEMPLATE_DIR, dest)
    return dest


def load_shot_types() -> dict:
    if not os.path.isfile(SHOT_TYPES_PATH):
        return {}
    return load_json(SHOT_TYPES_PATH).get("shot_types") or {}


def load_look_cores(look_id: str) -> tuple[str, str]:
    """Load look cores; prefer lib.look_package (validates non-empty positive)."""
    try:
        from lib.look_package import load_look_cores as _ll

        return _ll(look_id)
    except Exception:
        root = os.path.join(LOOKS_DIR, look_id)
        if not os.path.isdir(root):
            raise FileNotFoundError(f"look not found: {look_id}")
        pos = load_text(os.path.join(root, "prompts", "positive_core.txt"))
        neg = load_text(os.path.join(root, "prompts", "negative_core.txt"))
        return pos, neg


def resolve_work_size(format_id: str, work_preset: str | None = None) -> tuple[int, int, str, str]:
    """Return width, height, format_id, work_preset_id."""
    cfg = load_video_backends()
    fmt = get_format(format_id, cfg)
    preset_id = work_preset or fmt.get("default_work_preset") or cfg.get("default_work_preset")
    if not preset_id:
        raise ValueError(f"No work preset for format {format_id}")
    pr = get_preset(str(preset_id), cfg)
    return int(pr["width"]), int(pr["height"]), format_id, str(preset_id)


class StoryPackage:
    def __init__(self, episode_id: str):
        self.episode_id = episode_id
        self.root = package_dir(episode_id)
        if not os.path.isdir(self.root):
            raise FileNotFoundError(self.root)
        self.shots_path = os.path.join(self.root, "shots.json")
        self.doc = load_json(self.shots_path)

    @classmethod
    def load(cls, episode_id: str) -> "StoryPackage":
        return cls(episode_id)

    def save(self) -> None:
        save_json(self.shots_path, self.doc)

    def path(self, *parts: str) -> str:
        return os.path.join(self.root, *parts)

    def format_id(self) -> str:
        return str(self.doc.get("format") or "cinematic_16x9")

    def look_id(self) -> str:
        return str(self.doc.get("look_id") or "cinematic_moody_v1")

    def shots(self) -> list[dict[str, Any]]:
        return list(self.doc.get("shots") or [])

    def get_shot(self, shot_id: str) -> dict[str, Any]:
        for s in self.shots():
            if s.get("shot_id") == shot_id:
                return s
        raise KeyError(shot_id)

    def update_shot(self, shot_id: str, **fields: Any) -> dict[str, Any]:
        for s in self.doc.setdefault("shots", []):
            if s.get("shot_id") == shot_id:
                s.update(fields)
                self.save()
                return s
        raise KeyError(shot_id)

    def ensure_shot(
        self,
        shot_id: str,
        *,
        action: str,
        order: int | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        try:
            s = self.get_shot(shot_id)
            if action:
                s["action"] = action
            s.update({k: v for k, v in fields.items() if v is not None})
            self.save()
            return s
        except KeyError:
            shots = self.doc.setdefault("shots", [])
            ord_ = order if order is not None else (len(shots) + 1)
            rec = {
                "shot_id": shot_id,
                "scene_id": fields.get("scene_id") or "SC01",
                "order": ord_,
                "duration_sec": fields.get("duration_sec") or 4,
                "shot_type": fields.get("shot_type") or "medium",
                "camera": fields.get("camera")
                or {"angle": "eye_level", "move": "static", "lens_feel": "35mm"},
                "action": action,
                "dialogue": fields.get("dialogue") or "",
                "vo": fields.get("vo") or "",
                "sfx": fields.get("sfx") or [],
                "music_cue": fields.get("music_cue") or "",
                "character_ids": fields.get("character_ids") or [],
                "character_refs": fields.get("character_refs") or {},
                "location_id": fields.get("location_id"),
                "location_ref": fields.get("location_ref"),
                "lighting": fields.get("lighting") or "",
                "appearance_prompt": "",
                "motion_prompt": fields.get("motion_prompt")
                or "gentle natural motion, cinematic camera",
                "motion_preset": fields.get("motion_preset")
                or fields.get("i2v_motion_preset"),
                "negative_motion": fields.get("negative_motion")
                or "warp, identity morph, flicker, morphing face",
                "board_panel": f"boards/panels/{shot_id}.png",
                "keyframe": f"keyframes/{shot_id}.png",
                "keyframe_status": "missing",
                "clip_work": f"clips/work/{shot_id}.mp4",
                "clip_deliver": f"clips/deliver/{shot_id}.mp4",
                "seed": None,
                "continuity": fields.get("continuity") or {},
            }
            # strip Nones already handled
            shots.append(rec)
            self.save()
            return rec

    def list_shot_ids(self) -> list[str]:
        return [s["shot_id"] for s in sorted(self.shots(), key=lambda x: x.get("order", 0))]
