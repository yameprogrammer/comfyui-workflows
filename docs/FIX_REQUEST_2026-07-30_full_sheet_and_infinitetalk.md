# 수정 요청 — character_full_sheet / InfiniteTalk (2026-07-30)

| 항목 | 내용 |
|------|------|
| **상태** | 🟢 IN PROGRESS — Phase 0–3 코드 + IT 스모크 완료; full_sheet 실측 재검증 남음 |
| **우선순위** | **P0** (실전 뮤비 파이프라인 블로커) |
| **구현 계획** | **[docs/superpowers/plans/2026-07-30-full-sheet-and-infinitetalk-fix.md](superpowers/plans/2026-07-30-full-sheet-and-infinitetalk-fix.md)** |
| **보고 세션** | GREEN LIGHTER 쇼츠 MV (`D:\뮤직비디오 작업\GREEN LIGHTER`) |
| **캐릭터** | `green_lighter_idol_v1` (cast pick krea c01 → master_front only trusted) |
| **에피소드** | `stories/green_lighter_ep01` |
| **관련 failure notes** | `FN-20260729-001` (full_sheet) · `FN-20260729-002` (InfiniteTalk) |
| **작성** | Grok agent session 2026-07-29~30 · 계획 문서화 2026-07-30 |

---

## 0. 한 줄 요약

1. **`character_full_sheet.py` 공정은 현재 프로덕션 사용 금지** — 얼굴 일관성·샷 사이즈·자동 approve가 깨짐.  
2. **`generate_s2v.py --backend infinitetalk`는 현재 큐 단계에서 실패** — `WanVideoClipVisionEncode` 노드 없음.  
3. 실전 우회: 키프레임은 `krea2_identity_edit` + master_front만; 립싱크는 **`ltx23_ia2v`** 로 진행함.

**원인 확정 요약 (2026-07-30 조사):** IT = `ComfyUI-WanVideoWrapper.disabled` + preflight 없음. FS = cast `positive_core`(head-and-shoulders) 전신 주입 + plain i2i에 size 미전달 + 고 denoise + auto_approve 파일존재=승인.  
**수정은 계획 문서 Phase 0→4 순서로 진행** (코드 미착수).

---

## 1. InfiniteTalk 파손 (SI2V)

### 1.1 증상

```text
python scripts/generate_s2v.py --backend infinitetalk \
  -i stories/green_lighter_ep01/keyframes/S01.png \
  -a <drive.wav> -o out.mp4 ...
```

```text
[ERROR] queue HTTP 400: {
  "error": {
    "type": "missing_node_type",
    "message": "Node 'WanVideoClipVisionEncode' not found. The custom node may not be installed.",
    "details": "Node ID '#4'",
    "extra_info": {
      "node_id": "4",
      "class_type": "WanVideoClipVisionEncode"
    }
  }
}
FAIL QUEUE_FAILED
```

- Comfy 엔진 패밀리 스위칭(`infinitetalk`)까지는 진입함.  
- **프롬프트 큐 등록 단계에서 실패** — 모델 가중치 문제가 아니라 **커스텀 노드 타입 부재**.

### 1.2 영향

| 영향 | 설명 |
|------|------|
| 립싱크 1급 백엔드 불가 | 카탈로그/문서상 InfiniteTalk = “토킹 립 품질 대안 ready” 로 안내됨 → **실제로는 사용 불가** |
| 에이전트 시간 낭비 | 길이 계약·슬라이스 준비 후 첫 클립에서 실패 |
| 폴백 | `ltx23_ia2v` (i2v_audio) 로 뮤비 보컬 진행 — 동작하나 IT 대비 립 정밀도 기대치 다름 |

### 1.3 재현 조건

- 서버: `http://127.0.0.1:8188` (동작 중)  
- CLI: `scripts/generate_s2v.py --backend infinitetalk`  
- 워크플로/러너: InfiniteTalk 경로 (로그에 `Wan2_1-InfiniTetalk-Single`, `WanVideo*` 계열)  
- 환경: 로컬 ComfyUI portable (`F:\ComfyUI_windows_portable` 계열)

### 1.4 추정 원인

1. **WanVideo / InfiniteTalk 관련 커스텀 노드 미설치·미로드**  
   - 최소 누락 타입: `WanVideoClipVisionEncode`  
   - 동일 계열 노드가 더 필요할 가능성 높음 (ClipVision / Multitalk / TeaCache 등).  
2. **카탈로그 “ready” 표기와 런타임 헬스체크 불일치**  
   - `docs/tool_catalog.md` / `audio_motion_production_modes.md` 는 IT를 1급 대안으로 기술.  
   - 노드 존재 여부 preflight 없음 → 에이전트가 실패 전까지 모름.

### 1.5 수정 요청 (권장 순서)

| ID | 작업 | 완료 기준 |
|----|------|-----------|
| **IT-1** | ComfyUI에 InfiniteTalk 워크플로가 요구하는 커스텀 노드 설치/복구 (`WanVideoClipVisionEncode` 등) | `GET /object_info` 에 해당 class_type 존재 |
| **IT-2** | `python scripts/generate_s2v.py --backend infinitetalk` 스모크 (짧은 wav + 얼굴 스틸, 9:16) | exit 0, mp4 생성, 입 모션 육안 OK |
| **IT-3** | `scripts/tool_health.py` 또는 s2v 시작 시 **백엔드별 required nodes** 검사 | 누락 시 즉시 `BACKEND_UNAVAILABLE` + 설치 힌트 (QUEUE 400 전에) |
| **IT-4** | 카탈로그/오디오 모드 문서: IT **when-not** = 노드 미설치 시 사용 금지; 기본 폴백 `ltx23_ia2v` 명시 | 에이전트가 IT 선택 전에 헬스 결과 반영 |
| **IT-5** | (선택) 설치 스크립트/체크리스트: 필요 모델 경로 + 노드 패키지 이름 SSOT | README 한 장으로 복구 가능 |

### 1.6 임시 운용 규칙 (수정 전까지)

```text
립싱크 본선:  --backend ltx23_ia2v  (+ --format shorts_9x16 --ltx-profile work)
InfiniteTalk: 호출하지 말 것 (노드 복구 전)
```

실측 폴백 성공 예: `green_lighter_ep01` L01–L10, preview  
`stories/green_lighter_ep01/exports/final/green_lighter_ep01_s2v_preview.mp4`

---

## 2. character_full_sheet 파손 (캐릭터 시트)

### 2.1 증상 (실측 패키지)

대상: `characters/green_lighter_idol_v1`  
입력 신뢰 레퍼: cast **krea c01** → `approved/master_front.png` (사이버 시크 얼굴)  
명령: `python scripts/character_full_sheet.py --id green_lighter_idol_v1 --run --model pro`

| 영역 | 관측 |
|------|------|
| **Identity drift** | master_full / expression / costume on-model 이 master_front 와 **다른 인물** (앞머리 아이돌 톤으로 재발명) |
| **Framing collapse** | costume_default·detail_* 가 전신/디테일이 아니라 **얼굴 CU** |
| **Detail garbage** | `costume_detail_footwear`: 얼굴 히어로 + 구석 신발 인셋 |
| **Pose hallucination** | `pose_hands_hips` → **3인 그룹**; `pose_stand_idle` 유리/왜곡 오버레이 |
| **Auto L2 lie** | 시각 QA 없이 auto-approve → `status=approved` `missing_mvp=[]` **L2 완료 위장** |
| **Turnaround** | head 일부는 상대적으로 낫지만 body turn 체형/톤 불일치 |

패키지 조치 (세션 중): `manifest.status = rejected_quality`  
소비자 메모: 프로젝트 `casting/FULL_SHEET_REJECT.md`  
Failure note: **FN-20260729-001**

### 2.2 영향

| 영향 | 설명 |
|------|------|
| 시트 공정 신뢰 붕괴 | “풀 시트 먼저” 요청 시 시간·VRAM 낭비 후 폐기 |
| 다운스트림 오염 위험 | auto-approve 된 refs를 shot_compose 가 집어쓰면 identity 오염 |
| 우회 비용 | master_front + `krea2_identity_edit` 로 키프레임 재구성 (가능했으나 시트 가치 없음) |

### 2.3 추정 원인 (파이프라인 설계)

1. **약한 identity lock** — 매 시트 i2i/expand 가 프롬프트로 얼굴을 재서술 → drift  
2. **프리셋 샷 사이즈 미강제** — full / detail 의도 vs 실제 생성 framing 불일치  
3. **휴먼 게이트 부재** — design / costume / turns / expr / pose 페이즈별 검수 없이 일괄 진행  
4. **`auto_approve` = 파일 존재 시 승인** — 시각 일관성·solitary·shot-size 검증 없음  
5. **ControlNet pose 경로** — multi-person / 장면 환각 허용  
6. **candidates=1** — 선택지 없이 한 장 채택 후 승인

### 2.4 수정 요청 (권장 순서)

| ID | 작업 | 완료 기준 |
|----|------|-----------|
| **FS-1** | **프로덕션 게이트**: full_sheet 결과를 시각 QA 없이 L2/approved 로 올리지 않음 | auto_approve 제거 또는 `--require-qa` 기본 ON |
| **FS-2** | 페이즈별 **휴먼/에이전트 게이트** (design → costume → turns → expr → pose) | 페이즈 실패 시 중단; 다음 페이즈 오염 방지 |
| **FS-3** | **Face identity lock** — master_front 2-img / FaceID / embed distance; 임계 초과 시 reject | drift 시 자동 fail + regenerate |
| **FS-4** | 프리셋 **shot-size 강제** + 사후 framing 휴리스틱 (얼굴 비율, 전신 발 포함 여부) | detail 시트에 얼굴 히어로 금지 |
| **FS-5** | **solitary hard fail** — 2인 이상 검출 시 pose/costume fail | multi-person 승인 불가 |
| **FS-6** | ControlNet pose: multi-person negative + 템플릿 검증; 실패 시 i2i 폴백 또는 skip | hands_hips 3인 재현 불가 |
| **FS-7** | 문서 SOP: “missing_mvp=[] ≠ 품질 완료”; 리뷰 그리드 육안 필수 | casting pipeline md 갱신 |
| **FS-8** | 현재 `green_lighter_idol_v1` 시트 refs 를 **production ref 로 쓰지 말 것** 플래그 유지 | status rejected_quality 유지 또는 refs quarantine |

### 2.5 임시 운용 규칙 (수정 전까지)

```text
DO NOT: character_full_sheet.py --run  for production cast lock
DO:     cast_pool → promote → master_front only
DO:     keyframes via generate_krea2_identity_edit.py -i master_front (9:16 linked aspect)
DO:     ignore / quarantine full_sheet refs under characters/<id>/refs until rewrite
```

**부수 수정 (이미 반영, 참고)**  
`generate_krea2_identity_edit.py`: UI→API 변환 시 widget 1024² 가 ResolutionSelector 링크를 덮어 **정사각 강제** 하던 버그 수정 (링크 우선). 9:16 키프레임 재생성 검증됨 (`840×1496`).

---

## 3. 공통 개선 (도구 신뢰성)

| ID | 작업 | 이유 |
|----|------|------|
| **H-1** | 백엔드/엔진 **preflight** (required nodes, models, aspect wiring) | IT·시트 모두 “돌리기 전 실패”가 맞음 |
| **H-2** | “ready / production” 라벨은 스모크 테스트 통과 후에만 | 문서 허위 광고 방지 |
| **H-3** | 시각 품질 실패는 파일 생성만으로 success 처리 금지 | full_sheet L2 위장과 동일 패턴 |
| **H-4** | failure_note 태그 표준: `missing_node`, `identity_drift`, `auto_approve`, `framing` | 검색·회귀 |

---

## 4. 증거 경로 (로컬)

| 종류 | 경로 |
|------|------|
| full_sheet reject 메모 | `characters/green_lighter_idol_v1` (manifest rejected_quality) |
| 소비자 reject 메모 | `D:\뮤직비디오 작업\GREEN LIGHTER\casting\FULL_SHEET_REJECT.md` |
| full_sheet review 예 | `characters/green_lighter_idol_v1/exports/full_sheet/review_*.png` |
| IT 실패 로그 패턴 | `WanVideoClipVisionEncode` / `QUEUE_FAILED` |
| IT failure note | `failures/notes/FN-20260729-002.json` |
| sheet failure note | `failures/notes/FN-20260729-001.json` |
| LTX 폴백 성공 프리뷰 | `stories/green_lighter_ep01/exports/final/green_lighter_ep01_s2v_preview.mp4` |
| identity edit aspect fix | `scripts/generate_krea2_identity_edit.py` (link-over-widget) |

---

## 5. 수락 기준 (이 문서 DONE 조건)

상세 체크리스트·태스크: **[구현 계획 § Acceptance](superpowers/plans/2026-07-30-full-sheet-and-infinitetalk-fix.md)**

- [x] InfiniteTalk: 스모크 s2v exit 0 + 노드 preflight (`stories/_tool_smoke/infinitetalk_smoke.mp4`)  
- [x] full_sheet: sheet-role core + size pass-through + lock/denoise + no silent auto L2 + framing gate (코드; 재생성 육안 선택)  
- [x] 카탈로그/when-not/`video_backends.json` 업데이트  
- [ ] `FN-20260729-001` / `FN-20260729-002` 에 fix ref 또는 closed 처리  
- [x] `process.md` 에 수정 이력 한 줄

---

## 6. 비범위

- GREEN LIGHTER 가창 구간 타이밍 재슬라이스 (콘텐츠 이슈, 툴 버그 아님)  
- 자막 번인 / 1080 upscale (후속 제작 단계)  
- full_sheet 전체 리라이트 외 캐릭터 LoRA 학습
