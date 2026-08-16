# Factory Skills — 에이전트 탑재 스킬 (SSOT)

이 폴더는 **ComfyUI 미디어 공장(`agent_custom`)이 배포하는 에이전트 스킬**의 원본(SSOT)이다.  
Grok / Claude Code / Cursor / Codex 등 **어떤 에이전트든** 이 도구로 영상·이미지 작업을 할 때:

```text
1) skills/ 목록을 확인한다
2) 세션에 스킬이 없으면 → 여기 내용을 로드(탑재)한다
3) 연출 스킬 → 프롬프트 스킬 → 생성 CLI → 평가 스킬
```

- **Skills** = 연출·프롬프트 판단 (두뇌)  
- **scripts/** = Comfy 생성·게이트·조립 (손)

---

## 0. Equip Contract

### 영상 작업 시 필수 탑재 순서

| 순서 | 스킬 | 언제 |
|------|------|------|
| **1** | **video-direction** | 기획·SHOT_DESIGN 전 (영상 기획을 할 때만) |
| **2** | **generation-prompt** | `shot_compose` / `generate_*` / `episode_i2v|s2v` **직전** |
| **3** | **output-review** | `generate_*` **직후**. 파일 열고 판정. exit 0 ≠ 완료 |
| **4** | **video-edit** | 클립이 생긴 뒤 컷·타이틀·믹스·마스터. concat으로 납품 금지 |

```bash
python scripts/skill_equip.py list
python scripts/skill_equip.py install video-direction
python scripts/skill_equip.py install generation-prompt
python scripts/skill_equip.py install output-review
# --target grok|claude|all
```

최소: 각 스킬 `SKILL.md` 전문 세션 로드.

### 금지

- 연출·프롬프트 스킬 없이 대량 생성  
- SHOT_DESIGN 없이 태그 수프 프롬프트  
- I2V에 얼굴·의상 장문 재서술  
- 생성 성공 = 품질 성공 (`output-review` / visual QA 없이 완료 선언)

### 증명 산출

- `CREATIVE.md` · `SHOT_DESIGN.md`  
- `prompts/S0x.md` 또는 `PROMPT_PACK.md` (still + motion)  
- QA / approve 게이트 · 원오프는 `reviews/<name>/record.json`  

---

## 1. 스킬 목록

| id | 경로 | 용도 | 상태 |
|----|------|------|------|
| **video-direction** | [video-direction/](video-direction/) | 기획·연출·샷 문법·시각 1–10층 | ✅ v1.11 |
| **generation-prompt** | [generation-prompt/](generation-prompt/) | SHOT → 모델별 방언 프롬프트 | ✅ v1.3 |
| **video-edit** | [video-edit/](video-edit/) | 말→EDIT_PLAN→타임라인→마스터 QA | ✅ v1.5 |
| **output-review** | [output-review/](output-review/) | generate_* 결과 능동 평가 · fail→레버 | ✅ v1.0 |

---

## 2. 관계

```text
video-direction          generation-prompt           scripts/              output-review
CREATIVE + SHOT_DESIGN → still/i2v/si2v strings  →  generate_*         →  pack → open → record
```

장문 공장 문서: `docs/generation_prompt_craft.md` · `docs/video_director_master_persona.md` 등.

---

## 3. 버전

스킬 변경 시 `process.md` + 해당 `SKILL.md` version.  
`python scripts/skill_equip.py install <id>` 로 에이전트 경로 동기화.
