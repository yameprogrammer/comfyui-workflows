# MiniMax H3 개선 도구 — 에이전트 우선 경로

MiniMax H3 생성은 `generate_minimax_h3_optimized`를 먼저 사용한다. cwd는 `F:/Agent_media_tools`, 결과는 호출하는 프로젝트의 MP4 경로다. R2V는 기존 검증된 프리셋을 그대로 재사용한다. 별도 R2V 복사본은 없다.

```bat
python scripts/generate_minimax_h3_optimized.py --task t2v --aspect 9:16 --prompt-file F:/my_project/prompts/S01.txt -o F:/my_project/clips/S01.mp4
python scripts/generate_minimax_h3_optimized.py --task i2v -i F:/my_project/stills/start.png --aspect 9:16 --prompt-file F:/my_project/prompts/S02.txt -o F:/my_project/clips/S02.mp4
python scripts/generate_minimax_h3_optimized.py --task flf -i F:/my_project/stills/start.png --last F:/my_project/stills/end.png --prompt-file F:/my_project/prompts/S03.txt -o F:/my_project/clips/S03.mp4
python scripts/generate_minimax_h3_optimized.py --task r2v -i F:/my_project/stills/hero.png --aspect 9:16 --duration 8 --prompt-file F:/my_project/prompts/S04.txt -o F:/my_project/clips/S04.mp4
python scripts/generate_minimax_h3_optimized.py --task v2v --ref-video F:/my_project/refs/plate.mp4 --prompt-file F:/my_project/prompts/S05.txt -o F:/my_project/clips/S05.mp4
python scripts/generate_minimax_h3_optimized.py --task ai2v -i F:/my_project/stills/hero.png -a F:/my_project/refs/voice.wav --audio-start 0 --aspect 9:16 --prompt-file F:/my_project/prompts/S06.txt -o F:/my_project/clips/S06.mp4
python scripts/generate_minimax_h3_optimized.py --list-profiles
```

Portable Python: `F:/ComfyUI_windows_portable/python_embeded/python.exe`를 `python` 대신 사용할 수 있다. R2V·AI2V는 `-i`를 반복해 이미지 최대 9장을 지정한다. FLF는 `-i 시작 --last 끝`이다. V2V는 영상 하나와 연결된 soundtrack을 참조한다. AI2V의 오디오는 요청 길이만큼 잘라 참조한다. 프롬프트에서 각 `<Picture n>`, `<Video 1>`, `<Audio 1>`의 역할을 명시한다.

| 작업 | 구성 |
|---|---|
| T2V / I2V / FLF | 설치된 FL2VA, res_multistep 20스텝, 저해상도 15 + latent x2 + 고해상도 5 |
| R2V / V2V / AI2V | Singularity REF2VA + R2V DMD LoRA, Euler 8스텝, 저해상도 7 + latent x2 + 고해상도 1 |

공통: 텍스트 인코더 언로드, 고해상도 H3 Memory Optimization, 샘플링 후 모델 전체 언로드 → 영상·오디오 VAE → MP4 저장. FL2VA의 첫 패스도 메모리 최적화한다. I2V/FLF는 확대된 크기에 맞춰 고해상도 프레임 조건을 다시 만들어 크기 불일치를 방지한다.

| 프로필 | 가로 시작 → 출력 | `--aspect 9:16` 시작 → 출력 |
|---|---|---|
| draft | 512×288 → 1024×576 | 288×512 → 576×1024 (정확한 9:16) |
| work (기본) | 672×384 → 1344×768 | 384×672 → 768×1344 |
| 1080 | 960×544 → 1920×1088 | 544×960 → 1088×1920 |

`--width`와 `--height`는 **첫 패스 크기**이며 최종 크기는 x2다. 둘 다 32의 배수로 지정한다. work/1080은 정확한 16:9·9:16과 약간 다르므로 납품 때 비율을 맞춘다. 기본 5초, 권장 단일 클립 최대 8초. 요청 5/7/8초는 각각 약 5.167/7.292/8초로 정렬된다. `--attention sol`은 기존 R2V의 마지막 단계에만 지원하며 기본은 dense다.

V2V는 참조를 통한 새 생성이다. 원본 픽셀을 denoise strength로 변환하거나 정확한 카메라 경로를 보장하지 않는다. AI2V는 원본 오디오를 최종 영상에 덮어씌우지 않으며 원본 문장·립싱크·성우 음색의 정확한 재현은 별도 검수한다. 원하는 대사는 프롬프트에도 작성한다.

`--dry-run`은 프로젝트에 실행 그래프만 저장한다. 입력을 복사하거나 Comfy 작업을 제출하지 않는다. 실제 실행은 프로젝트에 `.mp4`, `.api.json`, `.meta.json`을 남기며 원본 입력을 고유한 이름으로 Comfy 입력 폴더에 복사한다. 실행 옵션이나 NVIDIA 설정을 자동 변경하지 않는다. 이 PC의 성공 기준 환경은 Dynamic VRAM 켜짐 / async offload 꺼짐 / Python CUDA 시스템 비대체 선호다.

## 대안과 검수

- 새로운 일반 H3 생성: 이 도구 우선. 가로만 있다는 이유로 기존 20스텝 단일 패스로 복귀하지 않는다.
- 기존 R2V 자동화 호환: `generate_minimax_h3_7plus1` 유지. 새 CLI의 R2V는 동일 프리셋에 세로·크기 옵션을 추가한 경로다.
- polish / carry-from / 혼합 다중 영상·오디오 참조 / 카메라 잠금 입력 조합: 해당 기능이 필요한 이유를 기록하고 기존 `generate_minimax_h3` 또는 camera-previz 경로를 사용한다.
- 원본 WAV를 유지하는 제작용 정확한 대사 립싱크: `generate_s2v` 등 작업 요구에 맞는 도구를 선택한다.

생성 전 failure_note와 generation-prompt, 생성 후 output-review로 영상·음성·동작·얼굴·대사를 검수한다. CLI 성공은 저장 성공이며 품질 승인과 다르다.

## 검증 범위

2026-10-03 RTX 4090에서 새 5가지 입력 방식은 요청 0.9초/22프레임, 최종 576×1024의 실제 생성·MP4 저장·오디오 포함·첫 프레임 디코딩을 통과했다. T2V 21.06초, I2V 30.23초, FLF 36.64초, V2V 24.16초, AI2V 24.26초. 이는 짧은 실행 경로 검증이다. 기존 R2V 7+1의 세로 7초와 8초 작업도 저장까지 성공했지만, 모든 모드의 긴 작업·립싱크·품질을 인증하지 않는다.

워크플로우 원본/API/검증 기록은 `workflows/human/minimax_h3/optimized` 및 `workflows/agent/presets/minimax_h3_optimized_*`에 보관한다. UI는 ComfyUI Workflows → H3_Optimized_Modes에 이미 저장되어 있다.
