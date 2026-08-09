#!/usr/bin/env python3
"""
Remap VRMC_vrm humanoid bones to the skinned PascalCase armature nodes.

Warudo was animating a second ghost skeleton (hips/head/leftUpperArm...) that
has no mesh weights, so head/arms appeared frozen.
"""

from __future__ import annotations

import json
import struct
import shutil
from pathlib import Path

EXPORTS = Path(r"D:\캐릭터\drafts\mecha_patlabor_v3\exports")
SRC = EXPORTS / "mecha_patlabor_v3_warudo.vrm"
# also fix the non-warudo name
ALSO = [EXPORTS / "mecha_patlabor_v3.vrm"]

# VRMC_vrm humanBone key -> Blender/export joint name with weights
REMAP = {
    "hips": "Hips",
    "spine": "Spine",
    "chest": "Chest",
    "upperChest": "Chest",
    "neck": "Neck",
    "head": "Head",
    "leftShoulder": "LeftShoulder",
    "leftUpperArm": "LeftUpperArm",
    "leftLowerArm": "LeftLowerArm",
    "leftHand": "LeftHand",
    "rightShoulder": "RightShoulder",
    "rightUpperArm": "RightUpperArm",
    "rightLowerArm": "RightLowerArm",
    "rightHand": "RightHand",
    "leftUpperLeg": "LeftUpperLeg",
    "leftLowerLeg": "LeftLowerLeg",
    "leftFoot": "LeftFoot",
    "rightUpperLeg": "RightUpperLeg",
    "rightLowerLeg": "RightLowerLeg",
    "rightFoot": "RightFoot",
}


def load_glb(path: Path) -> tuple[dict, bytes | None, bytes]:
    data = path.read_bytes()
    assert data[:4] == b"glTF", "not glTF"
    # header
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    off = 12
    json_chunk = None
    bin_chunk = None
    while off + 8 <= len(data):
        clen, ctype = struct.unpack_from("<I4s", data, off)
        off += 8
        chunk = data[off : off + clen]
        off += clen
        if ctype == b"JSON":
            json_chunk = json.loads(chunk.decode("utf-8"))
        elif ctype == b"BIN\x00":
            bin_chunk = chunk
    if json_chunk is None:
        raise RuntimeError("no JSON chunk")
    return json_chunk, bin_chunk, data[:12]


def save_glb(path: Path, gltf: dict, bin_chunk: bytes | None) -> None:
    json_bytes = json.dumps(gltf, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    # pad json to 4 bytes with spaces
    pad = (4 - (len(json_bytes) % 4)) % 4
    json_bytes += b" " * pad

    chunks = b""
    chunks += struct.pack("<I4s", len(json_bytes), b"JSON") + json_bytes
    if bin_chunk is not None:
        bin_pad = (4 - (len(bin_chunk) % 4)) % 4
        bin_data = bin_chunk + (b"\x00" * bin_pad)
        chunks += struct.pack("<I4s", len(bin_data), b"BIN\x00") + bin_data

    total = 12 + len(chunks)
    header = struct.pack("<4sII", b"glTF", 2, total)
    path.write_bytes(header + chunks)


def fix_file(path: Path) -> dict:
    gltf, bin_chunk, _ = load_glb(path)
    nodes = gltf["nodes"]
    name_to_idx = {}
    for i, n in enumerate(nodes):
        name = n.get("name")
        if name and name not in name_to_idx:
            # prefer first occurrence (skinned PascalCase chain appears first)
            name_to_idx[name] = i

    ext = gltf.get("extensions", {}).get("VRMC_vrm")
    if not ext:
        return {"path": str(path), "error": "no VRMC_vrm"}
    humanoid = ext.setdefault("humanoid", {})
    hb = humanoid.setdefault("humanBones", {})

    before = {k: v.get("node") for k, v in hb.items()}
    changes = []
    for key, bone_name in REMAP.items():
        if bone_name not in name_to_idx:
            continue
        idx = name_to_idx[bone_name]
        old = hb.get(key, {}).get("node") if key in hb else None
        hb[key] = {"node": idx}
        if old != idx:
            old_name = nodes[old]["name"] if old is not None else None
            changes.append(f"{key}: {old_name}({old}) -> {bone_name}({idx})")

    # backup
    bak = path.with_suffix(path.suffix + ".pre_humanoid_fix.bak")
    if not bak.is_file():
        shutil.copyfile(path, bak)

    save_glb(path, gltf, bin_chunk)

    # verify
    gltf2, _, _ = load_glb(path)
    hb2 = gltf2["extensions"]["VRMC_vrm"]["humanoid"]["humanBones"]
    verify = {k: gltf2["nodes"][v["node"]]["name"] for k, v in sorted(hb2.items())}

    return {
        "path": str(path),
        "size": path.stat().st_size,
        "changes": changes,
        "verify": verify,
        "humanBone_count": len(hb2),
    }


def main() -> int:
    targets = []
    if SRC.is_file():
        targets.append(SRC)
    for p in ALSO:
        if p.is_file() and p not in targets:
            targets.append(p)
    if not targets:
        print("no vrm files")
        return 1
    for p in targets:
        r = fix_file(p)
        print(json.dumps(r, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
