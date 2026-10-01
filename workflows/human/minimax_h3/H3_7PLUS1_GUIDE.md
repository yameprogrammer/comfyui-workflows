# MiniMax H3 R2V 7+1 — 에이전트 사용 가이드

이미지 레퍼런스로 인물과 스타일을 유지하는 H3 R2V 작업은 `generate_minimax_h3_7plus1`을 우선 선택한다. 기본은 `work`, `dense`, 5초다. 이 도구는 첫 프레임을 고정하는 I2V와 다르다.

| 항목 | 구성 |
|---|---|
| 모델 | Singularity ref2va Pruned v1.3 INT8 |
| LoRA | DMD ref2va 8-step turbo pruned, strength 1.0 |
| 샘플링 | Euler / simple / 8스텝 / video shift 12 / audio shift 3 |
| 구조 | 저해상도 7스텝 → 3D 잠재 공간 x2 → 고해상도 1스텝 |
| 메모리 | 텍스트 인코더 언로드, 마지막 단계 H3 Memory Optimization, 디코딩 전 VRAM Debug |
| 오디오 | H3가 생성한 오디오를 디코딩·저장. 외부 WAV를 입힌 A2V가 아님 |
| 워크플로 SSOT | `workflows/agent/presets/minimax_h3_7plus1*.api.json` 및 `.ports.json` |

## 실행

cwd는 `F:\Agent_media_tools`. 출력·리뷰·프롬프트 파일은 호출하는 프로젝트에 둔다. 아래 `F:/my_project`를 실제 프로젝트 경로로 바꾼다. ComfyUI portable Python을 사용할 경우 `python` 대신 `F:/ComfyUI_windows_portable/python_embeded/python.exe`를 사용한다.

```bat
python scripts/generate_minimax_h3_7plus1.py -i F:/my_project/stills/hero.png --prompt-file F:/my_project/prompts/S01.txt -o F:/my_project/clips/S01.mp4 --seed 42
python scripts/generate_minimax_h3_7plus1.py -i F:/my_project/stills/hero.png --prompt-file F:/my_project/prompts/S01.txt --profile 1080 -o F:/my_project/clips/S01_1080.mp4 --seed 42
python scripts/generate_minimax_h3_7plus1.py --ref-image F:/my_project/stills/hero.png --ref-image F:/my_project/stills/style.png --prompt-file F:/my_project/prompts/S02.txt -o F:/my_project/clips/S02.mp4
python scripts/generate_minimax_h3_7plus1.py --list-profiles
```

| 프로필 | 시작 해상도 | 최종 해상도 | 기본 길이 |
|---|---:|---:|---:|
| `work` | 672×384 | 1344×768 | 요청 5초 → 124프레임, 약 5.167초 |
| `1080` | 960×544 | 1920×1088 | 동일 |

각 변의 x2는 픽셀 수 x4다. 1088 높이는 모델 정렬에 따른 값이며 정확한 1080 납품은 후처리에서 crop/resize한다. 첫 작업은 `work`로 확인하고 최종 출력에서 `1080`을 선택한다. `--duration`, `--ref-image-size max`, 여러 참조 이미지는 추가 메모리를 요구할 수 있다. 검증된 기본은 참조 한 장·5초·`match`다.

`--attention sol`은 **마지막 고해상도 1스텝에만** Sol을 적용한다. 앞 7스텝에는 적용하지 않는다. 1MP 테스트의 추가 이득이 약 4%였으므로 기본은 `dense`다. Sol은 별도 후보로 비교·검수한다.

`--dry-run`은 프로젝트에 패치된 `.api.json`만 저장한다. Comfy 요청이나 이미지 복사는 하지 않으므로 해당 JSON의 이미지 이름은 실제 실행 전 placeholder다. 정상 실행은 `.mp4`, 실행한 `.api.json`, 모델·시드·시간·prompt_id를 포함한 `.meta.json`을 프로젝트에 남긴다. 캐시를 자동으로 비우거나 다른 작업을 중단하지 않는다.

## 프롬프트와 검수

생성 전 `skills/generation-prompt/SKILL.md`와 `references/minimax_h3.md`를 따른다. 참조 입력 순서가 `<Picture 1>`, `<Picture 2>` 순서이며 각 이미지 역할을 지정한다. 예시:

```text
subject_definitions: <Subject 1> is the person in <Picture 1>; preserve identity and outfit.
summary: [reference generation] Subject 1 gives a brief greeting in the setting of <Picture 1>.
retention_analysis: <Picture 1> fully_preserved - identity, style, wardrobe and setting.
detailed_description: [Shot 1] Medium close-up, locked tripod. Subject 1 blinks, turns slightly to her right, then looks back with a small smile. Subject 1 (S1) says: <d>[Korean] 안녕하세요.</d>
overall_soundscape: Quiet ambience, one clear speaking voice as written.
non_diegetic_music: N/A
```

생성 직전 `failure_note.py before`, 생성 직후 `output-review`의 pack → 파일 열기 → record를 진행한다. exit 0은 파일 생성 성공이다. 얼굴·안경·의상 유지, 끝까지 실제 움직임, 워프, 길이, 오디오, 대사·립싱크를 작업 요구에 맞게 확인한다.

## 도구 선택과 대안

| 상황 | 선택 |
|---|---|
| 이미지 참조 H3 R2V 반복 제작 | 이 도구 `work` 우선, 납품 후보는 `1080` |
| 새 방식에서 동작·인물이 무너짐 | 원인 검토 후 기존 `generate_minimax_h3 --task r2v --profile native_fast`와 같은 조건 비교 |
| 시작 프레임 고정 I2V, T2V, 첫/끝 프레임 FLF | 기존 `generate_minimax_h3`의 해당 task |
| 잠긴 3D 카메라/참조 영상 | `camera-previz`를 먼저 읽고 기존 `generate_minimax_h3 --task r2v --ref-video plate.mp4` |
| 외부 녹음에 정확한 립싱크 | `generate_s2v` 등 해당 작업 도구. 이 도구를 A2V로 부르지 않는다 |

```bat
python scripts/generate_minimax_h3.py --task r2v -i F:/my_project/stills/hero.png --prompt-file F:/my_project/prompts/S01.txt --profile native_fast -o F:/my_project/clips/S01_baseline.mp4
python scripts/generate_minimax_h3.py --task i2v -i F:/my_project/stills/start.png --prompt-file F:/my_project/prompts/S01.txt -o F:/my_project/clips/S01_i2v.mp4
```

등록 CLI의 추가 통합 실행에서도 5초 작업이 57.48초에 생성되었다. 출력 MP4·실행 API·메타데이터 저장을 확인했다. 네이티브 오디오는 납품 전 청취와 레벨 검수가 필요하며, 통합 샘플의 float 디코딩 peak는 약 1.137이었다. 정확한 대사·립싱크와 완전한 카메라 고정은 이 테스트로 인증하지 않는다.

## 실증 근거와 범위

2026-10-02, RTX 4090 24GB·RAM 64GB·ComfyUI 0.37.0. 동일 이미지·프롬프트·시드로 각 구성의 전체 그래프를 1회 실행했다. execution_cached는 빈 목록이다. OS 디스크 캐시와 백그라운드 프로세스는 통제하지 않았다.

| 구성 | 출력 | 생성 시간 |
|---|---|---:|
| 기존 15+5 구조 R2V | 1344×768 | 113.9초 |
| Singularity 7+1 Dense | 1344×768 | 56.6초 |
| Singularity 7+1 Sol | 1344×768 | 54.3초 |
| Singularity 7+1 Dense | 1920×1088 | 120.5초 |

기본 새 구성에서 약 50% 시간 감소를 관찰했다. 이는 모델·LoRA·스텝·메모리 처리를 함께 바꾼 파이프라인 비교이며 개별 요소 효과를 분리한 실험이 아니다. 최대 전체 GPU 사용량은 약 23.5GB로 비슷했다. 큰 VRAM 절감이나 모든 장면의 2배 속도를 보장하지 않는다.

검증 장면은 애니메이션 인물 한 명의 작은 머리·입 움직임이다. 얼굴·안경 유지와 프리즈 없음은 프레임으로 확인했다. 손, 빠른 동작, 실사, 긴 영상, 정확한 대사·립싱크는 미검증이다. 여러 이미지, `max`, 긴 duration도 별도 검수가 필요하다. 기계 판독 측정 기록은 `H3_7PLUS1_BENCHMARK.json`에 보관한다.

## 설치된 의존성과 UI

ComfyUI ≥0.33.0, Deno Custom Nodes, H3-Optimizations, KJNodes, VideoHelperSuite, MiniMax H3 latent upscaler가 필요하다. 현재 검증 PC에는 설치되어 있다. 필요한 노드나 모델이 없으면 설치 필요를 보고하고 다른 모델로 조용히 바꾸지 않는다.

모델은 `F:\model` 공유 경로를 사용한다. Singularity 모델, `H3_71_validation/experimental`의 DMD ref2va LoRA, 기존 Qwen3VL NVFP4 AWQ 인코더와 H3 VAE·3D upscaler를 재사용한다. 가중치나 API 전체 스텝을 임의 변경해도 이 도구 이름으로 검증된 구성이라고 표시하지 않는다.

ComfyUI의 **Workflows → H3_71_validation**에 1MP·1080·Sol UI가 저장되어 있다. 휴먼 원본 복사본은 이 가이드와 같은 폴더다. 기존 워크플로우는 유지한다.
