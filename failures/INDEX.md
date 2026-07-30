# Failure notes INDEX (auto-generated)

Do not edit by hand — `python scripts/failure_note.py add` regenerates.

| id | sev | stage | tags | symptom |
|----|-----|-------|------|---------|
| `FN-20260729-002` | high | clip | infinitetalk, missing_node, s2v, comfy_n | generate_s2v --backend infinitetalk fails QUEUE_FAILED missing_node_type WanV... |
| `FN-20260729-001` | high | character_sheet | identity_drift, full_sheet, auto_approve | full_sheet for green_lighter_idol_v1 drifts face from master_front; costume s... |
| `FN-20260715-006` | high | keyframe | prompt_ignored, face_cu_spam, insert_fai | Weak or conflicted prompts: character face core overrode insert/action; tag-s... |
| `FN-20260715-005` | critical | planning | mass_approve, qa_skipped | User required self keyframe/clip verification but agent mass-approved without... |
| `FN-20260715-004` | critical | storyboard | same_framing, face_cu_spam, shot_grammar | S05 S06 S08 S09 S13 S15-S18 nearly identical face/upper framings; user reject... |
| `FN-20260715-003` | high | keyframe | car_geometry, glass_mirror, anatomy_feet | Car door open with contorted body; S11 body/car break; S12 side mirror looks ... |
| `FN-20260715-002` | high | keyframe | anatomy_feet, insert_failed, face_cu_spa | Shoe insert requested but result was face close-up with deformed raised leg/f... |
| `FN-20260715-001` | critical | clip | freeze_pad, duration_mismatch, qa_skippe | All cuts freeze for last 30-50 percent of duration (e.g. S01 freezes 5s-8s). ... |

_Updated: 2026-07-29T22:25:54+00:00 · count=8_
