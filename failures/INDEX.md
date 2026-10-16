# Failure notes INDEX (auto-generated)

Do not edit by hand — `python scripts/failure_note.py add` regenerates.

| id | sev | stage | tags | symptom |
|----|-----|-------|------|---------|
| `FN-20261016-009` | medium | advanced_motion_quality | ltx25, retake, extension, union, control | Temporal mask Retake runs but requested blue-ball rewrite fails; Union canny ... |
| `FN-20261016-008` | medium | motion_quality | ltx25, ingredients, identity, speech, va | Some face reference sheets retain panels; default-quality facial speech drift... |
| `FN-20261016-007` | medium | clip | ltx25, ingredients, reference-layout | Ingredients output retains reference-sheet black margins and second panel ins... |
| `FN-20261016-006` | medium | audio | higgs3, windows, encoding, subprocess | Higgs3 original8188 inference loaded weights but worker failed on progress-ba... |
| `FN-20261016-005` | medium | keyframe | flux3, style_transfer, content_drift | 0.25MP style transfer copied donor composition |
| `FN-20261016-004` | medium | keyframe | flux3, style_transfer, reference_resolut | Stronger whole-image style caption still retains photographic material |
| `FN-20261016-003` | medium | keyframe | flux3, style_transfer, reference | Watercolor transfer kept photographic teapot and wood texture |
| `FN-20261016-002` | medium | keyframe | flux3, reference, background | Character edit retained original indoor plaster wall when garden was requested |
| `FN-20261016-001` | medium | keyframe | flux3, multi_reference, framing | Two-reference teapot composition occluded blue handle and mismatched scale |
| `FN-20261014-001` | medium | clip | minimax_h3, r2v, loop, gaze | Pia 1080 R2V7+1 preserved viewer gaze and changed late head/mouth, breaking d... |
| `FN-20261012-004` | medium | edit | shorts, first-frame, cut-boundary, flash | Music-selected Shorts start exposes 1-2 frames of prior shot, and a brief nex... |
| `FN-20261012-003` | high | edit | render_edit, chained_concat, duration, f | Five valid video sections total4837frames rendered into3789video frames while... |
| `FN-20261012-002` | high | tool | h3, ref_video, output_selection, input_p | Image plus video R2V returned LoadVideo input preview rather than generated S... |
| `FN-20261012-001` | medium | clip | h3, r2v, ref2va, spatial_continuity, pro | MV006 direct image-reference production S02v001 preserves family identities b... |
| `FN-20261011-011` | medium | clip | h3, r2v, paper, fold, scale, framing | MV006 S19 image-reference R2V v001 and v002 convert small single-fold N04 int... |
| `FN-20261011-010` | medium | reference_repair | qwen, instantx, inpaint, mask, block_noi | MV006 K_PM masked wall repair produced colored block noise inside white mask ... |
| `FN-20261011-009` | medium | reference_sheet | krea2, identity_edit, hair, viewpoint | MV006 generic side prompt ponytail if present invented tied hair on short-hai... |
| `FN-20261011-008` | low | keyframe | krea2, style, prompt_adherence | MV006 modern anime sample B rendered as simplified storybook illustration ins... |
| `FN-20261011-007` | medium | still | krea2, framing, paper, contact | MV006 watercolor look v001 cropped legs and invented memo touch; v002 still c... |
| `FN-20261011-006` | medium | edit_qa | ffmpeg, frame-extraction, subtitle-qa | Sparse selected image2 VFR QA sequence can repeat or substitute frames even w... |
| `FN-20261011-005` | high | clip | minimax_h3, near_static_tail, motion_qa | MV005 S12 v002 had a 4+ second near-static generated tail. A frame pass based... |
| `FN-20261011-004` | high | clip | minimax_h3, unrequested_prop, book_conti | MV005 S15 face reaction generated an open book and supporting hand entering t... |
| `FN-20261011-003` | high | video | minimax_h3, native, bag, screen_directio | MV005 S57 native v001 sat naturally but placed dark bag inside the next woman... |
| `FN-20261011-002` | high | edit_qa | ffmpeg, animatic, color_range, frame_cou | MV005 render_edit reported344.32sec/exit0 but video229.24sec5731frames; audio... |
| `FN-20261011-001` | high | output_review | anatomy, continuity, quality | Still QA passed incorrect hand and lap ownership plus degraded style; user ca... |
| `FN-20261010-009` | medium | previz | blender, camera, marker | Additional overhead layout rendered with shot camera despite assigning layout... |
| `FN-20261010-008` | medium | clip | h3, ref2va, exact_dialogue, prompt_leaka | MV004 H01 T01 independent ASR detected extra opening words before target dial... |
| `FN-20261010-007` | medium | motion | minimax_h3, hands, incomplete_motion | MV004 S26 native73frames keeps hands at temples; planned2.72s slot lacks comp... |
| `FN-20261010-006` | medium | clip | minimax_h3, silent_reaction, closed_mout | MV004 S09 quiet two-shot introduced repeated boy jaw/lip opening despite tiny... |
| `FN-20261010-005` | medium | clip | minimax_h3, condensation, glasses, conti | MV004 S08 clear-lens glance I2V introduced persistent droplets on the left le... |
| `FN-20261010-004` | medium | motion | minimax_h3, i2v, glasses, hand_contact | MV004 S25 v001 keeps glasses coherent but cuff retreats and bare fingertips o... |
| `FN-20261010-003` | low | previz | blender, previz, exposure, visibility | MV004 first S07/S28 3D plates kept dolly framing but Standard-view bright are... |
| `FN-20261010-002` | medium | still | flow, nano_banana, multi_reference, layo | MV004 Flow new stills retained style-reference counter geometry or merely hel... |
| `FN-20261010-001` | high | clip | h3, r2v, ref2va, two-subject, gesture | Ref2VA two-person input became Harin-only close portrait; Seah omitted and ra... |
| `FN-20261009-004` | high | s2v | comfyui, gpu, execution_interrupted, con | Native calm S05 sampler interrupted at 10/20; another prompt then ran. |
| `FN-20261009-003` | high | composite.qa | head, neck, torso, warp, temporal_QC | User rejected welcome v004: excessive head movement and detached head versus ... |
| `FN-20261009-002` | medium | motion | infinitetalk, body_motion, cfg, performa | Welcome S01 prompt-only stable-talk T01 retains torso bounce; sparse flow dy1... |
| `FN-20261009-001` | medium | composite.qa | blender, mouth, seam, tracking | MV003 S44 T04 has a detached faint chin mark in frames38-46 and78-88 below no... |
| `FN-20261008-007` | medium | video | h3, eye, reflection, continuity | MV003 S39 T01 tiny gold iris-edge point grows and travels across iris |
| `FN-20261008-006` | medium | motion | minimax_h3, i2v, gesture, continuity | MV003 S29 T01 gaze-down prompt invented unjoined hand rising to chest from fr... |
| `FN-20261008-005` | high | motion | minimax_h3, night_continuity, gaze | S15 reflected golden light became sunrise/daylight; S16 pupil-only awareness ... |
| `FN-20261008-004` | medium | motion | minimax_h3, continuity, event_timing, fi | MV003 S11 T01 adds multiple colored fireworks before designed first event S14 |
| `FN-20261008-003` | medium | inpaint | qwen, inpaint, mouth, mask, artifacts | S44 local Qwen ye pose has colored mosaic clusters around lip border |
| `FN-20261008-002` | medium | motion | minimax_h3, i2v, gesture, continuity | MV003 S55 T01 added right-hand chin touch during blink despite relaxed arms b... |
| `FN-20261008-001` | medium | motion | minimax_h3, silent_articulation, phoneme | MV003 S44 work I2V T01 produced three broad similar openings with0.67secclose... |
| `FN-20261005-010` | medium | motion | infinitetalk, expression, audio_tail, pu | Welcome Seah pilot S02 retains kiss-like puckered lips and exaggerated eyebro... |
| `FN-20261005-011` | medium | audio_prepare | qwen3_tts, SaveAudioMP3, container, wav_ | generate_qwen3_tts -o S01.wav writes MP3 payload because graph uses SaveAudio... |
| `FN-20261005-009` | medium | tool_preflight | qwen_image_21, preset_schema, comfy_vali | qwen_image_21_edit fails Comfy validation: switch missing, cache dtype missin... |
| `FN-20261005-008` | high | keyframe | qwen, multi_reference, two_people, ident | Welcome BG_HS first insertion retained one Harin-like face and changed yellow... |
| `FN-20261005-007` | high | video | minimax_h3, vram, hang, cache | MiniMax H3 holds almost all VRAM at 0/20 Model Initializing; shortening durat... |
| `FN-20261005-006` | high | qa | qa_scope, source_hash, subtitle_sync, au | Earlier MV passed technical checks despite visible quality defects; automatic... |
| `FN-20261005-005` | high | edit | fps, trim, concat, frame_count, endpoint | Mixed source/output frame grids and nested concat required endpoint correctio... |
| `FN-20261005-004` | high | motion | minimax_h3, reflection, lip_motion, hand | MV rebuild R018 reflection blinked and turned independently; R022/R029 produc... |
| `FN-20261005-003` | high | thumbnail | style_mismatch, viewer_expectation, refe | Dedicated MV thumbnail v001 looked much more detailed than the actual animati... |
| `FN-20261005-002` | high | audio_mix | adelay, afade, silent_music, qa_scope | Lumi curation v003 became digitally silent after 14 seconds despite global pe... |
| `FN-20261005-001` | high | motion | minimax_h3, aspect_ratio, stretch | MV faces and props distorted after arbitrary aspect stills entered H3; small ... |
| `FN-20261004-002` | high | keyframe | anime, identity, multi_reference | Qwen edit of H02 retained original juvenile head silhouette rather than selec... |
| `FN-20261004-001` | medium | storyboard | anima, framing, infant, hands | Storyboard T2I produced duplicate portraits for a hand insert and implausible... |
| `FN-20261003-003` | medium | clip | minimax_h3 | B native contains an unintended 0-3 second spoken preface before the complete... |
| `FN-20261003-002` | medium | clip | minimax_h3 | Carry-from generation returned the 22-frame silent input preview instead of t... |
| `FN-20261003-001` | medium | clip | minimax_h3 | Greeting wave at 0.7-2.2 seconds but speech starts at 3.8 seconds in A native. |
| `FN-20260924-003` | high | h3_i2v | h3, vae | Video decode stays at full GPU after the sampler finishes and never writes th... |
| `FN-20260924-002` | high | h3_i2v | h3, rainbow | A colored spectrum band grows across the rooftop floor. |
| `FN-20260924-001` | high | keyframe | s02, krea2_style, crop | 16:9 kneel crops the eyes or turns into a reach |
| `FN-20260919-002` | high | clip | h3, r2v, camera_roll, composition, rejec | scene_07_h3_take01 exhibited severe 35-degree camera roll and diagonal horizo... |
| `FN-20260919-001` | high | clip | h3, r2v, previz, proxy_leak | scene_02_h3_take01 exposed raw Blender proxy geometry (gray wall and orange c... |
| `FN-20260909-001` | high | keyframe | krea2, rebalance, black | generate_krea --rebalance 2.0 writes 1920x1088 RGB all-zero PNG (~10KB). Same... |
| `FN-20260908-006` | high | clip | h3, r2v, previz | Person R2V pasted master_full as a cardboard cutout onto the orange corridor_... |
| `FN-20260908-005` | high | clip | h3, B7, drop | S19 hanging-drop hold becomes a pouring stream by mid |
| `FN-20260908-004` | high | clip | h3, r2v, previz | Object R2V kept gray Blender proxy look instead of Krea watercolor Picture 1 |
| `FN-20260908-003` | high | keyframe | krea2, identity_edit, aspect | identity_edit output 1024x1024 instead of 1920x1088 |
| `FN-20260908-002` | high | keyframe | krea2, tower, drop | Hanging coffee drop rendered as Edison bulb or closed glass sphere |
| `FN-20260908-001` | medium | keyframe | krea, slow-drip, tower | Krea2 maps cold-brew tower to iced drinking tumbler |
| `FN-20260902-006` | high | keyframe | krea2, s12, t2i | T2I invented a printer, gibberish card text 데와단라CO, recast face, high angle, ... |
| `FN-20260902-005` | medium | still | krea, identity, pose, costume, sheet | kim costume_default from seated master_front stayed seated MCU twice (seeds 1... |
| `FN-20260902-004` | high | still | krea, identity, expression, smile | kim expr_knowing_laugh v1 (seed 455550237) became a teeth-wide commercial gri... |
| `FN-20260902-003` | high | still | krea, location, pantry, food_disco, yell | Pantry recast p03/p04 (seeds 52201/52202) got slim brown foil sticks but stil... |
| `FN-20260902-002` | high | still | krea, location, pos, card_insert, negati | Empty POS desk stills (54001/54002 and retry +100) always seat a standing hol... |
| `FN-20260902-001` | high | still | krea, location, pantry, food_disco, pack | Empty Korean office pantry gens (seeds 52001/52002 and retry +100) rendered y... |
| `FN-20260830-008` | high | keyframe | illustrious_advanced, style_drift, lora | Advanced_V37 ignored prompts; 6/6 locks = cyberpunk schoolgirl fire Tokyo sky... |
| `FN-20260830-007` | high | clip | i2v, motion, jump | Jump takeoff cannot be made to read as a jump after multiple I2V/FLF pairs |
| `FN-20260830-006` | high | clip | i2v, motion, jump | Takeoff FLF looks like a frog squat rubber-banding into a hanging doll with f... |
| `FN-20260830-005` | high | clip | i2v, motion, jump | Jump takeoff clip looks like mid-air pose morph; body stays hovering, no floo... |
| `FN-20260830-004` | high | clip | fall, s05_job, push-in, minimax_h3 | S04_11 t99 Luna sitting on the floor. Fall is Sequence 5 job. Camera also lef... |
| `FN-20260830-003` | high | clip | identity_swap, jersey, tracking, minimax | S04_09 tracking I2V: t50 silver hair wears 10; t99 camera flies to hoop, 10 i... |
| `FN-20260830-002` | high | clip | dunk, rim_grab, layup, minimax_h3 | S04_06 chorus-1 layup I2V became a rim-hang dunk by t50/t99. Hand grabbed the... |
| `FN-20260830-001` | high | clip | flf, zoom, camera_breathing, minimax_h3, | Static FLF clips S03_01 and S02_04: framing inflates/undulates mid-take (Ken ... |
| `FN-20260829-001` | high | clip | extra_hands, extra_limbs, flf, minimax_h | S01_05 FLF mid-frames grew helper arms from off-screen; jersey 11 became 1; s... |
| `FN-20260815-001` | medium | keyframe | inpaint, eye, krita, qwen, anima | Krita MCP ellipse fill looks stamped; Qwen InstantX inpaint upscaled 960->153... |
| `FN-20260729-002` | high | clip | infinitetalk, missing_node, s2v, comfy_n | generate_s2v --backend infinitetalk fails QUEUE_FAILED missing_node_type WanV... |
| `FN-20260729-001` | high | character_sheet | identity_drift, full_sheet, auto_approve | full_sheet for green_lighter_idol_v1 drifts face from master_front; costume s... |
| `FN-20260715-006` | high | keyframe | prompt_ignored, face_cu_spam, insert_fai | Weak or conflicted prompts: character face core overrode insert/action; tag-s... |
| `FN-20260715-005` | critical | planning | mass_approve, qa_skipped | User required self keyframe/clip verification but agent mass-approved without... |
| `FN-20260715-004` | critical | storyboard | same_framing, face_cu_spam, shot_grammar | S05 S06 S08 S09 S13 S15-S18 nearly identical face/upper framings; user reject... |
| `FN-20260715-003` | high | keyframe | car_geometry, glass_mirror, anatomy_feet | Car door open with contorted body; S11 body/car break; S12 side mirror looks ... |
| `FN-20260715-002` | high | keyframe | anatomy_feet, insert_failed, face_cu_spa | Shoe insert requested but result was face close-up with deformed raised leg/f... |
| `FN-20260715-001` | critical | clip | freeze_pad, duration_mismatch, qa_skippe | All cuts freeze for last 30-50 percent of duration (e.g. S01 freezes 5s-8s). ... |

_Updated: 2026-10-16T23:00:31+00:00 · count=97_
