#!/usr/bin/env python3
"""
Project Real Loser — Weapon Asset Validator (validate_weapons.py)
Target Engine: Unity 2022.3.40f1 LTS (URP, Android ARM64 IL2CPP)
"""

import os
import sys
import json
import struct
import hashlib
from typing import Dict, List, Tuple, Any

REQUIRED_WEAPONS = [
    "wpn_m9_beretta",
    "wpn_glock17_tactical",
    "wpn_usp45_suppressed",
    "wpn_makarov_pm",
    "wpn_deagle_50ae",
    "wpn_mp5sd_integral",
    "wpn_mp5a3_tactical",
    "wpn_uzi_pro",
    "wpn_pp19_bizon",
    "wpn_p90_pdw",
    "wpn_m4a1_sopmod",
    "wpn_ak47_m",
    "wpn_ak74u_krinkov",
    "wpn_g36c_commando",
    "wpn_aug_a2",
    "wpn_galil_ace",
    "wpn_spas12_tactical",
    "wpn_m870_breacher",
    "wpn_saiga12_auto",
    "wpn_svd_dragunov",
    "wpn_awm_l115a3",
    "wpn_m82_barrett",
    "wpn_m249_saw",
    "wpn_rpg7_launcher",
    "wpn_knife_mesh",
    "wpn_garrote_mesh",
]

REQUIRED_EMPTIES = [
    "GripR",
    "GripL",
    "Muzzle",
    "Eject",
    "Mag",
    "SightAnchor",
]


def parse_glb(filepath: str) -> Tuple[Dict[str, Any], bytes]:
    with open(filepath, "rb") as f:
        data = f.read()
    if len(data) < 20:
        raise ValueError("File too small to be a valid .glb")
    magic, version, total_len = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or total_len != len(data):
        raise ValueError("Invalid GLB header")
    json_len, json_type = struct.unpack_from("<II", data, 12)
    if json_type != 0x4E4F534A:
        raise ValueError("Missing JSON chunk")
    gltf = json.loads(data[20 : 20 + json_len].decode("utf-8"))
    bin_offset = 20 + json_len
    bin_len, bin_type = struct.unpack_from("<II", data, bin_offset)
    if bin_type != 0x004E4942:
        raise ValueError("Missing BIN chunk")
    bin_data = data[bin_offset + 8 : bin_offset + 8 + bin_len]
    return gltf, bin_data


def validate_weapon_glb(filepath: str) -> Tuple[bool, List[str], str]:
    errors: List[str] = []
    try:
        gltf, bin_data = parse_glb(filepath)
    except Exception as exc:
        return False, [f"GLB parse failure: {exc}"], ""

    nodes = gltf.get("nodes", [])
    meshes = gltf.get("meshes", [])

    if len(meshes) < 4:
        errors.append(f"Expected >= 4 articulated sub-meshes, found {len(meshes)}.")

    mesh_nodes = [n for n in nodes if "mesh" in n]
    if len(mesh_nodes) < 4:
        errors.append(f"Expected >= 4 articulated mesh nodes, found {len(mesh_nodes)}.")

    node_names = {n.get("name", ""): n for n in nodes}
    for emp in REQUIRED_EMPTIES:
        if emp not in node_names:
            errors.append(f"Missing required reference empty node '{emp}'.")
        else:
            n = node_names[emp]
            if "translation" not in n or len(n["translation"]) != 3:
                errors.append(f"Reference empty '{emp}' missing 3D `translation` vector.")

    vhash = hashlib.sha256(bin_data).hexdigest()
    return (len(errors) == 0), errors, vhash


def validate_all_weapons(wpn_dir: str) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not os.path.isdir(wpn_dir):
        return False, [f"Weapon directory not found: {wpn_dir}"]

    seen_hashes: Dict[str, str] = {}
    for wpn_id in REQUIRED_WEAPONS:
        glb_path = os.path.join(wpn_dir, f"{wpn_id}.glb")
        if not os.path.exists(glb_path):
            errors.append(f"Missing required weapon GLB: {glb_path}")
            continue
        ok, w_errs, vhash = validate_weapon_glb(glb_path)
        if not ok:
            for e in w_errs:
                errors.append(f"[{wpn_id}] {e}")
            continue
        if vhash in seen_hashes:
            errors.append(
                f"[DUPLICATE WEAPON GEOMETRY] {wpn_id} shares identical binary buffer with {seen_hashes[vhash]}"
            )
        else:
            seen_hashes[vhash] = wpn_id

    return (len(errors) == 0), errors


def main() -> int:
    wpn_dir = sys.argv[1] if len(sys.argv) > 1 else "Assets/_Project/Art/Weapons"
    ok, errs = validate_all_weapons(wpn_dir)
    if ok:
        print(
            f"[PASS] All {len(REQUIRED_WEAPONS)} weapon .glb assets in '{wpn_dir}' "
            f"passed 4-submesh articulation, 6 reference empties, and unique geometry checks."
        )
        return 0
    else:
        print(f"[FAIL] Weapon validation failed with {len(errs)} error(s):")
        for e in errs:
            print(f"  - {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
