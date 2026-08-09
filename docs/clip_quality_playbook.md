# 영상 클립 품질 플레이북 (에이전트용)

- **작성**: 2026-08-09  
- **근거**: 웹·Reddit/Comfy 커뮤니티·Lightricks/Wan 가이드 + 공장 A/B  
- **CLI**: `python scripts/clip_quality.py`  
- **코드**: `lib/clip_quality.py`  
- **관련**: [ltx23_quality_research_and_improvement.md](ltx23_quality_research_and_improvement.md) · [wan_vs_ltx_i2v_ab_2026-07-17.md](wan_vs_ltx_i2v_ab_2026-07-17.md)

---

## 1. 2026 커뮤니티·벤더 합의 (요약)

| 주제 | 합의 | 공장 반영 |
|------|------|-----------|
| **엔진** | Wan 2.2 ≈ 비주얼 디테일 우위 · LTX 2.3 ≈ 속도·긴 클립·오디오 네이티브 | I2V 기본 **LTX AIO** · 품질 경쟁 시 Wan |
| **해상도** | work **720p** 시작 → 납품은 업스케일 | `--ltx-profile work` (1280 long edge) |
| **클립 길이** | 짧은 pure take + FLF/체인 | ≤97f (~4s@24) · `flf2v` / `chain_*` |
| **I2V 프롬프트** | **모션/카메라만** · 얼굴·의상 재서술 금지 | `clip_quality check-prompt` · Rule 7.5 |
| **Wan 블러** | steps↑ · Euler · 과한 길이↓ · high/low dual | `--profile quality` · steps 가드 |
| **LTX CFG** | ~3–3.5 (2–5) | AIO 기본 프로필 |
| **얼굴** | CU면 gen 후 face enhance · 립은 InfiniteTalk | `wan22_face_enhance` · `generate_s2v` IT |
| **후처리** | gen 구조 고정 후 ESRGAN/SeedVR2 | `upscale_recommend` · `upscale_video` |
| **롱폼 스티치** | 중간 산출 저손실 · 키프레임 계획 | last-frame extend · lossless 중간 권장 |
| **키프레임** | 나쁜 still → 좋은 I2V 없음 | shot QA before motion |

---

## 2. 에이전트 기본 루프

```text
1) still QA (open file) → approve
2) clip_quality recommend --goal work|hero
3) clip_quality check-prompt -p "..."
4) failure_note.py search "freeze OR blur OR face"
5) generate_i2v / generate_s2v  (--ltx-profile work|hero)
6) 결과 open + freeze/face 검사
7) clip_quality polish  (face CU → face enhance → upscale)
8) assemble (승인 클립만)
```

```bash
python scripts/clip_quality.py recommend --goal hero --face-cu --duration 3.5
python scripts/clip_quality.py check-prompt -p "slow push-in, soft blink, locked frame"
python scripts/generate_i2v.py -i key.png -o out.mp4 -p "slow push-in, soft blink" --ltx-profile work
python scripts/clip_quality.py probe -i out.mp4
python scripts/clip_quality.py polish -i out.mp4 -o out_1080.mp4 --goal delivery --face
```

### 에피소드 draft → work → hero (L11)

```bash
# Plan only (no Comfy)
python scripts/clip_quality.py episode-plan -e YOUR_EP --phase full

# Execute by phase
python scripts/episode_i2v.py -e YOUR_EP --ltx-profile draft --fps 24
# … open + reject bad motion …
python scripts/episode_i2v.py -e YOUR_EP --ltx-profile work --fps 24
# … clip QA + approve showcase cuts …
python scripts/episode_i2v.py -e YOUR_EP --shots S02,S05 --ltx-profile hero --fps 24
python scripts/clip_quality.py polish -i stories/YOUR_EP/clips/work/S02.mp4 \
  -o stories/YOUR_EP/clips/deliver/S02.mp4 --goal delivery --face --seedvr2
```

| 단계 | 티어 | 대상 |
|------|------|------|
| **draft** | `--ltx-profile draft` (~540) | 승인 키프레임 전샷 스카우트 |
| **work** | `work` (720p 기본) | 본선 배치 |
| **hero** | `hero` (~1080 + IC 0.55) | 쇼케이스/승인 컷만 재생성 |

---

## 3. 티어

| goal | gen | post |
|------|-----|------|
| **draft** | LTX draft / Wan preview · 짧은 프레임 | 스킵 또는 light upscale |
| **work** (기본) | LTX work 720p · ≤4–5s soft-cap | face if CU · ESRGAN 1080 납품 |
| **hero** | LTX hero · ≤4s · **2-stage IC 0.55** · 좋은 KF | face enhance + SeedVR2 opt-in |

**2-stage 메모:** LTX AIO 그래프는 항상 half-res → latent upsample → stage-2.  
별도 스위치 없음 — 프로필이 **upscale IC LoRA 강도**만 조정 (`draft 0.4` / `work 0.45` / `hero 0.55`).

---

## 4. 하지 말 것

| 금지 | 이유 |
|------|------|
| I2V에 `1girl, masterpiece, blue eyes…` | 아이덴티티는 픽셀이 담당 · 모션 붕괴 |
| 8–15초 한 방 pure I2V | 드리프트·프리즈 · 분할/FLF |
| 프리즈/정체 클립을 업스케일로 “살림” | 구조 실패는 재생성 |
| 모든 컷 InfiniteTalk | 립 히어로만 |
| 매 체인마다 고압축 H.264 | 디테일·색 붕괴 (스티치 중간은 저손실) |

---

## 5. 도구 맵

| 단계 | CLI |
|------|-----|
| 계획 | `clip_quality recommend` · `clip_quality episode-plan -e EP` |
| 프롬프트 | `clip_quality check-prompt` · `generation-prompt` skill |
| 생성 | `generate_i2v` · `generate_s2v` · `episode_i2v --ltx-profile` · `generate_flf2v` |
| 얼굴 | `generate_wan22_face_enhance` · `clip_quality polish --face` |
| 해상도 | `upscale_recommend` · `upscale_video` · `upscale_ltx_spatial` |
| 체인 | `chain_si2v_last_frame` · `chain_one_take` · `assemble_video` |
| 실패 학습 | `failure_note.py search` |
| 긴 pure I2V | 기본 soft-cap · 강제 시 `--allow-long-i2v` |

---

## 6. 참고 링크

- https://ltx.io/blog/comfyui-workflow-guide  
- Wan 2.2 I2V: motion-only prompt (Comfy / HF discuss)  
- Reddit r/comfyui: Wan blur → steps/Euler; long take → FLF + keyframes; LTX res2s / Q-tier  
- 공장: [ltx23_quality_research_and_improvement.md](ltx23_quality_research_and_improvement.md)
