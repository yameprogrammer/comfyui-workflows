# ComfyUI H3 반복 실행 안정화 — 작업 에이전트 가이드

2026-10-05 · 적용 PC: RTX 4090 24GB / 시스템 RAM 64GB.
검증된 조건에서는 개선됐다. 8초 I2V 두 번과 그 직후 짧은 I2V가 서버 재시작 없이 완료됐다. 다른 모델·모든 해상도·장기 무재발을 보장하는 판정은 아니다.

## 작업 시작 시 적용

1. 도구 위치는 `F:/Agent_media_tools`. FL2VA T2V/I2V/FLF는 `scripts/generate_minimax_h3.py`의 기본 단일 샘플링을 사용한다. 재현 기준은 `--profile work --aspect 9:16 --duration 8` I2V다. native는 이번 반복 검증 범위 밖이다. `native_fast`, latent x2, FL2VA 15+5는 실험용으로 남긴다. R2V/V2V/AI2V의 기존 optimized 우선 정책은 유지하되 이번 I2V 검증 결과를 그 경로의 안정성 인증으로 옮기지 않는다.
2. 이 PC의 기본 실행기는 `F:/ComfyUI_windows_portable/run_nvidia_gpu.bat`. **Dynamic VRAM 켜짐 + async offload 2 streams + `--reserve-vram 3 --vram-headroom 2`**, pinned memory 기본값을 사용한다. `--disable-async-offload`나 `--disable-dynamic-vram`을 추가하지 않는다. 이 옵션들은 ComfyUI 서버 옵션이며 생성 CLI에 전달하지 않는다. 이미 켜진 서버는 배치 파일을 고쳤다고 설정이 바뀌지 않으므로 실제 시작 명령과 시작 로그를 확인한다. 다른 실행기에도 자동 반영됐다고 가정하지 않는다.
3. 아래 세 구성요소가 함께 있어야 한다. 저장한 예전 API JSON을 다시 제출하지 말고 현재 러너로 새 그래프를 만든다. UI 워크플로우와 다른 PC에는 이 로컬 수정이 자동 배포되지 않는다.
4. 생성 전 `python scripts/failure_note.py before "minimax_h3 vram hang cache"`. 출력·실행 그래프·리뷰는 호출한 프로젝트에 저장한다. 생성 후 output-review로 실제 영상과 음성을 확인한다.

| 구성요소 | 확인할 내용 |
|---|---|
| 기본 러너 `lib/minimax_h3_runner.py` | 인코딩 node 131 → node 145 `VRAM_Debug` → 첫 샘플러 125. `empty_cache`, `gc_collect`, `unload_all_models` 모두 true. 최종 샘플러 → node 144 → 영상·오디오 디코딩도 유지 |
| 로컬 KJNodes `F:/ComfyUI_windows_portable/ComfyUI/custom_nodes/ComfyUI-KJNodes/nodes/nodes.py` | `VRAM_Debug.IS_CHANGED`가 호출마다 `float("nan")` 반환. 같은 조건·다른 시드에서 정리 노드가 캐시로 생략되는 것을 방지 |
| 서버 실행 설정 | Dynamic VRAM / async 2 streams / reserve 3 / headroom 2를 실제 프로세스와 로그에서 확인 |

KJNodes 보완은 **공용 도구 저장소 밖의 로컬 패치**다. 패키지 업데이트로 덮어쓰일 수 있다. 업데이트 후 동등한 캐시 방지 처리가 있는지 먼저 확인하고, 없다면 해당 클래스에만 아래 보완을 복원한다. 기존 클래스나 파일 전체를 덮어쓰지 않는다. 실행 중인 서버에 소스 수정은 소급 적용되지 않는다. 진행 작업을 확인한 뒤 관리하는 서버를 재시작해야 한다.

```python
@classmethod
def IS_CHANGED(cls, **kwargs):
    return float("nan")
```

## 왜 영상 길이만 줄여도 해결되지 않았나

프레임 수 이외에도 이전 실행의 모델 상주 상태, 정리 노드의 실행 캐시, 모델을 GPU로 옮기는 방식과 여유 메모리가 영향을 줬다. 같은 조건에서 시드만 바꾸면 정리 노드가 생략되는 사례를 확인했다. 캐시 방지와 샘플링 전 정리만으로 짧은 반복은 통과했지만 8초는 여전히 정체했다. async offload와 추가 headroom을 함께 적용한 뒤 최종 반복 검증이 통과했다. 정확한 CUDA 내부 대기 위치까지 확인한 것은 아니다.

VRAM 점유나 GPU 사용률 하나로 정체를 판정하지 않는다. 실패 당시 GPU 사용률 100%도 관측됐다. 단계 진행, 로그 갱신, GPU 전력/메모리 사용, 시스템 RAM을 함께 본다. reserve 3은 실제 빈 VRAM 3GiB 보장이 아니다. Dynamic VRAM을 끄는 대안은 완료되기는 했으나 시스템 RAM 여유가 약 0.5~2GiB까지 줄어 기본값에서 제외했다.

## 재발 시 대응 순서

1. 연속 제출을 멈추고 현재 작업의 prompt ID, task, 모델, seed, 크기/프레임 수, 마지막 진행 단계와 시각, 실행 그래프·서버 로그를 프로젝트에 보존한다. GPU 상태와 시스템 RAM 여유도 함께 기록한다. 응답하는 API만 제한 시간으로 조회한다. 서버 API 자체가 멎으면 같은 조회를 무한 반복하지 않는다.
2. 인코딩 / 첫 샘플링 / 업스케일 / 두 번째 샘플링 / 디코딩 중 정체 위치를 구분한다. 이번 보완을 개선형 15+5의 두 번째 샘플링 정체 해결로 간주하지 않는다.
3. 실제 서버 옵션, node 145·144 연결, KJNodes 캐시 방지를 확인한다. 같은 입력·새 시드의 기록에서 인코딩이 캐시되는 것은 정상이나 정리 노드는 매번 실행돼야 한다.
4. 정체한 작업과 서버 소유권을 확인하고 정상 취소를 우선한다. 취소에 응답하지 않을 때에만 해당 ComfyUI 서버를 복구한다. 다른 에이전트의 정상 작업이나 모든 Python 프로세스를 일괄 종료하지 않는다. 정체한 프로세스에서 길이만 줄여 계속 비교하지 않는다.
5. 원인을 하나씩 변경하고 검증 기준을 반복한다: 같은 서버에서 8초 work I2V → 같은 조건·새 시드 8초 → 0.9초 480×864. 실제 완료·전체 영상/음성 디코딩을 확인한다. 정해진 시간만 지났거나 CLI가 성공했다고 품질까지 승인하지 않는다. 실패와 새 검증 결과는 failure_note 및 process.md에 기록한다.

## 확인된 결과와 한계

| 순서 | 기본 I2V 조건 | 완료 시간 | 파일 검증 |
|---|---|---|---|
| 1 | 8초, 576×1024, 20스텝 | 203.30초 | 192 영상 프레임 및 전체 오디오 디코딩 |
| 2 | 동일 참조/프롬프트, 새 시드, 8초 | 196.16초 | 192 영상 프레임 및 전체 오디오 디코딩 |
| 3 | 같은 서버에서 0.9초, 480×864 | 22.27초 | 22 영상 프레임 및 전체 오디오 디코딩 |

기본 I2V, FL2VA INT8 ConvRot + NVFP4 Qwen3VL 32B TE, SageAttention auto, res_multistep 20스텝 기준. 위 시간은 당시 관측값이며 타임아웃 기준이 아니다. T2V/FLF/R2V 전체, native 고해상도, 장시간 연속 운영은 이번 검증에 포함되지 않는다. 이전 FLF 성공 기록 및 사용자의 native 성공 보고와 구분한다. 기술적 파일 완성 확인이며 카메라 고정·연출 품질 승인은 아니다.

보존한 [검증 요약 JSON](validation/comfyui_h3_20261005.json). 원본 로그·그래프·백업·미디어 검증 기록: `F:/ComfyUI_windows_portable/tmp/comfy_diag_20261005`. 로컬 원본 경로는 다른 PC에서 사용할 수 없을 수 있다.

유지보수 확인(도구 루트에서):

```text
python -m unittest discover -s tests -p test_minimax_h3_decode_barrier.py
python -m unittest discover -s tests -p test_minimax_h3_optimized.py
python scripts/tool_index_check.py
python scripts/tool_intent.py "minimax_h3 vram hang"
```

앞의 그래프 검사는 GPU 정체가 없다는 증거를 대신하지 않는다. 실행 검증을 해야 반복 안정성 범위를 넓힐 수 있다. 모드별 사용법은 [H3 도구 가이드](../workflows/human/minimax_h3/H3_OPTIMIZED_GUIDE.md)를 따른다.
