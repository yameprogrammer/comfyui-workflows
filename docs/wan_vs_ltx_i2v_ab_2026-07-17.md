# A/B: Wan 2.2 vs LTX 2.3 I2V (same keyframe / work tier)

- **Date**: 2026-07-17  
- **Source still**: `stories/sonagi_mv_v3/keyframes/S01.png` (960×544)  
- **Prompt**: gentle continuous motion, soft rain on glass, natural micro body sway…  
- **Seed**: 42  

## Outputs

| Backend | File | Measured |
|---------|------|----------|
| **wan22** | `F:\generated_videos\ab_wan_vs_ltx\S01_wan22.mp4` | 960×544 · 16fps · 33f · ~2s · steps=6 · ~78s · ~2.7Mbps |
| **ltx23_aio_i2v** | `F:\generated_videos\ab_wan_vs_ltx\S01_ltx23.mp4` | 960×576* · 24fps · 49f · ~2s · steps=20 · ~112s · ~6.6Mbps |

\*LTX AIO snapped aspect slightly (960×576 vs requested 960×544); same work tier.

Compare sheets: `compare_f00_wan_vs_ltx.png`, `compare_f08_wan_vs_ltx.png` in the same folder.

## Visual verdict

| Axis | Wan 2.2 GGUF+lightx2v | LTX 2.3 AIO |
|------|----------------------|-------------|
| Still sharpness | Good / slightly plastic | Slightly softer, more filmic |
| Motion | Micro-wobble, near-still | Clear pose/gaze/hand change |
| Continuity feel | Freeze-adjacent | Living take |
| Bitrate / encode | Low | Higher |
| **Overall work quality** | Fallback | **Winner** |

## Policy locked

```text
default I2V   = ltx23_aio_i2v
default FLF   = ltx23_aio_flf   (generate_i2v --last / motion_driver=flf2v)
default SI2V  = ltx23_aio (existing)
wan22 / wan22_flf = explicit fallback only
```

See `video_backends.json` → `i2v_quality_policy`.
