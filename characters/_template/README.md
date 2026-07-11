# Character package template

Copy this folder to `characters/<character_id>/` (or use `character_create.py`).

## Required workflow (L2)

1. Fill `bible.json` + `prompts/positive_core.txt` + `negative_core.txt`
2. Generate masters → `refs/master/`
3. `character_approve.py --as master_front`
4. Expand sheets → `refs/turnaround|expression|costume/`
5. Approve MVP aliases into `approved/`
6. Set `bible.status` / `manifest.status` to `approved` when L2 MVP complete

See: `../../character_impl_spec.md`
