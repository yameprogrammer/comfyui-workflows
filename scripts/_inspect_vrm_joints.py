import struct
import json
from pathlib import Path

p = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports\mecha_patlabor_v3_warudo.vrm")
data = p.read_bytes()
off = 12
while off + 8 <= len(data):
    clen, ctype = struct.unpack_from("<I4s", data, off)
    off += 8
    chunk = data[off : off + clen]
    off += clen
    if ctype != b"JSON":
        continue
    j = json.loads(chunk.decode("utf-8"))
    nodes = j["nodes"]
    skin = j["skins"][0]
    joints = skin["joints"]
    print("ALL JOINTS:")
    for i, ji in enumerate(joints):
        n = nodes[ji]
        print(
            f"  [{i}] node={ji} name={n.get('name')!r} children={n.get('children')} mesh={n.get('mesh')}"
        )
    hb = j["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"]
    print("\nHUMAN BONES -> node name:")
    for k, v in sorted(hb.items()):
        ni = v.get("node")
        name = nodes[ni].get("name") if ni is not None else None
        in_skin = ni in joints if ni is not None else False
        print(f"  {k}: node={ni} name={name!r} in_skin_joints={in_skin}")
    print("inverseBindMatrices", "inverseBindMatrices" in skin)
    # parent chain of Hips vs hips
    print("\nNODE PARENT MAP for arm/head:")
    # build child->parent
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children") or []:
            parent[c] = i
    for target in ("Head", "head", "LeftUpperArm", "leftUpperArm", "Hips", "hips"):
        idx = next((i for i, n in enumerate(nodes) if n.get("name") == target), None)
        if idx is None:
            print(target, "NOT FOUND")
            continue
        chain = [target]
        cur = idx
        while cur in parent:
            cur = parent[cur]
            chain.append(nodes[cur].get("name"))
        print(target, "->", " / ".join(chain))
    break
