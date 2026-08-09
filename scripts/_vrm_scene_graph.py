#!/usr/bin/env python3
import json
import struct
from pathlib import Path


def load(path):
    data = path.read_bytes()
    off = 12
    gltf = None
    while off + 8 <= len(data):
        clen, ctype = struct.unpack_from("<I4s", data, off)
        off += 8
        chunk = data[off : off + clen]
        off += clen
        if ctype == b"JSON":
            gltf = json.loads(chunk.decode("utf-8"))
    return gltf


def dump(path: Path):
    g = load(path)
    nodes = g["nodes"]
    print("===", path.name, "===")
    print("scenes", g.get("scenes"))
    print("scene", g.get("scene"))

    def walk(i, depth=0):
        n = nodes[i]
        flags = []
        if "mesh" in n:
            flags.append(f"mesh={n['mesh']}")
        if "skin" in n:
            flags.append(f"skin={n['skin']}")
        if "translation" in n:
            flags.append(f"t={n['translation']}")
        if "rotation" in n:
            flags.append(f"r={n['rotation']}")
        if "scale" in n:
            flags.append(f"s={n['scale']}")
        print("  " * depth + f"[{i}] {n.get('name')!r} " + " ".join(flags))
        for c in n.get("children") or []:
            walk(c, depth + 1)

    for root in g["scenes"][0]["nodes"]:
        walk(root)

    # materials
    mats = g.get("materials", [])
    print("materials", len(mats))
    for i, m in enumerate(mats[:3]):
        print(" ", i, m.get("name"), list(m.keys()))
        pbr = m.get("pbrMetallicRoughness") or {}
        print("   pbr", list(pbr.keys()), "baseColorTexture" in pbr)

    # extensions VRMC
    vrm = g["extensions"]["VRMC_vrm"]
    print("meta", vrm.get("meta"))
    print("firstPerson", vrm.get("firstPerson"))
    print("lookAt", vrm.get("lookAt"))
    # humanoid rest pose?
    print("humanoid keys", vrm.get("humanoid", {}).keys())


dump(Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports\mecha_yame_v2.vrm"))
print()
dump(Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports\mecha_patlabor_v3_warudo.vrm"))
