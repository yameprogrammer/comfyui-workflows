"""Report missing node types for Lonecat AIO vs live ComfyUI object_info."""
from __future__ import annotations

import json
import urllib.request
from collections import Counter
from pathlib import Path

WF = Path(
    r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows"
    r"\Lonecat's AIO Z-Image ver 17.json"
)


def main() -> None:
    ui = json.loads(WF.read_text(encoding="utf-8"))
    types = Counter(n.get("type") for n in ui["nodes"])
    info = json.loads(
        urllib.request.urlopen("http://127.0.0.1:8188/object_info", timeout=120).read()
    )
    missing = []
    present = []
    for t, c in types.most_common():
        if t in info:
            present.append((t, c))
        else:
            missing.append((t, c))
    print(f"workflow types: {len(types)}")
    print(f"present: {len(present)} missing: {len(missing)}")
    print("\n=== MISSING (will break queue) ===")
    for t, c in missing:
        print(f"  {c:4}x  {t}")
    print("\n=== PRESENT top ===")
    for t, c in present[:30]:
        print(f"  {c:4}x  {t}")


if __name__ == "__main__":
    main()
