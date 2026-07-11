"""Put repo root + scripts/ on sys.path so agent CLIs can import lib and peers.

Every entrypoint under scripts/ should `import _bootstrap` before other local imports.
Run from anywhere: `python path/to/scripts/generate_moody.py ...`
"""

from __future__ import annotations

import os
import sys

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPTS_DIR)

for _p in (_ROOT, _SCRIPTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

REPO_ROOT = _ROOT
SCRIPTS_DIR = _SCRIPTS_DIR
