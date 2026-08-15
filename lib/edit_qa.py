"""Master QA pack: stills at hook/mid/end + duration + peak."""

from __future__ import annotations

import json
import os
from typing import Any

from lib.comfy_client import fail_result, ok_result, utc_now_iso
from lib.ffmpeg_util import probe_duration, run_ffmpeg


def edit_qa_pack(video_path: str, out_dir: str) -> dict[str, Any]:
    if not os.path.isfile(video_path):
        return fail_result(error="SOURCE_MISSING", message=video_path)
    dur = probe_duration(video_path) or 0.0
    os.makedirs(out_dir, exist_ok=True)
    stamps = {
        "t003": 0.3,
        "hook": min(1.5, max(0.2, dur * 0.12)),
        "mid": max(0.2, dur * 0.5),
        "end": max(0.1, dur - 0.25),
    }
    frames = []
    for name, t in stamps.items():
        if t >= dur:
            t = max(0.0, dur - 0.05)
        dest = os.path.join(out_dir, f"{name}.png")
        r = run_ffmpeg(
            [
                "-ss",
                f"{t:.3f}",
                "-i",
                os.path.abspath(video_path),
                "-frames:v",
                "1",
                dest,
            ],
            timeout_sec=60,
        )
        if r.get("ok") and os.path.isfile(dest):
            frames.append({"name": name, "t": t, "path": os.path.abspath(dest)})
    meta = {
        "source": os.path.abspath(video_path),
        "duration_sec": dur,
        "frames": frames,
        "created_at": utc_now_iso(),
    }
    meta_path = os.path.join(out_dir, "qa_pack.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return ok_result(tool="edit_qa_pack", path=os.path.abspath(out_dir), meta_path=os.path.abspath(meta_path), duration=dur, frames=frames)


def edit_qa_record(
    pack_dir: str,
    *,
    verdict: str,
    notes: str = "",
) -> dict[str, Any]:
    v = verdict.strip().lower()
    if v not in {"pass", "fail"}:
        return fail_result(error="BAD_VERDICT", message=verdict)
    rec = {
        "verdict": v,
        "notes": notes,
        "pack": os.path.abspath(pack_dir),
        "created_at": utc_now_iso(),
    }
    path = os.path.join(pack_dir, "qa_record.json")
    os.makedirs(pack_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return ok_result(tool="edit_qa_record", path=os.path.abspath(path), verdict=v)
