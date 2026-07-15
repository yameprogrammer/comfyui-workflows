# Grok Build 하이브리드 툴링 (공장 + 그록 네이티브)

**대상 에이전트:** Grok Build / Grok CLI (이미지·영상 네이티브 툴 보유)  
**상위 공통 규칙:** 모든 에이전트 — [agent_native_capability_autonomy.md](agent_native_capability_autonomy.md) · Rule **8.0**  
**이 문서:** Grok 전용 매핑 · Rule **8.1**

공장 SSOT는 그대로 `agent_custom` 이다. 그록 네이티브 툴은 **가속·실험·수술 편집** 레이어다.

---

## 0. 도구 선택 주체 (기본 = 에이전트 자율)

| 상황 | 행동 |
|------|------|
| 사용자가 도구를 **명시하지 않음** | 에이전트가 목표·품질·속도·게이트에 맞게 **공장 / 그록 네이티브를 스스로 선택**하고 실행 |
| 사용자가 도구를 **명시** (“Comfy로”, “그록 편집으로”, “IT 다시”) | **사용자 지정 우선** |
| 애매한 트레이드오프 | 도구 메뉴를 나열해 고르게 하지 말고, **추천 1안을 실행하거나** 한 줄로 선택지만 제시 |

**금지에 가까운 습관:** 매 단계 “어떤 툴 쓸까요?” 묻기.  
**권장:** 알아서 돌리고, 결과·다음 게이트만 짧게 보고.

선택 기준은 §2 결정 트리. 사용자가 도구를 거론하기 전까지 **에이전트 판단이 기본값**이다.

---

## 1. 도구 역할 분담

| 단계 | 공장 (Comfy CLI) | 그록 네이티브 | 비고 |
|------|------------------|---------------|------|
| 컨셉 / 무드보드 | 선택 | **`image_gen` 우선** | 빠르고 저렴. 본선 ID 아님 |
| 캐릭 시트 / 룩 / 로케 pack | **필수** | 참고 이미지만 | 시트·bible·approve 는 공장 |
| 프로덕션 키프레임 | **`shot_compose` 본선** | `image_edit` 로 **국소 수정** 가능 | 드롭/소품 등 1장 수술 |
| 립싱크 SI2V | **`episode_s2v` / IT** | 불가 (대체 금지) | TTS+driving 필수 |
| 무대사 I2V | **`episode_i2v` 본선** | `image_to_video` / `reference_to_video` **프리뷰** | 프리뷰≠납품 |
| BGM / assemble / 1080 | **공장 필수** | — | hard gate 유지 |
| 작업대 export | **필수** | — | Rule 소비자 계약 |

### 그록 네이티브 툴 맵

| 툴 | 용도 |
|----|------|
| `image_gen` | 시놉 비주얼 러프, 의상 아이디어, 보드 썸네일 |
| `image_edit` | 승인된 키프레임 **국소** 수정 (물방울, 빨대, 손 등). identity 유지 프롬프트 필수 |
| `image_to_video` | 키프레임 1장 → 짧은 모션 **프리뷰** (push-in, sip 등) |
| `reference_to_video` | 복수 레퍼로 스타일 모션 탐색 (본선 클립 아님) |

---

## 2. 에이전트 자율 선택용 결정 트리

사용자가 도구를 지정하지 않았을 때, 에이전트가 **내부적으로** 따른다 (유저에게 도구 메뉴 제시 아님).

```text
이 산출물이 납품 클립/립/합본에 직접 들어가나?
  YES → 공장 CLI (또는 공장 재생성)
  NO  → 그록으로 속도 내기 OK

키프레임에 “작은 결함”만 있고 구도·정체성은 OK인가?
  YES → image_edit 1회 → 공장 keyframes/ 에 덮어쓰기 → status draft 재승인
  NO  → shot_compose 재생성

무대사 모션 의도를 빠르게 검증하는 게 본선 비용보다 이득인가?
  YES → image_to_video 프리뷰 → 확정 후 episode_i2v 본선
  NO  → 바로 episode_i2v

대사/립이 필요한가?
  YES → 그록 영상 금지. TTS + episode_s2v only
```

---

## 3. 핸드오프 규칙 (공장에 넣는 법)

1. **이미지는 파일 경로로만** 공장에 편입한다 (세션 토큰만 두고 “끝” 금지).  
2. 키프레임 교체 시:
   - 저장: `stories/<ep>/keyframes/S0x.png` (work size 544×960 맞출 것)
   - `keyframe_status=draft` → 유저 육안 → `shot_approve --status approved`
   - 메타에 `source=grok_image_edit` 또는 `grok_image_gen` 기록 권장
3. 그록 **영상 프리뷰**는 `clips/work/_preview_grok/` 등 **프리뷰 전용** 경로.  
   - `clip_status=approved` 금지  
   - assemble 입력 금지  
4. 유저에게 경로를 말할 때 **공장 + 작업대 export** 둘 다 (소비자 계약).

```bash
# 그록 편집 후 예
# (수동 복사로 keyframes 갱신 후)
python scripts/shot_approve.py -e EP -s S03 --status draft   # 필요 시
# 재승인
python scripts/shot_approve.py -e EP -s S03 --status approved
python scripts/export_episode_to_workspace.py -e EP --dest "..."
```

---

## 4. 이 에피소드에서 특히 유효한 패턴

| 이슈 | 하이브리드 처방 |
|------|-----------------|
| 얼굴 물방울 | `image_edit` 로 키프레임 건조 피부 → 해당 샷 I2V/SI2V만 재생성 (전 에피 블러 금지) |
| 무대사 S01/S06/S09 의도 확인 | `image_to_video` 6s 프리뷰 → OK 시 `episode_i2v` |
| 대사 잘림 / 립 | **그록 영상 금지** — `AGENT_IT_MAX_FRAMES` + center_voicey + `episode_s2v` |
| 과한 제스처 | motion_prompt 완화 후 **공장 SI2V 재생성** (그록으로 립 유지 불가) |

---

## 5. 금지

* 그록 영상으로 InfiniteTalk / 립 컷 **대체**  
* 그록 산출물만 작업대에 두고 공장 `shots.json` / approve 게이트 **우회**  
* 픽셀 블러로 “물방울 제거” 후 본선 확정 (실사 붕괴 — 2026-07-13 사고)  
* 프리뷰 클립을 `assemble` 에 몰래 투입  

---

## 6. 효율 목표

| 목표 | 수단 |
|------|------|
| 유저 대기 ↓ | 컨셉·프리뷰는 그록, 본선만 Comfy |
| GPU 점유 ↓ | 확정 전 전 샷 IT 돌리지 말 것 |
| 정체성 유지 | 시트·shot_compose 본선, 그록은 국소 편집 |
| 감사 가능 | 메타·process.md 에 어떤 툴로 냈는지 한 줄 |

---

## 관련

* [agent_rules.md](../agent_rules.md) Rule 8  
* [AGENTS.md](../AGENTS.md)  
* [agent_consumer_workspace_contract.md](agent_consumer_workspace_contract.md)  
* [production_asset_pipeline.md](production_asset_pipeline.md)  
