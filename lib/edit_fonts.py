"""Named Hangul fonts for EDIT titles. Aliases, not file paths.

  python scripts/render_title.py --list-fonts
  python scripts/setup_edit_fonts.py
  python scripts/render_title.py --font yeonung --text "포기하지 마" -o cap.png
"""

from __future__ import annotations

import os
from typing import Any

from lib.comfy_client import WORKSPACE_ROOT

# OFL display cuts fetched by setup_edit_fonts.py (gitignored binaries).
PACK_DIR = os.path.join(WORKSPACE_ROOT, "third_party", "fonts")

# Agent-facing names. First existing candidate wins.
# "pack:Name.ttf" resolves under third_party/fonts/.
ALIASES: dict[str, dict[str, Any]] = {
    "yeonung": {
        "use": "예능·무도 본문 (굵은 디스플레이)",
        "files": ["pack:BlackHanSans-Regular.ttf", "pack:DoHyeon-Regular.ttf"],
        "system": [
            r"C:\Windows\Fonts\malgunbd.ttf",
            r"C:\Windows\Fonts\NanumGothicBold.ttf",
        ],
    },
    "hook": {
        "use": "유튜브 훅 / 큰 한 줄",
        "files": ["pack:BlackHanSans-Regular.ttf"],
        "system": [
            r"C:\Windows\Fonts\malgunbd.ttf",
            r"C:\Windows\Fonts\NanumGothicBold.ttf",
        ],
    },
    "soft": {
        "use": "둥근 예능 / 리액션",
        "files": ["pack:Jua-Regular.ttf"],
        "system": [
            r"C:\Windows\Fonts\malgun.ttf",
            r"C:\Windows\Fonts\NanumGothic.ttf",
        ],
    },
    "display": {
        "use": "제목형 고딕",
        "files": ["pack:DoHyeon-Regular.ttf", "pack:BlackHanSans-Regular.ttf"],
        "system": [r"C:\Windows\Fonts\malgunbd.ttf"],
    },
    "gothic": {
        "use": "본문 고딕 (정보·로어서드)",
        "files": [],
        "system": [
            r"C:\Windows\Fonts\malgun.ttf",
            r"C:\Windows\Fonts\NanumGothic.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        ],
    },
    "gothic_bold": {
        "use": "본문 고딕 볼드",
        "files": [],
        "system": [
            r"C:\Windows\Fonts\malgunbd.ttf",
            r"C:\Windows\Fonts\NanumGothicBold.ttf",
            r"C:\Windows\Fonts\malgun.ttf",
        ],
    },
}

# Pack files (OFL) — setup script downloads these.
PACK_FONTS: dict[str, str] = {
    "BlackHanSans-Regular.ttf": (
        "https://github.com/google/fonts/raw/main/ofl/blackhansans/BlackHanSans-Regular.ttf"
    ),
    "Jua-Regular.ttf": (
        "https://github.com/google/fonts/raw/main/ofl/jua/Jua-Regular.ttf"
    ),
    "DoHyeon-Regular.ttf": (
        "https://github.com/google/fonts/raw/main/ofl/dohyeon/DoHyeon-Regular.ttf"
    ),
}

_FALLBACK_REGULAR = [
    r"C:\Windows\Fonts\malgun.ttf",
    r"C:\Windows\Fonts\NanumGothic.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
]
_FALLBACK_BOLD = [
    r"C:\Windows\Fonts\malgunbd.ttf",
    r"C:\Windows\Fonts\NanumGothicBold.ttf",
    r"C:\Windows\Fonts\malgun.ttf",
]


def pack_path(name: str) -> str:
    return os.path.join(PACK_DIR, name)


def _exists(path: str) -> bool:
    return bool(path) and os.path.isfile(path)


def _expand(token: str) -> str:
    if token.startswith("pack:"):
        return pack_path(token[5:])
    return token


def list_fonts() -> list[dict[str, Any]]:
    rows = []
    for name, spec in ALIASES.items():
        path = resolve_alias(name)
        rows.append(
            {
                "name": name,
                "use": spec["use"],
                "ready": bool(path),
                "path": path,
            }
        )
    return rows


def resolve_alias(name: str) -> str | None:
    spec = ALIASES.get(name)
    if not spec:
        return None
    for token in list(spec.get("files") or []) + list(spec.get("system") or []):
        path = _expand(str(token))
        if _exists(path):
            return os.path.abspath(path)
    return None


def resolve_font(explicit: str | None = None, *, weight: str = "regular") -> str | None:
    """Path, alias, EDIT_FONT, or system fallback. None if nothing usable."""
    if explicit:
        raw = str(explicit).strip()
        if _exists(raw):
            return os.path.abspath(raw)
        key = raw.lower().replace("-", "_")
        if key in ALIASES:
            hit = resolve_alias(key)
            if hit:
                return hit
            return None
        env_try = os.environ.get("EDIT_FONT")
        if env_try and _exists(env_try):
            return os.path.abspath(env_try)
        return None
    env = os.environ.get("EDIT_FONT")
    if env and _exists(env):
        return os.path.abspath(env)
    cands = _FALLBACK_BOLD if weight == "bold" else _FALLBACK_REGULAR
    if weight == "bold":
        cands = cands + [c for c in _FALLBACK_REGULAR if c not in cands]
    else:
        cands = cands + [c for c in _FALLBACK_BOLD if c not in cands]
    for cand in cands:
        if _exists(cand):
            return os.path.abspath(cand)
    return None


def known_font_names() -> list[str]:
    return list(ALIASES.keys())


def pack_status() -> dict[str, Any]:
    files = []
    for name, url in PACK_FONTS.items():
        p = pack_path(name)
        files.append({"name": name, "ready": _exists(p), "path": p, "url": url})
    return {
        "dir": PACK_DIR,
        "files": files,
        "aliases": list_fonts(),
    }
