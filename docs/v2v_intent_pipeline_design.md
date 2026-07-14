# V2V 의도 파이프라인 — motion / camera / style

- **작성**: 2026-07-15  
- **상태**: 설계 SSOT + **P0 구현 착수** (`generate_v2v.py`, true video inject)  
- **관련**: [video_delivery_and_backends.md](video_delivery_and_backends.md) · [flf2v_f2f_roadmap.md](flf2v_f2f_roadmap.md) · [ltx23_aio_pipeline_integration.md](ltx23_aio_pipeline_integration.md) · [agent_video_tooling_todo.md](agent_video_tooling_todo.md) · [dance_challenge_pipeline_design.md](dance_challenge_pipeline_design.md)

---

## 0. 한 줄

```text
레퍼 비디오(구조) + 스틸/룩(겉모습)
  → intent: camera | motion | style
  → work clip → clip_status 승인 → assemble
```

**본선 대사·립(SI2V)과 분리.**  
**컷 이음(FLF / last-frame chain)과도 분리.**

| 축 | 담당 | 이 문서 |
|----|------|---------|
| 립·발화 | `si2v` | ❌ |
| 텍스트 모션 | `i2v` | ❌ (레퍼 없을 때) |
| 원테이크 이음 | `flf2v` | ❌ → flf 로드맵 |
| **레퍼 연출** | `v2v_*` | ✅ |

---

## 1. 의도 3분 (이름 SSOT)

| intent / motion_driver | 구조 출처 | 겉모습 출처 | 대표 용도 |
|------------------------|-----------|-------------|-----------|
| **`v2v_camera`** | 카메라 플레이트 비디오 | approved keyframe / 로케 still | establishing, B-roll, 패닝·돌리 |
| **`v2v_motion`** | 액션·댄스·제스처 레퍼 | char keyframe | 무대사 바디 리타겟 |
| **`v2v_style`** | 소스 비디오 (구도·타이밍 유지) | `look_id` / style prompt | 룩 통일, 재채색 |

레거시 주의:

| 이름 | 의미 | 비고 |
|------|------|------|
| `ltx23_aio_v2v` (구 문서) | last-frame **이어 생성**에 가깝던 매핑 | 진짜 모션 레퍼 아님 |
| `ltx23_aio_v2v_true` / `generate_v2v -v` | AIO `[[P:03 Video to Video]]` + **VHS_LoadVideo** | P0 true path |

---

## 2. 입력 계약

### 2.1 공통

| 항목 | 규칙 |
|------|------|
| work 해상도 | format + work preset (I2V와 동일 2단 전략) |
| 길이 | `trim` 구간 ≈ 출력 클립 (± pad); 초과 시 hard fail 권장 |
| 승인 | `clips/work` → `clip_status` → assemble (완화 금지) |
| 대사 샷 | dialogue/vo 있으면 **기본 si2v**; v2v는 경고 또는 차단 |

### 2.2 intent별

| intent | 필수 | 권장 strength 가이드 | 프롬프트 가드 |
|--------|------|----------------------|---------------|
| camera | `-v` plate + `-i` scene/char still | 0.55–0.75 | camera only, lock identity |
| motion | `-v` action + `-i` identity still | 0.60–0.85 | match body timing, lock face/wardrobe |
| style | `-v` source (+ optional still) + look/style text | 0.25–0.50 | preserve structure, restyle look |

`strength` 는 메타·향후 노드 매핑용; P0에서는 **intent 프롬프트 프리셋 + 문서 가이드**가 1차 컨트롤.

### 2.3 에피소드 경로

```text
stories/<ep>/
  refs/video/           # 원본 레퍼
  refs/video_prep/      # (선택) work res / trim 캐시
  keyframes/approved/
  clips/work/*_v2v.mp4
```

샷 필드 (스키마 확장):

```json
{
  "shot_id": "S03",
  "motion_driver": "v2v_camera",
  "video_refs": {
    "driving": "refs/video/cam_orbit_s03.mp4",
    "trim_start_sec": 0.0,
    "trim_duration_sec": 4.0,
    "strength": 0.65,
    "intent": "camera"
  },
  "keyframe": "keyframes/approved/S03.png",
  "look_id": null
}
```

`video_refs.intent` 생략 시 `motion_driver` 접미사에서 유도 (`v2v_camera` → `camera`).

---

## 3. 도구 레이어 (공장 대칭)

```text
lib/v2v_contract.py          # 길이·trim·필수 입력
lib/ltx_aio_workflow_runner  # video_name → node 787 (VHS_LoadVideo)
scripts/generate_v2v.py      # 단발 MVP (intent 프리셋)
scripts/generate_s2v.py      # --video 전달 (AIO v2v 모드 공유)
scripts/episode_v2v.py       # 배치 (motion_driver=v2v_*)
video_backends.json          # kind=v2v backends
```

### 3.1 CLI (P0)

```bash
# 카메라 플레이트
python scripts/generate_v2v.py --intent camera \
  -v stories/EP/refs/video/cam.mp4 \
  -i stories/EP/keyframes/approved/S03.png \
  -o stories/EP/clips/work/S03_v2v.mp4 \
  --width 544 --height 960 --duration 4 --dry-run

# 모션 리타겟
python scripts/generate_v2v.py --intent motion -v dance.mp4 -i hero.png -o out.mp4

# 스타일
python scripts/generate_v2v.py --intent style -v src.mp4 -i still.png \
  -p "quiet luxury film still, soft grade" -o out.mp4 --strength 0.35
```

### 3.2 백엔드

| id | status | 설명 |
|----|--------|------|
| `ltx23_aio_v2v_true` | experimental → ready after smoke | AIO V2V + real `-v` |
| `ltx23_aio_v2v_true_audio` | experimental | V2V + audio port |
| `ltx23_aio_v2v` | ready (legacy alias) | 모드 스위치 유지; **레퍼 없이 last-frame 철학과 혼동 주의** |

1차 엔진: **LTX 2.3 AIO real UI WF**.  
2차(필요 시): Wan VACE / control-video — 모션 고정 강화.  
댄스 장르 전용 공정은 [dance_challenge_pipeline_design.md](dance_challenge_pipeline_design.md) 와 연계 (P3).

---

## 4. 에이전트 라우팅 규칙

```text
if shot has dialogue/vo needing lips:
    si2v
elif shot.motion_driver in v2v_* or video_refs.driving:
    generate_v2v / episode_v2v  (intent from driver or video_refs.intent)
elif text-only camera/action:
    i2v
elif one-take bridge:
    flf / chain_one_take
```

- `AGENT_COMFY_AUTOSTART` / `ensure_comfy_running` 기존 계약 유지.  
- 엔진 패밀리: LTX AIO → `FAMILY_LTX` (`comfy_engine_session`).  
- 워크스페이스 export: `episode_*` 와 동일 옵션 (P1).

---

## 5. 페이즈 · DoD

### P0 — 정직화 + true video path ✅

- [x] 설계 문서 (본 파일)  
- [x] runner `video_name` 주입 검증 (node 787) + force_rate/trim frames  
- [x] `generate_v2v.py` MVP + intent 프리셋  
- [x] `generate_s2v --video` / `--trim-start` 연동  
- [x] `video_backends` / schema enum / `MOTION_DRIVERS`  
- [x] dry-run 스모크 (synthetic plate + still → AIO switch API)  
- [ ] 실 GPU 스모크 클립 1개 (camera plate) — 운용 시 실행  

**DoD:** `-v` + `-i` + `--intent camera` dry-run API 빌드 OK; 실기동 시 work 클립 1개.

### P1 — 에피소드 계약

- [x] `episode_v2v.py` 배치 1차 (dialogue skip, workspace export)  
- [ ] `episode_status`: `need_video_ref` / `v2v_ready`  
- [x] `lib/v2v_contract.py` trim/duration hard fail  
- [ ] 파일럿 샷 1개 (B-roll)

### P2 — intent 프리셋 고도화

- strength → 노드 매핑 (가능 시)  
- `refs/video_prep` fps/해상도 통일  
- look bible → style 프롬프트 조립  

### P3 — 대안 엔진 · 댄스 연계

- Wan/control backend opt-in  
- dance_challenge D-티켓과 motion 레퍼 공유  

---

## 6. 하지 않음

- 대사 본선을 V2V로 대체  
- FLF를 V2V 이름 아래에 흡수  
- 클라우드 only V2V를 공장 기본값으로  
- 매 샷 기본 엔진을 V2V로  

---

## 7. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-15 | 초안. intent 3분, 공장 대칭 CLI, P0–P3, 레거시 AIO v2v 구분 |
