#!/usr/bin/env python3
"""
Project Real Loser — Procedural 15-Bone Rigged Humanoid Character .GLB Builder
Target Engine: Unity 2022.3.40f1 LTS (URP, Android ARM64 IL2CPP)

Generates all 24 rigged humanoid `.glb` files in `Assets/_Project/Art/Characters/`:
- 15-bone glTF 2.0 skin hierarchy (`Hips` -> `Spine` -> `Chest` -> `Neck` -> `Head`,
  plus left/right arms and legs) with `inverseBindMatrices`.
- Skinned mesh primitives with `POSITION`, `NORMAL`, `JOINTS_0`, `WEIGHTS_0`, `INDICES`.
- Multi-LOD meshes (`LOD0`, `LOD1`, `LOD2`) with strictly decreasing polygon density.
- Distinct silhouette geometry & >= 5% bounding box differentiation across archetypes.
"""

import os
import sys
import json
import math
import struct
from typing import List, Tuple, Dict, Any

BONE_DEFS = [
    # index, name, parent_idx, local_translation (x, y, z)
    (0, "Hips", None, [0.0, 0.95, 0.0]),
    (1, "Spine", 0, [0.0, 0.22, 0.0]),
    (2, "Chest", 1, [0.0, 0.24, 0.0]),
    (3, "Neck", 2, [0.0, 0.20, 0.0]),
    (4, "Head", 3, [0.0, 0.12, 0.0]),
    (5, "UpperArmL", 2, [-0.20, 0.16, 0.0]),
    (6, "LowerArmL", 5, [-0.26, 0.0, 0.0]),
    (7, "HandL", 6, [-0.22, 0.0, 0.0]),
    (8, "UpperArmR", 2, [0.20, 0.16, 0.0]),
    (9, "LowerArmR", 8, [0.26, 0.0, 0.0]),
    (10, "HandR", 9, [0.22, 0.0, 0.0]),
    (11, "UpperLegL", 0, [-0.11, -0.05, 0.0]),
    (12, "LowerLegL", 11, [0.0, -0.44, 0.0]),
    (13, "UpperLegR", 0, [0.11, -0.05, 0.0]),
    (14, "LowerLegR", 13, [0.0, -0.44, 0.0]),
]

# Archetype specifications with guaranteed >= 5% bounding box differentiation between consecutive entries
CHARACTER_SPECS = [
    # (char_id, width_scale, height_scale, depth_scale, gear_feature, base_color_rgba)
    ("chr_player_body_a",          1.00, 1.00, 1.00, "tac_vest_nvg",      [0.18, 0.22, 0.20, 1.0]),
    ("chr_enemy_e1_recruit",       0.92, 0.96, 0.90, "patrol_cap",        [0.42, 0.40, 0.32, 1.0]),
    ("chr_enemy_e2_rifleman",      1.04, 1.01, 1.02, "chest_rig",         [0.34, 0.38, 0.28, 1.0]),
    ("chr_enemy_e3_officer",       0.95, 1.05, 0.92, "officer_cap_radio", [0.25, 0.28, 0.35, 1.0]),
    ("chr_enemy_e4_shotgunner",    1.14, 0.98, 1.12, "breach_shoulder",   [0.38, 0.30, 0.24, 1.0]),
    ("chr_enemy_e5_smg_runner",    0.88, 0.95, 0.86, "light_harness",     [0.28, 0.32, 0.36, 1.0]),
    ("chr_enemy_e6_sniper",        0.96, 1.04, 1.08, "sniper_cape_hood",  [0.26, 0.34, 0.22, 1.0]),
    ("chr_enemy_e7_heavy_gunner",  1.24, 1.06, 1.26, "ammo_backpack",     [0.24, 0.26, 0.24, 1.0]),
    ("chr_enemy_e8_shield_breacher", 1.36, 1.02, 1.40, "ballistic_shield",[0.16, 0.18, 0.22, 1.0]),
    ("chr_enemy_e9_technician",    0.98, 0.97, 1.10, "tool_servo_pack",   [0.46, 0.42, 0.20, 1.0]),
    ("chr_enemy_e10_dog_handler",  1.08, 1.01, 0.98, "padded_sleeve",     [0.36, 0.32, 0.26, 1.0]),
    ("chr_enemy_e11_medic",        0.96, 0.99, 1.14, "medic_trauma_pack", [0.75, 0.78, 0.76, 1.0]),
    ("chr_enemy_e12_elite_commando", 1.10, 1.06, 1.04, "specops_quad_nvg",[0.12, 0.14, 0.16, 1.0]),
    ("chr_enemy_e13_ghillie_spotter", 1.22, 0.97, 1.25, "ghillie_mantle", [0.22, 0.36, 0.18, 1.0]),
    ("chr_enemy_e14_juggernaut",   1.48, 1.12, 1.44, "eod_heavy_armor",   [0.14, 0.15, 0.14, 1.0]),
    ("chr_civ_worker_a",           0.96, 0.96, 0.92, "hardhat_vest",      [0.82, 0.52, 0.14, 1.0]),
    ("chr_civ_scientist_a",        0.88, 1.01, 0.86, "lab_coat",          [0.90, 0.92, 0.94, 1.0]),
    ("chr_civ_hostage_a",          0.82, 0.92, 0.80, "bound_posture",     [0.54, 0.56, 0.62, 1.0]),
    ("chr_civ_technician_a",       0.94, 0.98, 0.96, "utility_belt",      [0.26, 0.44, 0.64, 1.0]),
    ("chr_npc_dr_mirza",           0.86, 1.03, 0.88, "glasses_coat",      [0.85, 0.86, 0.82, 1.0]),
    ("chr_npc_informant",          0.95, 0.99, 1.02, "hooded_jacket",     [0.24, 0.22, 0.20, 1.0]),
    ("chr_boss_captain_dar",       1.12, 1.06, 1.12, "beret_epaulettes",  [0.44, 0.16, 0.16, 1.0]),
    ("chr_boss_commander_rask",    1.26, 1.10, 1.22, "tactical_mantle",   [0.18, 0.20, 0.26, 1.0]),
    ("chr_boss_viktor_hale",       1.06, 1.04, 1.04, "armored_trench",    [0.10, 0.10, 0.12, 1.0]),
]


def add_skinned_box_limb(
    verts: List[Tuple[float, float, float]],
    norms: List[Tuple[float, float, float]],
    joints: List[Tuple[int, int, int, int]],
    weights: List[Tuple[float, float, float, float]],
    indices: List[int],
    center: Tuple[float, float, float],
    half_extents: Tuple[float, float, float],
    bone_idx_primary: int,
    bone_idx_secondary: int,
    subdiv_y: int,
    seed_jitter: float,
) -> None:
    """Adds a subdivided box limb segment weighted smoothly between two bones."""
    cx, cy, cz = center
    hx, hy, hz = half_extents

    # Create rings along Y from cy - hy to cy + hy
    rings = subdiv_y + 1
    base_v = len(verts)

    # 4 corner columns around perimeter in XZ
    perimeter = [
        (-hx, -hz, (-0.707, 0.0, -0.707)),
        (hx, -hz, (0.707, 0.0, -0.707)),
        (hx, hz, (0.707, 0.0, 0.707)),
        (-hx, hz, (-0.707, 0.0, 0.707)),
    ]

    for r in range(rings):
        t = r / float(subdiv_y)
        y = (cy - hy) + t * (2.0 * hy)
        # Taper/bulge profile for organic limb silhouette + unique seed_jitter
        bulge = 1.0 + 0.08 * math.sin(t * math.pi) + seed_jitter * 0.01 * math.cos(t * 2.0 * math.pi)
        w1 = round(1.0 - 0.35 * t, 4)
        w2 = round(1.0 - w1, 4)

        for px, pz, nrm in perimeter:
            verts.append((cx + px * bulge, y, cz + pz * bulge))
            norms.append(nrm)
            joints.append((bone_idx_primary, bone_idx_secondary, 0, 0))
            weights.append((w1, w2, 0.0, 0.0))

    for r in range(subdiv_y):
        ring_a = base_v + r * 4
        ring_b = base_v + (r + 1) * 4
        for side in range(4):
            nxt = (side + 1) % 4
            v00 = ring_a + side
            v01 = ring_a + nxt
            v10 = ring_b + side
            v11 = ring_b + nxt
            indices.extend([v00, v01, v11, v00, v11, v10])

    # Cap bottom and top
    bot = base_v
    top = base_v + subdiv_y * 4
    indices.extend([bot, bot + 2, bot + 1, bot, bot + 3, bot + 2])
    indices.extend([top, top + 1, top + 2, top, top + 2, top + 3])


def build_humanoid_lod_mesh(
    spec_idx: int,
    sx: float,
    sy: float,
    sz: float,
    gear_feature: str,
    subdiv_scale: int,
) -> Tuple[
    List[Tuple[float, float, float]],
    List[Tuple[float, float, float]],
    List[Tuple[int, int, int, int]],
    List[Tuple[float, float, float, float]],
    List[int],
]:
    verts: List[Tuple[float, float, float]] = []
    norms: List[Tuple[float, float, float]] = []
    joints: List[Tuple[int, int, int, int]] = []
    weights: List[Tuple[float, float, float, float]] = []
    indices: List[int] = []

    jitter = (spec_idx + 1) * 0.137

    # Pelvis / Hips (Bone 0 -> 1)
    add_skinned_box_limb(verts, norms, joints, weights, indices,
                         (0.0, 0.94 * sy, 0.0), (0.16 * sx, 0.11 * sy, 0.11 * sz), 0, 1, 2 * subdiv_scale, jitter)
    # Spine / Abdomen (Bone 1 -> 2)
    add_skinned_box_limb(verts, norms, joints, weights, indices,
                         (0.0, 1.16 * sy, 0.0), (0.15 * sx, 0.12 * sy, 0.11 * sz), 1, 2, 2 * subdiv_scale, jitter)
    # Chest / Torso (Bone 2 -> 3)
    add_skinned_box_limb(verts, norms, joints, weights, indices,
                         (0.0, 1.40 * sy, 0.0), (0.19 * sx, 0.14 * sy, 0.13 * sz), 2, 3, 3 * subdiv_scale, jitter)
    # Neck (Bone 3 -> 4)
    add_skinned_box_limb(verts, norms, joints, weights, indices,
                         (0.0, 1.58 * sy, 0.0), (0.06 * sx, 0.05 * sy, 0.06 * sz), 3, 4, 1 * subdiv_scale, jitter)
    # Head (Bone 4)
    add_skinned_box_limb(verts, norms, joints, weights, indices,
                         (0.0, 1.73 * sy, 0.0), (0.10 * sx, 0.12 * sy, 0.11 * sz), 4, 3, 3 * subdiv_scale, jitter)

    # Left Arm (Bones 5, 6, 7)
    add_skinned_box_limb(verts, norms, joints, weights, indices,
                         (-0.27 * sx, 1.38 * sy, 0.0), (0.06 * sx, 0.14 * sy, 0.06 * sz), 5, 6, 2 * subdiv_scale, jitter)
    add_skinned_box_limb(verts, norms, joints, weights, indices,
                         (-0.42 * sx, 1.22 * sy, 0.02 * sz), (0.05 * sx, 0.13 * sy, 0.05 * sz), 6, 7, 2 * subdiv_scale, jitter)
    add_skinned_box_limb(verts, norms, joints, weights, indices,
                         (-0.50 * sx, 1.08 * sy, 0.04 * sz), (0.04 * sx, 0.06 * sy, 0.03 * sz), 7, 6, 1 * subdiv_scale, jitter)

    # Right Arm (Bones 8, 9, 10)
    add_skinned_box_limb(verts, norms, joints, weights, indices,
                         (0.27 * sx, 1.38 * sy, 0.0), (0.06 * sx, 0.14 * sy, 0.06 * sz), 8, 9, 2 * subdiv_scale, jitter)
    add_skinned_box_limb(verts, norms, joints, weights, indices,
                         (0.42 * sx, 1.22 * sy, 0.02 * sz), (0.05 * sx, 0.13 * sy, 0.05 * sz), 9, 10, 2 * subdiv_scale, jitter)
    add_skinned_box_limb(verts, norms, joints, weights, indices,
                         (0.50 * sx, 1.08 * sy, 0.04 * sz), (0.04 * sx, 0.06 * sy, 0.03 * sz), 10, 9, 1 * subdiv_scale, jitter)

    # Left Leg (Bones 11, 12)
    add_skinned_box_limb(verts, norms, joints, weights, indices,
                         (-0.11 * sx, 0.65 * sy, 0.0), (0.08 * sx, 0.22 * sy, 0.08 * sz), 11, 12, 2 * subdiv_scale, jitter)
    add_skinned_box_limb(verts, norms, joints, weights, indices,
                         (-0.11 * sx, 0.22 * sy, 0.01 * sz), (0.065 * sx, 0.22 * sy, 0.075 * sz), 12, 11, 2 * subdiv_scale, jitter)

    # Right Leg (Bones 13, 14)
    add_skinned_box_limb(verts, norms, joints, weights, indices,
                         (0.11 * sx, 0.65 * sy, 0.0), (0.08 * sx, 0.22 * sy, 0.08 * sz), 13, 14, 2 * subdiv_scale, jitter)
    add_skinned_box_limb(verts, norms, joints, weights, indices,
                         (0.11 * sx, 0.22 * sy, 0.01 * sz), (0.065 * sx, 0.22 * sy, 0.075 * sz), 14, 13, 2 * subdiv_scale, jitter)

    # Archetype-specific gear geometry so each character silhouette & bounding box is unmistakably distinct
    gear_offset = (spec_idx % 5) * 0.015
    if "shield" in gear_feature:
        add_skinned_box_limb(verts, norms, joints, weights, indices,
                             (-0.34 * sx, 1.12 * sy, 0.26 * sz), (0.28 * sx, 0.48 * sy, 0.04 * sz), 6, 7, 2 * subdiv_scale, jitter)
    elif "backpack" in gear_feature or "pack" in gear_feature:
        add_skinned_box_limb(verts, norms, joints, weights, indices,
                             (0.0, 1.36 * sy, -0.19 * sz), (0.16 * sx, 0.20 * sy, 0.09 * sz), 2, 1, 2 * subdiv_scale, jitter)
    elif "ghillie" in gear_feature or "cape" in gear_feature or "mantle" in gear_feature:
        add_skinned_box_limb(verts, norms, joints, weights, indices,
                             (0.0, 1.24 * sy, -0.16 * sz), (0.26 * sx, 0.36 * sy, 0.08 * sz), 2, 4, 2 * subdiv_scale, jitter)
    elif "eod" in gear_feature:
        add_skinned_box_limb(verts, norms, joints, weights, indices,
                             (0.0, 1.54 * sy, 0.02 * sz), (0.28 * sx, 0.12 * sy, 0.20 * sz), 2, 4, 2 * subdiv_scale, jitter)
    else:
        add_skinned_box_limb(verts, norms, joints, weights, indices,
                             (0.0, (1.34 + gear_offset) * sy, 0.14 * sz), (0.14 * sx, 0.12 * sy, 0.04 * sz), 2, 1, 1 * subdiv_scale, jitter)

    return verts, norms, joints, weights, indices


def compute_world_bone_positions() -> List[Tuple[float, float, float]]:
    world_pos: List[Tuple[float, float, float]] = [(0.0, 0.0, 0.0)] * len(BONE_DEFS)
    for idx, name, parent, trans in BONE_DEFS:
        if parent is None:
            world_pos[idx] = (trans[0], trans[1], trans[2])
        else:
            px, py, pz = world_pos[parent]
            world_pos[idx] = (px + trans[0], py + trans[1], pz + trans[2])
    return world_pos


def pack_character_glb(
    filepath: str,
    char_id: str,
    spec_idx: int,
    sx: float,
    sy: float,
    sz: float,
    gear_feature: str,
    base_color: List[float],
) -> None:
    bin_chunks = bytearray()
    buffer_views = []
    accessors = []
    meshes = []

    def align4(buf: bytearray) -> None:
        while len(buf) % 4 != 0:
            buf.append(0)

    # 1. InverseBindMatrices for 15 bones (column-major 4x4 float32 matrices)
    world_positions = compute_world_bone_positions()
    ibm_offset = len(bin_chunks)
    for bx, by, bz in world_positions:
        # Column-major 4x4 translation matrix with (-bx, -by, -bz) in column 3
        mat = [
            1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.0,
            -bx, -by, -bz, 1.0,
        ]
        bin_chunks.extend(struct.pack("<16f", *mat))
    align4(bin_chunks)
    ibm_bv_idx = len(buffer_views)
    buffer_views.append({
        "buffer": 0,
        "byteOffset": ibm_offset,
        "byteLength": 15 * 64,
    })
    ibm_acc_idx = len(accessors)
    accessors.append({
        "bufferView": ibm_bv_idx,
        "byteOffset": 0,
        "componentType": 5126,  # FLOAT
        "count": 15,
        "type": "MAT4",
    })

    # 2. Build LOD0 (subdiv=3), LOD1 (subdiv=2), LOD2 (subdiv=1)
    for lod_tag, subdiv in (("LOD0", 3), ("LOD1", 2), ("LOD2", 1)):
        verts, norms, jnts, wgts, idxs = build_humanoid_lod_mesh(
            spec_idx, sx, sy, sz, gear_feature, subdiv
        )
        vcount = len(verts)
        icount = len(idxs)

        # POSITION
        pos_off = len(bin_chunks)
        min_v = [min(v[k] for v in verts) for k in range(3)]
        max_v = [max(v[k] for v in verts) for k in range(3)]
        for vx, vy, vz in verts:
            bin_chunks.extend(struct.pack("<3f", vx, vy, vz))
        align4(bin_chunks)
        pos_bv = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": pos_off, "byteLength": vcount * 12, "target": 34962})
        pos_acc = len(accessors)
        accessors.append({
            "bufferView": pos_bv,
            "byteOffset": 0,
            "componentType": 5126,
            "count": vcount,
            "type": "VEC3",
            "min": [round(x, 5) for x in min_v],
            "max": [round(x, 5) for x in max_v],
        })

        # NORMAL
        nrm_off = len(bin_chunks)
        for nx, ny, nz in norms:
            bin_chunks.extend(struct.pack("<3f", nx, ny, nz))
        align4(bin_chunks)
        nrm_bv = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": nrm_off, "byteLength": vcount * 12, "target": 34962})
        nrm_acc = len(accessors)
        accessors.append({
            "bufferView": nrm_bv,
            "byteOffset": 0,
            "componentType": 5126,
            "count": vcount,
            "type": "VEC3",
        })

        # JOINTS_0 (UNSIGNED_BYTE VEC4)
        jnt_off = len(bin_chunks)
        for j0, j1, j2, j3 in jnts:
            bin_chunks.extend(struct.pack("<4B", j0, j1, j2, j3))
        align4(bin_chunks)
        jnt_bv = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": jnt_off, "byteLength": vcount * 4, "target": 34962})
        jnt_acc = len(accessors)
        accessors.append({
            "bufferView": jnt_bv,
            "byteOffset": 0,
            "componentType": 5121,  # UNSIGNED_BYTE
            "count": vcount,
            "type": "VEC4",
        })

        # WEIGHTS_0 (FLOAT VEC4)
        wgt_off = len(bin_chunks)
        for w0, w1, w2, w3 in wgts:
            bin_chunks.extend(struct.pack("<4f", w0, w1, w2, w3))
        align4(bin_chunks)
        wgt_bv = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": wgt_off, "byteLength": vcount * 16, "target": 34962})
        wgt_acc = len(accessors)
        accessors.append({
            "bufferView": wgt_bv,
            "byteOffset": 0,
            "componentType": 5126,  # FLOAT
            "count": vcount,
            "type": "VEC4",
        })

        # INDICES (UNSIGNED_SHORT SCALAR)
        idx_off = len(bin_chunks)
        for i_val in idxs:
            bin_chunks.extend(struct.pack("<H", i_val))
        align4(bin_chunks)
        idx_bv = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": idx_off, "byteLength": icount * 2, "target": 34963})
        idx_acc = len(accessors)
        accessors.append({
            "bufferView": idx_bv,
            "byteOffset": 0,
            "componentType": 5123,  # UNSIGNED_SHORT
            "count": icount,
            "type": "SCALAR",
        })

        meshes.append({
            "name": f"{char_id}_{lod_tag}",
            "primitives": [{
                "attributes": {
                    "POSITION": pos_acc,
                    "NORMAL": nrm_acc,
                    "JOINTS_0": jnt_acc,
                    "WEIGHTS_0": wgt_acc,
                },
                "indices": idx_acc,
                "material": 0,
                "mode": 4,
            }],
        })

    # Construct Nodes:
    # Nodes 0..14: 15 bones
    # Nodes 15, 16, 17: LOD0, LOD1, LOD2 skinned mesh nodes
    # Node 18: Character Root
    nodes = []
    children_map: Dict[int, List[int]] = {i: [] for i in range(15)}
    for idx, name, parent, _ in BONE_DEFS:
        if parent is not None:
            children_map[parent].append(idx)

    for idx, name, parent, trans in BONE_DEFS:
        node_dict: Dict[str, Any] = {
            "name": name,
            "translation": trans,
            "rotation": [0.0, 0.0, 0.0, 1.0],
            "scale": [1.0, 1.0, 1.0],
        }
        if children_map[idx]:
            node_dict["children"] = children_map[idx]
        nodes.append(node_dict)

    # Skinned mesh nodes 15, 16, 17
    for m_idx, lod_tag in enumerate(("LOD0", "LOD1", "LOD2")):
        nodes.append({
            "name": f"{char_id}_{lod_tag}_Node",
            "mesh": m_idx,
            "skin": 0,
        })

    # Root node 18
    nodes.append({
        "name": char_id,
        "children": [0, 15, 16, 17],
        "extras": {
            "archetype": char_id,
            "gear_feature": gear_feature,
            "skeleton_bones": 15,
        },
    })

    gltf_dict = {
        "asset": {
            "version": "2.0",
            "generator": "Project Real Loser Procedural 15-Bone Character Builder v3",
        },
        "scene": 0,
        "scenes": [{"name": "CharacterScene", "nodes": [18]}],
        "nodes": nodes,
        "skins": [{
            "name": f"{char_id}_Humanoid15Rig",
            "skeleton": 0,
            "joints": list(range(15)),
            "inverseBindMatrices": ibm_acc_idx,
        }],
        "meshes": meshes,
        "materials": [{
            "name": f"{char_id}_URP_Lit",
            "pbrMetallicRoughness": {
                "baseColorFactor": base_color,
                "metallicFactor": 0.15,
                "roughnessFactor": 0.78,
            },
        }],
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(bin_chunks)}],
    }

    json_str = json.dumps(gltf_dict, separators=(",", ":"))
    json_bytes = json_str.encode("utf-8")
    while len(json_bytes) % 4 != 0:
        json_bytes += b" "

    total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_chunks)
    with open(filepath, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total_len))
        f.write(struct.pack("<II", len(json_bytes), 0x4E4F534A))
        f.write(json_bytes)
        f.write(struct.pack("<II", len(bin_chunks), 0x004E4942))
        f.write(bin_chunks)


def build_all_characters(out_dir: str = "Assets/_Project/Art/Characters") -> int:
    os.makedirs(out_dir, exist_ok=True)
    for idx, (char_id, sx, sy, sz, gear, color) in enumerate(CHARACTER_SPECS):
        out_path = os.path.join(out_dir, f"{char_id}.glb")
        pack_character_glb(out_path, char_id, idx, sx, sy, sz, gear, color)
    print(f"[BUILD SUCCESS] Generated {len(CHARACTER_SPECS)} 15-bone rigged character .glb files in '{out_dir}'.")
    return 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "Assets/_Project/Art/Characters"
    sys.exit(build_all_characters(target))
