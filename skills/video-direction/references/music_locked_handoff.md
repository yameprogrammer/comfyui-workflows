# Music-locked planning and PC-HOME handoff

Read for music-led MV planning. Keep CREATIVE.md, SHOT_DESIGN.md, PROMPT_PACK and EDIT_PLAN as the existing deliverables; this reference adds evidence and timing, not a second production workflow.

## Audio lock before timed shots

Identify the selected audio file, SHA256, actual duration and selection status. Record which facts were measured (tool/method), directly listened to (windows covered), supplied by the user, estimated, or unverified. A file hash proves identity, not musical analysis. Do not invent BPM, lyric timing, section boundaries or listening results. Without the actual track, write provisional planning and label timing unverified; do not call it audio-locked.

Map actual intro/verse/pre/chorus/bridge/outro or the track's own structure to start/end times, emotion, energy and one visual duty. Distinguish measured boundaries from creative interpretations. Check beat estimates against audible attacks/phrases; energy peaks alone do not establish BPM. Preserve deliberate chorus/motif repetition with meaningful variation. Cut on phrases, accents, action or emotional turns as appropriate; no mandatory cut on every beat, fixed lead-frame offset or ban on repeated 30-second passages.

## Shot timing and source lineage

Use a declared rational fps and integer frame intervals: start_frame inclusive, end_frame exclusive; duration = (end-start)/fps. Timecodes are display values derived from frames; state whether they are elapsed-time or SMPTE and declare drop-frame when used. Establish the total picture frame count from the measured audio duration, rounding policy and any intentional tail; report the resulting sub-frame audio difference.

For the main picture track, require first start=0, positive durations, adjacent end=next start and last end=declared total. Flag unexplained gaps/overlaps; keep overlays/transitions on explicitly separate tracks. Pin lip/performance windows to absolute master-audio positions, then fit other shots into the remaining gaps. Record optional signed cut offsets in frames relative to a named cue, with a reason; recheck continuity after applying them.

Each SHOT_DESIGN row binds section, duty, emotion/energy, time interval, existing character/wardrobe/look anchors, image prompt and motion prompt references. Use generation-prompt's chosen model dialect. For each clip, retain source path/version, source in/out, planned use interval and related prompt revision. Request selective regeneration only for affected shots; do not change unaffected anchors or footage.

Confirm the chosen backend/profile's current supported clip duration in the actual environment and record the evidence. A project's current limit (for example eight seconds) is not a universal model rule. Split longer designed shots at intentional action/phrase boundaries; budget handles within the limit. Generated take length and edited use length are distinct. Do not freeze-pad short motion to meet the master duration or stretch the locked song merely to fit pictures.

## Minimal edit-plan supplement

If machine-readable handoff helps, attach these fields to EDIT_PLAN rather than create a competing project tree:

```json
{
  "audio": {"path": "selected-master.wav", "sha256": "record actual hash", "duration_sec": null, "evidence": "unverified"},
  "fps": {"num": 30, "den": 1},
  "total_frames": null,
  "sections": [],
  "shots": [],
  "handoff": {"saved_blend": null, "sha256": null}
}
```

For sections use existing IDs, start_frame/end_frame, emotion/energy, duty and evidence. For shots use existing shot_id, section_id, start_frame/end_frame, source path and source_in_frame/source_out_frame with source fps, anchor IDs and prompt_ref; add cut_offset_frames only when needed. Null means unknown and blocks timing validation, not zero. Hash strings above are illustrative, not evidence.

This is a planning supplement, **not edit_timeline.v1, a Remotion composition or a Blender import schema**. Any tool-specific conversion is a separate, explicit step that must preserve timing and lineage and validate its resulting timeline. Planning JSON is not authority to rebuild a user's edited blend.

## PC-HOME editing and final-save authority

Before editing on PC-HOME read C:/Users/parkp/ai-vault/decisions/video_edit_pipeline.md, its PC-HOME section and the target project's AGENTS.md. This branch overrides generic factory edit_pack/FFmpeg delivery instructions for these projects. Follow images (Flow/image tools/local as authorized) → local clips → Remotion source and short graphics/transparent clips → Blender VSE editable cuts/audio/TEXT captions → user preview/manual edits/save → exact latest saved blend → separate render copy and release QC. Keep assets and documents inside the project's existing layout.

In a request to output an already hand-edited blend, skip rebuilding from CREATIVE/SHOT_DESIGN/old JSON: identify the exact saved path, record hash, distinguish unsaved/dirty GUI state, and avoid simultaneous saves. Inspect saved timeline/source links, render from a separate copy only within current authority, and re-acquire if the user's saved hash changes. Keep original media and user edits intact; use original sources with proxies disabled for final output. Do not occupy mouse/keyboard/focus or initialize/replace the user's layout. Follow the shared document's MCP and known-crash restrictions.

Preserve existing lower Korean burn-in. Keep ordinary captions editable; change Remotion-baked text through its source and replace only that graphics clip. Where the project requires them, prepare per-final-video EN/JA SRT and KO/EN/JA upload copy, with actual final audio/timeline correspondence and release QC; translations alone do not prove subtitle completion. Inspect actual frames/decode/audio as authorized and report unverified checks rather than claim release readiness.

Project authority remains decisive: D:/drama stays planning/prompts only, with user-run previz/render and no shell media generation/render unless a current explicit instruction changes that scope. Shared editing documentation, this reference, or an old delegation in another project does not expand it. Neither planning nor local QC authorizes paid generation or public posting.
