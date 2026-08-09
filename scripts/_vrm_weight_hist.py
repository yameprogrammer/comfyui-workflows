#!/usr/bin/env python3
import struct
import json
from pathlib import Path
from collections import Counter


def load(path):
    data = path.read_bytes()
    off = 12
    gltf = None
    bin_chunk = None
    while off + 8 <= len(data):
        clen, ctype = struct.unpack_from("<I4s", data, off)
        off += 8
        chunk = data[off : off + clen]
        off += clen
        if ctype == b"JSON":
            gltf = json.loads(chunk.decode("utf-8"))
        elif ctype == b"BIN\x00":
            bin_chunk = chunk
    return gltf, bin_chunk


def hist(path: Path):
    gltf, bin_chunk = load(path)
    nodes = gltf["nodes"]
    skin = gltf["skins"][0]
    joints = skin["joints"]
    prim = gltf["meshes"][0]["primitives"][0]
    attrs = prim["attributes"]
    accessors = gltf["accessors"]
    views = gltf["bufferViews"]

    ja = accessors[attrs["JOINTS_0"]]
    wa = accessors[attrs["WEIGHTS_0"]]
    jv = views[ja["bufferView"]]
    wv = views[wa["bufferView"]]
    joff = (jv.get("byteOffset") or 0) + (ja.get("byteOffset") or 0)
    woff = (wv.get("byteOffset") or 0) + (wa.get("byteOffset") or 0)
    n = ja["count"]
    jctype = ja["componentType"]
    wctype = wa["componentType"]
    print(path.name, "verts", n, "jctype", jctype, "wctype", wctype, "joints", len(joints))

    joint_weight_sum = Counter()
    verts_with_non_hips = 0
    max_j = 0
    # component sizes
    # 5121 ubyte, 5123 ushort, 5125 uint, 5126 float
    for i in range(n):
        if jctype == 5121:
            js = struct.unpack_from("<4B", bin_chunk, joff + i * 4)
        elif jctype == 5123:
            js = struct.unpack_from("<4H", bin_chunk, joff + i * 8)
        else:
            raise RuntimeError(jctype)
        if wctype == 5126:
            ws = struct.unpack_from("<4f", bin_chunk, woff + i * 16)
        elif wctype == 5121:
            raw = struct.unpack_from("<4B", bin_chunk, woff + i * 4)
            ws = tuple(x / 255.0 for x in raw)
        elif wctype == 5123:
            raw = struct.unpack_from("<4H", bin_chunk, woff + i * 8)
            ws = tuple(x / 65535.0 for x in raw)
        else:
            raise RuntimeError(wctype)
        max_j = max(max_j, max(js))
        used_non_zero = False
        for j, w in zip(js, ws):
            if w > 1e-5:
                joint_weight_sum[j] += w
                if j != 0:
                    used_non_zero = True
        if used_non_zero:
            verts_with_non_hips += 1

    print("max_joint_index", max_j, "verts_with_non_joint0", verts_with_non_hips)
    print("top joints by weight sum:")
    for j, s in joint_weight_sum.most_common(25):
        name = nodes[joints[j]].get("name") if j < len(joints) else "?"
        print(f"  idx={j:2d} name={name:16s} sum={s:.1f}")
    # humanoid
    hb = gltf["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"]
    print("humanoid head node", hb.get("head"), "->", nodes[hb["head"]["node"]].get("name"))
    print("humanoid leftUpperArm", hb.get("leftUpperArm"), "->", nodes[hb["leftUpperArm"]["node"]].get("name"))
    # is mesh parented under armature?
    print("mesh nodes skin", [(i, n.get("name"), n.get("skin"), n.get("children")) for i, n in enumerate(nodes) if "mesh" in n])
    # scene roots
    print("scenes", gltf.get("scenes"))


def main():
    hist(Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports\mecha_yame_v2.vrm"))
    print("---")
    hist(Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports\mecha_patlabor_v3_warudo.vrm"))


if __name__ == "__main__":
    main()
