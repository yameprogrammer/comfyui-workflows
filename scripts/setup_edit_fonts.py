#!/usr/bin/env python3
"""Fetch OFL Hangul display fonts for EDIT title aliases.

  python scripts/setup_edit_fonts.py
  python scripts/setup_edit_fonts.py --status

Writes third_party/fonts/ (gitignored). Aliases: yeonung, hook, soft, display.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys
import urllib.request

from lib.comfy_client import ok_result
from lib.edit_fonts import PACK_DIR, PACK_FONTS, pack_path, pack_status


def _download(url: str, dest: str) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    print(f"[setup] GET {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "agent_custom-edit-fonts"})
    with urllib.request.urlopen(req, timeout=180) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk)
    os.replace(tmp, dest)


def setup() -> dict:
    os.makedirs(PACK_DIR, exist_ok=True)
    for name, url in PACK_FONTS.items():
        dest = pack_path(name)
        if os.path.isfile(dest) and os.path.getsize(dest) > 10_000:
            print(f"[setup] have {name}")
            continue
        _download(url, dest)
        print(f"[setup] → {dest} ({os.path.getsize(dest)} bytes)")
    return pack_status()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="EDIT 한글 디스플레이 폰트 (OFL)")
    p.add_argument("--status", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    if args.status:
        st = pack_status()
    else:
        st = setup()
    if args.json:
        print(json.dumps(ok_result(tool="setup_edit_fonts", **st), indent=2, ensure_ascii=False))
    else:
        for f in st["files"]:
            mark = "ok" if f["ready"] else "MISSING"
            print(f"{mark}\t{f['name']}\t{f['path']}")
        print("aliases:")
        for a in st["aliases"]:
            mark = "ok" if a["ready"] else "fallback-missing"
            print(f"  {mark}\t{a['name']}\t{a['use']}\t{a['path'] or '-'}")
    return 0 if all(f["ready"] for f in st["files"]) or args.status else 1


if __name__ == "__main__":
    sys.exit(main())
