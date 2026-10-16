# MiniMax H3 — 기본형·개선형 선택 가이드

운영·업데이트 확인·재발 대응: [H3 반복 안정화 가이드](../../../docs/comfyui_h3_stability.md).

## 2026-10-05 이 PC의 H3 정체 재발 보완

- 기본 러너: 이미지/텍스트 인코딩 완료 → node 145 전체 모델 해제 → 단일 샘플링 → node 144 전체 모델 해제 → 영상/오디오 디코딩.
- 로컬 `ComfyUI/custom_nodes/ComfyUI-KJNodes/nodes/nodes.py`의 `VRAM_Debug.IS_CHANGED`가 매번 NaN을 반환하도록 수정했다. 이 수정 없이 노드만 추가하면 같은 입력·다른 시드 실행에서 정리가 캐시되어 건너뛰어질 수 있다. KJNodes 업데이트로 덮어쓰면 이 보완도 확인해야 한다.
- 검증된 현재 실행 조합: **Dynamic VRAM 켜짐, async offload 2 streams 켜짐, `--reserve-vram 3 --vram-headroom 2`**. `--disable-async-offload`를 붙이지 않는다. `F:/ComfyUI_windows_portable/run_nvidia_gpu.bat`에 반영했다. 이 옵션은 실제 여유 VRAM이 항상 3GiB임을 보장하지 않는다.
- 메모리 정리만 보완한 dynamic/async-off 조합은 0.9초 연속 실행은 성공했지만 8초에서 정체했다. reserve 3만 추가해도 실패했고, async를 켜면 480×864의 8초 연속 저장은 성공했지만 576×1024는 여전히 정체했다. `--vram-headroom 2`로 다른 앱을 포함한 추가 여유 공간을 확보한 조합을 최종 검증했다. 정확한 CUDA 내부 교착 위치까지 증명한 것은 아니다.
- dynamic 비활성화도 8초 저장에는 성공했으나 시스템 RAM 여유가 약 0.5~2GiB까지 줄어 기본값으로 선택하지 않았다. 최종 dynamic/async-on 비교에서는 샘플링 중 약 28~35GiB의 RAM 여유를 관측했다.
- 검증 범위: 기본 I2V, 같은 참조/프롬프트, 단일 20스텝. 8초 work 576×1024의 시드 변경 연속 실행 및 이후 0.9초 재실행. 다른 모델·native 고해상도·개선형 15+5 전체의 무재발 보장은 아니다. 기술적 파일 완성을 검증했으며 원본 카메라 고정 연출의 품질 승인은 아니다.
- 이미 저장한 API JSON은 자동 변경되지 않는다. 기본 도구로 새 그래프를 생성한다. 상세 실행 기록과 원본 백업: `F:/ComfyUI_windows_portable/tmp/comfy_diag_20261005`.

FL2VA 계열 **T2V/I2V/FLF는 `scripts/generate_minimax_h3.py` 기본 단일 샘플링을 우선 사용**한다. `--profile work` 또는 `native`, 숏츠는 `--aspect 9:16`. `native_fast`, `--latent-upscale 2` 및 개선형 FL2VA 15+5는 현재 제작 기본값에서 제외하고 원인 분리 실험에만 사용한다. **R2V/V2V/AI2V는 `scripts/generate_minimax_h3_optimized.py` 우선**을 유지한다. FLF는 기본형의 VAE 전 모델 해제 보완 후 8초·576×1024 저장 성공을 확인했고, 네이티브 해상도 성공은 사용자가 보고했다. 2026-10-05 기본 I2V는 8초·576×1024 두 번과 직후 짧은 실행을 서버 재시작 없이 검증했다. T2V 및 native 고해상도 전체의 장시간 안정성 검증을 뜻하지 않는다.

```bat
python scripts/generate_minimax_h3.py --task t2v --profile work --aspect 9:16 --prompt-file F:/my_project/prompts/S01.txt -o F:/my_project/clips/S01.mp4
python scripts/generate_minimax_h3.py --task i2v --profile work -i F:/my_project/stills/start.png --aspect 9:16 --prompt-file F:/my_project/prompts/S02.txt -o F:/my_project/clips/S02.mp4
python scripts/generate_minimax_h3.py --task flf --profile work -i F:/my_project/stills/start.png --last F:/my_project/stills/end.png --prompt-file F:/my_project/prompts/S03.txt -o F:/my_project/clips/S03.mp4
python scripts/generate_minimax_h3_optimized.py --task r2v -i F:/my_project/stills/hero.png --aspect 9:16 --duration 8 --prompt-file F:/my_project/prompts/S04.txt -o F:/my_project/clips/S04.mp4
python scripts/generate_minimax_h3_optimized.py --task v2v --ref-video F:/my_project/refs/plate.mp4 --prompt-file F:/my_project/prompts/S05.txt -o F:/my_project/clips/S05.mp4
python scripts/generate_minimax_h3_optimized.py --task ai2v -i F:/my_project/stills/hero.png -a F:/my_project/refs/voice.wav --audio-start 0 --aspect 9:16 --prompt-file F:/my_project/prompts/S06.txt -o F:/my_project/clips/S06.mp4
python scripts/generate_minimax_h3_optimized.py --list-profiles
```

Portable Python: `F:/ComfyUI_windows_portable/python_embeded/python.exe`를 `python` 대신 사용할 수 있다. R2V·AI2V는 `-i`를 반복해 이미지 최대 9장을 지정한다. FLF는 `-i 시작 --last 끝`이다. V2V는 영상 하나와 연결된 soundtrack을 참조한다. AI2V의 오디오는 요청 길이만큼 잘라 참조한다. 프롬프트에서 각 `<Picture n>`, `<Video 1>`, `<Audio 1>`의 역할을 명시한다.

아래 구성과 해상도 표는 **개선형 CLI 전용**이다. FL2VA 제작 기본형의 프로필 해상도와 혼동하지 않는다.

| 작업 | 개선형 구성 |
|---|---|
| T2V / I2V / FLF (실험용) | 설치된 FL2VA, res_multistep 20스텝, 저해상도 15 + latent x2 + 고해상도 5 |
| R2V / V2V / AI2V | Singularity REF2VA + R2V DMD LoRA, Euler 8스텝, 저해상도 7 + latent x2 + 고해상도 1 |

공통: 텍스트 인코더 언로드, 고해상도 H3 Memory Optimization, 샘플링 후 모델 전체 언로드 → 영상·오디오 VAE → MP4 저장. FL2VA의 첫 패스도 메모리 최적화한다. I2V/FLF는 확대된 크기에 맞춰 고해상도 프레임 조건을 다시 만들어 크기 불일치를 방지한다.

| 프로필 | 가로 시작 → 출력 | `--aspect 9:16` 시작 → 출력 |
|---|---|---|
| draft | 512×288 → 1024×576 | 288×512 → 576×1024 (정확한 9:16) |
| work (기본) | 672×384 → 1344×768 | 384×672 → 768×1344 |
| 1080 | 960×544 → 1920×1088 | 544×960 → 1088×1920 |

`--width`와 `--height`는 **첫 패스 크기**이며 최종 크기는 x2다. 둘 다 32의 배수로 지정한다. work/1080은 정확한 16:9·9:16과 약간 다르므로 납품 때 비율을 맞춘다. 기본 5초, 권장 단일 클립 최대 8초. 요청 5/7/8초는 각각 약 5.167/7.292/8초로 정렬된다. `--attention sol`은 기존 R2V의 마지막 단계에만 지원하며 기본은 dense다.

V2V는 참조를 통한 새 생성이다. 원본 픽셀을 denoise strength로 변환하거나 정확한 카메라 경로를 보장하지 않는다. AI2V는 원본 오디오를 최종 영상에 덮어씌우지 않으며 원본 문장·립싱크·성우 음색의 정확한 재현은 별도 검수한다. 원하는 대사는 프롬프트에도 작성한다.

`--dry-run`은 프로젝트에 실행 그래프만 저장한다. 입력을 복사하거나 Comfy 작업을 제출하지 않는다. 실제 실행은 프로젝트에 `.mp4`, `.api.json`, `.meta.json`을 남기며 원본 입력을 고유한 이름으로 Comfy 입력 폴더에 복사한다. 실행 옵션이나 NVIDIA 설정을 자동 변경하지 않는다. 현재 실행 설정은 이 문서의 2026-10-05 재발 보완 절을 따른다. 과거 async-off 성공 기록을 현재 기본 설정으로 재사용하지 않는다.

## 대안과 검수

- 새 H3 생성: FL2VA T2V/I2V/FLF는 기본형 단일 샘플링, Ref2VA R2V/V2V/AI2V는 개선형을 우선한다.
- 기존 R2V 자동화 호환: `generate_minimax_h3_7plus1` 유지. 새 CLI의 R2V는 동일 프리셋에 세로·크기 옵션을 추가한 경로다.
- polish / carry-from / 혼합 다중 영상·오디오 참조 / 카메라 잠금 입력 조합: 해당 기능이 필요한 이유를 기록하고 기존 `generate_minimax_h3` 또는 camera-previz 경로를 사용한다.
- 원본 WAV를 유지하는 제작용 정확한 대사 립싱크: `generate_s2v` 등 작업 요구에 맞는 도구를 선택한다.

생성 전 failure_note와 generation-prompt, 생성 후 output-review로 영상·음성·동작·얼굴·대사를 검수한다. CLI 성공은 저장 성공이며 품질 승인과 다르다.

## 검증 범위

2026-10-03 RTX 4090에서 새 5가지 입력 방식은 요청 0.9초/22프레임, 최종 576×1024의 실제 생성·MP4 저장·오디오 포함·첫 프레임 디코딩을 통과했다. T2V 21.06초, I2V 30.23초, FLF 36.64초, V2V 24.16초, AI2V 24.26초. 이는 짧은 실행 경로 검증이다. 기존 R2V 7+1의 세로 7초와 8초 작업도 저장까지 성공했지만, 모든 모드의 긴 작업·립싱크·품질을 인증하지 않는다.

워크플로우 원본/API/검증 기록은 `workflows/human/minimax_h3/optimized` 및 `workflows/agent/presets/minimax_h3_optimized_*`에 보관한다. UI는 ComfyUI Workflows → H3_Optimized_Modes에 이미 저장되어 있다.

## 2026-10-04 FLF/I2V 샘플링 전 메모리 해제 보완

FLF/I2V는 저해상도·고해상도 키프레임 조건을 모두 준비한 뒤 TE와 VAE를 명시적으로 해제하고 1차 샘플링을 시작한다. DenoTextEncoderUnload의 두 번째 조건 입출력은 고해상도 양성 조건을 전달하는 동기화 용도이며 negative CFG로 사용하지 않는다. 1차 샘플링 완료 직후 생성 모델을 해제한 뒤 업스케일러를 실행한다. 업스케일러가 직접 CUDA 메모리를 할당하므로 이 사전 해제가 필요하다. 업스케일 완료 후에도 모델을 해제한 뒤 2차 샘플링으로 넘어간다. 기존 디코딩 직전 해제는 유지한다.

이는 8초 768×1344 FLF의 첫 샘플링 정체에 대한 메모리 전환 보완이다. 이전 렌더 검증은 22프레임·576×1024였으며 8초 안정성의 근거가 아니다. 수정 전 제출된 큐에는 적용되지 않으므로 다음 호출에서 새 그래프를 제출해야 한다. 같은 설정 반복 재시작은 피하고 실제 완료 여부로 판단한다. 2026-10-04 실제 8초 수정본은 1차 15단계를 약 49초에 완료했으나 21:05:43 업스케일러의 temporal chunking에서 정체했다. 이에 업스케일 직전 해제 노드 220을 추가했다. 이 추가 수정 후 업스케일은 완료됐으나, 8초·576×1024 및 768×1344 모두 두 번째 샘플링 첫 단계에서 정체했다.

## 2026-10-04 기본 FL2VA 디코딩 전 메모리 해제

기본 `generate_minimax_h3.py --task flf --profile work`의 단일 샘플링 경로는 8초·576×1024·20단계를 약 195초에 완료했으나 영상 VAE 로딩 뒤 정체했다. 기본 러너에 최종 샘플러 → VRAM_Debug(전체 모델 해제·캐시 정리) → 영상/오디오 VAE 디코딩을 추가했다. 단일 샘플링·기존 SageAttention·모델·해상도·스텝은 유지한다. 같은 러너의 다른 생성 모드도 공통 디코딩 경계를 사용한다.

현재 FLF 비교 검증에는 이 기본 단일 샘플링 경로를 사용한다. 개선형 15+5는 8초에서 두 번째 샘플링 정체가 남아 있어 안정화 완료로 취급하지 않는다. 이미 제출한 큐에는 소급 적용되지 않으며 다음 호출에서 새 그래프를 제출해야 한다. 수정 후 기본 FLF는 8초·576×1024·192프레임·오디오 포함 MP4 저장과 전체 영상 프레임 디코딩을 확인했다(226.88초, prompt a8cf609d-879b-43d1-8911-3bd03950799b). 네이티브 해상도 성공은 사용자 보고다.

## 개선형 FL2VA 원인 분리 계획

제작 기본값은 위의 단일 샘플링 경로다. 개선형 FL2VA를 자동 재시도하거나 해상도만 낮추며 반복하지 않는다.

확인된 사실: 생성 모델 해제 후 업스케일 자체는 완료된다. 개선형은 두 번째 샘플링에서 정체한다. 기본형은 SageAttention, 개선형은 Kitchen INT8 및 H3MemoryOptimization이므로 단계 수만의 문제로 확정할 수 없다.

별도 실험에서는 이미지·프롬프트·시드·8초·576×1024·모델·실행 옵션을 고정한다. 성공한 단일+Sage를 기준으로 (1) 단일+Kitchen만, (2) 단일+Kitchen+H3MemoryOptimization, (3) 두 단계+Sage로 변수를 분리한다. 각 비교는 VAE 전 해제를 유지하고, 두 단계는 업스케일 전후 해제도 유지한다. 현재 정체 상태의 프로세스에서 연속 비교하지 않는다.

모델 재로딩 및 같은 원본에서 파생한 두 최적화 모델의 패치/캐시 수명도 확인한다. 첫 패스의 denoised_output을 확대해 두 번째 구간에 다시 노이즈를 넣는 방식은 연속 20스텝과 동일하지 않고 res_multistep 내부 이력도 새로 시작한다. 이는 별도 품질·수치 검증 대상이며 정체 원인으로 확정된 것은 아니다. 전체 저장 성공, 실행 시간, 단계별 최대 VRAM, 시작·끝 프레임 및 오디오 품질을 비교한 뒤에만 제작 기본값 승격을 검토한다.
