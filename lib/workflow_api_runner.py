"""
Run a ComfyUI **API-format** workflow JSON with port patches only.

No graph assembly, no convert_ui_to_api, no runtime node injection.
SSOT: workflows/agent/**/*.api.json + matching *.ports.json
"""

from __future__ import annotations

import copy
import json
import os
import random
import shutil
from pathlib import Path
from typing import Any

from lib.comfy_client import (
    DEFAULT_SERVER,
    download_image,
    extract_first_image,
    fail_result,
    get_comfy_input_dir,
    ok_result,
    queue_prompt,
    utc_now_iso,
    wait_for_history,
    write_meta,
)
from lib.workflow_paths import (
    AGENT_WORKFLOWS_DIR,
    load_catalog,
    resolve_workflow,
)

PRESETS_DIR = os.path.join(AGENT_WORKFLOWS_DIR, "presets")
FEATURE_PRESETS_PATH = os.path.join(PRESETS_DIR, "lonecat_feature_presets.json")
CAPABILITIES_PATH = os.path.join(
    AGENT_WORKFLOWS_DIR,
    "..",
    "human",
    "Lonecat_AIO_Z-Image_ver17_CAPABILITIES.json",
)
KREA2_CAPABILITIES_PATH = os.path.join(
    AGENT_WORKFLOWS_DIR,
    "..",
    "human",
    "Krea2_SFW_NSFW_v10_CAPABILITIES.json",
)


def _read_json(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_feature_presets() -> dict[str, Any]:
    if os.path.isfile(FEATURE_PRESETS_PATH):
        return _read_json(FEATURE_PRESETS_PATH)
    return {"presets": {}, "select_preset": {}}


def load_capabilities(family: str | None = None) -> dict[str, Any]:
    """Load capability map. family=krea2|zimage|None(all merged features)."""
    fam = (family or "").lower()
    if fam in ("krea2", "krea"):
        path = os.path.normpath(KREA2_CAPABILITIES_PATH)
        if not os.path.isfile(path):
            return {}
        data = _read_json(path)
        for f in data.get("features") or []:
            f.setdefault("family", "krea2")
        return data
    if fam in ("zimage", "lonecat", "z-image"):
        path = os.path.normpath(CAPABILITIES_PATH)
        if not os.path.isfile(path):
            return {}
        data = _read_json(path)
        for f in data.get("features") or []:
            f.setdefault("family", "lonecat")
        return data
    # merge feature lists for --list-features
    out: dict[str, Any] = {"features": [], "workflows": []}
    for path, label in (
        (os.path.normpath(CAPABILITIES_PATH), "lonecat"),
        (os.path.normpath(KREA2_CAPABILITIES_PATH), "krea2"),
    ):
        if not os.path.isfile(path):
            continue
        data = _read_json(path)
        out["workflows"].append(
            {
                "family": label,
                "workflow": data.get("workflow"),
                "ready_presets": data.get("ready_presets"),
                "path": path,
            }
        )
        for f in data.get("features") or []:
            f = dict(f)
            f.setdefault("family", label)
            out["features"].append(f)
        if label == "lonecat":
            out["agent_policy_lonecat"] = data.get("agent_policy")
        if label == "krea2":
            out["agent_policy_krea2"] = data.get("agent_policy")
    return out


def select_lonecat_preset(
    *,
    mode: str = "t2i",
    unet_name: str | None = None,
    feature_ids: list[str] | None = None,
    family: str | None = None,
) -> str:
    """
    Pick a catalog/feature preset name for agents.

    mode: t2i | i2i | t2i_low_vram | gguf | controlnet | cn
    family: zimage | lonecat | krea2 | krea (optional)
    unet_name: if ends with .gguf → GGUF preset; if path contains krea → krea2
    feature_ids: optional requested features (future multi-preset)
    """
    fp = load_feature_presets()
    sel = fp.get("select_preset") or {}
    presets = fp.get("presets") or {}
    by_family = sel.get("by_family") or {}

    fam = (family or "").lower().strip()
    unet_l = (unet_name or "").lower()
    if not fam:
        if "krea" in unet_l:
            fam = "krea2"
        elif unet_l.endswith(".gguf"):
            fam = "zimage"
        else:
            fam = "zimage"

    if mode in ("controlnet", "cn", "t2i_controlnet", "i2i_controlnet"):
        name = (
            sel.get("controlnet_default")
            or "zimage_fun_union_controlnet"
        )
    elif mode in ("i2i", "img2img"):
        if fam in ("krea2", "krea"):
            name = sel.get("i2i_krea2") or "krea2_i2i_v10"
        else:
            name = sel.get("i2i_default") or "lonecat_i2i_identity"
    elif fam in ("krea2", "krea"):
        name = by_family.get("krea2") or sel.get("t2i_krea2") or "krea2_t2i_v10"
    elif unet_l.endswith(".gguf") or mode in ("t2i_low_vram", "gguf"):
        name = sel.get("t2i_low_vram") or "lonecat_t2i_gguf"
    else:
        name = (
            by_family.get(fam)
            or sel.get("t2i_default")
            or "lonecat_t2i_turbo"
        )

    # If planned and not ready, fall back within family
    entry = presets.get(name) or {}
    if entry.get("status") and entry.get("status") != "ready":
        if fam in ("krea2", "krea"):
            return "krea2_t2i_v10" if "krea2_t2i_v10" in presets else "lonecat_t2i_turbo"
        return "lonecat_t2i_turbo"
    return name


def resolve_preset(name_or_path: str) -> tuple[str, str | None]:
    """
    Return (api_json_path, ports_json_path_or_none).

    Accepts:
      - catalog alias (entry.format == api)
      - path to .api.json
      - bare name under workflows/agent/presets/
    """
    raw = (name_or_path or "").strip()
    if not raw:
        raise FileNotFoundError("Empty preset name")

    catalog = load_catalog()
    workflows = catalog.get("workflows") or {}
    if raw in workflows:
        entry = workflows[raw]
        if isinstance(entry, dict) and entry.get("format") == "api":
            api_file = entry.get("file") or entry.get("workflow_api")
            ports_file = entry.get("ports")
            if not api_file:
                raise FileNotFoundError(f"Catalog {raw!r} missing file")
            # Prefer workflows/agent/ relative paths (e.g. presets/foo.api.json)
            api_path = None
            for cand in (
                api_file if os.path.isabs(api_file) else None,
                os.path.join(AGENT_WORKFLOWS_DIR, api_file),
                os.path.join(PRESETS_DIR, os.path.basename(api_file)),
            ):
                if cand and os.path.isfile(cand):
                    api_path = os.path.abspath(cand)
                    break
            if not api_path:
                api_path = resolve_workflow(api_file, require=True)
            ports_path = None
            if ports_file:
                for cand in (
                    ports_file if os.path.isabs(ports_file) else None,
                    os.path.join(AGENT_WORKFLOWS_DIR, ports_file),
                    os.path.join(PRESETS_DIR, os.path.basename(ports_file)),
                ):
                    if cand and os.path.isfile(cand):
                        ports_path = os.path.abspath(cand)
                        break
            return api_path, ports_path

    # path or presets/
    if raw.endswith(".ports.json"):
        raise FileNotFoundError("Pass the .api.json or catalog alias, not ports alone")

    candidates = []
    if os.path.isfile(raw):
        candidates.append(os.path.abspath(raw))
    candidates.extend(
        [
            os.path.join(PRESETS_DIR, raw if raw.endswith(".json") else f"{raw}.api.json"),
            os.path.join(PRESETS_DIR, f"{raw}.api.json") if not raw.endswith(".json") else "",
            os.path.join(AGENT_WORKFLOWS_DIR, raw if raw.endswith(".json") else f"{raw}.json"),
        ]
    )
    api_path = None
    for c in candidates:
        if c and os.path.isfile(c):
            api_path = os.path.abspath(c)
            break
    if not api_path:
        # try resolve_workflow for legacy names
        try:
            api_path = resolve_workflow(raw, require=True)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Preset/API workflow not found: {raw!r}") from e

    # sidecar ports
    ports_path = None
    for p in (
        api_path.replace(".api.json", ".ports.json"),
        api_path.replace(".json", ".ports.json"),
        os.path.join(os.path.dirname(api_path), Path(api_path).stem + ".ports.json"),
    ):
        if p != api_path and os.path.isfile(p):
            ports_path = os.path.abspath(p)
            break
    return api_path, ports_path


def apply_ports(
    api: dict[str, Any],
    ports_spec: dict[str, Any],
    values: dict[str, Any],
    *,
    copy_images: bool = True,
) -> dict[str, Any]:
    """
    Patch api graph in-place from ports_spec['ports'] and values.

    values keys match ports_spec ports keys (positive, seed, input_image, …).
    """
    ports = ports_spec.get("ports") or {}
    defaults = ports_spec.get("defaults") or {}
    merged = {**defaults, **{k: v for k, v in values.items() if v is not None}}

    for port_name, spec in ports.items():
        if port_name not in merged:
            continue
        node_id = str(spec["node"])
        key = spec["key"]
        if node_id not in api:
            if spec.get("optional"):
                continue
            raise KeyError(f"Port {port_name}: node {node_id} missing from API graph")
        val = merged[port_name]
        # image: copy into Comfy input dir, set filename only
        # Must match live Comfy --input-directory (often F:\ComfyUI_data\input),
        # NOT the legacy portable ComfyUI\input path.
        if spec.get("copy_to_input_dir") and isinstance(val, str) and os.path.isfile(val):
            if copy_images:
                input_dir = get_comfy_input_dir()
                os.makedirs(input_dir, exist_ok=True)
                base = os.path.basename(val)
                # unique-ish to avoid collisions
                dest_name = f"wf_api_{port_name}_{base}"
                dest = os.path.join(input_dir, dest_name)
                shutil.copy2(val, dest)
                val = dest_name
            else:
                val = os.path.basename(val)
        api[node_id].setdefault("inputs", {})[key] = val

    return api


def run_workflow_api(
    preset: str,
    *,
    ports: dict[str, Any] | None = None,
    output_path: str | None = None,
    meta_out: str | None = None,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: float = 900,
    seed: int | None = None,
) -> dict[str, Any]:
    """
    Load API workflow + ports map, apply patches, queue, download first image.

    ``ports`` may include positive, negative, seed, denoise, input_image, width, height, …
    If seed is None and ports map has seed, a random seed is used unless ports already set.
    """
    try:
        api_path, ports_path = resolve_preset(preset)
    except FileNotFoundError as e:
        return fail_result(error="PRESET_MISSING", message=str(e))

    api = _read_json(api_path)
    if not isinstance(api, dict) or not api:
        return fail_result(error="BAD_API_JSON", message=api_path)

    # Detect UI-format accident
    if "nodes" in api and "links" in api:
        return fail_result(
            error="UI_FORMAT_NOT_API",
            message=f"{api_path} looks like UI workflow; export Save (API Format) first",
        )

    ports_spec: dict[str, Any] = {"ports": {}, "defaults": {}}
    if ports_path and os.path.isfile(ports_path):
        ports_spec = _read_json(ports_path)

    values = dict(ports or {})
    if seed is not None:
        values["seed"] = int(seed)
    elif "seed" not in values and "seed" in (ports_spec.get("ports") or {}):
        values["seed"] = random.randint(1, 2**31 - 1)
    # multi-seed graphs (e.g. Krea2 dual pass) share the same seed unless overridden
    if "seed" in values:
        for alt in ("seed_b", "seed_c", "seed_d", "global_seed"):
            if alt in (ports_spec.get("ports") or {}) and alt not in values:
                values[alt] = values["seed"]

    try:
        api = copy.deepcopy(api)
        apply_ports(api, ports_spec, values)
    except Exception as e:
        return fail_result(error="PORT_PATCH_FAILED", message=str(e))

    try:
        prompt_id = queue_prompt(server_address, api)
    except Exception as e:
        return fail_result(error="QUEUE_FAILED", message=str(e))

    try:
        history = wait_for_history(server_address, prompt_id, timeout_sec=timeout_sec)
    except TimeoutError as e:
        return fail_result(error="COMFY_TIMEOUT", message=str(e), prompt_id=prompt_id)
    except Exception as e:
        return fail_result(error="EXEC_FAILED", message=str(e), prompt_id=prompt_id)

    try:
        filename, subfolder, image_type = extract_first_image(history)
    except Exception as e:
        return fail_result(error="NO_OUTPUT", message=str(e), prompt_id=prompt_id)

    if not output_path:
        output_path = os.path.join(
            r"F:\generated_images",
            f"wf_api_{Path(api_path).stem}_{values.get('seed', 'x')}.png",
        )
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    try:
        download_image(server_address, filename, subfolder, image_type, output_path)
    except Exception as e:
        return fail_result(error="DOWNLOAD_FAILED", message=str(e), prompt_id=prompt_id)

    applied_seed = values.get("seed")
    meta = {
        "mode": "workflow_api",
        "workflow_api": os.path.abspath(api_path),
        "ports_file": os.path.abspath(ports_path) if ports_path else None,
        "preset": preset,
        "seed": applied_seed,
        "ports_applied": {k: (v if k != "positive" else str(v)[:200]) for k, v in values.items()},
        "comfy_prompt_id": prompt_id,
        "output_path": os.path.abspath(output_path),
        "created_at": utc_now_iso(),
    }
    meta_path = meta_out
    if meta_path is None and output_path:
        meta_path = os.path.splitext(output_path)[0] + ".meta.json"
    if meta_path:
        write_meta(meta_path, meta)

    return ok_result(
        output_path=os.path.abspath(output_path),
        seed=applied_seed,
        prompt_id=prompt_id,
        meta=meta,
        meta_path=meta_path,
        workflow_api=os.path.abspath(api_path),
    )
