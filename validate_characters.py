#!/usr/bin/env python3
"""
Project Real Loser — Character Asset Validator (validate_characters.py)
Target Engine: Unity 2022.3.40f1 LTS (URP, Android ARM64 IL2CPP)
"""

import os
import sys
import json
import struct
import hashlib
from typing import Dict, List, Tuple, Any

REQUIRED_CHARACTERS = [
    "chr_player_body_a",
    "chr_enemy_e1_recruit",
    "chr_enemy_e2_rifleman",
    "chr_enemy_e3_officer",
    "chr_enemy_e4_shotgunner",
    "chr_enemy_e5_smg_runner",
    "chr_enemy_e6_sniper",
    "chr_enemy_e7_heavy_gunner",
    "chr_enemy_e8_shield_breacher",
    "chr_enemy_e9_technician",
    "chr_enemy_e10_dog_handler",
    "chr_enemy_e11_medic",
    "chr_enemy_e12_elite_commando",
    "chr_enemy_e13_ghillie_spotter",
    "chr_enemy_e14_juggernaut",
    "chr_civ_worker_a",
    "chr_civ_scientist_a",
    "chr_civ_hostage_a",
    "chr_civ_technician_a",
    "chr_npc_dr_mirza",
    "chr_npc_informant",
    "chr_boss_captain_dar",
    "chr_boss_commander_rask",
    "chr_boss_viktor_hale",
]

REQUIRED_15_BONES = [
    "Hips",
    "Spine",
    "Chest",
    "Neck",
    "Head",
    "UpperArmL",
    "LowerArmL",
    "HandL",
    "UpperArmR",
    "LowerArmR",
    "HandR",
    "UpperLegL",
    "LowerLegL",
    "UpperLegR",
    "LowerLegR",
]


def parse_glb(filepath: str) -> Tuple[Dict[str, Any], bytes]:
    with open(filepath, "rb") as f:
        data = f.read()
    if len(data) < 20:
        raise ValueError("File too small to be a valid .glb")
    magic, version, total_len = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF":
        raise ValueError(f"Invalid magic bytes: {magic!r}")
    if version != 2:
        raise ValueError(f"Unsupported glTF version: {version}")
    if total_len != len(data):
        raise ValueError(f"Header length {total_len} != file size {len(data)}")

    json_len, json_type = struct.unpack_from("<II", data, 12)
    if json_type != 0x4E4F534A:
        raise ValueError("First chunk is not JSON")
    json_bytes = data[20 : 20 + json_len]
    gltf = json.loads(json_bytes.decode("utf-8"))

    bin_offset = 20 + json_len
    if bin_offset + 8 > len(data):
        raise ValueError("Missing BIN chunk")
    bin_len, bin_type = struct.unpack_from("<II", data, bin_offset)
    if bin_type != 0x004E4942:
        raise ValueError("Second chunk is not BIN")
    bin_data = data[bin_offset + 8 : bin_offset + 8 + bin_len]
    return gltf, bin_data


def validate_character_glb(filepath: str) -> Tuple[bool, List[str], Dict[str, Any]]:
    errors: List[str] = []
    meta: Dict[str, Any] = {}
    try:
        gltf, bin_data = parse_glb(filepath)
    except Exception as exc:
        return False, [f"GLB parse failure: {exc}"], meta

    nodes = gltf.get("nodes", [])
    skins = gltf.get("skins", [])
    meshes = gltf.get("meshes", [])
    accessors = gltf.get("accessors", [])
    buffer_views = gltf.get("bufferViews", [])

    if not skins:
        errors.append("Missing `skins` array in glTF.")
    else:
        skin = skins[0]
        joints = skin.get("joints", [])
        if len(joints) != 15:
            errors.append(f"Expected 15-bone humanoid skin rig, found {len(joints)} joints.")
        joint_names = [nodes[j].get("name", "") for j in joints if j < len(nodes)]
        missing_bones = [b for b in REQUIRED_15_BONES if b not in joint_names]
        if missing_bones:
            errors.append(f"Missing required humanoid bones: {missing_bones}")
        if "inverseBindMatrices" not in skin:
            errors.append("Skin missing `inverseBindMatrices` accessor.")

    mesh_by_name = {m.get("name", ""): m for m in meshes}
    lod_counts = {}
    lod0_bbox = None
    lod0_pos_hash = None

    for lod_tag in ("LOD0", "LOD1", "LOD2"):
        matched_mesh = None
        for mname, m in mesh_by_name.items():
            if mname.endswith(f"_{lod_tag}") or mname == lod_tag:
                matched_mesh = m
                break
        if not matched_mesh:
            errors.append(f"Missing required {lod_tag} mesh.")
            continue

        prims = matched_mesh.get("primitives", [])
        if not prims:
            errors.append(f"{lod_tag} mesh has no primitives.")
            continue

        prim = prims[0]
        attrs = prim.get("attributes", {})
        for req_attr in ("POSITION", "NORMAL", "JOINTS_0", "WEIGHTS_0"):
            if req_attr not in attrs:
                errors.append(f"{lod_tag} primitive missing required attribute '{req_attr}'.")

        pos_acc_idx = attrs.get("POSITION")
        if pos_acc_idx is not None and pos_acc_idx < len(accessors):
            pos_acc = accessors[pos_acc_idx]
            lod_counts[lod_tag] = int(pos_acc.get("count", 0))
            if lod_tag == "LOD0":
                cmin = pos_acc.get("min", [0, 0, 0])
                cmax = pos_acc.get("max", [0, 0, 0])
                lod0_bbox = (
                    round(float(cmax[0] - cmin[0]), 4),
                    round(float(cmax[1] - cmin[1]), 4),
                    round(float(cmax[2] - cmin[2]), 4),
                )
                bv = buffer_views[pos_acc["bufferView"]]
                offset = bv.get("byteOffset", 0) + pos_acc.get("byteOffset", 0)
                length = bv["byteLength"]
                lod0_pos_hash = hashlib.sha256(bin_data[offset : offset + length]).hexdigest()

    if len(lod_counts) == 3:
        if not (lod_counts["LOD0"] > lod_counts["LOD1"] > lod_counts["LOD2"] > 0):
            errors.append(
                f"Invalid LOD vertex reduction order: LOD0={lod_counts['LOD0']}, "
                f"LOD1={lod_counts['LOD1']}, LOD2={lod_counts['LOD2']}"
            )

    meta["bbox"] = lod0_bbox
    meta["vertex_hash"] = lod0_pos_hash
    meta["lod_counts"] = lod_counts
    return (len(errors) == 0), errors, meta


def validate_all_characters(char_dir: str) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not os.path.isdir(char_dir):
        return False, [f"Character directory not found: {char_dir}"]

    seen_hashes: Dict[str, str] = {}
    bboxes: Dict[str, Tuple[float, float, float]] = {}

    for char_id in REQUIRED_CHARACTERS:
        glb_path = os.path.join(char_dir, f"{char_id}.glb")
        if not os.path.exists(glb_path):
            errors.append(f"Missing required character GLB: {glb_path}")
            continue
        ok, c_errs, meta = validate_character_glb(glb_path)
        if not ok:
            for e in c_errs:
                errors.append(f"[{char_id}] {e}")
            continue

        vhash = meta.get("vertex_hash")
        if vhash in seen_hashes:
            errors.append(
                f"[DUPLICATE GEOMETRY] {char_id} shares identical vertex buffer hash with {seen_hashes[vhash]}"
            )
        elif vhash:
            seen_hashes[vhash] = char_id

        if meta.get("bbox"):
            bboxes[char_id] = meta["bbox"]

    char_list = [c for c in REQUIRED_CHARACTERS if c in bboxes]
    for i in range(len(char_list) - 1):
        c1, c2 = char_list[i], char_list[i + 1]
        b1, b2 = bboxes[c1], bboxes[c2]
        vol1 = b1[0] * b1[1] * b1[2]
        vol2 = b2[0] * b2[1] * b2[2]
        rel_diff_vol = abs(vol1 - vol2) / max(vol1, vol2, 1e-6)
        max_axis_diff = max(
            abs(b1[k] - b2[k]) / max(b1[k], b2[k], 1e-6) for k in range(3)
        )
        if max(rel_diff_vol, max_axis_diff) < 0.05:
            errors.append(
                f"[BBOX SIMILARITY] {c1} {b1} and {c2} {b2} differ by less than 5% "
                f"(vol_diff={rel_diff_vol*100:.2f}%, axis_diff={max_axis_diff*100:.2f}%)."
            )

    return (len(errors) == 0), errors


def main() -> int:
    char_dir = sys.argv[1] if len(sys.argv) > 1 else "Assets/_Project/Art/Characters"
    ok, errs = validate_all_characters(char_dir)
    if ok:
        print(
            f"[PASS] All {len(REQUIRED_CHARACTERS)} character .glb assets in '{char_dir}' "
            f"passed 15-bone rig, LOD0/1/2, unique hash, and >=5% bbox differentiation checks."
        )
        return 0
    else:
        print(f"[FAIL] Character validation failed with {len(errs)} error(s):")
        for e in errs:
            print(f"  - {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
