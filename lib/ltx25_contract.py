"""Version and result checks for the opt-in LTX-2.5 path; no GPU imports."""

from pathlib import Path


def active_loras(api):
    return [{"node": str(nid), "slot": key, **value}
            for nid, node in api.items()
            for key, value in node.get("inputs", {}).items()
            if key.startswith("lora_") and isinstance(value, dict) and value.get("on")]


def check_ltx25_graph(api, *, lora_policy="quality"):
    """Reject accidental legacy model/active adapter selections before queueing."""
    selected = []
    for node in api.values():
        inputs = node.get("inputs", {})
        kind = node.get("class_type", "")
        if kind in ("UNETLoader", "CLIPLoader", "VAELoader", "VAELoaderKJ", "LatentUpscaleModelLoader"):
            for key in ("unet_name", "clip_name", "vae_name", "model_name"):
                name = inputs.get(key)
                if isinstance(name, str) and ("ltx" in name.lower() or "gemma" in name.lower()):
                    # TAE preview is not used as the main decoder.
                    if name == "taeltx2_3.safetensors":
                        continue
                    if "2.5" not in name:
                        raise ValueError(f"LTX-2.5 path selected legacy component: {name}")
                    selected.append(name)
        for key, value in inputs.items():
            if lora_policy == "none" and key.startswith("lora_") and isinstance(value, dict) and value.get("on"):
                raise ValueError(f"Explicit no-LoRA policy still has an enabled adapter: {value.get('lora')}")
    if not any("ltx-2.5-22b-distilled-transformer" in name for name in selected):
        raise ValueError("LTX-2.5 distilled transformer missing from expanded graph")
    return sorted(set(selected))


def find_completed_media(history, output_root, *, audio_only=False):
    """Require server success and a nonempty, contained output artifact."""
    status = history.get("status", {})
    if status.get("status_str") != "success" or status.get("completed") is not True:
        raise RuntimeError(f"Generation did not complete successfully: {status}")
    root = Path(output_root).resolve()
    extensions = {".wav", ".flac", ".mp3", ".ogg"} if audio_only else {".mp4", ".mkv", ".webm", ".mov"}
    for output in history.get("outputs", {}).values():
        for key in ("gifs", "images", "videos", "audio", "audios"):
            entries = output.get(key, [])
            if isinstance(entries, dict):
                entries = [entries]
            for item in entries:
                if not isinstance(item, dict) or item.get("type", "output") != "output":
                    continue
                path = (root / item.get("subfolder", "") / item.get("filename", "")).resolve()
                if not path.is_relative_to(root) or path.suffix.lower() not in extensions:
                    continue
                if path.is_file() and path.stat().st_size > 0:
                    return path
    raise FileNotFoundError("Server completed but no nonempty output media file exists")
