#!/usr/bin/env python3
"""
YouTube reference ingest (no Comfy).

  python scripts/youtube_ingest.py "https://www.youtube.com/watch?v=..." -o dumps/yt_demo
  python scripts/youtube_ingest.py URL --whisper --highlights
  python scripts/youtube_ingest.py URL --download-media --cut --max-clips 5

Outputs package:
  meta.json · transcript.json · transcript.srt · summary.md · highlights.json
  SOURCE.md · (optional) source.mp4 · clips/*.mp4

Policy: internal reference / analysis only — not for re-uploading source media.
Docs: docs/youtube_ref_ingest_research.md
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import json
import sys

from lib.youtube_ingest import (
    SOURCE_POLICY,
    cut_highlights_from_package,
    extract_video_id,
    ingest_youtube,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Ingest a YouTube URL into a reference package "
            "(meta, captions/transcript, summary, optional highlights/clips)."
        )
    )
    p.add_argument("url", nargs="?", help="YouTube URL or 11-char video id")
    p.add_argument(
        "-o",
        "--out",
        default=None,
        help="Output package directory (default dumps/yt_ref_<id>_<ts>/)",
    )
    p.add_argument(
        "--lang",
        default="ko,en",
        help="Caption language priority, comma-separated (default ko,en)",
    )
    p.add_argument(
        "--whisper",
        action="store_true",
        help="If no captions, download audio and run Whisper (if installed)",
    )
    p.add_argument(
        "--whisper-model",
        default="base",
        help="Whisper model size (default base)",
    )
    p.add_argument(
        "--download-media",
        action="store_true",
        help="Download source video (mp4) into package",
    )
    p.add_argument(
        "--max-height",
        type=int,
        default=720,
        help="Max video height when downloading (default 720)",
    )
    p.add_argument(
        "--highlights",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write highlights.json (default on)",
    )
    p.add_argument(
        "--max-clips",
        type=int,
        default=5,
        help="Max highlight candidates / cuts (default 5)",
    )
    p.add_argument(
        "--cut",
        action="store_true",
        help="Download media (if needed) and ffmpeg-cut highlight clips",
    )
    p.add_argument(
        "--reencode",
        action="store_true",
        help="Re-encode clips instead of stream copy",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable result JSON",
    )
    # Re-cut from existing package
    p.add_argument(
        "--from-package",
        default=None,
        help="Existing package dir: rebuild/cut highlights only",
    )
    p.add_argument(
        "--rebuild-highlights",
        action="store_true",
        help="With --from-package: recompute highlight windows",
    )

    args = p.parse_args(argv)

    if args.from_package:
        r = cut_highlights_from_package(
            args.from_package,
            max_clips=args.max_clips,
            reencode=args.reencode,
            rebuild_highlights=args.rebuild_highlights,
        )
        if args.json:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        else:
            if not r.get("ok"):
                print(f"FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
                return 1
            print(f"OK package={r.get('package_dir')}")
            print(f"  media={r.get('media')}")
            print(f"  clips={len(r.get('clips') or [])}")
            for c in r.get("clips") or []:
                print(f"    {c}")
        return 0 if r.get("ok") else 1

    if not args.url:
        p.print_help()
        print("\nExamples:")
        print('  python scripts/youtube_ingest.py "https://youtu.be/VIDEO_ID" -o dumps/yt_demo')
        print("  python scripts/youtube_ingest.py URL --cut --max-clips 3")
        print("  python scripts/youtube_ingest.py --from-package dumps/yt_demo --rebuild-highlights --cut")
        print(f"\nPolicy: {SOURCE_POLICY[:100]}…")
        return 0

    url = args.url.strip()
    if extract_video_id(url) and "://" not in url:
        url = f"https://www.youtube.com/watch?v={url}"

    langs = [x.strip() for x in (args.lang or "ko,en").split(",") if x.strip()]
    r = ingest_youtube(
        url,
        args.out,
        langs=langs,
        whisper=bool(args.whisper),
        whisper_model=args.whisper_model,
        download_media=bool(args.download_media),
        max_height=int(args.max_height),
        highlights=bool(args.highlights),
        max_clips=int(args.max_clips),
        cut_clips=bool(args.cut),
        reencode_clips=bool(args.reencode),
    )

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
    else:
        if not r.get("ok"):
            print(f"FAIL {r.get('error')}: {r.get('message')}", file=sys.stderr)
            steps = r.get("steps") or {}
            for k, v in steps.items():
                print(f"  step {k}: {v}", file=sys.stderr)
            return 1
        print(f"OK  {r.get('title')}")
        print(f"  video_id={r.get('video_id')}")
        print(f"  out_dir={r.get('out_dir')}")
        print(f"  segments={r.get('segment_count')}  highlights={r.get('highlight_count')}")
        steps = r.get("steps") or {}
        for k, v in steps.items():
            ok = v.get("ok") if isinstance(v, dict) else None
            extra = ""
            if isinstance(v, dict):
                if v.get("source"):
                    extra += f" source={v['source']}"
                if v.get("count") is not None:
                    extra += f" count={v['count']}"
                if v.get("error"):
                    extra += f" err={v['error']}"
            print(f"  [{k}] ok={ok}{extra}")
        paths = r.get("paths") or {}
        for k, v in paths.items():
            if k == "clips" and isinstance(v, list):
                print(f"  paths.clips ({len(v)})")
                for c in v:
                    print(f"    {c}")
            else:
                print(f"  paths.{k}={v}")
        print(f"\nPolicy: {SOURCE_POLICY}")
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
