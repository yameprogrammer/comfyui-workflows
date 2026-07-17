"""Factory floor cleanup — staging may exist; consumers must export then tidy.

Lifecycle:
  1) generate into factory staging (stories/, F:/generated_*, Comfy output)
  2) export to AGENT_WORKSPACE
  3) factory_cleanup (this module) — remove disposable smoke/dumps; optional episode

Never deletes characters/, locations/, looks/, workflows/, skills/ packages.
"""

from __future__ import annotations

import os
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from lib.comfy_client import WORKSPACE_ROOT

# Loose dumps outside the repo (this machine's historical defaults)
DEFAULT_DUMP_DIRS = [
    r"F:\generated_images",
    r"F:\generated_videos",
]

# Filename prefixes / patterns considered disposable smoke in dump dirs
SMOKE_NAME_RE = re.compile(
    r"(?i)("
    r"^ab_|"
    r"^flf_smoke|"
    r"^agent_i2v_|"
    r"^agent_flf_|"
    r"^agent_ltx_|"
    r"^wf_api_|"
    r"^lonecat_|"
    r"^output_|"
    r"^qwen_|"
    r"^face_enh|"
    r"^wan_up|"
    r"smoke"
    r")"
)

COMFY_INPUT_DIR = Path(
    os.environ.get("COMFYUI_INPUT_DIR")
    or r"F:\ComfyUI_windows_portable\ComfyUI\input"
)
COMFY_OUTPUT_DIR = Path(
    os.environ.get("COMFYUI_OUTPUT_DIR")
    or r"F:\ComfyUI_windows_portable\ComfyUI\output"
)

# temp_* copies agents drop into Comfy input
COMFY_INPUT_TEMP_RE = re.compile(r"(?i)^(temp_|wf_api_|agent_)")


@dataclass
class CleanupPlan:
    roots_scanned: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    dirs: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    bytes_total: int = 0

    def add_file(self, path: Path) -> None:
        try:
            size = path.stat().st_size if path.is_file() else 0
        except OSError:
            size = 0
        self.files.append(str(path))
        self.bytes_total += size

    def add_dir(self, path: Path) -> None:
        self.dirs.append(str(path))
        try:
            for root, _ds, fs in os.walk(path):
                for f in fs:
                    try:
                        self.bytes_total += (Path(root) / f).stat().st_size
                    except OSError:
                        pass
        except OSError:
            pass

    def to_dict(self) -> dict[str, Any]:
        return {
            "roots_scanned": self.roots_scanned,
            "files": len(self.files),
            "dirs": len(self.dirs),
            "file_samples": self.files[:40],
            "dir_samples": self.dirs[:20],
            "skipped": self.skipped[:30],
            "errors": self.errors,
            "bytes_total": self.bytes_total,
            "mb_total": round(self.bytes_total / (1024 * 1024), 2),
        }


def _older_than(path: Path, min_age_hours: float) -> bool:
    if min_age_hours <= 0:
        return True
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return False
    return (time.time() - mtime) >= min_age_hours * 3600


def plan_smoke_dumps(
    *,
    dump_dirs: Iterable[str] | None = None,
    min_age_hours: float = 0,
    include_all_in_ab_dirs: bool = True,
) -> CleanupPlan:
    """Disposable files under F:/generated_* and similar dump roots."""
    plan = CleanupPlan()
    for d in dump_dirs or DEFAULT_DUMP_DIRS:
        root = Path(d)
        plan.roots_scanned.append(str(root))
        if not root.is_dir():
            plan.skipped.append(f"missing:{root}")
            continue
        # ab_* subdirs: whole directory candidates
        try:
            for child in root.iterdir():
                if not _older_than(child, min_age_hours):
                    plan.skipped.append(f"too_new:{child}")
                    continue
                name = child.name
                if child.is_dir() and (
                    name.startswith("ab_")
                    or "smoke" in name.lower()
                    or name.startswith("flf_")
                ):
                    if include_all_in_ab_dirs:
                        plan.add_dir(child)
                    continue
                if child.is_file() and SMOKE_NAME_RE.search(name):
                    plan.add_file(child)
        except OSError as e:
            plan.errors.append(f"{root}: {e}")
    return plan


def plan_comfy_temps(*, min_age_hours: float = 0) -> CleanupPlan:
    """temp_/agent_/wf_api_ copies in Comfy input (+ optional agent_* in output)."""
    plan = CleanupPlan()
    for root, kind in ((COMFY_INPUT_DIR, "input"), (COMFY_OUTPUT_DIR, "output")):
        plan.roots_scanned.append(str(root))
        if not root.is_dir():
            plan.skipped.append(f"missing:{root}")
            continue
        try:
            for child in root.iterdir():
                if not child.is_file():
                    continue
                if kind == "input" and not COMFY_INPUT_TEMP_RE.search(child.name):
                    continue
                if kind == "output" and not re.search(
                    r"(?i)^(agent_|wf_api_)", child.name
                ):
                    continue
                if not _older_than(child, min_age_hours):
                    plan.skipped.append(f"too_new:{child}")
                    continue
                plan.add_file(child)
        except OSError as e:
            plan.errors.append(f"{root}: {e}")
    return plan


def plan_archive_logs() -> CleanupPlan:
    """scripts/_archive/tmp/*.out.txt investigation logs."""
    plan = CleanupPlan()
    root = Path(WORKSPACE_ROOT) / "scripts" / "_archive" / "tmp"
    plan.roots_scanned.append(str(root))
    if not root.is_dir():
        plan.skipped.append(f"missing:{root}")
        return plan
    for p in root.glob("*.out.txt"):
        plan.add_file(p)
    for p in root.glob("*_ports.out.txt"):
        plan.add_file(p)
    return plan


def plan_preset_backups() -> CleanupPlan:
    plan = CleanupPlan()
    root = Path(WORKSPACE_ROOT) / "workflows" / "agent" / "presets" / "_backup_colon"
    plan.roots_scanned.append(str(root))
    if root.is_dir():
        plan.add_dir(root)
    else:
        plan.skipped.append(f"missing:{root}")
    return plan


def plan_episode_staging(
    episode_id: str,
    *,
    require_export_marker: bool = True,
) -> CleanupPlan:
    """
    Optional wipe of stories/<ep>/ after export.

    Safety: if require_export_marker, looks for meta/workspace_export.json
    or env AGENT_CLEANUP_FORCE_EPISODE=1.
    """
    plan = CleanupPlan()
    ep = (episode_id or "").strip()
    root = Path(WORKSPACE_ROOT) / "stories" / ep
    plan.roots_scanned.append(str(root))
    if not root.is_dir():
        plan.errors.append(f"episode missing: {root}")
        return plan
    if require_export_marker:
        marker = root / "meta" / "workspace_export.json"
        force = (os.environ.get("AGENT_CLEANUP_FORCE_EPISODE") or "").strip() in (
            "1",
            "true",
            "yes",
        )
        if not marker.is_file() and not force:
            plan.errors.append(
                f"refuse episode cleanup without {marker} "
                f"(export first, or AGENT_CLEANUP_FORCE_EPISODE=1)"
            )
            return plan
    plan.add_dir(root)
    return plan


def merge_plans(*plans: CleanupPlan) -> CleanupPlan:
    out = CleanupPlan()
    seen_f: set[str] = set()
    seen_d: set[str] = set()
    for p in plans:
        out.roots_scanned.extend(p.roots_scanned)
        out.skipped.extend(p.skipped)
        out.errors.extend(p.errors)
        for f in p.files:
            if f not in seen_f:
                seen_f.add(f)
                out.files.append(f)
        for d in p.dirs:
            if d not in seen_d:
                seen_d.add(d)
                out.dirs.append(d)
        out.bytes_total += p.bytes_total
    return out


def execute_plan(plan: CleanupPlan, *, dry_run: bool = True) -> dict[str, Any]:
    deleted_files = 0
    deleted_dirs = 0
    errors = list(plan.errors)
    if dry_run:
        return {
            "dry_run": True,
            "would_delete_files": len(plan.files),
            "would_delete_dirs": len(plan.dirs),
            "mb": plan.to_dict()["mb_total"],
            "plan": plan.to_dict(),
        }
    for f in plan.files:
        try:
            Path(f).unlink(missing_ok=True)
            deleted_files += 1
        except OSError as e:
            errors.append(f"file {f}: {e}")
    # deepest dirs first
    for d in sorted(plan.dirs, key=lambda s: s.count(os.sep), reverse=True):
        try:
            shutil.rmtree(d, ignore_errors=False)
            deleted_dirs += 1
        except OSError as e:
            errors.append(f"dir {d}: {e}")
    return {
        "dry_run": False,
        "deleted_files": deleted_files,
        "deleted_dirs": deleted_dirs,
        "mb_planned": plan.to_dict()["mb_total"],
        "errors": errors,
        "plan": plan.to_dict(),
    }


def build_scope_plan(
    scope: str,
    *,
    episode_id: str | None = None,
    min_age_hours: float = 0,
) -> CleanupPlan:
    """
    scope:
      smoke   — generated_* dumps + ab_/smoke names
      comfy   — Comfy input/output agent temps
      logs    — archive tmp *.out.txt + preset backups
      session — smoke + comfy + logs (default after tool sessions)
      episode — stories/<ep> after export marker
      all     — session + (episode if given)
    """
    s = (scope or "session").strip().lower()
    plans: list[CleanupPlan] = []
    if s in ("smoke", "session", "all"):
        plans.append(plan_smoke_dumps(min_age_hours=min_age_hours))
    if s in ("comfy", "session", "all"):
        plans.append(plan_comfy_temps(min_age_hours=min_age_hours))
    if s in ("logs", "session", "all"):
        plans.append(plan_archive_logs())
        plans.append(plan_preset_backups())
    if s in ("episode", "all") and episode_id:
        plans.append(plan_episode_staging(episode_id))
    if not plans:
        p = CleanupPlan()
        p.errors.append(f"unknown scope: {scope!r}")
        return p
    return merge_plans(*plans)
