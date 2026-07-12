#!/usr/bin/env python3
"""
Generate dialogue/VO for a shot with Qwen3-TTS and bind as SI2V driving.

Typical story dialogue cut:
  episode_tts → audio/dialogue/<shot>.mp3
            → prepare_driving (center_voicey)
            → motion_driver=si2v + audio_refs.driving
            → episode_s2v / generate_s2v (LTX or InfiniteTalk)

Usage:
  python scripts/episode_tts.py -e sonagi_cafe_smoke_v1 -s S02 \\
    --text "비가 오네… 창밖이 흐려." --mode custom --speaker Sohee \\
    --instruct "soft sad Korean young woman, quiet intimate" --bind-si2v
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import sys

from generate_qwen3_tts import CUSTOM_SPEAKERS, LANGUAGES, generate_qwen3_tts
from lib.ffmpeg_util import DRIVING_PREP_MODES, prepare_driving_audio
from lib.story_package import StoryPackage, validate_episode_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11
EXIT_FAIL = 30


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Shot dialogue TTS + optional SI2V bind")
    p.add_argument("--episode", "-e", required=True)
    p.add_argument("--shot", "-s", required=True)
    p.add_argument("--text", "-t", default=None, help="Override shot.dialogue / vo")
    p.add_argument(
        "--role",
        default="dialogue",
        choices=["dialogue", "vo", "vocal"],
        help="Stem role (default dialogue)",
    )
    p.add_argument("--mode", "-m", choices=["custom", "design", "clone"], default="custom")
    p.add_argument("--speaker", default="Sohee", help=f"custom speakers: {CUSTOM_SPEAKERS}")
    p.add_argument("--language", default="Korean", choices=list(LANGUAGES))
    p.add_argument("--instruct", default="", help="Emotion / voice design instruct")
    p.add_argument("--ref-audio", default=None, help="Clone sample (or use --voice-id)")
    p.add_argument("--ref-text", default="", help="Transcript of ref audio")
    p.add_argument(
        "--voice-id",
        default=None,
        help="Registered voices/<id> profile (clone)",
    )
    p.add_argument("--model-size", default="1.7B", choices=["0.6B", "1.7B"])
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--temperature", type=float, default=0.9)
    p.add_argument("--top-p", type=float, default=0.8)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument(
        "--bind-si2v",
        action="store_true",
        help="Prepare driving + set motion_driver=si2v + audio_refs.driving",
    )
    p.add_argument(
        "--prepare-mode",
        default="center_voicey",
        choices=list(DRIVING_PREP_MODES),
    )
    p.add_argument("--no-prepare", action="store_true", help="Skip driving prep")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] bad episode id", file=sys.stderr)
        return EXIT_USAGE
    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print(f"[ERROR] episode missing {args.episode}", file=sys.stderr)
        return EXIT_MISSING
    try:
        shot = story.get_shot(args.shot)
    except KeyError:
        print(f"[ERROR] shot missing {args.shot}", file=sys.stderr)
        return EXIT_USAGE

    text = (args.text or shot.get("dialogue") or shot.get("vo") or "").strip()
    if not text:
        print(
            "[ERROR] no text — pass --text or set shot.dialogue / shot.vo",
            file=sys.stderr,
        )
        return EXIT_USAGE

    stem_dir = "dialogue" if args.role == "dialogue" else ("vo" if args.role == "vo" else "music")
    out_rel = f"audio/{stem_dir}/{args.shot}_qwen3tts.mp3"
    out_path = story.path(*out_rel.split("/"))

    print(
        f"episode_tts episode={args.episode} shot={args.shot} "
        f"mode={args.mode} role={args.role}"
    )
    print(f"  text={text[:100]!r}")
    print(f"  out={out_path}")

    if args.dry_run:
        print("[dry-run] skip generate")
        return EXIT_OK

    r = generate_qwen3_tts(
        text,
        mode=args.mode,
        speaker=args.speaker,
        language=args.language,
        instruct=args.instruct,
        ref_audio=args.ref_audio,
        ref_text=args.ref_text,
        voice_id=args.voice_id,
        model_size=args.model_size,
        output_filename=out_path,
        seed=args.seed,
        temperature=args.temperature,
        top_p=args.top_p,
        timeout_sec=args.timeout,
        meta_out=story.path("meta", f"{args.shot}_tts.json"),
    )
    if not r.get("ok"):
        print(f"[ERROR] TTS {r.get('error')}: {r.get('message')}", file=sys.stderr)
        return EXIT_FAIL

    fields: dict = {
        args.role if args.role in ("dialogue", "vo") else "dialogue": text,
    }
    # store raw tts path in audio_refs
    audio_refs = dict(shot.get("audio_refs") or {})
    audio_refs["tts"] = {
        "path": out_rel.replace("\\", "/"),
        "mode": args.mode,
        "speaker": args.speaker if args.mode == "custom" else None,
        "instruct": args.instruct or None,
        "engine": "qwen3_tts",
    }

    driving_rel = None
    if args.bind_si2v:
        drive_src = out_path
        if not args.no_prepare:
            drive_out = story.path(
                "audio", "exports", "s2v_drive", f"{args.shot}_qwen3tts_{args.prepare_mode}.wav"
            )
            prep = prepare_driving_audio(
                drive_src,
                drive_out,
                mode=args.prepare_mode,
            )
            if not prep.get("ok"):
                print(
                    f"[WARN] prepare_driving failed: {prep.get('error')} {prep.get('message')}; "
                    f"using raw tts",
                    file=sys.stderr,
                )
            else:
                drive_src = drive_out
                driving_rel = os.path.relpath(drive_out, story.root).replace("\\", "/")
        if driving_rel is None:
            driving_rel = out_rel.replace("\\", "/")
        audio_refs["driving"] = {
            "path": driving_rel,
            "role": args.role,
            "source": "qwen3_tts",
            "prepare_mode": None if args.no_prepare else args.prepare_mode,
        }
        fields["motion_driver"] = "si2v"
        if not (shot.get("motion_prompt") or "").strip():
            fields["motion_prompt"] = (
                "character speaks the dialogue, natural lip sync, subtle head motion, "
                "keep identity and wardrobe fixed"
            )
        print(f"  bound SI2V driving={driving_rel}")

    fields["audio_refs"] = audio_refs
    story.update_shot(args.shot, **fields)

    print(f"OK tts={out_path}")
    if args.bind_si2v:
        print(
            f"  next: python scripts/episode_s2v.py -e {args.episode} "
            f"--shots {args.shot}"
        )
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
