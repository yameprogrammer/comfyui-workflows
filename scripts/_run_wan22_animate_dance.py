#!/usr/bin/env python3
"""Deprecated thin wrapper — use generate_wan22_animate.py."""
from __future__ import annotations

import _bootstrap  # noqa: F401

import sys

from generate_wan22_animate import main

if __name__ == "__main__":
    print(
        "[deprecated] use: python scripts/generate_wan22_animate.py ...",
        file=sys.stderr,
    )
    raise SystemExit(main())
