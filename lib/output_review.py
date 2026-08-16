"""One-off output review packs (still / clip / audio).

Episode shots stay on shot_qa_*. Edit masters stay on edit_qa_*.
This module is the toolbox-mode judge: brief → pack → open → record → next lever.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from lib.comfy_client import ok_result, utc_now_iso
from lib.output_policy import die_if_toolbox

REVIEW_KIND_STILL = "still"
REVIEW_KIND_CLIP = "clip"
REVIEW_KIND_AUDIO = "audio"

STILL_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
CLIP_EXTS = {".mp4", ".webm", ".mov", ".mkv", ".avi"}
AUDIO_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}
MEDIA_EXTS = STILL_EXTS | CLIP_EXTS | AUDIO_EXTS

# Blocking items (one fail → whole verdict fail)
STILL_CHECKS: tuple[tuple[str, str], ...] = (
    ("S1_intent", "Matches brief subject / action / place"),
    ("S2_shot_size", "Shot size matches brief"),
    ("S3_identity", "Same person if a character was specified (else skip)"),
    ("S4_anatomy", "Hands / feet / limbs intact"),
    ("S5_anti", "Brief anti-list is absent"),
    ("S6_junk_text", "No accidental on-image garbage text"),
    ("S7_light", "Light / materials are specific (hint, not always blocking)"),
)
CLIP_CHECKS: tuple[tuple[str, str], ...] = (
    ("C1_no_freeze", "Motion continues to the last frame"),
    ("C2_motion_matches", "Camera / body action matches the motion brief"),
    ("C3_identity_hold", "Person matches the source still"),
    ("C4_no_warp", "No melt / morph"),
    ("C5_duration", "Length is real motion, not silence-pad"),
)
AUDIO_CHECKS: tuple[tuple[str, str], ...] = (
    ("A1_duration", "Duration within ~10% of brief"),
    ("A2_not_dead", "Has real level; not silent / constant PCM"),
    ("A3_bpm", "Estimated tempo matches brief (if given)"),
    ("A4_role_pure", "Stem/solo request is that role only"),
    ("A5_key", "Does not fight the stated key / chords"),
    ("A6_not_fullmix", "Solo/stem request is not a full band mix"),
)

OPTIONAL_STILL = frozenset({"S7_light"})
OPTIONAL_CLIP: frozenset[str] = frozenset()
OPTIONAL_AUDIO = frozenset({"A3_bpm", "A5_key"})

LEVERS: dict[str, dict[str, str]] = {
    "S1_intent": {
        "use": "rewrite prompt in the same dialect",
        "cli": 'python scripts/prompt_dialect.py show krea  # then same generate_* with a new sentence',
    },
    "S2_shot_size": {
        "use": "generate_reframe",
        "cli": 'python scripts/generate_reframe.py -i img.png --size medium -o out.png',
    },
    "S3_identity": {
        "use": "generate_character_consistent",
        "cli": 'python scripts/generate_character_consistent.py -i ref.png -p "..." -o out.png',
    },
    "S4_anatomy": {
        "use": "krea2_hand_detail / face_detail / anatomy_detail",
        "cli": "python scripts/generate_krea2_hand_detail.py -i img.png -o out.png",
    },
    "S5_anti": {
        "use": "rewrite prompt; put anti in front",
        "cli": "same generate_* with a changed prompt (not the same string)",
    },
    "S6_junk_text": {
        "use": "generate_qwen_edit",
        "cli": 'python scripts/generate_qwen_edit.py -i img.png -p "Remove all on-image text, keep the scene" -o out.png',
    },
    "S7_light": {
        "use": "generation-prompt rewrite (do not swap model first)",
        "cli": "python scripts/prompt_dialect.py show krea",
    },
    "C1_no_freeze": {
        "use": "shorter i2v / camera_move; no pad",
        "cli": 'python scripts/generate_i2v.py -i key.png -p "slow push-in, continuous" -o clip.mp4',
    },
    "C2_motion_matches": {
        "use": "rewrite motion-only I2V prompt",
        "cli": 'python scripts/generate_camera_move.py -i key.png --preset push_in -o clip.mp4',
    },
    "C3_identity_hold": {
        "use": "re-review the still first",
        "cli": "python scripts/review_media.py pack -i key.png --intent \"...\"",
    },
    "C4_no_warp": {
        "use": "shorter clip, less motion",
        "cli": 'python scripts/generate_i2v.py -i key.png -p "subtle blink, locked frame" -o clip.mp4',
    },
    "C5_duration": {
        "use": "flf / chain — never freeze-pad",
        "cli": "python scripts/generate_flf2v.py -i start.png --last end.png -p \"...\" -o bridge.mp4",
    },
    "A1_duration": {
        "use": "regenerate with --duration / --seconds",
        "cli": 'python scripts/generate_stable_audio.py -p "..." --duration 15 -o bed.flac',
    },
    "A2_not_dead": {
        "use": "ACE audio-codes / shorter chunks",
        "cli": "python scripts/generate_bgm.py --engine ace --audio-codes --seconds 15 -o bed.mp3",
    },
    "A3_bpm": {
        "use": "lock clock with MIDI",
        "cli": 'python scripts/generate_midi_arrangement.py --chords "Am,F,C,G" --genre lofi_hiphop -o bed.mid',
    },
    "A4_role_pure": {
        "use": "discard stem; MIDI role or solo prompt",
        "cli": 'python scripts/generate_stable_audio.py -p "solo dry kick and snare, no bass, no melody" --duration 8 -o drums.flac',
    },
    "A5_key": {
        "use": "skeleton + MIDI",
        "cli": 'python scripts/extract_music_skeleton.py --chords "Am,F,C,G" --bpm 96 -o sk.json',
    },
    "A6_not_fullmix": {
        "use": "treat as a bed, or remake as solo",
        "cli": 'python scripts/generate_minimax_music.py --mode bgm --caption "..." -o bed.flac',
    },
}

_KIND_CHECKS = {
    REVIEW_KIND_STILL: STILL_CHECKS,
    REVIEW_KIND_CLIP: CLIP_CHECKS,
    REVIEW_KIND_AUDIO: AUDIO_CHECKS,
}
_KIND_OPTIONAL = {
    REVIEW_KIND_STILL: OPTIONAL_STILL,
    REVIEW_KIND_CLIP: OPTIONAL_CLIP,
    REVIEW_KIND_AUDIO: OPTIONAL_AUDIO,
}


def detect_kind(path: str, *, kind: str | None = None) -> str:
    if kind:
        k = kind.strip().lower()
        if k in _KIND_CHECKS:
            return k
        raise ValueError(f"unknown kind: {kind}")
    ext = Path(path).suffix.lower()
    if ext in STILL_EXTS:
        return REVIEW_KIND_STILL
    if ext in CLIP_EXTS:
        return REVIEW_KIND_CLIP
    if ext in AUDIO_EXTS:
        return REVIEW_KIND_AUDIO
    raise ValueError(f"cannot detect media kind from extension: {path}")


def checks_for(kind: str) -> tuple[tuple[str, str], ...]:
    return _KIND_CHECKS[kind]


def optional_ids(kind: str) -> frozenset[str]:
    return _KIND_OPTIONAL[kind]


def blocking_ids(kind: str) -> list[str]:
    opt = optional_ids(kind)
    return [cid for cid, _ in checks_for(kind) if cid not in opt]


def lever_for(check_id: str) -> dict[str, str]:
    row = LEVERS.get(check_id)
    if not row:
        return {"use": "see skills/output-review/references/next_lever.md", "cli": ""}
    return dict(row)


def review_next_cli(path: str, *, intent: str = "") -> str:
    intent_q = (intent or "<write the brief you just used>").replace('"', "'")
    return (
        f'python scripts/review_media.py pack -i "{os.path.abspath(path)}" '
        f'--intent "{intent_q}"'
    )


def attach_review_hint(result: dict[str, Any]) -> dict[str, Any]:
    """Add next_action on successful media outputs. No-op otherwise."""
    if not result.get("ok"):
        return result
    if result.get("next_action"):
        return result
    path = result.get("output_path") or result.get("path")
    if not path or not isinstance(path, str):
        return result
    ext = Path(path).suffix.lower()
    if ext not in MEDIA_EXTS:
        return result
    result["next_action"] = "review_media"
    result["review_cli"] = review_next_cli(path, intent=str(result.get("prompt") or ""))
    result.setdefault("agent_notes", [])
    note = (
        "exit 0 means the file exists, not that it matches the brief. "
        "Equip output-review and run review_cli before showing the user."
    )
    if note not in result["agent_notes"]:
        result["agent_notes"].append(note)
    return result


def print_review_nudge(path: str, *, intent: str = "") -> None:
    print(
        f"[REVIEW] file exists ≠ quality. Open it, then:\n"
        f"  {review_next_cli(path, intent=intent)}"
    )


def default_pack_dir(media_path: str) -> str:
    return os.path.abspath(media_path) + ".review"


def pack_paths(pack_dir: str) -> dict[str, str]:
    root = os.path.abspath(pack_dir)
    return {
        "root": root,
        "brief": os.path.join(root, "BRIEF.md"),
        "review": os.path.join(root, "REVIEW.md"),
        "probe": os.path.join(root, "probe.json"),
        "record": os.path.join(root, "record.json"),
        "frames": os.path.join(root, "frames"),
        "spectrogram": os.path.join(root, "spectrogram.png"),
    }


def _write_text(path: str, text: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _probe_media(path: str, kind: str, pack: dict[str, str]) -> dict[str, Any]:
    info: dict[str, Any] = {
        "path": os.path.abspath(path),
        "kind": kind,
        "exists": os.path.isfile(path),
        "bytes": os.path.getsize(path) if os.path.isfile(path) else 0,
    }
    if kind == REVIEW_KIND_CLIP:
        try:
            from lib.ffmpeg_util import probe_duration

            info["duration_sec"] = probe_duration(path)
        except Exception as e:  # pragma: no cover - probe optional
            info["duration_sec"] = None
            info["probe_error"] = str(e)
        frames_dir = pack["frames"]
        os.makedirs(frames_dir, exist_ok=True)
        try:
            from lib.visual_qa import extract_video_frame

            extracted: list[str] = []
            for label in ("first", "mid", "last"):
                dest = os.path.join(frames_dir, f"{label}.png")
                if extract_video_frame(path, dest, at=label):
                    extracted.append(dest)
            info["frames"] = extracted
        except Exception as e:  # pragma: no cover
            info["frames"] = []
            info["frame_error"] = str(e)
    elif kind == REVIEW_KIND_AUDIO:
        try:
            from lib.audio_package import probe_audio_duration

            info["duration_sec"] = probe_audio_duration(path)
        except Exception:
            try:
                from lib.ffmpeg_util import probe_duration

                info["duration_sec"] = probe_duration(path)
            except Exception as e:  # pragma: no cover
                info["duration_sec"] = None
                info["probe_error"] = str(e)
        spec = pack["spectrogram"]
        try:
            from lib.ffmpeg_util import run_ffmpeg

            r = run_ffmpeg(
                [
                    "-y",
                    "-i",
                    path,
                    "-lavfi",
                    "showspectrumpic=s=960x360:legend=disabled",
                    spec,
                ],
                timeout_sec=60,
            )
            info["spectrogram"] = spec if r.get("ok") and os.path.isfile(spec) else None
        except Exception as e:  # pragma: no cover
            info["spectrogram"] = None
            info["spectrogram_error"] = str(e)
    return info


def _render_review_md(
    *,
    media: str,
    kind: str,
    intent: str,
    anti: str,
    probe: dict[str, Any],
    pack: dict[str, str],
) -> str:
    checks = checks_for(kind)
    opt = optional_ids(kind)
    lines = [
        "# REVIEW",
        "",
        "exit 0 ≠ pass. Open every path under OPEN, then `review_media record`.",
        "",
        f"- kind: `{kind}`",
        f"- media: `{media}`",
        f"- intent: {intent or '(write the brief now)'}",
    ]
    if anti:
        lines.append(f"- anti: {anti}")
    lines.extend(["", "## OPEN", ""])
    lines.append(f"- media: `{media}`")
    for fr in probe.get("frames") or []:
        lines.append(f"- frame: `{fr}`")
    if probe.get("spectrogram"):
        lines.append(f"- spectrogram: `{probe['spectrogram']}`")
    lines.append(f"- probe: `{pack['probe']}`")
    lines.extend(["", "## CHECKS", ""])
    for cid, desc in checks:
        flag = "" if cid not in opt else " (hint)"
        lines.append(f"- [ ] `{cid}`{flag} — {desc}")
    lines.extend(["", "## IF FAIL", ""])
    for cid, _ in checks:
        lev = lever_for(cid)
        if lev.get("cli"):
            lines.append(f"- `{cid}` → {lev['use']}")
            lines.append(f"  `{lev['cli']}`")
    lines.extend(
        [
            "",
            "## RECORD",
            "",
            "```bash",
            f'python scripts/review_media.py record --pack "{pack["root"]}" '
            f'--verdict pass --opened --notes "what you saw"',
            "```",
            "",
            "Skill: `skills/output-review/SKILL.md`",
            "",
        ]
    )
    return "\n".join(lines)


def build_pack(
    media_path: str,
    *,
    intent: str,
    pack_dir: str | None = None,
    kind: str | None = None,
    anti: str = "",
) -> dict[str, Any]:
    media = os.path.abspath(media_path)
    if not os.path.isfile(media):
        return {
            "ok": False,
            "error": "NO_MEDIA",
            "message": f"media not found: {media}",
        }
    kind_r = detect_kind(media, kind=kind)
    dest = die_if_toolbox(pack_dir or default_pack_dir(media))
    os.makedirs(dest, exist_ok=True)
    pack = pack_paths(dest)
    probe = _probe_media(media, kind_r, pack)
    brief = (
        f"# BRIEF\n\n"
        f"- intent: {intent or '(missing — write before judging)'}\n"
        f"- anti: {anti or '(none stated)'}\n"
        f"- kind: {kind_r}\n"
        f"- media: {media}\n"
    )
    _write_text(pack["brief"], brief)
    _write_text(
        pack["review"],
        _render_review_md(
            media=media,
            kind=kind_r,
            intent=intent,
            anti=anti,
            probe=probe,
            pack=pack,
        ),
    )
    with open(pack["probe"], "w", encoding="utf-8") as f:
        json.dump(probe, f, ensure_ascii=False, indent=2)
    open_list = [media]
    open_list.extend(probe.get("frames") or [])
    if probe.get("spectrogram"):
        open_list.append(probe["spectrogram"])
    return ok_result(
        tool="review_media.pack",
        pack_dir=dest,
        media=media,
        kind=kind_r,
        intent=intent,
        review_md=pack["review"],
        probe=pack["probe"],
        open=open_list,
        checks=[cid for cid, _ in checks_for(kind_r)],
        blocking=blocking_ids(kind_r),
        next_action="open_then_record",
        message="Open every path in open[], then review_media record --opened",
    )


def write_record(
    pack_dir: str,
    *,
    verdict: str,
    notes: str,
    opened: bool,
    fails: list[str] | None = None,
    next_id: str | None = None,
    agent: str = "",
) -> dict[str, Any]:
    dest = die_if_toolbox(pack_dir)
    pack = pack_paths(dest)
    if not os.path.isdir(dest):
        return {
            "ok": False,
            "error": "NO_PACK",
            "message": f"pack dir missing: {dest}",
        }
    v = (verdict or "").strip().lower()
    if v not in {"pass", "fail", "pending"}:
        return {"ok": False, "error": "BAD_VERDICT", "message": f"verdict={verdict}"}
    fail_ids = [x.strip() for x in (fails or []) if x and x.strip()]
    if v == "pass" and not opened:
        return {
            "ok": False,
            "error": "NOT_OPENED",
            "message": "pass requires --opened (you must open the pack files)",
            "exit_hint": 23,
        }
    if v == "pass" and fail_ids:
        return {
            "ok": False,
            "error": "PASS_WITH_FAILS",
            "message": "cannot pass while --fail IDs are set",
        }
    if v == "fail" and not fail_ids:
        return {
            "ok": False,
            "error": "FAIL_NEEDS_ID",
            "message": "fail requires at least one --fail CHECK_ID",
        }
    next_cli = ""
    next_use = ""
    nid = (next_id or (fail_ids[0] if fail_ids else "")).strip()
    if nid:
        lev = lever_for(nid)
        next_use = lev.get("use") or ""
        next_cli = lev.get("cli") or ""
    rec = {
        "verdict": v,
        "opened": bool(opened),
        "notes": notes or "",
        "fails": fail_ids,
        "next": nid,
        "next_use": next_use,
        "next_cli": next_cli,
        "agent": agent or os.environ.get("AGENT_NAME") or "",
        "created_at": utc_now_iso(),
        "pack_dir": dest,
    }
    with open(pack["record"], "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    msg = "recorded pass — may show user or advance"
    if v == "fail":
        msg = f"recorded fail {fail_ids} — run next_cli, do not claim done"
    elif v == "pending":
        msg = "recorded pending"
    return ok_result(
        tool="review_media.record",
        path=pack["record"],
        verdict=v,
        fails=fail_ids,
        next_cli=next_cli,
        next_use=next_use,
        message=msg,
        next_action="repair" if v == "fail" else "advance",
    )


def format_checks(kind: str) -> str:
    opt = optional_ids(kind)
    lines = [f"# {kind} checks", ""]
    for cid, desc in checks_for(kind):
        tag = "hint" if cid in opt else "block"
        lines.append(f"- `{cid}` ({tag}) {desc}")
    return "\n".join(lines) + "\n"
