> **ARCHIVED (2026-07-14)** — 운영 SSOT 아님. 인덱스: [../../README.md](../../README.md). 활성 백로그: [../../agent_video_tooling_todo.md](../../agent_video_tooling_todo.md).

# 스토리보드 · 키프레임 실무 리서치 (캐릭터/로케 시트 이후)

- **작성일**: 2026-07-12  
- **목적**: 캐릭터 시트·로케이션 시트 **이후** 실무에서 키프레임/스토리보드를 어떤 형식·순서로 만들고 영상에 쓰는지 커뮤니티·벤더 관행을 정리하고, `agent_custom` 공정에 반영  
- **관련**: [storyboard_pipeline_design.md](storyboard_pipeline_design.md), [character_casting_pipeline.md](character_casting_pipeline.md), [location_sheet_system_design.md](location_sheet_system_design.md)

---

## 1. 공통으로 반복되는 파이프라인 (2025–2026 커뮤니티 합의)

거의 모든 실무/튜토리얼이 **같은 뼈대**를 쓴다:

```text
① Asset cards / packs
   - Character sheet (multi-angle face/body, costume lock)
   - Environment / location card (hero + multi-angle + empty stage)
   - Style / look card
② Storyboard-first (연출 합의)  — NOT “한 줄 프롬프트로 바로 장편 T2V”
③ Production keyframe stills   — 샷당 1장(또는 first+last), 최종 비율
④ Human / agent gate           — contact sheet 검수
⑤ Image-to-video (I2V)         — 키프레임 앵커 + motion-only 프롬프트
⑥ (선택) First–Last / multi-keyframe bridge
⑦ Edit · sound · deliver
```

| 출처 유형 | 핵심 메시지 |
|-----------|-------------|
| **Topview Canvas 등 에이전트 워크플로** | asset cards (char/style/**environment**) → storyboard preview → keyframe review → motion (Seedance 등) |
| **Kling 공식 가이드** | ideation + visual refs → **T2I key frames per shot** → I2V → QC → edit; multi-angle refs = 감독 레퍼 |
| **Mindstudio / 크리에이터 블로그** | character sheet + storyboard + **location docs** 가 일관성 SSOT |
| **inVideo / consistency 가이드** | multi-angle character sheet → **anchor keyframe at target location** → animate |
| **Reddit r/generativeAI / r/StableDiffusion** | “Bake keyframes first”; I2V 프롬프트에 얼굴 재서술 금지; first–last chain; 드리프트 주의 |
| **Runway / Luma** | Keyframes (first / mid / last) 또는 multi-keyframe 으로 모션 구간 제어 |
| **Wan / ComfyUI FLF2V 튜토리얼** | Flux 등으로 일관 키프레임 → first-to-last frame video |
| **학술 (multistage / DrawVideo 계열)** | char assets → scene initial frame (I2I) → I2V clip; 또는 sketch→reference keyframe→derivative action keyframes→clips |

**한 줄**: 시트는 DNA, **키프레임은 샷의 법적 증거(anchor)**, 영상 모델은 **그 앵커를 움직이게만** 한다.

---

## 2. 완성 “포맷” — 실무에서 넘기는 것

커뮤니티·프로가 **영상 단계에 넘기는 패키지**는 대략 다음이다:

### 2.1 머신용 (필수)

| 산출물 | 역할 |
|--------|------|
| **샷 리스트** (JSON/CSV/표) | shot_id, order, duration, action, camera, char_ids, location_id, motion_prompt |
| **샷별 키프레임 PNG** | I2V first frame; 에피소드 **최종 종횡비** |
| **(선택) last / bridge 키프레임** | FLF2V / multi-keyframe 입력 |
| **ref 바인딩** | 이 샷이 쓰는 char approved alias + loc approved alias |
| **스타일/룩 id** | look cores 재사용 |

### 2.2 사람용 (거의 필수)

| 산출물 | 역할 |
|--------|------|
| **Contact sheet / board grid** | 전 샷 한 장 검수 (animatic 느낌) |
| **Asset one-pager** | 캐릭터 시트 요약 + 로케 hero (선택 PDF) |
| **Do / Don’t** | 조명·의상·화면 방향 규칙 한 줄 |

### 2.3 우리 레포 매핑

| 커뮤니티 포맷 | agent_custom |
|---------------|--------------|
| Asset cards | `characters/<id>/approved/*`, `locations/<id>/approved/*`, `looks/<id>/` |
| Shot list | `stories/<ep>/shots.json` |
| Production keyframes | `stories/<ep>/keyframes/S0x.png` + `meta/S0x.json` |
| Board contact | `stories/<ep>/board/storyboard_contact.png` (`storyboard_export`) |
| Motion | `episode_i2v` / `episode_s2v` / (후속 FLF2V) |
| Delivery | `deliveries/` + assemble |

보드 패널(러프 스케치)과 **프로덕션 키프레임**을 구분한다.  
실무 AI 파이프에서는 종종 **포토리얼 키프레임 = 보드 최종 패널**로 합쳐진다 (클라이언트 합의용 contact sheet).

---

## 3. 키프레임을 “잘” 만드는 규칙 (커뮤니티 DoD)

1. **샷당 1 앵커 스틸** — 최종 format 비율로 bake.  
2. **올바른 ref 타입**  
   - close-up → face / expr  
   - wide → full body + empty_stage / master_wide  
   - establishing → location only  
   - insert → landmark / prop  
3. **캐릭터를 장소에 “앉히기”** — char sheet만 돌리지 말고 loc empty_stage/angle와 합성·동시 프롬프트.  
4. **I2V 프롬프트 = 모션·카메라만** — “젊은 여성 얼굴 재설명” 금지 (정체성 붕괴).  
5. **클립 길이 짧게** (대략 3–6s) 후 체인.  
6. **연속성** — N의 끝 프레임 ≈ N+1의 시작 (또는 명시적 last_keyframe).  
7. **게이트** — contact sheet 통과 전 전량 I2V 금지.  
8. **의상/소품 잠금** — 시트에서 정한 default wardrobe를 샷 전반 유지 (의도적 alt만 변경).

---

## 4. 영상 엔진 쪽 입력 관례

| 엔진 계열 | 키프레임 사용 |
|-----------|----------------|
| **I2V (Wan 등)** | first frame 필수, motion prompt |
| **FLF2V / first–last** | first + last still, 중간 모션 보간 |
| **Multi-keyframe (Luma Ray, Runway Turbo)** | first / mid / last 최대 N장 |
| **Elements / Character ID (Kling 등)** | 시트 멀티앵글 업로드 + 샷 키프레임 (클라우드; 로컬 파이프는 approved refs로 대체) |

로컬 Comfy 본선은 **키프레임 품질이 전부**에 가깝다.  
클라우드 Elements는 우리 **approved multi-view 시트**와 역할이 같다.

---

## 5. 우리 공정에 넣는 운영 SOP (Production v1)

```text
A  Character full_sheet → approved
B  Location full_sheet  → approved
C  Look cores           → looks/<id>
D  story_init --seed-shots N
E  Fill shots.json (action, shot_type, character_ids, location_id,
                    character_refs, location_ref, motion_prompt)
F  shot_compose (per shot or --all)  @ episode format work size
G  storyboard_export → board contact + checklist
H  Human gate → shot_approve
I  episode_i2v (approved only); motion_prompt = motion only
J  assemble / deliver
```

CLI:

```bash
python scripts/story_init.py --id demo_ep01 --format cinematic_16x9 \
  --look cinematic_moody_v1 --seed-shots 3 --title "Demo"

# shots.json 편집 후
python scripts/shot_compose.py -e demo_ep01 --all
python scripts/storyboard_export.py -e demo_ep01
python scripts/shot_approve.py -e demo_ep01 --all-drafts  # if available
python scripts/episode_i2v.py -e demo_ep01 --shots all_approved
```

---

## 6. 갭 vs 구현 상태 (리서치 반영 후)

| 커뮤니티 관행 | 이전 | 반영 |
|---------------|------|------|
| Asset packs first | ✅ char/loc | 유지 |
| Storyboard-first | ✅ design | SOP 문서 강화 |
| shot_type별 ref 선택 | 약함 | `shot_type_presets` + compose resolver |
| Contact board export | ⬜ | `storyboard_export.py` |
| first–last 필드 | 부분 | shots + meta `keyframe_end` |
| I2V motion-only 규칙 | 문서 | SOP + meta 경고 |
| FLF2V / F2F 배치 | ⬜ PLANNED | **S6** — [flf2v_f2f_roadmap.md](flf2v_f2f_roadmap.md) (2026-07-12 로드맵 고정) |

---

## 7. 참고 링크 (검색 시점 요약)

- Kling: AI image-to-video workflow guide (key frames per shot, multi-angle refs)  
- Topview-style agent canvas: asset cards → storyboard → keyframe → motion  
- Mindstudio: storyboards + character sheets + location docs  
- Runway Gen-3 keyframes help; Luma multi-keyframe 담론  
- Reddit: bake keyframes first; first–last chain; identity drift  
- arXiv multistage character-stable pipelines; DrawVideo storyboard keyframe expansion  
- Wan FLF2V / ComfyUI first–last tutorials  

(상세 URL은 검색 세션 로그 및 상위 웹 결과 참조.)

