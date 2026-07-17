#!/usr/bin/env python3
"""
Smoke-run Lonecat's AIO Z-Image ver 17 via ComfyUI API.

Resolves frontend-only SetNode/GetNode buses (KJNodes) and skips note/label
nodes that are not executable. Injects a short T2I prompt for sonagi smoke.
"""
from __future__ import annotations

import json
import os
import random
import shutil
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"F:\ComfyUI_workflows\agent_custom")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from lib.comfy_client import (  # noqa: E402
    DEFAULT_SERVER,
    download_image,
    extract_first_image,
    queue_prompt,
    wait_for_history,
)

WF_SRC = Path(
    r"F:\ComfyUI_windows_portable\ComfyUI\user\default\workflows"
    r"\Lonecat's AIO Z-Image ver 17.json"
)
OUT_DIR = Path(r"D:\뮤직비디오 작업\소나기_v2\03_키프레임\v3_smoke_lonecat_v17")
OUT_DIR.mkdir(parents=True, exist_ok=True)
META_DIR = ROOT / "workflows" / "human"
META_DIR.mkdir(parents=True, exist_ok=True)

# Skip frontend-only / non-executing nodes
SKIP_TYPES = {
    "Note",
    "MarkdownNote",
    "Label (rgthree)",
    "Bookmark (rgthree)",
    "Reroute",
    "Fast Groups Bypasser (rgthree)",
    "Fast Groups Muter (rgthree)",
    "Fast Bypasser (rgthree)",
    "Fast Muter (rgthree)",
    "Node Collector (rgthree)",
    "SetNode",
    "GetNode",
}

# Node mode: 0=active, 2=muted, 4=bypassed (Comfy convention)
MODE_MUTE = 2
MODE_BYPASS = 4

SMOKE_PROMPT = (
    "cinematic photoreal film still, medium shot waist-up, mid-20s Korean woman, "
    "slightly long oval face, warm dark brown eyes, collarbone-length dark black-brown "
    "soft waves side part, natural skin pores freckles, wearing soft cream knit cardigan "
    "over white blouse, light wash blue jeans, standing at Seoul convenience store "
    "checkout counter holding translucent plastic shopping bag, stocked snack shelves "
    "and fluorescent lights behind, glass door with rainy street outside, cool fluorescent "
    "key light, 35mm eye level, photoreal film grain, sharp focus on face and bag"
)
SMOKE_NEGATIVE = (
    "bad anatomy, bad hands, watermark, ugly, distorted, censored, lowres, pixelated, "
    "jpeg artifacts, signature, logo, text, extra fingers, missing fingers, plastic skin"
)


def _http_json(path: str, method: str = "GET", body: dict | None = None, timeout: float = 120):
    url = f"http://{DEFAULT_SERVER}{path}"
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw.decode("utf-8")) if raw else {}


def fetch_object_info() -> dict:
    return _http_json("/object_info", timeout=180)


def resolve_set_get(ui: dict) -> dict:
    """Rewrite links so GetNode outputs become the SetNode input sources."""
    nodes = {n["id"]: n for n in ui["nodes"]}
    links = list(ui.get("links") or [])
    # link: [link_id, from_id, from_slot, to_id, to_slot, type]

    # Map set name -> (source_node_id, source_slot, type)
    set_sources: dict[str, tuple[int, int, str | None]] = {}
    for n in ui["nodes"]:
        if n.get("type") != "SetNode":
            continue
        name = (n.get("widgets_values") or [None])[0]
        if not name:
            continue
        # find link into SetNode
        for link in links:
            if link[3] == n["id"]:
                set_sources[str(name)] = (link[1], link[2], link[5] if len(link) > 5 else None)
                break

    # GetNode id -> resolved source
    get_resolve: dict[int, tuple[int, int, str | None]] = {}
    for n in ui["nodes"]:
        if n.get("type") != "GetNode":
            continue
        name = (n.get("widgets_values") or [None])[0]
        if name is not None and str(name) in set_sources:
            get_resolve[n["id"]] = set_sources[str(name)]

    # Rewrite links that come FROM GetNode to come from Set's source instead
    new_links = []
    next_id = max((l[0] for l in links), default=0) + 1
    for link in links:
        lid, fr, fslot, to, tslot = link[0], link[1], link[2], link[3], link[4]
        ltype = link[5] if len(link) > 5 else None
        # skip links into SetNode or from/to pure skip later
        if nodes.get(to, {}).get("type") == "SetNode":
            continue
        if nodes.get(fr, {}).get("type") == "GetNode":
            if fr in get_resolve:
                src_id, src_slot, src_type = get_resolve[fr]
                new_links.append([next_id, src_id, src_slot, to, tslot, src_type or ltype])
                next_id += 1
            continue
        if nodes.get(fr, {}).get("type") == "SetNode":
            # SetNode passthrough output if any — treat as source input
            name = (nodes[fr].get("widgets_values") or [None])[0]
            if name is not None and str(name) in set_sources:
                src_id, src_slot, src_type = set_sources[str(name)]
                new_links.append([next_id, src_id, src_slot, to, tslot, src_type or ltype])
                next_id += 1
            continue
        new_links.append(link)

    ui = dict(ui)
    ui["links"] = new_links
    return ui


def convert_ui_to_api_full(ui_data: dict, object_info: dict) -> dict:
    """UI→API with object_info widget order mapping + Set/Get resolved graph."""
    ui_data = resolve_set_get(ui_data)
    links = {l[0]: l for l in ui_data.get("links", [])}
    api: dict[str, dict] = {}

    for node in ui_data.get("nodes", []):
        class_type = node.get("type")
        if class_type in SKIP_TYPES:
            continue
        # muted nodes
        mode = node.get("mode", 0)
        if mode in (MODE_MUTE, MODE_BYPASS):
            continue
        if class_type not in object_info:
            # keep missing optional nodes out; warn
            print(f"[WARN] skip missing class: {class_type} id={node.get('id')}")
            continue

        node_id = str(node["id"])
        inputs: dict = {}

        # Linked inputs
        for inp in node.get("inputs") or []:
            name = inp.get("name")
            link_id = inp.get("link")
            if link_id is not None and link_id in links:
                link = links[link_id]
                origin = str(link[1])
                # if origin was Set/Get skipped, should already be rewritten
                if nodes_type(ui_data, link[1]) in SKIP_TYPES:
                    continue
                inputs[name] = [origin, link[2]]

        # Widget inputs via object_info order
        widgets = node.get("widgets_values") or []
        info = object_info[class_type]
        required = info.get("input", {}).get("required", {}) or {}
        optional = info.get("input", {}).get("optional", {}) or {}
        # Flatten widget-bearing inputs in definition order
        widget_names: list[str] = []
        for section in (required, optional):
            for name, spec in section.items():
                # skip if already linked
                if name in inputs:
                    continue
                # combo/int/float/string/boolean etc have widget
                if not isinstance(spec, list) or not spec:
                    continue
                typ = spec[0]
                # Linked-only types
                if typ in (
                    "MODEL",
                    "CLIP",
                    "VAE",
                    "CONDITIONING",
                    "LATENT",
                    "IMAGE",
                    "MASK",
                    "CONTROL_NET",
                    "CLIP_VISION",
                    "STYLE_MODEL",
                    "GLIGEN",
                    "UPSCALE_MODEL",
                    "AUDIO",
                    "WEBCAM",
                    "*",
                ):
                    continue
                widget_names.append(name)

        # Some nodes pack widgets with extra UI state (rgthree seed etc.)
        wi = 0
        for name in widget_names:
            if wi >= len(widgets):
                break
            val = widgets[wi]
            # Skip nested dict headers (Power Lora etc.) carefully
            inputs[name] = val
            wi += 1

        # Fallback specials if object_info order failed to cover common cases
        if class_type == "CLIPTextEncode" and "text" not in inputs and widgets:
            inputs["text"] = widgets[0]
        if class_type == "easy positive" and "positive" not in inputs and widgets:
            inputs["positive"] = widgets[0]
        if class_type == "easy negative" and "negative" not in inputs and widgets:
            inputs["negative"] = widgets[0]
        if class_type == "Text Multiline" and "text" not in inputs and widgets:
            inputs["text"] = widgets[0]
        if class_type == "LoadImage" and widgets:
            inputs["image"] = widgets[0]
            inputs["upload"] = "image"
        if class_type == "UNETLoader" and len(widgets) >= 2:
            inputs.setdefault("unet_name", widgets[0])
            inputs.setdefault("weight_dtype", widgets[1])
        if class_type == "VAELoader" and widgets:
            inputs.setdefault("vae_name", widgets[0])
        if class_type == "CLIPLoader" and len(widgets) >= 3:
            inputs.setdefault("clip_name", widgets[0])
            inputs.setdefault("type", widgets[1])
            inputs.setdefault("device", widgets[2])

        api[node_id] = {"class_type": class_type, "inputs": inputs}

    # Drop links that point to missing node ids
    valid = set(api.keys())
    for nid, node in list(api.items()):
        for k, v in list(node["inputs"].items()):
            if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str):
                if v[0] not in valid:
                    del node["inputs"][k]
    return api


def nodes_type(ui: dict, nid: int) -> str | None:
    for n in ui["nodes"]:
        if n["id"] == nid:
            return n.get("type")
    return None


def inject_smoke_prompt(ui: dict, prompt: str, negative: str, seed: int) -> dict:
    """Patch UI widgets before conversion."""
    for n in ui["nodes"]:
        t = n.get("type")
        title = n.get("title") or ""
        # Main user prompt path often goes through Final Prompt / CLIP encodes
        # Inject into empty easy positive (id 1342 area) and quality prompt
        if t == "easy positive" and title in ("", "Quality Prompt"):
            # keep quality tags on Quality Prompt; put scene on empty easy positive
            if title == "Quality Prompt":
                n["widgets_values"] = [
                    "photorealistic, detailed skin, high quality, natural pores, film grain"
                ]
            else:
                n["widgets_values"] = [prompt]
        if t == "easy negative" and "Negative" in title:
            n["widgets_values"] = [negative]
        if t == "Seed (rgthree)":
            # widgets: seed, ...
            w = list(n.get("widgets_values") or [-1])
            w[0] = seed
            n["widgets_values"] = w
        if t == "CLIPTextEncode" and not title:
            # only replace empty encodes if they already empty or short
            w = n.get("widgets_values") or [""]
            if isinstance(w, list) and (not w[0] or len(str(w[0])) < 5):
                # leave empty; positive comes via bus
                pass
        # Prefer Turbo settings already in graph; set denoise mxSlider low for T2I-ish
        if t == "mxSlider" and title == "Denoise":
            # Xi, Xf, isfloatX — use low denoise for pure gen if I2I off
            n["widgets_values"] = [1.0, 1.0, 1]
        # Aspect: force 16:9 cinematic if CR Aspect Ratio present
        if t == "CR Aspect Ratio Social Media":
            # width, height, preset, ...
            w = list(n.get("widgets_values") or [])
            if len(w) >= 2:
                w[0], w[1] = 1024, 576
            n["widgets_values"] = w
        # Filename prefix
        if t == "DF_Text" and title == "Filename Prefix":
            n["widgets_values"] = ["sonagi_lonecat_v17_smoke"]
    return ui


def prune_unreachable(api: dict) -> dict:
    """Keep only nodes that feed into SaveImage / Image Saver* outputs."""
    outputs = {
        nid
        for nid, n in api.items()
        if n["class_type"]
        in (
            "SaveImage",
            "Image Saver",
            "Image Saver Simple",
            "Save Image (LoraManager)",
            "PreviewImage",
        )
    }
    if not outputs:
        return api
    # reverse deps
    consumers = defaultdict(set)
    for nid, n in api.items():
        for v in n["inputs"].values():
            if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str):
                consumers[v[0]].add(nid)
    # BFS backward from outputs — actually need nodes that outputs depend on
    needed = set(outputs)
    changed = True
    while changed:
        changed = False
        for nid in list(needed):
            n = api.get(nid)
            if not n:
                continue
            for v in n["inputs"].values():
                if isinstance(v, list) and len(v) == 2 and isinstance(v[0], str):
                    if v[0] not in needed and v[0] in api:
                        needed.add(v[0])
                        changed = True
    return {nid: api[nid] for nid in needed if nid in api}


def validate_api(api: dict, object_info: dict) -> list[str]:
    problems = []
    for nid, n in api.items():
        ct = n["class_type"]
        if ct not in object_info:
            problems.append(f"missing class {ct} @ {nid}")
            continue
        req = object_info[ct].get("input", {}).get("required", {}) or {}
        for name in req:
            if name not in n["inputs"]:
                # some required may have defaults
                spec = req[name]
                if isinstance(spec, list) and len(spec) >= 2 and isinstance(spec[1], dict):
                    if "default" in spec[1]:
                        continue
                # IMAGE etc without default
                problems.append(f"missing input {ct}.{name} @ {nid}")
    return problems


def main() -> int:
    print("Loading workflow:", WF_SRC)
    ui = json.loads(WF_SRC.read_text(encoding="utf-8"))
    print(f"nodes={len(ui.get('nodes', []))} links={len(ui.get('links', []))}")

    # Copy to human SSOT
    dest = META_DIR / "Lonecat_AIO_Z-Image_ver17.json"
    if not dest.exists():
        shutil.copy2(WF_SRC, dest)
        print("Copied to", dest)

    seed = random.randint(1, 2**31 - 1)
    ui = inject_smoke_prompt(ui, SMOKE_PROMPT, SMOKE_NEGATIVE, seed)
    print("seed", seed)

    print("Fetching object_info...")
    info = fetch_object_info()
    print("object_info classes", len(info))

    print("Converting UI → API (Set/Get resolve)...")
    api = convert_ui_to_api_full(ui, info)
    print("api nodes before prune", len(api))
    api = prune_unreachable(api)
    print("api nodes after prune", len(api))

    # Force UNET to moodyPro if present path matches workflow default z_image_turbo
    for nid, n in api.items():
        if n["class_type"] == "UNETLoader":
            # keep workflow default first for fidelity
            print("UNETLoader", nid, n["inputs"].get("unet_name"))
        if n["class_type"] == "easy positive":
            print("easy positive", nid, str(n["inputs"].get("positive", ""))[:80])
        if n["class_type"] in ("SaveImage", "Image Saver Simple", "Image Saver"):
            print("save node", nid, n["class_type"], n["inputs"])

    problems = validate_api(api, info)
    print(f"validation issues: {len(problems)}")
    for p in problems[:40]:
        print(" ", p)
    if len(problems) > 80:
        print("  ...")

    # Save API dump for debug
    dump = OUT_DIR / "lonecat_v17_api_prompt.json"
    dump.write_text(json.dumps(api, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", dump)

    # If too many hard missing classes, abort
    hard = [p for p in problems if p.startswith("missing class")]
    if hard:
        print("[ERROR] hard missing classes — cannot run full AIO until nodes installed")
        for p in hard[:20]:
            print(" ", p)
        # still try — some may be in pruned branch

    print("Queueing to ComfyUI...")
    try:
        prompt_id = queue_prompt(DEFAULT_SERVER, api)
    except Exception as e:
        print("[ERROR] queue failed:", e)
        # try with client_id free prompt
        try:
            body = {"prompt": api}
            res = _http_json("/prompt", method="POST", body=body, timeout=60)
            prompt_id = res.get("prompt_id")
            print("queue alt response", res)
        except Exception as e2:
            print("[ERROR] alt queue failed:", e2)
            return 1
    print("prompt_id", prompt_id)

    try:
        history = wait_for_history(DEFAULT_SERVER, prompt_id, timeout_sec=900)
    except Exception as e:
        print("[ERROR] history:", e)
        return 2

    status = history.get("status") or {}
    if status.get("status_str") == "error":
        print("[ERROR] execution error")
        for msg in status.get("messages") or []:
            print(" ", msg)
        return 3

    try:
        filename, subfolder, image_type = extract_first_image(history)
    except Exception as e:
        print("[ERROR] no output image:", e)
        # dump history keys
        print("history keys", history.keys())
        outs = history.get("outputs") or {}
        print("output nodes", list(outs.keys())[:20])
        return 4

    out_path = OUT_DIR / "S01_lonecat_v17_smoke.png"
    download_image(DEFAULT_SERVER, filename, subfolder, image_type, str(out_path))
    print("OK saved", out_path)

    meta = {
        "workflow": str(WF_SRC),
        "engine": "Lonecat_AIO_Z-Image_ver17",
        "seed": seed,
        "prompt": SMOKE_PROMPT,
        "negative": SMOKE_NEGATIVE,
        "prompt_id": prompt_id,
        "output": str(out_path),
        "api_nodes": len(api),
        "validation_issues": len(problems),
    }
    (OUT_DIR / "S01_lonecat_v17_smoke.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # also copy into episode keyframes for comparison
    ep = ROOT / "stories" / "sonagi_mv_v3" / "keyframes" / "S01_lonecat_v17_smoke.png"
    shutil.copy2(out_path, ep)
    print("copied", ep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
