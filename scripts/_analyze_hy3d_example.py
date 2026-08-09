import json
from pathlib import Path

ui_path = Path(
    r"F:/ComfyUI_windows_portable/ComfyUI/custom_nodes/ComfyUI-Hunyuan3DWrapper/example_workflows/hy3d_example_01.json"
)
ui = json.loads(ui_path.read_text(encoding="utf-8"))
print("=== NODES ===")
for n in ui.get("nodes", []):
    t = n.get("type", "")
    w = n.get("widgets_values", [])
    print(f"id={n.get('id')} type={t} w={w[:12]}")

print("\n=== LINKS ===")
links = ui.get("links", [])
print("link_count", len(links))
# [id, from_node, from_slot, to_node, to_slot, type]
by_dst = {}
for L in links:
    if not isinstance(L, list) or len(L) < 5:
        continue
    lid, src, sslot, dst, dslot = L[0], L[1], L[2], L[3], L[4]
    by_dst.setdefault(dst, []).append((src, sslot, dslot, L[5] if len(L) > 5 else ""))
    print(L)

# Build simplified stage map
print("\n=== GEOMETRY CHAIN (expected) ===")
print("LoadImage -> rembg/resize -> Hy3DGenerateMesh -> VAEDecode -> Postprocess -> Export")
print("=== TEXTURE CHAIN (expected) ===")
print("Delight -> UVWrap -> RenderMV -> SampleMV -> Bake -> Inpaint -> Apply -> Export")
