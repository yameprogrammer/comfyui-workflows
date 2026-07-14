"""Export factory episode artifacts into the consumer AGENT_WORKSPACE (P0-3).

Factory floor: stories/<ep>/ under agent_custom.
Workbench:     $AGENT_WORKSPACE/episodes/<ep>/  (or explicit --dest).

After generation (i2v/s2v/tts), call maybe_export_episode() so agents do not
leave the only copy on the factory floor.
"""

from __future__ import annotations

import os
import shutil
from typing import Any

from lib.agent_result import agent_result

# Relative paths under stories/<ep>/ to copy when present
DEFAULT_PARTS = [
    "shots.json",
    "keyframes",
    "clips/work",
    "clips/deliver",
    "audio",
    "exports/final",
    "meta",
    "board",
]

# Lighter set for mid-pipeline (after clip gen)
CLIP_PARTS = [
    "shots.json",
    "keyframes",
    "clips/work",
    "meta",
    "audio",
]

# After TTS only
AUDIO_PARTS = [
    "shots.json",
    "audio",
    "meta",
]


def resolve_workspace_root() -> str | None:
    ws = os.environ.get("AGENT_WORKSPACE") or os.environ.get("AGENT_PROJECT_DIR")
    if not ws:
        return None
    ws = ws.strip().strip('"').strip("'")
    return os.path.abspath(ws) if ws else None


def resolve_export_dest(episode_id: str, dest: str | None = None) -> str | None:
    """Explicit dest, or $AGENT_WORKSPACE/episodes/<ep>."""
    if dest:
        return os.path.abspath(dest)
    root = resolve_workspace_root()
    if not root:
        return None
    return os.path.join(root, "episodes", episode_id)


def should_auto_export(*, flag: bool | None = None) -> bool:
    """
    flag True  → always try
    flag False → never
    flag None  → auto if AGENT_WORKSPACE / AGENT_PROJECT_DIR set
                 or AGENT_EXPORT_WORKSPACE=1
    """
    if flag is True:
        return True
    if flag is False:
        return False
    env = (os.environ.get("AGENT_EXPORT_WORKSPACE") or "").strip().lower()
    if env in ("1", "true", "yes", "on"):
        return True
    if env in ("0", "false", "no", "off"):
        return False
    return resolve_workspace_root() is not None


def _copy_tree_or_file(src: str, dst: str) -> list[str]:
    copied: list[str] = []
    if not os.path.exists(src):
        return copied
    parent = os.path.dirname(dst)
    if parent:
        os.makedirs(parent, exist_ok=True)
    if os.path.isdir(src):
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        copied.append(dst)
    else:
        shutil.copy2(src, dst)
        copied.append(dst)
    return copied


def export_episode(
    episode_id: str,
    dest: str,
    *,
    parts: list[str] | None = None,
    story_root: str | None = None,
) -> dict[str, Any]:
    """Copy stories/<ep> slices into dest. Fail-soft on missing optional parts."""
    if story_root is None:
        from lib.story_package import StoryPackage

        story = StoryPackage.load(episode_id)
        src_root = story.root
    else:
        src_root = story_root

    dest = os.path.abspath(dest)
    os.makedirs(dest, exist_ok=True)

    parts = parts or list(DEFAULT_PARTS)
    copied: list[str] = []
    missing: list[str] = []
    for rel in parts:
        rel = rel.replace("\\", "/").strip("/")
        src = os.path.join(src_root, *rel.split("/"))
        dst = os.path.join(dest, *rel.split("/"))
        if not os.path.exists(src):
            missing.append(rel)
            continue
        copied.extend(_copy_tree_or_file(src, dst))

    note = os.path.join(dest, "FROM_AGENT_CUSTOM.txt")
    with open(note, "w", encoding="utf-8") as f:
        f.write(
            "Exported from agent_custom tool repo.\n"
            f"episode_id={episode_id}\n"
            f"source={src_root}\n"
            f"dest={dest}\n"
            "Edit and deliver FROM THIS DIRECTORY (or your project root).\n"
            "Do not leave the only copy under the tool repo stories/ folder.\n"
        )
    copied.append(note)

    return agent_result(
        ok=bool(copied),
        tool="workspace_export",
        episode_id=episode_id,
        error=None if copied else "NOTHING_COPIED",
        message=f"exported to {dest}",
        exit_code=0 if copied else 11,
        artifacts=[{"role": "workspace_copy", "path": dest}]
        + [{"role": "file", "path": p} for p in copied[:40]],
        extra={
            "source_root": src_root,
            "dest": dest,
            "missing_optional": missing,
            "parts": parts,
            "agent_notes": [
                "Outputs now live in YOUR workspace. Continue editing here.",
                "Tool repo stories/ is a factory floor — not the final workbench.",
            ],
        },
    )


def maybe_export_episode(
    episode_id: str,
    *,
    export_flag: bool | None = None,
    dest: str | None = None,
    parts: list[str] | None = None,
    quiet: bool = False,
) -> dict[str, Any]:
    """
    Conditionally export after generation.

    Returns result dict; skipped=True when no workspace configured / disabled.
    """
    if not should_auto_export(flag=export_flag):
        return {
            "ok": True,
            "skipped": True,
            "reason": "export_disabled",
            "message": "workspace export skipped (no flag / no AGENT_WORKSPACE)",
        }

    resolved = resolve_export_dest(episode_id, dest)
    if not resolved:
        return {
            "ok": False,
            "skipped": True,
            "error": "NO_WORKSPACE",
            "message": (
                "--export-workspace set but no --export-dest and "
                "AGENT_WORKSPACE / AGENT_PROJECT_DIR unset"
            ),
        }

    try:
        result = export_episode(episode_id, resolved, parts=parts)
    except FileNotFoundError:
        return {
            "ok": False,
            "skipped": False,
            "error": "EPISODE_MISSING",
            "message": f"episode missing: {episode_id}",
        }

    if not quiet:
        print(f"[export-workspace] dest={resolved} ok={result.get('ok')}")
        missing = (result.get("extra") or {}).get("missing_optional") or []
        if missing:
            print(f"[export-workspace] missing optional: {', '.join(missing[:12])}")
    result["skipped"] = False
    result["dest"] = resolved
    return result


def add_export_workspace_args(parser) -> None:
    """Attach standard flags to episode_* CLIs."""
    parser.add_argument(
        "--export-workspace",
        action="store_true",
        default=None,
        help="Copy outputs to AGENT_WORKSPACE/episodes/<ep> (or --export-dest) after run",
    )
    parser.add_argument(
        "--no-export-workspace",
        action="store_true",
        help="Do not auto-export even if AGENT_WORKSPACE is set",
    )
    parser.add_argument(
        "--export-dest",
        default=None,
        help="Explicit export destination directory (overrides AGENT_WORKSPACE default)",
    )


def export_flag_from_args(args) -> bool | None:
    """None = auto, True = force, False = never."""
    if getattr(args, "no_export_workspace", False):
        return False
    if getattr(args, "export_workspace", None):
        return True
    return None
