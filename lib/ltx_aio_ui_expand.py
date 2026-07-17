"""Expand LTX AIO UI workflow (with subgraphs) into Comfy API prompt format.

Root links: [link_id, origin_id, origin_slot, target_id, target_slot, type]
Subgraph links: {id, origin_id, origin_slot, target_id, target_slot, type}
Subgraph instance node type == subgraph definition id (uuid).
Expanded node ids: \"{instance_id}:{inner_id}\" matching Comfy history format.
"""
from __future__ import annotations

import copy
from typing import Any

# Virtual nodes inside subgraph definitions
SG_INPUT_ID = -10
SG_OUTPUT_ID = -20


def _widgets_to_inputs(node: dict[str, Any]) -> dict[str, Any]:
    """Best-effort: prefer already-resolved inputs; fill from widgets_values for free widgets."""
    inputs: dict[str, Any] = {}
    # linked inputs first
    for inp in node.get("inputs") or []:
        name = inp.get("name")
        if name is None:
            continue
        link = inp.get("link")
        if link is not None:
            # resolved later
            inputs[name] = {"__link__": link}
        elif "widget" in inp and inp.get("widget"):
            # widget-backed; value may be in widgets_values by order — handled below
            pass

    # Many Comfy UI nodes store free values only in widgets_values ordered by widgets
    # For API export Comfy usually already maps them — we keep widgets via class defaults
    # and only set names that appear as non-link widgets in common loaders.
    wv = node.get("widgets_values")
    ct = node.get("type") or ""

    # Heuristic mapping for common loaders used by AIO
    if isinstance(wv, list) and wv:
        if ct in ("LoadImage",):
            inputs["image"] = wv[0]
        elif ct in ("LoadAudio",):
            inputs["audio"] = wv[0]
        elif ct in ("TrimAudioDuration",):
            if len(wv) >= 1:
                inputs.setdefault("start_index", wv[0])
            if len(wv) >= 2:
                inputs.setdefault("duration", wv[1])
        elif ct in ("CLIPTextEncode", "Text Multiline"):
            inputs["text"] = wv[0] if not isinstance(wv[0], list) else wv[0]
        elif ct in ("JWInteger",):
            inputs["value"] = wv[0]
        elif ct in ("RandomNoise",):
            inputs["noise_seed"] = wv[0]
        elif ct in ("DualClipLoaderGGUF", "DualCLIPLoader"):
            if len(wv) >= 1:
                inputs["clip_name1"] = wv[0]
            if len(wv) >= 2:
                inputs["clip_name2"] = wv[1]
            if len(wv) >= 3:
                inputs["type"] = wv[2]
            if len(wv) >= 4:
                inputs["device"] = wv[3]
        elif ct in ("UnetLoaderGGUF",):
            if len(wv) >= 1:
                inputs["unet_name"] = wv[0]
        elif ct in ("GGUFLoaderKJ",):
            keys = [
                "model_name",
                "extra_model_name",
                "dequant_dtype",
                "patch_dtype",
                "patch_on_device",
                "enable_fp16_accumulation",
                "attention_override",
            ]
            for i, k in enumerate(keys):
                if i < len(wv):
                    inputs[k] = wv[i]
        elif ct in ("VAELoader", "VAELoaderKJ"):
            if len(wv) >= 1:
                inputs["vae_name"] = wv[0]
            if ct == "VAELoaderKJ":
                if len(wv) >= 2:
                    inputs["device"] = wv[1]
                if len(wv) >= 3:
                    inputs["weight_dtype"] = wv[2]
        elif ct in ("mxSlider",):
            if len(wv) >= 1:
                inputs["Xi"] = wv[0]
            if len(wv) >= 2:
                inputs["Xf"] = wv[1]
            if len(wv) >= 3:
                inputs["isfloatX"] = wv[2]
        elif ct in ("Combo Clone",):
            inputs["combo"] = wv[0]
        elif ct in ("ManualSigmas",):
            inputs["sigmas"] = wv[0]
        elif ct in ("KSamplerSelect", "Sampler Selector (Image Saver)"):
            inputs["sampler_name"] = wv[0]
        elif ct in ("CFGGuider",):
            if len(wv) >= 1:
                inputs["cfg"] = wv[0]
        elif ct in ("ComfySwitchNode",):
            if len(wv) >= 1:
                inputs["switch"] = wv[0]
        elif ct in ("SolidMask",):
            if len(wv) >= 1:
                inputs["value"] = wv[0]
            if len(wv) >= 2:
                inputs["width"] = wv[1]
            if len(wv) >= 3:
                inputs["height"] = wv[2]
        elif ct in ("EmptyLTXVLatentVideo",):
            # often linked; widgets may hold defaults
            if len(wv) >= 1:
                inputs.setdefault("width", wv[0])
            if len(wv) >= 2:
                inputs.setdefault("height", wv[1])
            if len(wv) >= 3:
                inputs.setdefault("length", wv[2])
            if len(wv) >= 4:
                inputs.setdefault("batch_size", wv[3])
        elif ct in ("LTXVEmptyLatentAudio",):
            if len(wv) >= 1:
                inputs.setdefault("frames_number", wv[0])
            if len(wv) >= 2:
                inputs.setdefault("frame_rate", wv[1])
            if len(wv) >= 3:
                inputs.setdefault("batch_size", wv[2])
        elif ct in ("LTXVImgToVideoInplace",):
            if len(wv) >= 1:
                inputs.setdefault("strength", wv[0])
            if len(wv) >= 2:
                inputs.setdefault("bypass", wv[1])
        elif ct in ("VHS_VideoCombine",):
            # complex widgets — leave links only; filename_prefix often in widgets
            if isinstance(wv, dict):
                for k in (
                    "frame_rate",
                    "loop_count",
                    "filename_prefix",
                    "format",
                    "pix_fmt",
                    "crf",
                    "save_metadata",
                    "trim_to_audio",
                    "pingpong",
                    "save_output",
                ):
                    if k in wv:
                        inputs[k] = wv[k]
            elif isinstance(wv, list) and len(wv) >= 3:
                # older list layout varies — keep safe defaults
                pass
        elif ct in ("Power Lora Loader (rgthree)",):
            # preserve entire widgets structure in inputs as Comfy API expects
            if isinstance(wv, list):
                # API form from history used named lora_1...
                # Keep widgets_values-like mapping later if needed
                pass
        elif ct in ("SetNode", "GetNode"):
            if len(wv) >= 1:
                # GetNode/SetNode constant name is not an API input usually —
                # these nodes expand differently; keep as-is if present
                pass

    return inputs


def _index_root_links(links: list) -> dict[int, tuple]:
    """link_id -> (origin_id, origin_slot, target_id, target_slot, type)."""
    out: dict[int, tuple] = {}
    for l in links or []:
        if isinstance(l, (list, tuple)) and len(l) >= 6:
            out[int(l[0])] = (l[1], l[2], l[3], l[4], l[5])
        elif isinstance(l, dict) and "id" in l:
            out[int(l["id"])] = (
                l.get("origin_id"),
                l.get("origin_slot"),
                l.get("target_id"),
                l.get("target_slot"),
                l.get("type"),
            )
    return out


def _index_sg_links(links: list) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for l in links or []:
        if isinstance(l, dict) and "id" in l:
            out[int(l["id"])] = l
        elif isinstance(l, (list, tuple)) and len(l) >= 6:
            out[int(l[0])] = {
                "id": l[0],
                "origin_id": l[1],
                "origin_slot": l[2],
                "target_id": l[3],
                "target_slot": l[4],
                "type": l[5],
            }
    return out


def _is_widget_spec(spec: Any) -> bool:
    if not isinstance(spec, list) or not spec:
        return False
    t0 = spec[0]
    if isinstance(t0, list):  # COMBO options
        return True
    if isinstance(t0, str) and t0.upper() in (
        "INT",
        "FLOAT",
        "STRING",
        "BOOLEAN",
        "COMBO",
        "NUMBER",
    ):
        return True
    return False


def _widget_field_names_from_object_info(
    ct: str, object_info: dict[str, Any] | None
) -> list[str]:
    """Ordered widget field names from object_info (required then optional)."""
    if not object_info or ct not in object_info:
        return []
    names: list[str] = []
    req = (object_info[ct].get("input") or {}).get("required") or {}
    opt = (object_info[ct].get("input") or {}).get("optional") or {}
    for d in (req, opt):
        for name, spec in d.items():
            if _is_widget_spec(spec):
                names.append(name)
    return names


def _widget_field_names_from_ui(ui_node: dict[str, Any]) -> list[str]:
    """Prefer UI input order: any input with a ``widget`` key (incl. linked / dynamic combo).

    This is the authoritative order for widgets_values, including nested names like
    ``resize_type.width`` and ``sampling_mode.temperature``.
    """
    names: list[str] = []
    for inp in ui_node.get("inputs") or []:
        if not isinstance(inp, dict):
            continue
        if not inp.get("widget"):
            continue
        name = inp.get("name")
        if name:
            names.append(str(name))
    return names


def _fill_missing_widgets_from_ui(
    api: dict[str, Any],
    ui_by_api_id: dict[str, dict],
    object_info: dict[str, Any] | None = None,
) -> None:
    """Fill widget defaults from UI widgets_values.

    Prefer UI ``widget``-tagged input order (handles DYNAMICCOMBO nested fields).
    Fall back to object_info widget names when UI lacks widget tags.

    widgets_values keeps a slot for every widget including linked ones — advance
    the index for linked slots without overwriting the link.
    """
    for api_id, node in api.items():
        ct = node.get("class_type") or ""
        ui = ui_by_api_id.get(api_id) or {}
        wv = ui.get("widgets_values")
        if wv is None:
            continue
        ins = node.setdefault("inputs", {})
        names = _widget_field_names_from_ui(ui)
        if not names:
            names = _widget_field_names_from_object_info(ct, object_info)
        if isinstance(wv, list) and names:
            # Power Lora list form handled elsewhere
            if ct == "Power Lora Loader (rgthree)":
                continue
            # SamplerCustom: UI has control_after_generate between seed and cfg
            if ct == "SamplerCustom":
                # Keep links; only ensure cfg is a float (not "fixed"/"randomize")
                cfg = ins.get("cfg")
                if isinstance(cfg, str) or cfg is None:
                    cfg_val = 1.0
                    for item in reversed(wv if isinstance(wv, list) else []):
                        if isinstance(item, (int, float)) and not isinstance(item, bool):
                            if float(item) <= 100.0:
                                cfg_val = float(item)
                                break
                    ins["cfg"] = cfg_val
                continue
            # KSampler: same control_after_generate trap
            if ct == "KSampler":
                if isinstance(wv, list) and len(wv) >= 7 and isinstance(wv[1], str):
                    try:
                        ins["seed"] = int(wv[0])
                    except Exception:
                        pass
                    try:
                        ins["steps"] = int(wv[2])
                    except Exception:
                        pass
                    try:
                        ins["cfg"] = float(wv[3])
                    except Exception:
                        pass
                    if isinstance(wv[4], str):
                        ins["sampler_name"] = wv[4]
                    if isinstance(wv[5], str):
                        ins["scheduler"] = wv[5]
                    try:
                        ins["denoise"] = float(wv[6])
                    except Exception:
                        pass
                ins.pop("control_after_generate", None)
                # repair if fill already corrupted
                if isinstance(ins.get("steps"), str):
                    try:
                        ins["steps"] = int(wv[2]) if isinstance(wv, list) and len(wv) > 2 else 20
                    except Exception:
                        ins["steps"] = 20
                if isinstance(ins.get("cfg"), str) or (
                    isinstance(ins.get("sampler_name"), (int, float))
                ):
                    try:
                        ins["cfg"] = float(wv[3]) if isinstance(wv, list) and len(wv) > 3 else 2.5
                    except Exception:
                        ins["cfg"] = 2.5
                    if isinstance(wv, list) and len(wv) > 4 and isinstance(wv[4], str):
                        ins["sampler_name"] = wv[4]
                    if isinstance(wv, list) and len(wv) > 5 and isinstance(wv[5], str):
                        ins["scheduler"] = wv[5]
                    if isinstance(wv, list) and len(wv) > 6:
                        try:
                            ins["denoise"] = float(wv[6])
                        except Exception:
                            ins["denoise"] = 1.0
                continue
            wi = 0
            for name in names:
                if wi >= len(wv):
                    break
                val = wv[wi]
                wi += 1
                if isinstance(val, dict) and val.get("type") == "PowerLoraLoaderHeaderWidget":
                    continue
                # UI-only combos (seed control) must not overwrite real inputs
                if name in ("control_after_generate", "control_before_generate"):
                    continue
                # already a resolved link — keep link, slot consumed
                if name in ins and isinstance(ins[name], list):
                    continue
                if name not in ins:
                    ins[name] = val
                else:
                    cur = ins[name]
                    if not isinstance(cur, list):
                        ins[name] = val
        elif isinstance(wv, dict):
            for k, v in wv.items():
                if k not in ins:
                    ins[k] = v
                elif not isinstance(ins[k], list):
                    ins[k] = v


def expand_ui_workflow_to_api(
    workflow: dict[str, Any],
    object_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Expand UI workflow JSON into API prompt dict (class_type + inputs)."""
    nodes = {n["id"]: n for n in (workflow.get("nodes") or []) if "id" in n}
    root_links = _index_root_links(workflow.get("links") or [])
    subgraphs = {
        sg["id"]: sg for sg in (workflow.get("definitions") or {}).get("subgraphs") or []
    }

    # Map link_id -> (api_origin_id_str, origin_slot)
    link_source: dict[int, tuple[str, int]] = {}

    # First pass: register sources from non-subgraph root nodes
    api: dict[str, Any] = {}

    def add_api_node(api_id: str, ui_node: dict[str, Any], mode: int | None = None) -> None:
        ct = ui_node.get("type")
        if not ct or ct in subgraphs:
            return
        # Skip note-only / markdown
        if ct in ("Note", "MarkdownNote", "PreviewAny"):
            return
        # NEVER (2): omit entirely.
        # BYPASS (4): omit node body — passthrough rewiring is applied later.
        node_mode = mode if mode is not None else ui_node.get("mode", 0)
        try:
            if int(node_mode) in (2, 4):
                return
        except Exception:
            pass
        inputs = _widgets_to_inputs(ui_node)
        # Power Lora special: history used structured inputs — copy from widgets_values list form
        if ct == "Power Lora Loader (rgthree)":
            wv = ui_node.get("widgets_values")
            if isinstance(wv, list):
                # rebuild like history
                inputs = {"PowerLoraLoaderHeaderWidget": {"type": "PowerLoraLoaderHeaderWidget"}}
                li = 1
                for item in wv:
                    if isinstance(item, dict) and "lora" in item:
                        inputs[f"lora_{li}"] = item
                        li += 1
                inputs["➕ Add Lora"] = ""
        # SamplerCustom UI widgets: [add_noise, noise_seed, control_after_generate, cfg]
        # control_after_generate is UI-only and must not land on cfg.
        if ct == "SamplerCustom":
            wv = ui_node.get("widgets_values")
            if isinstance(wv, list) and wv:
                inputs["add_noise"] = bool(wv[0]) if len(wv) >= 1 else True
                if len(wv) >= 2:
                    try:
                        inputs["noise_seed"] = int(wv[1])
                    except Exception:
                        inputs["noise_seed"] = 0
                # cfg is last numeric; skip the 'fixed'/'randomize' control string
                cfg_val = 1.0
                for item in reversed(wv):
                    if isinstance(item, (int, float)) and not isinstance(item, bool):
                        # seed is usually large; cfg is small float
                        if float(item) <= 100.0:
                            cfg_val = float(item)
                            break
                inputs["cfg"] = cfg_val
                inputs.pop("control_after_generate", None)
        # KSampler UI: [seed, control_after_generate, steps, cfg, sampler_name, scheduler, denoise]
        if ct == "KSampler":
            wv = ui_node.get("widgets_values")
            if isinstance(wv, list) and len(wv) >= 7:
                try:
                    inputs["seed"] = int(wv[0])
                except Exception:
                    inputs["seed"] = 0
                # skip wv[1] control_after_generate
                try:
                    inputs["steps"] = int(wv[2])
                except Exception:
                    inputs["steps"] = 20
                try:
                    inputs["cfg"] = float(wv[3])
                except Exception:
                    inputs["cfg"] = 2.5
                inputs["sampler_name"] = wv[4] if isinstance(wv[4], str) else "euler"
                inputs["scheduler"] = wv[5] if isinstance(wv[5], str) else "simple"
                try:
                    inputs["denoise"] = float(wv[6])
                except Exception:
                    inputs["denoise"] = 1.0
                inputs.pop("control_after_generate", None)
            elif isinstance(wv, list) and len(wv) >= 6 and not isinstance(wv[1], str):
                # already without control widget
                pass
        node_api = {"class_type": ct, "inputs": inputs}
        if ui_node.get("title"):
            node_api["_meta"] = {"title": ui_node.get("title")}
        api[api_id] = node_api

    # Register root non-subgraph nodes
    for nid, n in nodes.items():
        t = n.get("type") or ""
        if t in subgraphs:
            continue
        add_api_node(str(nid), n)

    # Map outputs of root nodes to link sources
    for nid, n in nodes.items():
        t = n.get("type") or ""
        if t in subgraphs:
            continue
        try:
            nmode = int(n.get("mode", 0) or 0)
        except Exception:
            nmode = 0
        if nmode == 2:
            continue
        if nmode == 4:
            # BYPASS root node: pass first live input through to all output links
            first_in = None
            for inp in n.get("inputs") or []:
                link = inp.get("link")
                if link is not None and int(link) in link_source:
                    first_in = link_source[int(link)]
                    break
                if link is not None:
                    # origin may not be registered yet — resolve from root_links
                    if int(link) in root_links:
                        oid, oslot, _tid, _ts, _ty = root_links[int(link)]
                        first_in = (str(oid), int(oslot))
                        break
            if first_in is None:
                continue
            for slot, out in enumerate(n.get("outputs") or []):
                for lid in out.get("links") or []:
                    if lid is not None:
                        link_source[int(lid)] = first_in
            continue
        for slot, out in enumerate(n.get("outputs") or []):
            for lid in out.get("links") or []:
                if lid is not None:
                    link_source[int(lid)] = (str(nid), slot)

    # Bypass (mode 4) subgraph instances: map outputs → inputs (UI pass-through)
    bypass_sg_feed: dict[int, dict[int, tuple[str, int]]] = {}
    # Expand each subgraph instance
    for inst_id, inst in nodes.items():
        t = inst.get("type") or ""
        if t not in subgraphs:
            continue
        # Honor switch mute on the *instance* (Fast Groups Bypasser / group mode)
        try:
            inst_mode = int(inst.get("mode", 0) or 0)
        except Exception:
            inst_mode = 0
        if inst_mode == 2:
            # NEVER — omit entirely (no passthrough)
            continue
        if inst_mode == 4:
            # BYPASS — pass-through by *type* (not raw slot index).
            # Distilled LoRA SG: out0/out1 MODEL must map to in0 MODEL, not in1 lora_name.
            feed: dict[int, tuple[str, int]] = {}
            feed_by_type: dict[str, tuple[str, int]] = {}
            for lid, (oid, oslot, tid, tslot, _ty) in root_links.items():
                if tid != inst_id:
                    continue
                src = (
                    link_source[lid]
                    if lid in link_source
                    else (str(oid), int(oslot))
                )
                feed[int(tslot)] = src
                ty = str(_ty or "").upper()
                if ty and ty not in feed_by_type:
                    feed_by_type[ty] = src
            bypass_sg_feed[int(inst_id)] = feed
            sg_def = subgraphs[t]
            sg_outs = sg_def.get("outputs") or []
            for rlid, (roid, roslot, rtid, rtslot, rty) in root_links.items():
                if roid != inst_id:
                    continue
                out_ty = str(rty or "").upper()
                if not out_ty and int(roslot) < len(sg_outs):
                    out_ty = str((sg_outs[int(roslot)] or {}).get("type") or "").upper()
                src = None
                if out_ty and out_ty in feed_by_type:
                    src = feed_by_type[out_ty]
                if src is None:
                    # same-index only when types match / missing type
                    src = feed.get(int(roslot))
                if src is None:
                    src = feed.get(0)
                if src:
                    link_source[int(rlid)] = src
            continue
        sg = subgraphs[t]
        sg_nodes = {n["id"]: n for n in (sg.get("nodes") or []) if "id" in n}
        sg_links = _index_sg_links(sg.get("links") or [])

        # Map: subgraph input slot index -> root (api_id, slot) feeding it
        # From root links targeting inst_id
        input_feed: dict[int, tuple[str, int]] = {}
        for lid, (oid, oslot, tid, tslot, _ty) in root_links.items():
            if tid == inst_id and lid in link_source:
                input_feed[int(tslot)] = link_source[lid]
            elif tid == inst_id:
                # origin might be GetNode already in api
                input_feed[int(tslot)] = (str(oid), int(oslot))

        # Also: subgraph.inputs order defines slots
        sg_inputs = sg.get("inputs") or []

        # Create API nodes for inner nodes
        for iid, inode in sg_nodes.items():
            api_id = f"{inst_id}:{iid}"
            add_api_node(api_id, inode)

        # Map inner outputs to link sources (inner link ids)
        inner_link_source: dict[int, tuple[str, int]] = {}
        for iid, inode in sg_nodes.items():
            api_id = f"{inst_id}:{iid}"
            for slot, out in enumerate(inode.get("outputs") or []):
                for lid in out.get("links") or []:
                    if lid is not None:
                        inner_link_source[int(lid)] = (api_id, slot)

        # Subgraph input virtual: links with origin_id == -10
        # Those should map to input_feed[slot]
        for lid, L in sg_links.items():
            oid = L.get("origin_id")
            oslot = int(L.get("origin_slot") or 0)
            if oid == SG_INPUT_ID:
                if oslot in input_feed:
                    inner_link_source[int(lid)] = input_feed[oslot]
                # else leave unresolved

        # Resolve inputs for inner nodes
        for iid, inode in sg_nodes.items():
            api_id = f"{inst_id}:{iid}"
            if api_id not in api:
                continue
            for inp in inode.get("inputs") or []:
                name = inp.get("name")
                link = inp.get("link")
                if name is None:
                    continue
                if link is not None and int(link) in inner_link_source:
                    src_id, src_slot = inner_link_source[int(link)]
                    api[api_id]["inputs"][name] = [src_id, src_slot]
                # else keep widget value already set

        # Map subgraph outputs: links with target_id == -20
        # Outer root links from inst outputs already point to consumers via root link_source
        # We need to fix link_source for links originating from inst_id
        for lid, L in sg_links.items():
            if L.get("target_id") == SG_OUTPUT_ID:
                # origin is inner node producing this output slot
                oslot = int(L.get("target_slot") or 0)  # output index of subgraph
                origin = L.get("origin_id")
                origin_slot = int(L.get("origin_slot") or 0)
                if origin is None or origin == SG_INPUT_ID:
                    continue
                api_origin = f"{inst_id}:{origin}"
                # Find root links that start from inst_id, origin_slot == oslot
                for rlid, (roid, roslot, rtid, rtslot, rty) in root_links.items():
                    if roid == inst_id and int(roslot) == oslot:
                        link_source[int(rlid)] = (api_origin, origin_slot)

    # Resolve remaining root node inputs that use __link__ or link field
    for nid, n in nodes.items():
        t = n.get("type") or ""
        if t in subgraphs:
            continue
        api_id = str(nid)
        if api_id not in api:
            continue
        for inp in n.get("inputs") or []:
            name = inp.get("name")
            link = inp.get("link")
            if name is None or link is None:
                continue
            if int(link) in link_source:
                src_id, src_slot = link_source[int(link)]
                api[api_id]["inputs"][name] = [src_id, src_slot]

    # Clean __link__ placeholders
    for n in api.values():
        ins = n.get("inputs") or {}
        drop = [k for k, v in ins.items() if isinstance(v, dict) and "__link__" in v]
        for k in drop:
            del ins[k]

    # Resolve SetNode/GetNode pairs into direct links (UI helper nodes, not real API)
    api = _resolve_set_get_nodes(api, workflow)

    # Build ui lookup for widget fill
    ui_by_api_id: dict[str, dict] = {}
    for n in workflow.get("nodes") or []:
        ui_by_api_id[str(n.get("id"))] = n
    for sg in (workflow.get("definitions") or {}).get("subgraphs") or []:
        for root_n in workflow.get("nodes") or []:
            if root_n.get("type") == sg.get("id"):
                inst = root_n.get("id")
                for n in sg.get("nodes") or []:
                    ui_by_api_id[f"{inst}:{n.get('id')}"] = n

    _fill_missing_widgets_from_ui(api, ui_by_api_id, object_info)

    # Resolve Use Everywhere (cg-use-everywhere) broadcasts before dropping AE nodes
    api = _resolve_use_everywhere(api, workflow, ui_by_api_id)

    # Drop note / orchestrator-only helpers that cannot execute via API
    # (UI chrome only — never drop real loaders/samplers; switches use mode mute instead)
    drop_types = {
        "Note",
        "MarkdownNote",
        "OrchestratorNodeMuter",
        "Anything Everywhere",
        "PreviewImage",
        "PreviewAny",
        "GetNode",
        "SetNode",
        "Label (rgthree)",
        "Fast Groups Bypasser (rgthree)",
        "Fast Groups Muter (rgthree)",
        "Bookmarks (rgthree)",
    }
    api = {k: v for k, v in api.items() if v.get("class_type") not in drop_types}

    # Safety: DualCLIP → any encode/lora missing clip (AE fallback if AE parse missed)
    api = _wire_missing_clip_inputs(api)

    # rgthree Context Switch: pick first non-empty context (muted branches omitted)
    api = _resolve_rgthree_context_switches(api, workflow)

    # Any Switch (rgthree): first live input
    api = _resolve_any_switch(api)

    # Remove mode field if present — some Comfy builds reject unknown keys
    for n in api.values():
        n.pop("mode", None)

    # Drop inputs that reference removed (muted) nodes
    for n in api.values():
        ins = n.get("inputs") or {}
        for k, v in list(ins.items()):
            if isinstance(v, list) and len(v) == 2 and str(v[0]) not in api:
                del ins[k]

    # Final cleanup: drop empty Context / Context Switch / Any Switch chrome if unused
    api = _drop_unreferenced_helpers(api)

    return api


# Context (rgthree) / Context Switch output slot index → bus key
_CTX_OUT_SLOTS = (
    "CONTEXT",  # 0
    "MODEL",  # 1
    "CLIP",  # 2
    "VAE",  # 3
    "POSITIVE",  # 4
    "NEGATIVE",  # 5
    "LATENT",  # 6
    "IMAGE",  # 7
    "SEED",  # 8
)
_CTX_IN_KEYS = {
    "MODEL": "model",
    "CLIP": "clip",
    "VAE": "vae",
    "POSITIVE": "positive",
    "NEGATIVE": "negative",
    "LATENT": "latent",
    "IMAGE": ("images", "image"),
    "SEED": "seed",
}


def _resolve_rgthree_context_switches(
    api: dict[str, Any], workflow: dict[str, Any]
) -> dict[str, Any]:
    """Collapse Context Switch (rgthree) to the first Context with live inputs.

    UI Fast Groups Bypasser mutes unused model/CLIP/VAE loaders; Context nodes for
    those branches become empty. Runtime JS picks the first non-empty context —
    API has no JS, so we rewire consumers to that context's underlying links.
    """
    # Build: switch_id -> chosen context api_id
    chosen: dict[str, str] = {}
    for sid, node in api.items():
        if node.get("class_type") != "Context Switch (rgthree)":
            continue
        ins = node.get("inputs") or {}
        pick = None
        for i in range(1, 12):
            key = f"ctx_{i:02d}"
            link = ins.get(key)
            if not (isinstance(link, list) and len(link) == 2):
                continue
            ctx_id = str(link[0])
            ctx = api.get(ctx_id) or {}
            if ctx.get("class_type") != "Context (rgthree)":
                # still allow non-empty
                pick = ctx_id
                break
            ctx_ins = ctx.get("inputs") or {}
            has_live = False
            for ck, cv in ctx_ins.items():
                if ck == "base_ctx":
                    continue
                if isinstance(cv, list) and len(cv) == 2 and str(cv[0]) in api:
                    has_live = True
                    break
            if has_live:
                pick = ctx_id
                break
        if pick:
            chosen[str(sid)] = pick

    if not chosen:
        return api

    def _source_for(switch_id: str, out_slot: int) -> list | None:
        ctx_id = chosen.get(str(switch_id))
        if not ctx_id:
            return None
        ctx = api.get(ctx_id) or {}
        if out_slot < 0 or out_slot >= len(_CTX_OUT_SLOTS):
            return None
        bus = _CTX_OUT_SLOTS[out_slot]
        if bus == "CONTEXT":
            return [ctx_id, 0]
        keys = _CTX_IN_KEYS.get(bus)
        if keys is None:
            return None
        if isinstance(keys, str):
            keys = (keys,)
        ctx_ins = ctx.get("inputs") or {}
        for k in keys:
            v = ctx_ins.get(k)
            if isinstance(v, list) and len(v) == 2:
                return list(v)
        return None

    # Rewire all consumers of Context Switch outputs
    for _nid, node in api.items():
        ins = node.get("inputs") or {}
        for k, v in list(ins.items()):
            if not (isinstance(v, list) and len(v) == 2):
                continue
            src_id, src_slot = str(v[0]), int(v[1])
            if src_id not in chosen:
                continue
            rep = _source_for(src_id, src_slot)
            if rep is not None:
                ins[k] = rep

    return api


def _resolve_any_switch(api: dict[str, Any]) -> dict[str, Any]:
    """Any Switch (rgthree): first live linked input → rewire consumers of output 0."""
    picks: dict[str, list] = {}
    for sid, node in api.items():
        if node.get("class_type") != "Any Switch (rgthree)":
            continue
        ins = node.get("inputs") or {}
        # common names: any_01 / input_01 / or ordered any_01...
        for i in range(1, 16):
            for key in (f"any_{i:02d}", f"input_{i:02d}", f"any_{i}", f"input_{i}"):
                v = ins.get(key)
                if isinstance(v, list) and len(v) == 2 and str(v[0]) in api:
                    picks[str(sid)] = list(v)
                    break
            if str(sid) in picks:
                break
        if str(sid) not in picks:
            # fallback: first list-valued input
            for _k, v in ins.items():
                if isinstance(v, list) and len(v) == 2 and str(v[0]) in api:
                    picks[str(sid)] = list(v)
                    break

    if not picks:
        return api
    for _nid, node in api.items():
        ins = node.get("inputs") or {}
        for k, v in list(ins.items()):
            if isinstance(v, list) and len(v) == 2 and str(v[0]) in picks:
                ins[k] = list(picks[str(v[0])])
    return api


def _drop_unreferenced_helpers(api: dict[str, Any]) -> dict[str, Any]:
    """Remove Context/Switch chrome that nothing references (optional cleanup)."""
    helper = {
        "Context (rgthree)",
        "Context Switch (rgthree)",
        "Any Switch (rgthree)",
    }
    referenced: set[str] = set()
    for node in api.values():
        for v in (node.get("inputs") or {}).values():
            if isinstance(v, list) and len(v) >= 1:
                referenced.add(str(v[0]))
    # Keep helpers still referenced; drop unreferenced helpers only
    out = {}
    for nid, node in api.items():
        ct = node.get("class_type") or ""
        if ct in helper and str(nid) not in referenced:
            continue
        out[nid] = node
    return out


def _resolve_use_everywhere(
    api: dict[str, Any],
    workflow: dict[str, Any],
    ui_by_api_id: dict[str, dict],
) -> dict[str, Any]:
    """Wire unlinked inputs that Use Everywhere would fill (type broadcast)."""
    # type_upper -> [src_api_id, slot]
    broadcasts: dict[str, list] = {}
    for api_id, node in api.items():
        if node.get("class_type") != "Anything Everywhere":
            continue
        ui = ui_by_api_id.get(str(api_id)) or {}
        # Match UI input labels/types to resolved API inputs
        for inp in ui.get("inputs") or []:
            name = inp.get("name")
            if not name:
                continue
            src = (node.get("inputs") or {}).get(name)
            if not (isinstance(src, list) and len(src) == 2):
                continue
            ty = str(inp.get("type") or inp.get("label") or "").upper()
            if not ty or ty == "*":
                # try label
                ty = str(inp.get("label") or "").upper()
            if ty and ty != "*":
                broadcasts[ty] = [str(src[0]), int(src[1])]

    if not broadcasts:
        return api

    # For each node, if an input type matches a broadcast and is missing, fill it
    for api_id, node in api.items():
        if node.get("class_type") == "Anything Everywhere":
            continue
        ui = ui_by_api_id.get(str(api_id)) or {}
        ins = node.setdefault("inputs", {})
        for inp in ui.get("inputs") or []:
            name = inp.get("name")
            if not name or name in ins:
                continue
            # only fill if unlinked in UI (link is None) — AE fills those
            if inp.get("link") is not None:
                continue
            ty = str(inp.get("type") or "").upper()
            if ty in broadcasts:
                ins[name] = list(broadcasts[ty])
    return api


def _wire_missing_clip_inputs(api: dict[str, Any]) -> dict[str, Any]:
    """Fallback: connect DualCLIP loaders to nodes that need CLIP."""
    clip_src = None
    for nid, node in api.items():
        ct = node.get("class_type") or ""
        if ct in ("DualClipLoaderGGUF", "DualCLIPLoader", "CLIPLoader", "CLIPLoaderGGUF"):
            clip_src = [str(nid), 0]
            break
    if not clip_src:
        return api
    need_clip_types = {
        "CLIPTextEncode",
        "TextGenerateLTX2Prompt",
        "Power Lora Loader (rgthree)",
        "LoraLoader",
        "LoraLoaderModelOnly",
    }
    for _nid, node in api.items():
        ct = node.get("class_type") or ""
        if ct not in need_clip_types:
            continue
        ins = node.setdefault("inputs", {})
        if "clip" not in ins:
            # LoraLoaderModelOnly has no clip — skip if not in inputs schema
            if ct == "LoraLoaderModelOnly":
                continue
            ins["clip"] = list(clip_src)
    return api


def _bus_name_from_ui(ui: dict[str, Any]) -> str | None:
    wv = ui.get("widgets_values") or []
    if wv and isinstance(wv[0], str) and wv[0].strip():
        return wv[0].strip()
    title = ui.get("title") or ""
    # titles like Set_m audio in / Get_m vae video
    for prefix in ("Set_", "Get_"):
        if title.startswith(prefix) and len(title) > len(prefix):
            # Set_m audio in -> m audio in
            rest = title[len(prefix) :]
            return rest.strip() or None
    return None


def _resolve_set_get_nodes(api: dict[str, Any], workflow: dict[str, Any]) -> dict[str, Any]:
    """Wire consumers of GetNode to the source of the matching SetNode name.

    Multi-pass: SetNodes may chain; GetNodes may feed other SetNodes.
    """
    ui_by_api_id: dict[str, dict] = {}
    for n in workflow.get("nodes") or []:
        ui_by_api_id[str(n.get("id"))] = n
    for sg in (workflow.get("definitions") or {}).get("subgraphs") or []:
        for root_n in workflow.get("nodes") or []:
            if root_n.get("type") == sg.get("id"):
                inst = root_n.get("id")
                for n in sg.get("nodes") or []:
                    ui_by_api_id[f"{inst}:{n.get('id')}"] = n

    def first_link(node: dict[str, Any]) -> list | None:
        for _k, v in (node.get("inputs") or {}).items():
            if isinstance(v, list) and len(v) == 2:
                return list(v)
        return None

    # Multi-pass resolve (Get->Set chains)
    for _pass in range(8):
        set_map: dict[str, list] = {}
        for api_id, node in api.items():
            if node.get("class_type") != "SetNode":
                continue
            ui = ui_by_api_id.get(str(api_id)) or {}
            name = _bus_name_from_ui(ui)
            src = first_link(node)
            if name and src:
                # If src is a GetNode that already resolved... follow below after map
                set_map[name] = src

        get_ids: dict[str, str] = {}
        for api_id, node in api.items():
            if node.get("class_type") != "GetNode":
                continue
            ui = ui_by_api_id.get(str(api_id)) or {}
            name = _bus_name_from_ui(ui)
            if name:
                get_ids[str(api_id)] = name

        changed = 0
        for _nid, node in api.items():
            ins = node.get("inputs") or {}
            for k, v in list(ins.items()):
                if not (isinstance(v, list) and len(v) == 2):
                    continue
                src_id = str(v[0])
                # follow GetNode
                if src_id in get_ids:
                    gname = get_ids[src_id]
                    if gname in set_map:
                        new_v = list(set_map[gname])
                        # unwrap Get->Get by one hop if needed
                        if str(new_v[0]) in get_ids and get_ids[str(new_v[0])] in set_map:
                            new_v = list(set_map[get_ids[str(new_v[0])]])
                        if new_v != v:
                            ins[k] = new_v
                            changed += 1
        if changed == 0:
            break

    return api
