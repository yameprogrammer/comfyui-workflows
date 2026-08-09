"""
LTX optional LoRAs — machine-readable catalog for agents.

SSOT prose: docs/ltx_loras_agent.md
CLI: scripts/ltx_lora_status.py
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Shared model library (extra_model_paths)
LORA_ROOTS = [
    Path(r"F:\model\loras\LTX2.3"),
    Path(r"F:\ComfyUI_windows_portable\ComfyUI\models\loras\LTX2.3"),
    Path(r"F:\ComfyUI_windows_portable\ComfyUI\models\loras"),
]

# --- Asian Face (Deno) ---
ASIAN_FACE_FILES = [
    r"LTX2.3\LTX2.3_EastAsian_Facial_Fidelity_v1.safetensors",
    r"LTX2.3\ltx-face-prior-f1-profile-correction-step11019.safetensors",
    "LTX2.3_EastAsian_Facial_Fidelity_v1.safetensors",
    "ltx-face-prior-f1-profile-correction-step11019.safetensors",
]

# --- Relight IC-LoRA (Lightricks) ---
RELIGHT_FILES = [
    r"LTX2.3\ltx-2.3-22b-ic-lora-relight-1.0.safetensors",
    r"LTX2.3\LTX2.3_IC-LoRA_Relight_v1.safetensors",
    "ltx-2.3-22b-ic-lora-relight-1.0.safetensors",
    "LTX2.3_IC-LoRA_Relight_v1.safetensors",
]

RELIGHT_HF_REPO = "Lightricks/LTX-2.3-22b-IC-LoRA-Relight"
RELIGHT_HF_FILE = "ltx-2.3-22b-ic-lora-relight-1.0.safetensors"


def _resolve_lora(candidates: list[str]) -> Path | None:
    for root in LORA_ROOTS:
        if not root.exists():
            continue
        for rel in candidates:
            # full relative under loras/
            p = root / rel.replace("LTX2.3\\", "").replace("LTX2.3/", "")
            if p.is_file() and p.stat().st_size > 1_000_000:
                return p
            p2 = root / Path(rel).name
            if p2.is_file() and p2.stat().st_size > 1_000_000:
                return p2
        # also search rglob by basename
        for rel in candidates:
            name = Path(rel).name
            for hit in root.rglob(name):
                if hit.is_file() and hit.stat().st_size > 1_000_000:
                    return hit
    # F:\model\loras with LTX2.3 prefix
    base = Path(r"F:\model\loras")
    for rel in candidates:
        p = base / rel.replace("/", "\\")
        if p.is_file() and p.stat().st_size > 1_000_000:
            return p
    return None


def catalog() -> list[dict[str, Any]]:
    """Full agent-facing catalog entries."""
    asian_path = _resolve_lora(ASIAN_FACE_FILES)
    relight_path = _resolve_lora(RELIGHT_FILES)

    return [
        {
            "id": "asian_face",
            "name": "East Asian Facial Fidelity (Deno)",
            "kind": "lora",
            "base": "LTX-2.3 I2V",
            "status": "ready" if asian_path else "missing",
            "path": str(asian_path) if asian_path else None,
            "default_strength": 1.0,
            "default_on": True,
            "auto_inject": True,
            "inject": "LTX AIO PowerLora node 211 (apply_ltx_asian_face_lora)",
            "cli_flags": [
                "--ltx-asian-face / --no-ltx-asian-face",
                "--ltx-asian-face-strength",
            ],
            "env": ["AGENT_LTX_ASIAN_FACE", "AGENT_LTX_ASIAN_FACE_STRENGTH"],
            "trigger_word": None,
            "when": [
                "Asian-led LTX I2V/FLF/SI2V",
                "Camera orbit/profile face drift toward Western features",
            ],
            "when_not": [
                "Western / non-Asian lead",
                "Need character FaceID lock (use ID LoRA / still QA instead)",
                "Dance choreography quality (use wan22_animate)",
            ],
            "source": {
                "civitai": "https://civitai.com/models/2816700",
                "youtube": "https://youtu.be/9Dkd3JwkJWo",
            },
            "docs": "docs/ltx_loras_agent.md#1-asian-face--asian_face-",
        },
        {
            "id": "relight",
            "name": "LTX-2.3 IC-LoRA Relight (Lightricks)",
            "kind": "ic_lora",
            "base": "LTX-2.3-22B",
            "status": "ready" if relight_path else "gated_or_missing",
            "path": str(relight_path) if relight_path else None,
            "default_strength": 1.0,
            "default_on": False,
            "auto_inject": False,
            "inject": "Dedicated relight V2V workflow (not AIO default stack)",
            "cli": "scripts/generate_ltx_relight.py (requires weights)",
            "env": [],
            "trigger_word": "relight the video to match the light-direction ball.",
            "when": [
                "Finished exterior clip needs sun direction / magic-hour look change",
                "Episode FINISH look pass after motion approved",
            ],
            "when_not": [
                "Interior dialogue",
                "First-pass generation / dance retarget / face identity",
                "Weights missing (do not call)",
            ],
            "control": "Source video + light-direction ball top-right + caption",
            "source": {
                "huggingface": f"https://huggingface.co/{RELIGHT_HF_REPO}",
                "youtube": "https://youtu.be/OJkNlT5B-5M",
                "file": RELIGHT_HF_FILE,
            },
            "docs": "docs/ltx_loras_agent.md#2-relight-ic-lora--relight-",
            "install": (
                "hf auth login --force; accept model gate; "
                "python scripts/ltx_lora_status.py download-relight"
            ),
        },
    ]


def status_summary() -> dict[str, Any]:
    entries = catalog()
    return {
        "ok": True,
        "loras": entries,
        "ready_ids": [e["id"] for e in entries if e["status"] == "ready"],
        "blocked_ids": [e["id"] for e in entries if e["status"] != "ready"],
    }


def try_download_relight(token: str | None = None) -> dict[str, Any]:
    """Download Relight weights if HF auth + gate allow."""
    from huggingface_hub import hf_hub_download

    out_dir = Path(r"F:\model\loras\LTX2.3")
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / RELIGHT_HF_FILE
    alias = out_dir / "LTX2.3_IC-LoRA_Relight_v1.safetensors"
    tok = token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    try:
        p = hf_hub_download(
            RELIGHT_HF_REPO,
            RELIGHT_HF_FILE,
            local_dir=str(out_dir / "_hf_relight_tmp"),
            token=tok,
        )
        src = next(Path(out_dir / "_hf_relight_tmp").rglob(RELIGHT_HF_FILE))
        if not dest.exists() or dest.stat().st_size < 10_000_000:
            import shutil

            shutil.move(str(src), str(dest))
        if not alias.exists():
            try:
                os.link(dest, alias)
            except OSError:
                import shutil

                shutil.copy2(dest, alias)
        return {
            "ok": True,
            "path": str(dest),
            "size": dest.stat().st_size,
            "alias": str(alias),
        }
    except Exception as e:
        return {
            "ok": False,
            "error": type(e).__name__,
            "message": str(e),
            "hint": (
                "HF gated model: run `hf auth login --force`, open the model page, "
                "Agree and Access, then retry download-relight."
            ),
        }
