# Agent-callable workflows

에이전트 CLI가 읽는 **도구용 워크플로/프리셋**입니다.  
휴먼 UI 실험(`../human/`)과 섞지 마십시오.

도구 특징·선택: **[docs/tool_catalog.md](../../docs/tool_catalog.md)**

> **전환 플랜 (JSON 직접 API 호출):**  
> [`docs/workflow_api_direct_call_plan.md`](../../docs/workflow_api_direct_call_plan.md)  
> 목표: 미니 그래프/`convert_ui_to_api`/런타임 inject 폐기 → `*.api.json` + port patch + `/prompt` 만.
>
> **기능 선택 (Bypasser/셀렉터 → 프리셋):**  
> Lonecat: [`../human/Lonecat_AIO_Z-Image_ver17_AGENT_GUIDE.md`](../human/Lonecat_AIO_Z-Image_ver17_AGENT_GUIDE.md) ·  
> Krea2: [`../human/Krea2_SFW_NSFW_v10_AGENT_GUIDE.md`](../human/Krea2_SFW_NSFW_v10_AGENT_GUIDE.md) ·  
> [`presets/lonecat_feature_presets.json`](presets/lonecat_feature_presets.json) ·  
> `python scripts/run_workflow_api.py --list-features`

## Catalog (SSOT 별칭)

| 키 | 파일 | 스크립트 |
|----|------|----------|
| `t2i_moody` | `T2I-moody.json` | `scripts/generate_moody.py` (Phase2 → Lonecat T2I 예정) |
| `lonecat_i2i_identity` | `presets/lonecat_i2i_identity.api.json` | **I2I 본선** `generate_moody_i2i` / lock / ipadapter(alias) |
| `krea2_t2i_v10` | `presets/krea2_t2i_v10.api.json` | Krea2 T2I (SFW+NSFW capable) `generate_krea` |
| `krea2_nsfw_t2i` | 동일 프리셋 별칭 | **빨간맛 still** `generate_krea_nsfw` (adult 18+ only) |
| `ltx23_nsfw_i2v` | human `ltx23_nsfw/ltx23I2VWorkflow_v20` (UI expand) | **빨간맛 I2V** `generate_ltx_nsfw_i2v` — real WF + group switches |
| `ltx23_nsfw_director` | human `ltx23_nsfw/ltx23DirectorWorkflow_directorV20` | **빨간맛 Director** `generate_ltx_nsfw_director` |
| `qwen_instantx_inpaint` | human `image_qwen_image_instantx_inpainting_controlnet` | **마스크 인페인트** `generate_qwen_inpaint` — InstantX CN real WF |
| `zimage_fun_union_controlnet` | `presets/zimage_fun_union_controlnet.api.json` | **CN 본선** `generate_moody_controlnet` (Fun Union 공식) |
| `i2i_moody` | `I2I-moody.json` | 레거시 미니 only (`--legacy-mini`) |
| `i2i_controlnet_moody` | `I2I-ControlNet-moody.json` | CN 레거시 미니 only (`AGENT_CN_BACKEND=legacy_mini`) |
| `i2i_controlnet_moody` | `I2I-ControlNet-moody.json` | `scripts/generate_moody_controlnet.py`, expand CN |
| `i2v_wan22_a14b` | `presets/i2v_wan22_a14b.api.json` | `generate_i2v --backend wan22` (API) |
| `wan22_*` planned | human `wan22/` pack | FaceEnhance / Upscale / FLF / Animate — see AGENT_GUIDE |
| `t2i_krea` | `T2I-krea.json` | `scripts/generate_krea.py` |
| `t2i_z_image_turbo` | `T2I-z-image-turbo.json` | (베이스/참고) |
| `qwen_edit_2511` | **JSON 없음 — API inject** | `generate_qwen_edit.py` (기본 GGUF=angle과 동일 모델) · `shot_keyframe_edit --engine qwen` |
| `qwen_angle_2511` | **JSON 없음 — API inject** | `generate_qwen_angle.py` · `character_qwen_turns` (Angles LoRA 턴) |
| *(SI2V InfiniteTalk)* | **JSON 없음 — API inject** | `generate_s2v.py --backend infinitetalk` |
| *(SI2V LTX custom-audio)* | **JSON 없음 — API inject** | `generate_s2v.py --backend ltx23_ia2v` |

### Still-edit engine coexistence

| 엔진 | 스크립트 | 가중치 | 언제 |
|------|----------|--------|------|
| Lonecat I2I | `generate_moody_i2i` / lock / `ipadapter` 이름 유지 | `lonecat_i2i_identity` API | 키프레임·아이덴티티 denoise |
| Qwen Edit | `generate_qwen_edit` / `shot_keyframe_edit --engine qwen` | **2509 Q5 GGUF** + 지시 인코더 (Angles 없음) | 물체 교체·제거 |
| Qwen Angle | `generate_qwen_angle` / `character_qwen_turns` | **2511 GGUF** + Lightning + **Angles LoRA** | 헤드/바디 멀티뷰 (`<sks>`) |

편집 기본 백엔드 `gguf_2509`. **Lightning 기본 ON** → 결과 부족 시만 `--no-lightning --steps 20 --cfg 4`.

별칭·파일 매핑은 [catalog.json](catalog.json) 이 코드와 공유하는 SSOT입니다.

SI2V는 런타임 API inject (`lib/ltx_s2v.py` / `build_infinitetalk_api`).  
참고 휴먼 WF: `F:\ComfyUI_workflows\LTX2.3\Custom-Audio\…`, Wan InfiniteTalk 예제.  
공식 LTX IC-LoRA LipDub은 V2V + gated 가중치 — 에이전트 미연동.

## Agent-friendly 설계 원칙

1. **주입 포트 안정**: 스크립트가 찾는 `class_type`(예: `KSampler`, `Prompt (LoraManager)`, `UNETLoader`)을 함부로 바꾸지 말 것.
2. **링크 우선**: 위젯 값보다 링크된 입력이 우선한다. UI에서 링크를 끊으면 스크립트 가정이 깨진다.
3. **한 그래프 한 책임**: T2I / I2I / ControlNet / I2V를 한 파일에 몰아넣지 않는다.
4. **프로모트 시 스크립트 동반**: JSON만 바꾸고 `generate_*.py` 매핑을 안 맞추면 금지 (agent_rules Rule 2).
5. **해상도**: I2V는 work 해상도 프리셋 기준. 납품 1080p는 업스케일 층 (video_delivery_and_backends.md).

## 수정 체크리스트

- [ ] `workflows/human/` 또는 UI에서 검증했는가?
- [ ] agent 디렉터리에 반영했는가?
- [ ] 해당 `generate_*.py` / convert 로직 동작 확인?
- [ ] `process.md` 기록?

## 레거시

루트 워크플로우 JSON은 제거되었다. **편집·프로모트는 여기(`workflows/agent/`)에만** 한다.
