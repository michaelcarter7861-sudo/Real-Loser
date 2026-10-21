#!/usr/bin/env python3
"""
Project Real Loser — Procedural Traps (T1–T16) & Modular Compound Architecture .GLB Builder
Target Engine: Unity 2022.3.40f1 LTS (URP, Android ARM64 IL2CPP)

Generates:
- 16 Traps (`T1`–`T16`) in `Assets/_Project/Art/Traps/`
- 14 Modular Compound Architecture & Interactive Prop `.glb` assets in `Assets/_Project/Art/Environment/`:
  - `env_fence_chainlink_4m.glb`
  - `env_wall_concrete_4m.glb`
  - `env_wall_brick_4m.glb`
  - `env_wall_adobe_4m.glb`
  - `env_gate_sliding_6m.glb`
  - `env_corner_post_a.glb`
  - `env_watchtower_metal_a.glb`
  - `env_bldg_guardhouse_a.glb`
  - `env_bldg_barracks_a.glb`
  - `env_bldg_comms_bunker_a.glb`
  - `prop_breaker_box_a.glb`
  - `prop_generator_diesel_a.glb`
  - `prop_locker_metal_a.glb`
  - `prop_dumpster_metal_a.glb`
"""

import os
import sys
import json
import struct
from typing import List, Tuple, Dict, Any

TRAP_SPECS = [
    ("trap_t1_tripwire_alarm",      (0.60, 0.18, 0.08), [0.65, 0.22, 0.16, 1.0]),
    ("trap_t2_tripwire_grenade",    (0.62, 0.22, 0.10), [0.28, 0.38, 0.22, 1.0]),
    ("trap_t3_directional_mine",    (0.24, 0.16, 0.07), [0.26, 0.34, 0.24, 1.0]),
    ("trap_t4_buried_mine",         (0.28, 0.08, 0.28), [0.34, 0.30, 0.22, 1.0]),
    ("trap_t5_laser_grid",          (0.16, 1.80, 0.12), [0.85, 0.12, 0.15, 1.0]),
    ("trap_t6_motion_sensor",       (0.20, 0.26, 0.15), [0.82, 0.84, 0.86, 1.0]),
    ("trap_t7_pressure_plate",      (0.85, 0.04, 0.85), [0.42, 0.40, 0.38, 1.0]),
    ("trap_t8_noise_trap",          (0.75, 0.14, 0.75), [0.58, 0.52, 0.44, 1.0]),
    ("trap_t9_sentry_turret",       (0.90, 1.35, 0.90), [0.22, 0.24, 0.26, 1.0]),
    ("trap_t10_searchlight_tower",  (0.70, 1.65, 0.70), [0.75, 0.78, 0.65, 1.0]),
    ("trap_t11_security_camera",    (0.22, 0.24, 0.42), [0.78, 0.80, 0.82, 1.0]),
    ("trap_t12_electric_fence",     (4.00, 2.80, 0.18), [0.30, 0.42, 0.58, 1.0]),
    ("trap_t13_alarmed_door",       (1.10, 2.20, 0.14), [0.52, 0.20, 0.18, 1.0]),
    ("trap_t14_booby_trapped_door", (1.12, 2.20, 0.16), [0.46, 0.34, 0.22, 1.0]),
    ("trap_t15_dog_patrol_hazard",  (0.45, 0.72, 1.05), [0.38, 0.28, 0.18, 1.0]),
    ("trap_t16_env_hazard",         (1.60, 0.35, 1.60), [0.64, 0.76, 0.84, 1.0]),
]

ENV_ARCH_SPECS = [
    ("env_fence_chainlink_4m",  (4.00, 2.80, 0.12), [0.52, 0.55, 0.58, 1.0]),
    ("env_wall_concrete_4m",    (4.00, 3.20, 0.35), [0.62, 0.63, 0.61, 1.0]),
    ("env_wall_brick_4m",       (4.00, 3.00, 0.32), [0.58, 0.28, 0.22, 1.0]),
    ("env_wall_adobe_4m",       (4.00, 2.90, 0.40), [0.72, 0.58, 0.42, 1.0]),
    ("env_gate_sliding_6m",     (6.00, 3.00, 0.22), [0.32, 0.35, 0.38, 1.0]),
    ("env_corner_post_a",       (0.42, 3.30, 0.42), [0.48, 0.50, 0.52, 1.0]),
    ("env_watchtower_metal_a",  (3.60, 8.50, 3.60), [0.34, 0.36, 0.38, 1.0]),
    ("env_bldg_guardhouse_a",   (6.00, 3.80, 6.00), [0.56, 0.54, 0.50, 1.0]),
    ("env_bldg_barracks_a",     (14.0, 4.20, 8.00), [0.52, 0.50, 0.46, 1.0]),
    ("env_bldg_comms_bunker_a", (10.0, 4.50, 10.0), [0.44, 0.46, 0.45, 1.0]),
    ("prop_breaker_box_a",      (0.55, 0.85, 0.28), [0.36, 0.44, 0.38, 1.0]),
    ("prop_generator_diesel_a", (1.80, 1.45, 1.10), [0.68, 0.52, 0.16, 1.0]),
    ("prop_locker_metal_a",     (0.90, 2.05, 0.65), [0.38, 0.42, 0.44, 1.0]),
    ("prop_dumpster_metal_a",   (2.10, 1.35, 1.40), [0.22, 0.38, 0.26, 1.0]),
]


def pack_static_asset_glb(
    filepath: str,
    asset_id: str,
    dims: Tuple[float, float, float],
    color: List[float],
    seed_idx: int,
) -> None:
    hx, hy, hz = dims[0] * 0.5, dims[1] * 0.5, dims[2] * 0.5
    cy = hy  # Pivot at ground level y=0

    # Two-tier architectural mesh (base structure + detail housing)
    verts = [
        (-hx, 0.0, -hz), (hx, 0.0, -hz), (hx, dims[1], -hz), (-hx, dims[1], -hz),
        (-hx, 0.0,  hz), (hx, 0.0,  hz), (hx, dims[1],  hz), (-hx, dims[1],  hz),
        (-hx * 0.75, dims[1], -hz * 0.75), (hx * 0.75, dims[1], -hz * 0.75),
        (hx * 0.75, dims[1] + 0.08 + seed_idx * 0.004, hz * 0.75),
        (-hx * 0.75, dims[1] + 0.08 + seed_idx * 0.004, hz * 0.75),
    ]
    norms = [
        (0.0, 0.0, -1.0), (0.0, 0.0, -1.0), (0.0, 0.0, -1.0), (0.0, 0.0, -1.0),
        (0.0, 0.0,  1.0), (0.0, 0.0,  1.0), (0.0, 0.0,  1.0), (0.0, 0.0,  1.0),
        (0.0, 1.0,  0.0), (0.0, 1.0,  0.0), (0.0, 1.0,  0.0), (0.0, 1.0,  0.0),
    ]
    indices = [
        0, 2, 1, 0, 3, 2,
        4, 5, 6, 4, 6, 7,
        0, 1, 5, 0, 5, 4,
        1, 2, 6, 1, 6, 5,
        2, 3, 7, 2, 7, 6,
        3, 0, 4, 3, 4, 7,
        8, 9, 10, 8, 10, 11,
    ]

    bin_chunks = bytearray()
    for vx, vy, vz in verts:
        bin_chunks.extend(struct.pack("<3f", vx, vy, vz))
    for nx, ny, nz in norms:
        bin_chunks.extend(struct.pack("<3f", nx, ny, nz))
    for iv in indices:
        bin_chunks.extend(struct.pack("<H", iv))
    while len(bin_chunks) % 4 != 0:
        bin_chunks.append(0)

    vcnt = len(verts)
    icnt = len(indices)
    min_v = [min(v[k] for v in verts) for k in range(3)]
    max_v = [max(v[k] for v in verts) for k in range(3)]

    gltf_dict = {
        "asset": {"version": "2.0", "generator": "Project Real Loser Trap & Architecture Builder v3"},
        "scene": 0,
        "scenes": [{"name": "AssetScene", "nodes": [0]}],
        "nodes": [{
            "name": asset_id,
            "mesh": 0,
            "translation": [0.0, 0.0, 0.0],
            "rotation": [0.0, 0.0, 0.0, 1.0],
            "scale": [1.0, 1.0, 1.0],
            "extras": {"asset_id": asset_id, "dimensions": list(dims)},
        }],
        "meshes": [{
            "name": f"{asset_id}_Mesh",
            "primitives": [{
                "attributes": {"POSITION": 0, "NORMAL": 1},
                "indices": 2,
                "material": 0,
                "mode": 4,
            }],
        }],
        "materials": [{
            "name": f"{asset_id}_URP_Mat",
            "pbrMetallicRoughness": {
                "baseColorFactor": color,
                "metallicFactor": 0.35,
                "roughnessFactor": 0.65,
            },
        }],
        "accessors": [
            {
                "bufferView": 0,
                "byteOffset": 0,
                "componentType": 5126,
                "count": vcnt,
                "type": "VEC3",
                "min": [round(x, 5) for x in min_v],
                "max": [round(x, 5) for x in max_v],
            },
            {
                "bufferView": 1,
                "byteOffset": 0,
                "componentType": 5126,
                "count": vcnt,
                "type": "VEC3",
            },
            {
                "bufferView": 2,
                "byteOffset": 0,
                "componentType": 5123,
                "count": icnt,
                "type": "SCALAR",
            },
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": vcnt * 12, "target": 34962},
            {"buffer": 0, "byteOffset": vcnt * 12, "byteLength": vcnt * 12, "target": 34962},
            {"buffer": 0, "byteOffset": vcnt * 24, "byteLength": icnt * 2, "target": 34963},
        ],
        "buffers": [{"byteLength": len(bin_chunks)}],
    }

    json_bytes = json.dumps(gltf_dict, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4 != 0:
        json_bytes += b" "

    total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_chunks)
    with open(filepath, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total_len))
        f.write(struct.pack("<II", len(json_bytes), 0x4E4F534A))
        f.write(json_bytes)
        f.write(struct.pack("<II", len(bin_chunks), 0x004E4942))
        f.write(bin_chunks)


def build_all_traps_and_env(
    trap_dir: str = "Assets/_Project/Art/Traps",
    env_dir: str = "Assets/_Project/Art/Environment",
) -> int:
    os.makedirs(trap_dir, exist_ok=True)
    os.makedirs(env_dir, exist_ok=True)

    for idx, (tid, dims, col) in enumerate(TRAP_SPECS):
        pack_static_asset_glb(os.path.join(trap_dir, f"{tid}.glb"), tid, dims, col, idx + 1)

    for idx, (eid, dims, col) in enumerate(ENV_ARCH_SPECS):
        pack_static_asset_glb(os.path.join(env_dir, f"{eid}.glb"), eid, dims, col, idx + 50)

    print(
        f"[BUILD SUCCESS] Generated {len(TRAP_SPECS)} Trap .glb files in '{trap_dir}' "
        f"and {len(ENV_ARCH_SPECS)} Compound Architecture .glb files in '{env_dir}'."
    )
    return 0


if __name__ == "__main__":
    sys.exit(build_all_traps_and_env())
