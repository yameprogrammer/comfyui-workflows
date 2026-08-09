#!/usr/bin/env python3
"""
Drift check: tool_intent scripts exist; planned status cannot hide ready CLIs.

Discovery only — no Comfy, no generation.

  python scripts/tool_index_check.py
  python scripts/tool_index_check.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.tool_intent import INTENT_TOOLS  # noqa: E402

_AGENT_CLI_PREFIXES = ("generate_", "upscale_", "extract_", "youtube_")


def _script_paths_from_text(text: str) -> list[str]:
    if not text:
        return []
    return re.findall(r"scripts/([A-Za-z0-9_\-]+\.py)", text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="Machine-readable summary")
    args = ap.parse_args()

    errors: list[str] = []
    warns: list[str] = []

    # --- intent cards: scripts must exist ---
    intent_scripts: set[str] = set()
    for t in INTENT_TOOLS:
        tid = t.get("id", "?")
        script = (t.get("script") or "").strip()
        if script:
            intent_scripts.add(script)
            p = ROOT / "scripts" / script
            if not p.is_file():
                errors.append(f"intent {tid}: missing scripts/{script}")
        for key in ("cli",):
            for name in _script_paths_from_text(str(t.get(key) or "")):
                intent_scripts.add(name)
                if not (ROOT / "scripts" / name).is_file():
                    errors.append(f"intent {tid}: cli references missing scripts/{name}")
        for ex in t.get("examples") or []:
            for name in _script_paths_from_text(str(ex)):
                if not (ROOT / "scripts" / name).is_file():
                    errors.append(f"intent {tid}: example references missing scripts/{name}")
        for alt in t.get("alternatives") or []:
            for name in _script_paths_from_text(str(alt.get("cli") or "")):
                if not (ROOT / "scripts" / name).is_file():
                    # alternatives may point at optional tools — warn only
                    warns.append(f"intent {tid}: alternative missing scripts/{name}")

    # --- catalog.json: planned must not hide agent CLIs ---
    cat_path = ROOT / "workflows" / "agent" / "catalog.json"
    cat = json.loads(cat_path.read_text(encoding="utf-8"))
    catalog_scripts: set[str] = set()
    for name, ent in (cat.get("workflows") or {}).items():
        status = (ent.get("status") or "").strip()
        rels: list[str] = []
        for key in ("scripts", "used_by"):
            for rel in ent.get(key) or []:
                rels.append(rel)
                catalog_scripts.add(Path(rel).name)
        if status != "planned":
            continue
        for rel in rels:
            path = ROOT / rel
            if not path.is_file():
                continue
            base = path.name
            if base.startswith(_AGENT_CLI_PREFIXES):
                errors.append(
                    f"catalog {name}: status=planned but agent CLI exists: {rel}"
                )

    # soft: intent script not listed in any catalog scripts/used_by
    for s in sorted(intent_scripts):
        if s not in catalog_scripts and s not in (
            "failure_note.py",
            "story_init.py",
            "character_full_sheet.py",
            "tool_intent.py",
        ):
            # many META/BUNDLE helpers are intentional omissions
            if s.startswith(_AGENT_CLI_PREFIXES) or s in (
                "ltx_lora_status.py",
                "youtube_ingest.py",
                "upscale_recommend.py",
            ):
                warns.append(f"intent script not in catalog scripts/used_by: {s}")

    # --- video_backends.json ---
    vb_path = ROOT / "video_backends.json"
    vb = json.loads(vb_path.read_text(encoding="utf-8"))
    for name, ent in (vb.get("backends") or {}).items():
        if (ent.get("status") or "") != "planned":
            continue
        cli = ent.get("cli")
        if not cli:
            continue
        path = ROOT / cli
        if path.is_file():
            errors.append(f"video_backends {name}: planned but cli exists: {cli}")

    summary = {
        "intent_cards": len(INTENT_TOOLS),
        "errors": errors,
        "warns": warns,
        "error_count": len(errors),
        "warn_count": len(warns),
        "ok": len(errors) == 0,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        for e in errors:
            print(f"ERROR: {e}")
        for w in warns:
            print(f"WARN:  {w}")
        print(
            f"intent_cards={len(INTENT_TOOLS)} errors={len(errors)} warns={len(warns)}"
        )
        if errors:
            print("FAIL — fix planned/ready drift or missing scripts")
        else:
            print("OK — no hard drift")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
