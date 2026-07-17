#!/usr/bin/env python3
"""
Verify LTX AIO v44:
  1) All Select-options modes mute correctly
  2) Clip length / longer_edge / aspect / fps inject into API nodes
  3) Optional live smokes for param + mode paths

Usage:
  python scripts/_tmp_ltx_aio_verify_params_modes.py           # dry graph checks only
  python scripts/_tmp_ltx_aio_verify_params_modes.py --live    # also run short I2V smokes
"""
from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import os
import sys
import wave
from pathlib import Path

from lib.ltx_aio_mode_select import (
    AIO_MODE_PORTS,
    apply_aio_mode_to_ui_workflow,
    list_features,
    parse_p_tags,
)
from lib.ltx_aio_workflow_runner import build_aio_switched_api

OUT_DIR = Path(r"F:\generated_images\ltx_aio_verify")
SRC_IMG_CANDS = [
    r"F:\generated_images\qwen_multiangle_view_test\body_front.png",
    r"F:\ComfyUI_workflows\agent_custom\characters\sonagi_heroine_v1\approved\master_front.png",
    r"F:\ComfyUI_workflows\agent_custom\stories\sonagi_mv_v3\keyframes\S01.png",
]


def _find_src() -> str:
    for c in SRC_IMG_CANDS:
        if os.path.isfile(c):
            return c
    raise FileNotFoundError("no source image")


def _count_p_modes(ui: dict) -> dict[str, dict[str, int]]:
    """Per [[P:tag]] count of ALWAYS(0) / NEVER(2) across root+subgraphs."""
    from collections import defaultdict

    stats: dict[str, dict[str, int]] = defaultdict(lambda: {"always": 0, "never": 0, "other": 0})

    def walk(nodes):
        for n in nodes or []:
            title = n.get("title") or ""
            tags = parse_p_tags(title)
            if not tags:
                continue
            mode = n.get("mode", 0)
            key = "always" if mode == 0 else ("never" if mode == 2 else "other")
            for t in tags:
                stats[t][key] += 1

    walk(ui.get("nodes"))
    for sg in (ui.get("definitions") or {}).get("subgraphs") or []:
        walk(sg.get("nodes"))
    return {k: dict(v) for k, v in stats.items()}


def verify_modes() -> list[dict]:
    results = []
    for feat in list_features():
        mode = feat["mode"]
        active = set(feat["select_options"])
        inactive = set(AIO_MODE_PORTS.keys())  # unused
        from lib.ltx_aio_workflow_runner import _load_ui

        ui = apply_aio_mode_to_ui_workflow(_load_ui(), mode)
        stats = _count_p_modes(ui)
        ok = True
        problems = []
        for port, st in stats.items():
            if port in active:
                if st["always"] < 1:
                    ok = False
                    problems.append(f"active port {port!r} has always=0")
            else:
                # inactive ports should not have ALWAYS nodes (or only 0 always)
                if st["always"] > 0:
                    ok = False
                    problems.append(
                        f"inactive port {port!r} still ALWAYS={st['always']}"
                    )
        results.append(
            {
                "check": "mode_mute",
                "mode": mode,
                "ok": ok,
                "active": sorted(active),
                "p_stats": stats,
                "problems": problems,
                "mode_changes": len(ui.get("_agent_aio_mode_changes") or []),
            }
        )
        status = "OK" if ok else "FAIL"
        print(f"[{status}] mode={mode} active={sorted(active)} problems={problems}")
    return results


def verify_param_inject() -> list[dict]:
    cases = [
        {
            "name": "clip3_edge768_9x16",
            "clip_length_sec": 3,
            "longer_edge": 768,
            "aspect": "9:16",
            "fps": 24,
        },
        {
            "name": "clip5_edge1024_16x9",
            "clip_length_sec": 5,
            "longer_edge": 1024,
            "aspect": "16:9",
            "fps": 24,
        },
        {
            "name": "clip2_edge640_9x16",
            "clip_length_sec": 2,
            "longer_edge": 640,
            "aspect": "9:16",
            "fps": 24,
        },
        {
            "name": "clip8_edge960_1x1",
            "clip_length_sec": 8,
            "longer_edge": 960,
            "aspect": "1:1",
            "fps": 24,
        },
    ]
    results = []
    for c in cases:
        api, meta = build_aio_switched_api(
            mode="i2v",
            image_name="dummy.png",
            prompt="param inject test",
            negative="text",
            seed=1,
            clip_length_sec=c["clip_length_sec"],
            longer_edge=c["longer_edge"],
            aspect=c["aspect"],
            fps=c["fps"],
        )
        n196 = (api.get("196") or {}).get("inputs") or {}
        n1688 = (api.get("1688") or {}).get("inputs") or {}
        n1774 = (api.get("1774") or {}).get("inputs") or {}
        n869 = (api.get("869") or {}).get("inputs") or {}
        n149 = (api.get("149") or {}).get("inputs") or {}

        expect_clip = max(1, min(20, int(c["clip_length_sec"])))
        expect_edge = max(512, min(2048, int(round(c["longer_edge"] / 64.0) * 64)))
        # runner snaps edge to 64 multiples and min 512
        got_clip = n196.get("Xi")
        got_edge = n1688.get("Xi")
        got_aspect = n1774.get("combo")
        got_fps = n869.get("value")
        got_img = n149.get("image")

        ok = (
            got_clip == expect_clip
            and got_edge == expect_edge
            and got_aspect == c["aspect"]
            and got_fps == c["fps"]
            and got_img == "dummy.png"
            and meta.get("clip_length_sec") == expect_clip
            and meta.get("longer_edge") == expect_edge
            and meta.get("aspect") == c["aspect"]
        )
        row = {
            "check": "param_inject",
            "name": c["name"],
            "ok": ok,
            "expect": {
                "clip": expect_clip,
                "edge": expect_edge,
                "aspect": c["aspect"],
                "fps": c["fps"],
            },
            "got": {
                "clip": got_clip,
                "edge": got_edge,
                "aspect": got_aspect,
                "fps": got_fps,
                "image": got_img,
                "meta": {
                    "clip": meta.get("clip_length_sec"),
                    "edge": meta.get("longer_edge"),
                    "aspect": meta.get("aspect"),
                },
            },
            "nodes_present": {
                "196": "196" in api,
                "1688": "1688" in api,
                "1774": "1774" in api,
                "869": "869" in api,
                "149": "149" in api,
            },
        }
        results.append(row)
        print(
            f"[{'OK' if ok else 'FAIL'}] inject {c['name']} "
            f"clip={got_clip}/{expect_clip} edge={got_edge}/{expect_edge} "
            f"aspect={got_aspect!r}/{c['aspect']!r} fps={got_fps}"
        )
    return results


def verify_mode_media_ports() -> list[dict]:
    """Ensure load ports present in API for each mode's media."""
    results = []
    cases = [
        ("i2v", {"149": "image"}, {"image_name": "a.png"}),
        ("i2v_audio", {"149": "image", "412": "audio"}, {"image_name": "a.png", "audio_name": "a.wav"}),
        ("flf", {"149": "image", "786": "image"}, {"image_name": "a.png", "last_image_name": "b.png"}),
        (
            "fml",
            {"149": "image", "786": "image", "1705": "image"},
            {"image_name": "a.png", "last_image_name": "b.png", "mid_image_name": "c.png"},
        ),
        ("v2v", {"787": "video"}, {"image_name": "a.png", "video_name": "v.mp4"}),
        ("t2v", {}, {"prompt": "hello"}),
    ]
    for mode, expect_nodes, kwargs in cases:
        api, meta = build_aio_switched_api(mode=mode, seed=1, **kwargs)
        problems = []
        for nid, key in expect_nodes.items():
            if nid not in api:
                problems.append(f"missing node {nid}")
            else:
                val = (api[nid].get("inputs") or {}).get(key)
                if not val:
                    problems.append(f"node {nid}.{key} empty")
        ok = not problems
        results.append(
            {
                "check": "mode_media_ports",
                "mode": mode,
                "ok": ok,
                "problems": problems,
                "active_ports": meta.get("active_ports"),
            }
        )
        print(f"[{'OK' if ok else 'FAIL'}] media mode={mode} {problems or 'ports set'}")
    return results


def _write_silence_wav(path: str, seconds: float = 2.0, sr: int = 24000) -> str:
    n = int(sr * seconds)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"\x00\x00" * n)
    return path


def live_smokes(src: str) -> list[dict]:
    from generate_s2v import generate_s2v

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    # 1) Param matrix — short pure I2V
    param_jobs = [
        {
            "name": "i2v_clip2_544x960",
            "backend": "ltx23_aio_i2v",
            "width": 544,
            "height": 960,
            "frames": 25,  # ~1s@24; runner may use clip length from frames/fps
            "fps": 24,
            "prompt": "subtle blink, gentle head motion, locked identity",
        },
        {
            "name": "i2v_clip_edge768_16x9",
            "backend": "ltx23_aio_i2v",
            "width": 1024,
            "height": 576,
            "frames": 25,
            "fps": 24,
            "prompt": "subtle motion landscape framing, locked identity",
        },
    ]

    for job in param_jobs:
        out = str(OUT_DIR / f"{job['name']}.mp4")
        print(f"\n=== LIVE {job['name']} ===")
        r = generate_s2v(
            input_image_path=src,
            audio_path=None,
            output_filename=out,
            prompt=job["prompt"],
            negative="animation, cartoon, text, morphing face",
            width=job["width"],
            height=job["height"],
            num_frames=job["frames"],
            fps=job["fps"],
            seed=77,
            backend=job["backend"],
            timeout_sec=1800,
        )
        ok = bool(r.get("ok")) and os.path.isfile(out) and os.path.getsize(out) > 1000
        results.append(
            {
                "check": "live",
                "name": job["name"],
                "ok": ok,
                "error": r.get("error"),
                "message": (r.get("message") or "")[:300],
                "path": out if ok else None,
                "bytes": os.path.getsize(out) if ok else 0,
                "meta_runner": (r.get("meta") or {}).get("ltx_runner")
                or (r.get("meta") or {}).get("runner"),
            }
        )
        print(f"[{'OK' if ok else 'FAIL'}] {job['name']} err={r.get('error')} path={out if ok else None}")

    # 2) FLF mode (first + last = same + side as last for angle change)
    last = (
        r"F:\generated_images\qwen_multiangle_view_test\body_side.png"
        if os.path.isfile(r"F:\generated_images\qwen_multiangle_view_test\body_side.png")
        else src
    )
    out = str(OUT_DIR / "flf_first_last.mp4")
    print("\n=== LIVE flf ===")
    r = generate_s2v(
        input_image_path=src,
        audio_path=None,
        output_filename=out,
        prompt="camera arcs gently, keep identity fixed",
        negative="text, morphing",
        width=544,
        height=960,
        num_frames=25,
        fps=24,
        seed=78,
        backend="ltx23_aio_flf",
        last_image_path=last,
        timeout_sec=1800,
    )
    ok = bool(r.get("ok")) and os.path.isfile(out) and os.path.getsize(out) > 1000
    results.append(
        {
            "check": "live",
            "name": "flf",
            "ok": ok,
            "error": r.get("error"),
            "message": (r.get("message") or "")[:300],
            "path": out if ok else None,
            "bytes": os.path.getsize(out) if ok else 0,
        }
    )
    print(f"[{'OK' if ok else 'FAIL'}] flf err={r.get('error')}")

    # 3) I2V + audio (silence 2s)
    wav = str(OUT_DIR / "silence_2s.wav")
    _write_silence_wav(wav, 2.0)
    out = str(OUT_DIR / "i2v_audio_silence.mp4")
    print("\n=== LIVE i2v_audio ===")
    r = generate_s2v(
        input_image_path=src,
        audio_path=wav,
        output_filename=out,
        prompt="person still, subtle motion, locked identity",
        negative="text, morphing",
        width=544,
        height=960,
        fps=24,
        seed=79,
        backend="ltx23_aio",
        timeout_sec=1800,
    )
    ok = bool(r.get("ok")) and os.path.isfile(out) and os.path.getsize(out) > 1000
    results.append(
        {
            "check": "live",
            "name": "i2v_audio",
            "ok": ok,
            "error": r.get("error"),
            "message": (r.get("message") or "")[:300],
            "path": out if ok else None,
            "bytes": os.path.getsize(out) if ok else 0,
        }
    )
    print(f"[{'OK' if ok else 'FAIL'}] i2v_audio err={r.get('error')}")

    # 4) T2V short (no image required in mode but generate_s2v may still want image)
    out = str(OUT_DIR / "t2v_smoke.mp4")
    print("\n=== LIVE t2v ===")
    r = generate_s2v(
        input_image_path=src,  # may be ignored for pure t2v
        audio_path=None,
        output_filename=out,
        prompt="cinematic portrait of a young Korean woman, soft light, subtle motion",
        negative="text, cartoon",
        width=544,
        height=960,
        num_frames=25,
        fps=24,
        seed=80,
        backend="ltx23_aio_t2v",
        timeout_sec=1800,
    )
    ok = bool(r.get("ok")) and os.path.isfile(out) and os.path.getsize(out) > 1000
    results.append(
        {
            "check": "live",
            "name": "t2v",
            "ok": ok,
            "error": r.get("error"),
            "message": (r.get("message") or "")[:300],
            "path": out if ok else None,
            "bytes": os.path.getsize(out) if ok else 0,
        }
    )
    print(f"[{'OK' if ok else 'FAIL'}] t2v err={r.get('error')}")

    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="Run live Comfy video smokes")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []

    print("=== 1) MODE MUTE (Select options) ===")
    all_rows.extend(verify_modes())

    print("\n=== 2) PARAM INJECT (clip / edge / aspect / fps) ===")
    all_rows.extend(verify_param_inject())

    print("\n=== 3) MODE MEDIA PORTS ===")
    all_rows.extend(verify_mode_media_ports())

    if args.live:
        print("\n=== 4) LIVE SMOKES ===")
        src = _find_src()
        print("src", src)
        all_rows.extend(live_smokes(src))

    summary = {
        "total": len(all_rows),
        "ok": sum(1 for r in all_rows if r.get("ok")),
        "fail": sum(1 for r in all_rows if not r.get("ok")),
        "rows": all_rows,
    }
    out = OUT_DIR / "_verify_summary.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n=== SUMMARY ===")
    print(f"ok={summary['ok']}/{summary['total']} fail={summary['fail']}")
    print("wrote", out)
    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
