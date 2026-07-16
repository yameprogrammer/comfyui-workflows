"""Comfy engine-family session: free memory only when the model family changes.

Policy (default AGENT_COMFY_FREE_POLICY=on_switch):
  - Same family as last successful ensure → no free (e.g. LTX S02→S03→S04)
  - Different family (Moody I2I → LTX) → unload + free + memory gate
  - never / always overrides via env

CLI processes are short-lived, so last-family state is persisted on disk under
.agent_cache/comfy_engine_session.json (repo root).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from lib.comfy_client import (
    DEFAULT_SERVER,
    WORKSPACE_ROOT,
    free_comfy_memory,
    get_queue,
    memory_snapshot,
    utc_now_iso,
)

# --- Engine families (weights / TE stacks that should not share hot VRAM) ---

FAMILY_MOODY = "moody_still"  # ZImage / Lumina2 T2I I2I ControlNet
FAMILY_LTX = "ltx"  # LTX 2.3 GGUF + Gemma TE + dual VAE
FAMILY_INFINITETALK = "infinitetalk"
FAMILY_WAN = "wan"  # Wan2.2 I2V
FAMILY_ACE = "ace_step"  # BGM
FAMILY_QWEN_EDIT = "qwen_edit_2509"  # Qwen-Image-Edit-2509 instruction edit (fp8 + VL)
FAMILY_QWEN_ANGLE = "qwen_edit_2511_angle"  # Qwen-Image-Edit-2511 multi-angle (GGUF + Angles LoRA)
FAMILY_OTHER = "other"

# Optional minimum free memory after switch free (env overrides)
DEFAULT_MIN_RAM_FREE_GB = 12.0
DEFAULT_MIN_VRAM_FREE_MB = 4000.0

SESSION_PATH = os.path.join(WORKSPACE_ROOT, ".agent_cache", "comfy_engine_session.json")


def resolve_free_policy(explicit: str | None = None) -> str:
    """on_switch (default) | always | never"""
    raw = (explicit or os.environ.get("AGENT_COMFY_FREE_POLICY") or "on_switch").strip().lower()
    if raw in ("on_switch", "switch", "family"):
        return "on_switch"
    if raw in ("always", "every", "each"):
        return "always"
    if raw in ("never", "off", "0", "false", "no"):
        return "never"
    return "on_switch"


def family_for_s2v_backend(backend: str) -> str:
    b = (backend or "").strip().lower()
    if b == "infinitetalk":
        return FAMILY_INFINITETALK
    if b.startswith("ltx") or "ltx" in b:
        return FAMILY_LTX
    return FAMILY_OTHER


def family_for_i2v_backend(backend: str) -> str:
    b = (backend or "").strip().lower()
    if "wan" in b:
        return FAMILY_WAN
    if b.startswith("ltx") or "ltx" in b:
        return FAMILY_LTX
    return FAMILY_OTHER


def _load_session() -> dict[str, Any]:
    try:
        if os.path.isfile(SESSION_PATH):
            with open(SESSION_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _save_session(data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(SESSION_PATH), exist_ok=True)
    tmp = SESSION_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SESSION_PATH)


def get_last_family() -> str | None:
    fam = _load_session().get("last_family")
    return str(fam) if fam else None


def _thresholds() -> tuple[float, float]:
    ram = float(os.environ.get("AGENT_COMFY_MIN_RAM_FREE_GB", DEFAULT_MIN_RAM_FREE_GB))
    vram = float(os.environ.get("AGENT_COMFY_MIN_VRAM_FREE_MB", DEFAULT_MIN_VRAM_FREE_MB))
    return ram, vram


def _queue_busy(server_address: str) -> bool:
    try:
        q = get_queue(server_address)
        running = q.get("queue_running") or []
        pending = q.get("queue_pending") or []
        return bool(running) or bool(pending)
    except Exception:
        return False


def free_and_verify(
    server_address: str = DEFAULT_SERVER,
    *,
    wait_idle_sec: float = 5.0,
    free_twice: bool = True,
    enforce_threshold: bool = True,
) -> dict[str, Any]:
    """Unload models, free cache, snapshot memory. Does not change last_family."""
    t0 = time.time()
    deadline = t0 + max(0.0, wait_idle_sec)
    while time.time() < deadline and _queue_busy(server_address):
        time.sleep(0.4)

    before = memory_snapshot(server_address)
    free_comfy_memory(server_address, unload_models=True, free_memory=True)
    time.sleep(0.8)
    if free_twice:
        free_comfy_memory(server_address, unload_models=True, free_memory=True)
        time.sleep(0.5)
    after = memory_snapshot(server_address)

    min_ram, min_vram = _thresholds()
    ok = True
    reasons: list[str] = []
    if enforce_threshold:
        if after["ram_free_gb"] < min_ram:
            ok = False
            reasons.append(
                f"ram_free {after['ram_free_gb']:.1f}GB < min {min_ram:.1f}GB"
            )
        if after["vram_free_mb"] < min_vram:
            ok = False
            reasons.append(
                f"vram_free {after['vram_free_mb']:.0f}MB < min {min_vram:.0f}MB"
            )

    return {
        "ok": ok,
        "freed": True,
        "before": {
            "ram_free_gb": before["ram_free_gb"],
            "vram_free_mb": before["vram_free_mb"],
        },
        "after": {
            "ram_free_gb": after["ram_free_gb"],
            "vram_free_mb": after["vram_free_mb"],
        },
        "min_ram_free_gb": min_ram,
        "min_vram_free_mb": min_vram,
        "reasons": reasons,
        "elapsed_sec": round(time.time() - t0, 2),
    }


def ensure_engine(
    family: str,
    server_address: str = DEFAULT_SERVER,
    *,
    policy: str | None = None,
    force_free: bool = False,
    enforce_threshold: bool = True,
    caller: str | None = None,
) -> dict[str, Any]:
    """Ensure Comfy is ready for this engine family.

    Returns meta dict (always includes ok, family, action, last_family).
    On policy on_switch + same family → action=skip_same_family, ok=True.
    On free failure vs thresholds → ok=False (caller should abort).
    """
    family = (family or FAMILY_OTHER).strip().lower()
    pol = resolve_free_policy(policy)
    last = get_last_family()
    switched = last is not None and last != family
    need_free = force_free or pol == "always" or (pol == "on_switch" and switched)

    # First call in a cold session: no free (Comfy may already be clean)
    if pol == "on_switch" and last is None and not force_free:
        need_free = False

    result: dict[str, Any] = {
        "ok": True,
        "family": family,
        "last_family": last,
        "policy": pol,
        "action": "none",
        "switched": switched,
        "caller": caller,
        "at": utc_now_iso(),
    }

    if pol == "never" and not force_free:
        result["action"] = "skip_policy_never"
        _save_session(
            {
                "last_family": family,
                "updated_at": utc_now_iso(),
                "last_action": result["action"],
                "server": server_address,
            }
        )
        print(f"[comfy-engine] family={family} action=skip_policy_never (prev={last})")
        return result

    if not need_free:
        result["action"] = "skip_same_family" if last == family else "skip_cold_start"
        try:
            snap = memory_snapshot(server_address)
            result["memory"] = {
                "ram_free_gb": snap["ram_free_gb"],
                "vram_free_mb": snap["vram_free_mb"],
            }
        except Exception as e:
            result["memory_error"] = str(e)
        _save_session(
            {
                "last_family": family,
                "updated_at": utc_now_iso(),
                "last_action": result["action"],
                "server": server_address,
            }
        )
        print(
            f"[comfy-engine] family={family} action={result['action']} "
            f"(prev={last}) mem={result.get('memory')}"
        )
        return result

    # Free path
    result["action"] = "free_on_switch" if switched else "free_always"
    print(
        f"[comfy-engine] family={family} action={result['action']} "
        f"(prev={last}) → unload + free…"
    )
    try:
        fr = free_and_verify(
            server_address,
            enforce_threshold=enforce_threshold,
        )
        result["free"] = fr
        result["ok"] = bool(fr.get("ok", True))
        if not result["ok"]:
            result["error"] = "MEMORY_GATE"
            result["message"] = "; ".join(fr.get("reasons") or ["memory gate failed"])
            print(f"[comfy-engine] MEMORY GATE FAIL: {result['message']}")
            # Do not update last_family on failed gate — next call retries free
            return result
        print(
            f"[comfy-engine] free OK "
            f"RAM {fr['before']['ram_free_gb']:.1f}→{fr['after']['ram_free_gb']:.1f}GB "
            f"VRAM {fr['before']['vram_free_mb']:.0f}→{fr['after']['vram_free_mb']:.0f}MB"
        )
    except Exception as e:
        result["ok"] = False
        result["error"] = "FREE_FAILED"
        result["message"] = str(e)
        print(f"[comfy-engine] free failed: {e}")
        return result

    _save_session(
        {
            "last_family": family,
            "updated_at": utc_now_iso(),
            "last_action": result["action"],
            "server": server_address,
            "last_free": result.get("free"),
        }
    )
    return result


def mark_family(family: str, server_address: str = DEFAULT_SERVER) -> None:
    """Record family without free (e.g. after manual Comfy restart)."""
    _save_session(
        {
            "last_family": (family or FAMILY_OTHER).strip().lower(),
            "updated_at": utc_now_iso(),
            "last_action": "mark_only",
            "server": server_address,
        }
    )
