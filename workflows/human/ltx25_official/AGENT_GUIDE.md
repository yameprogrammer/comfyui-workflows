<!-- LTX25-ADVANCED-FOLLOWUP-20261017 -->
## LTX-2.5 latest validation states — 2026-10-17T08:00:31.657607+09:00

**Do not merge execution success, bounded visual quality, user review, and missing models.** New4small advanced probes completed on the existing INT8 server; no model/package/node downloads, installation, restart or permanent default changes. APIs live in the validation project, not a newly deployed general production CLI.

| Feature | Execution | Quality | User review / missing component |
|---|---|---|---|
| Ingredients public original/portrait-only/matched-text + close-up | completed | scene integration without panels and framing change observed | exact all-angle face identity pending |
| Korean/English generated speech and A2V | completed | ASR phrase match; A2V waveform preservation; tested quality-on face drift fails | pronunciation/noise/timbre/listening and phoneme-level sync pending |
| Temporal Retake local mask probe | completed | requested blue-ball change FAILED; outside-window preservation bounded | not unchanged native RetakePipeline |
|49to97frame video extension | completed | actual new motion, no conspicuous seam jump, bounded visual success | exact pan unverified; source audio was not preserved |
| Union canny92/200and25/80 | both completed | ball path partially followed; tabletop geometry FAILED in both | depth/pose not tested; exact official2.5example2.3adapter used |
| MotionTrack / In-Outpainting | not run | none | adapter not installed; exact filenames/sizes in report |
| DFR / temporal upscale | not run | none | detailing/temporal assets missing; native route needs compatible weights/runtime, not Comfy ConvRot |

Panel causality is **not isolated**. No enhancer/I2Vanchor was active and CropGuides wiring is correct in tested graphs. Public input/graph controls disprove blanket reference impossibility; reference sheet/prompt/seed/resolution/sampler/strength/decoder/output differences remain confounded. Threshold-only repair did not resolve Union geometry. Preserve the original quality default; one English adapter-off ablation is not general incompatibility evidence.

[Latest state-by-state report](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/quality_validation_20261016_2208/ADVANCED_REPORT.md) includes causal audit, actual audio-boundary frames, prompt IDs/hashes/time/VRAM, missing official files/bytes/license/gates, and user listening material. Library contains **LTX25_Validation_Comparisons_20261017.zip** (sanitized fictional characters/stock voices/prop comparisons only; no real-person public portrait/API/accounts/computer paths). Overall production/whole-feature validation remains incomplete. Earlier pending/completed paragraphs below are dated history.


<!-- LTX25-QUALITY-FOLLOWUP-20261017 -->
## LTX-2.5 face/dialogue followup — 2026-10-17T07:48:44.784216+09:00

Status remains **ready_experimental**. Public original → portrait-only replacement → matched-character text all generated one scene without retained panels. A close-up wording repair also worked. This does not establish exact facial identity; earlier local two-view sheet failures remain valid bounded failures, not proof that Ingredients is impossible. No I2V anchor or enhancer was active; conditioned positive/negative reached CropGuides correctly.

Korean/English LTX-generated speech and input-frozen A2V phrases matched offline CPU ASR. A2V waveform correlation was0.999294/0.999134. **Listening, precise phoneme sync and production identity remain pending**; ASR/spectra/mouth-energy curves are not auditory passes. In one controlled English case, disabling the two added AIO quality adapters reduced facial/expression drift (supplementary mid-frame reference cosine0.437→0.786), but decoded audio overshoot needs review. Keep the original quality default and generic2.3 route; this is one explicit ablation, not a blanket incompatibility claim.

Approved fictional photoreal/anime sources and cached Qwen stock voices only; no cloned character-pack voice, external upload, model/package/node installation or restart. Current phase:10additional completed jobs; all phase records22include one invalid metadata-only prompt ablation preserved/excluded. Retake candidate is **prepared only, not queued**; extension/Union/MotionTrack/DFR runtime quality is still pending.

Read [the quality report](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/quality_validation_20261016_2208/QUALITY_REPORT.md) for exact input/prompt/API/history/hash/time/VRAM, public graph audit, failed cases and source/output listening previews. Machine result: [QUALITY_RESULTS.json](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/quality_validation_20261016_2208/QUALITY_RESULTS.json). Older status paragraphs below are historical snapshots.


# LTX-2.5 T2A / A2V / Ingredients 사용 가이드

최신 정리: 2026-10-16T15:46:24.123116+00:00. 상태 **ready_experimental — 소품 참조 시각 검증 통과, 정확 인물·청취 미검증**. 현재 승인된 설치·연결·제한적 검증 범위를 완료했다. 추가 GPU 실행·설치·업데이트·재시작은 이 문서 정리에서 하지 않았다.

## 시작 경로와 완료 범위

[AGENTS.md](../../../AGENTS.md) → [TOOLS.md](../../../TOOLS.md) / [카탈로그](../../../docs/tool_catalog.md) → 이 가이드. 검색 `python scripts/tool_intent.py "ltx25 ingredients"`, 실행 `scripts/generate_ltx25_official.py --task t2a|a2v|ingredients`. 일반 I2V/S2V 기본2.3과 기존 AIO quality LoRA 정책을 유지한다.

| 경로 | 실행 근거 | 품질 범위 |
|---|---|---|
| AIO T2V/I2V/FLF | 49프레임·24fps 짧은 실행, T2V quality/none 비교 | 기본 움직임 확인. 긴 영상·발화·인물 제작 품질 미검증 |
| T2A | 약2초·48kHz stereo FLAC,22.93초 | 무음/클리핑 검사 통과. 청취·소리 의미 미검증 |
| 공식 기반 A2V | 384×256→768×512,49프레임,25.35초 | 원본 오디오 AAC 출력 상관0.999209. 발화/립싱크 미검증 |
| Ingredients 공식 버킷 | 768×448·121프레임·24fps,seed4747,강도1 | **소품/장소 결합과 구르는 공 시각 PASS**. 특정 시트·프롬프트 한정 |
| Ingredients 공개 사례 비교 | 동일 INT8+새2.5 어댑터,seed42/강도1.4/CFG++,928×544,121프레임,75.73초 | 인물·기타·무대 결합 확인. 요청보다 넓은 구도, 정확 얼굴·머리 및 청취 pending |

총12회 기록은 [runtime-validation.json](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/runtime-validation.json), [현재 상태](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/ingredients-repair-status.json), [회귀 검사](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/ingredients-repair-regression.json)에 있다. API 그래프는 공식 예제를 INT8에 맞춘 직접 구성이다. 원본 UI는 [SOURCES.json](SOURCES.json)에 별도 보관했으며 브라우저 UI 실행은 검증하지 않았다.

## Ingredients 참조 시트 규칙

1. **검은 배경, 텍스트 없는 요소별 패널**을 유지한다. 서로 다른 소품/인물/장소를 분리한다. 장소 패널은 가능하면 해당 소품·인물이 없는 깨끗한 배경으로 구성한다.
2. 중요한 소품은 충분히 크게 둔다. 같은 공을 장소 사진과 확대 사진에 중복 배치한 기존 시트는 이 테스트에서 레이아웃 누출을 일으켰다. 중복/혼합 패널을 피하는 것은 이 사례의 검증된 예방책이며 모든 경우의 필요조건으로 일반화하지 않는다.
3. 프롬프트는 `Reference sheet:`에서 **실제 패널 위치와 내용**을 정확히 설명하고 `Generated video:`에서 새 장면·동작·카메라·소리를 설명한다. 시트 레이아웃을 장면 자체로 재서술하지 않는다.
4. 먼저 공식 학습 버킷 **768×448 /121프레임/24fps**, reference downscale1, 어댑터1, Euler ancestral8단계/CFG1을 사용한다. 정적 시트는 RepeatImageBatch로121프레임 반복하며 IC guide로 전달한다. 시트를 첫 출력 프레임에 강제하지 않는다. sampler 뒤 CropGuides로 참조를 제거한다.
5. 참조 VAE 인코딩 기본은 공식 UI와 같은 **untiled**다. 이 설정만 바꾸는 실험은 실패를 해결하지 못했다. 시트/설명을 바꾸는 복합 변경이 같은 seed4747에서 문제를 해결했으며 이미지와 문구의 개별 기여도는 미분리다.

기본 Ingredients 길이/크기는 CLI가5초/768×448로 설정한다. `--adapter-strength 1.4 --sampler euler_ancestral_cfg_pp`는 명시적인 커뮤니티 비교 옵션이다. 강도1에서도 소품 테스트는 통과했으므로1.4를 보편 해법으로 강제하지 않는다. 부정 프롬프트는 CFG1에서 효과를 보장하지 않는다.

## 검증한 입력·출력과 재현 명령

- **통과한 입력 시트:** [ingredients_clean_sheet.png](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_clean_sheet.png)
- **정확한 긴 프롬프트:** [ingredients-clean-prompt.txt](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/ingredients-clean-prompt.txt)
- **실제 출력:** [ingredients_clean_sheet.mp4](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_clean_sheet.mp4) · [접촉시트](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_clean_sheet_contact.jpg)
- **실제 API/검수:** [API](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_clean_sheet.mp4.api.json) · [시각 PASS 기록](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/reviews/ingredients_clean_sheet/record.json)
- **공개 사례:** [최종 비교 영상](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_loopforge_exact.mp4) · [설정·한계](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/INGREDIENTS_DIAGNOSIS.md)

다음 명령은 검증한 시트·긴 프롬프트·시드를 사용한다. 수정한 빌더의 생성 그래프가 실제 통과 API와 동일함을 CPU 비교했다. 실행은 이 문서 정리에서 다시 하지 않았다. 출력 경로는 사용자의 실제 프로젝트로 정한다.

```powershell
Set-Location F:/Agent_media_tools
$ingredientsPrompt = Get-Content -Raw -Encoding UTF8 'C:/Users/parkp/Documents/Codex/2026-10-16/task-8/ingredients-clean-prompt.txt'
& F:/ComfyUI_windows_portable/python_embeded/python.exe -B scripts/generate_ltx25_official.py --task ingredients -i 'C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_clean_sheet.png' -p $ingredientsPrompt --seconds 5 --width 768 --height 448 --seed 4747 -o F:/my_project/ingredients_ball.mp4
```

`--export-api`는 `--output` 위치에 API 봉투만 저장하며 큐·입력 복사를 하지 않는다. 실제 실행은 출력 옆에 `.api.json`, `.history.json`, `.run.json`을 남긴다. 출력은 toolbox 밖이어야 한다. CLI는 기존 서버만 사용하며 큐가 바쁘면 거부한다. 생성 완료 후 파일을 열고 output-review를 기록한다.

T2A/A2V 기본 호출:

```powershell
python scripts/generate_ltx25_official.py --task t2a -p "A gentle stream flows over rocks, no music, no speech." --seconds 2 -o F:/my_project/stream.flac
python scripts/generate_ltx25_official.py --task a2v -a F:/my_project/stream.flac -p "A shallow forest stream flows over stones; static camera." --seconds 2 --width 384 --height 256 -o F:/my_project/stream.mp4
```

## 알려진 실패와 이력

- 시트 패널을 유지한 채 패널 안에서만 움직이는 현상; 프롬프트 수정 후 검은 세로 가림이 남은 현상. [원래 실패 시트](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_sheet.png), [첫 실패](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_ball_contact.jpg), [둘째 실패](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/validation/ingredients_ball_fullframe_contact.jpg).
- untiled만 바꾼 대조도 실패. 깨끗한 요소 분리 시트와 일치하는 설명으로 복구. 검은 배경 자체를 없애는 해법은 권장하지 않는다.
- 첫 커뮤니티 비교 호출은 시드/샘플러 키가 다른 노드에 들어가 무시됐다. 이를 정확 재현으로 집계하지 않고 기록을 보존한 뒤 실제42/CFG++로 수정했다. [설정 정정 기록](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/ingredients-settings-correction.json).
- [실패 노트 FN-20261016-007](../../../failures/notes/FN-20261016-007.json), [상세 진단·공식/커뮤니티 신뢰 수준](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/INGREDIENTS_DIAGNOSIS.md), [이전 가이드 원문](HISTORY_20261016_BEFORE_CLOSEOUT.md). 과거 FAIL은 삭제하지 않았으며 현재 상태는 위의 제한적 PASS/pending이다.

## 모델·공식 출처

체크포인트 단일 경로: `F:/model/loras/LTX2.5/ltx-2.5-22b-ic-lora-ingredients-0.9.safetensors`. 크기1,308,787,472바이트. 로컬 SHA256 `ff873a5beada3c579a8137c7c53343916f78bcc9a529ba910143073fe8715e95`. 사용자 요청대로 검증 후 Downloads 중복을 제거했다. upstream 공식 SHA 일치 여부는 미확인이고 HF 인증/동의는 변경하지 않았다. [이동 증거](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/ingredients-local-verification.json).

베이스는 설치된2.5 distilled INT8 ConvRot, 전용 Gemma4 INT8, 표준2.5 video/audio VAE다. A2V는 설치된2.5 spatial latent×2를 사용한다. Ingredients는 단일 단계다. ConvRot는 Comfy 전용이다. 원본 공식2.5 UI의 Ingredients는2.3 파일을 지정하므로 새2.5 카드 기반 경로와 구분한다. 2.3 LoRA 파일명만으로 비호환 판정하지 않는다.

[공식2.5 모델](https://huggingface.co/Lightricks/LTX-2.5) · [새2.5 Ingredients 카드](https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Ingredients) · [공식 버전별 IC-LoRA 안내](https://docs.ltx.io/open-source-model/integration-tools/ic-lo-ra-adapters#ingredients) · [공개 INT8 성공 사례](https://loopforge.cc/projects/ltx-2-5-loras/guitarist-on-a-stage/) · [현재 모델 라이선스](https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x). 소스 저장소의 오래된 LICENSE 사본을 현재 모델 라이선스로 대체하지 않는다.

## 남은 미검증·미완성 범위

- 정확한 인물 얼굴/머리·여러 얼굴·손/연주·발화/립싱크·오디오 청취·실제 제작 샷 품질.
- 브라우저 UI import/실행, 긴 클립, AIO FML/V2V와 모든 오디오 입력 조합. 노드/API 확장 검증을 GPU 실행으로 간주하지 않는다.
- Union/MotionTrack/In-Outpainting, native multishot, 자동 길이·enhancer, 생성 keyframe·extension/retake, DFR/pixel detailing·temporal upscale,4K/HDR/Alpha/Layout/Refine/Restore 등은 전용 모델/배선/실행 범위가 각각 미완성이므로 일괄 준비 완료로 표시하지 않는다.
- Dub-It/Relight의2.3 전용 문서를2.5 지원 증거로 합산하지 않는다. 전체 기능 비교는 [전체 점검 보고서](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/LTX25_FINAL_REPORT.md).

새 모델·노드의 일괄 추가는 하지 않았다. 필요 기능을 선택한 뒤 목적별 검증을 진행한다. 현재는 추가 실행 예정/차단 없이 문서 정리까지 완료했다.
