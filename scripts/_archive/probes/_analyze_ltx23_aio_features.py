#!/usr/bin/env python3
"""
Deep-scan ltx23AllInOneWorkflowForRTX_v44 for Select options / switches / [[P:]] tags.
Writes:
  workflows/human/LTX23_AIO_v44_CAPABILITIES.json
  workflows/human/LTX23_AIO_v44_AGENT_GUIDE.md
  workflows/agent/presets/ltx23_aio_feature_presets.json
"""
from __future__ import annotations

import _bootstrap  # noqa: F401
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"F:\ComfyUI_workflows\agent_custom")
SRC = ROOT / "workflows" / "human" / "ltx23AllInOneWorkflowForRTX_v44.json"
HUMAN = ROOT / "workflows" / "human"
PRESETS = ROOT / "workflows" / "agent" / "presets"

P_TAG_RE = re.compile(r"\[\[P:([^\]]+)\]\]")
MODE_LABEL = {0: "ALWAYS", 2: "NEVER", 4: "BYPASS"}


def iter_all_nodes(wf: dict):
    for n in wf.get("nodes") or []:
        yield "root", n
    for sg in (wf.get("definitions") or {}).get("subgraphs") or []:
        name = sg.get("name") or sg.get("id") or "subgraph"
        for n in sg.get("nodes") or []:
            yield name, n


def main() -> None:
    wf = json.loads(SRC.read_text(encoding="utf-8"))
    type_counts = Counter()
    p_tags = Counter()
    p_nodes: dict[str, list] = defaultdict(list)
    selectors = []
    switches = []
    notes = []
    groups = []

    for layer, n in iter_all_nodes(wf):
        t = n.get("type") or ""
        type_counts[t] += 1
        title = n.get("title") or ""
        mode = n.get("mode", 0)
        widgets = n.get("widgets_values")
        for tag in P_TAG_RE.findall(title):
            p_tags[tag] += 1
            p_nodes[tag].append(
                {
                    "layer": layer,
                    "id": n.get("id"),
                    "type": t,
                    "title": title,
                    "mode": mode,
                    "mode_name": MODE_LABEL.get(mode, str(mode)),
                }
            )
        tl = t.lower()
        titl = title.lower()
        if any(
            k in tl or k in titl
            for k in (
                "select",
                "switch",
                "orchestr",
                "muter",
                "bypass",
                "impactint",
                "any switch",
                "power lora",
            )
        ):
            entry = {
                "layer": layer,
                "id": n.get("id"),
                "type": t,
                "title": title,
                "mode": mode,
                "widgets": widgets,
                "properties": {
                    k: (n.get("properties") or {}).get(k)
                    for k in (
                        "Node name for S&R",
                        "cnr_id",
                        "proxyWidgets",
                    )
                    if (n.get("properties") or {}).get(k) is not None
                },
            }
            if "orchestr" in tl or "muter" in tl or "select" in titl:
                selectors.append(entry)
            elif "switch" in tl or "switch" in titl:
                switches.append(entry)
            else:
                switches.append(entry)
        if t in ("Note", "MarkdownNote") and widgets:
            text = widgets[0] if isinstance(widgets, list) and widgets else str(widgets)
            if isinstance(text, str) and (
                "Select" in text or "Audio" in text or "Image to Video" in text
            ):
                notes.append(
                    {
                        "layer": layer,
                        "id": n.get("id"),
                        "title": title,
                        "text_preview": text[:1500],
                    }
                )

    for g in wf.get("groups") or []:
        groups.append(
            {
                "title": g.get("title"),
                "color": g.get("color"),
                "bounding": g.get("bounding"),
            }
        )

    # Official mode table (from existing mode_select + notes)
    from lib.ltx_aio_mode_select import AIO_MODE_PORTS, ALL_P_PORTS, describe_mode

    features = []
    mode_to_backend = {
        "i2v": "ltx23_aio_i2v",
        "i2v_audio": "ltx23_aio",
        "flf": "ltx23_aio_flf",
        "flf_audio": "ltx23_aio_flf_audio",
        "fml": "ltx23_aio_fml",
        "fml_audio": "ltx23_aio_fml_audio",
        "v2v": "ltx23_aio_v2v",
        "v2v_audio": "ltx23_aio_v2v_audio",
        "v2v_true": "ltx23_aio_v2v_true",
        "v2v_true_audio": "ltx23_aio_v2v_true_audio",
        "t2v": "ltx23_aio_t2v",
        "t2v_audio": "ltx23_aio_t2v_audio",
    }
    # Add v2v_true as alias of v2v ports if missing from AIO_MODE_PORTS
    feature_rows = [
        ("mode_t2v", "t2v", "Text to Video", ["prompt"], False),
        ("mode_t2v_audio", "t2v_audio", "Text + Audio to Video", ["prompt", "audio"], True),
        ("mode_i2v", "i2v", "Image to Video", ["image", "prompt"], False),
        (
            "mode_i2v_audio",
            "i2v_audio",
            "Image + Audio to Video (SI2V default)",
            ["image", "audio", "prompt"],
            True,
        ),
        (
            "mode_flf",
            "flf",
            "First/Last Frame",
            ["image", "last_image", "prompt"],
            False,
        ),
        (
            "mode_flf_audio",
            "flf_audio",
            "First/Last + Audio",
            ["image", "last_image", "audio", "prompt"],
            True,
        ),
        (
            "mode_fml",
            "fml",
            "First/Mid/Last Frame",
            ["image", "mid_image", "last_image", "prompt"],
            False,
        ),
        (
            "mode_fml_audio",
            "fml_audio",
            "First/Mid/Last + Audio",
            ["image", "mid_image", "last_image", "audio", "prompt"],
            True,
        ),
        (
            "mode_v2v",
            "v2v",
            "Video to Video",
            ["image_or_ref", "video", "prompt"],
            False,
        ),
        (
            "mode_v2v_audio",
            "v2v_audio",
            "Video to Video + Audio",
            ["image_or_ref", "video", "audio", "prompt"],
            True,
        ),
    ]
    for fid, mode, label, inputs, needs_audio in feature_rows:
        try:
            desc = describe_mode(mode)
            ports = desc["active_ports"]
        except ValueError:
            ports = sorted(AIO_MODE_PORTS.get(mode, set()))
        features.append(
            {
                "feature_id": fid,
                "mode": mode,
                "label": label,
                "select_options": ports,
                "backend": mode_to_backend.get(mode, f"ltx23_aio_{mode}"),
                "cli": f"python scripts/generate_s2v.py --backend {mode_to_backend.get(mode, 'ltx23_aio')} --ltx-mode {mode}",
                "required_inputs": inputs,
                "needs_audio": needs_audio,
                "status": "ready",
                "p_tagged_nodes": {
                    p: len(p_nodes.get(p, [])) for p in ports
                },
            }
        )

    # Secondary switches found in scan
    secondary = []
    for s in selectors + switches:
        secondary.append(
            {
                "id": s["id"],
                "type": s["type"],
                "title": s["title"],
                "layer": s["layer"],
                "widgets": s.get("widgets"),
            }
        )

    caps = {
        "workflow": "ltx23AllInOneWorkflowForRTX_v44",
        "source_ui": str(SRC).replace("\\", "/"),
        "version": 1,
        "architecture": {
            "root_nodes": len(wf.get("nodes") or []),
            "subgraphs": len((wf.get("definitions") or {}).get("subgraphs") or []),
            "type_counts_top": type_counts.most_common(30),
        },
        "select_options_ports": sorted(ALL_P_PORTS),
        "p_tag_counts": dict(p_tags.most_common()),
        "p_tag_nodes": {k: v for k, v in p_nodes.items()},
        "features": features,
        "orchestrator_selectors": selectors,
        "switches": switches,
        "notes_relevant": notes,
        "groups": groups,
        "agent_policy": {
            "selection": "feature_id or --ltx-mode or --backend ltx23_aio_*",
            "implementation": (
                "apply_aio_mode_to_ui_workflow([[P:]] mute) + expand_ui_workflow_to_api "
                "+ port inject (prompt/seed/image/audio/edge/aspect/fps)"
            ),
            "do_not": [
                "homemade mini graph as default",
                "rename [[P:]] tags or group P",
                "leave Orchestrator UI widgets as sole source of truth (re-apply mode each run)",
            ],
            "cli_list": "python scripts/run_ltx_aio_features.py --list",
            "cli_run": "python scripts/generate_s2v.py --backend ltx23_aio_i2v | --ltx-mode i2v_audio ...",
        },
        "param_ports": [
            {"name": "prompt", "role": "positive text"},
            {"name": "negative", "role": "negative text"},
            {"name": "seed", "role": "sampler seed"},
            {"name": "image", "role": "first frame / I2V"},
            {"name": "last_image", "role": "FLF last frame"},
            {"name": "mid_image", "role": "FML mid frame"},
            {"name": "audio", "role": "SI2V drive wav"},
            {"name": "video", "role": "V2V drive video"},
            {"name": "longer_edge", "role": "resolution long edge"},
            {"name": "aspect", "role": "9:16 or 16:9"},
            {"name": "fps", "role": "usually 24 for AIO distill"},
            {"name": "clip_length_sec", "role": "AIO clip length slider"},
            {"name": "trim_start_sec", "role": "audio/video trim start"},
        ],
    }

    out_caps = HUMAN / "LTX23_AIO_v44_CAPABILITIES.json"
    out_caps.write_text(
        json.dumps(caps, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("wrote", out_caps)

    # Feature presets index (agent)
    fp = {
        "version": 1,
        "description": "LTX 2.3 AIO v44 feature → backend/mode selection",
        "source_ui": "workflows/human/ltx23AllInOneWorkflowForRTX_v44.json",
        "runner": "lib/ltx_aio_workflow_runner.py",
        "select_preset": {
            "default_s2v": "i2v_audio",
            "default_i2v": "i2v",
            "by_mode": {f["mode"]: f["backend"] for f in features},
        },
        "features": {
            f["feature_id"]: {
                "mode": f["mode"],
                "backend": f["backend"],
                "select_options": f["select_options"],
                "status": f["status"],
                "cli": f["cli"],
            }
            for f in features
        },
    }
    PRESETS.mkdir(parents=True, exist_ok=True)
    out_fp = PRESETS / "ltx23_aio_feature_presets.json"
    out_fp.write_text(json.dumps(fp, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", out_fp)

    # Agent guide MD
    lines = [
        "# LTX 2.3 All-In-One v44 — Agent feature selection",
        "",
        "Source UI: `workflows/human/ltx23AllInOneWorkflowForRTX_v44.json`",
        "",
        "This AIO is **not** a single linear graph. Agents pick a **Select options** combination",
        "(via `[[P:]]` mute table) then inject ports. Implementation: `ltx_aio_mode_select` + `ltx_aio_workflow_runner`.",
        "",
        "## How to choose",
        "",
        "1. Decide mode: T2V / I2V / FLF / FML / V2V (± Audio)",
        "2. Call `generate_s2v` with matching `--backend ltx23_aio_*` **or** `--ltx-mode <mode>`",
        "3. Pass required media: `-i` / `--last` / `--mid` / `-a` / `--video`",
        "4. Do **not** build mini graphs; do **not** rename `[[P:]]` tags",
        "",
        "List features:",
        "```bash",
        "python scripts/run_ltx_aio_features.py --list",
        "```",
        "",
        "## Select options → agent mode",
        "",
        "| Feature | Mode | Select options (ON) | Backend | Required inputs |",
        "|---------|------|---------------------|---------|-----------------|",
    ]
    for f in features:
        opts = ", ".join(f"`{p}`" for p in f["select_options"])
        req = ", ".join(f["required_inputs"])
        lines.append(
            f"| {f['label']} | `{f['mode']}` | {opts} | `{f['backend']}` | {req} |"
        )
    lines += [
        "",
        "## CLI examples",
        "",
        "```bash",
        "# Pure I2V (no audio)",
        "python scripts/generate_s2v.py --backend ltx23_aio_i2v -i first.png --prompt '...'",
        "",
        "# Image + Audio SI2V (default s2v)",
        "python scripts/generate_s2v.py --backend ltx23_aio -i first.png -a drive.wav --prompt '...'",
        "",
        "# First/Last frame",
        "python scripts/generate_s2v.py --backend ltx23_aio_flf -i first.png --last last.png --prompt '...'",
        "",
        "# Explicit mode flag (same runner)",
        "python scripts/generate_s2v.py --backend ltx23_aio --ltx-mode flf_audio -i f.png --last l.png -a a.wav",
        "```",
        "",
        "## [[P:]] port inventory (scanned)",
        "",
    ]
    for tag, cnt in p_tags.most_common():
        lines.append(f"- `{tag}` — {cnt} tagged nodes")
    lines += [
        "",
        "## Secondary switches (scanned)",
        "",
        "These are additional Comfy switch/orchestrator nodes. Mode path uses **[[P:]] mute** as SSOT;",
        "secondary switches are applied by the expanded AIO graph / runner inject where needed.",
        "",
    ]
    for s in secondary[:40]:
        lines.append(
            f"- id `{s['id']}` `{s['type']}` — {s.get('title') or '(no title)'} ({s['layer']})"
        )
    lines += [
        "",
        "## Machine-readable",
        "",
        "- `workflows/human/LTX23_AIO_v44_CAPABILITIES.json`",
        "- `workflows/agent/presets/ltx23_aio_feature_presets.json`",
        "- `workflows/agent/ltx23_aio.manifest.json`",
        "",
        "Rescan: `python scripts/_analyze_ltx23_aio_features.py`",
        "",
    ]
    out_md = HUMAN / "LTX23_AIO_v44_AGENT_GUIDE.md"
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", out_md)
    print("p_tags", dict(p_tags))
    print("selectors", len(selectors), "switches", len(switches))
    print("features", len(features))


if __name__ == "__main__":
    main()
