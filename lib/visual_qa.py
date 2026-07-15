"""Visual QA contracts for keyframe / clip approve hard gates (Rule 7.3).

Agents must write a structured QA JSON (pass) before shot_approve may set
keyframe_status=approved or clip_status=approved. Mechanical file existence
alone is not quality proof.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any

from lib.comfy_client import WORKSPACE_ROOT, utc_now_iso
from lib.story_package import StoryPackage

# Exit when approve blocked by missing/fail visual QA
EXIT_VISUAL_QA = 23

STAGES = ("keyframe", "clip", "identity")
VERDICTS = ("pass", "fail", "pending")
METHODS = ("vision_open", "human", "heuristic", "hybrid", "skipped")

# Required checklist IDs that must be true for approve
KEYFRAME_REQUIRED_CHECKS = (
    "K2_action_intent",
    "K4_anatomy",
    "K5_identity",
)
CLIP_REQUIRED_CHECKS = (
    "C1_no_freeze_pad",
    "C3_no_warp",
    "C4_identity_hold",
)

KEYFRAME_CHECK_IDS = (
    "K1_shot_type",
    "K2_action_intent",
    "K3_motif",
    "K4_anatomy",
    "K5_identity",
    "K6_wardrobe_props",
    "K7_space",
    "K8_glass_mirror",
    "K9_framing_variety",
    "K10_canvas",
    "K11_text_junk",
    "K12_anti_list",
    "K13_wardrobe_continuity",
    "K14_weather_continuity",
    "K15_size_rhythm",
)

CLIP_CHECK_IDS = (
    "C1_no_freeze_pad",
    "C2_duration",
    "C3_no_warp",
    "C4_identity_hold",
    "C5_motion_match",
    "C6_props_stable",
    "C7_si2v_lip",
    "C8_frame_defects",
    "C9_audio_policy",
)


def qa_dir(story: StoryPackage) -> str:
    d = story.path("meta", "visual_qa")
    os.makedirs(d, exist_ok=True)
    return d


def qa_json_rel(shot_id: str, stage: str) -> str:
    return f"meta/visual_qa/{shot_id}_{stage}.json"


def qa_json_path(story: StoryPackage, shot_id: str, stage: str) -> str:
    return story.path(*qa_json_rel(shot_id, stage).split("/"))


def qa_pack_rel(shot_id: str, stage: str = "keyframe") -> str:
    return f"boards/qa/{shot_id}_{stage}_pack.png"


def qa_pack_path(story: StoryPackage, shot_id: str, stage: str = "keyframe") -> str:
    return story.path(*qa_pack_rel(shot_id, stage).split("/"))


def identity_sheet_rel() -> str:
    return "boards/identity_contact.png"


def identity_qa_rel() -> str:
    return "meta/visual_qa/episode_identity.json"


def identity_sheet_path(story: StoryPackage) -> str:
    return story.path(*identity_sheet_rel().split("/"))


def identity_qa_path(story: StoryPackage) -> str:
    return story.path(*identity_qa_rel().split("/"))


def qa_log_path(story: StoryPackage) -> str:
    return story.path("QA_LOG.md")


def file_sha256(path: str, *, max_bytes: int | None = None) -> str | None:
    if not path or not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            if max_bytes is None:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            else:
                h.update(f.read(max_bytes))
        return h.hexdigest()
    except OSError:
        return None


def keyframe_abs(story: StoryPackage, shot: dict) -> str | None:
    sid = shot.get("shot_id")
    rel = shot.get("keyframe") or (f"keyframes/{sid}.png" if sid else None)
    if not rel:
        return None
    p = story.path(*str(rel).replace("\\", "/").split("/"))
    return p if os.path.isfile(p) else None


def work_clip_abs(story: StoryPackage, shot: dict) -> str | None:
    sid = shot.get("shot_id") or ""
    candidates = [
        shot.get("clip_work_s2v"),
        shot.get("clip_work"),
        f"clips/work/{sid}_s2v.mp4",
        f"clips/work/{sid}.mp4",
    ]
    for rel in candidates:
        if not rel:
            continue
        p = story.path(*str(rel).replace("\\", "/").split("/"))
        if os.path.isfile(p):
            return p
    return None


def resolve_identity_ref(
    story: StoryPackage,
    shot: dict,
    *,
    character_id: str | None = None,
) -> str | None:
    """Best face/body ref for side-by-side identity QA."""
    cids = list(shot.get("character_ids") or [])
    if character_id:
        cids = [character_id] + [c for c in cids if c != character_id]
    if not cids:
        # episode-level cast
        for key in ("character_ids", "cast_ids"):
            raw = story.doc.get(key)
            if isinstance(raw, list) and raw:
                cids = [str(x) for x in raw]
                break
        primary = story.doc.get("primary_character_id") or story.doc.get("character_id")
        if primary:
            cids = [str(primary)] + cids

    # shot-level character_refs map alias -> path
    crefs = shot.get("character_refs") or {}
    if isinstance(crefs, dict):
        for key in ("master_front", "face", "primary", "ref"):
            raw = crefs.get(key)
            if isinstance(raw, str):
                p = raw
                if not os.path.isabs(p):
                    p = story.path(*p.replace("\\", "/").split("/"))
                    if not os.path.isfile(p):
                        # workspace-relative characters/
                        p2 = os.path.join(WORKSPACE_ROOT, raw.replace("\\", "/"))
                        p = p2 if os.path.isfile(p2) else p
                if os.path.isfile(p):
                    return p

    for cid in cids:
        try:
            from lib.character_package import CharacterPackage

            pkg = CharacterPackage.load(str(cid))
            ref = pkg.default_source_ref()
            if ref and os.path.isfile(ref):
                return ref
            for alias in ("master_front", "master_full", "face_neutral"):
                for folder in ("approved", "refs"):
                    for ext in (".png", ".jpg", ".webp"):
                        cand = pkg.path(folder, f"{alias}{ext}")
                        if os.path.isfile(cand):
                            return cand
        except Exception:
            root = os.path.join(WORKSPACE_ROOT, "characters", str(cid), "approved")
            for name in ("master_front.png", "master_full.png", "face_neutral.png"):
                cand = os.path.join(root, name)
                if os.path.isfile(cand):
                    return cand
    return None


def prev_keyframe_abs(story: StoryPackage, shot: dict) -> str | None:
    shots = sorted(story.shots(), key=lambda s: s.get("order", 0))
    sid = shot.get("shot_id")
    prev = None
    for s in shots:
        if s.get("shot_id") == sid:
            break
        prev = s
    if not prev:
        return None
    return keyframe_abs(story, prev)


def load_qa_report(path: str) -> dict[str, Any] | None:
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def required_checks_for(stage: str) -> tuple[str, ...]:
    if stage == "keyframe":
        return KEYFRAME_REQUIRED_CHECKS
    if stage == "clip":
        return CLIP_REQUIRED_CHECKS
    return ()


def normalize_check_entry(val: Any) -> dict[str, Any]:
    if isinstance(val, bool):
        return {"pass": val, "note": ""}
    if isinstance(val, dict):
        p = val.get("pass")
        if p is None and "ok" in val:
            p = val.get("ok")
        return {
            "pass": bool(p),
            "note": str(val.get("note") or val.get("message") or ""),
        }
    if isinstance(val, str):
        low = val.strip().lower()
        if low in ("pass", "ok", "true", "1", "yes"):
            return {"pass": True, "note": ""}
        if low in ("fail", "false", "0", "no"):
            return {"pass": False, "note": ""}
        # "fail:extra fingers"
        if ":" in val:
            head, note = val.split(":", 1)
            return {
                "pass": head.strip().lower() in ("pass", "ok", "true", "yes"),
                "note": note.strip(),
            }
        return {"pass": False, "note": val}
    return {"pass": False, "note": str(val)}


def parse_check_cli(items: list[str] | None) -> dict[str, dict[str, Any]]:
    """Parse --check K4_anatomy=pass or K4_anatomy=fail:note"""
    out: dict[str, dict[str, Any]] = {}
    for raw in items or []:
        if not raw or "=" not in raw:
            continue
        key, val = raw.split("=", 1)
        key = key.strip()
        out[key] = normalize_check_entry(val.strip())
    return out


def build_qa_report(
    *,
    episode_id: str,
    shot_id: str,
    stage: str,
    verdict: str,
    checks: dict[str, Any] | None = None,
    notes: str = "",
    method: str = "vision_open",
    agent: str = "",
    artifact: str | None = None,
    artifact_sha256: str | None = None,
    evidence_paths: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stage = str(stage).lower().strip()
    verdict = str(verdict).lower().strip()
    method = str(method).lower().strip()
    if stage not in STAGES:
        raise ValueError(f"invalid stage: {stage}")
    if verdict not in VERDICTS:
        raise ValueError(f"invalid verdict: {verdict}")
    if method not in METHODS:
        method = "vision_open"

    norm_checks: dict[str, dict[str, Any]] = {}
    for k, v in (checks or {}).items():
        norm_checks[str(k)] = normalize_check_entry(v)

    # Auto-fail verdict if required checks fail
    req = required_checks_for(stage)
    if verdict == "pass" and req:
        for cid in req:
            ent = norm_checks.get(cid)
            if not ent or not ent.get("pass"):
                verdict = "fail"
                notes = (notes + f" | auto-fail missing/failed {cid}").strip(" |")

    report: dict[str, Any] = {
        "schema": "agent_visual_qa_v1",
        "episode_id": episode_id,
        "shot_id": shot_id,
        "stage": stage,
        "verdict": verdict,
        "method": method,
        "agent": agent or os.environ.get("AGENT_NAME") or os.environ.get("USERNAME") or "",
        "notes": notes or "",
        "checks": norm_checks,
        "artifact": artifact,
        "artifact_sha256": artifact_sha256,
        "evidence_paths": list(evidence_paths or []),
        "checked_at": utc_now_iso(),
        "required_checks": list(req),
    }
    if extra:
        report["extra"] = extra
    return report


def save_qa_report(story: StoryPackage, report: dict[str, Any]) -> str:
    stage = report["stage"]
    shot_id = report["shot_id"]
    path = qa_json_path(story, shot_id, stage)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    append_qa_log_row(
        story,
        shot_id=shot_id,
        stage=stage,
        verdict=str(report.get("verdict")),
        notes=str(report.get("notes") or ""),
    )
    return path


def append_qa_log_row(
    story: StoryPackage,
    *,
    shot_id: str,
    stage: str,
    verdict: str,
    notes: str = "",
) -> None:
    path = qa_log_path(story)
    header = (
        "# QA_LOG\n\n"
        "| shot | stage | verdict | notes | at |\n"
        "|------|-------|---------|-------|-----|\n"
    )
    at = utc_now_iso()
    note_clean = (notes or "").replace("|", "/").replace("\n", " ")[:200]
    row = f"| {shot_id} | {stage} | {verdict.upper()} | {note_clean} | {at} |\n"
    if not os.path.isfile(path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(header)
            f.write(row)
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write(row)


def validate_qa_for_approve(
    story: StoryPackage,
    shot: dict,
    stage: str,
    *,
    require_pack: bool = False,
) -> dict[str, Any]:
    """
    Return {ok, error, message, report, path}.
    ok=True only when approve is allowed for this stage.
    """
    sid = str(shot.get("shot_id") or "")
    stage = stage.lower().strip()
    path = qa_json_path(story, sid, stage)
    report = load_qa_report(path)

    if not report:
        return {
            "ok": False,
            "error": "QA_MISSING",
            "message": (
                f"visual QA JSON missing for {sid} stage={stage}. "
                f"Run: python scripts/shot_qa_pack.py -e {story.episode_id} -s {sid} "
                f"&& python scripts/shot_qa_record.py -e {story.episode_id} -s {sid} "
                f"--stage {stage} --verdict pass --pass-required --notes \"...\""
            ),
            "path": path,
            "report": None,
        }

    if str(report.get("method") or "").lower() == "skipped":
        return {
            "ok": False,
            "error": "QA_SKIPPED",
            "message": "method=skipped is not valid for approve",
            "path": path,
            "report": report,
        }

    if str(report.get("verdict") or "").lower() != "pass":
        return {
            "ok": False,
            "error": "QA_FAIL",
            "message": (
                f"visual QA verdict={report.get('verdict')!r} — fix/regenerate, "
                f"then re-record pass"
            ),
            "path": path,
            "report": report,
        }

    # Required checks
    checks = report.get("checks") or {}
    if not isinstance(checks, dict):
        checks = {}
    for cid in required_checks_for(stage):
        ent = normalize_check_entry(checks.get(cid)) if cid in checks else None
        if not ent or not ent.get("pass"):
            return {
                "ok": False,
                "error": "QA_CHECK_FAIL",
                "message": f"required check {cid} not pass in {path}",
                "path": path,
                "report": report,
            }

    # Artifact freshness: sha must match current media when present
    if stage == "keyframe":
        art = keyframe_abs(story, shot)
    elif stage == "clip":
        art = work_clip_abs(story, shot)
    else:
        art = None

    if art:
        current_sha = file_sha256(art)
        recorded = report.get("artifact_sha256")
        if recorded and current_sha and recorded != current_sha:
            return {
                "ok": False,
                "error": "QA_STALE",
                "message": (
                    f"QA JSON is stale (artifact changed since check). "
                    f"Re-run shot_qa_record after reviewing new file: {art}"
                ),
                "path": path,
                "report": report,
            }
        if not recorded and current_sha:
            # Soft: allow but warn via message — still ok for approve if other gates pass
            # Prefer requiring sha for new records; legacy pass without sha: allow
            pass

    if require_pack:
        pack = qa_pack_path(story, sid, stage if stage in ("keyframe", "clip") else "keyframe")
        if not os.path.isfile(pack):
            return {
                "ok": False,
                "error": "QA_PACK_MISSING",
                "message": (
                    f"QA pack missing: {pack}. "
                    f"Run shot_qa_pack.py -e {story.episode_id} -s {sid}"
                ),
                "path": path,
                "report": report,
            }

    # Live re-check freeze on clip approve (do not trust stale C1 pass alone)
    if stage == "clip" and art and freeze_gate_enabled():
        allow_still = shot_allows_still_freeze(shot, story.doc)
        sample = story.path("boards", "qa", f"{sid}_clip_frames")
        gate = gate_work_clip_no_freeze(
            art,
            sample_dir=sample,
            allow_still=allow_still,
        )
        if not gate.get("ok") and gate.get("error") == "FREEZE_PAD_SUSPECT":
            return {
                "ok": False,
                "error": "FREEZE_PAD_SUSPECT",
                "message": gate.get("message") or "freeze detected on clip",
                "path": path,
                "report": report,
                "freeze": gate,
            }

    return {
        "ok": True,
        "error": None,
        "message": "visual QA pass",
        "path": path,
        "report": report,
    }


def require_visual_qa_enabled() -> bool:
    """Default ON. Set AGENT_REQUIRE_VISUAL_QA=0 to disable (debug)."""
    raw = (os.environ.get("AGENT_REQUIRE_VISUAL_QA") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def shot_qa_status(story: StoryPackage, shot: dict) -> dict[str, Any]:
    """Summary for episode_status."""
    sid = str(shot.get("shot_id") or "")
    kf_path = qa_json_path(story, sid, "keyframe")
    clip_path = qa_json_path(story, sid, "clip")
    kf = load_qa_report(kf_path)
    cl = load_qa_report(clip_path)
    kf_verdict = (kf or {}).get("verdict")
    cl_verdict = (cl or {}).get("verdict")
    kf_file = keyframe_abs(story, shot) is not None
    clip_file = work_clip_abs(story, shot) is not None

    # Stale detection
    kf_stale = False
    if kf and kf_file:
        art = keyframe_abs(story, shot)
        sha = file_sha256(art) if art else None
        if sha and kf.get("artifact_sha256") and kf.get("artifact_sha256") != sha:
            kf_stale = True
    clip_stale = False
    if cl and clip_file:
        art = work_clip_abs(story, shot)
        sha = file_sha256(art) if art else None
        if sha and cl.get("artifact_sha256") and cl.get("artifact_sha256") != sha:
            clip_stale = True

    return {
        "shot_id": sid,
        "keyframe_qa": kf_verdict,
        "keyframe_qa_ok": kf_verdict == "pass" and not kf_stale,
        "keyframe_qa_stale": kf_stale,
        "keyframe_qa_path": qa_json_rel(sid, "keyframe") if kf else None,
        "clip_qa": cl_verdict,
        "clip_qa_ok": cl_verdict == "pass" and not clip_stale,
        "clip_qa_stale": clip_stale,
        "clip_qa_path": qa_json_rel(sid, "clip") if cl else None,
        "qa_pack_exists": os.path.isfile(qa_pack_path(story, sid, "keyframe")),
    }


def load_identity_qa(story: StoryPackage) -> dict[str, Any] | None:
    return load_qa_report(identity_qa_path(story))


def save_identity_qa(
    story: StoryPackage,
    *,
    verdict: str,
    notes: str = "",
    shot_ids: list[str] | None = None,
    method: str = "vision_open",
    agent: str = "",
) -> str:
    sheet = identity_sheet_path(story)
    report = {
        "schema": "agent_visual_qa_v1",
        "episode_id": story.episode_id,
        "shot_id": None,
        "stage": "identity",
        "verdict": str(verdict).lower().strip(),
        "method": method,
        "agent": agent or os.environ.get("AGENT_NAME") or "",
        "notes": notes or "",
        "checks": {
            "I1_cast_consistency": {
                "pass": str(verdict).lower() == "pass",
                "note": notes or "",
            }
        },
        "artifact": identity_sheet_rel() if os.path.isfile(sheet) else None,
        "artifact_sha256": file_sha256(sheet) if os.path.isfile(sheet) else None,
        "evidence_paths": [identity_sheet_rel()] if os.path.isfile(sheet) else [],
        "shot_ids": shot_ids or [
            s.get("shot_id") for s in story.shots() if keyframe_abs(story, s)
        ],
        "checked_at": utc_now_iso(),
        "required_checks": ["I1_cast_consistency"],
    }
    path = identity_qa_path(story)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    append_qa_log_row(
        story,
        shot_id="EP",
        stage="identity",
        verdict=str(report["verdict"]),
        notes=notes,
    )
    return path


def build_compare_strip(
    panels: list[tuple[str, str]],
    output_path: str,
    *,
    thumb_h: int = 480,
    pad: int = 10,
    label_h: int = 28,
    bg: tuple[int, int, int] = (18, 18, 20),
) -> dict[str, Any]:
    """
    panels: list of (label, image_path). Missing paths become dark placeholders.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return {"ok": False, "error": "PIL_MISSING", "message": "pip install Pillow"}

    if not panels:
        return {"ok": False, "error": "NO_PANELS", "message": "no panels"}

    thumbs: list[Any] = []
    labels: list[str] = []
    for label, path in panels:
        labels.append(label)
        if path and os.path.isfile(path):
            try:
                im = Image.open(path).convert("RGB")
                w = max(1, int(im.width * (thumb_h / im.height)))
                im = im.resize((w, thumb_h), Image.Resampling.LANCZOS)
                thumbs.append(im)
                continue
            except Exception:
                pass
        thumbs.append(Image.new("RGB", (int(thumb_h * 9 / 16), thumb_h), (48, 32, 32)))

    cell_h = thumb_h + label_h + pad * 2
    widths = [t.width + pad * 2 for t in thumbs]
    total_w = sum(widths)
    sheet = Image.new("RGB", (total_w, cell_h), bg)
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    x = 0
    for thumb, label, wcell in zip(thumbs, labels, widths):
        sheet.paste(thumb, (x + pad, pad + label_h))
        draw.text((x + pad, 6), label[:40], fill=(220, 220, 220), font=font)
        x += wcell

    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    sheet.save(output_path)
    return {
        "ok": True,
        "output_path": os.path.abspath(output_path),
        "panels": len(thumbs),
    }


def extract_video_frame(video: str, png: str, *, time_sec: float | None = None, at: str = "first") -> bool:
    """Extract one frame; at=first|last|mid or time_sec."""
    from lib.ffmpeg_util import run_ffmpeg, probe_duration

    os.makedirs(os.path.dirname(os.path.abspath(png)) or ".", exist_ok=True)
    if time_sec is not None:
        r = run_ffmpeg(
            [
                "-y",
                "-ss",
                f"{max(0.0, float(time_sec)):.3f}",
                "-i",
                video,
                "-frames:v",
                "1",
                "-q:v",
                "2",
                png,
            ],
            timeout_sec=60,
        )
        return bool(r.get("ok") and os.path.isfile(png) and os.path.getsize(png) > 500)

    if at == "mid":
        dur = probe_duration(video) or 0.0
        return extract_video_frame(video, png, time_sec=max(0.0, dur * 0.5))
    if at == "last":
        r = run_ffmpeg(
            ["-y", "-sseof", "-0.05", "-i", video, "-frames:v", "1", "-q:v", "2", png],
            timeout_sec=60,
        )
        if r.get("ok") and os.path.isfile(png) and os.path.getsize(png) > 500:
            return True
        return extract_video_frame(video, png, time_sec=None, at="first")
    # first
    r = run_ffmpeg(
        ["-y", "-i", video, "-frames:v", "1", "-q:v", "2", png],
        timeout_sec=60,
    )
    return bool(r.get("ok") and os.path.isfile(png) and os.path.getsize(png) > 500)


def freeze_gate_enabled() -> bool:
    """Default ON. AGENT_FREEZE_GATE=0 disables post-gen / QA freeze detection."""
    raw = (os.environ.get("AGENT_FREEZE_GATE") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def freeze_diff_threshold() -> float:
    """Mean absolute RGB diff; below = nearly identical frames."""
    try:
        return float(os.environ.get("AGENT_FREEZE_DIFF_THRESHOLD") or "2.5")
    except ValueError:
        return 2.5


def _frame_mean_abs_diff(path_a: str, path_b: str) -> float | None:
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        import numpy as np  # type: ignore

        a = np.asarray(Image.open(path_a).convert("RGB"), dtype=np.float32)
        b = np.asarray(Image.open(path_b).convert("RGB"), dtype=np.float32)
        if a.shape != b.shape:
            b_img = Image.open(path_b).convert("RGB").resize(
                (a.shape[1], a.shape[0]), Image.Resampling.LANCZOS
            )
            b = np.asarray(b_img, dtype=np.float32)
        return float(np.mean(np.abs(a - b)))
    except Exception:
        try:
            from PIL import Image, ImageChops, ImageStat

            a = Image.open(path_a).convert("RGB")
            b = Image.open(path_b).convert("RGB")
            if a.size != b.size:
                b = b.resize(a.size, Image.Resampling.LANCZOS)
            diff = ImageChops.difference(a, b)
            stat = ImageStat.Stat(diff)
            return float(sum(stat.mean) / 3.0)
        except Exception:
            return None


def freeze_pad_heuristic(
    video: str,
    *,
    sample_dir: str,
    threshold: float | None = None,
) -> dict[str, Any]:
    """
    Multi-point motion check for freeze pad / dead tail.

    - freeze_tail: early segment still has motion, late segment nearly static
      (classic short-I2V + tpad clone / dead end)
    - static_clip: whole clip nearly static (fail for work motion clips unless allow_still)

    Returns {ok, freeze_suspect, kind, mean_abs_diff, pairs, ...}.
    """
    from lib.ffmpeg_util import probe_duration

    thr = float(threshold if threshold is not None else freeze_diff_threshold())
    os.makedirs(sample_dir, exist_ok=True)
    dur = probe_duration(video)
    if not dur or dur < 0.4:
        return {
            "ok": False,
            "error": "DURATION_UNKNOWN_OR_SHORT",
            "freeze_suspect": None,
            "duration_sec": dur,
        }

    # fractions along timeline
    points = {
        "p20": max(0.0, dur * 0.20),
        "p40": max(0.0, dur * 0.40),
        "p55": max(0.0, dur * 0.55),
        "p75": max(0.0, dur * 0.75),
        "p92": max(0.0, dur - 0.12),
    }
    paths: dict[str, str] = {}
    for name, t in points.items():
        p = os.path.join(sample_dir, f"_freeze_{name}.png")
        if not extract_video_frame(video, p, time_sec=t):
            return {
                "ok": False,
                "error": "FRAME_FAIL",
                "freeze_suspect": None,
                "failed_point": name,
            }
        paths[name] = p

    def _pair(a: str, b: str) -> float | None:
        return _frame_mean_abs_diff(paths[a], paths[b])

    pair_specs = [
        ("early", "p20", "p40"),
        ("mid", "p40", "p55"),
        ("late_a", "p55", "p75"),
        ("late_b", "p55", "p92"),
        ("tail", "p75", "p92"),
    ]
    pairs: dict[str, float] = {}
    for label, a, b in pair_specs:
        d = _pair(a, b)
        if d is None:
            return {"ok": False, "error": "DIFF_FAIL", "freeze_suspect": None}
        pairs[label] = round(d, 3)

    early_motion = pairs["early"] >= thr or pairs["mid"] >= thr
    late_static = pairs["late_b"] < thr or pairs["tail"] < thr
    all_static = all(v < thr for v in pairs.values())

    kind = "ok"
    freeze_suspect = False
    if all_static:
        kind = "static_clip"
        freeze_suspect = True
    elif early_motion and late_static:
        kind = "freeze_tail"
        freeze_suspect = True
    elif pairs["late_b"] < thr and pairs["tail"] < thr and pairs["mid"] < thr * 1.2:
        # weak motion then hard freeze
        kind = "freeze_tail"
        freeze_suspect = True

    mid_end = pairs.get("late_b", pairs.get("tail", 0.0))
    return {
        "ok": True,
        "freeze_suspect": freeze_suspect,
        "kind": kind,
        "mean_abs_diff": mid_end,
        "mean_abs_diff_mid_end": mid_end,
        "threshold": thr,
        "duration_sec": round(float(dur), 3),
        "pairs": pairs,
        "frames": paths,
        "mid_frame": paths.get("p55"),
        "end_frame": paths.get("p92"),
    }


def gate_work_clip_no_freeze(
    video: str,
    *,
    sample_dir: str | None = None,
    allow_still: bool = False,
    threshold: float | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """
    Post-generation / approve gate: work clips must not be freeze-padded.

    allow_still: intentional still/hold shot (motion_driver=still or explicit flag).
    force: run even if AGENT_FREEZE_GATE=0.
    """
    if not force and not freeze_gate_enabled():
        return {
            "ok": True,
            "skipped": True,
            "freeze_suspect": False,
            "message": "freeze gate disabled (AGENT_FREEZE_GATE=0)",
        }
    if not video or not os.path.isfile(video):
        return {
            "ok": False,
            "error": "CLIP_MISSING",
            "freeze_suspect": None,
            "message": f"clip missing: {video}",
        }
    if sample_dir is None:
        sample_dir = os.path.join(
            os.path.dirname(os.path.abspath(video)) or ".",
            "_freeze_qa",
            os.path.splitext(os.path.basename(video))[0],
        )
    report = freeze_pad_heuristic(video, sample_dir=sample_dir, threshold=threshold)
    if not report.get("ok"):
        # Do not hard-fail generation solely because probe/PIL failed — soft skip
        return {
            "ok": True,
            "skipped": True,
            "freeze_suspect": None,
            "probe_error": report.get("error"),
            "message": f"freeze probe skipped: {report.get('error')}",
            "report": report,
        }
    if report.get("freeze_suspect") and not allow_still:
        kind = report.get("kind") or "freeze"
        return {
            "ok": False,
            "error": "FREEZE_PAD_SUSPECT",
            "freeze_suspect": True,
            "kind": kind,
            "message": (
                f"freeze/{kind} detected (mid-end diff={report.get('mean_abs_diff')}, "
                f"thr={report.get('threshold')}). "
                "Do not tpad/clone to fill duration — regen full-length motion "
                "or split the shot. Intentional still: --allow-freeze / allow_still."
            ),
            "report": report,
        }
    if report.get("freeze_suspect") and allow_still:
        return {
            "ok": True,
            "freeze_suspect": True,
            "kind": report.get("kind"),
            "allowed_still": True,
            "message": "static/freeze allowed (allow_still)",
            "report": report,
        }
    return {
        "ok": True,
        "freeze_suspect": False,
        "kind": "ok",
        "message": "motion ok",
        "report": report,
    }


def shot_allows_still_freeze(shot: dict | None, story_doc: dict | None = None) -> bool:
    """True when freeze/static is intentional for this shot."""
    if not shot:
        return False
    if shot.get("allow_freeze") or shot.get("allow_still") or shot.get("intentional_still"):
        return True
    try:
        from lib.audio_package import shot_motion_driver

        d = shot_motion_driver(shot, story_doc or {})
        if d == "still":
            return True
    except Exception:
        if str(shot.get("motion_driver") or "").lower() == "still":
            return True
    # explicit motion prompt markers
    mp = (shot.get("motion_prompt") or "").lower()
    if any(
        x in mp
        for x in (
            "intentional still",
            "freeze frame hold",
            "locked still frame",
            "no motion hold",
        )
    ):
        return True
    return False


def pass_all_required_checks(stage: str, notes_by_id: dict[str, str] | None = None) -> dict[str, dict]:
    notes_by_id = notes_by_id or {}
    return {
        cid: {"pass": True, "note": notes_by_id.get(cid, "")}
        for cid in required_checks_for(stage)
    }


def parse_fail_notes(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())
