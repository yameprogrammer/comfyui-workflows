"""Compile edit_timeline.v1 to an ffmpeg argv (no subprocess)."""

from __future__ import annotations

import os
from typing import Any

from lib.edit_look import compose_key, compose_look, look_filter
from lib.edit_motion import compose_motion
from lib.edit_timeline import play_dur, resolve_media_path, timeline_duration, validate_timeline
from lib.ffmpeg_util import probe_duration

VO_ROLES = ("vo", "vocal", "dialogue", "speech", "host", "voice")


def _ff_expr(expr: str) -> str:
    return expr.replace(",", "\\,")


def _overlay_xy(m: dict) -> tuple[str, str]:
    dx, dy = float(m["dx"]), float(m["dy"])
    move = float(m["move"])
    if move <= 0 or (abs(dx) < 0.5 and abs(dy) < 0.5):
        return "0", "0"
    s, e = float(m["start"]), float(m["end"])
    din = max(0.04, move)
    dout = max(0.04, move * 0.75)
    intro = f"max(0,1-min(1,max(0,t-{s:.4f})/{din:.4f}))"
    outro = f"max(0,1-min(1,max(0,{e:.4f}-t)/{dout:.4f}))"
    if str(m.get("ease") or "linear") == "out_cubic":
        intro = f"(1-pow(1-({intro})\\,3))"
        outro = f"(1-pow(1-({outro})\\,3))"
    mix = f"max({intro},{outro})"
    x = "0" if abs(dx) < 0.5 else _ff_expr(f"{dx:.2f}*{mix}")
    y = "0" if abs(dy) < 0.5 else _ff_expr(f"{dy:.2f}*{mix}")
    return x, y


def _ff_path(path: str) -> str:
    return os.path.abspath(path).replace("\\", "/")


def _norm_chain(
    label: str,
    clip: dict,
    w: int,
    h: int,
    fps: int,
    *,
    plate_input: int | None = None,
) -> tuple[list[str], str]:
    inn = float(clip.get("in") or 0.0)
    out = float(clip["out"])
    speed = float(clip.get("speed") or 1.0) or 1.0
    fit = (clip.get("transform") or {}).get("fit") or "cover"
    parts = [f"[{label}]trim=start={inn}:end={out},setpts=PTS-STARTPTS"]
    if abs(speed - 1.0) > 1e-6:
        parts.append(f"setpts=PTS/{speed}")
    if fit == "stretch":
        parts.append(f"scale={w}:{h}")
    elif fit == "contain":
        parts.append(
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black"
        )
    else:
        parts.append(
            f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
        )
    parts.append(f"fps={fps}")
    key = compose_key(clip.get("key"))
    if not key:
        parts.append("format=yuv420p,setsar=1")
        return [",".join(parts) + f"[{label}n]"], f"{label}n"
    hx = key["color"]
    bg = key["background"]
    keyed = (
        f"{','.join(parts)},format=gbrp,"
        f"chromakey={hx}:{key['similarity']:.3f}:{key['blend']:.3f},"
        f"format=yuva420p[{label}k]"
    )
    if plate_input is not None:
        plate = (
            f"[{plate_input}:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},fps={fps},format=yuv420p,setsar=1[{label}bg]"
        )
    elif str(bg).startswith("0x"):
        dur = play_dur(clip)
        plate = (
            f"color=c={bg}:s={w}x{h}:r={fps}:d={max(dur, 0.1):.4f},format=yuv420p[{label}bg]"
        )
    else:
        parts.append("format=yuv420p,setsar=1")
        return [",".join(parts) + f"[{label}n]"], f"{label}n"
    over = f"[{label}bg][{label}k]overlay=0:0,format=yuv420p,setsar=1[{label}n]"
    return [keyed, plate, over], f"{label}n"


def compile_ffmpeg(
    tl: dict,
    output_path: str,
    *,
    timeline_path: str | None = None,
) -> dict[str, Any]:
    tl = validate_timeline(tl)
    clips = list(tl["clips"])
    if not clips:
        raise ValueError("timeline has no clips")
    w, h, fps = int(tl["width"]), int(tl["height"]), int(tl["fps"])
    inputs: list[str] = []
    resolved: list[str] = []
    for c in clips:
        p = resolve_media_path(str(c["path"]), timeline_path=timeline_path)
        if not os.path.isfile(p):
            raise FileNotFoundError(p)
        inputs.extend(["-i", p])
        resolved.append(p)

    plate_input_by_clip: dict[int, int] = {}
    for i, c in enumerate(clips):
        ck = compose_key(c.get("key"))
        bg = (ck or {}).get("background")
        if ck and bg and os.path.isfile(str(bg)):
            plate_input_by_clip[i] = len(inputs) // 2
            inputs.extend(["-i", str(bg)])

    overlay_files: list[tuple[int, dict, str]] = []
    for o in tl.get("overlays") or []:
        op = o.get("path")
        if not op:
            continue
        rp = resolve_media_path(str(op), timeline_path=timeline_path)
        if not os.path.isfile(rp):
            raise FileNotFoundError(rp)
        idx = len(inputs) // 2
        inputs.extend(["-i", rp])
        overlay_files.append((idx, o, rp))

    audio_files: list[tuple[int, dict, str]] = []
    for a in tl.get("audio") or []:
        ap = resolve_media_path(str(a["path"]), timeline_path=timeline_path)
        if not os.path.isfile(ap):
            raise FileNotFoundError(ap)
        idx = len(inputs) // 2
        inputs.extend(["-i", ap])
        audio_files.append((idx, a, ap))

    fc: list[str] = []
    clip_labs: list[str] = []
    for i, c in enumerate(clips):
        chains, lab = _norm_chain(
            str(i), c, w, h, fps, plate_input=plate_input_by_clip.get(i)
        )
        fc.extend(chains)
        clip_labs.append(lab)

    xf_map = {}
    for t in tl.get("transitions") or []:
        if t.get("type") == "crossfade":
            xf_map[(t["from"], t["to"])] = float(t["dur"])

    if len(clips) == 1:
        last_v = clip_labs[0]
    else:
        prev = clip_labs[0]
        acc = play_dur(clips[0])
        for i in range(1, len(clips)):
            pair = (clips[i - 1]["id"], clips[i]["id"])
            d = xf_map.get(pair, 0.0)
            out_lab = f"x{i}"
            nxt = clip_labs[i]
            if d > 0:
                off = max(0.0, acc - d)
                fc.append(
                    f"[{prev}][{nxt}]xfade=transition=fade:duration={d}:offset={off:.4f}[{out_lab}]"
                )
                acc = acc + play_dur(clips[i]) - d
            else:
                fc.append(f"[{prev}][{nxt}]concat=n=2:v=1:a=0[{out_lab}]")
                acc = acc + play_dur(clips[i])
            prev = out_lab
        last_v = prev

    look = compose_look(tl.get("look"))
    grade = look_filter(look)
    if grade:
        fc.append(f"[{last_v}]{grade}[vgrade]")
        last_v = "vgrade"

    for idx, o, _rp in overlay_files:
        m = compose_motion(o, width=w, height=h)
        s, e = m["start"], m["end"]
        fi, fo, move = m["fade_in"], m["fade_out"], m["move"]
        z0, z1 = m["scale_from"], m["scale_to"]
        need_scale = abs(z0 - z1) > 0.01 and move > 0
        need_prep = fi > 0 or fo > 0 or need_scale
        ov_src = f"{idx}:v"
        if need_prep:
            chain = f"[{idx}:v]format=rgba,fps={fps},loop=loop=-1:size=1:start=0"
            if need_scale:
                z = (
                    f"if(lt(t,{s:.4f}),{z0:.4f},"
                    f"if(lt(t,{s + move:.4f}),{z0:.4f}+{(z1 - z0):.4f}*min(1,(t-{s:.4f})/{move:.4f}),{z1:.4f}))"
                )
                chain += f",scale=w='iw*({_ff_expr(z)})':h=-1:eval=frame"
                if o.get("ox") is None:
                    chain += f",pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black@0"
            if fi > 0:
                chain += f",fade=t=in:st={s:.4f}:d={fi:.3f}:alpha=1"
            if fo > 0:
                chain += f",fade=t=out:st={max(s, e - fo):.4f}:d={fo:.3f}:alpha=1"
            chain += f"[ovs{idx}]"
            fc.append(chain)
            ov_src = f"ovs{idx}"
        mx, my = _overlay_xy(m)
        if o.get("ox") is not None:
            bx, by = float(o["ox"]), float(o.get("oy") or 0)
            gw, gh = o.get("ow"), o.get("oh")
            if need_scale and gw and gh:
                x = _ff_expr(f"{bx:.1f}-(w-{int(gw)})/2")
                y = _ff_expr(f"{by:.1f}-(h-{int(gh)})/2")
            else:
                x, y = f"{bx:.1f}", f"{by:.1f}"
            if mx != "0":
                x = f"{x}+{mx}"
            if my != "0":
                y = f"{y}+{my}"
        else:
            x, y = mx, my
        out_lab = f"ov{idx}"
        fc.append(
            f"[{last_v}][{ov_src}]overlay={x}:{y}:enable='between(t,{s:.4f},{e:.4f})'[{out_lab}]"
        )
        last_v = out_lab

    dur = timeline_duration(tl)
    extra_in: list[str] = []
    if audio_files:
        a_labs = []
        vo_js: list[int] = []
        bed_js: list[int] = []
        for j, (idx, a, ap) in enumerate(audio_files):
            inn = float(a.get("in") or 0.0)
            out = a.get("out")
            start = float(a.get("start") or 0.0)
            vol = float(a.get("volume") or 1.0)
            fade_in = max(0.0, float(a.get("fade_in") or 0.0))
            fade_out = max(0.0, float(a.get("fade_out") or 0.0))
            delay_ms = int(round(start * 1000))
            chain = f"[{idx}:a]atrim=start={inn}"
            if out is not None:
                chain += f":end={float(out)}"
            chain += ",asetpts=PTS-STARTPTS"
            if delay_ms > 0:
                chain += f",adelay={delay_ms}:all=1"
            if fade_in > 0:
                chain += f",afade=t=in:st=0:d={fade_in:.3f}"
            if fade_out > 0:
                seg = (float(out) - inn) if out is not None else probe_duration(ap)
                if seg and seg > 0:
                    chain += f",afade=t=out:st={max(0.0, float(seg) - fade_out):.3f}:d={fade_out:.3f}"
            chain += f",volume={vol}[a{j}]"
            fc.append(chain)
            a_labs.append(f"[a{j}]")
            role = str(a.get("role") or "").lower()
            if a.get("duck") is not None:
                bed_js.append(j)
            elif role in VO_ROLES:
                vo_js.append(j)
        mix_labs = []
        if bed_js and vo_js:
            key = vo_js[0]
            for j in range(len(a_labs)):
                if j in bed_js:
                    duck = float(audio_files[j][1].get("duck") or 0.28)
                    duck = min(1.0, max(0.05, duck))
                    fc.append(
                        f"[a{j}][a{key}]sidechaincompress=threshold=0.03:ratio=8:"
                        f"attack=40:release=280:mix=1:level_sc=1[a{j}d]"
                    )
                    # keep a floor so ducked bed is audible at ~duck
                    fc.append(f"[a{j}d]volume={duck + (1.0 - duck) * 0.15:.3f}[a{j}m]")
                    mix_labs.append(f"[a{j}m]")
                else:
                    mix_labs.append(f"[a{j}]")
        else:
            mix_labs = list(a_labs)
        if len(mix_labs) == 1:
            last_a = mix_labs[0].strip("[]")
        else:
            ins = "".join(mix_labs)
            fc.append(f"{ins}amix=inputs={len(mix_labs)}:normalize=0[amix]")
            last_a = "amix"
        fc.append(f"[{last_a}]apad,atrim=0:{dur:.4f}[aout]")
        map_a = ["-map", "[aout]"]
    else:
        extra_in = [
            "-f",
            "lavfi",
            "-t",
            f"{max(dur, 0.1):.4f}",
            "-i",
            "anullsrc=r=48000:cl=stereo",
        ]
        silent_idx = len(resolved) + len(overlay_files) + len(audio_files)
        map_a = ["-map", f"{silent_idx}:a"]

    graph = ";".join(fc)
    argv = [
        *inputs,
        *extra_in,
        "-filter_complex",
        graph,
        "-map",
        f"[{last_v}]",
        *map_a,
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-t",
        f"{dur:.4f}",
        os.path.abspath(output_path),
    ]
    return {
        "argv": argv,
        "graph": graph,
        "duration": dur,
        "inputs": resolved,
    }
