<!-- MOSS_IMAGE_TOOL -->
MOSS-Image agent route: `python scripts/generate_moss_image.py --status`, then `--help`. Seven native image modes: t2i/layout/edit/multi-edit/control/color/depth. Read `workflows/human/moss_image/AGENT_GUIDE.md`; use generation-prompt and output-review. Missing weights fail without downloads. Never restart/clear/cancel ComfyUI from this tool. Edit weights have no separately stated original license; commercial review required.
<!-- /MOSS_IMAGE_TOOL -->

<!-- MOSS-SPEECH-20261019 -->
## MOSS speech generation — TTS / TTSD / VoiceGenerator

For speech creation, use [MOSS speech guide](workflows/human/moss_speech/AGENT_GUIDE.md): `generate_moss_tts.py` (Korean/multilingual + authorized voice reference), `generate_moss_ttsd.py` (S1/S2 dialogue continuation), `generate_moss_voice.py` (English/Chinese instruction voice design). Actual WAV execution verified in isolated F:/MOSS-TTS; status ready_experimental with listening/identity/emotion limits. Existing character voice locks remain. This is separate from `transcribe_moss.py`, which converts audio to text. Read [measured validation](F:/MOSS-TTS/validation/VALIDATION_REPORT.md); outputs belong to caller project. No undocumented TTS emotion tags, no direct Korean VoiceGenerator promise.

<!-- MOSS-NATIVE-20261019 -->
## MOSS local transcription / diarization

Use [MOSS Windows native guide](workflows/human/moss_transcribe/AGENT_GUIDE.md) and `python scripts/transcribe_moss.py -i F:/my_project/speech.wav -o F:/my_project/moss_take01`. Isolated Python3.12, local-only CUDA/BF16/SDPA, no ComfyUI changes. `ready_experimental`: synthetic English execution passed; specified Korean original is missing, real Korean / ~5min validation pending. Raw output retained; anonymous IDs are not cross-file identities; token cap warns. Read the guide and execution/quality limits before use.


<!-- IMAGE-TOOL-PRIORITY-20261018 -->
## 이미지 도구 선택 — 최신 사용자 지침 (2026-10-18)

> 로컬 도구들이 텍스트가 포함된 뭔가를 만들 때는 좀 성능이 떨어지니까 텍스트가 포함된 뭔가를 만드는건 보조관의 이미지 도구를 사용하고 그외에는 Flux3나 Krea2 모델을 사용해서 작업 하는걸로 합시다.

- **이미지 안에 글자가 포함되면 보좌관 이미지 생성 도구를 사용한다.** 로컬 모델의 글자 표현 한계를 고려한 선택이다. 생성 후 실제 이미지를 열어 철자·문구·누락·가독성을 검수한다.
- **글자 없는 이미지는 로컬 FLUX3 또는 Krea2를 사용한다.** FLUX3는 full-caption, Krea2는 해당 모델의 자연어 프롬프트 규칙을 따른다.
- 이번 지침은 이전 **“텍스트가 있으면 Flow 또는 보좌관 이미지 도구”**보다 최신이며 이미지 선택 시 우선 적용한다. **Flow 전면 금지를 뜻하지 않는다.**
- 정확한 자막·타이틀·광고 문구는 기존대로 Remotion/Blender 등의 별도 텍스트 소스·레이어로 후반 합성할 수 있다. 글자 없는 배경·원화 생성은 위 로컬 모델을 사용한다.
- 적용 범위는 이미지 생성 도구 선택이다. **영상·TTS·Blender·Remotion 도구 선택과 기존 편집 워크플로우는 변경하지 않는다.**

[이미지 선택 가이드](docs/agent_native_capability_autonomy.md) · [도구 카탈로그](docs/tool_catalog.md)

<!-- /IMAGE-TOOL-PRIORITY-20261018 -->

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


# AGENTS.md — `agent_custom` = ComfyUI **tool box**



This is **not** your film project folder and **not** a fixed production line.  

It is a **collection of media tools** (still / edit / I2V / TTS / …) driven by local ComfyUI.



```text

Your goal (the video you need)

  → pick intents from the catalog shelves (GENERATE / TRANSFORM / MOTION / …)

  → call scripts/ with -o / --output pointing at YOUR project

  → review_media pack → open the file → record pass/fail → next lever

  → never leave finished media in this repo

```



**This directory is a toolbox only.** Episode trees, character sheets, location plates, `dumps/`, and deliveries do **not** belong here. Put every still / clip / zip under the **project you are actually making**.



| Do | Don’t |

|----|--------|

| Start at **[TOOLS.md](TOOLS.md)** or `python scripts/tool_intent.py "…"`, then **[docs/tool_catalog.md](docs/tool_catalog.md)** | Treat CREATIVE→assemble as mandatory for every job |

| Pass **`-o` / `--output` / `--dest`** to a path **outside** this repo (or set `AGENT_WORKSPACE`) | Write mp4/png/wav into `stories/`, `dumps/`, `characters/<id>/`, `deliveries/` |

| Before heavy gen: `python scripts/failure_note.py before "…"`; on FAIL: `failure_note.py add` | Repeat known factory failures (freeze, feet, mass approve, …) |

| After `generate_*`: equip **output-review**, open the file, `review_media record` | Treat CLI exit 0 as quality, or skip opening the file |

| Combine tools freely for *this* video | Assume episode approve / assemble is required for one-off cuts |

| Keep project media in **your** project folder | Leave “finished” work only here |

| Use `stories/_template` + approve + assemble **only if you choose that recipe — and still write the episode into your project** | Confuse optional helpers with “the only way” or treat this repo as a media archive |



**Provider vs consumer:** we maintain tools + specs; **you pick wisely for your project.**



Catalog SSOT: intent-first **[docs/tool_catalog.md](docs/tool_catalog.md)** · Maintainers: [agent_rules.md](agent_rules.md) · history: [process.md](process.md)





## FLUX3 Klein — prompt and usage entry

For `generate_flux3.py` read [FLUX3 usage](workflows/human/flux3/AGENT_GUIDE.md), [full-caption / reference / typography guidance](skills/generation-prompt/references/flux3_still.md), and [measured validation limits](workflows/human/flux3/TEST_MATRIX.md). This local distilled INT8 profile has no prompt upsampler node: supply the expanded final-scene caption. FLUX.1/2 short-prompt recipes do not apply. Typography examples are untested; strict style QC remains experimental.

## LTX-2.5 — explicit version and validation scope

For LTX-2.5, begin at [the version/usage guide](workflows/human/LTX25_AIO_AGENT_GUIDE.md), [MOTION catalog](docs/tool_catalog.md), and [prompt input/enhancer guidance](skills/generation-prompt/references/ltx25_video.md). Discover with `python scripts/tool_intent.py "ltx 2.5"`; execute explicitly with `generate_ltx25_aio.py`. Generic I2V/S2V defaults remain 2.3.

Status remains `ready_experimental`: short T2V/I2V/FLF, T2A and A2V executed on original8188. [Official-derived tasks](workflows/human/ltx25_official/AGENT_GUIDE.md) use `generate_ltx25_official.py --task t2a|a2v|ingredients`; Ingredients initial two visual failures were followed by a controlled diagnosis: a distinct prop/empty-location sheet and matching positional prompt visually PASSED at seed4747/strength1; character/prop/location retrieval works but exact human identity remains pending. See `C:/Users/parkp/Documents/Codex/2026-10-16/task-8/INGREDIENTS_DIAGNOSIS.md`. Full playback/listening, character/speech and broader durations remain pending. `--lora-policy quality` preserves the original AIO two-LoRA default; a 2.3 LoRA filename alone does not imply incompatibility. Record execution and media QA separately. Evidence: `C:/Users/parkp/Documents/Codex/2026-10-16/task-8/runtime-validation.json`.

Ingredients current rules, known failures, tested input/output paths and exact reproduction command: [current task guide](workflows/human/ltx25_official/AGENT_GUIDE.md). Its status table supersedes historical pending/failed snapshots; face identity/listening and the advanced-feature list remain unverified.

## Higgs TTS 3 — local speech / ready_experimental

For short Korean/English speech, emotion tags or local-reference conditioning, read [Higgs usage](workflows/human/higgs3_tts/AGENT_GUIDE.md) and [measured tests/limits](workflows/human/higgs3_tts/TEST_MATRIX.md). Discover with `python scripts/tool_intent.py "higgs tts 3"`; run `python scripts/generate_higgs3_tts.py -t "안녕하세요." --emotion elation -o F:/my_project/voice.wav` from this toolbox root.

Use original8188 `Higgs3IsolatedTTS`; its private Transformers5 worker preserves the original Transformers4 environment. Status is **ready_experimental**: actual generation/ASR/technical checks passed, but perceived emotion, noise/voice identity and browser UI execution remain unverified. Open the media and keep listening QC pending when it cannot be heard; ASR/spectrograms are not a listening pass. Serialize GPU jobs with other tools.

References stay local and require rights/consent. For an own-voice request inspect the character pack's `voice/voice.json`; distinguish its real recording from generated VoiceDesign samples and preserve the pack's default voice lock. Published creator content, including monetized video, needs prominent **Boson AI's Higgs Audio** credit in audio/description under the [official license](https://huggingface.co/bosonai/higgs-tts-3-4b/blob/main/LICENSE); third-party serving/product distribution requires separate licensing.

## MiniMax H3 — 모델 계열별 기본 도구



실행 전 [H3 반복 안정화 가이드](docs/comfyui_h3_stability.md)를 따른다. 서버 설정·러너 정리 노드·로컬 KJNodes 캐시 방지를 함께 확인한다.



**이 PC의 2026-10-05 안정화 설정:** Dynamic VRAM + async offload 2 streams + `--reserve-vram 3 --vram-headroom 2`. `--disable-async-offload`는 제거한다. 기본 실행 배치에 반영됨. 기본 러너의 샘플링 전 모델 해제와 로컬 KJNodes `VRAM_Debug.IS_CHANGED` 캐시 방지 수정이 함께 필요하다. 검증 범위·업데이트 주의는 [H3_OPTIMIZED_GUIDE](workflows/human/minimax_h3/H3_OPTIMIZED_GUIDE.md)의 2026-10-05 절을 따른다.



FL2VA 계열 **T2V/I2V/FLF는 `scripts/generate_minimax_h3.py` 기본 단일 샘플링을 우선 사용**한다. `--profile work` 또는 `native`, 숏츠는 `--aspect 9:16`. `native_fast`, `--latent-upscale 2` 및 개선형 FL2VA 15+5는 현재 제작 기본값에서 제외하고 원인 분리 실험에만 사용한다. **R2V/V2V/AI2V는 `scripts/generate_minimax_h3_optimized.py` 우선**을 유지한다. FLF는 기본형의 VAE 전 모델 해제 보완 후 8초·576×1024 저장 성공을 확인했고, 네이티브 해상도 성공은 사용자가 보고했다. 2026-10-05 기본 I2V는 8초·576×1024 두 번과 직후 짧은 실행을 서버 재시작 없이 검증했다. T2V 및 native 고해상도 전체의 장시간 안정성 검증을 뜻하지 않는다.



가이드: [H3_OPTIMIZED_GUIDE](workflows/human/minimax_h3/H3_OPTIMIZED_GUIDE.md). V2V는 영상 참조 생성, AI2V는 오디오+이미지 참조 생성이며 H3 생성 오디오를 저장한다. 원본 WAV를 그대로 입히거나 정확한 립싱크를 보장하지 않는다. `generate_minimax_h3`는 FL2VA 기본 생성과 polish/carry/특수 혼합 참조에 사용한다. 잠긴 카메라는 먼저 `camera-previz`를 따르고, 필요한 이미지+참조 영상 입력을 지원하는 기존 경로를 유지한다. `generate_minimax_h3_7plus1`은 기존 R2V 호환 도구로 유지한다. 생성물과 리뷰는 호출하는 프로젝트에 저장하며 failure_note / generation-prompt / output-review 절차를 유지한다.



## 0. OPTIONAL — Full episode direction rail (only if your project uses it)



**If your project chooses** the factory’s long-form shot pipeline (music video / story episode with `stories/<ep>/` + assemble):



### 0.A Skills directory (portable director brain)



| Item | Path |

|------|------|

| **Skill SSOT** | **[skills/](skills/)** · equip contract [skills/README.md](skills/README.md) |

| **Director skill** | **[skills/video-direction/SKILL.md](skills/video-direction/SKILL.md)** |

| **Camera lock** | **[skills/camera-previz/SKILL.md](skills/camera-previz/SKILL.md)** — Blender plate → H3 `--ref-video`. CLI: `python scripts/generate_previz.py`. Hub copy: `F:\AI_Skills\skills\camera-previz` |



**Rule:** If your agent session does **not** already have `video-direction` loaded:



```bash

python scripts/skill_equip.py list

python scripts/skill_equip.py install video-direction --target grok   # or claude / all

python scripts/skill_equip.py install camera-previz --target all      # grok/claude/codex/gemini/cursor/hub

# Minimum if install unavailable: READ skills/video-direction/SKILL.md fully and adopt it

```



Lock a 3D camera / 프리비즈 / playblast → load `camera-previz` **before** `generate_camera_move`. Do not invent that path in an I2V prompt.



Do **not** skip to `shot_compose` / batch motion without this skill (or equivalent master persona load).



### 0.B Documents (deep SSOT — after skill load)



| Order | Document | Why |

|-------|----------|-----|

| **1** | **[skills/video-direction/SKILL.md](skills/video-direction/SKILL.md)** | **Equip first** — gated direction + handoff |

| **2** | **[skills/generation-prompt/SKILL.md](skills/generation-prompt/SKILL.md)** | **Before generate** — still/I2V/SI2V prompt packs (no tag-soup) |

| **2b** | **[skills/output-review/SKILL.md](skills/output-review/SKILL.md)** | **After generate** — open file, judge brief, next lever |

| **3** | **[docs/video_director_master_persona.md](docs/video_director_master_persona.md)** | Long-form shot grammar SSOT |

| **4** | [docs/video_creative_director_persona.md](docs/video_creative_director_persona.md) | Creative Pack fields |

| **5** | [docs/image_cut_verification_gate.md](docs/image_cut_verification_gate.md) | Open-file QA before approve |

| **6** | [docs/generation_prompt_craft.md](docs/generation_prompt_craft.md) | Factory prompt SSOT (Rule 7.5) |



Paste and adopt the skill SYSTEM identity (and master persona §1 if diving deep).



### If using this optional rail, produce before episode mainline



1. **Equip** `video-direction` skill (install or full read)  

2. `CREATIVE.md` — one-image pitch, paradox, motifs×3, anti-list, thumbnail thesis  

3. `SHOT_DESIGN.md` — **size rhythm line** + per-shot type / angle / move / intent / risk  

4. **Equip** `generation-prompt` → per-shot **still + motion** prompts (quality gates)  

5. Only then: assets → keyframes → visual QA → motion → freeze gate → assemble  



**If not using this rail:** skip §0 and call tools from [docs/tool_catalog.md](docs/tool_catalog.md) only.



### Hard bans



| Ban | Instead |

|-----|---------|

| Pipeline tables only as “planning” | Director + DP thinking first |

| Three identical framings in a row | Size/angle change every cut |

| Lyric slide-show | Visual jobs per section (chorus = event) |

| Face CU for every emotional line | Coverage: wide / medium / insert / CU |

| Freeze-pad short I2V to fake length | Full-length motion or split shots |

| Mass `approved` without opening files | QA_LOG per shot |

| Weak tag-soup prompts (`8k masterpiece…`) | [generation_prompt_craft.md](docs/generation_prompt_craft.md): Subject→Action→Light→Camera |

| I2V prompt re-describing face/wardrobe | Motion/camera only |



### Generation prompts (quality)



Before every T2I / I2I / I2V / SI2V call:



1. Equip **[skills/generation-prompt](skills/generation-prompt/SKILL.md)**  

2. Expand SHOT_DESIGN → still/i2v/si2v strings (quality gates)  

3. Follow **[docs/generation_prompt_craft.md](docs/generation_prompt_craft.md)** (Rule **7.5**): Subject→Action→Light→Camera; I2V motion-only  



Planning without prompt craft still yields poor stills/clips — **direction + prompts** both required.



### Image / cut verification



Before `keyframe_status=approved` or `clip_status=approved`:



1. `shot_qa_pack` → **open pack** (ref|current|prev) · checklist · `shot_qa_record`  

2. Fail anatomy / identity drift / freeze → regenerate — **approve without QA JSON = exit 23**  

3. 3+ keyframes: `episode_identity_sheet` + identity pass (cross-shot cast)  





### Failure notes (shared across agents)



Learn from prior agents — **do not repeat known mistakes**.



```bash

# BEFORE generating / storyboarding

python scripts/failure_note.py search "freeze OR framing OR car OR feet"

python scripts/failure_note.py list --limit 10



# AFTER any FAIL or user rejection

python scripts/failure_note.py add --stage keyframe --tags ... \

  --symptom "..." --cause "..." --fix "..." --prevention "..." \

  --severity high --agent <you> -e EP -s S0x

```



Docs: [docs/failure_notes_system.md](docs/failure_notes_system.md) · folder [failures/](failures/) · Rule **7.4**.



Rules: [agent_rules.md](agent_rules.md) **7.0** (persona) · **7.2** (order) · **7.3** (visual QA) · **7.4** (failure notes) · **7.5** (prompts) · **8.0** (your tools).



### Use YOUR tools and skills (do not wait for the user to name them)



The user **cannot** know every agent’s private tools, skills, MCP servers, or plugins.  

For video work you **must proactively** pick anything you can actually call that improves **quality or speed**, while keeping factory gates.



| Do | Don’t |

|----|--------|

| Inventory your session capabilities and use them | Ask “which tool?” every step |

| Research, edit stills, preview motion, vision-QA, subagents… when useful | Only run bare `scripts/*` when better options exist |

| Write approved clips into **your project**, then assemble there | Skip QA because a native tool “looked fine” |

| Obey user if they lock a tool (“Comfy only”) | Invent tools you don’t have |



Full rule: [docs/agent_native_capability_autonomy.md](docs/agent_native_capability_autonomy.md) · Rule **8.0**  

Grok mapping: [docs/grok_build_hybrid_tooling.md](docs/grok_build_hybrid_tooling.md) · Rule **8.1**



---



## Critical rule (consumer agents)



1. Run CLIs from this repo root (`python scripts/...`).

2. **Every output path is in YOUR project** (`-o` / `--output` / `--dest` or `AGENT_WORKSPACE`).

3. Do **not** write finished media into `stories/`, `dumps/`, `characters/<id>/`, or `deliveries/`.

4. If the only copy lives in this repo, the job is **incomplete**.



```bash

set AGENT_WORKSPACE=PATH/TO/YOUR/PROJECT

python scripts/generate_i2v.py -i "%AGENT_WORKSPACE%/stills/S01.png" -o "%AGENT_WORKSPACE%/clips/S01.mp4"

```



Full contract: [docs/agent_consumer_workspace_contract.md](docs/agent_consumer_workspace_contract.md)  

AV reliability: [docs/agent_av_smoke_checklist.md](docs/agent_av_smoke_checklist.md)  

Tooling backlog: [docs/agent_video_tooling_todo.md](docs/agent_video_tooling_todo.md)  

Planning SOP: [docs/creative_brief_autonomy_design.md](docs/creative_brief_autonomy_design.md)  

Maintainers: [agent_rules.md](agent_rules.md)  



Default: **agent picks factory + its own tools/skills** until the user names a tool; factory remains SSOT for lips/assemble/gates (Rule **8.0**).



## Video highway (short)



```bash

# 0) LOAD master persona + write CREATIVE.md + SHOT_DESIGN.md  (Rule 7.0)

# ComfyUI :8188

python scripts/smoke_agent_av.py -e EP

# keyframe open+QA → approve, then motion, then clip open+QA → approve

python scripts/shot_qa_pack.py -e EP -s S0x

python scripts/shot_qa_record.py -e EP -s S0x --stage keyframe --verdict pass --pass-required --notes "..."

python scripts/shot_approve.py -e EP -s S0x --status approved

python scripts/shot_approve.py -e EP -s S0x --clip approved   # after clip QA record

python scripts/episode_status.py -e EP

python scripts/assemble_video.py -e EP --stage work

# 납품 마스터 (concat 아님): equip video-edit → EDIT_PLAN →

python scripts/edit_pack.py -i a.mp4 -i b.mp4 --text "포기하지 마" --look night \

  -o "$AGENT_WORKSPACE/edits/s01/master.mp4" --qa

python scripts/export_episode_to_workspace.py -e EP --dest "$AGENT_WORKSPACE/episodes/EP"

```



**Rule:** never jump to final assemble to judge middle cuts. Approve each work clip first. Assemble rejects unapproved clips (exit 22) unless `--force-clip-gate` (debug only). `assemble_video` is debug concat. Delivery master is `edit_pack`.



## Short music covers



For YuE2 커버곡 / generated singing / reference singing: read `skills/yue2-cover/SKILL.md`, then use `python scripts/cover_music.py doctor`. Follow `workflows/human/cover_music/AGENT_GUIDE.md`. Generated voice is the default; reference voice conversion is optional when requested. This audio-only workflow does not need video direction or camera skills.

<!-- DENOMIX-8PLUS2-20261030 -->
## DenoMix H3 R2V8+2 — opt-in

Use `python scripts/generate_minimax_h3_denomix.py --status`, then [DenoMix guide](workflows/human/minimax_h3_denomix/AGENT_GUIDE.md). Default requested5s, hard local request cap10s;10s aligns to243frames/10.125s.15s was safely interrupted for resource pressure, not an OOM exception. Within-shot appearance and ASR are bounded observations; exact identity, listening and lip sync remain unapproved. No installs, service restart or queue cancellation. Existing H3 default routes remain unchanged.
<!-- /DENOMIX-8PLUS2-20261030 -->
