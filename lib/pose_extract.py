"""
Extract pose stick videos from RGB footage via ComfyUI-WanAnimatePreprocess.

Uses YOLO + ViTPose (detection folder) → DrawViTPose stick render → mp4.
Output is a black-background pose plate suitable for Fun Control / Animate.
"""

from __future__ import annotations

import os
import shutil
import time
import uuid
from typing import Any

from lib.comfy_client import (
    DEFAULT_SERVER,
    download_image,
    ensure_comfy_running,
    fail_result,
    get_comfy_input_dir,
    get_comfy_output_dir,
    history_execution_error,
    ok_result,
    queue_prompt,
    utc_now_iso,
    wait_for_history,
    write_meta,
)
from lib.ffmpeg_util import probe_duration, run_ffmpeg

DEFAULT_VITPOSE = "vitpose-l-wholebody.onnx"
DEFAULT_YOLO = "yolov10m.onnx"
DEFAULT_ONNX_DEVICE = "CUDAExecutionProvider"


def _extract_video_from_history(history_entry: dict) -> tuple[str, str, str]:
    outputs = history_entry.get("outputs") or {}
    for _nid, node_out in outputs.items():
        for key in ("gifs", "videos", "images"):
            items = node_out.get(key)
            if not items:
                continue
            if not isinstance(items, list):
                items = [items]
            for item in items:
                if isinstance(item, dict) and item.get("filename"):
                    return (
                        item["filename"],
                        item.get("subfolder", "") or "",
                        item.get("type", "output") or "output",
                    )
    raise FileNotFoundError(f"No video in outputs: {list(outputs.keys())}")


def stage_video_to_comfy_input(
    video_path: str,
    *,
    server: str = DEFAULT_SERVER,
    name: str | None = None,
) -> str:
    """Copy local video into Comfy input dir; return basename for LoadVideo."""
    if not os.path.isfile(video_path):
        raise FileNotFoundError(video_path)
    inp = get_comfy_input_dir(server)
    os.makedirs(inp, exist_ok=True)
    base = name or f"pose_src_{uuid.uuid4().hex[:10]}{os.path.splitext(video_path)[1]}"
    if not base.lower().endswith((".mp4", ".webm", ".mov", ".mkv")):
        base = base + ".mp4"
    dest = os.path.join(inp, base)
    shutil.copy2(video_path, dest)
    return base


def trim_video_hook(
    video_path: str,
    output_path: str,
    *,
    start_sec: float = 0.0,
    duration_sec: float | None = None,
    width: int | None = None,
    height: int | None = None,
    fps: float | None = None,
    timeout_sec: float = 600,
) -> dict[str, Any]:
    """Optional pre-trim/re-encode before pose extract (keeps silent audio)."""
    if not os.path.isfile(video_path):
        return fail_result(error="VIDEO_MISSING", message=video_path)
    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    start = max(0.0, float(start_sec))
    args: list[str] = [
        "-y",
        "-ss",
        str(start),
        "-i",
        video_path,
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=44100",
    ]
    if duration_sec is not None and float(duration_sec) > 0:
        args.extend(["-t", str(float(duration_sec))])
    vf_parts: list[str] = []
    if width and height:
        vf_parts.append(
            f"scale={int(width)}:{int(height)}:force_original_aspect_ratio=decrease,"
            f"pad={int(width)}:{int(height)}:(ow-iw)/2:(oh-ih)/2"
        )
    if fps and float(fps) > 0:
        vf_parts.append(f"fps={float(fps)}")
    if vf_parts:
        args.extend(["-vf", ",".join(vf_parts)])
    args.extend(
        [
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            output_path,
        ]
    )
    r = run_ffmpeg(args, timeout_sec=timeout_sec)
    if r.get("ok") and os.path.isfile(output_path):
        r["output_path"] = os.path.abspath(output_path)
    return r


def build_pose_extract_api(
    *,
    video_basename: str,
    width: int = 544,
    height: int = 960,
    fps: float = 16.0,
    filename_prefix: str = "pose/extract",
    vitpose_model: str = DEFAULT_VITPOSE,
    yolo_model: str = DEFAULT_YOLO,
    onnx_device: str = DEFAULT_ONNX_DEVICE,
    retarget_padding: int = 16,
    body_stick_width: int = -1,
    hand_stick_width: int = -1,
    draw_head: bool = True,
    retarget_image_basename: str | None = None,
) -> dict[str, Any]:
    """Comfy API graph: LoadVideo → ViTPose → DrawViTPose → SaveVideo.

    Optional ``retarget_image_basename`` maps dance pose onto target body
    proportions (PoseAndFaceDetection.retarget_image) — helps cross-cast dance.
    """
    pose_inputs: dict[str, Any] = {
        "model": ["3", 0],
        "images": ["2", 0],
        "width": int(width),
        "height": int(height),
    }
    api: dict[str, Any] = {
        "1": {
            "class_type": "LoadVideo",
            "inputs": {"file": video_basename},
        },
        "2": {
            "class_type": "GetVideoComponents",
            "inputs": {"video": ["1", 0]},
        },
        "3": {
            "class_type": "OnnxDetectionModelLoader",
            "inputs": {
                "vitpose_model": vitpose_model,
                "yolo_model": yolo_model,
                "onnx_device": onnx_device,
            },
        },
        "5": {
            "class_type": "DrawViTPose",
            "inputs": {
                "pose_data": ["4", 0],
                "width": int(width),
                "height": int(height),
                "retarget_padding": int(retarget_padding),
                "body_stick_width": int(body_stick_width),
                "hand_stick_width": int(hand_stick_width),
                "draw_head": bool(draw_head),
            },
        },
        "6": {
            "class_type": "CreateVideo",
            "inputs": {"images": ["5", 0], "fps": float(fps)},
        },
        "7": {
            "class_type": "SaveVideo",
            "inputs": {
                "video": ["6", 0],
                "filename_prefix": filename_prefix,
                "format": "auto",
                "codec": "auto",
            },
        },
    }
    if retarget_image_basename:
        api["8"] = {
            "class_type": "LoadImage",
            "inputs": {"image": retarget_image_basename},
        }
        pose_inputs["retarget_image"] = ["8", 0]
    api["4"] = {
        "class_type": "PoseAndFaceDetection",
        "inputs": pose_inputs,
    }
    return api


def extract_pose_video(
    video_path: str,
    output_path: str,
    *,
    width: int = 544,
    height: int = 960,
    fps: float = 16.0,
    start_sec: float = 0.0,
    duration_sec: float | None = None,
    vitpose_model: str = DEFAULT_VITPOSE,
    yolo_model: str = DEFAULT_YOLO,
    onnx_device: str = DEFAULT_ONNX_DEVICE,
    server_address: str = DEFAULT_SERVER,
    timeout_sec: int = 1800,
    meta_out: str | None = None,
    dry_run: bool = False,
    work_dir: str | None = None,
    filename_prefix: str | None = None,
    retarget_image: str | None = None,
) -> dict[str, Any]:
    """
    RGB dance/ref video → pose stick mp4.

    Optional start/duration re-encode first (recommended for long shorts).
    Optional ``retarget_image``: target character still for body proportion retarget.
    """
    if not os.path.isfile(video_path):
        return fail_result(error="VIDEO_MISSING", message=video_path)
    if retarget_image and not os.path.isfile(retarget_image):
        return fail_result(error="RETARGET_MISSING", message=retarget_image)

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    stages: list[dict[str, Any]] = []
    drive = os.path.abspath(video_path)
    td = work_dir
    if (start_sec and float(start_sec) > 0) or (
        duration_sec is not None and float(duration_sec) > 0
    ):
        import tempfile

        td = work_dir or tempfile.mkdtemp(prefix="pose_extract_")
        os.makedirs(td, exist_ok=True)
        trimmed = os.path.join(td, "hook.mp4")
        tr = trim_video_hook(
            drive,
            trimmed,
            start_sec=float(start_sec or 0.0),
            duration_sec=float(duration_sec) if duration_sec is not None else None,
            width=width,
            height=height,
            fps=fps,
        )
        stages.append({"name": "trim", "ok": bool(tr.get("ok")), "error": tr.get("error")})
        if not tr.get("ok"):
            return fail_result(
                error=tr.get("error") or "TRIM_FAILED",
                message=tr.get("message"),
                stages=stages,
            )
        drive = trimmed

    prefix = filename_prefix or f"pose/extract_{uuid.uuid4().hex[:8]}"
    api = build_pose_extract_api(
        video_basename="__placeholder__",
        width=width,
        height=height,
        fps=fps,
        filename_prefix=prefix,
        vitpose_model=vitpose_model,
        yolo_model=yolo_model,
        onnx_device=onnx_device,
        retarget_image_basename="__retarget__" if retarget_image else None,
    )

    meta: dict[str, Any] = {
        "tool": "extract_pose_video",
        "created_at": utc_now_iso(),
        "source_video": os.path.abspath(video_path),
        "drive_video": drive,
        "retarget_image": os.path.abspath(retarget_image) if retarget_image else None,
        "width": width,
        "height": height,
        "fps": fps,
        "start_sec": float(start_sec or 0.0),
        "duration_sec": duration_sec,
        "vitpose_model": vitpose_model,
        "yolo_model": yolo_model,
        "onnx_device": onnx_device,
        "stages": stages,
    }

    if dry_run:
        meta["dry_run"] = True
        meta["api_nodes"] = list(api.keys())
        if meta_out:
            write_meta(meta_out, meta)
        return ok_result(
            dry_run=True,
            output_path=None,
            meta_path=meta_out,
            message="pose extract dry-run (no Comfy queue)",
            **meta,
        )

    ensure_comfy_running(server_address)
    try:
        basename = stage_video_to_comfy_input(drive, server=server_address)
    except Exception as e:
        return fail_result(error="STAGE_FAILED", message=str(e), stages=stages)

    api["1"]["inputs"]["file"] = basename
    meta["comfy_input_name"] = basename
    stages.append({"name": "stage_input", "ok": True, "file": basename})

    if retarget_image:
        try:
            # stage still as image for LoadImage
            inp = get_comfy_input_dir(server_address)
            os.makedirs(inp, exist_ok=True)
            rname = f"pose_retarget_{uuid.uuid4().hex[:10]}{os.path.splitext(retarget_image)[1] or '.png'}"
            shutil.copy2(retarget_image, os.path.join(inp, rname))
            if "8" in api:
                api["8"]["inputs"]["image"] = rname
            meta["comfy_retarget_name"] = rname
            stages.append({"name": "stage_retarget", "ok": True, "file": rname})
        except Exception as e:
            return fail_result(error="RETARGET_STAGE_FAILED", message=str(e), stages=stages)

    t0 = time.time()
    try:
        prompt_id = queue_prompt(server_address, api)
    except Exception as e:
        return fail_result(error="QUEUE_FAILED", message=str(e), stages=stages, **meta)

    meta["prompt_id"] = prompt_id
    try:
        hist = wait_for_history(server_address, prompt_id, timeout_sec=timeout_sec)
    except Exception as e:
        return fail_result(
            error="WAIT_FAILED",
            message=str(e),
            prompt_id=prompt_id,
            stages=stages,
            **meta,
        )

    err = history_execution_error(hist)
    if err:
        return fail_result(
            error="EXECUTION_ERROR",
            message=err,
            prompt_id=prompt_id,
            stages=stages,
            **meta,
        )

    try:
        fn, sub, typ = _extract_video_from_history(hist)
    except Exception as e:
        return fail_result(
            error="EXTRACT_FAILED",
            message=str(e),
            prompt_id=prompt_id,
            stages=stages,
            **meta,
        )

    comfy_out = get_comfy_output_dir(server_address)
    src = os.path.join(comfy_out, sub, fn) if sub else os.path.join(comfy_out, fn)
    try:
        if os.path.isfile(src):
            shutil.copy2(src, output_path)
        else:
            download_image(server_address, fn, sub, typ, output_path)
    except Exception as e:
        return fail_result(
            error="COPY_FAILED",
            message=str(e),
            prompt_id=prompt_id,
            comfy_filename=fn,
            stages=stages,
            **meta,
        )

    elapsed = round(time.time() - t0, 1)
    meta.update(
        {
            "ok": True,
            "output_path": os.path.abspath(output_path),
            "elapsed_sec": elapsed,
            "comfy_filename": fn,
            "subfolder": sub,
            "source_duration_sec": probe_duration(video_path),
        }
    )
    stages.append({"name": "comfy_pose", "ok": True, "elapsed_sec": elapsed})
    meta["stages"] = stages
    if meta_out:
        write_meta(meta_out, meta)
        meta["meta_path"] = meta_out
    return ok_result(**meta)
