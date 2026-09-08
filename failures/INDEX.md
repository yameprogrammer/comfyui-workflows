# Failure notes INDEX (auto-generated)

Do not edit by hand — `python scripts/failure_note.py add` regenerates.

| id | sev | stage | tags | symptom |
|----|-----|-------|------|---------|
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

_Updated: 2026-09-08T23:10:54+00:00 · count=30_
