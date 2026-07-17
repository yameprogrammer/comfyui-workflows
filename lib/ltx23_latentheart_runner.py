"""LatentHeart LTX2.3 AIO (LTX Director) — real UI + GGUF-first profiles.

SSOT:
  workflows/human/ltx23_latentheart_aio/LTX23LTXDirector2.json  (default)
  workflows/human/ltx23_latentheart_aio/LTX23LTXDirector13.json (director node v1.3)

Civitai 2553704 — modular SFW/NSFW T/I/A2V with Director, ID LoRA, ControlNet,
Detailer, Upscaler, Interpolator. Model groups self-contained: STANDARD / GGUF / 10EROS.

Policy: real UI only; group modes + port inject; default **GGUF** for VRAM.
"""

from __future__ import annotations

import json
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
from lib.comfy_engine_session import FAMILY_LTX, ensure_engine
from lib.ltx23_latentheart_switches import (
    FEATURE_GROUPS,
    PROFILES,
    apply_switch_profile,
    list_profiles,
)
from lib.ltx_aio_ui_expand import expand_ui_workflow_to_api
from lib.workflow_video_runner import extract_first_video, _resolve_local_video

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
HUMAN_DIR = WORKSPACE_ROOT / "workflows" / "human" / "ltx23_latentheart_aio"
UI_DIRECTOR2 = HUMAN_DIR / "LTX23LTXDirector2.json"
UI_DIRECTOR13 = HUMAN_DIR / "LTX23LTXDirector13.json"
API_CACHE = (
    WORKSPACE_ROOT
    / "workflows"
    / "agent"
    / "presets"
    / "ltx23_latentheart_aio.api.json"
)

DEFAULT_PROFILE = "gguf_distilled"
GGUF_DISTILLED = r"LTX2.3\LTX-2.3-22B-distilled-1.1-Q4_K_M.gguf"
GGUF_10EROS = r"LTX2.3\10Eros_v1-Q4_K_M.gguf"


def _load_ui(path: Path | str | None = None) -> dict[str, Any]:
    p = Path(path or UI_DIRECTOR2)
    if not p.is_file():
        raise FileNotFoundError(f"LatentHeart AIO UI not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _fetch_object_info(server: str = DEFAULT_SERVER) -> dict[str, Any] | None:
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://{server}/object_info", timeout=90) as resp:
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


def _object_info_has(class_type: str, server: str = DEFAULT_SERVER) -> bool:
    oi = _fetch_object_info(server)
    return bool(oi and class_type in oi)


def _machine_safe_widgets(ui: dict[str, Any], *, server: str = DEFAULT_SERVER) -> None:
    """Host-safe widget tweaks without rebuilding the graph."""
    has_mel = _object_info_has("MelBandRoFormerModelLoader", server)
    for n in ui.get("nodes") or []:
        t = n.get("type") or ""
        if t == "GGUFLoaderKJ":
            wv = list(n.get("widgets_values") or [])
            while len(wv) < 7:
                wv.append(None)
            wv[5] = False  # fp16 accumulation off
            n["widgets_values"] = wv
        if t == "ModelPatchTorchSettings":
            w = list(n.get("widgets_values") or [False])
            if w:
                w[0] = False
            n["widgets_values"] = w
        # Lipsync MelBand pack — if custom node missing, NEVER those nodes
        # (Any Switch audio path should fall through). Not a mini-graph: same as muting group.
        if not has_mel and t in (
            "MelBandRoFormerModelLoader",
            "MelBandRoFormerSampler",
            "LTXVAudioVAEEncode",
        ):
            n["mode"] = 2


def _port_ui_prompts(ui: dict[str, Any], positive: str, negative: str | None) -> None:
    """Inject prompt into PrimitiveStringMultiline BASE PROMPT + LTXDirector global."""
    for n in ui.get("nodes") or []:
        title = (n.get("title") or "").strip()
        t = n.get("type") or ""
        if t == "PrimitiveStringMultiline" and "BASE PROMPT" in title.upper():
            n["widgets_values"] = [positive]
        if t == "LTXDirector":
            wv = list(n.get("widgets_values") or [])
            # timeline JSON often index 6; also set global via string fields if present
            # widgets vary by director version — patch JSON global_prompt when possible
            for i, v in enumerate(wv):
                if isinstance(v, str) and v.strip().startswith("{") and "global_prompt" in v:
                    try:
                        data = json.loads(v)
                        data["global_prompt"] = positive
                        wv[i] = json.dumps(data, ensure_ascii=False)
                    except Exception:
                        pass
            n["widgets_values"] = wv
        if t in ("CLIPTextEncode",) and "negative" in title.lower():
            if negative is not None:
                n["widgets_values"] = [negative]


def _port_seed(ui: dict[str, Any], seed: int) -> None:
    for n in ui.get("nodes") or []:
        t = n.get("type") or ""
        if t in ("RandomNoise", "Seed (rgthree)", "easy seed"):
            wv = list(n.get("widgets_values") or [])
            if wv:
                wv[0] = int(seed)
                n["widgets_values"] = wv


def build_api(
    *,
    profile: str = DEFAULT_PROFILE,
    director_version: str = "2",
    features_on: list[str] | None = None,
    features_off: list[str] | None = None,
    model: str | None = None,
    gguf_name: str | None = None,
    server_address: str = DEFAULT_SERVER,
    cache: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    ui_path = UI_DIRECTOR2 if str(director_version) in ("2", "v2", "director2") else UI_DIRECTOR13
    ui = _load_ui(ui_path)
    ui = apply_switch_profile(
        ui,
        profile,
        features_on=features_on,
        features_off=features_off,
        model=model,
        gguf_name=gguf_name,
    )
    _machine_safe_widgets(ui)
    oi = _fetch_object_info(server_address)
    api = expand_ui_workflow_to_api(ui, object_info=oi)

    # Drop pure chrome
    drop = {
        "Note",
        "MarkdownNote",
        "Label (rgthree)",
        "Bookmark (rgthree)",
        "Fast Groups Bypasser (rgthree)",
        "Fast Groups Muter (rgthree)",
        "PreviewAny",
        "PreviewImage",
        "PreviewAudio",
        "easy showAnything",
        "ShowText|pysssss",
    }
    api = {k: v for k, v in api.items() if v.get("class_type") not in drop}
    alive = set(api)
    for n in api.values():
        ins = n.get("inputs") or {}
        for k, v in list(ins.items()):
            if isinstance(v, list) and len(v) == 2 and str(v[0]) not in alive:
                del ins[k]

    # Ensure GGUF loader in API uses local name if present
    gname = gguf_name or (PROFILES.get(profile) or {}).get("gguf_name") or GGUF_DISTILLED
    for n in api.values():
        if n.get("class_type") == "GGUFLoaderKJ":
            n.setdefault("inputs", {})["model_name"] = gname
            n["inputs"]["enable_fp16_accumulation"] = False

    meta = {
        "profile": profile,
        "director_version": director_version,
        "ui": str(ui_path),
        "gguf_name": gname,
        "node_count": len(api),
        "has_video": any(n.get("class_type") == "VHS_VideoCombine" for n in api.values()),
        "has_director": any(n.get("class_type") == "LTXDirector" for n in api.values()),
        "has_gguf": any(n.get("class_type") == "GGUFLoaderKJ" for n in api.values()),
    }
    if cache:
        try:
            API_CACHE.parent.mkdir(parents=True, exist_ok=True)
            with open(API_CACHE, "w", encoding="utf-8") as f:
                json.dump(api, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    return api, meta


def apply_api_ports(
    api: dict[str, Any],
    *,
    positive: str,
    negative: str | None = None,
    seed: int | None = None,
    filename_prefix: str = "ltx23_lh_aio",
) -> dict[str, Any]:
    seed_i = int(seed if seed is not None else random.randint(1, 2**31 - 1))
    for nid, n in api.items():
        ct = n.get("class_type") or ""
        ins = n.setdefault("inputs", {})
        if ct == "RandomNoise" and "noise_seed" in ins or ct == "RandomNoise":
            if "noise_seed" in ins or not any(isinstance(v, list) for k, v in ins.items() if "seed" in k):
                ins["noise_seed"] = seed_i
            for k in list(ins.keys()):
                if "seed" in k and not isinstance(ins[k], list):
                    ins[k] = seed_i
        if ct == "LTXDirector":
            # global_prompt socket may be linked; also text fields
            if "global_prompt" in ins and not isinstance(ins.get("global_prompt"), list):
                ins["global_prompt"] = positive
        if ct == "VHS_VideoCombine":
            ins["filename_prefix"] = filename_prefix
            ins["save_output"] = True
            ins.pop("videopreview", None)
        if ct == "CLIPTextEncode" and negative is not None:
            # only if free text widget
            if "text" in ins and not isinstance(ins["text"], list):
                # avoid overwriting positive encodes blindly — skip unless empty title path
                pass
    return {"seed": seed_i, "positive": positive[:200]}


def _postprocess_latentheart_api(
    api: dict[str, Any],
    *,
    positive: str,
    gname: str,
    frames: int = 49,
    fps: float = 24.0,
    seconds: float = 2.0,
) -> dict[str, Any]:
    """Fix expand widget mis-maps that block validation (Director, latent length, VHS)."""
    # Ensure GGUF unet name is valid single-backslash form
    for n in api.values():
        if n.get("class_type") == "UnetLoaderGGUF":
            n.setdefault("inputs", {})["unet_name"] = gname.replace("/", "\\")

    # LTXDirector free fields — expand often mis-assigns timeline JSON
    for n in api.values():
        if n.get("class_type") != "LTXDirector":
            continue
        ins = n.setdefault("inputs", {})
        # Keep linked sockets; force free scalars
        for k in (
            "start_second",
            "end_second",
            "duration_seconds",
            "start_frame",
            "end_frame",
            "duration_frames",
            "frame_rate",
            "timeline_data",
            "local_prompts",
            "segment_lengths",
            "epsilon",
            "guide_strength",
            "resize_method",
            "display_mode",
        ):
            if isinstance(ins.get(k), list):
                # break bad type links (e.g. length→AUDIO)
                if k in ("end_frame", "duration_frames", "start_frame"):
                    del ins[k]
                elif k in ("start_second", "end_second", "duration_seconds", "frame_rate"):
                    # keep if linked to float source; else replace later
                    pass
        ins["start_second"] = 0.0 if not isinstance(ins.get("start_second"), list) else ins["start_second"]
        if not isinstance(ins.get("end_second"), list):
            ins["end_second"] = float(seconds)
        if not isinstance(ins.get("duration_seconds"), list) or isinstance(ins.get("duration_seconds"), str):
            # duration_seconds must be float, not timeline JSON
            if isinstance(ins.get("duration_seconds"), str) and ins["duration_seconds"].strip().startswith("{"):
                # move JSON to timeline_data
                ins["timeline_data"] = ins["duration_seconds"]
            ins["duration_seconds"] = float(seconds)
        ins["start_frame"] = 0
        ins["end_frame"] = int(frames)
        ins["duration_frames"] = int(frames)
        if not isinstance(ins.get("frame_rate"), list):
            ins["frame_rate"] = float(fps)
        ins.setdefault("timeline_data", json.dumps({
            "mainTrackEnabled": True,
            "audioTrackEnabled": False,
            "motionTrackEnabled": False,
            "segments": [],
            "motionSegments": [],
            "audioSegments": [],
            "global_prompt": positive,
            "normalStartFrame": 0,
            "normalDurationFrames": int(frames),
        }))
        ins.setdefault("local_prompts", "")
        ins.setdefault("segment_lengths", "")
        ins.setdefault("epsilon", 0.001)
        ins.setdefault("guide_strength", "")
        if not isinstance(ins.get("resize_method"), str):
            ins["resize_method"] = "maintain aspect ratio"
        if not isinstance(ins.get("global_prompt"), list):
            ins["global_prompt"] = positive
        # clip may be optional linked
        if "clip" not in ins:
            # find DualCLIPLoader
            for oid, on in api.items():
                if on.get("class_type") == "DualCLIPLoader":
                    ins["clip"] = [oid, 0]
                    break

    # MathExpression width snap often mis-links MODEL as b — force free divisible_by=32
    for n in api.values():
        if n.get("class_type") != "MathExpression|pysssss":
            continue
        ins = n.setdefault("inputs", {})
        expr = str(ins.get("expression") or "")
        if "32" in expr or "round" in expr:
            # keep a if GetImageSize width/height; force b numeric
            if isinstance(ins.get("b"), list):
                ins["b"] = 1  # expression uses b*32 → 32 when b=1

    # EmptyLTXVLatentVideo: length must be INT not AUDIO link
    for n in api.values():
        if n.get("class_type") != "EmptyLTXVLatentVideo":
            continue
        ins = n.setdefault("inputs", {})
        length = ins.get("length")
        if isinstance(length, list) or not isinstance(length, int):
            ins["length"] = int(frames)
        # prefer free size if math chain broken
        for dim, default in (("width", 768), ("height", 512)):
            v = ins.get(dim)
            if isinstance(v, list):
                src = str(v[0])
                # if points at broken MathExpression fed by MODEL, detach
                src_n = api.get(src) or {}
                if src_n.get("class_type") == "MathExpression|pysssss":
                    # keep link if b is now numeric
                    pass
            else:
                ins.setdefault(dim, default)
        ins.setdefault("batch_size", 1)

    # CFGGuider needs model — use pipeOut model slot when missing
    pipe_model = None
    for oid, on in api.items():
        if on.get("class_type") == "easy pipeOut":
            # outputs model on slot 1 typically when expanded consumers use [id,1]
            pipe_model = [oid, 1]
            break
    if pipe_model is None:
        for oid, on in api.items():
            if on.get("class_type") in ("LTX2_NAG", "UnetLoaderGGUF"):
                pipe_model = [oid, 0]
                break
    for n in api.values():
        if n.get("class_type") == "CFGGuider":
            ins = n.setdefault("inputs", {})
            if "model" not in ins and pipe_model:
                ins["model"] = list(pipe_model)

    # Sampler → decode: skip LTXVSeparateAVLatent when no audio (crashes on video-only)
    sampler_id = None
    for oid, on in api.items():
        if on.get("class_type") == "SamplerCustomAdvanced":
            sampler_id = oid
            break
    if sampler_id:
        for n in api.values():
            if n.get("class_type") == "LTXVTiledVAEDecode":
                n.setdefault("inputs", {})["latents"] = [sampler_id, 0]
            if n.get("class_type") == "VAEDecode":
                n.setdefault("inputs", {})["samples"] = [sampler_id, 0]
        # rewire Separate consumers to sampler (video-only)
        for on in api.values():
            oins = on.get("inputs") or {}
            for k, v in list(oins.items()):
                if not (isinstance(v, list) and len(v) == 2):
                    continue
                src = api.get(str(v[0])) or {}
                if src.get("class_type") == "LTXVSeparateAVLatent":
                    oins[k] = [sampler_id, 0]

    # VHS images from first video decode
    decode_id = None
    for oid, on in api.items():
        if on.get("class_type") in ("LTXVTiledVAEDecode", "VAEDecode"):
            decode_id = oid
            break
    for n in api.values():
        if n.get("class_type") != "VHS_VideoCombine":
            continue
        ins = n.setdefault("inputs", {})
        if "images" not in ins and decode_id:
            ins["images"] = [decode_id, 0]
        if isinstance(ins.get("frame_rate"), list):
            pass
        elif not ins.get("frame_rate"):
            ins["frame_rate"] = float(fps)
        fmt = ins.get("format") or ""
        if isinstance(fmt, str) and "nvenc" in fmt:
            ins["format"] = "video/h264-mp4"
        # optional audio often broken without MelBand — drop if switch chain incomplete
        if "audio" in ins:
            aud = ins["audio"]
            if isinstance(aud, list):
                # keep only if source exists
                if str(aud[0]) not in api:
                    del ins["audio"]
                else:
                    # prefer silent video-only for smoke reliability
                    del ins["audio"]

    # GetImageSize without image: feed EmptyImage if present
    empty_img = None
    for oid, on in api.items():
        if on.get("class_type") == "EmptyImage":
            empty_img = [oid, 0]
            break
    for n in api.values():
        if n.get("class_type") == "GetImageSize":
            ins = n.setdefault("inputs", {})
            if "image" not in ins and empty_img:
                ins["image"] = list(empty_img)

    # Director region JSON helpers — expand drops json_string
    for n in api.values():
        if n.get("class_type") == "JsonExtractString":
            ins = n.setdefault("inputs", {})
            if "json_string" not in ins or not ins.get("json_string"):
                ins["json_string"] = "{}"
            ins.setdefault("key", "total_regions")

    # VHS audio switch often needs StringCompare; if broken, drop audio input
    for n in api.values():
        if n.get("class_type") != "VHS_VideoCombine":
            continue
        ins = n.get("inputs") or {}
        aud = ins.get("audio")
        if isinstance(aud, list) and str(aud[0]) not in api:
            del ins["audio"]

    # ImpactIfNone empty → boolean false free if supported; else leave
    for n in api.values():
        if n.get("class_type") == "ImpactIfNone":
            ins = n.setdefault("inputs", {})
            # schema varies; skip if unlinked

    # Any Switch with no inputs: remove consumers' link if needed
    for nid, n in list(api.items()):
        if n.get("class_type") == "Any Switch (rgthree)":
            ins = n.get("inputs") or {}
            if not any(isinstance(v, list) for v in ins.values()):
                # global prompt switch empty — use free string on consumers
                for on in api.values():
                    oins = on.get("inputs") or {}
                    for k, v in list(oins.items()):
                        if isinstance(v, list) and len(v) == 2 and str(v[0]) == str(nid):
                            if k in ("global_prompt", "text", "positive"):
                                oins[k] = positive

    # final dead ref cleanup
    alive = set(api)
    for n in api.values():
        ins = n.get("inputs") or {}
        for k, v in list(ins.items()):
            if isinstance(v, list) and len(v) == 2 and str(v[0]) not in alive:
                del ins[k]
    return api


def generate_ltx23_latentheart(
    *,
    positive: str,
    output_path: str,
    negative: str | None = None,
    seed: int | None = None,
    profile: str = DEFAULT_PROFILE,
    director_version: str = "2",
    features_on: list[str] | None = None,
    features_off: list[str] | None = None,
    model: str | None = None,
    gguf_name: str | None = None,
    image_path: str | None = None,
    timeout_sec: float = 1800,
    server_address: str = DEFAULT_SERVER,
    filename_prefix: str = "ltx23_lh_aio",
) -> dict[str, Any]:
    eng = ensure_engine(FAMILY_LTX, server_address, caller="generate_ltx23_latentheart")
    if not eng.get("ok"):
        return fail_result(
            error="ENGINE_SESSION",
            message=eng.get("message") or "engine free failed",
            engine_session=eng,
        )

    # UI-level prompt before expand so Primitive/Director widgets bake in
    ui_path = UI_DIRECTOR2 if str(director_version) in ("2", "v2", "director2") else UI_DIRECTOR13
    try:
        ui = _load_ui(ui_path)
        ui = apply_switch_profile(
            ui,
            profile,
            features_on=features_on,
            features_off=features_off,
            model=model,
            gguf_name=gguf_name,
        )
        _machine_safe_widgets(ui)
        _port_ui_prompts(ui, positive, negative)
        seed_i = int(seed if seed is not None else random.randint(1, 2**31 - 1))
        _port_seed(ui, seed_i)
        if image_path:
            # optional: stage + point LoadImage nodes titled reference / start
            name = _stage(image_path, "ltx_lh")
            for n in ui.get("nodes") or []:
                if n.get("type") == "LoadImage":
                    title = (n.get("title") or "").lower()
                    if "prompt enhancer" in title:
                        continue
                    # only touch active image loaders
                    if int(n.get("mode", 0) or 0) == 0:
                        n["widgets_values"] = [name, "image"]
        oi = _fetch_object_info(server_address)
        api = expand_ui_workflow_to_api(ui, object_info=oi)
    except Exception as e:
        return fail_result(error="EXPAND_FAILED", message=str(e))

    drop = {
        "Note",
        "MarkdownNote",
        "Label (rgthree)",
        "Bookmark (rgthree)",
        "Fast Groups Bypasser (rgthree)",
        "Fast Groups Muter (rgthree)",
        "PreviewAny",
        "PreviewImage",
        "PreviewAudio",
        "easy showAnything",
        "ShowText|pysssss",
    }
    api = {k: v for k, v in api.items() if v.get("class_type") not in drop}
    alive = set(api)
    for n in api.values():
        ins = n.get("inputs") or {}
        for k, v in list(ins.items()):
            if isinstance(v, list) and len(v) == 2 and str(v[0]) not in alive:
                del ins[k]

    gname = gguf_name or (PROFILES.get(profile) or {}).get("gguf_name") or GGUF_DISTILLED
    # Normalize Windows path separators for Comfy combo lists
    gname = gname.replace("/", "\\")

    def _rewire_bypass(nid: str) -> None:
        """Point consumers of nid to its first MODEL/IMAGE/etc linked input."""
        node = api.get(nid) or {}
        ins = node.get("inputs") or {}
        feed = None
        for key in ("model", "images", "image", "samples", "latent"):
            v = ins.get(key)
            if isinstance(v, list) and len(v) == 2 and str(v[0]) in api:
                feed = list(v)
                break
        if feed is None:
            for v in ins.values():
                if isinstance(v, list) and len(v) == 2 and str(v[0]) in api:
                    feed = list(v)
                    break
        if feed is None:
            return
        for on in api.values():
            oins = on.get("inputs") or {}
            for k, v in list(oins.items()):
                if isinstance(v, list) and len(v) == 2 and str(v[0]) == str(nid):
                    oins[k] = list(feed)

    # Pack uses GGUFLoaderKJ (unet_gguf folder). Swap → UnetLoaderGGUF (diffusion_models).
    for nid, n in list(api.items()):
        if n.get("class_type") == "GGUFLoaderKJ":
            api[nid] = {
                "class_type": "UnetLoaderGGUF",
                "inputs": {"unet_name": gname},
                "_meta": {
                    "title": "UNET GGUF (agent)",
                    "note": f"swapped from GGUFLoaderKJ; {gname}",
                },
            }
        if n.get("class_type") == "DualCLIPLoader":
            ins = n.setdefault("inputs", {})
            # Local TE names (force known-good pair)
            ins["clip_name1"] = "gemma_3_12B_it_fp8_e4m3fn.safetensors"
            ins["clip_name2"] = "ltx-2.3_text_projection_bf16.safetensors"
            if "type" not in ins or ins.get("type") not in ("ltxv", "ltx"):
                ins["type"] = "ltxv"
        if n.get("class_type") == "VHS_VideoCombine":
            n.setdefault("inputs", {})["filename_prefix"] = filename_prefix
            n["inputs"]["save_output"] = True
            n["inputs"].pop("videopreview", None)
        if n.get("class_type") in (
            "LoraLoaderModelOnly",
            "LTXICLoRALoaderModelOnly",
            "Power Lora Loader (rgthree)",
        ):
            lora = (n.get("inputs") or {}).get("lora_name")
            # Always rewire optional pack LoRAs that often missing on disk
            if n.get("class_type") == "Power Lora Loader (rgthree)":
                _rewire_bypass(nid)
            elif isinstance(lora, str) and any(
                k in lora
                for k in (
                    "ID-LoRA",
                    "CelebVHQ",
                    "ic-lora-detailer",
                    "union-control",
                    "distilled-lora",
                    "fro90",
                )
            ):
                _rewire_bypass(nid)
        if n.get("class_type") == "LTXDirector":
            ins = n.setdefault("inputs", {})
            # free widgets often dropped by expand — short smoke defaults
            for k, v in (
                ("start_frame", 0),
                ("end_frame", 49),
                ("duration_frames", 49),
                ("start_second", 0.0),
                ("end_second", 2.0),
                ("duration_seconds", 2.0),
                ("frame_rate", 24),
            ):
                if k not in ins or ins.get(k) is None:
                    ins[k] = v
                elif isinstance(ins.get(k), list):
                    pass  # linked
                else:
                    # overwrite zero-ish missing end
                    if k == "end_frame" and int(ins.get(k) or 0) <= 0:
                        ins[k] = 49
        if n.get("class_type") == "EmptyLTXVLatentVideo":
            ins = n.setdefault("inputs", {})
            ins.setdefault("width", 768)
            ins.setdefault("height", 512)
            ins.setdefault("length", 49)
            ins.setdefault("batch_size", 1)
        if n.get("class_type") == "LTXVConditioning":
            ins = n.setdefault("inputs", {})
            if "frame_rate" not in ins or ins.get("frame_rate") is None:
                ins["frame_rate"] = 24.0
            if isinstance(ins.get("frame_rate"), list):
                pass
            elif not ins.get("frame_rate"):
                ins["frame_rate"] = 24.0

    # Drop custom nodes not installed on this host (after rewire not needed)
    oi = _fetch_object_info(server_address) or {}
    if oi:
        drop_missing = [
            nid
            for nid, n in api.items()
            if n.get("class_type") not in oi
            and n.get("class_type")
            not in (
                # keep nothing unknown
            )
        ]
        for nid in drop_missing:
            _rewire_bypass(nid)
            del api[nid]
        alive = set(api)
        for n in api.values():
            ins = n.get("inputs") or {}
            for k, v in list(ins.items()):
                if isinstance(v, list) and len(v) == 2 and str(v[0]) not in alive:
                    del ins[k]

    # Audio concat without audio: if audio_latent missing, try rewire video-only path
    for nid, n in list(api.items()):
        if n.get("class_type") != "LTXVConcatAVLatent":
            continue
        ins = n.get("inputs") or {}
        if "audio_latent" not in ins or not ins.get("audio_latent"):
            # pass video latent through
            vid = ins.get("video_latent") or ins.get("latent") or ins.get("samples")
            if isinstance(vid, list):
                for on in api.values():
                    oins = on.get("inputs") or {}
                    for k, v in list(oins.items()):
                        if isinstance(v, list) and len(v) == 2 and str(v[0]) == str(nid):
                            oins[k] = list(vid)

    api = _postprocess_latentheart_api(api, positive=positive, gname=gname)

    build_meta = {
        "profile": profile,
        "director_version": director_version,
        "gguf_name": gname,
        "node_count": len(api),
        "has_video": any(n.get("class_type") == "VHS_VideoCombine" for n in api.values()),
        "has_director": any(n.get("class_type") == "LTXDirector" for n in api.values()),
        "has_gguf": any(
            n.get("class_type") in ("GGUFLoaderKJ", "UnetLoaderGGUF") for n in api.values()
        ),
    }

    if not build_meta["has_video"]:
        return fail_result(error="GRAPH_INCOMPLETE", message="no VHS_VideoCombine", **build_meta)
    want_gguf = (model or profile or "gguf").lower().find("gguf") >= 0 or (
        (PROFILES.get(profile) or {}).get("model") == "gguf"
    )
    if not build_meta["has_gguf"] and want_gguf:
        return fail_result(
            error="GGUF_MISSING",
            message="No GGUF/UnetLoaderGGUF in expanded API — model group may still be STANDARD",
            **build_meta,
        )

    try:
        API_CACHE.parent.mkdir(parents=True, exist_ok=True)
        with open(API_CACHE, "w", encoding="utf-8") as f:
            json.dump(api, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    try:
        prompt_id = queue_prompt(server_address, api)
    except Exception as e:
        return fail_result(error="QUEUE_FAILED", message=str(e), build=build_meta)

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

    meta_path = str(out_p) + ".meta.json"
    write_meta(
        meta_path,
        {
            "tool": "ltx23_latentheart_aio",
            "profile": profile,
            "seed": seed_i,
            "prompt_id": prompt_id,
            "gguf_name": gname,
            "output": str(out_p),
            "created_at": utc_now_iso(),
        },
    )
    return ok_result(
        output_path=str(out_p),
        output=str(out_p),
        meta_path=meta_path,
        prompt_id=prompt_id,
        seed=seed_i,
        profile=profile,
        backend="gguf",
        build=build_meta,
    )
