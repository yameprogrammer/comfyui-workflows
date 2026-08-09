#!/usr/bin/env python3
"""Deep compare working mecha_yame_v2 VRM vs mecha_patlabor_v3 VRM for Warudo motion."""

from __future__ import annotations

import json
import struct
from pathlib import Path


def load_glb(path: Path):
    data = path.read_bytes()
    assert data[:4] == b"glTF"
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
    return gltf, bin_chunk, len(data)


def analyze(path: Path) -> dict:
    gltf, bin_chunk, size = load_glb(path)
    nodes = gltf.get("nodes", [])
    meshes = gltf.get("meshes", [])
    skins = gltf.get("skins", [])
    accessors = gltf.get("accessors", [])
    views = gltf.get("bufferViews", [])

    info = {
        "path": str(path),
        "size": size,
        "nodes": len(nodes),
        "meshes": len(meshes),
        "skins": len(skins),
        "extensions_used": gltf.get("extensionsUsed"),
        "extensions_required": gltf.get("extensionsRequired"),
        "scene": gltf.get("scene"),
        "scenes": gltf.get("scenes"),
    }

    # mesh attrs
    if meshes:
        prim = meshes[0]["primitives"][0]
        info["mesh_attrs"] = list(prim.get("attributes", {}).keys())
        info["mesh_material"] = prim.get("material")
        info["mesh_mode"] = prim.get("mode")
        # joints/weights accessor stats
        for key in ("JOINTS_0", "WEIGHTS_0", "POSITION"):
            ai = prim.get("attributes", {}).get(key)
            if ai is None:
                continue
            acc = accessors[ai]
            info[f"acc_{key}"] = {
                "count": acc.get("count"),
                "type": acc.get("type"),
                "componentType": acc.get("componentType"),
                "normalized": acc.get("normalized"),
                "max": acc.get("max"),
                "min": acc.get("min"),
            }

    # skins
    skin_infos = []
    for si, skin in enumerate(skins):
        joints = skin.get("joints", [])
        joint_names = [nodes[j].get("name") for j in joints]
        ibm_i = skin.get("inverseBindMatrices")
        ibm_count = accessors[ibm_i]["count"] if ibm_i is not None else None
        skin_infos.append(
            {
                "index": si,
                "joint_count": len(joints),
                "ibm_count": ibm_count,
                "skeleton": skin.get("skeleton"),
                "joint_names": joint_names,
                "duplicate_names": [n for n in joint_names if joint_names.count(n) > 1],
            }
        )
    info["skins_detail"] = skin_infos

    # which nodes have mesh
    mesh_nodes = [(i, n.get("name"), n.get("mesh"), n.get("skin")) for i, n in enumerate(nodes) if "mesh" in n]
    info["mesh_nodes"] = mesh_nodes

    # VRM extension
    ext = gltf.get("extensions", {})
    vrmc = ext.get("VRMC_vrm") or ext.get("VRM")
    info["vrm_ext_key"] = "VRMC_vrm" if "VRMC_vrm" in ext else ("VRM" if "VRM" in ext else None)
    if vrmc:
        info["vrm_spec"] = vrmc.get("specVersion")
        hb = (vrmc.get("humanoid") or {}).get("humanBones") or {}
        # normalize vrm0 vs vrm1
        if not hb and "humanoid" in vrmc:
            # VRM0 style humanBones list?
            h0 = vrmc["humanoid"]
            info["humanoid_raw_keys"] = list(h0.keys())
            hb = h0.get("humanBones") or {}
        mapped = {}
        for k, v in hb.items():
            if isinstance(v, dict):
                ni = v.get("node")
            else:
                ni = None
            name = nodes[ni].get("name") if ni is not None and ni < len(nodes) else None
            in_joints = False
            if skins and ni is not None:
                in_joints = ni in skins[0].get("joints", [])
            mapped[k] = {"node": ni, "name": name, "in_skin_joints": in_joints}
        info["humanBones"] = mapped
        info["humanBone_count"] = len(mapped)
        # missing required
        required = [
            "hips", "spine", "head",
            "leftUpperArm", "leftLowerArm", "leftHand",
            "rightUpperArm", "rightLowerArm", "rightHand",
            "leftUpperLeg", "leftLowerLeg", "leftFoot",
            "rightUpperLeg", "rightLowerLeg", "rightFoot",
        ]
        # case variants for VRM0
        def has_req(r):
            if r in mapped:
                return True
            # camelCase already
            return False
        info["missing_required"] = [r for r in required if not has_req(r)]

    # sample weights: first 20 verts joint indices used
    if meshes and bin_chunk is not None and "JOINTS_0" in meshes[0]["primitives"][0].get("attributes", {}):
        ji = meshes[0]["primitives"][0]["attributes"]["JOINTS_0"]
        wi = meshes[0]["primitives"][0]["attributes"]["WEIGHTS_0"]
        ja = accessors[ji]
        wa = accessors[wi]
        jv = views[ja["bufferView"]]
        wv = views[wa["bufferView"]]
        joff = (jv.get("byteOffset") or 0) + (ja.get("byteOffset") or 0)
        woff = (wv.get("byteOffset") or 0) + (wa.get("byteOffset") or 0)
        # UNSIGNED_SHORT = 5123, UNSIGNED_BYTE = 5121, FLOAT weights 5126
        jctype = ja["componentType"]
        wctype = wa["componentType"]
        n = min(50, ja["count"])
        used_joints = set()
        nonzero_w = 0
        if jctype == 5123:  # ushort
            for i in range(n):
                js = struct.unpack_from("<4H", bin_chunk, joff + i * 8)
                if wctype == 5126:
                    ws = struct.unpack_from("<4f", bin_chunk, woff + i * 16)
                elif wctype == 5121:
                    ws = tuple(x / 255.0 for x in struct.unpack_from("<4B", bin_chunk, woff + i * 4))
                else:
                    ws = (1, 0, 0, 0)
                for j, w in zip(js, ws):
                    if w > 1e-5:
                        used_joints.add(j)
                        nonzero_w += 1
        info["sample_used_joint_indices"] = sorted(used_joints)
        info["sample_joint_names"] = [
            skins[0]["joints"][j] if j < len(skins[0]["joints"]) else None for j in sorted(used_joints)
        ]
        info["sample_joint_names"] = [
            nodes[skins[0]["joints"][j]].get("name") for j in sorted(used_joints) if j < len(skins[0]["joints"])
        ]
        # max joint index across all verts (sample more)
        max_j = 0
        n2 = min(5000, ja["count"])
        if jctype == 5123:
            for i in range(n2):
                js = struct.unpack_from("<4H", bin_chunk, joff + i * 8)
                max_j = max(max_j, max(js))
        info["max_joint_index_sampled"] = max_j
        info["skin_joint_array_len"] = len(skins[0]["joints"]) if skins else 0

    # node name collision
    names = [n.get("name") for n in nodes]
    info["duplicate_node_names"] = sorted({n for n in names if n and names.count(n) > 1})

    return info


def main():
    v2_candidates = list(Path(r"D:\캐릭터\drafts\mecha_yame_v2\exports").glob("*.vrm"))
    v3 = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports\mecha_patlabor_v3_warudo.vrm")
    print("=== V2 files ===")
    for p in v2_candidates:
        print(p.name, p.stat().st_size)

    results = {}
    if v2_candidates:
        # prefer largest / warudo named
        v2 = None
        for p in v2_candidates:
            if "warudo" in p.name.lower() or p.name == "mecha_yame_v2.vrm":
                v2 = p
                break
        if v2 is None:
            v2 = max(v2_candidates, key=lambda p: p.stat().st_size)
        results["v2"] = analyze(v2)
    results["v3"] = analyze(v3)

    out = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports\vrm_compare.json")
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", out)

    # print key diffs
    if "v2" in results:
        a, b = results["v2"], results["v3"]
        keys = [
            "size", "nodes", "skins", "vrm_ext_key", "vrm_spec", "humanBone_count",
            "mesh_attrs", "duplicate_node_names", "missing_required",
            "max_joint_index_sampled", "skin_joint_array_len",
        ]
        print("\n=== KEY COMPARE ===")
        for k in keys:
            print(f"{k}: v2={a.get(k)} | v3={b.get(k)}")
        print("\nV2 humanBones sample:", list((a.get("humanBones") or {}).items())[:8])
        print("V3 humanBones sample:", list((b.get("humanBones") or {}).items())[:8])
        print("\nV2 skins:", a.get("skins_detail"))
        print("V3 skins:", b.get("skins_detail"))
        print("\nV2 mesh_nodes:", a.get("mesh_nodes"))
        print("V3 mesh_nodes:", b.get("mesh_nodes"))
        print("\nV2 sample joints:", a.get("sample_joint_names"))
        print("V3 sample joints:", b.get("sample_joint_names"))


if __name__ == "__main__":
    main()
