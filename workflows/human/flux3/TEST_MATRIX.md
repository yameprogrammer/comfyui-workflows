# FLUX3 통합 테스트 매트릭스

2026-10-16. 최종 실행 대상은 **F:\ComfyUI_windows_portable / http://127.0.0.1:8188**. Python3.13.12/Torch2.13cu130/transformers4.57.3 유지, ComfyUI0.41.1. 공식모델3개 SHA256/헤더 검증 완료.

6종 모두 실제 추론과 PNG 디코딩 성공. 최종 시각 QC **5종 통과, style1종 strict QC 실패(실험)**. 브라우저 UI 직접 import/Queue는 도구 초기화 오류로 미검증; UI/API의 모델·파라미터·연결과 설치 파일 동일성은 정적 대조한다.

## 원래8188의 기능별 실제 결과

공통: distilled INT8,16steps,CFG1,euler/simple,batch1. character seed271828, 나머지314159. 각 `.api.json`/`.history.json`/`.result.json`에 재현설정과 참조SHA 기록.

| 모드 | 해상도 | 호출→저장(s) | 관측 GPU최대(MiB) | 시각QC | 출력 |
|---|---:|---:|---:|---|---|
| t2i | 1024×1024 | 5.688 | 11866 | pass | `F:\Agent_media_sandboxes\flux3\validation\production\t2i.png` |
| single_edit | 1024×1024 | 5.625 | 13325 | pass | `F:\Agent_media_sandboxes\flux3\validation\production\single_edit.png` |
| multi_reference | 1344×768 | 8.781 | 14915 | pass | `F:\Agent_media_sandboxes\flux3\validation\production\multi_reference.png` |
| character_consistency | 768×1024 | 4.687 | 13077 | pass | `F:\Agent_media_sandboxes\flux3\validation\production\character_consistency.png` |
| style_consistency | 1024×1024 | 5.688 | 13215 | fail | `F:\Agent_media_sandboxes\flux3\validation\production\style_consistency.png` |
| box_layout | 1024×1024 | 2.579 | 14809 | pass | `F:\Agent_media_sandboxes\flux3\validation\production\box_layout.png` |

Multi-reference의 첫 square 시험은 손잡이 가림/크기 불일치로 실패했고, 가로 캔버스와 분리 soft-box 지시로 수정본 통과. Character의 첫 정원 전환은 원래 벽이 남아 실패했고, 전체 배경 교체 지시와 portrait해상도로 수정본 통과. Single edit는 색/구도 통과이나 무광보다 광택이 강한 재질 한계가 있다. Box는 좌우 배치를 따르지만 hard mask/정확한 경계 보장은 아니다.

Style은1MP에서 사진 질감 잔존,0.25MP에서 donor 구도·내용 복사,0.5MP에서도 강한 수채화 전이 미충족.4회 실제 시도와 실패 QA를 보존했다. 추가 BASE/upsampler/다른 모델로 범위를 늘리지 않았다.

## Agent_media_tools 정상 호출 검증

CLI `scripts/generate_flux3.py` → `lib/flux3_runner.py` → 기존 `comfy_engine_session.ensure_engine` → 원래8188. 기본프로파일 `flux3-production`; 선택 `flux3-isolated`는8193. API/UI6종, catalog7항목, intent카드와 가이드/이력 등록.

| 도구 호출 | 시간(s) | GPU최대(MiB) | 서버/결과 |
|---|---:|---:|---|
| toolbox_t2i | 11.984 | 15093 | http://127.0.0.1:8188; success; QC pass |
| toolbox_single_edit | 8.453 | 13147 | http://127.0.0.1:8188; success; QC pass |

T2I는 Qwen→FLUX3 전환의 free_on_switch, 편집은 skip_same_family를 실제 기록했다. 전체 시간은 모델 준비·업로드·샘플링·디코딩·메모리 게이트를 포함하며 순수 diffusion시간이 아니다. 등록 CLI로 재생성한 T2I는 sampler cache 없이 원래 T2I와 픽셀 SHA가 정확히 일치했다.

## 대표 기존 경로 회귀

| 경로 | 실행 | 총시간(s) | 관측최대(MiB) | 출력/범위 |
|---|---|---:|---:|---|
| krea | execution_success | 9.625 | 19286 | `F:\Agent_media_sandboxes\flux3\validation\regression\krea.png`; QC pass |
| qwen | execution_success | 37.016 | 19715 | `F:\Agent_media_sandboxes\flux3\validation\regression\qwen.png`; QC pass |
| h3 | execution_success | 24.735 | 21485 | `F:\Agent_media_sandboxes\flux3\validation\regression\h3.mp4`; QC fail_input_aspect_fixture |
| h3_square | execution_success | 23.391 | 21624 | `F:\Agent_media_sandboxes\flux3\validation\regression\h3_square.mp4`; QC pass |
| yue2 | execution_success | 4.484 | 11173 | `F:\Agent_media_sandboxes\flux3\validation\regression\yue2.wav`; QC technical_pass_listening_unavailable |

Krea2: 기존krea2_t2i_v10의512² 짧은 생성. Qwen: 기존편집8step의녹색변경. H3:2초요청은grid에따라2.333초/56프레임; 처음 square→16:9 시험의 비율변형은 테스트설정 실패로 남기고 동일종횡비 재시험을 별도로 기록한다. YuE2:4초/8step/min-duration3s의 실행·오디오 디코딩·non-silence 기술검사. 오디오 입력을 모델이 청취할 수 없어 음악장르/청감 품질은 미검증이며 완성곡 QC 통과로 표시하지 않는다. 이 범위는 모든 기존모델/해상도/긴영상의 exhaustive 회귀가 아니다.

## 보존·정적검사·잔여사항

- 전체 코드/custom_nodes/user/config 및embedded Python 백업: `F:\backups\ComfyUI_before_flux3_20261016`. 기존3개 로컬패치 재적용, 원래런처/데이터경로 유지.
- 필수8개패키지만 변경; Torch/torchvision/transformers는 그대로. 기존 pip충돌은 신규충돌 여부만 비교하고 무관한 기존 의존성을 수리하지 않음.
- 기존노드4603→4628, 이전 외부API노드OpenAIVideoSora2 하나가 목록에서 사라짐. 로컬 회귀와 구분하며 유료API는 실행하지 않음.
- VRAM은약0.5초 간격 nvidia-smi의GPU전체 사용량(다른 앱 포함) 관측최대, 정확한CUDA peak가 아님.
- 브라우저 UI Queue 미검증, strict style QC 실패, 오디오청감 미검증을 통과로 바꾸지 않음.
- 모델은F:\model의flux3 전용 물리 폴더로 중복없이 공유; 기존 동명VAE는 보존.

전체 재현·실패·QA 근거: `validation-results.json`, `F:\Agent_media_sandboxes\flux3\validation` 및 준비 폴더의 `evidence/`.

최종 정상 대기 확인: queue_idle=True, GPU사용량/활용률=2327, 20 (MiB/%), 원래8188/v0.41.1, 시험8193 listener=0. 새 실행은 넣지 않고 종료 시 모델메모리를 회수했다.

옵시디언: `C:\Users\parkp\ai-vault\projects\comfyui_workflows.md`의 FLUX3 운영 절에 기록하고 기존 INDEX 포인터를 갱신했다. 새 중복 메모 없음. 가이드·모델경로·6쌍 배포동일성 및 기존 문서보존 검사는 `final-static-checks.json` 참조.
