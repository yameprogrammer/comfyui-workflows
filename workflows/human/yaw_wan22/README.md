# YAW Wan 2.2 MoE v0.50

**Civitai:** [Yet Another Workflow easy T2V+I2V](https://civitai.red/models/2008892/yet-another-workflow-easy-t2v-i2v-yaw-wan-22)

| 파일 | 역할 |
|------|------|
| `yetAnotherWorkflowEasyT2vI2v_v050Moe.json` | 실 UI SSOT |
| `AGENT_GUIDE.md` | 목적 · 스위치 맵 · GGUF · CLI |
| `CAPABILITIES.json` | 기계 가독 기능/모델 |

```bash
python scripts/generate_yaw_wan22.py --list-features
python scripts/generate_yaw_wan22.py --task t2v -p "..." -o out.mp4
```

Agent default: **GGUF Q4** (pack fp16 is huge). Real UI + group modes only.
