# 키프레임 제작 파이프라인 가이드

- **작성**: 2026-07-19
- **목적**: I2V 영상 생성의 품질은 키프레임 품질에 달려 있다. 여러 도구를 단계별로 조합하여 최고 품질 키프레임을 만드는 전체 워크플로
- **관련**: tool_catalog.md §2.1-§2.3 · krea2_prompt_guide.md · generation_prompt_craft.md

---

## §1. 왜 키프레임이 중요한가

- **I2V 모델의 품질 상한은 입력 키프레임이 결정**: 흐릿하거나 해부학적으로 망가진 키프레임은 아무리 좋은 I2V 모델도 살릴 수 없다.
- **좋은 키프레임 = 인물 해부 정확 + 조명 일관 + 구도 연출 의도 반영**: 세 조건을 모두 갖춰야 I2V 입력으로 합격.
- **키프레임 QA 없이 I2V 진행 금지**: `docs/image_cut_verification_gate.md` 의 QA 체크리스트를 통과한 이미지만 `keyframe_status=approved` 처리할 수 있다.

> [!IMPORTANT]
> 키프레임이 FAIL이면 I2V 클립도 FAIL이다. 업스케일 전에 해부학/구도 결함을 반드시 수정할 것.

---

## §2. 키프레임 제작 단계 (단계별 의사결정 트리)

아래 표는 초안 생성부터 납품 업스케일까지 전 단계를 커버한다. 각 단계에서 **주 도구**를 먼저 시도하고, 목적이 맞지 않으면 대안을 사용한다.

| 단계 | 도구 | 언제 | CLI 예 |
|------|------|------|--------|
| **Step 1: T2I 초안** | `generate_krea` (기본) | 항상 | `python scripts/generate_krea.py -p "Photoreal cinematic still, medium shot, golden hour..." -o draft.png --seed 42` |
| Step 1 대안 | 에이전트 자체 `generate_image` 도구 | 빠른 컨셉 검증, 외부 레퍼 스타일 시도 | 에이전트 네이티브 도구 직접 호출 (ComfyUI 불필요) |
| **Step 2: 구도/각도 조정** | `generate_qwen_angle` | 동일 인물의 다른 각도(옆/뒤/3/4각) 필요 | `python scripts/generate_qwen_angle.py -i draft.png --angle side -o side.png` |
| Step 2 대안 | `generate_viewpoint` | 하이/로우 앵글 과장 (버즈아이·웜즈아이 등) | `python scripts/generate_viewpoint.py -i draft.png --preset low_angle -o out_low.png` |
| **Step 3: 부분 편집** | `generate_qwen_edit` | 배경·소품을 텍스트 지시로 변경 | `python scripts/generate_qwen_edit.py -i draft.png --instruction "change background to rainy night street"` |
| Step 3 대안 | `generate_qwen_inpaint` | 마스크 영역만 교체 (손·얼굴 국소 수정) | `python scripts/generate_qwen_inpaint.py -i draft.png --mask mask.png` |
| **Step 4: I2I 변형** | `generate_moody_i2i` | denoise 제어로 스타일·무드 변형 | `python scripts/generate_moody_i2i.py -i edited.png --denoise 0.75` |
| Step 4 대안 | `generate_character_consistent` | 같은 인물 유지하며 장면만 변경 | `python scripts/generate_character_consistent.py --mode lock -i face.png -p "cafe table, holding cup" -o scene.png` |
| **Step 5: z-image I2V로 중간 프레임 추출** | `generate_i2v` (z-image 백엔드) | 동적 중간 표정·자세 포착, 연속 동작 중 특정 프레임 사용 | `python scripts/generate_i2v.py -i key.png --frames 25 --extract-frame 12` |
| **Step 6: 업스케일 (필수)** | `upscale_image` | 항상 납품 전 실행 (기본 배치) | `python scripts/upscale_image.py -i final.png -o final_1080.png --style photo --preset deliver_1080` |
| Step 6 히어로 | `upscale_image --backend seedvr2` | Krea2·Z-Image 생성 최종 히어로 키프레임 | `python scripts/upscale_image.py -i final.png -o hero.png --backend seedvr2 --preset deliver_1080` |

> [!TIP]
> Step 5는 선택적이다. 키프레임이 이미 연출 의도에 맞는다면 Step 4 → Step 6으로 건너뛴다.

---

## §3. 에이전트 자체 도구 활용 (Rule 8.0)

`docs/agent_native_capability_autonomy.md` Rule 8.0에 따라 에이전트는 카탈로그 도구와 자신의 네이티브 도구를 **모두** 활용해야 한다.

### 두 레인 비교

| 도구 | 강점 | 약점 | 언제 |
|------|------|------|------|
| 에이전트 자체 `generate_image` | ComfyUI 없이도 즉시 실행, 외부 스타일 레퍼 시도, 빠른 컨셉 검증 | 로컬 해상도 제어·SeedVR2 연동 불가 | 방향 검증, 무드보드, 레퍼 합성 초안 |
| ComfyUI `generate_krea` | 고품질 로컬 생성, 해상도·시드 완전 제어, SeedVR2 업스케일 연동 | ComfyUI :8188 필요 | 본선 키프레임, 납품 스틸 |

### 권장 조합 예

```text
[빠른 방향 검증]
에이전트 generate_image → 컨셉 방향 확인 (30초)

[본선 키프레임 생성]
generate_krea → 고품질 초안 (로컬 ComfyUI)

[세부 조정]
generate_qwen_edit → 배경·소품 텍스트 지시 수정

[납품 업스케일]
upscale_image --backend seedvr2 → 히어로 1080p
```

> [!NOTE]
> Rule 8.0: 에이전트는 "어떤 도구를 써야 하나요?" 라고 묻지 않는다. 인벤토리를 파악하고 자율적으로 선택해 즉시 실행한다.

---

## §4. z-image I2I 워크플로 (디테일)

포즈 맵 기반 인물 재생성이 필요할 때 사용하는 구조적 I2I 워크플로.

| 항목 | 내용 |
|------|------|
| **워크플로 파일** | `workflows/human/image_z_image_turbo_fun_union_controlnet.json` |
| **CLI** | `generate_moody_controlnet` |
| **용도** | 포즈 맵 기반 인물 재생성, 스타일 전이, 구조 보존 변형 |
| **Controlnet 타입** | 포즈 (OpenPose) · 깊이 (Depth) · 캐니 (Canny) |
| **언제 말고** | 단순 얼굴 ID 문제 → `character_consistent` 우선 |

```bash
# 포즈 기반 재생성
python scripts/generate_moody_controlnet.py \
  -i reference.png \
  --controlnet-type pose \
  --strength 0.7 \
  -o reposed.png

# 깊이 기반 구조 보존 변형
python scripts/generate_moody_controlnet.py \
  -i reference.png \
  --controlnet-type depth \
  --strength 0.6 \
  -o depth_restyle.png
```

---

## §5. Qwen 멀티앵글 생성 (디테일)

동일 인물의 앞/옆/뒤/3/4 각도를 일관성 있게 생성하는 워크플로.

| 항목 | 내용 |
|------|------|
| **스크립트** | `scripts/generate_qwen_angle.py` |
| **워크플로 파일** | `workflows/human/멀티앵글생성-qwen-image.json` |
| **용도** | 동일 인물의 앞/옆/뒤/3/4각도 생성 |
| **특징** | Angles LoRA + qwen-image-edit-2511 GGUF 사용 |
| **에피소드 레일** | `character_qwen_turns`로 캐릭터 패키지 내 턴 배치 가능 |
| **언제 말고** | 패키지 없이 한 장만 필요 → `character_consistent --mode angle` |

```bash
# 사용 가능한 각도 프리셋 확인
python scripts/generate_qwen_angle.py --list-angles

# 옆면 생성
python scripts/generate_qwen_angle.py -i front.png --angle side -o side.png

# 뒷면 생성
python scripts/generate_qwen_angle.py -i front.png --angle back -o back.png

# 3/4 각도
python scripts/generate_qwen_angle.py -i front.png --angle three_quarter -o 3q.png

# 캐릭터 패키지 내 턴 배치 (에피소드 레일)
python scripts/character_qwen_turns.py -e EP -c char_name --angles front,side,back
```

---

## §6. Illustrious 원경 및 인물 복원 정책 (얼굴/디테일)

Illustrious(애니/일러스트) 체크포인트로 작업할 때, 캐릭터가 멀리 있는 원경(Distant View) 컷이나 얼굴 이목구비가 뭉개지는 문제 컷은 다음 복원 스택 정책을 따릅니다.

### 1. 복원 스택 적용 규칙
- **원경/문제 컷 재생성 시**: Face ADetailer와 Hires(하이레스) 스택을 활성화하여 이목구비를 복원합니다.
- **기본 명령어**: `generate_illustrious_standard.py` 실행 시 `--face` 및 `--hires-post` (또는 `--hires-pre`) 옵션을 명시적으로 적용합니다.

### 2. `--eyes` (Eyes ADetailer) 실패 및 대체 우회 정책
- **현상**: 로컬 ComfyUI 환경의 `models/ultralytics/bbox/` 디렉토리에 `Eyeful_v2-Individual.pt` (또는 `Eyeful_v2-Paired.pt`) 모델 파일이 존재하지 않아, `--eyes` 옵션 호출 시 에러가 발생하며 프로세스가 실패합니다.
- **우회 정책**: 
  - 원경 얼굴 복원 및 이목구비 재생성 시 **`--eyes` 대신 `--face` 옵션을 적용**합니다.
  - 얼굴 디테일러(`face_yolov8m.pt` 모델은 정상 가용)와 **Hires 스택(`--hires-post`)의 조합**만으로도 원경 애니 캐릭터의 눈과 얼굴 전반을 충분히 복원할 수 있습니다.
  - 에이전트는 작업 시 존재하지 않는 eyes 모델을 찾아 에러를 내지 말고, 즉시 `--face --hires-post` 조합을 적용하도록 이 정책을 고정합니다.

---

## §7. 키프레임 QA 체크리스트

참고: `docs/image_cut_verification_gate.md`

모든 항목이 ☑ 상태여야 `keyframe_status=approved` 처리할 수 있다.

| 항목 | 체크 |
|------|------|
| 해부학 (발, 손, 얼굴) 정상 | ☐ |
| 구도 연출 의도 일치 | ☐ |
| 조명 방향 일관 | ☐ |
| 인물 ID 일관 (레퍼 대비) | ☐ |
| 소품/배경 디테일 정확 | ☐ |
| I2V 입력으로 적합한 해상도 | ☐ |
| 업스케일 완료 | ☐ |

> [!WARNING]
> QA 없이 파일을 열지도 않고 approved 처리하는 것은 하드 금지 (exit 23). `shot_qa_record.py --verdict pass` 는 파일을 실제 열어 확인한 후에만 호출한다.

---

## §8. 실패 노트 연동

키프레임 생성 전후로 실패 노트를 검색/등록하여 반복 실수를 방지한다.

```bash
# 생성 전: 관련 실패 패턴 검색
python scripts/failure_note.py search "anatomy OR framing OR keyframe quality"
python scripts/failure_note.py list --limit 10

# 생성 후 FAIL 또는 유저 거부 시
python scripts/failure_note.py add \
  --stage keyframe \
  --tags anatomy_hands,framing_fail \
  --symptom "손가락 6개, 구도 좌편향" \
  --cause "denoise 너무 낮아 원본 구조 과다 보존" \
  --fix "denoise 0.85 이상으로 재생성 후 qwen_inpaint으로 손 수정" \
  --prevention "손 포함 샷은 denoise 0.8+ 또는 inpaint 후처리 예약" \
  --severity high \
  --agent <agent_id> \
  -e EP -s S0x
```

관련 문서: `docs/failure_notes_system.md` · 저장 폴더: `failures/`

---

## §9. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-19 | 초안: 키프레임 제작 전체 파이프라인 가이드 / §6 Illustrious 원경 인물 복원 정책 추가 |
