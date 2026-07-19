# 생성 프롬프트 크래프트 — 공장 최적화 (T2I / I2I / I2V / SI2V)

- **작성**: 2026-07-15  
- **상태**: ✅ **영상·이미지 본선 생성 시 필수**  
- **목적**: 기획·샷 설계가 좋아도 **프롬프트가 빈약하면 결과물이 무너진다**.  
  에이전트가 **고품질·구체·단일 의도** 프롬프트를 쓰도록 고정한다.  
- **이 공장 스택**: **Krea2 Turbo (Flow Matching) T2I** · Moody / Z-Image-Turbo I2I · Wan2.2 I2V · LTX SI2V · (선택) Grok 네이티브  
- **관련**: [moody_workflow_guide.md](moody_workflow_guide.md) · [video_director_master_persona.md](video_director_master_persona.md) · [image_cut_verification_gate.md](image_cut_verification_gate.md) · [agent_rules.md](../agent_rules.md) **Rule 7.5** · [AGENTS.md](../AGENTS.md)  
- **에이전트 스킬 (실행 강제)**: [skills/generation-prompt/SKILL.md](../skills/generation-prompt/SKILL.md) — SHOT→PROMPT_PACK · 생성 직전 equip  
- **모델별 방언 (v1.2+)**: [skills/generation-prompt/references/model_prompt_matrix.md](../skills/generation-prompt/references/model_prompt_matrix.md) — Krea / Z-Image / Illustrious / Qwen / Ideogram / Wan / LTX  
- **리서치 로그**: [skills/generation-prompt/RESEARCH.md](../skills/generation-prompt/RESEARCH.md)

> **기본 이미지 생성 모델**: Krea2 Turbo. 실사 키프레임은 `generate_krea` 우선.  
> Moody/Z-Image(Lonecat)는 I2I 변형·스타일 실험 대안.

---

## 0. 한 줄

```text
SUBJECT → ACTION/POSE → SETTING → LIGHT → CAMERA/LENS → STYLE/GRADE → MATERIAL DETAIL
한 샷 = 한 주 의도. 키워드 나열 금지. 모션 프롬프트에는 얼굴·의상 재서술 금지.
```

---

## 1. 공통 원칙 (모든 생성기)

### 1.1 순서 (커뮤니티·시네마 프롬프트 공통 패턴)

영문 본선 프롬프트는 **앞쪽이 가중**되는 경향이 크다. 중요 정보를 앞에 둔다.

| 순위 | 블록 | 예 |
|------|------|----|
| 1 | **Subject** | mid-20s Korean woman, oval face, shoulder-length dark brown soft wavy hair |
| 2 | **Action / pose** | standing under yellow parasol, closed black umbrella in right hand |
| 3 | **Setting** | rainy Seoul convenience-store street, wet reflective asphalt |
| 4 | **Lighting** | soft overcast key, warm store spill, restrained contrast |
| 5 | **Camera** | medium shot waist-up, 35mm, eye level, shallow depth of field |
| 6 | **Style / medium** | cinematic photoreal film still, Moody-grade naturalistic color, gentle film grain |
| 7 | **Materials / micro** | rain on knit fabric, natural skin micro-texture not plastic |

### 1.2 해야 할 것 / 하지 말 것

| 할 것 | 하지 말 것 |
|------|------------|
| 구체 명사·동사 (puddle ripple, chin lifts) | “beautiful cinematic masterpiece 8k” 만 나열 |
| **shot size + angle + one move** 명시 | “cinematic shot” 한 단어 |
| 해부·구조 제약 (feet flat, door closed) | 고난도 샷에 추상 감정만 |
| 긍정으로 기술 | 긴 negative로만 버티기 |
| 한 문장 덩어리 또는 짧은 절 연결 | 태그 50개 쉼표 지옥 |
| look/char/loc **core는 짧게 유지** 후 action이 주인공 | core 중복 3번 붙여 액션 매장 |

### 1.3 길이

| 용도 | 가이드 |
|------|--------|
| T2I 히어로 키프레임 | 40–120 단어 상당 · 핵심 6–8절 |
| I2I 변경 지시 | **바뀔 것 위주** 15–40 단어 + 유지 한 절 |
| I2V motion | **모션·카메라만** 8–25 단어 |
| SI2V | 퍼포/입 움직임 + 안정 · 배경 재서술 최소 |

너무 긴 프롬프트는 후반 토큰이 무시되거나 의도가 충돌한다.

### 1.4 언어

- **본선 생성 프롬프트: 영어** (이 공장 모델·I2V 관례).  
- intent/연출 메모·QA: 한국어 OK.  
- 화면에 넣을 **짧은 한글 타이포**만 예외 (Ideogram 등 타이포 툴).

---

## 2. 이 공장 전용 — Moody T2I / I2I (Z-Image Flow Matching)

### 2.1 T2I (`generate_moody` / `shot_compose` t2i)

**템플릿**

```text
[style/look short], [identity short if char], [location short if any],
[SHOT: size, angle, lens], [ACTION: concrete visible],
[LIGHT], [MATERIALS], photoreal cinematic still, sharp focus
```

**예 (medium · 우산 닫힘)**

```text
cinematic photoreal film still, Moody-grade naturalistic color, soft overcast light,
mid-20s Korean woman oval face warm brown eyes shoulder-length dark brown soft wavy hair,
cream knit cardigan white blouse light jeans, medium shot mid-thigh up, 35mm eye level,
standing under bright yellow convenience parasol, CLOSED black compact umbrella hanging in right hand unused,
looking sideways not at camera, wet reflective Seoul asphalt, rain, natural skin micro-texture not plastic, sharp focus
```

**예 (insert · 발만)**

```text
cinematic photoreal extreme high-angle INSERT, ONLY a pair of white low-top sneakers and lower calves
planted flat on wet dark asphalt, normal human foot anatomy two feet on ground, toe caps darkening with rainwater,
yellow parasol color in puddle reflection bokeh, NO face NO torso NO raised leg, soft rain, 50mm, sharp focus
```

### 2.2 I2I denoise (공장 SSOT 재확인)

| 목적 | denoise | 프롬프트 초점 |
|------|---------|----------------|
| 소품/국소 | 0.70–0.73 | 바꿀 사물만 |
| 조명/분위기 | 0.75–0.78 | light/time of day |
| 포즈·의상·장면 | 0.82–0.86 | pose + wardrobe + set |
| 사실상 재생성 | 0.90+ | 전체 재서술 |

I2I: **“what changes”** 를 앞에. “same person, keep face” 한 절이면 충분.

### 2.2b Qwen 지시 편집 (`generate_qwen_edit` / `shot_keyframe_edit --engine qwen`)

Moody I2I와 **공존**. 의미 단위 편집(물체 제거·교체, 소품 수정)에 쓴다.  
**가중치:** 멀티앵글과 **같은** `qwen-image-edit-2511` GGUF + Lightning (Angles LoRA 없음).  
각도 턴은 **`generate_qwen_angle` / `character_qwen_turns`** (같은 모델 + Angles LoRA + `<sks>`).

**프롬프트 패턴**

```text
[CHANGE: what to add/remove/replace], [KEEP: identity, framing, wardrobe, lighting unless asked]
```

| 할 것 | 하지 말 것 |
|------|------------|
| 한 번에 한 주 편집 의도 | 전체 재연출 + 의상 + 포즈 동시 요구 |
| 구체 명사 (plastic straw, left hand) | “make it better / fix anatomy” 만 |
| keep identity/framing 한 절 | 긴 스타일 태그 도배 |
| multi-ref 시 “image2 is face reference” 명시 | 참조 역할 모호 |

**예**

```text
Remove the plastic straw from the iced drink on the table, keep the same cup,
same woman identity and cafe framing, photoreal.
```

CLI는 기본적으로 identity keep 절을 붙인다 (`--raw-prompt` 로 끔).

**Lightning 운용 (공장 기본 정책)**

| 단계 | 설정 | 언제 |
|------|------|------|
| **기본** | Lightning **ON** (4step / CFG1) | 첫 패스·후보·빠른 확인 |
| **승격** | `--no-lightning --steps 20 --cfg 4` | 컵 날아감·국소 실패·approve 직전 재시도 |

속도 우선이 기본이고, **결과 보고 부족할 때만** 품질 패스로 올린다.

### 2.3 Look / Char / Loc 조립 규칙

`shot_compose` 가 core를 붙일 때:

1. look.positive_core — **짧게** (그레이드·매질)  
2. char — 얼굴·헤어·의상 잠금 (insert 무인물 샷이면 **생략 검토**)  
3. loc — 건축·재질 (insert 매크로면 약하게)  
4. **action / shot_type 지시가 가장 구체적**이어야 함  

**실패 패턴:** character portrait core가 insert action을 눌러 얼굴 CU로 붕괴 → `risk=insert` 시 char face 블록 제거 또는 T2I 단독.

### 2.4 품질 태그 (절제)

허용 (1회): `photoreal, sharp focus, natural skin micro-texture not plastic, gentle film grain`  
금지에 가까움: `masterpiece, best quality, 8k, ultra detailed` 도배, `trending on artstation` (포토리얼 뮤비용 톤 붕괴).

---

## 3. I2V 모션 프롬프트 (Wan2.2 / episode_i2v)

### 3.1 규칙 (공장 hard 습관)

- **모션·카메라·환경 움직임만** 쓴다.  
- **금지:** 얼굴 재서술, 의상 재나열, 새 캐릭터, 긴 스토리.  
- **한 샷 한 주 무브** (push-in **또는** walk **또는** rain density — 둘 이상 경쟁 금지).  
- 전 구간 움직임 암시: `continuous`, `throughout`, `steady` — **freeze pad 금지**와 호응.

### 3.2 템플릿

```text
[camera move], [subject micro-action], [environment motion], continuous, no warp no identity morph
```

| 샷 유형 | 모션 예 |
|---------|---------|
| insert rain | `raindrop impact ripples expand, continuous soft rain, micro push-in` |
| medium stand | `subtle breathing, damp hair drift, eyes glance aside, locked medium frame` |
| walk | `steady walk under umbrella, lateral track, continuous puddle splash` |
| car interior | `rain streaks slide on glass continuously, soft breathing, static cabin` |
| wide flood | `she walks into heavier rain, gentle track, continuous water spray` |

### 3.3 negative_motion

짧게: `warp, identity morph, flicker, freeze frame, extra limbs, face melt`

---

## 4. SI2V (립·보컬)

```text
singing performance, natural lip motion matching audio, subtle head sway, [emotion one word],
stable shoulders, continuous, no exaggerated mouth, no identity morph
```

- 배경·의상 장문 재서술 금지.  
- 뮤비: driving = master slice (center_voicey); 최종 믹스는 music_locked.

---

## 5. 샷 타입별 프롬프트 체크

| shot_type | 프롬프트에 반드시 | 피하기 |
|-----------|-------------------|--------|
| establishing / wide | full environment, readable architecture, scale | face-only crop |
| medium | waist or mid-thigh, hands/props visible if needed | ECU face |
| closeup | face + shoulders, lens 85mm feel | full body clutter |
| insert | **ONLY** detail subject, no face unless intentional | character portrait core |
| POV | through glass/wipers, coherent interior | broken door anatomy |

---

## 6. 고난도 제약 문장 치트시트

| risk | 넣을 절 |
|------|---------|
| feet | `both feet planted flat on ground, normal human anatomy, no raised leg, no extra toes` |
| hands | `five fingers natural grip, prop contacts hand` |
| car | `closed car doors, intact door frame and A-pillar, feet on floor, coherent interior geometry` |
| glass | `rain on windshield, realistic reflection, not a dashboard screen in a mirror` |
| umbrella | `CLOSED compact black umbrella` vs `OPEN black umbrella` — 상태 하나만 |

---

## 7. Grok 네이티브 (하이브리드 시)

| 툴 | 프롬프트 스타일 |
|----|----------------|
| image_gen | §1 순서, 2–5 문장, aspect 명시 |
| image_edit | **바뀔 것만** + keep identity/composition |
| image_to_video | 현재형 1–2문장, **단일 카메라/동작**, 6s/10s |

공장에 넣을 때는 해상도(work size) 맞추고 QA 동일.

---

## 8. 조립 체크리스트 (생성 버튼 전)

- [ ] Subject가 앞에 있는가  
- [ ] Shot size + angle + lens가 있는가  
- [ ] Action이 **눈에 보이는 동사**인가  
- [ ] Light 한 절  
- [ ] I2V면 모션만인가 (의상/얼굴 재서술 없음)  
- [ ] Insert면 face 블록 제거했는가  
- [ ] risk 제약이 필요한가  
- [ ] 한 주 의도만 있는가 (충돌 프롬프트 없음)  
- [ ] failure_note 관련 태그 예방 문구 반영했는가  

---

## 9. 나쁜 예 → 좋은 예

**Bad**

```text
beautiful cinematic masterpiece, Korean girl, rain, sad, 8k, best quality, music video, detailed
```

**Good**

```text
cinematic photoreal medium shot, mid-20s Korean woman cream cardigan, 35mm eye level,
standing under yellow store parasol in rain, closed black umbrella at her side,
looking aside, wet asphalt reflections, soft overcast light, natural skin texture, sharp focus
```

**Bad motion**

```text
beautiful woman in cream sweater walking in rain with emotional face, detailed clothing, 4k
```

**Good motion**

```text
steady walk under open umbrella, soft lateral track, continuous rain and puddle splash, no warp
```

---

## 10. 실패 노트 연동

프롬프트 빈약·충돌로 FAIL 시:

```bash
python scripts/failure_note.py add --stage keyframe --tags prompt_ignored,insert_failed \
  --symptom "..." --cause "weak/conflicting prompt" --fix "..." --prevention "apply generation_prompt_craft §..." \
  --severity high
```

관련 태그: `prompt_ignored`, `insert_failed`, `face_cu_spam`, `car_geometry`, `anatomy_feet`.
