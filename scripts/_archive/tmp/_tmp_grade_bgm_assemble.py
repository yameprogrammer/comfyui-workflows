#!/usr/bin/env python3
"""One-off: per-shot color grade + louder BGM hardcut assemble for cafe_gomin_ep01."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path("stories/cafe_gomin_ep01")
WORK = ROOT / "clips" / "work"
OUT = ROOT / "exports" / "final" / "cafe_gomin_ep01_final.mp4"
BGM = ROOT / "audio" / "music" / "bgm_cafe_soft.mp3"
W, H, FPS = 544, 960, 24
BGM_VOL = 0.42

ORDER = [
    ("S01", False),
    ("S02", True),
    ("S03", True),
    ("S04", True),
    ("S05", True),
    ("S06", False),
    ("S07", True),
    ("S08", True),
    ("S09", False),
]


def run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:] if r.stderr else "ffmpeg fail")


def dur(p: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(p),
        ],
        capture_output=True,
        text=True,
    )
    return float(r.stdout.strip())


def has_audio(p: Path) -> bool:
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            str(p),
        ],
        capture_output=True,
        text=True,
    )
    return "audio" in r.stdout


def clip_path(sid: str, s2v: bool) -> Path:
    if s2v:
        p = WORK / f"{sid}_s2v.mp4"
        if p.is_file():
            return p
    p = WORK / f"{sid}.mp4"
    if p.is_file():
        return p
    raise FileNotFoundError(sid)


def vf_for(i: int) -> str:
    base = (
        f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setsar=1"
    )
    if i < 3:
        grade = "eq=brightness=0.01:contrast=1.02:saturation=1.02"
    else:
        # warmer, less green, slight lift (S04+)
        grade = (
            "eq=gamma_r=1.12:gamma_g=0.90:gamma_b=1.02:"
            "brightness=0.045:contrast=1.03:saturation=1.04"
        )
    return f"{base},{grade}"


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="grade_asm_"))
    print("tmp", tmp)
    baked: list[Path] = []
    offsets = []
    t = 0.0
    for i, (sid, s2v) in enumerate(ORDER):
        src = clip_path(sid, s2v)
        dst = tmp / f"{i:02d}_{sid}.mp4"
        vf = vf_for(i)
        if has_audio(src):
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(src),
                "-vf",
                vf,
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-preset",
                "fast",
                "-crf",
                "18",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-shortest",
                str(dst),
            ]
        else:
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(src),
                "-f",
                "lavfi",
                "-i",
                "anullsrc=r=48000:cl=stereo",
                "-vf",
                vf,
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-preset",
                "fast",
                "-crf",
                "18",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                str(dst),
            ]
        run(cmd)
        d = dur(dst)
        offsets.append({"shot": sid, "start": t, "dur": d, "grade": "late" if i >= 3 else "early"})
        t += d
        baked.append(dst)
        print("baked", sid, round(d, 3), offsets[-1]["grade"])

    lst = tmp / "list.txt"
    with open(lst, "w", encoding="utf-8") as f:
        for p in baked:
            ap = p.resolve().as_posix().replace("'", r"'\''")
            f.write(f"file '{ap}'\n")
    body = tmp / "body.mp4"
    try:
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(body)])
    except RuntimeError:
        run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(lst),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(body),
            ]
        )
    tot = dur(body)
    print("body", round(tot, 3))

    bgm_loop = tmp / "bgm.wav"
    run(
        [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(BGM),
            "-t",
            f"{tot:.3f}",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(bgm_loop),
        ]
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fc = (
        f"[0:a]aformat=sample_fmts=fltp:channel_layouts=stereo,volume=1.0[va];"
        f"[1:a]aformat=sample_fmts=fltp:channel_layouts=stereo,volume={BGM_VOL}[ba];"
        f"[va][ba]amix=inputs=2:duration=first:dropout_transition=2:normalize=0,"
        f"alimiter=limit=0.95[aout]"
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(body),
            "-i",
            str(bgm_loop),
            "-filter_complex",
            fc,
            "-map",
            "0:v",
            "-map",
            "[aout]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            str(OUT),
        ]
    )
    print("FINAL", OUT, "dur", round(dur(OUT), 3), "bgm_vol", BGM_VOL)

    for label, ss, td in [("s01_bgm_region", 0, 3.5), ("s05_region", 18, 3)]:
        r = subprocess.run(
            [
                "ffmpeg",
                "-ss",
                str(ss),
                "-t",
                str(td),
                "-i",
                str(OUT),
                "-af",
                "volumedetect",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
        )
        for line in r.stderr.splitlines():
            if "mean_volume" in line or "max_volume" in line:
                print(label, line.strip())

    meta = {
        "mode": "assemble_grade_bgm",
        "grade": "S01-S03 mild; S04+ warm up / green down",
        "bgm_volume": BGM_VOL,
        "bgm_source": str(BGM),
        "duration": dur(OUT),
        "offsets": offsets,
    }
    meta_path = ROOT / "meta" / "cafe_gomin_ep01_assemble_grade.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("meta", meta_path)


if __name__ == "__main__":
    main()
