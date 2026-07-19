# LTX 2.3 video prompts (I2V / FLF / V2V / T2V / audio)

**CLI:** `generate_i2v` (default LTX AIO), `generate_flf2v`, `generate_s2v`, `generate_v2v`  
**Also:** `chain_si2v_last_frame` (extend), `chain_one_take` (one-take chain)  
**Research:** `docs/ltx23_quality_research_and_improvement.md` · `docs/ltx23_clip_extend_guide.md` · `docs/ltx23_prompt_guide.md`

---

## ⚠️ 핵심 하드 룰 (생성 전 필독)

| 규칙 | 내용 |
|------|------|
| **프레임 상한** | 단일 생성 **97프레임 이내** (24fps ≈4초). 초과 시 품질 저하 + drift |
| **100프레임+ 컷** | 선행 클립 last frame → extend 분할 체인 |
| **프롬프트 금지** | 얼굴 재서술, 의상 나열, 마스터피스 태그 |
| **단일 의도** | 한 샷 = 한 주 카메라 무브 또는 한 주 액션 |

---

## 1. I2V — 기본 문법

**Image = look · identity · appearance**  
**Prompt = temporal behavior (what happens in time)**

### 1.1 Simple (MV 단일 비트 — 권장)

```text
[ONE camera move], [body/prop micro-action], continuous motion throughout, no warp
```

**예시:**
```text
slow push-in toward face, subtle breathing and hair drift, continuous, no warp no identity morph
```

### 1.2 Chronological (시간축 서술 — 복합 비트)

LTX는 시간 순서 서술에 강하다. 한 샷 안에서 사건 순서를 적는다.

```text
[0–2s: 시작 상태]. [2–4s: 동작 변화]. [카메라 설명 throughout]. [선택: 환경 소리].
```

**예시:**
```text
She stands still under the yellow parasol, then slowly lifts her gaze to the right; rain continues throughout. Static medium shot, soft overcast light holds. Distant rain ambience.
```

### 1.3 Official 포커스 순서 (Lightricks 공식)

1. **Core actions** as they occur (가장 중요)
2. **Visual details that change** or must be emphasized
3. **Audio cues** if backend supports: `"dialogue in quotes"`, footsteps, rain

---

## 2. 카메라 무브 어휘 (LTX 최적화)

| 의도 | 프롬프트 어휘 |
|------|---------------|
| 줌인 | `slow push-in`, `gentle dolly forward` |
| 줌아웃 | `slow pull-back`, `gentle dolly back` |
| 패닝 | `slow pan left/right`, `lateral track` |
| 고정 | `static frame`, `locked medium shot` |
| 틸트 | `slow tilt up/down` |
| 원형 | `gentle arc around subject` |
| 핸드헬드 | `subtle handheld drift` |

**한 번에 하나만.** `push-in AND pan AND orbit` = 충돌 금지.

---

## 3. 미세 액션 어휘 (바디/소품)

| 의도 | 어휘 |
|------|------|
| 호흡 | `subtle breathing`, `chest micro-rise` |
| 눈 | `slow blink`, `eyes glance aside`, `gaze holds lens` |
| 헤어 | `hair drift in breeze`, `damp hair slight sway` |
| 손 | `fingers curl around cup`, `hand relaxes on railing` |
| 걷기 | `steady walk under umbrella`, `slow confident stride` |
| 비 | `continuous soft rain`, `rain bead slides down glass` |

---

## 4. 샷 유형별 템플릿

| 샷 유형 | 모션 프롬프트 예 |
|---------|-----------------|
| insert rain | `raindrop ripples expand on asphalt, micro push-in, continuous soft rain` |
| medium stand | `subtle breathing, hair drifts, eyes glance aside, locked medium frame, continuous` |
| walk | `steady walk under open umbrella, lateral track, puddle splash, continuous` |
| car interior | `rain streaks slide on glass, soft breathing, static cabin, continuous` |
| wide scene | `she walks into heavier rain, gentle pull-back, water spray, continuous` |
| CU face | `slow blink, cheek micro-tension, locked CU, no camera move, continuous` |

---

## 5. FLF (First–Last Frame)

프롬프트 = A→B 사이 **브리지 모션** (새 구성 금지).

```text
smooth transition, [how pose/camera interpolates A to B], continuous, no teleport, keep identity
```

**예:**
```text
camera gently pulls back as she lowers the umbrella, continuous smooth transition, identity preserved throughout
```

---

## 6. V2V

```text
[what changes: pace / weather density / performance energy], keep composition and identity, continuous
```

---

## 7. T2V (still 없음)

```text
[subject + setting], [action over time], [camera], [light], [ambient audio if any]
```

---

## 8. extend 체인 프롬프트 (100프레임+ 컷)

선행 클립 마지막 프레임 → 다음 클립 시작 프레임으로 사용 시:

```text
continuing [same motion/camera], [what evolves next], no jump cut, identity preserved
```

**예:**
```text
continuing the slow push-in, she now fully faces the camera, eyes hold lens, rain continuous, no jump cut
```

**extend 금지 패턴:** 새 인물 등장, 장소 전환, 의상 설명 재시작.

---

## 9. SI2V pointer

음성 구동: `motion_video_prompts.md` §SI2V — 입·퍼포먼스만.  
오디오가 드라이버. 입 닫힘 지시는 의도적 무성 샷만.

---

## 10. Negative

```text
warp, identity morph, freeze frame, flicker, extra limbs, face melt, whip pan, sudden cut, teleport
```

---

## 11. Quality gates (생성 전 체크)

- [ ] 단일 생성 = 97프레임 이내
- [ ] 100프레임+ = chain_si2v_last_frame 계획 수립
- [ ] 프롬프트에 얼굴 재서술 없음
- [ ] 카메라 무브 ≤ 1개
- [ ] 시간축 서술 시 순서 명확
- [ ] FLF면 브리지 언어 사용
- [ ] motion 동사 존재
- [ ] continuous / throughout 포함
