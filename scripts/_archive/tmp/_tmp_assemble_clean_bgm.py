#!/usr/bin/env python3
"""Hardcut assemble one-take clips, NO color grade, real BGM under dialogue."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path("stories/cafe_gomin_ep01")
WORK = ROOT / "clips" / "work"
OUT = ROOT / "exports" / "final" / "cafe_gomin_ep01_final.mp4"
BGM = ROOT / "audio" / "music" / "bgm_cafe_suno.mp3"
if not BGM.is_file():
    BGM = ROOT / "audio" / "music" / "bgm_cafe_ambient_synth.mp3"
W, H, FPS = 544, 960, 24
# Dialogue-forward mix: voice loud and clear, BGM present but under speech.
VOICE_VOL = 2.15
BGM_VOL = 0.78
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
        raise RuntimeError((r.stderr or r.stdout or "")[-900:])


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
    if not p.is_file():
        raise FileNotFoundError(sid)
    return p


def main() -> None:
    if not BGM.is_file():
        raise SystemExit(f"BGM missing: {BGM}")

    tmp = Path(tempfile.mkdtemp(prefix="asm_clean_"))
    print("tmp", tmp, "bgm", BGM)
    baked: list[Path] = []
    vf = (
        f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setsar=1"
    )
    for i, (sid, s2v) in enumerate(ORDER):
        src = clip_path(sid, s2v)
        dst = tmp / f"{i:02d}_{sid}.mp4"
        if has_audio(src):
            run(
                [
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
            )
        else:
            run(
                [
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
            )
        print("baked", sid, round(dur(dst), 3))
        baked.append(dst)

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
                str(body),
            ]
        )
    tot = dur(body)
    print("body", round(tot, 3))

    bgm_wav = tmp / "bgm.wav"
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
            str(bgm_wav),
        ]
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fc = (
        f"[0:a]aformat=sample_fmts=fltp:channel_layouts=stereo,"
        f"volume={VOICE_VOL},acompressor=threshold=-18dB:ratio=2.5:attack=5:release=80:"
        f"makeup=2[va];"
        f"[1:a]aformat=sample_fmts=fltp:channel_layouts=stereo,volume={BGM_VOL}[ba];"
        f"[va][ba]amix=inputs=2:duration=first:dropout_transition=2:normalize=0,"
        f"alimiter=limit=0.95:attack=5:release=50[aout]"
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(body),
            "-i",
            str(bgm_wav),
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
            str(OUT),
        ]
    )
    print(
        "FINAL",
        OUT,
        "dur",
        round(dur(OUT), 3),
        "bgm",
        BGM.name,
        "voice",
        VOICE_VOL,
        "bgm_vol",
        BGM_VOL,
    )

    for label, ss, t in [("s01_only", 0, 3.8), ("with_dialogue", 18, 3)]:
        r = subprocess.run(
            [
                "ffmpeg",
                "-ss",
                str(ss),
                "-t",
                str(t),
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

    # export short listen clips
    listen = ROOT / "exports" / "final" / "_listen_opening_4s.mp3"
    run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            "0",
            "-t",
            "4",
            "-i",
            str(OUT),
            "-vn",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "3",
            str(listen),
        ]
    )
    print("listen", listen)


if __name__ == "__main__":
    import subprocess

    main()
