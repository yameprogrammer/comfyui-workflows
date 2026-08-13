"""Refuse writing finished media into the tool repo (agent_custom).

Templates/schemas live here. Project stills/clips/packages live in AGENT_WORKSPACE
or an explicit --dest / -o outside this tree.

Override (maintainers only): AGENT_ALLOW_TOOLBOX_OUTPUT=1
"""

from __future__ import annotations

import os
import sys

from lib.comfy_client import WORKSPACE_ROOT

EXIT_TOOLBOX_WRITE = 14

_BLOCKED_TOP = frozenset(
    {
        "stories",
        "characters",
        "locations",
        "dumps",
        "deliveries",
        "voices",
        "looks",
    }
)


def toolbox_root() -> str:
    return os.path.abspath(WORKSPACE_ROOT)


def project_root() -> str | None:
    for name in ("AGENT_WORKSPACE", "AGENT_PROJECT_DIR"):
        raw = os.environ.get(name)
        if raw and raw.strip():
            return os.path.abspath(raw.strip())
    return None


def allow_toolbox_output() -> bool:
    return os.environ.get("AGENT_ALLOW_TOOLBOX_OUTPUT", "").strip() in {
        "1",
        "true",
        "yes",
        "on",
    }


def is_inside_toolbox(path: str | None) -> bool:
    if not path:
        return False
    abs_path = os.path.abspath(path)
    root = toolbox_root()
    try:
        return os.path.commonpath([abs_path, root]) == root
    except ValueError:
        return False


def toolbox_write_message(path: str) -> str:
    return (
        f"Refusing to write inside the tool repo: {os.path.abspath(path)}\n"
        "agent_custom is a toolbox only. Put media in YOUR project:\n"
        "  -o / --output / --dest  <project path>\n"
        "  or set AGENT_WORKSPACE=<project root>\n"
        "Do not use stories/, dumps/, characters/<id>/, deliveries/ here."
    )


class ToolboxWriteError(ValueError):
    def __init__(self, path: str):
        super().__init__(toolbox_write_message(path))
        self.path = path
        self.exit_code = EXIT_TOOLBOX_WRITE


def assert_outside_toolbox(path: str, *, label: str = "output") -> str:
    """Return abspath, or raise ToolboxWriteError if path is under the toolbox."""
    abs_path = os.path.abspath(path)
    if allow_toolbox_output():
        return abs_path
    if is_inside_toolbox(abs_path):
        # Allow reading/writing tiny scaffolding files only if explicitly under _template
        # is still a write into the repo — block all writes including templates copies dest.
        raise ToolboxWriteError(abs_path)
    return abs_path


def die_if_toolbox(path: str) -> str:
    try:
        return assert_outside_toolbox(path)
    except ToolboxWriteError as e:
        print(f"[ERROR] code={EXIT_TOOLBOX_WRITE} {e}", file=sys.stderr)
        raise SystemExit(EXIT_TOOLBOX_WRITE) from e


def resolve_package_dir(kind: str, package_id: str, dest: str | None = None) -> str:
    """Instance dir for characters/stories/locations — never under the toolbox.

    --dest  = that folder (package root)
    else    = $AGENT_WORKSPACE/<kind>/<id>
    """
    if dest and dest.strip():
        return die_if_toolbox(dest.strip())
    root = project_root()
    if not root:
        print(
            f"[ERROR] code={EXIT_TOOLBOX_WRITE} "
            f"Need --dest or AGENT_WORKSPACE for {kind}/{package_id}. "
            "Do not create packages inside the tool repo.",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_TOOLBOX_WRITE)
    return die_if_toolbox(os.path.join(root, kind, package_id))


def resolve_media_output(path: str | None, *, default_name: str) -> str:
    """Resolve -o for generate_* . Missing -o uses $AGENT_WORKSPACE/<default_name>."""
    if path and path.strip():
        return die_if_toolbox(path.strip())
    root = project_root()
    if not root:
        print(
            f"[ERROR] code={EXIT_TOOLBOX_WRITE} "
            f"Need -o/--output or AGENT_WORKSPACE (wanted {default_name}).",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_TOOLBOX_WRITE)
    return die_if_toolbox(os.path.join(root, default_name))
