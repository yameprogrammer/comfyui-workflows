"""RedCraft LTX2.3 I2V REDMix (NEWKrea2 collection) — real UI + GGUF fallback.

SSOT:
  workflows/human/ltx23_redmix_krea2/NEWKrea2LTX23Ideogram4_ltx23redmixkrea2.json

Civitai collection 579280 · version LTX2.3REDMixKrea2
  Outer graph: LoadImage → subgraph Image-to-Video (LTX-2.3) → SaveVideo
  Designed to animate stills (e.g. Krea2/Ideogram outputs) with LTX 2.3 I2V 2-pass.

Pack default UNET: REDGTA1.1_LTX23-int4-convrot.safetensors (often missing).
Agent default: UnetLoaderGGUF LTX distilled Q4_K_M (local), optional 10Eros GGUF.
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
from lib.ltx_aio_ui_expand import expand_ui_workflow_to_api
from lib.workflow_video_runner import extract_first_video, _resolve_local_video

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
HUMAN_DIR = WORKSPACE_ROOT / "workflows" / "human" / "ltx23_redmix_krea2"
HUMAN_UI = HUMAN_DIR / "NEWKrea2LTX23Ideogram4_ltx23redmixkrea2.json"
API_CACHE = (
    WORKSPACE_ROOT
    / "workflows"
    / "agent"
    / "presets"
    / "ltx23_redmix_krea2.api.json"
)

# Pack default (RedCraft specialized LTX) — usually not installed
PACK_UNET = "REDGTA1.1_LTX23-int4-convrot.safetensors"
# Local GGUF substitutes
GGUF_DISTILLED = r"LTX2.3\LTX-2.3-22B-distilled-1.1-Q4_K_M.gguf"
GGUF_10EROS = r"LTX2.3\10Eros_v1-Q4_K_M.gguf"
GGUF_DEV = r"LTX2.3\ltx-2.3-22b-dev-Q4_K_M.gguf"

CLIP_LOCAL = "gemma_3_12B_it_fp8_e4m3fn.safetensors"
CLIP_PROJ = "ltx-2.3_text_projection_bf16.safetensors"
DISTILL_LORA = r"LTX2.3\ltx-2.3-22b-distilled-1.1_lora-dynamic_fro09_avg_rank_111_bf16.safetensors"

BACKENDS = {
    "gguf_distilled": GGUF_DISTILLED,
    "gguf_10eros": GGUF_10EROS,
    "gguf_dev": GGUF_DEV,
}


def _load_ui(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path or HUMAN_UI)
    if not p.is_file():
        raise FileNotFoundError(f"redmix UI not found: {p}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _fetch_oi(server: str = DEFAULT_SERVER) -> dict[str, Any]:
    import urllib.request

    with urllib.request.urlopen(f"http://{server}/object_info", timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _stage(src: str, prefix: str = "redmix") -> str:
    src_p = Path(src)
    if not src_p.is_file():
        raise FileNotFoundError(src)
    dest = Path(COMFYUI_INPUT_DIR)
    dest.mkdir(parents=True, exist_ok=True)
    name = f"{prefix}_{int(time.time())}_{src_p.name}"
    shutil.copy2(src_p, dest / name)
    return name


def _rewire_model_passthrough(api: dict[str, Any], nid: str) -> None:
    node = api.get(nid) or {}
    ins = node.get("inputs") or {}
    feed = ins.get("model")
    if not (isinstance(feed, list) and len(feed) == 2):
        return
    for on in api.values():
        oins = on.get("inputs") or {}
        for k, v in list(oins.items()):
            if isinstance(v, list) and len(v) == 2 and str(v[0]) == str(nid):
                oins[k] = list(feed)


def _sanitize_api(
    api: dict[str, Any],
    *,
    backend: str,
    unet_name: str | None,
    positive: str,
    negative: str | None,
    image_name: str,
    seed: int,
    width: int | None,
    height: int | None,
    duration: int | None,
    fps: int | None,
    filename_prefix: str,
) -> dict[str, Any]:
    gname = (unet_name or BACKENDS.get(backend) or GGUF_DISTILLED).replace("/", "\\")
    use_gguf = (
        str(backend).startswith("gguf")
        or str(gname).lower().endswith(".gguf")
    )
    if str(backend).startswith("pack"):
        use_gguf = False
        gname = unet_name or PACK_UNET

    drop = {
        "Note",
        "MarkdownNote",
        "Reroute",
        "easy showAnything",
        "PreviewImage",
        "PreviewAny",
    }
    api = {k: v for k, v in api.items() if v.get("class_type") not in drop}

    for nid, n in list(api.items()):
        ct = n.get("class_type") or ""
        ins = n.setdefault("inputs", {})

        if ct == "UNETLoader" and use_gguf:
            api[nid] = {
                "class_type": "UnetLoaderGGUF",
                "inputs": {"unet_name": gname},
                "_meta": {
                    "title": "UNET GGUF (agent)",
                    "note": f"pack REDGTA missing → {gname}",
                },
            }
            continue

        if ct == "UNETLoader" and not use_gguf:
            ins["unet_name"] = unet_name or PACK_UNET
            ins.setdefault("weight_dtype", "default")

        if ct == "UnetLoaderGGUF":
            ins["unet_name"] = gname

        if ct == "DualCLIPLoader":
            # heretic int8 often missing → local fp8 gemma
            ins["clip_name1"] = CLIP_LOCAL
            ins["clip_name2"] = CLIP_PROJ
            ins["type"] = "ltxv"
            ins.setdefault("device", "default")

        if ct == "LoraLoaderModelOnly":
            lora = ins.get("lora_name")
            if isinstance(lora, str):
                # fix distilled path prefix LTX2\ → LTX2.3\
                if "distilled" in lora.lower() and "fro09" in lora.lower():
                    ins["lora_name"] = DISTILL_LORA
                elif any(k in lora for k in ("yoyo", "clapping-cheeks", "clapping")):
                    _rewire_model_passthrough(api, nid)

        if ct == "LoadImage":
            ins["image"] = image_name
            ins["upload"] = "image"

        if ct == "CLIPTextEncode":
            # positive is Chinese default game prompt; negative is quality ban
            # identify by content
            text = ins.get("text")
            if isinstance(text, str):
                if "pc game" in text.lower() or "cartoon" in text.lower():
                    if negative is not None:
                        ins["text"] = negative
                else:
                    # main prompt
                    ins["text"] = positive

        if ct == "TextGenerateLTX2Prompt":
            # optional enhancer — feed base prompt into text field if present
            if "text" in ins and not isinstance(ins["text"], list):
                ins["text"] = positive
            if "prompt" in ins and not isinstance(ins["prompt"], list):
                ins["prompt"] = positive

        if ct == "RandomNoise":
            ins["noise_seed"] = int(seed)

        if ct == "EmptyLTXVLatentVideo":
            if width is not None:
                ins["width"] = int(width)
            if height is not None:
                ins["height"] = int(height)
            if duration is not None:
                # duration in frames often
                ins["length"] = int(duration)
            ins.setdefault("batch_size", 1)

        if ct == "PrimitiveInt":
            # subgraph ports may map to primitives — leave unless we find titles
            pass

        if ct == "LTXVConditioning":
            if fps is not None and not isinstance(ins.get("frame_rate"), list):
                ins["frame_rate"] = float(fps)
            ins.setdefault("frame_rate", 24.0)

        if ct == "CreateVideo":
            if fps is not None and not isinstance(ins.get("fps"), list):
                ins["fps"] = float(fps)

        if ct == "SaveVideo":
            ins["filename_prefix"] = filename_prefix
            # prefer widely available codec
            if ins.get("format") in (None, "auto"):
                ins["format"] = "mp4"
            if ins.get("codec") in (None, "auto"):
                ins["codec"] = "h264"

        if ct == "CFGGuider" and "model" not in ins:
            # should already be linked; leave
            pass

    # Optional LoRAs often missing (yoyo / clapping-cheeks)
    for nid, n in list(api.items()):
        if n.get("class_type") != "LoraLoaderModelOnly":
            continue
        lora = (n.get("inputs") or {}).get("lora_name")
        if isinstance(lora, str) and (
            "yoyo" in lora.lower() or "clapping" in lora.lower()
        ):
            _rewire_model_passthrough(api, nid)

    # Pack uses Anything Everywhere / GetNode for VAE — re-wire to real VAELoader
    video_vae = None
    audio_vae = None
    for nid, n in api.items():
        if n.get("class_type") != "VAELoader":
            continue
        name = str((n.get("inputs") or {}).get("vae_name") or "")
        if "audio" in name.lower():
            audio_vae = nid
        else:
            video_vae = nid

    def _link_ok(v: Any) -> bool:
        return isinstance(v, list) and len(v) == 2 and str(v[0]) in api

    for nid, n in api.items():
        ct = n.get("class_type") or ""
        ins = n.setdefault("inputs", {})
        if video_vae and ct in (
            "LTXVImgToVideoInplace",
            "LTXVLatentUpsampler",
            "VAEDecodeTiled",
            "VAEDecode",
        ):
            if not _link_ok(ins.get("vae")):
                ins["vae"] = [video_vae, 0]
        # LTXVPreprocess has no vae input — strip if expand wrongly attached
        if ct == "LTXVPreprocess" and "vae" in ins:
            del ins["vae"]
        if audio_vae and ct in ("LTXVEmptyLatentAudio", "LTXVAudioVAEDecode"):
            if not _link_ok(ins.get("audio_vae")):
                ins["audio_vae"] = [audio_vae, 0]
            # some schemas use vae for audio decoder
            if ct == "LTXVAudioVAEDecode" and not _link_ok(ins.get("vae")):
                if "vae" in (n.get("inputs") or {}) or "audio_vae" not in ins:
                    pass
                if "audio_vae" not in ins:
                    ins["audio_vae"] = [audio_vae, 0]

    # Drop missing class types
    try:
        oi = _fetch_oi()
    except Exception:
        oi = {}
    if oi:
        for nid in list(api.keys()):
            ct = api[nid].get("class_type")
            if ct and ct not in oi:
                _rewire_model_passthrough(api, nid)
                if nid in api and api[nid].get("class_type") not in (
                    "UnetLoaderGGUF",
                    "UNETLoader",
                ):
                    del api[nid]

    alive = set(api)
    for n in api.values():
        ins = n.get("inputs") or {}
        for k, v in list(ins.items()):
            if isinstance(v, list) and len(v) == 2 and str(v[0]) not in alive:
                del ins[k]

    return api


def generate_ltx23_redmix_i2v(
    *,
    image_path: str,
    positive: str,
    output_path: str,
    negative: str | None = None,
    seed: int | None = None,
    backend: str = "gguf_distilled",
    unet_name: str | None = None,
    width: int | None = None,
    height: int | None = None,
    duration_frames: int | None = 49,
    fps: int | None = 24,
    timeout_sec: float = 900,
    server_address: str = DEFAULT_SERVER,
    filename_prefix: str = "ltx23_redmix",
    ui_path: str | Path | None = None,
) -> dict[str, Any]:
    eng = ensure_engine(FAMILY_LTX, server_address, caller="generate_ltx23_redmix_i2v")
    if not eng.get("ok"):
        return fail_result(
            error="ENGINE_SESSION",
            message=eng.get("message") or "engine free failed",
            engine_session=eng,
        )

    seed_i = int(seed if seed is not None else random.randint(1, 2**31 - 1))
    try:
        image_name = _stage(image_path, "redmix_i2v")
        ui = _load_ui(ui_path)
        # patch root LoadImage before expand
        for n in ui.get("nodes") or []:
            if n.get("type") == "LoadImage":
                n["widgets_values"] = [image_name, "image"]
        oi = _fetch_oi(server_address)
        api = expand_ui_workflow_to_api(ui, object_info=oi)
    except Exception as e:
        return fail_result(error="EXPAND_FAILED", message=str(e))

    try:
        api = _sanitize_api(
            api,
            backend=backend,
            unet_name=unet_name,
            positive=positive,
            negative=negative
            or "pc game, console game, video game, cartoon, childish, ugly, low quality, blur",
            image_name=image_name,
            seed=seed_i,
            width=width,
            height=height,
            duration=duration_frames,
            fps=fps,
            filename_prefix=filename_prefix,
        )
    except Exception as e:
        return fail_result(error="SANITIZE_FAILED", message=str(e))

    build = {
        "backend": backend,
        "unet": unet_name or BACKENDS.get(backend) or GGUF_DISTILLED,
        "node_count": len(api),
        "has_video_out": any(
            n.get("class_type") in ("SaveVideo", "CreateVideo", "VHS_VideoCombine")
            for n in api.values()
        ),
        "has_gguf": any(n.get("class_type") == "UnetLoaderGGUF" for n in api.values()),
    }

    try:
        API_CACHE.parent.mkdir(parents=True, exist_ok=True)
        with open(API_CACHE, "w", encoding="utf-8") as f:
            json.dump(api, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    if not build["has_video_out"]:
        return fail_result(error="GRAPH_INCOMPLETE", message="no video save node", **build)

    try:
        prompt_id = queue_prompt(server_address, api)
    except Exception as e:
        return fail_result(error="QUEUE_FAILED", message=str(e), build=build)

    try:
        entry = wait_for_history(server_address, prompt_id, timeout_sec=timeout_sec)
        if isinstance(entry, dict) and prompt_id in entry and "outputs" not in entry:
            entry = entry[prompt_id]
        # SaveVideo may put video under different keys
        try:
            fn, sub, typ = extract_first_video(entry)
        except Exception:
            # try videos/gifs/images recursively
            outs = entry.get("outputs") or {}
            found = None
            for _nid, o in outs.items():
                for key in ("gifs", "videos", "images", "video"):
                    items = o.get(key)
                    if isinstance(items, list) and items:
                        it = items[0]
                        if isinstance(it, dict) and it.get("filename"):
                            found = (
                                it["filename"],
                                it.get("subfolder") or "",
                                it.get("type") or "output",
                            )
                            break
                if found:
                    break
            if not found:
                raise
            fn, sub, typ = found
        src = _resolve_local_video(fn, sub, typ)
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out_p)
    except Exception as e:
        return fail_result(
            error="RUN_FAILED",
            message=str(e),
            prompt_id=prompt_id,
            build=build,
        )

    meta_path = str(out_p) + ".meta.json"
    write_meta(
        meta_path,
        {
            "tool": "ltx23_redmix_krea2",
            "backend": backend,
            "unet": build["unet"],
            "seed": seed_i,
            "prompt_id": prompt_id,
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
        backend=backend,
        build=build,
    )
