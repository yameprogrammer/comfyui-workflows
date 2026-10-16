# LTX-2.5 Ingredients: 실패 진단·커뮤니티 조사·복구

조사일 2026-10-16 UTC. 앞선 두 번의 실패를 완료로 간주한 정리는 철회하며, 아래 네 번의 가설·설정 검증을 추가했다. 최신 시각과 실행 수치는 `ingredients-repair-status.json`을 기준으로 한다.

**결론: 현재 INT8 + 새2.5 Ingredients 조합은 사용 가능하다.** 참조 시트/설명을 고친 공 테스트에서 시트 누출·검은 가림을 제거했다. 공개 인물·소품·장소 사례도 한 장면으로 결합됐다. 다만 정확한 인물 얼굴·머리 보존과 청취 품질은 별도 미통과 영역이다. 모델 전체의 사용 불가나 모든 참조의 성공을 주장하지 않는다.

## 무엇이 실패했는가

실제 입력 [원래 시트](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_sheet.png)는 같은 공을 두 번 담았다. 왼쪽에는 공이 이미 놓인 세로 장소 사진, 오른쪽에는 같은 공의 작은 확대 사진이 있었고 검은 여백이 넓었다. 두 패널이 서로 다른 시각 요소를 명확히 분리하지 못했다.

- [첫 결과](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_ball_contact.jpg): 왼쪽 패널 안에서만 공이 구르고 오른쪽 작은 공과 검은 시트 레이아웃이 계속 남았다.
- [프롬프트만 바꾼 결과](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_ball_fullframe_contact.jpg): 하나의 넓은 장면으로 바뀌었지만 검고 흐린 세로 덩어리가 전경을 계속 가렸다.
- 검은 배경 자체는 공식 요구사항이다. 이를 없애는 것이 일반 해법이라는 앞선 안내는 부정확했다. 최종 성공 시트도 검은 배경을 유지했다.

## 공식 조건 대조

[공식2.5 어댑터 카드](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Ingredients)는 정적인 복합 시트를 출력 해상도·fps·길이에 맞춰 반복하고 최소121프레임을 요구한다. 학습 버킷768×448/121/24fps, downscale1, 강도1, 텍스트 없는 검은 배경의 요소별 패널, 참조 설명과 생성 장면을 나누는 프롬프트가 기준이다.

| 항목 | 앞선 실제 구성 | 진단 |
|---|---|---|
| 모델 | 2.5 distilled INT8 ConvRot + 전용 Gemma4 INT8 + 표준2.5 video/audio VAE | 새2.5 어댑터와 실행됨. 카드의 dev base 메타데이터만으로 distilled를 금지할 근거 없음; 카드 사용 예제도 distilled |
| 어댑터 | `ltx-2.5-22b-ic-lora-ingredients-0.9.safetensors`, 강도1 | 헤더2.5/downscale1, 모델 적용480 patches 로그. 기존 AIO 품질 LoRA 정책은 변경하지 않고 이 원인분리 경로에만 Ingredients 단독 적용 |
| 참조 | ImageScale768×448 → RepeatImageBatch121 → IC guide | 최소길이·해상도·fps·강도·downscale 모두 충족. 파일 영상 대신 동일 IMAGE 배치를 반복하는 공식 Comfy 방식 |
| 생성 latent | EmptyLTXVLatentVideo, 참조는 별도 IC guide로 추가 | 시트를 첫 생성 프레임에 강제하는 I2V 연결 없음. `LTXVImgToVideoInplace` 없음 |
| 샘플링 | Euler ancestral, 공식8단계 manual sigmas, CFG1 | 공식 단일 단계 예제와 일치 |
| 출력 | sampler → SeparateAV → CropGuides → decode → mux | 참조 가이드 제거 배선 있음. 시트 영상 자체를 출력한 연결 오류 아님 |
| 참조 VAE | 후보는 tiled encode **true**, 공식 JSON은 **false** | 실제 차이. 끄는 단일변수 실험은 실패를 해결하지 못했음 |
| 시트·설명 | 같은 공 중복, 장소에 공 포함, 짧은 패널 설명 | 정리된 별도 소품/빈 장소와 정확한 위치 설명으로 교체 후 개선. 이미지와 설명의 개별 기여도는 아직 분리하지 못함 |

공식2.5 JSON은 [2.3 Ingredients 파일을 지정](https://docs.ltx.io/open-source-model/integration-tools/ic-lo-ra-adapters#ingredients)한다. 이번 후보는 새2.5 카드 조건으로 따로 구성했으며 단순 파일 교체와 동일하다고 부르지 않는다. 기본 bf16→Comfy INT8, 전용2.5 어댑터, 명시121/24/768×448, 타일 인코딩 및 mux 변경을 기록했다. 이번 성공은 이 조합이 원천적으로 지원 불가라는 가설을 반박하지만 bf16 대비 품질 동등성까지 입증하지는 않는다.

## 가설을 바꾼 추가 실행

모두 기존8188, 설치/업데이트/재시작 없음. 기존 성공 산출물은 보존했다.

| 실험 | 고정 / 변경 | 결과 |
|---|---|---|
| untiled, `cb2215f5-6397-41f3-9ae0-8e63bd482adb` | 기존 시트·전체화면 프롬프트·seed4747·강도1 유지. VAE 참조 타일만 true→false | 36.14초, **FAIL**. 같은 어두운 가림. 타일만으로 원인을 설명하거나 해결할 수 없음 |
| clean_sheet, `6a112922-45cb-443c-aa0e-8219f789b083` | seed4747·강도1·샘플러·출력 버킷 유지. 소품1패널/빈장소1패널로 재구성하고 정확한 위치별 설명. untiled 유지 | 37.06초, **제한된 소품/동작 시각 PASS**. 단일 공이 연속 탁자 장면을 가로질러 구름. 시트·가림 없음 |
| loopforge 부분 적용, `760e4620-901a-4612-bfa7-06332bf2f999` | 공개 시트/프롬프트·강도1.4·121/24. 실제 seed4747/Euler ancestral. 초기 의도42/CFG++와 다르게 적용돼 정확 재현 분류에서 제외 | 실행52초 내외. 인물/빨간기타/커튼/피아노 결합·움직임 확인. **정확 얼굴/머리 및 청취는 pending**. 잘못된 키는 비관련 노드의 무시되는 추가 입력으로 들어간 것을 확인 |
| loopforge 설정 수정, `db856dae-2f34-4525-b818-39cea36aef32` | 실제 RandomNoise42 / KSamplerSelect Euler ancestral CFG++ / 강도1.4를 API에서 확인. 전체 입력 키 검사.928×544/121/24 | 75.73초. 하나의 연속 무대에서 인물·빨간 기타·붉은 커튼·피아노·마이크 결합, 패널 누출 없음. 요청 medium보다 넓은 샷이며 얼굴은 작아 **정확 신원/청취 pending** |

[수정 시트](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_clean_sheet.png) · [공 성공 접촉시트](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_clean_sheet_contact.jpg) · [실제 영상](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_clean_sheet.mp4) · [공개 사례 재현 접촉시트](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_loopforge_contact.jpg) · [실제 영상](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_loopforge.mp4). API/history/run과 `validation/reviews/ingredients_*`에 실행·검수 증거가 있다. 실패 노트 FN-20261016-007도 원인과 복구 범위로 갱신했다.

정확한 시드/샘플러를 적용한 최종 비교본: [접촉시트](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_loopforge_exact_contact.jpg) · [영상](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_loopforge_exact.mp4). 앞선 부분 적용본의 설정 오류는 별도로 보존·공개했으며 이를 성공 재현으로 둔갑시키지 않았다.

## 공식·커뮤니티 근거와 신뢰 수준

| 출처 | 확인한 내용 / 로컬 비교 | 신뢰·한계 |
|---|---|---|
| [공식 모델 카드](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Ingredients), [공식 JSON](https://github.com/Lightricks/ComfyUI-LTXVideo/blob/master/example_workflows/2.5/LTX-2.5_ICLoRA_Ingredients_Single_Stage_Distilled.json) | 모델·버킷·참조·프롬프트 규약, 단일 단계 배선. 최소121/강도1부터 로컬 검증 | **높음**: 계약 근거. 특정 INT8 시트 결과 품질 보증은 아님 |
| [Loop Forge 기타 사례](https://loopforge.cc/projects/ltx-2-5-loras/guitarist-on-a-stage/) | 같은 distilled INT8 ConvRot+Gemma4 INT8+새2.5 Ingredients. RTX3060 12GB, 강도1.4,8단계 CFG++,seed42. 참조·JSON 공개 | **높은 재현성의 제3자 사례**: 파일을 내려받아 전체 노드·중첩 그래프 검사, 로컬 API로 재검증. 원래 UI 자체 실행/동영상의 비트 일치 재현은 아님 |
| Loop Forge JSON vs 페이지 | 페이지960×544지만 제공 JSON과1536×896 시트의 짧은변544/32반올림 계산은928×544. 로컬은 JSON 계산을 따름. decode temporal overlap16; 최종 저장만 VHS로 대체 | 공개 설정에도 불일치가 있으므로 “정확히 같은 결과”라고 주장하지 않음. source-manifest에 다운로드 파일 SHA 저장 |
| [Floyo2.5 공유 경로](https://www.floyo.ai/workflows/ltx-2-5-iclora-ingredients-for-refer-9zmb6zyv2p3a) | 새2.5 Ingredients+distilled bf16+Gemma4 bf16, CFG1/8단계, 패널 설명 강조. LoRA·IC guide·Repeat/Crop 노드 공개 | **중간**: 실제 워크플로우 소개지만 원시 JSON/정확 샘플러 미확인. API 인코딩 옵션도 있어 로컬 INT8 동일성 근거 아님. 3–4초 권고는2.5 카드 최소121 조건과 구분 |
| [Reddit2.5 업데이트](https://www.reddit.com/r/StableDiffusion/comments/1wdn4lf/ltx_silently_updated_the_ingredients_iclora_for/) | 2.5 릴리스 공유와 공식 데모에 대한 호평, 별도 workflow 요청 | **낮음**: 호평을 독립 재현 성공으로 집계하지 않음 |
| [Reddit Ingredients 시트 누출 토론](https://www.reddit.com/r/StableDiffusion/comments/1u8il10/lets_talk_about_the_ltx_new_ingredients_lora/) | 자체 시트는 박스 안 영상/시트혼합, 공식 시트는 성공한다는 경험. 구조적 패널 설명·강도1.5 제안 | **중간의 증상·가설 근거**: 주로2.3 사례. 새2.5 INT8의 확정 처방으로 사용하지 않음. 로컬은 공식 강도1에서도 복구 |
| [3090 24GB 장편 사용자 사례](https://www.reddit.com/r/comfyui/comments/1wcgswy/best_workflow_for_40_second_talking_videos_with/) | 2.5 distilled INT8+**2.3 Ingredients**+개인rank16 캐릭터 LoRA,960×544→×2/3단계,26×10초 사용자 보고 | **중간 이하**: 구체 설정이지만 개인 LoRA·다른 어댑터, JSON 미확인. 새2.5 파일의 직접 증거 아님. 링크된 YouTube 영상 자체는 직접 시청하지 않음 |
| [RTX4090 note 사례](https://note.com/kongo_jun/n/n3cbac07c8645) | dev INT8/bf16+distilled450 LoRA+Gemma4 INT8+**ConvVAE**, 새2.5 Ingredients;130초·큰 공유메모리 사용자 보고 | **중간**: 다른 스택의 성공/품질 한계 보고. dev나ConvVAE를 지금 추가해야 한다는 근거가 아님 |
| [Loop Forge 시트 누출](https://loopforge.cc/projects/ltx-2-5-loras/the-sheet-comes-through/) | 깨끗한 시트여도 패널누출. 추가 SlowMotion1.0가 켜진 사례 | **중간**: 입력 정리만으로 모든 문제가 해결되진 않는다는 근거. Ingredients 단독 실패로 일반화 불가 |
| HF [discussion1](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Ingredients/discussions/1), [discussion2](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Ingredients/discussions/2) | 학습데이터 요청, 공식 workflow 링크 안내 | 실행 설정·해결 로그 없음. 성공/실패 실험으로 집계하지 않음 |

GitHub 이슈 검색에서는 이 새2.5 INT8 Ingredients 조합의 확정 버그·패치를 찾지 못했다. 예전 LTX-2 CLIP 오류와2.3 feature request를 현재 원인으로 오인하지 않았다. 사용자 제공 YouTube 리뷰 `xCV2zVJKA5k`는 웹 조회 실패로 내용·21:13 시연을 직접 확인하지 못했으므로 인용하지 않는다.

제3자 JSON 전체의 실제 노드 클래스는 모두 로컬 스키마에 있었다. 두 UUID는 포함된 subgraph 정의이며 누락 플러그인이 아니다. 코드 실행·설치·다운로드·HTTP/API 송신 노드나 URL 문자열은 없었다. 기존 모델 이름, IC guide, sampler, 디코드, 파일 저장으로만 이뤄진 데이터 그래프다. 원시 제3자 코드를 실행하지 않고 확인한 설정을 자체 API에 반영했다. 표준 Comfy 연산식은 min/round/기본산술뿐이었다. 다운로드 원본과 SHA: `community_research/source-manifest.json`.

## 사용 경로·남은 한계

`F:/Agent_media_tools/scripts/generate_ltx25_official.py --task ingredients`는 이제 기본5초/768×448, untiled 참조 인코딩, 강도1/Euler ancestral로 동작한다. 기존 다른 task 기본값은 그대로다. `--adapter-strength 1.4 --sampler euler_ancestral_cfg_pp`는 커뮤니티 비교용 명시 옵션이며 기본을 바꾸지 않는다.

```powershell
python scripts/generate_ltx25_official.py --task ingredients -i C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_clean_sheet.png -p "Reference sheet: Top center is the red/yellow toy ball; bottom is an empty pale wooden table and gray wall. Generated video: One ball rolls from left to right across the full-frame tabletop, static camera." --seed 4747 -o F:/my_project/ingredients.mp4
```

정확히 검증한 긴 프롬프트는 `ingredients-clean-prompt.txt`, 실제 API는 `validation/ingredients_clean_sheet.mp4.api.json`이다. 위 짧은 예시는 형식 안내이며 같은 결과를 보장하는 검증 호출로 표시하지 않는다. 입력 시트를 첫 프레임으로 강제하지 않는다. 바깥 프로젝트 출력·공유GPU 큐 검사·성공/품질 분리 규칙을 유지한다.

현재 해결 범위는 **연결·소품/장소 결합·해당 시트누출 복구**다. 인물 얼굴을 정확하게 유지하는 제작 목적, 여러 얼굴, 복잡한 손 연주, 음성/음악 청취는 추가 목적별 검증이 필요하다. 같은 시드 재뽑기나 대형 모델 추가 없이 복구했으며, 지금 단계에 새 모델·노드·업데이트는 필요하지 않다.

## 모델 이동 검증

최종 단일 경로: `F:/model/loras/LTX2.5/ltx-2.5-22b-ic-lora-ingredients-0.9.safetensors`.
Downloads 동일 파일은 사용자 이동 요청에 따라 제거됐고 대상 파일은 존재한다. 크기1,308,787,472바이트, 로컬 SHA256 `ff873a5beada3c579a8137c7c53343916f78bcc9a529ba910143073fe8715e95`; 복사 후 원본·대상 전체 해시 일치를 확인한 뒤 정확한 원본만 제거했다. [기존 이동 증거](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/ingredients-local-verification.json). 공식 upstream SHA 비교는 메타데이터 비공개로 미확인이고, 이 로컬 해시는 이동 무결성 증거다. HF 인증·라이선스 동의 변경 없음.
