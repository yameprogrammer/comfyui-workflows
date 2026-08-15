#!/usr/bin/env python3
"""Download FluidSynth (Windows x64) + a GM soundfont for MIDI render.

  python scripts/setup_fluidsynth.py
  python scripts/setup_fluidsynth.py --status

Puts binaries under third_party/ (gitignored). generate_midi_render uses them automatically.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

from lib.comfy_client import WORKSPACE_ROOT
from lib.midi_render import find_fluidsynth, resolve_soundfont

FLUID_URL = (
    "https://github.com/FluidSynth/fluidsynth/releases/download/"
    "v2.6.0/fluidsynth-v2.6.0-win10-x64-cpp11.zip"
)
SF2_URL = (
    "https://github.com/mrbumpy409/GeneralUser-GS/raw/main/GeneralUser-GS.sf2"
)
SF2_FALLBACK = (
    "https://archive.org/download/free-soundfonts-sf2-2019-04/"
    "GeneralUser%20GS%20v1.471.sf2"
)


def _root() -> Path:
    return Path(WORKSPACE_ROOT)


def fluid_dir() -> Path:
    return _root() / "third_party" / "fluidsynth"


def sf2_path() -> Path:
    return _root() / "third_party" / "soundfonts" / "GeneralUser-GS.sf2"


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"[setup] GET {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "agent_custom-fluidsynth-setup"})
    with urllib.request.urlopen(req, timeout=180) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk)
    tmp.replace(dest)


def setup() -> dict:
    zpath = fluid_dir() / "fluidsynth-win10-x64.zip"
    if not find_fluidsynth():
        if not zpath.is_file():
            _download(FLUID_URL, zpath)
        print(f"[setup] unzip {zpath}")
        with zipfile.ZipFile(zpath) as zf:
            zf.extractall(fluid_dir())
    exe = find_fluidsynth()
    sf = resolve_soundfont()
    if not sf:
        dest = sf2_path()
        try:
            if not dest.is_file() or dest.stat().st_size < 1_000_000:
                _download(SF2_URL, dest)
        except Exception as e:
            print(f"[setup] primary sf2 failed ({e}); fallback archive.org")
            _download(SF2_FALLBACK, dest)
        sf = resolve_soundfont()
    return {
        "ok": bool(exe and sf),
        "fluidsynth": exe,
        "soundfont": sf,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Install FluidSynth + GM soundfont")
    p.add_argument("--status", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    if args.status:
        payload = {"ok": bool(find_fluidsynth() and resolve_soundfont()),
                   "fluidsynth": find_fluidsynth(),
                   "soundfont": resolve_soundfont()}
    else:
        payload = setup()
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"fluidsynth={payload.get('fluidsynth')}")
        print(f"soundfont={payload.get('soundfont')}")
        print("ok" if payload.get("ok") else "NOT READY")
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
