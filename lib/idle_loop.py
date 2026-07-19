"""
Idle motion + loop helpers (MOTION shelf).

Modes:
  idle     — subtle life I2V (motion preset idle), single play
  pingpong — I2V then reverse append (always seamless for looping players)
  roundtrip — I2V then FLF last→first still, concat (forward-ish loop)

Research note: true diffusion seamless loops are hard; pingpong is the robust default loop.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from typing import Any

from lib.comfy_client import fail_result, ok_result, utc_now_iso, write_meta
from lib.ffmpeg_util import concat_videos, run_ffmpeg
from lib.motion_presets import compose_motion_prompt, resolve_motion_preset_id

MODES = ("idle", "pingpong", "roundtrip")

# Default micro-motion preset for idle life
DEFAULT_MOTION_PRESET = "idle"


def extract_last_frame(video_path: str, image_path: str, *, timeout_sec: float = 120) -> dict[str, Any]:
    parent = os.path.dirname(os.path.abspath(image_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    # -sseof seeks near end; one frame
    r = run_ffmpeg(
        [
            "-sseof",
            "-0.15",
            "-i",
            video_path,
            "-frames:v",
            "1",
            "-q:v",
            "2",
            image_path,
        ],
        timeout_sec=timeout_sec,
    )
    if r.get("ok") and os.path.isfile(image_path):
        r["output_path"] = os.path.abspath(image_path)
    elif r.get("ok"):
        return fail_result(error="FRAME_EXTRACT_EMPTY", message=image_path)
    return r


def reverse_video(video_path: str, output_path: str, *, timeout_sec: float = 600) -> dict[str, Any]:
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    r = run_ffmpeg(
        [
            "-i",
            video_path,
            "-vf",
            "reverse",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            output_path,
        ],
        timeout_sec=timeout_sec,
    )
    if r.get("ok"):
        r["output_path"] = os.path.abspath(output_path)
    return r


def _run_i2v_idle(
    *,
    input_image: str,
    output_path: str,
    motion_preset: str,
    extra: str,
    frames: int,
    fps: int,
    seed: int | None,
    backend: str | None,
    format_id: str | None,
    work_preset: str | None,
    profile: str,
    timeout_sec: int,
    meta_out: str | None,
) -> dict[str, Any]:
    from generate_i2v import DEFAULT_NEGATIVE, generate_i2v

    pid = resolve_motion_preset_id(motion_preset) or DEFAULT_MOTION_PRESET
    prompt, neg_extra = compose_motion_prompt(pid, extra)
    negative = DEFAULT_NEGATIVE
    if neg_extra:
        negative = f"{negative}, {neg_extra}"
    return generate_i2v(
        input_image_path=input_image,
        prompt_text=prompt,
        negative_text=negative,
        output_filename=output_path,
        num_frames=frames,
        frame_rate=fps,
        seed=seed,
        backend=backend,
        format_id=format_id,
        preset=work_preset,
        profile=profile,
        meta_out=meta_out,
        timeout_sec=timeout_sec,
    )


def run_idle_loop(
    *,
    input_image: str,
    output_path: str,
    mode: str = "pingpong",
    motion_preset: str = DEFAULT_MOTION_PRESET,
    extra: str = "",
    frames: int = 49,
    fps: int = 16,
    seed: int | None = None,
    backend: str | None = None,
    format_id: str | None = None,
    work_preset: str | None = None,
    profile: str = "deliver",
    timeout_sec: int = 1800,
    meta_out: str | None = None,
    work_dir: str | None = None,
    flf_backend: str = "ltx23_aio_flf",
    flf_frames: int | None = None,
) -> dict[str, Any]:
    """
    Generate idle-like motion and optionally make a loopable file.

    mode:
      idle      — single forward clip (preset idle by default)
      pingpong  — forward + reverse (seamless for loop players)
      roundtrip — forward + FLF return to start still, then concat
    """
    if not os.path.isfile(input_image):
        return fail_result(error="SOURCE_MISSING", message=input_image)

    mode = (mode or "pingpong").lower().strip()
    if mode not in MODES:
        return fail_result(error="BAD_MODE", message=f"mode must be one of {MODES}")

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    tmp = work_dir or tempfile.mkdtemp(prefix="idle_loop_")
    os.makedirs(tmp, exist_ok=True)
    stages: list[dict[str, Any]] = []

    forward_path = os.path.join(tmp, "forward.mp4")
    print(f"[idle_loop] mode={mode} motion_preset={motion_preset} → I2V forward")
    r0 = _run_i2v_idle(
        input_image=input_image,
        output_path=forward_path,
        motion_preset=motion_preset,
        extra=extra,
        frames=frames,
        fps=fps,
        seed=seed,
        backend=backend,
        format_id=format_id,
        work_preset=work_preset,
        profile=profile,
        timeout_sec=timeout_sec,
        meta_out=os.path.join(tmp, "forward.meta.json"),
    )
    stages.append({"name": "i2v_forward", "ok": bool(r0.get("ok")), "error": r0.get("error")})
    if not r0.get("ok"):
        return fail_result(
            error=r0.get("error") or "I2V_FAILED",
            message=r0.get("message"),
            stages=stages,
        )

    final = forward_path
    loop_kind = "single_play"

    if mode == "idle":
        shutil.copy2(forward_path, output_path)
        final = os.path.abspath(output_path)
        loop_kind = "idle_single"

    elif mode == "pingpong":
        rev = os.path.join(tmp, "reverse.mp4")
        print("[idle_loop] reverse forward clip (pingpong)")
        rr = reverse_video(forward_path, rev, timeout_sec=min(600, timeout_sec))
        stages.append({"name": "reverse", "ok": bool(rr.get("ok")), "error": rr.get("error")})
        if not rr.get("ok"):
            return fail_result(
                error=rr.get("error") or "REVERSE_FAILED",
                message=rr.get("message"),
                stages=stages,
            )
        print("[idle_loop] concat forward + reverse")
        rc = concat_videos(
            [forward_path, rev],
            output_path,
            reencode=True,
            fps=fps,
            timeout_sec=timeout_sec,
        )
        stages.append({"name": "concat_pingpong", "ok": bool(rc.get("ok")), "error": rc.get("error")})
        if not rc.get("ok"):
            return fail_result(
                error=rc.get("error") or "CONCAT_FAILED",
                message=rc.get("message"),
                stages=stages,
            )
        final = os.path.abspath(output_path)
        loop_kind = "pingpong_seamless"

    elif mode == "roundtrip":
        last_png = os.path.join(tmp, "last_frame.png")
        print("[idle_loop] extract last frame")
        re = extract_last_frame(forward_path, last_png)
        stages.append({"name": "extract_last", "ok": bool(re.get("ok")), "error": re.get("error")})
        if not re.get("ok"):
            return fail_result(
                error=re.get("error") or "EXTRACT_FAILED",
                message=re.get("message"),
                stages=stages,
            )
        back_path = os.path.join(tmp, "return.mp4")
        from generate_i2v import DEFAULT_NEGATIVE, generate_i2v

        # Return to start still with gentle reverse-ish motion language
        back_prompt, neg_x = compose_motion_prompt(
            "idle",
            "smooth return to original pose and framing, continuous natural motion",
        )
        neg = DEFAULT_NEGATIVE
        if neg_x:
            neg = f"{neg}, {neg_x}"
        ff = int(flf_frames if flf_frames is not None else max(25, frames // 2))
        if ff % 2 == 0:
            ff += 1
        print(f"[idle_loop] FLF return last→start frames={ff} backend={flf_backend}")
        rb = generate_i2v(
            input_image_path=last_png,
            end_image_path=os.path.abspath(input_image),
            prompt_text=back_prompt,
            negative_text=neg,
            output_filename=back_path,
            num_frames=ff,
            frame_rate=fps,
            seed=(seed + 1) if seed is not None else None,
            backend=flf_backend,
            format_id=format_id,
            preset=work_preset,
            profile=profile,
            meta_out=os.path.join(tmp, "return.meta.json"),
            timeout_sec=timeout_sec,
        )
        stages.append({"name": "flf_return", "ok": bool(rb.get("ok")), "error": rb.get("error")})
        if not rb.get("ok"):
            return fail_result(
                error=rb.get("error") or "FLF_FAILED",
                message=rb.get("message")
                or "roundtrip FLF failed; try --mode pingpong",
                stages=stages,
            )
        print("[idle_loop] concat forward + return")
        rc = concat_videos(
            [forward_path, back_path],
            output_path,
            reencode=True,
            fps=fps,
            timeout_sec=timeout_sec,
        )
        stages.append({"name": "concat_roundtrip", "ok": bool(rc.get("ok")), "error": rc.get("error")})
        if not rc.get("ok"):
            return fail_result(
                error=rc.get("error") or "CONCAT_FAILED",
                message=rc.get("message"),
                stages=stages,
            )
        final = os.path.abspath(output_path)
        loop_kind = "roundtrip_forward"

    meta = {
        "tool": "generate_idle_loop",
        "mode": mode,
        "loop_kind": loop_kind,
        "motion_preset": resolve_motion_preset_id(motion_preset) or motion_preset,
        "source_image": os.path.abspath(input_image),
        "output_path": final,
        "frames": frames,
        "fps": fps,
        "seed": seed,
        "stages": stages,
        "work_dir": os.path.abspath(tmp),
        "created_at": utc_now_iso(),
        "note": (
            "pingpong = reverse append (reliable loop). "
            "roundtrip = FLF back to start (forward loop, may show seam). "
            "idle = single play micro-motion."
        ),
    }
    mpath = meta_out
    if mpath is None and output_path:
        mpath = os.path.splitext(output_path)[0] + ".json"
    if mpath:
        write_meta(mpath, meta)

    return ok_result(
        output_path=final,
        meta=meta,
        meta_path=mpath,
        mode=mode,
        loop_kind=loop_kind,
        stages=stages,
        seed=seed,
    )
