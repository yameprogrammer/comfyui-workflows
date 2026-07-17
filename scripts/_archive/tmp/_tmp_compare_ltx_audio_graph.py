#!/usr/bin/env python3
"""Compare agent LTX i2v_audio graph vs human AIO audio-related wiring."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.ltx_s2v import build_ltx_aio_mode_api  # noqa: E402


def dump_agent() -> None:
    api = build_ltx_aio_mode_api(
        mode="i2v_audio",
        first_image="temp_s2v_input.png",
        audio_name="temp_s2v_drive.wav",
        prompt="test speak",
        negative="bad",
        width=544,
        height=960,
        num_frames=89,
        fps=24.0,
        seed=1,
    )
    print("=== AGENT i2v_audio graph ===")
    for nid, n in sorted(
        api.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else 999
    ):
        print(f"{nid}: {n['class_type']}")
        for k, v in (n.get("inputs") or {}).items():
            print(f"    {k} = {v}")


def dump_human() -> None:
    p = ROOT / "workflows" / "human" / "ltx23AllInOneWorkflowForRTX_v44.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    links = {l[0]: l for l in data.get("links", [])}

    def src(link_id):
        if link_id is None:
            return None
        l = links.get(link_id)
        if not l:
            return f"missing:{link_id}"
        # [id, from_node, from_slot, to_node, to_slot, type]
        return f"n{l[1]}.out{l[2]} type={l[5]}"

    print("\n=== HUMAN AIO Audio / LTXV / AV path ===")
    keys = (
        "Audio",
        "Concat",
        "Separate",
        "AV",
        "LTXV",
        "ImgToVideo",
        "EmptyLTXV",
        "CreateVideo",
        "SaveVideo",
        "Guider",
        "SamplerCustom",
        "ManualSigmas",
        "AddGuide",
        "Conditioning",
        "TrimAudio",
        "LoadAudio",
        "Mel",
        "Voice",
        "ICLoRA",
        "Lip",
    )
    for n in sorted(data.get("nodes", []), key=lambda x: x.get("id", 0)):
        t = n.get("type") or ""
        title = n.get("title") or ""
        blob = f"{t} {title}"
        if not any(k.lower() in blob.lower() for k in keys):
            continue
        print(f"id={n['id']} mode={n.get('mode')} type={t} title={title!r}")
        wv = n.get("widgets_values")
        if wv is not None:
            s = json.dumps(wv, ensure_ascii=False)
            if len(s) > 240:
                s = s[:240] + "..."
            print(f"  widgets: {s}")
        for inp in n.get("inputs") or []:
            if inp.get("link") is not None:
                name = inp.get("name")
                print(f"  in {name} from {src(inp.get('link'))}")


def find_audio_input_label() -> None:
    p = ROOT / "workflows" / "human" / "ltx23AllInOneWorkflowForRTX_v44.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    print("\n=== nodes with title containing Audio input / P: ===")
    for n in data.get("nodes", []):
        title = n.get("title") or ""
        if "Audio" in title or "[[P:" in title or "audio" in title.lower():
            print(f"id={n['id']} mode={n.get('mode')} type={n.get('type')} title={title!r}")
            print(f"  widgets={n.get('widgets_values')}")


if __name__ == "__main__":
    dump_agent()
    dump_human()
    find_audio_input_label()
