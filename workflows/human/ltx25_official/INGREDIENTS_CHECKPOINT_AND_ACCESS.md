<!-- LTX25-CURRENT-START -->
> **LTX-2.5 현재 상태 (2026-10-16T15:46:24.123116+00:00): ready_experimental.** T2V/I2V/FLF/T2A/A2V 짧은 실행 확인; Ingredients는 소품/장소 참조 시각 PASS, 정확 얼굴·청취는 pending. 이전 실패/접근 차단 문장은 당시 이력이다. [현재 사용 가이드](F:/Agent_media_tools/workflows/human/ltx25_official/AGENT_GUIDE.md)에서 시트 규칙·실패 양상·검증 입력/출력·정확 재현 명령·미검증 목록을 확인한다. [복구 진단](C:/Users/parkp/Documents/Codex/2026-10-16/task-8/INGREDIENTS_DIAGNOSIS.md).
<!-- LTX25-CURRENT-END -->

# Ingredients checkpoint and access decision

Checked 2026-10-16 15:09 UTC / 2026-10-17 00:09 KST. GPU remains assigned to TTS.

## Which checkpoint

The new LTX-2.5 Ingredients model-card route uses:

- Page: https://huggingface.co/Lightricks/LTX-2.5-22b-IC-LoRA-Ingredients
- Revision: `12040e4091ac2008d3906a594e31a7fb1ab9d546`
- File: `ltx-2.5-22b-ic-lora-ingredients-0.9.safetensors`
- Size: 1,308,787,472 bytes. The gated public tree redacts the LFS object hash; no full hash or downloaded integrity is claimed.
- Model-card base metadata says `LTX-2.5-22B (dev)`; the same card's inference snippet explicitly uses `ltx_pipelines.ic_lora` with a distilled LTX-2.5 transformer. These are training/base metadata versus a specified inference recipe. Do not infer that a dev checkpoint must be downloaded just from the metadata. This local path has not yet been executed.

The separately pinned ComfyUI-LTXVideo commit `44c8a36b7c31ee00b4271daed11dc2a4aa481140` provides `example_workflows/2.5/LTX-2.5_ICLoRA_Ingredients_Single_Stage_Distilled.json`, but that exact JSON selects **`ltx-2.3-22b-ic-lora-ingredients-0.9.safetensors`** on the 2.5 distilled base. This is a distinct official workflow-defined compatibility route. Its adapter page is https://huggingface.co/Lightricks/LTX-2.3-22b-IC-LoRA-Ingredients, revision `dcc403d92aa0f5a983c5dbc7282503ca52f73a08`, size1,308,778,338 bytes.

Decision: for a new **2.5 Ingredients adapter evaluation**, target the 2.5 file/card route. Preserve the original pinned JSON unchanged as source evidence; make a separately labelled local candidate based on the 2.5 card, not a silent replacement. If reproducing the pinned official Comfy JSON unchanged instead, target only its exact 2.3 adapter. Do not download both by default. The official compatibility guide expressly documents this distinction: https://docs.ltx.io/open-source-model/integration-tools/ic-lo-ra-adapters#ingredients

## Components and reference data

For the 2.5 card's native Python two-stage inference recipe: LTX-2.5 distilled BF16 transformer, `gemma4-12b-with-proj-ltx-2.5-bf16.safetensors`, supported 2.5 video VAE, `ltx-2.5-audio-vae-bf16.safetensors`, and `ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors`, plus the Ingredients adapter. Do not use Comfy INT8 files in native Python.

For this 4090 installation, use a separately verified ComfyUI candidate with the existing INT8 ConvRot distilled transformer and LTX-specific Gemma4 INT8 encoder, existing 2.5 DiffVAE/audio VAE, and IC-LoRA reference-conditioning nodes. A spatial upscaler is needed only if that candidate actually uses two stages; the pinned single-stage Ingredients graph does not. The optional lighter 2.5 ConvVAE is absent; it is not required just to obtain the adapter. No replacement base model or Gemma3 download is justified at this point.

The card does not list a separate Ingredients config/text-embedding/tokenizer file. The base-model components remain separate. A plain generic LoRA loader without the reference-conditioning path is insufficient.

Reference data: a clean black-background, text-free reference sheet of character/prop/location panels, repeated as a static video. Reference downscale factor1, matching output geometry/fps, at least121 frames. Start at768×448,121frames,24fps and adapter strength1.0. Prompt must contain `Reference sheet: ...` and `Generated video: ...`. These are the documented trained/reference settings; 24GB execution and identity quality remain unverified.

## Authentication versus consent

Read-only diagnostics with the existing configured HF credential:

- `/api/whoami-v2`:401, `Invalid username or password.` No account identity or token was printed.
- Official2.5 pinned-file HEAD:401, `X-Error-Code: GatedRepo`.
- Same unauthenticated HEAD:401, `GatedRepo`.
- Public metadata says `gated=auto`; both public file listings are readable. File listing availability is not download authorization.

Conclusion: the credential presented is not accepted by HF. Expired/revoked/wrong credentials are possible; the exact cause and the account's existing model approval cannot be established. Do not claim that the user has not agreed to the model. First restore a valid authorized login; then check this exact repo's access. No alternative mirror, token workaround, access request, model download, or gate acceptance was performed.

The public gate asks the user to share contact information and says Agree and Access acknowledges Lightricks' privacy policy and consents to offers/updates including targeted/personalized advertising, with unsubscribe available. If the authenticated account has not already accepted that gate, fresh explicit user consent is required; generic installation approval is not automatically that consent.

## License

The2.5 model card links `LTX-2.x Community License Agreement`, dated2026-08-11: https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x . The earlier repository source snapshot's January LICENSE is a different artifact and is not a substitute for the current2.5 model license.

The current license is conditional, not unrestricted public-domain/Apache licensing. Section2 covers the entity-wide $10M annual-revenue threshold and its defined non-commercial exception; redistribution/fine-tune transfer and AttachmentA have additional requirements. The binding linked license controls. This audit does not establish the user's entity eligibility or accept any new terms.

Evidence: ingredients-access-diagnostic.json; ingredients-file-metadata.json; workflows/human/ltx25_official/SOURCES.json.


## Resolved by manual user download — 2026-10-16T15:25:12.160419+00:00

User-authorized move complete: exact2.5 checkpoint is at `F:/model/loras/LTX2.5/ltx-2.5-22b-ic-lora-ingredients-0.9.safetensors`; Downloads duplicate removed after fullhash/header verification. No auth/consent changes. Local SHA256 ff873a5beada3c579a8137c7c53343916f78bcc9a529ba910143073fe8715e95; authoritative upstream SHA equality unavailable. Historical initial two runs completed with visual FAIL; later clean-sheet/positional-prompt repair visually PASSED for the bounded prop case. Exact human identity/listening remain pending. See AGENT_GUIDE.md and `C:/Users/parkp/Documents/Codex/2026-10-16/task-8/ingredients-local-verification.json`. Earlier access diagnosis is historical, not a current model-availability blocker.
