#!/usr/bin/env python3
from __future__ import annotations

from lib import illustrious_pack_common as c
from lib import illustrious_standard_v37_runner as std
from lib.illustrious_advanced_v37_runner import FEATURE_GROUPS, UI_PATH, load_groups
from lib.ltx_aio_ui_expand import expand_ui_workflow_to_api


def main() -> None:
    ui = c.load_json(UI_PATH)
    groups = load_groups()["groups"]
    off = set(FEATURE_GROUPS.keys())
    ui2 = c.apply_group_modes(
        ui,
        groups,
        FEATURE_GROUPS,
        features_on=set(),
        features_off=off,
        default_on=set(),
    )
    oi = std._fetch_object_info()
    api = expand_ui_workflow_to_api(ui2, object_info=oi)
    std._reapply_widgets_from_ui(api, ui2, oi)
    std._fix_bad_widget_types(api)
    std._restore_links_from_ui(api, ui2)
    std._resolve_bypass_hops(api, ui2)
    std._fix_frontend_only_helpers(api)
    std._fix_combo_placeholders(api)
    std._fix_bad_widget_types(api)
    std._remap_detectors(api)
    std._restore_links_from_ui(api, ui2)
    std._resolve_bypass_hops(api, ui2)
    for n in api.values():
        ins = n.get("inputs") or {}
        for k, v in list(ins.items()):
            if isinstance(v, list) and len(v) == 2 and str(v[0]) not in api:
                del ins[k]

    for nid in ["80", "22", "93", "95", "98", "99", "164", "111", "57", "58", "103"]:
        node = api.get(nid)
        print("---", nid, None if not node else node.get("class_type"))
        if not node:
            continue
        for k, v in (node.get("inputs") or {}).items():
            if isinstance(v, list) and len(v) == 2:
                src = api.get(str(v[0]), {})
                print(f"  {k} <- {v}  src={src.get('class_type')}")
            else:
                print(f"  {k} = {v!r}")

    # validate types against object_info roughly for ImpactSwitch
    print("nodes in api", len(api))


if __name__ == "__main__":
    main()
