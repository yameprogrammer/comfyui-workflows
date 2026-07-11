#!/usr/bin/env python3
"""Report episode production_mode / mix_policy / stem readiness."""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.audio_package import (
    audio_readiness,
    ensure_audio_dirs,
    resolve_default_motion_driver,
    resolve_mix_policy,
    shot_motion_driver,
    normalize_production_mode,
)
from lib.story_package import StoryPackage, validate_episode_id

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING = 11


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Episode audio / motion-driver status")
    parser.add_argument("--episode", "-e", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not validate_episode_id(args.episode):
        print("[ERROR] code=2 invalid episode id", file=sys.stderr)
        return EXIT_USAGE

    try:
        story = StoryPackage.load(args.episode)
    except FileNotFoundError:
        print("[ERROR] code=11 episode missing", file=sys.stderr)
        return EXIT_MISSING

    ensure_audio_dirs(story.root)
    ready = audio_readiness(story.root, story.doc)
    mode = normalize_production_mode(story.doc.get("production_mode"))
    policy = resolve_mix_policy(story.doc)
    default_driver = resolve_default_motion_driver(story.doc)

    drivers = {}
    for s in story.shots():
        d = shot_motion_driver(s, story.doc)
        drivers[d] = drivers.get(d, 0) + 1

    report = {
        "episode_id": args.episode,
        "production_mode": mode,
        "mix_policy": policy,
        "default_motion_driver": default_driver,
        "motion_driver_counts": drivers,
        "readiness": ready,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return EXIT_OK

    print(f"episode={args.episode}")
    print(f"production_mode={mode}  mix_policy={policy}")
    print(f"default_motion_driver={default_driver}")
    print(f"motion_drivers={drivers}")
    st = ready.get("stems") or {}
    print(
        f"stems master={st.get('master') or '-'} bgm={st.get('bgm') or '-'} "
        f"dialogue={st.get('dialogue_n')} vo={st.get('vo_n')} sfx={st.get('sfx_n')}"
    )
    print(f"ready={ready.get('ready')} missing={ready.get('missing') or []}")
    if ready.get("si2v_missing"):
        print(f"si2v need driving audio: {ready['si2v_missing']}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
