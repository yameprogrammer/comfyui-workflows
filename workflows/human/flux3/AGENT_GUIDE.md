# FLUX3 Klein — PC-HOME 원래 portable 통합

2026-10-16. 기본은 **distilled INT8 /16steps/CFG1/euler/simple/batch1**, 별도 prompt upsampler 없이 에이전트가 상세 영문 장면 캡션을 작성한다. NVFP4/BASE/추가 모델은 설치하지 않았다.

**검증 범위:** 6종 API의 실제 추론·PNG 디코딩 완료. T2I, single edit, multi-reference, character, box의 수정된 샘플은 시각 QC 통과. **style은 API 실행 성공이나 엄격한 내용보존+수채화 전이 QC 실패로 실험 기능**이다. UI/API6쌍의 모델·값·연결 정적 동등성 및 서버 노드 등록은 확인했으나, 브라우저 도구 오류로 UI 직접 import/Queue는 미검증이다. UI 실행까지 완료했다고 해석하지 말 것.

## 위치와 시작

- 기본 서버: http://127.0.0.1:8188 — 사용자의 기존 ComfyUI 경로.
- 코드: `F:\ComfyUI_windows_portable\ComfyUI` v0.41.1, commit `45bf90d1c91eecd782643346dcfb73cb0017667f` + 보존한 로컬 수정3개.
- 실행 환경: `F:\ComfyUI_windows_portable\python_embeded\python.exe`, Python3.13.12, torch2.13.0+cu130, torchvision0.28.0+cu130, transformers4.57.3 유지. comfy-kitchen0.2.37, comfy-aimdo0.5.6 및 frontend/templates/docs 관련8개 패키지만 변경했다.
- 원래 실행: `F:\ComfyUI_windows_portable\run_nvidia_gpu.bat`. 기존 async-offload2/reserve-vram3/vram-headroom2와 input/output/temp 설정을 유지했다.
- 최종 모델 물리 폴더: `F:\model\diffusion_models\flux3`, `F:\model\text_encoders\flux3`, `F:\model\vae\flux3`. 사전검증 폴더에서 이동 후 공식 SHA256을 다시 확인했으며 현재 junction 의존성 없이 공용모델경로에 보관한다. 추가 다운로드/중복복사/기존 동명VAE 덮어쓰기는 없다. 모델 loader명은 `flux3\파일명`.
- 사용자 Downloads의 필수3개를 공식 크기/SHA256/헤더 검증 후 사전검증 경로로 이동했고, 최종 공용모델경로로 정리 후 다시 검증했다. `model-move-map.json`, `model-final-move-map.json`, `shared-model-namespace.json`에 원본·중간·최종경로 기록.
- 사전 검증 루트: `F:\Agent_media_sandboxes\flux3`. venv는 생산과 같은 transformers4.57.3으로 재검증했으며 격리8193 서버는 검증 후 중지했다. 필요할 때 `Start-Flux3.ps1`로 별도 실행 가능하다.
- API SSOT: `F:\Agent_media_tools\workflows\agent\flux3\*.api.json`
- UI: `F:\Agent_media_tools\workflows\human\flux3\*.json`. 원래 ComfyUI의 `user/default/workflows/flux3`에도 등록한다. 기본8188 UI에서 연다. 샘플 참조는 `F:\ComfyUI_data\input\flux3_*.png`에 두며 사용자 이미지로 교체할 수 있다.
- 검증 결과: `F:\Agent_media_sandboxes\flux3\validation` (PNG, 실제API, history, 측정JSON, reviews).
- 검증 표: 같은 가이드 폴더의 `TEST_MATRIX.md` 및 `validation-results.json`.

## Agent_media_tools 호출

repo root에서 실행하며 결과는 항상 toolbox 밖 프로젝트로 지정한다. 기본 `--profile flux3-production`은8188이며, 선택형 `--profile flux3-isolated`는8193이다. 두 서버를 동시에 GPU작업에 사용하지 않는다.

```powershell
Set-Location F:\Agent_media_tools
python scripts/generate_flux3.py --mode t2i --prompt-file workflows/human/flux3/prompts/t2i.txt -o F:\my_project\stills\new.png
python scripts/generate_flux3.py --mode single_edit --prompt-file workflows/human/flux3/prompts/single_edit.txt -i F:\my_project\stills\new.png -o F:\my_project\stills\edit.png
python scripts/generate_flux3.py --mode multi_reference --prompt-file workflows/human/flux3/prompts/multi_reference.txt -i F:\my_project\stills\new.png -i F:\my_project\stills\edit.png -o F:\my_project\stills\multi.png
python scripts/generate_flux3.py --mode character_consistency --prompt-file workflows/human/flux3/prompts/character_consistency.txt -i F:\my_project\person.png -o F:\my_project\garden.png
python scripts/generate_flux3.py --mode style_consistency --prompt-file workflows/human/flux3/prompts/style_consistency.txt -i F:\my_project\content.png -i F:\my_project\style.png -o F:\my_project\styled.png
python scripts/generate_flux3.py --mode box_layout --prompt-file workflows/human/flux3/prompts/box_layout.txt -o F:\my_project\layout.png
```

예제 캡션은 샘플용이므로 실제 소재에 맞춰 바꾼다. `-p`도 사용 가능하다. `--dry-run`은 API만 저장하며 추론하지 않는다.

기본 크기는 T2I/단일편집/style/box가1024², multi가1344x768, character가768x1024다. `--width/--height`로16배수 크기를 지정하고 `--seed`, `--steps`로 설정을 변경한다. UI와 CLI는 같은 API JSON의 기본값을 따른다. style 참조는 기본0.5MP, 나머지는1MP이며 `--ref-megapixels`로 변경한다.

호출자는 입력 이미지를 로컬 서버에 업로드하고, 큐/작업 잠금을 확인한 후 하나씩 실행한다. `.api.json`, `.history.json`, `.result.json`을 PNG와 함께 저장한다. production8188의 큐도 사전 확인하지만, 다른 도구가 검사 직후 별도 작업을 시작하는 경쟁까지 막지는 못하므로 모든 GPU 호출자가 직렬 사용 원칙을 지켜야 한다. 타임아웃은 서버작업을 강제 종료하지 않는다. 잠금이 남았다면 큐/history를 먼저 확인하고 실제 작업 중에는 제거하지 말 것.

## 프롬프트·참조

FLUX.1/FLUX.2의 짧은 프롬프트 규칙을 그대로 쓰지 않는다. FLUX3 공식 카드/시스템프롬프트에 맞춰 보통100~350단어의 구체적인 장면을 작성한다: medium, 구도, 대상 수와 위치, 외형·재료, 조명, 배경. 편집은 결과 장면과 변경할 내용, 보존할 내용을 구체적으로 쓴다. style은 이름보다 palette/stroke/texture를 묘사한다.

최대10장까지 `-i` 반복 가능. `<ref_image_0>`, `<ref_image_1>` 순서로 각 역할을 지시한다. `ReferenceMultiLatent`로 positive/negative 양쪽에 같은 참조를 연결한다. 기본 출력 크기는 독립 `EmptyFlux2LatentImage`로 설정하므로 첫 참조의 종횡비에 종속되지 않는다. 원본 공식 editing template의 reference-latent 출력 크기 경로와 이 점이 다르다.

box는 캡션 뒤 JSON 배열로 `[top,left,bottom,right]` 0~1000 좌표를 붙인다. id는 캡션의 `<id>`에 대응시킨다. **soft guidance**로 실제 픽셀 경계나 영역외 불변을 보장하지 않는다. 이 패키지는 ControlNet/mask-inpainting/Fill/LoRA 로딩을 지원 확인하지 않았다. BASE의 LoRA 학습 연구 용도와 호환 LoRA 실행 워크플로우를 혼동하지 않는다.

## 실제 발견한 한계와 QC

- Single edit: 색상 변경과 구도 보존은 좋았으나 무광 요청보다 광택이 강해질 수 있다.
- Multi-reference: square에서 작은 대상/손잡이가 가려졌다. 가로 캔버스, 같은 크기, 간격과 soft boxes를 명시하여 수정본 통과.
- Character: 얼굴/안경/머리/의상 보존은 좋았으나 원본 배경이 남았다. 전체 배경 교체와 새 장면을 명시하여 수정본 통과. 생체인식/ID잠금 보장은 하지 않는다.
- Style:1MP에서는 사진 질감 잔존,0.25MP에서는 donor 내용·구도로 드리프트,0.5MP도 강한 수채화 전이 미충족. 이 샘플의 strict QC는 실패다. 사용자가 다른 reference/목표를 쓰면 결과가 달라지므로 매번 파일을 열어 검수한다. 추가 BASE/모델의 품질 개선은 아직 시험하지 않았다.
- 실행 후 generation-prompt/output-review 및 `review_media pack/record` 사용. 실패노트 FN-20261016-001~005에 수리 근거를 남겼다. exit0만으로 통과라고 하지 않는다.
- VRAM 수치는0.5초 간격 nvidia-smi의 **GPU전체 사용량** 관측 최대치로 다른 앱을 포함하며 CUDA 정확한 peak가 아니다. `--cache-none`로 실제 재샘플링한 seed 재현 결과의 픽셀SHA가 정확히 일치했다. 다른 장치/버전의 bitwise 재현은 보장하지 않는다.

## 보존·약관

사용자의 최종 통합 승인 후 `F:\ComfyUI_windows_portable` 코드를 v0.41.1로 업데이트하고8필수패키지만 변경했다. 기존 로그 오류 처리와 YuE2 min_duration/min_tokens 패치3개를 보존했고, 원래 런처·데이터 경로·Torch·transformers를 유지했다. 유휴큐를 확인하여8188을 통제 재시작했다. Agent_media_tools에는 FLUX3 새 파일과 검색·카탈로그·가이드·이력만 추가하며 기존 변경분을 보존한다. 기존 공용 VAE는 공식 팩과 해시가 달라 덮어쓰지 않았다.

전체 코드/custom_nodes/user/config 및 embedded Python 백업: `F:\backups\ComfyUI_before_flux3_20261016` (약12.1GB). 원래 HEAD `f427c3a285502cc452bbf134b810668844b79ffa`, 로컬수정은 `production-local.patch`, 기존패키지는 `installed-packages.json`. 롤백은 활성큐가 없는 상태에서 서버를 멈추고, 현재 환경을 별도 보존한 뒤 코드HEAD와 로컬패치, embedded Python을 같은 백업시점으로 함께 복원한다. 기존모델/input/output은 백업복원으로 덮어쓰지 않는다. 기존 `tools/restore_env.ps1`의 단순 overlay는 새 패키지 잔재를 지우지 않으므로 완전한 Python 롤백은 현재폴더 보존 후 백업폴더를 새로 복원하는 방식이 필요하다.

기존 pip check 충돌은 작업 전후 별도 기록하며 이번 모델 추가 범위에서 무관한 기존패키지를 일괄 수리하지 않는다. 노드 등록 비교에서 기존 외부 API 노드 `OpenAIVideoSora2`가 사라진 것은 잔여 호환성 차이로 기록한다. 유료 외부API를 실행해 검증하지 않았다. 로컬 대표 회귀 실행 범위와 결과는 TEST_MATRIX.md를 따른다.

사용자가 HF에서 직접 동의·다운로드한 공식 모델을 사용한다. 토큰 읽기/출력/생성이나 새 인증은 수행하지 않았다. 모델은 [FLUX Kommunity v1.0](https://huggingface.co/black-forest-labs/flux-3-image-klein/blob/main/LICENSE.md): 비상업 사용과 qualifying user(계열사 포함 연간총수익US$5M미만 등)의 상업 출력 예외를 구분하고, 출력검토/해당 법률상AI표시 등 전체약관을 따른다. 단순 무제한상업 오픈소스라고 소개하지 않는다.

공식 근거: [모델 카드](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy), [Comfy 가이드](https://docs.comfy.org/tutorials/flux/flux-3-klein), [원본 템플릿](https://github.com/Comfy-Org/workflow_templates). 모델·템플릿 고정커밋/원본과 설치 증거는 준비 작업 폴더에 보관한다.
