"""Yet Another Workflow (YAW) Wan 2.2 MoE v0.50 — real UI + GGUF diffusion.

SSOT:
  workflows/human/yaw_wan22/yetAnotherWorkflowEasyT2vI2v_v050Moe.json

Source purpose (Civitai 2008892 / boobkake22):
  Easy T2V + I2V template for Wan 2.2 MoE (high+low noise). Beginner-friendly
  controls, no subgraphs. MoE variant = minimum visual complexity.

Agent policy:
  - Keep real UI graph (no mini rebuild).
  - Toggle T2V / I2V groups via node mode (same as green Fast Groups Muter).
  - Default diffusion = **UnetLoaderGGUF** (local Q4_K_M). Pack ships fp16
    UNETLoader names that are ~28GB×4 and often not installed.
  - Resolve SimpleSwitch (first live input) after expand — expand does not.
  - Bypass interpolators by default (GIMM/RIFE) so post chain passthrough works.
"""

from __future__ import annotations

import copy
import json
import os
import random
import shutil
import time
from pathlib import Path
from typing import Any

from lib.comfy_client import (
    COMFYUI_INPUT_DIR,
    DEFAULT_SERVER,
    fail_result,
    ok_result,
    queue_prompt,
    utc_now_iso,
    wait_for_history,
    write_meta,
)
from lib.comfy_engine_session import FAMILY_WAN, ensure_engine
from lib.ltx_aio_ui_expand import expand_ui_workflow_to_api
from lib.workflow_video_runner import extract_first_video, _resolve_local_video

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
HUMAN_DIR = WORKSPACE_ROOT / "workflows" / "human" / "yaw_wan22"
HUMAN_UI = HUMAN_DIR / "yetAnotherWorkflowEasyT2vI2v_v050Moe.json"
API_CACHE = (
    WORKSPACE_ROOT
    / "workflows"
    / "agent"
    / "presets"
    / "yaw_wan22_v050_moe.api.json"
)

# Pack UNETLoader widget names (fp16) — large; optional if present
FP16 = {
    "t2v_high": "wan2.2_t2v_high_noise_14B_fp16.safetensors",
    "t2v_low": "wan2.2_t2v_low_noise_14B_fp16.safetensors",
    "i2v_high": "wan2.2_i2v_high_noise_14B_fp16.safetensors",
    "i2v_low": "wan2.2_i2v_low_noise_14B_fp16.safetensors",
}

# Local GGUF (ComfyUI-GGUF UnetLoaderGGUF list)
GGUF = {
    "t2v_high": r"Wan2.2\Wan2.2-T2V-A14B-HighNoise-Q4_K_M.gguf",
    "t2v_low": r"Wan2.2\Wan2.2-T2V-A14B-LowNoise-Q4_K_M.gguf",
    "i2v_high": r"Wan2.2\Wan2.2-I2V-A14B-HighNoise-Q4_K_M.gguf",
    "i2v_low": r"Wan2.2\Wan2.2-I2V-A14B-LowNoise-Q4_K_M.gguf",
}

# UI node ids
UNET_T2V_HIGH = "149"
UNET_T2V_LOW = "150"
UNET_I2V_HIGH = "177"
UNET_I2V_LOW = "178"
# Group members for T2V / I2V (mode 0 = on, 2 = never)
T2V_NODES = (149, 150, 1331)  # UNETs + TaskSelector T2V
I2V_NODES = (177, 178, 166, 1333)  # UNETs + Load Start + TaskSelector I2V
END_IMAGE_NODES = (339, 1327, 1328)
# Post VFI — agent default OFF (bypass passthrough)
VFI_NODES = (1373, 1374, 1375)  # GIMM load/interp + RIFE
COLOR_CORRECT = (160,)  # already often bypass in pack

DEFAULT_NEG = (
    "色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，"
    "最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部"
)


def _load_ui(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path or HUMAN_UI)
    if not p.is_file():
        raise FileNotFoundError(f"YAW UI not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _fetch_object_info(server: str = DEFAULT_SERVER) -> dict[str, Any] | None:
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://{server}/object_info", timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _stage(src: str, prefix: str) -> str:
    src_p = Path(src)
    if not src_p.is_file():
        raise FileNotFoundError(f"missing: {src}")
    dest = Path(COMFYUI_INPUT_DIR)
    dest.mkdir(parents=True, exist_ok=True)
    name = f"{prefix}_{int(time.time())}_{src_p.name}"
    shutil.copy2(src_p, dest / name)
    return name


def _set_modes(ui: dict[str, Any], node_ids: tuple[int, ...] | list[int], mode: int) -> None:
    want = {int(i) for i in node_ids}
    for n in ui.get("nodes") or []:
        if int(n.get("id", -1)) in want:
            n["mode"] = int(mode)


def apply_task_modes(
    ui: dict[str, Any],
    *,
    task: str = "t2v",
    end_image: bool = False,
    enable_vfi: bool = False,
) -> dict[str, Any]:
    """T2V vs I2V like green Fast Groups Muter (always one)."""
    ui = copy.deepcopy(ui)
    task = (task or "t2v").strip().lower()
    if task in ("i2v", "image", "img2vid"):
        _set_modes(ui, I2V_NODES, 0)
        _set_modes(ui, T2V_NODES, 2)
    else:
        _set_modes(ui, T2V_NODES, 0)
        _set_modes(ui, I2V_NODES, 2)

    if end_image:
        _set_modes(ui, END_IMAGE_NODES, 0)
    else:
        _set_modes(ui, END_IMAGE_NODES, 2)

    # Interpolators: bypass so image chain passthrough (mode 4)
    if enable_vfi:
        _set_modes(ui, (1373, 1374), 0)
        _set_modes(ui, (1375,), 2)
    else:
        _set_modes(ui, VFI_NODES, 4)
        _set_modes(ui, COLOR_CORRECT, 4)

    return ui


def _resolve_simple_switches(api: dict[str, Any]) -> dict[str, Any]:
    """SimpleSwitch: first live input01..input06 → rewire consumers (drop switch).

    Iterates until stable — switches often feed other switches.
    """
    for _round in range(16):
        picks: dict[str, list] = {}
        for sid, node in list(api.items()):
            if node.get("class_type") != "SimpleSwitch":
                continue
            ins = node.get("inputs") or {}
            chosen = None
            for i in range(1, 7):
                v = ins.get(f"input{i:02d}")
                if isinstance(v, list) and len(v) == 2 and str(v[0]) in api:
                    # skip pointing at another unresolved SimpleSwitch if possible
                    src = api.get(str(v[0])) or {}
                    if src.get("class_type") == "SimpleSwitch":
                        continue
                    chosen = list(v)
                    break
            if chosen is None:
                for _k, v in ins.items():
                    if isinstance(v, list) and len(v) == 2 and str(v[0]) in api:
                        chosen = list(v)
                        break
            if chosen is not None:
                picks[str(sid)] = chosen

        if not picks:
            break

        for _nid, node in api.items():
            ins = node.get("inputs") or {}
            for k, v in list(ins.items()):
                if isinstance(v, list) and len(v) == 2 and str(v[0]) in picks:
                    ins[k] = list(picks[str(v[0])])

        for sid in picks:
            api.pop(sid, None)

    return api


def _multi_hop_bypass(api: dict[str, Any], ui: dict[str, Any]) -> None:
    nodes = {int(n["id"]): n for n in (ui.get("nodes") or []) if "id" in n}
    links = {}
    for L in ui.get("links") or []:
        if isinstance(L, list) and len(L) >= 5:
            links[int(L[0])] = L

    def live(oid: int, oslot: int, depth: int = 0) -> tuple[str, int] | None:
        if depth > 28:
            return None
        if str(oid) in api:
            return (str(oid), int(oslot))
        n = nodes.get(int(oid))
        if not n:
            return None
        mode = int(n.get("mode", 0) or 0)
        if mode not in (2, 4):
            return None
        for inp in n.get("inputs") or []:
            lid = inp.get("link")
            if lid is None or int(lid) not in links:
                continue
            L = links[int(lid)]
            hit = live(int(L[1]), int(L[2]), depth + 1)
            if hit:
                return hit
        return None

    # restore missing from UI links
    for n in ui.get("nodes") or []:
        nid = str(n.get("id"))
        if nid not in api or int(n.get("mode", 0) or 0) in (2, 4):
            continue
        ins = api[nid].setdefault("inputs", {})
        for inp in n.get("inputs") or []:
            name = inp.get("name")
            lid = inp.get("link")
            if name is None or lid is None or int(lid) not in links:
                continue
            cur = ins.get(name)
            if isinstance(cur, list) and len(cur) == 2 and str(cur[0]) in api:
                continue
            L = links[int(lid)]
            hit = live(int(L[1]), int(L[2]))
            if hit:
                ins[name] = [hit[0], hit[1]]

    for node in api.values():
        ins = node.get("inputs") or {}
        for k, v in list(ins.items()):
            if not (isinstance(v, list) and len(v) == 2):
                continue
            if str(v[0]) in api:
                continue
            try:
                hit = live(int(v[0]), int(v[1]))
            except Exception:
                hit = None
            if hit:
                ins[k] = [hit[0], hit[1]]
            else:
                del ins[k]


def _swap_unets_to_gguf(
    api: dict[str, Any],
    *,
    task: str,
    use_fp16: bool = False,
    gguf_map: dict[str, str] | None = None,
) -> str:
    """Replace UNETLoader with UnetLoaderGGUF (default) or keep fp16 names."""
    gmap = gguf_map or GGUF
    task = (task or "t2v").lower()
    if task in ("i2v", "image", "img2vid"):
        mapping = {
            UNET_I2V_HIGH: ("i2v_high", gmap["i2v_high"], FP16["i2v_high"]),
            UNET_I2V_LOW: ("i2v_low", gmap["i2v_low"], FP16["i2v_low"]),
        }
    else:
        mapping = {
            UNET_T2V_HIGH: ("t2v_high", gmap["t2v_high"], FP16["t2v_high"]),
            UNET_T2V_LOW: ("t2v_low", gmap["t2v_low"], FP16["t2v_low"]),
        }

    backend = "fp16" if use_fp16 else "gguf"
    for nid, (_role, gguf_name, fp16_name) in mapping.items():
        if nid not in api:
            continue
        if use_fp16:
            api[nid] = {
                "class_type": "UNETLoader",
                "inputs": {"unet_name": fp16_name, "weight_dtype": "default"},
                "_meta": {"title": f"UNET fp16 {_role}"},
            }
        else:
            api[nid] = {
                "class_type": "UnetLoaderGGUF",
                "inputs": {"unet_name": gguf_name},
                "_meta": {"title": f"UNET GGUF {_role}"},
            }
    # Any leftover UNETLoader on inactive path: leave or drop later
    return backend


def _drop_chrome(api: dict[str, Any]) -> dict[str, Any]:
    drop = {
        "Note",
        "MarkdownNote",
        "Fast Groups Muter (rgthree)",
        "Fast Groups Bypasser (rgthree)",
        "PlaySound|pysssss",
        "PreviewImage",
        "easy cleanGpuUsed",
        "easy clearCacheAll",
    }
    api = {k: v for k, v in api.items() if v.get("class_type") not in drop}
    alive = set(api)
    for n in api.values():
        ins = n.get("inputs") or {}
        for k, v in list(ins.items()):
            if isinstance(v, list) and len(v) == 2 and str(v[0]) not in alive:
                del ins[k]
    return api


def _strip_vhs_preview_widget(api: dict[str, Any]) -> None:
    for n in api.values():
        if n.get("class_type") != "VHS_VideoCombine":
            continue
        ins = n.get("inputs") or {}
        ins.pop("videopreview", None)
        ins["save_output"] = True


def _fix_pack_widgets(api: dict[str, Any], ui: dict[str, Any]) -> None:
    """Fill free widgets expand missed (seed control slot / denoise etc.)."""
    ui_by = {str(n["id"]): n for n in (ui.get("nodes") or []) if "id" in n}

    # WanMoeKSampler widgets:
    # boundary, seed, control_after_generate, steps, cfg_high, cfg_low,
    # sampler, scheduler, sigma_shift, denoise
    if "1389" in api:
        ins = api["1389"].setdefault("inputs", {})
        wv = ui_by.get("1389", {}).get("widgets_values") or []
        # denoise is required and often last free widget
        if "denoise" not in ins or ins.get("denoise") is None:
            den = 1.0
            if isinstance(wv, list) and wv:
                # last numeric float-like
                for v in reversed(wv):
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        # prefer last value in [0,1] range as denoise
                        if 0 <= float(v) <= 1.0:
                            den = float(v)
                            break
                # pack default denoise=1 at end
                if isinstance(wv[-1], (int, float)):
                    den = float(wv[-1])
            ins["denoise"] = den
        # free fallbacks if not linked
        if not isinstance(ins.get("boundary"), list) and isinstance(wv, list) and wv:
            ins.setdefault("boundary", float(wv[0]) if isinstance(wv[0], (int, float)) else 0.875)
        if not isinstance(ins.get("steps"), list) and isinstance(wv, list) and len(wv) >= 4:
            if isinstance(wv[3], int):
                ins.setdefault("steps", int(wv[3]))

    # StepBudget: accelerated_steps, full_steps
    if "1352" in api:
        ins = api["1352"].setdefault("inputs", {})
        wv = ui_by.get("1352", {}).get("widgets_values") or [10, 30]
        if isinstance(wv, list) and len(wv) >= 2:
            ins.setdefault("accelerated_steps", int(wv[0]))
            ins.setdefault("full_steps", int(wv[1]))

    # mxSlider length seconds
    if "139" in api:
        ins = api["139"].setdefault("inputs", {})
        wv = ui_by.get("139", {}).get("widgets_values") or [5, 5, 0]
        if isinstance(wv, list) and wv:
            ins.setdefault("Xi", float(wv[0]))
            if len(wv) > 1:
                ins.setdefault("Xf", float(wv[1]))
            if len(wv) > 2:
                ins.setdefault("isfloatX", int(wv[2]))

    # TaskSelector / AccelerationSelector free combos
    if "1331" in api:
        wv = ui_by.get("1331", {}).get("widgets_values") or ["T2V"]
        api["1331"].setdefault("inputs", {}).setdefault(
            "task", wv[0] if isinstance(wv, list) else "T2V"
        )
    if "1333" in api:
        wv = ui_by.get("1333", {}).get("widgets_values") or ["I2V"]
        api["1333"].setdefault("inputs", {}).setdefault(
            "task", wv[0] if isinstance(wv, list) else "I2V"
        )
    if "1351" in api:
        wv = ui_by.get("1351", {}).get("widgets_values") or ["High + Low"]
        api["1351"].setdefault("inputs", {}).setdefault(
            "acceleration", wv[0] if isinstance(wv, list) else "High + Low"
        )

    # Power Lora Loader: drop chrome-only widget keys that confuse some builds
    for nid, n in api.items():
        if n.get("class_type") != "Power Lora Loader (rgthree)":
            continue
        ins = n.get("inputs") or {}
        clean = {}
        for k, v in ins.items():
            if k in ("model", "clip") or isinstance(v, list):
                clean[k] = v
            elif k in ("text",) and isinstance(v, str):
                clean[k] = v
        # keep model/clip at minimum
        if "model" in ins:
            clean["model"] = ins["model"]
        if "clip" in ins:
            clean["clip"] = ins["clip"]
        n["inputs"] = clean


def _sanitize_dead_optional_links(api: dict[str, Any]) -> None:
    """Drop links to missing nodes (optional image on WanResolutions etc.)."""
    alive = set(api)
    for n in api.values():
        ins = n.get("inputs") or {}
        for k, v in list(ins.items()):
            if isinstance(v, list) and len(v) == 2 and str(v[0]) not in alive:
                del ins[k]
    # remove empty SimpleSwitch shells
    empty_sw = [
        nid
        for nid, n in api.items()
        if n.get("class_type") == "SimpleSwitch"
        and not any(isinstance(v, list) for v in (n.get("inputs") or {}).values())
    ]
    for nid in empty_sw:
        del api[nid]
    # purge refs to removed switches
    alive = set(api)
    for n in api.values():
        ins = n.get("inputs") or {}
        for k, v in list(ins.items()):
            if isinstance(v, list) and len(v) == 2 and str(v[0]) not in alive:
                del ins[k]


def build_api(
    *,
    task: str = "t2v",
    use_fp16: bool = False,
    enable_vfi: bool = False,
    end_image: bool = False,
    server_address: str = DEFAULT_SERVER,
    ui_path: str | Path | None = None,
    cache: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Expand real YAW UI → API. No mini-graph rebuild."""
    ui0 = _load_ui(ui_path)
    ui = apply_task_modes(
        ui0, task=task, end_image=end_image, enable_vfi=enable_vfi
    )
    oi = _fetch_object_info(server_address)
    api = expand_ui_workflow_to_api(ui, object_info=oi)
    backend = _swap_unets_to_gguf(api, task=task, use_fp16=use_fp16)
    _fix_pack_widgets(api, ui)
    # Resolve switches / bypass like UI (order matters)
    for _ in range(3):
        _multi_hop_bypass(api, ui)
        api = _resolve_simple_switches(api)
    api = _drop_chrome(api)
    _strip_vhs_preview_widget(api)
    _fix_pack_widgets(api, ui)
    _sanitize_dead_optional_links(api)
    # one more hop after chrome drop
    _multi_hop_bypass(api, ui)
    api = _resolve_simple_switches(api)
    _sanitize_dead_optional_links(api)

    # Guarantee denoise after all rewires
    if "1389" in api:
        api["1389"].setdefault("inputs", {}).setdefault("denoise", 1.0)

    meta = {
        "task": task,
        "backend": backend,
        "node_count": len(api),
        "has_vhs": any(n.get("class_type") == "VHS_VideoCombine" for n in api.values()),
        "has_sampler": any(n.get("class_type") == "WanMoeKSampler" for n in api.values()),
    }
    if cache:
        try:
            API_CACHE.parent.mkdir(parents=True, exist_ok=True)
            with open(API_CACHE, "w", encoding="utf-8") as f:
                json.dump(api, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    return api, meta


def apply_ports(
    api: dict[str, Any],
    *,
    positive: str,
    negative: str | None = None,
    seed: int | None = None,
    image_name: str | None = None,
    end_image_name: str | None = None,
    length_seconds: float | None = None,
    steps: int | None = None,
    width: int | None = None,
    height: int | None = None,
    filename_prefix: str = "yaw_wan22",
    acceleration: str | None = None,
) -> dict[str, Any]:
    seed_i = int(seed if seed is not None else random.randint(1, 2**31 - 1))
    neg = negative if negative is not None else DEFAULT_NEG

    if "351" in api:
        api["351"].setdefault("inputs", {})["text"] = positive
    if "352" in api:
        api["352"].setdefault("inputs", {})["text"] = neg
    if "158" in api:
        api["158"].setdefault("inputs", {})["seed"] = seed_i

    if image_name and "166" in api:
        api["166"].setdefault("inputs", {})["image"] = image_name
    if end_image_name and "339" in api:
        api["339"].setdefault("inputs", {})["image"] = end_image_name

    # Length slider node 139 mxSlider — Xi often seconds
    if length_seconds is not None and "139" in api:
        ins = api["139"].setdefault("inputs", {})
        # mxSlider widgets vary; set common keys
        if "Xi" in ins or True:
            ins["Xi"] = float(length_seconds)
        if "value" in ins:
            ins["value"] = float(length_seconds)

    if steps is not None and "1352" in api:
        # StepBudget: accelerated_steps / full_steps (lightx2v uses accelerated)
        ins = api["1352"].setdefault("inputs", {})
        ins["accelerated_steps"] = int(steps)
        ins.setdefault("full_steps", max(int(steps) * 3, 30))

    if width is not None and "226" in api:
        api["226"].setdefault("inputs", {})["width"] = int(width)
    if height is not None and "226" in api:
        api["226"].setdefault("inputs", {})["height"] = int(height)

    if acceleration and "1351" in api:
        api["1351"].setdefault("inputs", {})["acceleration"] = acceleration

    for nid, n in api.items():
        if n.get("class_type") == "VHS_VideoCombine":
            n.setdefault("inputs", {})["filename_prefix"] = filename_prefix
            n["inputs"]["save_output"] = True

    return {"seed": seed_i, "positive": positive[:200]}


def generate_yaw_wan22(
    *,
    positive: str,
    output_path: str,
    task: str = "t2v",
    negative: str | None = None,
    seed: int | None = None,
    image_path: str | None = None,
    end_image_path: str | None = None,
    length_seconds: float | None = None,
    steps: int | None = None,
    width: int | None = None,
    height: int | None = None,
    use_fp16: bool = False,
    enable_vfi: bool = False,
    acceleration: str | None = None,
    timeout_sec: float = 1200,
    server_address: str = DEFAULT_SERVER,
    ui_path: str | Path | None = None,
    filename_prefix: str = "yaw_wan22",
) -> dict[str, Any]:
    eng = ensure_engine(FAMILY_WAN, server_address, caller="generate_yaw_wan22")
    if not eng.get("ok"):
        return fail_result(
            error="ENGINE_SESSION",
            message=eng.get("message") or "engine free failed",
            engine_session=eng,
        )

    task_l = (task or "t2v").lower()
    if image_path:
        task_l = "i2v"

    try:
        api, build_meta = build_api(
            task=task_l,
            use_fp16=use_fp16,
            enable_vfi=enable_vfi,
            end_image=bool(end_image_path),
            server_address=server_address,
            ui_path=ui_path,
        )
    except Exception as e:
        return fail_result(error="EXPAND_FAILED", message=str(e))

    # Ensure we still have a video saver + sampler
    has_vhs = any(n.get("class_type") == "VHS_VideoCombine" for n in api.values())
    has_samp = any(n.get("class_type") == "WanMoeKSampler" for n in api.values())
    if not has_vhs or not has_samp:
        return fail_result(
            error="GRAPH_INCOMPLETE",
            message=f"missing VHS={has_vhs} sampler={has_samp} nodes={len(api)}",
            build=build_meta,
        )

    try:
        img_name = _stage(image_path, "yaw_i2v") if image_path else None
        end_name = _stage(end_image_path, "yaw_end") if end_image_path else None
    except Exception as e:
        return fail_result(error="INPUT_MISSING", message=str(e))

    port_meta = apply_ports(
        api,
        positive=positive,
        negative=negative,
        seed=seed,
        image_name=img_name,
        end_image_name=end_name,
        length_seconds=length_seconds,
        steps=steps,
        width=width,
        height=height,
        filename_prefix=filename_prefix,
        acceleration=acceleration,
    )

    try:
        prompt_id = queue_prompt(server_address, api)
    except Exception as e:
        return fail_result(
            error="QUEUE_FAILED",
            message=str(e),
            build=build_meta,
            api_nodes=len(api),
        )

    try:
        entry = wait_for_history(server_address, prompt_id, timeout_sec=timeout_sec)
        if isinstance(entry, dict) and prompt_id in entry and "outputs" not in entry:
            entry = entry[prompt_id]
        fn, sub, typ = extract_first_video(entry)
        src = _resolve_local_video(fn, sub, typ)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out_p)
    except Exception as e:
        return fail_result(
            error="RUN_FAILED",
            message=str(e),
            prompt_id=prompt_id,
            build=build_meta,
        )

    meta = {
        "tool": "yaw_wan22_v050_moe",
        "task": task_l,
        "backend": build_meta.get("backend"),
        "ports": port_meta,
        "prompt_id": prompt_id,
        "output": str(out_p),
        "created_at": utc_now_iso(),
    }
    meta_path = str(out_p) + ".meta.json"
    write_meta(meta_path, meta)
    return ok_result(
        output_path=str(out_p),
        output=str(out_p),
        meta_path=meta_path,
        prompt_id=prompt_id,
        seed=port_meta.get("seed"),
        task=task_l,
        backend=build_meta.get("backend"),
    )
