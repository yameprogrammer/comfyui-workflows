#!/usr/bin/env python3
"""Extract AIO subgraph audio path by reconstructing links from node outputs."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / "workflows" / "human" / "ltx23AllInOneWorkflowForRTX_v44.json"


def main() -> None:
    data = json.loads(WF.read_text(encoding="utf-8"))
    sg = data["definitions"]["subgraphs"][0]
    nodes = {n["id"]: n for n in sg["nodes"]}
    links = sg.get("links") or []
    print("links", type(links), len(links))
    if links:
        print("link0 type", type(links[0]), str(links[0])[:200])

    # map link_id -> source
    by_out = {}
    for n in sg["nodes"]:
        for oi, out in enumerate(n.get("outputs") or []):
            for lid in out.get("links") or []:
                by_out[lid] = {
                    "from_id": n["id"],
                    "from_slot": oi,
                    "from_name": out.get("name"),
                    "from_type": n.get("type"),
                    "from_title": n.get("title"),
                    "from_mode": n.get("mode"),
                }

    # map link_id -> consumers
    by_in = {}
    for n in sg["nodes"]:
        for inp in n.get("inputs") or []:
            lid = inp.get("link")
            if lid is None:
                continue
            by_in.setdefault(lid, []).append(
                {
                    "to_id": n["id"],
                    "to_type": n.get("type"),
                    "to_title": n.get("title"),
                    "to_mode": n.get("mode"),
                    "in_name": inp.get("name"),
                }
            )

    def dump_node(nid: int) -> None:
        n = nodes[nid]
        print(
            f"\nNODE {nid} mode={n.get('mode')} type={n.get('type')} title={n.get('title')!r}"
        )
        print("  widgets=", n.get("widgets_values"))
        for inp in n.get("inputs") or []:
            lid = inp.get("link")
            src = by_out.get(lid)
            if src:
                print(
                    f"  in {inp.get('name')} <- {src['from_id']} "
                    f"{src['from_type']} mode={src['from_mode']} "
                    f"title={src['from_title']!r} out={src['from_name']}"
                )
            else:
                w = (inp.get("widget") or {}).get("name")
                print(f"  in {inp.get('name')} (widget={w}) link={lid}")
        for oi, out in enumerate(n.get("outputs") or []):
            for lid in out.get("links") or []:
                for c in by_in.get(lid, []):
                    print(
                        f"  out[{oi}:{out.get('name')}] -> {c['to_id']} "
                        f"{c['to_type']} mode={c['to_mode']} in={c['in_name']} "
                        f"title={c['to_title']!r}"
                    )

    focus = [
        1061,  # EmptyLatentAudio
        1201,  # AudioVAEEncode (always)
        1495,  # AudioVAEEncode [[P:Audio input]] muted
        1496,  # SolidMask
        1499,  # SetLatentNoiseMask
        1202,  # AudioVideoMask
        1193,  # ImgToVideo
        1155,
        1163,
        1055,  # Concat
        1782,
        1054,  # Sampler
        1066,
        1068,
        1783,
        1064,
        1060,
        1196,
    ]
    for nid in focus:
        if nid in nodes:
            dump_node(nid)

    # Who feeds 1055 audio_latent and video_latent
    print("\n=== PATH TO SAMPLER 1054 latent_image ===")
    dump_node(1054)
    print("\n=== PATH TO SAMPLER 1066 latent_image ===")
    dump_node(1066)


if __name__ == "__main__":
    main()
