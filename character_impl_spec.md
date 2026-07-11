# 🛠️ 캐릭터 시트 시스템 — 구현 착수 스펙 (Implementation Spec)

- **작성일**: 2026-07-11
- **상태**: **P0~P2 코드 + 파일럿 E2E 완료** / **용도 프로필(profile) 스펙 추가·구현 대기**
- **상위 설계**: [character_sheet_system_design.md](character_sheet_system_design.md)
- **영상 로드맵**: [video_pipeline_roadmap.md](video_pipeline_roadmap.md)
- **프리셋 데이터**: [characters/sheet_presets.json](characters/sheet_presets.json)
- **용도 프로필 SSOT**: [characters/profiles.json](characters/profiles.json)
- **패키지 템플릿**: [characters/_template/](characters/_template/)
- **파일럿 브리프**: [characters/pilots/mina_park_v1_brief.md](characters/pilots/mina_park_v1_brief.md)

---

## 0. 활성 트랙 선언 (에이전트 필수 준수)

```text
현재 활성 트랙: CHARACTER_L2_SOFT_FACTORY
완료: P0 문서/템플릿, P1 CLI 재현성, P2 create/expand/approve, 파일럿 mina_park_v1 E2E
다음: P2.5 용도 프로필(video_ref | artbook) 구현 → P4 ControlNet turnaround / P7 shot
동결: L3 LoRA 학습, I2V 본구현은 별 트랙 (스파이크만 허용)
```

| 결정 항목 | 확정 값 (파일럿 기본) | 비고 |
|----------|----------------------|------|
| 매체 | `cinematic_photoreal` (실사) | Moody Pro 기본 |
| 일관성 레벨 | **L2** (I2I + approved refs) | L3는 후속 |
| 검수 | **사람 approve 필수** (`approved/` 승격) | 자동 QA는 후순위 |
| **기본 용도 프로필** | **`video_ref`** | 영상 일관성 첨부용 |
| 선택 용도 프로필 | `artbook` | 고해상·풀시트·(후속) 업스케일/그리드 |
| 파일럿 포맷 | 세로 쇼츠 준비용 캐릭터 팩 | 시트 기본 1:1, 전신은 세로 허용 |
| 기본 모델 | `pro` | real/wild 선택 가능 |

---

## 1. 착수 가능 판정 체크리스트

아래가 모두 있으면 P1 코딩 시작 가능.

| # | 항목 | 상태 |
|---|------|------|
| 1 | 폴더 규약 + `_template/` | ✅ 본 커밋 |
| 2 | `bible` / `manifest` 스키마 | ✅ `characters/schemas/` |
| 3 | 시트 프리셋 (prompt/denoise/cfg/path) | ✅ `sheet_presets.json` |
| 4 | 파일 명명 규칙 표 | ✅ 본 문서 §3 |
| 5 | 기본 해상도/시드/재시도 정책 | ✅ 본 문서 §4 |
| 6 | 기존 CLI P1 패치 스펙 | ✅ 본 문서 §5 |
| 7 | 신규 CLI 입출력 계약 | ✅ 본 문서 §6 |
| 8 | 프롬프트 조립 알고리즘 | ✅ 본 문서 §7 |
| 9 | 에러 코드 / 종료 코드 | ✅ 본 문서 §8 |
| 10 | 수동 런북 (L1 검증) | ✅ 본 문서 §9 |
| 11 | 파일럿 캐릭터 브리프 | ✅ `pilots/mina_park_v1_brief.md` |
| 12 | 구현 작업 티켓 순서 | ✅ 본 문서 §10 |
| 13 | 용도 프로필 스펙 (`video_ref` / `artbook`) | ✅ 스펙·`profiles.json` / ⬜ CLI 연동 |

---

## 1.5 용도 프로필 (Purpose Profiles) — 스펙

### 1.5.1 목적

캐릭터 시트 도구를 **한 가지 해상도·MVP 세트에 고정하지 않고**, 사용 목적에 따라 설정을 고른다.

| 프로필 ID | 이름 | 목적 |
|-----------|------|------|
| **`video_ref`** | 영상 레퍼용 | 샷 키프레임·I2I·I2V에 붙이는 **일관성 첨부 팩** (기본) |
| **`artbook`** | 아트북용 | **결과물 자체**가 되는 고디테일 프레젠테이션/인쇄 지향 시트 |

핵심 원칙:

```text
동일 캐릭터 패키지 (bible / identity / approved 공유)
        +
프로필별: 해상도 · MVP 시트 목록 · candidates · export · (후속) upscale/grid
        +
Comfy 엔진 WF는 복제하지 않음 (T2I / I2I / ControlNet 공용)
```

- 인쇄 아트북용이면 해상도·시트 커버리지·후처리가 더 높아야 함.
- 영상 레퍼용이면 1024급·얇은 MVP·속도가 우선 (현재 파일럿과 정합).

### 1.5.2 SSOT 파일

| 파일 | 역할 |
|------|------|
| [characters/profiles.json](characters/profiles.json) | 프로필 정의 **SSOT** |
| [characters/sheet_presets.json](characters/sheet_presets.json) | 시트별 prompt/denoise (프로필 무관 엔진 레시피) |
| `bible.active_profile` | 패키지가 마지막으로 사용한 프로필 |
| `bible.exports` / `exports/<profile>/` | 프로필별 export 상태·경로 (구현 시) |

### 1.5.3 프로필 비교 (요약)

| 항목 | `video_ref` (기본) | `artbook` |
|------|--------------------|-----------|
| 품질 우선순위 | speed_consistency | detail_print |
| master face | 1024×1024 | 1536×1536 |
| full body / turn / costume | 1024×1536 | 1536×2304 |
| MVP 그룹 | master + expression | master + turnaround + expression + costume + pose |
| candidates (sheet 기본) | 2 | 4 |
| upscale | off | on (scale 2, Phase 2) |
| grid export | off | on (Phase 2) |
| export 경로 | `exports/video_ref/` | `exports/artbook/` |

상세 수치·alias 목록은 **`profiles.json`이 항상 우선**한다.

### 1.5.4 CLI 계약 (구현 대상 — Ticket P2.5)

```bash
# 기본 = video_ref
python character_create.py --id hero_v1 --name "Hero" --profile video_ref ...

# 아트북 모드 (고해상·풀 MVP)
python character_create.py --id hero_v1 --name "Hero" --profile artbook --force ...
python character_expand_sheets.py --id hero_v1 --profile artbook --sheets all_mvp
```

| 인자 | 적용 CLI | 기본 | 동작 |
|------|----------|------|------|
| `--profile` | create, expand, (후속) export | `video_ref` | `profiles.json` 로드 후 size/mvp/candidates 적용 |
| (파생) `all_mvp` | expand | | 프로필의 `mvp_sheet_groups` / `all_mvp_key` 기준 |

**구현 규칙**

1. width/height는 프로필 `sizes`에서 시트 타입별로 선택해 T2I/I2I에 전달 (I2I는 입력 해상도 제약이 있으면 문서화).
2. `missing_mvp` 계산은 프로필별 `mvp_aliases` 사용 (video_ref는 turn/costume 없어도 L2-video 완료 가능).
3. artbook 고해상 재생성 시 **character_id를 바꾸지 않음** — 같은 패키지에 export만 분리.
4. 워크플로우 JSON을 프로필마다 복제하지 말 것.

### 1.5.5 bible / manifest 확장 필드

```json
{
  "active_profile": "video_ref",
  "exports": {
    "video_ref": {
      "status": "approved",
      "updated_at": "ISO-8601",
      "path": "exports/video_ref"
    },
    "artbook": {
      "status": "draft",
      "updated_at": null,
      "path": "exports/artbook"
    }
  }
}
```

`manifest.level`은 당분간 공유 L1/L2/L3를 유지하고, 프로필별 완료는 `exports.<profile>.status`로 구분한다.

### 1.5.6 단계적 구현 (과설계 방지)

| Phase | 내용 | 상태 |
|-------|------|------|
| **Spec** | 본 절 + `profiles.json` | ✅ |
| **P2.5a** | `--profile` 로드, 기본 `video_ref`, MVP alias/candidates/size 적용 | ⬜ |
| **P2.5b** | create/expand가 프로필 size를 generate_* 에 전달 | ⬜ |
| **P2.5c** | `exports/<profile>/` 복사·bible.exports 갱신 | ⬜ |
| **P2.5d** | artbook upscale + grid export | ⬜ 후순위 (P3와 연계 가능) |

---

## 2. 디렉터리 및 경로 규약

### 2.1 저장소 루트 기준

```text
agent_custom/
  characters/
    _template/                 # 새 캐릭터 복사 원본
    schemas/
      bible.schema.json
      manifest.schema.json
    sheet_presets.json         # 시트 prompt/denoise SSOT
    profiles.json              # 용도 프로필 SSOT (video_ref | artbook)
    pilots/
      mina_park_v1_brief.md
    <character_id>/            # 실제 캐릭터 패키지
      exports/video_ref/       # P2.5
      exports/artbook/         # P2.5
  character_create.py          # P2 (+ P2.5 --profile)
  character_expand_sheets.py   # P2 (+ P2.5 --profile)
  character_approve.py         # P2
  shot_with_character.py       # P7 신규
  generate_moody.py            # P1 패치
  generate_moody_i2i.py        # P1 패치
  lib/
    comfy_client.py
    prompt_assembly.py
    character_package.py
```

### 2.2 캐릭터 패키지 필수 파일

생성 직후(`status=draft`) 최소:

```text
characters/<id>/
  bible.json              # active_profile, exports (P2.5)
  manifest.json
  prompts/positive_core.txt
  prompts/negative_core.txt
  refs/master/          # 후보 이미지
  refs/turnaround/
  refs/expression/
  refs/costume/
  refs/head/
  refs/pose/
  approved/             # 비어 있음 허용
  meta/                 # 생성 메타 JSON 저장
  versions/CHANGELOG.md
```

### 2.3 절대 경로 (환경)

| 용도 | 경로 |
|------|------|
| 워크스페이스 | `F:\ComfyUI_workflows\agent_custom\` |
| ComfyUI 서버 | `127.0.0.1:8188` |
| ComfyUI input | `F:\ComfyUI_windows_portable\ComfyUI\input\` |
| 기본 이미지 출력 (레거시) | `F:\generated_images\` |
| 캐릭터 패키지 출력 | `F:\ComfyUI_workflows\agent_custom\characters\<id>\` |

스크립트는 **캐릭터 관련 출력은 패키지 폴더 안**에 저장한다. 레거시 `F:\generated_images`는 단독 T2I/I2I 호출 시에만 사용.

---

## 3. 파일 명명 규칙

### 3.1 패턴

```text
{character_id}__{sheet}__{view}__{variant}__s{seed}__c{candidate}.png
```

| 토큰 | 규칙 | 예 |
|------|------|-----|
| `character_id` | 소문자, 숫자, `_` 만. 공백 금지 | `mina_park_v1` |
| `sheet` | 아래 enum | `master`, `turnaround`, `expression`, `costume`, `pose`, `head` |
| `view` | 아래 enum | `front`, `qf`, `side`, `back`, `upper`, `full` |
| `variant` | 의미 태그. 소문자+`_` | `neutral`, `joy`, `default_outfit`, `cand` |
| `seed` | 정수 | `s884212` |
| `candidate` | 후보 번호 01부터 | `c01` |

### 3.2 sheet / view enum

**sheet**

| 값 | 의미 |
|----|------|
| `master` | 히어로 마스터 |
| `turnaround` | 전신 회전 |
| `head` | 머리/얼굴 회전 |
| `expression` | 표정 |
| `costume` | 의상 변형 |
| `pose` | 포즈/액션 |
| `shot` | 스토리 키프레임 (P7) |

**view**

| 값 | 의미 |
|----|------|
| `front` | 정면 |
| `qf` | 3/4 (three-quarter front) |
| `side` | 측면 프로필 |
| `back` | 후면 |
| `upper` | 상반신 |
| `full` | 전신 |
| `close` | 얼굴 클로즈업 |
| `na` | 뷰 비해당 |

### 3.3 approved 승격 시 이름

approved는 **짧고 안정적인 별칭**을 쓴다 (시드/후보 번호 제거).

```text
approved/master_front.png
approved/master_full.png
approved/turn_front.png
approved/turn_qf.png
approved/turn_side.png
approved/turn_back.png
approved/expr_neutral.png
approved/expr_joy.png
approved/expr_sad.png
approved/expr_angry.png
approved/expr_surprise.png
approved/expr_think.png
approved/costume_default.png
approved/costume_alt1.png
```

`character_approve.py`가 `refs/...` → `approved/{alias}.png` 복사 + `manifest.json` / `bible.sheet_index` 갱신.

### 3.4 메타 JSON

이미지와 1:1:

```text
meta/{same_basename}.json
```

예:  
`refs/master/mina_park_v1__master__front__neutral__s884212__c01.png`  
→ `meta/mina_park_v1__master__front__neutral__s884212__c01.json`

메타 필드 (필수):

```json
{
  "character_id": "mina_park_v1",
  "sheet": "master",
  "view": "front",
  "variant": "neutral",
  "seed": 884212,
  "candidate": 1,
  "model": "pro",
  "workflow": "T2I-moody",
  "mode": "t2i",
  "prompt": "...",
  "negative": "...",
  "denoise": null,
  "cfg": null,
  "steps": null,
  "sampler": null,
  "scheduler": null,
  "source_image": null,
  "created_at": "ISO-8601",
  "comfy_prompt_id": "...",
  "output_path": "..."
}
```

---

## 4. 생성 기본값 (Defaults)

| 키 | 값 | 적용 |
|----|-----|------|
| `default_model` | `pro` | 전 시트 |
| `t2i_width` / `t2i_height` | 프로필 `sizes` 따름 | 기본 프로필 `video_ref` → face 1024×1024 |
| `sheet_width/height` | 프로필 `sizes` 따름 | artbook은 더 큼; I2I는 입력 제약 시 문서화 |
| `candidates_master` | 프로필 기본 (video 4 / artbook 4) | create |
| `candidates_sheet` | 프로필 기본 (video 2 / artbook 4) | expand 항목당 |
| `default_profile` | `video_ref` | `profiles.json` |
| `i2i_cfg_default` | `3.5` | 시트 I2I |
| `i2i_sampler` | `euler` | 고정 (Rule 3) |
| `i2i_scheduler` | `normal` | 고정 |
| `retry_max` | `2` | 네트워크/큐 실패 시 |
| `poll_interval_sec` | `1.0` | Comfy history |
| `timeout_sec` | `600` | 단일 생성 |
| `require_human_approve` | `true` | L2 |

### Denoise 밴드 (기존 검증값 — 코드 상수와 동기)

| 밴드 ID | denoise | 용도 |
|---------|---------|------|
| `local_edit` | `0.70` | 소품/미세 |
| `atmosphere` | `0.78` | 조명/표정 약변화 |
| `expression` | `0.80` | 표정 시트 |
| `turn_mild` | `0.82` | 각도 소폭 |
| `turn_hard` | `0.85` | 측면/후면/큰 포즈 |
| `costume` | `0.84` | 의상 교체 |
| `rebuild` | `0.90` | 거의 재생성 (검수 필수, 기본 프리셋 비사용) |

상세 항목별 값은 **`characters/sheet_presets.json`이 SSOT(Single Source of Truth)**.

---

## 5. P1 — 기존 CLI 패치 스펙

### 5.1 `generate_moody.py` 추가 인자

| 인자 | 타입 | 기본 | 설명 |
|------|------|------|------|
| `--seed` | int | `None` → 랜덤 | 고정 시드 |
| `--prompt-file` | path | None | 파일이 있으면 `--prompt`보다 우선 |
| `--negative` | str | `""` | 네거티브 (워크플로에 노드 없으면 로그만/메타 저장) |
| `--negative-file` | path | None | 네거티브 파일 |
| `--meta-out` | path | None | 메타 JSON 경로. 미지정 시 output stem + `.json` (output 있을 때) |
| `--steps` | int | None | 지정 시 KSampler steps 덮어쓰기 |
| `--cfg` | float | None | T2I CFG 덮어쓰기 |
| `--width` | int | None | latent width |
| `--height` | int | None | latent height |

**함수 시그니처 변경 (권장):**

```python
def generate_image(
    prompt_text: str,
    model_type: str = "real",
    output_filename: str | None = None,
    seed: int | None = None,
    negative_text: str = "",
    steps: int | None = None,
    cfg: float | None = None,
    width: int | None = None,
    height: int | None = None,
    meta_out: str | None = None,
) -> dict | bool:
```

- 성공 시 **dict** 반환 권장: `{ok, output_path, seed, prompt_id, meta_path}`  
- 하위 호환: 최소 `True/False` 유지해도 되나, 캐릭터 CLI는 dict를 기대.

**시드:**

```python
new_seed = seed if seed is not None else random.randint(1, 1125899906842624)
```

**네거티브:**  
현재 T2I-moody에 전용 negative 노드가 없을 수 있다. P1에서는:

1. 메타에 `negative` 저장 (필수)
2. 워크플로에 negative 입력이 발견되면 주입
3. 없으면 warning 로그 후 스킵

### 5.2 `generate_moody_i2i.py` 추가 인자

| 인자 | 타입 | 기본 | 설명 |
|------|------|------|------|
| `--seed` | int | None | 고정 시드 |
| `--prompt-file` | path | None | 프롬프트 파일 |
| `--negative` / `--negative-file` | | | 동상 |
| `--meta-out` | path | None | 메타 JSON |
| `--core-prefix-file` | path | None | 앞에 붙일 고정 외형 블록 |
| `--core-suffix-file` | path | None | 뒤에 붙일 블록 |

**프롬프트 조립 (I2I):**

```text
final_prompt = join_nonempty([
  read(core_prefix_file),   # positive_core
  prompt_text,              # 시트/샷 지시
  read(core_suffix_file)    # 선택
], separator=", ")
```

**반환:** T2I와 동일한 dict 형태.

### 5.3 공용 유틸 (P1에서 `lib/` 추출 권장)

| 함수 | 역할 |
|------|------|
| `load_text(path) -> str` | 파일 읽기 |
| `assemble_prompt(core, instruction, suffix=None) -> str` | 조립 |
| `write_meta(path, data) -> None` | 메타 저장 |
| `queue_and_wait(server, api_prompt, timeout) -> history` | 폴링 |
| `download_output(server, history, dest) -> path` | 저장 |

기존 `convert_ui_to_api`는 **공유 모듈로 옮기되 동작 변경 금지** (Rule 2/3).

### 5.4 P1 완료 기준 (DoD)

- [x] `--seed` / `--prompt-file` / `--negative-file` / `--meta-out` CLI 추가
- [x] I2I `--core-prefix-file` / `--core-suffix-file` + 최종 프롬프트 메타 기록
- [x] 성공 시 dict 반환 (`ok`, `output_path`, `seed`, `prompt_id`, `meta_path`)
- [x] `lib/comfy_client.py` 등 공용 모듈 추출
- [x] `process.md` 이력 추가
- [ ] 실서버에서 `--seed` 재현·이미지 생성 스모크 (Comfy 가동 후)

---

## 6. P2 — 신규 CLI 계약

모든 캐릭터 CLI는 워크스페이스 루트에서 실행:

```bash
cd F:\ComfyUI_workflows\agent_custom
python character_create.py ...
```

### 6.1 `character_create.py`

**목적:** 패키지 폴더 생성 + bible draft + master 후보 T2I N장.

```bash
python character_create.py \
  --id mina_park_v1 \
  --name "Mina Park" \
  --model pro \
  --candidates 4 \
  --seed-base 1000 \
  --from-brief characters/pilots/mina_park_v1_brief.md \
  # 또는 직접:
  --appearance-prompt "..." \
  --positive-core-file path \
  --negative-core-file path
```

| 인자 | 필수 | 설명 |
|------|------|------|
| `--id` | Y | character_id |
| `--name` | Y | display_name |
| `--model` | N | default pro |
| `--candidates` | N | default 4 |
| `--seed-base` | N | 있으면 seed_base+i 사용, 없으면 랜덤 |
| `--appearance-prompt` | N* | 마스터용 풀 프롬프트 |
| `--from-brief` | N* | 브리프 마크다운/JSON에서 필드 로드 (구현 시 간단 파서 또는 강제 bible 입력) |
| `--force` | N | 기존 id 덮어쓰기 |

\* appearance-prompt 또는 brief/core 중 하나 필요.

**동작 순서:**

1. `characters/<id>` 존재 시 에러 (unless `--force`)
2. `_template/` 복사
3. `bible.json` 채움 (`status=draft`, appearance/prompts)
4. `positive_core.txt` / `negative_core.txt` 기록
5. preset `master.front_upper` (및 옵션 full)으로 T2I × candidates
6. 출력을 `refs/master/` + `meta/`
7. `manifest.json` assets 목록 갱신
8. stdout에 후보 경로 리스트 출력
9. exit 0

**성공 stdout 예:**

```text
OK character_id=mina_park_v1
masters=4
  characters/mina_park_v1/refs/master/...c01.png
  ...
NEXT: 후보를 고른 뒤 character_approve.py 로 master_front 승격
```

### 6.2 `character_expand_sheets.py`

**목적:** approved master(또는 지정 ref)에서 시트 배치 생성.

```bash
python character_expand_sheets.py \
  --id mina_park_v1 \
  --sheets turnaround,expression,costume \
  --source approved/master_front.png \
  --model pro \
  --candidates 2
```

| 인자 | 필수 | 설명 |
|------|------|------|
| `--id` | Y | |
| `--sheets` | Y | 콤마 목록 또는 `all_mvp` |
| `--source` | N | 기본: `bible.identity.primary_ref` 또는 `approved/master_front.png` |
| `--model` | N | |
| `--candidates` | N | 항목당 후보 수 default 2 |
| `--presets-file` | N | default `characters/sheet_presets.json` |
| `--only` | N | 프리셋 id 필터 예: `turnaround.side,expression.joy` |
| `--dry-run` | N | 프롬프트/경로만 출력 |

**`all_mvp` 확장 목록:**  
`sheet_presets.json` → `mvp_sheet_groups` 참고.

**동작:**

1. 패키지·source 존재 확인 (source 없으면 exit 20)
2. 각 preset에 대해:
   - prompt = assemble(positive_core, preset.instruction)
   - I2I(source, denoise, cfg, seed)
   - `refs/{sheet}/` 저장 + meta
3. manifest 갱신
4. 실패 항목은 로그 후 계속, 종료 시 요약. 전부 실패면 exit 30

### 6.3 `character_approve.py`

```bash
python character_approve.py \
  --id mina_park_v1 \
  --from refs/master/....c02.png \
  --as master_front
```

| 인자 | 필수 | 설명 |
|------|------|------|
| `--id` | Y | |
| `--from` | Y | 패키지 상대 또는 절대 경로 |
| `--as` | Y | approved 별칭 키 (확장자 없이). 맵은 아래 |
| `--set-primary` | N | primary_ref로 설정 |
| `--status` | N | bible.status 변경 예: `approved` |

**`--as` 허용 키:** §3.3 파일명에서 `.png` 제거한 것  
(`master_front`, `turn_side`, `expr_joy`, …)

**동작:**

1. 소스 이미지 존재 확인
2. `approved/{as}.png` 로 복사
3. manifest `approved` 섹션 갱신
4. bible `sheet_index` / `identity.primary_ref` 갱신 (해당 시)
5. CHANGELOG 한 줄 append

### 6.4 `shot_with_character.py` (P7 — 계약만 선정의, 구현은 P2 후)

```bash
python shot_with_character.py \
  --id mina_park_v1 \
  --shot "medium shot, rainy night street, holding umbrella" \
  --ref approved/master_front.png \
  --denoise 0.78 \
  --out characters/mina_park_v1/refs/shots/ep01_s03.png
```

규칙:
- `bible.status` 가 `approved` 가 아니면 경고 (또는 `--allow-draft`)
- 프롬프트 = positive_core + shot + (optional shot template)
- I2I with ref
- 메타 저장

---

## 7. 프롬프트 조립 알고리즘

### 7.1 공식

```text
positive = join_comma([
  positive_core,          # 고정 외형 (짧고 반복 가능)
  preset.instruction,     # 시트/샷 지시
  preset.style_lock,      # "neutral gray background, studio softbox" 등
  quality_tags            # 전역 품질 태그 (presets.global)
])

negative = join_comma([
  negative_core,
  preset.negative_extra,
  global_negative
])
```

`join_comma`: 빈 문자열 제거 후 `", "` 연결. 중복 구문 제거는 선택.

### 7.2 positive_core 작성 규칙

- **길이:** 40~120 단어 권장
- **포함:** 나이대, 얼굴, 헤어, 체형, 기본 의상, 고정 특징(점 등), 스타일(cinematic photo)
- **제외:** 특정 장면, 감정, 극단 포즈 (시트 instruction에 맡김)
- **트리거:** L3 이전에는 `character_id`를 이름으로  squish 가능 (`Mina Park`)

### 7.3 negative_core 최소 세트

```text
identity shift, different person, face morph, extra fingers, deformed hands,
mutated face, bad anatomy, blurry face, watermark, text, logo, cropped head,
duplicate face, age change, glasses (unless character wears glasses)
```

캐릭터 forbidden 목록을 bible에서 읽어 추가.

---

## 8. 에러 코드 및 로깅

| Exit | 코드 이름 | 상황 |
|------|-----------|------|
| 0 | OK | 성공 |
| 2 | USAGE | 인자 오류 |
| 10 | PACKAGE_EXISTS | create 시 이미 존재 |
| 11 | PACKAGE_MISSING | id 폴더 없음 |
| 12 | TEMPLATE_MISSING | `_template` 없음 |
| 20 | SOURCE_MISSING | I2I 소스 없음 |
| 21 | PRESET_MISSING | 프리셋 id 없음 |
| 22 | APPROVE_ALIAS_INVALID | --as 키 무효 |
| 30 | ALL_GENERATIONS_FAILED | 전부 실패 |
| 31 | PARTIAL_FAILURE | 일부 실패 (expand는 설정에 따라 0 또는 31) |
| 40 | COMFY_UNREACHABLE | 서버 연결 실패 |
| 41 | COMFY_TIMEOUT | 타임아웃 |
| 42 | COMFY_NO_OUTPUT | 출력 이미지 없음 |

**권장:** expand 기본은 부분 성공 시 **exit 0** + stderr에 `WARN partial=...`.  
`--strict` 시 부분 실패 exit 31.

로그 포맷:

```text
[INFO] ...
[WARN] ...
[ERROR] code=40 message=...
```

---

## 9. 수동 런북 (문서/도구 검증용 L1)

코딩 전·후로 사람이 검증할 때:

### 9.1 Comfy 준비
1. ComfyUI `127.0.0.1:8188` 실행
2. Moody 모델 3종 로드 가능 상태

### 9.2 마스터 1장 (P1 패치 후)

```bash
python generate_moody.py ^
  -m pro ^
  --seed 10001 ^
  --prompt-file characters/pilots/samples/mina_positive_master.txt ^
  -o characters/mina_park_v1/refs/master/manual_master.png
```

### 9.3 파생 1장

```bash
python generate_moody_i2i.py ^
  -i characters/mina_park_v1/refs/master/manual_master.png ^
  -m pro -d 0.85 -c 3.5 ^
  --core-prefix-file characters/mina_park_v1/prompts/positive_core.txt ^
  -p "same person, full body side profile view, standing, neutral gray background, even studio lighting" ^
  -o characters/mina_park_v1/refs/turnaround/manual_side.png
```

### 9.4 검수
- 동일 인물로 보이는지
- 메타 JSON seed/prompt 기록 여부

---

## 10. 구현 티켓 순서 (에이전트용)

### Ticket P1-A — T2I seed/meta/prompt-file
- [x] `generate_moody.py`

### Ticket P1-B — I2I seed/meta/core-prefix
- [x] `generate_moody_i2i.py`

### Ticket P1-C — `lib/comfy_client.py` 추출
- [x] 완료

### Ticket P2-A — `character_package.py`
- [x] `lib/character_package.py`

### Ticket P2-B — `character_create.py`
- [x] 완료

### Ticket P2-C — `character_expand_sheets.py`
- [x] 완료

### Ticket P2-D — `character_approve.py`
- [x] 완료

### Ticket P2-E — 파일럿 E2E (Comfy 필요)
1. [x] create mina_park_v1 (`--from-brief-samples`)
2. [x] master approve (`s10002__c02`)
3. [x] expand all_mvp (12/12)
4. [x] MVP alias approve 전부
5. [x] `bible.status=approved` / `level=L2`
6. [x] process.md + `characters/mina_park_v1/PILOT_NOTES.md`
7. [ ] 품질 개선: ControlNet turnaround / full-body master (후속)

### Ticket P2.5 — 용도 프로필 (`video_ref` | `artbook`)
- [x] 스펙 문서 §1.5 + [characters/profiles.json](characters/profiles.json)
- [x] **P2.5a** `lib/profiles.py` + `--profile` (create/expand/approve)
- [x] **P2.5b** create: 프로필 size → T2I width/height (I2I는 size_hint 메타; 입력 해상도 유지)
- [x] **P2.5c** 프로필별 `mvp_aliases` / `missing_mvp` / `all_mvp`
- [x] **P2.5d** `bible.active_profile` + `exports/` 디렉터리 생성 + exports.status
- [ ] **P2.5e** artbook upscale + grid (후순위, P3 연계)
- DoD: video_ref 기본·얇은 MVP ✅ / artbook dry-run size·full master ✅

### Ticket P4 — ControlNet turnaround
- [x] expand `--engine` + turnaround → ControlNet
- [x] pose templates + controlnet runner meta/seed
- [x] mina 실생성 4뷰 (품질 실패 문서화)
- [ ] Empty-latent / full-body-source CN 경로로 측면·후면 성공

### Ticket P7-A — `shot_with_character.py` (파일럿 후)


---

## 11. 모듈 의사코드 (expand 핵심)

```python
def expand_character(id, sheets, source, model, candidates, presets_path):
    pkg = CharacterPackage.load(id)
    core = pkg.read_positive_core()
    negative = pkg.read_negative_core()
    presets = load_presets(presets_path).select(sheets)
    source_path = pkg.resolve(source)
    results = []
    for preset in presets:
        for c in range(1, candidates + 1):
            seed = random_or_derived(...)
            prompt = assemble(core, preset["instruction"], preset.get("style_lock"))
            neg = assemble(negative, preset.get("negative_extra", ""))
            out = pkg.refs_path(preset["sheet"], filename_for(...))
            meta = out.with_suffix replaced to meta/
            result = generate_i2i_image(
                input_image_path=source_path,
                prompt_text=prompt,
                denoise_val=preset["denoise"],
                cfg_val=preset["cfg"],
                model_type=model,
                output_filename=out,
                seed=seed,
                negative_text=neg,
                meta_out=meta,
            )
            results.append(result)
    pkg.update_manifest(results)
    return results
```

---

## 12. 테스트 계획 (최소)

| ID | 테스트 | 기대 |
|----|--------|------|
| T1 | create --id test_char | 폴더/bible/masters 생성 |
| T2 | create 동일 id 재실행 | exit 10 |
| T3 | expand without approve source | exit 20 또는 --source 명시 시 성공 |
| T4 | expand turnaround.side | refs/turnaround 파일 ≥1 |
| T5 | approve --as master_front | approved/master_front.png 존재 |
| T6 | seed 고정 2회 메타 | seed 필드 동일 |
| T7 | Comfy 종료 상태 | exit 40 |

---

## 13. 명시적 비범위 (이 스펙에서 구현하지 말 것)

- LoRA 학습 스크립트
- ControlNet 워크플로 JSON
- I2V / FFmpeg 조립
- 자동 얼굴 유사도 QA
- 그리드 합성 (P3)
- Web UI

---

## 14. 관련 파일 인덱스

| 파일 | 역할 |
|------|------|
| [character_sheet_system_design.md](character_sheet_system_design.md) | 배경·리서치·장기 로드맵 |
| [character_impl_spec.md](character_impl_spec.md) | **이 문서 — 코딩 계약** |
| [characters/sheet_presets.json](characters/sheet_presets.json) | 시트 프리셋 SSOT (prompt/denoise) |
| [characters/profiles.json](characters/profiles.json) | **용도 프로필 SSOT** (video_ref / artbook) |
| [characters/schemas/bible.schema.json](characters/schemas/bible.schema.json) | bible 스키마 |
| [characters/schemas/manifest.schema.json](characters/schemas/manifest.schema.json) | manifest 스키마 |
| [characters/_template/](characters/_template/) | 패키지 템플릿 |
| [characters/pilots/mina_park_v1_brief.md](characters/pilots/mina_park_v1_brief.md) | 파일럿 정의 |
| [characters/mina_park_v1/PILOT_NOTES.md](characters/mina_park_v1/PILOT_NOTES.md) | 실서버 E2E 품질 메모 |

---

## 15. 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-07-11 | 구현 착수 스펙 초판 — P0 산출물과 동기화 |
| 2026-07-11 | P1~P2 구현·파일럿 E2E 반영 |
| 2026-07-11 | **용도 프로필 스펙** 추가 (`video_ref` / `artbook`), Ticket **P2.5**, `profiles.json` |
