#!/usr/bin/env python3
"""
Phase A — multi-engine character casting pool (exploration T2I).

Does NOT lock identity. After human pick, use character_promote.py → expand sheets.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401

import argparse
import os
import random
import sys

from lib.cast_pool import (
    ENGINE_SPECS,
    candidate_filename,
    cast_dir,
    ensure_cast,
    list_candidate_paths,
    load_manifest,
    parse_engines,
    save_manifest,
    validate_cast_id,
)
from lib.comfy_client import utc_now_iso
from lib.contact_sheet import build_contact_sheet

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PARTIAL = 31
EXIT_GEN = 30


def _gen_one(
    *,
    engine: str,
    prompt: str,
    negative: str,
    out_path: str,
    seed: int,
    width: int,
    height: int,
    dry_run: bool,
    timeout: int,
) -> dict:
    spec = ENGINE_SPECS[engine]
    if dry_run:
        print(f"  [dry-run] {engine} seed={seed} → {out_path}")
        return {"ok": True, "dry_run": True, "engine": engine, "seed": seed, "path": out_path}

    if spec["kind"] == "moody":
        from generate_moody import generate_image

        r = generate_image(
            prompt_text=prompt,
            model_type=spec["model"],
            output_filename=out_path,
            seed=seed,
            negative_text=negative,
            width=width,
            height=height,
            timeout_sec=timeout,
        )
        # generate_moody returns dict-like or path patterns
        if isinstance(r, dict):
            ok = bool(r.get("ok") or r.get("output_path") or os.path.isfile(out_path))
            return {
                "ok": ok,
                "engine": engine,
                "seed": seed,
                "path": out_path if os.path.isfile(out_path) else r.get("output_path"),
                "error": r.get("error"),
            }
        ok = os.path.isfile(out_path)
        return {"ok": ok, "engine": engine, "seed": seed, "path": out_path}

    if spec["kind"] == "krea":
        from generate_krea import generate_krea_image

        ok = bool(
            generate_krea_image(
                prompt_text=prompt,
                steps=8,
                cfg=1.0,
                sampler="euler_ancestral",
                scheduler="simple",
                output_filename=out_path,
            )
        )
        # krea ignores seed/size for now — still useful alternate quality axis
        return {
            "ok": ok and os.path.isfile(out_path),
            "engine": engine,
            "seed": seed,
            "path": out_path if os.path.isfile(out_path) else None,
            "error": None if ok else "KREA_FAILED",
        }

    return {"ok": False, "error": "UNKNOWN_ENGINE", "engine": engine}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Cast pool: multi-engine T2I character candidates (exploration)"
    )
    p.add_argument("--cast", default=None, help="cast_id e.g. heroine_ep01_cast")
    p.add_argument("--prompt", "-p", default=None, help="Appearance / casting prompt")
    p.add_argument("--prompt-file", default=None)
    p.add_argument("--negative", default=None)
    p.add_argument(
        "--engines",
        default="moody_pro,krea",
        help="Comma list: moody_real,moody_pro,moody_wild,krea",
    )
    p.add_argument("--per-engine", type=int, default=3, help="Candidates per engine")
    p.add_argument("--seed-base", type=int, default=None)
    p.add_argument("--width", type=int, default=1024)
    p.add_argument("--height", type=int, default=1024)
    p.add_argument("--contact-sheet", action="store_true", default=True)
    p.add_argument("--no-contact-sheet", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--list-engines", action="store_true")
    args = p.parse_args(argv)

    if args.list_engines:
        for k, v in ENGINE_SPECS.items():
            print(f"{k:12} {v['label']}  strengths={v['strengths']}")
        return EXIT_OK

    if not args.cast or not validate_cast_id(args.cast):
        print("[ERROR] --cast required (valid snake_case id)", file=sys.stderr)
        return EXIT_USAGE

    prompt = args.prompt
    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read().strip()
    if not prompt:
        # allow resume generation with existing manifest prompt
        try:
            man = load_manifest(args.cast)
            prompt = man.get("prompt")
        except Exception:
            prompt = None
    if not (prompt or "").strip():
        print("[ERROR] --prompt or --prompt-file required (or existing cast)", file=sys.stderr)
        return EXIT_USAGE

    try:
        engines = parse_engines(args.engines)
    except KeyError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return EXIT_USAGE

    neg = args.negative or ""
    man = ensure_cast(args.cast, prompt=prompt.strip(), negative=neg, engines=engines)
    if not neg:
        neg = man.get("negative") or ""

    seed_base = args.seed_base if args.seed_base is not None else random.randint(1000, 999999)
    cand_dir = os.path.join(cast_dir(args.cast), "candidates")
    os.makedirs(cand_dir, exist_ok=True)

    print(
        f"cast_pool cast={args.cast} engines={engines} per_engine={args.per_engine} "
        f"size={args.width}x{args.height} dry_run={args.dry_run}"
    )
    print(f"  prompt={prompt[:120]}...")

    ok_n = 0
    fail_n = 0
    new_entries = list(man.get("candidates") or [])
    idx = 0
    for eng in engines:
        for i in range(1, max(1, args.per_engine) + 1):
            idx += 1
            seed = seed_base + idx * 17
            fn = candidate_filename(args.cast, eng, seed, i)
            out_path = os.path.join(cand_dir, fn)
            if os.path.isfile(out_path) and not args.dry_run:
                print(f"\n=== {eng} c{i:02d} seed={seed} SKIP exists ===")
                ok_n += 1
                rel = f"candidates/{fn}"
                if not any((e.get("file") == rel) for e in new_entries):
                    new_entries.append(
                        {
                            "file": rel,
                            "engine": eng,
                            "seed": seed,
                            "index": i,
                            "created_at": utc_now_iso(),
                            "status": "candidate",
                        }
                    )
                continue
            print(f"\n=== {eng} c{i:02d} seed={seed} ===")
            r = _gen_one(
                engine=eng,
                prompt=prompt.strip(),
                negative=neg,
                out_path=out_path,
                seed=seed,
                width=args.width,
                height=args.height,
                dry_run=args.dry_run,
                timeout=args.timeout,
            )
            if r.get("ok"):
                ok_n += 1
                rel = f"candidates/{fn}"
                new_entries.append(
                    {
                        "file": rel,
                        "engine": eng,
                        "seed": seed,
                        "index": i,
                        "created_at": utc_now_iso(),
                        "status": "candidate",
                    }
                )
                print(f"  OK {out_path}")
            else:
                fail_n += 1
                print(f"  FAIL {r.get('error')}")

    if not args.dry_run:
        man["candidates"] = new_entries
        man["engines"] = engines
        man["status"] = "open"
        save_manifest(args.cast, man)

        if args.contact_sheet and not args.no_contact_sheet:
            paths = list_candidate_paths(args.cast)
            sheet_path = os.path.join(cast_dir(args.cast), "contact_sheet.png")
            cs = build_contact_sheet(paths, sheet_path, cols=min(4, max(1, len(engines))))
            if cs.get("ok"):
                print(f"\ncontact_sheet={sheet_path}")
            else:
                print(f"[WARN] contact sheet: {cs.get('error')} {cs.get('message')}")

    print(f"\nDone cast={args.cast} ok={ok_n} fail={fail_n}")
    print(f"  next: review {cast_dir(args.cast)}")
    print(
        "  then: python scripts/character_promote.py "
        f"--from <candidate.png> --id <char_id> --name \"...\" --cast {args.cast}"
    )
    if ok_n == 0 and fail_n:
        return EXIT_GEN
    if fail_n:
        return EXIT_PARTIAL
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
