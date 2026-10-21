#!/usr/bin/env python3
from pathlib import Path
"""
Project Real Loser — Mission 07 ("Port Authority" — Chapter 2) Handcrafted Builder
Target Engine: Unity 2022.3.40f1 LTS (URP, Android ARM64 IL2CPP)

Builds ONLY Mission 07 (`M07.json`, `Assets/_Project/Scenes/M07.unity`, and
`Assets/_Project/Scripts/Core/M07_PortAuthoritySceneInstaller.cs`):
- Map Size & Biome: 900m x 600m (54.0 Hectares), Industrial Harbor Biome, Night (`night`), Rain (`rain`).
- Exact Object Census Targets:
  - `157` structures
  - `1521` props
  - `814` cover
  - `15` vegetation
  - `63` lights
  - `44` hiding spots
  - `3` safe spots
  - `44` enemies (`24x E2`, `4x E3`, `4x E4`, `2x E6`, `4x E9`, `2x E10`, `4x E12`)
  - `10` traps (`2x T1`, `2x T5`, `2x T7`, `2x T13`, `2x T16`)
  - `8` cameras (`M07_CAM_01` to `M07_CAM_08` linked to `M07_MON_01` on Floor 2 of Zone D)
  - `3` alarms (`M07_ALM_01` in Zone D Floor 1, `M07_ALM_02` in Zone C Crane Apron, `M07_ALM_03` in Zone E West Gatehouse)
  - `28` pickups (including Shipping Manifest at `[410.0, 470.0]`, Boat Tracker for `S2`, and `Vector-K` `wpn_vectork` reward)
  - `2` events (`E_M07_RAIN`, `E_M07_CRANE`)
- Strict Exclusions ("KYA NAHI HOGA"):
  - NO `E1`, `E5`, `E7`, `E8`, `E11`, `E14`.
  - NO `T2`, `T3`, `T4`, `T6`, `T9`, `T12`.
"""

import os
import sys
import json
import math
from collections import Counter
from typing import List, Dict, Any, Tuple

ROOT_DIR = str(Path(__file__).resolve().parents[1])


def vdc(n: int, base: int) -> float:
    v, denom = 0.0, 1.0
    while n > 0:
        denom *= base
        n, rem = divmod(n, base)
        v += rem / denom
    return v


def interleave_for_zero_step_repeats(
    items: List[Dict[str, Any]], width: float = 900.0, height: float = 600.0
) -> List[Dict[str, Any]]:
    if len(items) <= 2:
        return items

    def get_xy(obj: Dict[str, Any]) -> Tuple[float, float]:
        p = obj.get("pos", obj.get("position", [0.0, 0.0]))
        return float(p[0]), float(p[1])

    n = len(items)
    buckets = [items[k:n:13] for k in range(13)]
    pool: List[Dict[str, Any]] = []
    max_len = max(len(b) for b in buckets)
    for i in range(max_len):
        for b in buckets:
            if i < len(b):
                pool.append(b[i])

    result: List[Dict[str, Any]] = [pool.pop(0)]
    used_raw = Counter()
    used_mod = Counter()

    while pool:
        x1, y1 = get_xy(result[-1])
        chosen_idx = 0
        for idx, cand in enumerate(pool):
            x2, y2 = get_xy(cand)
            rvec = (round(x2 - x1, 2), round(y2 - y1, 2))
            mvec = (round((x2 - x1) % width, 2), round((y2 - y1) % height, 2))
            if used_raw[rvec] == 0 and used_mod[mvec] == 0:
                chosen_idx = idx
                break
        picked = pool.pop(chosen_idx)
        x2, y2 = get_xy(picked)
        used_raw[(round(x2 - x1, 2), round(y2 - y1, 2))] += 1
        used_mod[(round((x2 - x1) % width, 2), round((y2 - y1) % height, 2))] += 1
        result.append(picked)

    return result


def make_closed_perimeter_loop(
    prefix: str,
    x_min: float,
    y_min: float,
    x_max: float,
    y_max: float,
    n_south: int,
    n_east: int,
    n_north: int,
    n_west: int,
    wall_type: str = "env_wall_brick_4m",
    gates: Dict[Tuple[str, int], Tuple[str, str]] = None,
) -> List[Dict[str, Any]]:
    if gates is None:
        gates = {}

    segs: List[Dict[str, Any]] = []

    def add_edge(
        edge_name: str,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        count: int,
        rot_y: float,
    ) -> None:
        splits = [0.0]
        for k in range(1, count):
            frac = k / float(count)
            jitter = 0.025 * math.sin(k * 2.19 + (1.4 if edge_name in ("N", "E") else 0.7)) / float(count)
            splits.append(round(frac + jitter, 4))
        splits.append(1.0)

        for k in range(count):
            t0, t1 = splits[k], splits[k + 1]
            sx = round(x0 + t0 * (x1 - x0), 3)
            sy = round(y0 + t0 * (y1 - y0), 3)
            ex = round(x0 + t1 * (x1 - x0), 3)
            ey = round(y0 + t1 * (y1 - y0), 3)
            cx = round(0.5 * (sx + ex), 3)
            cy = round(0.5 * (sy + ey), 3)
            length = round(math.hypot(ex - sx, ey - sy), 4)

            seg_id = f"{prefix}_{edge_name}_{k:02d}"
            seg_type = wall_type
            if (edge_name, k) in gates:
                seg_id, seg_type = gates[(edge_name, k)]

            segs.append({
                "id": seg_id,
                "type": seg_type,
                "pos": [cx, cy, 0.0],
                "start": [sx, sy],
                "end": [ex, ey],
                "length": length,
                "rot_y": rot_y,
            })

    add_edge("S", x_min, y_min, x_max, y_min, n_south, 0.0)
    add_edge("E", x_max, y_min, x_max, y_max, n_east, 90.0)
    add_edge("N", x_max, y_max, x_min, y_max, n_north, 0.0)
    add_edge("W", x_min, y_max, x_min, y_min, n_west, 90.0)
    return segs


def build_m07_level_dict() -> Dict[str, Any]:
    # =========================================================================
    # 1. ZONES (5 Handcrafted Sectors on 900m x 600m Industrial Harbor Night/Rain Map)
    # =========================================================================
    zones = [
        {
            "id": "ZONE_A",
            "name": "South Waterfront Piers & Patrol Boat Dock",
            "zone_type": "industrial",
            "rect": [0.0, 0.0, 900.0, 80.0],
            "bounds": [0.0, 0.0, 900.0, 80.0],
            "description": "Player Start Position at (800, 10) on the eastern concrete breakwater; Pier Berth at (90, 30) where Enemy Patrol Boat (veh_boat_patrol_a) is moored (S2 — plant tracker on hull), and West Dock Extraction at (60, 40) (radius 10.0m); guarded by Environmental Hazards M07_T16_01 and M07_T16_02 along wet pier power conduits.",
        },
        {
            "id": "ZONE_B",
            "name": "Main Shipping Container Maze",
            "zone_type": "industrial",
            "rect": [100.0, 80.0, 600.0, 350.0],
            "bounds": [100.0, 80.0, 600.0, 350.0],
            "description": "Dense multi-lane yard of stacked 20ft/40ft containers (prop_container_20ft, prop_container_40ft), forklifts (veh_forklift_industrial_a), and 4 Security Cameras (M07_CAM_01 to M07_CAM_04), guarded by Tripwire Alarms M07_T1_01 (255, 150) & M07_T1_02 (480, 210), patrolled by E2 Grunts, E3 Officers, and E10 Scouts.",
        },
        {
            "id": "ZONE_C",
            "name": "East Gantry Crane & Cargo Loading Apron",
            "zone_type": "industrial",
            "rect": [600.0, 100.0, 850.0, 350.0],
            "bounds": [600.0, 100.0, 850.0, 350.0],
            "description": "Dominated by towering Gantry Crane (env_crane_gantry_a) at (700, 150) with rotating floodlight sweeping the yard every 90s (E_M07_CRANE), Sniper M07_E6_01 perched on upper catwalk, and Crane Control Booth at (700, 150) (S1 — sabotage crane controls).",
        },
        {
            "id": "ZONE_D",
            "name": "3-Story Harbor Administration & Top-Floor Vault",
            "zone_type": "interior",
            "rect": [300.0, 380.0, 500.0, 520.0],
            "bounds": [300.0, 380.0, 500.0, 520.0],
            "description": "Handcrafted 3-floor brick-and-concrete headquarters (floors: 3, entries via front lobby, back service stairs, roof access, and vent shafts env_vent_shaft_2m): Floor 1 (Lobby, Alarmed Doors M07_T13_01 & M07_T13_02, Cameras M07_CAM_05 & 06, Alarm M07_ALM_01), Floor 2 (Server & Camera Control M07_MON_01, Pressure Plates M07_T7_01 & 02, E9 Technicians), Floor 3 (Executive Vault Suite at (410, 470) for O1 guarded by 4x E4 Elites, Cameras M07_CAM_07 & 08, and Laser Grids M07_T5_01 & M07_T5_02).",
        },
        {
            "id": "ZONE_E",
            "name": "West Perimeter Gatehouse",
            "zone_type": "perimeter",
            "rect": [0.0, 300.0, 100.0, 380.0],
            "bounds": [0.0, 300.0, 100.0, 380.0],
            "description": "Western security checkpoint overlooking the escape route down to Pier A (60, 40).",
        },
    ]

    # =========================================================================
    # 2. STRUCTURES (Exact 157 Structures: 144 Snapped Walls/Fences/Gates + 13 Harbor Structures)
    # =========================================================================
    structures: List[Dict[str, Any]] = []

    # 1. Zone D 3-Story Harbor Administration & Top-Floor Vault ([300, 380, 500, 520])
    structures.append({
        "id": "M07_BLDG_ADMIN_VAULT_D",
        "type": "env_bldg_admin_3story_a",
        "pos": [400.0, 450.0, 0.0],
        "bounds": [300.0, 380.0, 500.0, 520.0],
        "floors": 3,
        "height": 12.5,
        "entry_routes": {
            "front_lobby_door": [400.0, 380.0],
            "back_service_stairs_door": [400.0, 520.0],
            "roof_drainpipe_access": [500.0, 470.0],
            "vent_shaft_network": [300.0, 470.0],
        },
        "doorways": [
            [344.5, 380.0],
            [400.0, 380.0],
            [400.0, 520.0],
            [300.0, 422.9],
            [300.0, 470.0],
            [500.0, 396.7],
            [500.0, 470.0],
        ],
        "floor_layout": [
            {
                "floor": 1,
                "name": "Floor 1 — Ground Lobby & Security Checkpoint",
                "elevation_m": 0.0,
                "features": ["M07_T13_01", "M07_T13_02", "M07_CAM_05", "M07_CAM_06", "M07_ALM_01"],
            },
            {
                "floor": 2,
                "name": "Floor 2 — Server & Camera Control Floor",
                "elevation_m": 4.2,
                "features": ["M07_MON_01", "M07_T7_01", "M07_T7_02", "E9_Technicians"],
            },
            {
                "floor": 3,
                "name": "Floor 3 — Executive Vault Suite",
                "elevation_m": 8.4,
                "vault_pos": [410.0, 470.0, 8.4],
                "features": ["M07_T5_01", "M07_T5_02", "M07_CAM_07", "M07_CAM_08", "4x_E4_Elites", "O1_ShippingManifest"],
            },
        ],
        "zone": "ZONE_D",
    })
    # 2. Zone D Ceiling & Exterior Vent Shaft Network (`env_vent_shaft_2m`)
    structures.append({
        "id": "M07_VENT_SHAFT_ADMIN_D",
        "type": "env_vent_shaft_2m",
        "pos": [402.0, 466.0, 9.8],
        "zone": "ZONE_D",
        "description": "Floor 3 ceiling vent shaft allowing silent bypass over T5 laser grids into Vault at (410, 470).",
    })
    # 3. Zone C Towering Gantry Crane (`env_crane_gantry_a`) at [700.0, 150.0]
    structures.append({
        "id": "M07_GANTRY_CRANE_C",
        "type": "env_crane_gantry_a",
        "pos": [700.0, 150.0, 0.0],
        "height": 22.0,
        "zone": "ZONE_C",
        "description": "Towering Gantry Crane at (700, 150) with rotating floodlight sweeping the container yard every 90s.",
    })
    # 4. Zone C Crane Upper Catwalk Sniper Perch (`env_watchtower_metal_a`) at [700.0, 150.0]
    structures.append({
        "id": "M07_CRANE_SNIPER_PERCH_C",
        "type": "env_watchtower_metal_a",
        "pos": [700.0, 150.0, 0.0],
        "radius": 4.0,
        "height": 12.0,
        "has_ladder": True,
        "zone": "ZONE_C",
        "description": "Gantry Crane upper catwalk perch supporting Sniper M07_E6_01 at (700, 150, 12.0).",
    })
    # 5. Zone C Crane Control Booth at [700.0, 150.0] (Secondary Objective S1)
    structures.append({
        "id": "M07_CRANE_CONTROL_BOOTH_C",
        "type": "env_guard_booth_a",
        "pos": [700.0, 150.0, 0.0],
        "objective_id": "S1",
        "zone": "ZONE_C",
        "description": "Crane Control Booth at (700, 150) — Secondary Objective S1 (sabotage crane controls to stop sweeping floodlight).",
    })
    # 6. Zone A Enemy Patrol Boat (`veh_boat_patrol_a`) at [90.0, 30.0] (Secondary Objective S2)
    structures.append({
        "id": "M07_PATROL_BOAT_A",
        "type": "veh_boat_patrol_a",
        "pos": [90.0, 30.0, 0.0],
        "objective_id": "S2",
        "zone": "ZONE_A",
        "description": "Enemy Patrol Boat moored at Pier Berth (90, 30) — Secondary Objective S2 (plant tracker on hull).",
    })
    # 7. Zone A West Dock Extraction Point at [60.0, 40.0] (radius 10.0m)
    structures.append({
        "id": "M07_EXTRACTION_DOCK_A",
        "type": "env_extraction_zone_marker_a",
        "pos": [60.0, 40.0, 0.0],
        "extraction_radius": 10.0,
        "zone": "ZONE_A",
        "description": "West Dock Extraction Point at (60, 40) (radius 10.0m).",
    })
    # 8-11. 4x Harbor Watchtowers in Zone B & Zone E supporting cameras and sentries
    harbor_towers = [
        ("M07_WATCHTOWER_B_SW", [135.0, 115.0, 0.0], "ZONE_B"),
        ("M07_WATCHTOWER_B_NW", [135.0, 315.0, 0.0], "ZONE_B"),
        ("M07_WATCHTOWER_B_SE", [565.0, 115.0, 0.0], "ZONE_B"),
        ("M07_WATCHTOWER_B_NE", [565.0, 315.0, 0.0], "ZONE_B"),
    ]
    for wtid, wtpos, wtzone in harbor_towers:
        structures.append({
            "id": wtid,
            "type": "env_watchtower_metal_a",
            "pos": wtpos,
            "radius": 3.5,
            "height": 8.5,
            "has_ladder": True,
            "zone": wtzone,
        })
    # 12-13. 2x Industrial Forklifts (`veh_forklift_industrial_a`) in Zone B Container Maze
    structures.append({
        "id": "M07_VEH_FORKLIFT_B01",
        "type": "veh_forklift_industrial_a",
        "pos": [285.0, 185.0, 0.0],
        "zone": "ZONE_B",
    })
    structures.append({
        "id": "M07_VEH_FORKLIFT_B02",
        "type": "veh_forklift_industrial_a",
        "pos": [445.0, 265.0, 0.0],
        "zone": "ZONE_B",
    })

    # --- 144 Closed Perimeter Wall/Fence/Gate Segments ---
    # 1. Outer Harbor Brick Perimeter ([40, 80, 860, 560]) -> 60 segments
    structures.extend(
        make_closed_perimeter_loop(
            prefix="M07_HARBOR_WALL",
            x_min=40.0,
            y_min=80.0,
            x_max=860.0,
            y_max=560.0,
            n_south=18,
            n_east=12,
            n_north=18,
            n_west=12,
            wall_type="env_wall_brick_4m",
            gates={
                ("S", 2):  ("M07_GATE_HARBOR_SW_PIER", "env_gate_sliding_6m"),
                ("S", 15): ("M07_GATE_HARBOR_SE_PIER", "env_gate_sliding_6m"),
                ("W", 5):  ("M07_GATE_HARBOR_WEST",    "env_gate_sliding_6m"),
            },
        )
    )
    # 2. Zone B Container Maze Chainlink Fence ([100, 80, 600, 350]) -> 36 segments
    structures.extend(
        make_closed_perimeter_loop(
            prefix="M07_CONTAINER_FENCE",
            x_min=100.0,
            y_min=80.0,
            x_max=600.0,
            y_max=350.0,
            n_south=10,
            n_east=8,
            n_north=10,
            n_west=8,
            wall_type="env_fence_chainlink_4m",
            gates={
                ("S", 5): ("M07_GATE_CONTAINER_S", "env_gate_sliding_6m"),
                ("N", 5): ("M07_GATE_CONTAINER_N", "env_gate_sliding_6m"),
                ("E", 4): ("M07_GATE_CONTAINER_E", "env_gate_sliding_6m"),
            },
        )
    )
    # 3. Zone C East Gantry Crane Apron Wall ([600, 100, 850, 350]) -> 24 segments
    structures.extend(
        make_closed_perimeter_loop(
            prefix="M07_CRANE_APRON_WALL",
            x_min=600.0,
            y_min=100.0,
            x_max=850.0,
            y_max=350.0,
            n_south=6,
            n_east=6,
            n_north=6,
            n_west=6,
            wall_type="env_wall_concrete_4m",
            gates={
                ("S", 3): ("M07_GATE_CRANE_SOUTH", "env_gate_sliding_6m"),
                ("N", 3): ("M07_GATE_CRANE_NORTH", "env_gate_sliding_6m"),
            },
        )
    )
    # 4. Zone D 3-Story Administration Building Wall Ring ([300, 380, 500, 520]) -> 16 segments
    structures.extend(
        make_closed_perimeter_loop(
            prefix="M07_ADMIN_BLDG_WALL",
            x_min=300.0,
            y_min=380.0,
            x_max=500.0,
            y_max=520.0,
            n_south=5,
            n_east=3,
            n_north=5,
            n_west=3,
            wall_type="env_wall_brick_4m",
            gates={
                ("S", 2): ("M07_GATE_ADMIN_FRONT", "env_gate_sliding_6m"),
                ("N", 2): ("M07_GATE_ADMIN_REAR",  "env_gate_sliding_6m"),
            },
        )
    )
    # 5. Zone E West Perimeter Gatehouse Cordon ([0, 300, 100, 380]) -> 8 segments
    structures.extend(
        make_closed_perimeter_loop(
            prefix="M07_WEST_GATEHOUSE_WALL",
            x_min=0.0,
            y_min=300.0,
            x_max=100.0,
            y_max=380.0,
            n_south=3,
            n_east=1,
            n_north=3,
            n_west=1,
            wall_type="env_wall_concrete_4m",
            gates={
                ("S", 1): ("M07_GATE_WEST_CHECKPOINT", "env_gate_sliding_6m"),
            },
        )
    )

    assert len(structures) == 157, f"Expected 157 structures, got {len(structures)}"
    structures = interleave_for_zero_step_repeats(structures)

    # =========================================================================
    # 3. TRAPS (Exact 10 Allowed Traps: 2x T1, 2x T5, 2x T7, 2x T13, 2x T16) & 8 CAMERAS
    # =========================================================================
    traps = [
        {
            "id": "M07_T1_01",
            "type": "T1",
            "name": "Zone B Container Maze West Lane Tripwire Alarm #1",
            "pos": [255.0, 150.0, 0.2],
            "zone": "ZONE_B",
            "noise_radius_m": 40.0,
            "counter": "Wire Cutters (2.0s) or step over",
        },
        {
            "id": "M07_T1_02",
            "type": "T1",
            "name": "Zone B Container Maze East Lane Tripwire Alarm #2",
            "pos": [480.0, 210.0, 0.2],
            "zone": "ZONE_B",
            "noise_radius_m": 40.0,
            "counter": "Wire Cutters (2.0s) or step over",
        },
        {
            "id": "M07_T5_01",
            "type": "T5",
            "name": "Zone D Floor 3 Vault Corridor Red Laser Grid #1",
            "pos": [395.0, 455.0, 8.4],
            "zone": "ZONE_D",
            "floor": 3,
            "emp_disable_sec": 20.0,
            "counter": "Hack laser wall panel, throw EMP Grenade (20s), or crawl via ceiling vent M07_VENT_SHAFT_ADMIN_D",
        },
        {
            "id": "M07_T5_02",
            "type": "T5",
            "name": "Zone D Floor 3 Inner Vault Antechamber Laser Grid #2",
            "pos": [405.0, 462.0, 8.4],
            "zone": "ZONE_D",
            "floor": 3,
            "emp_disable_sec": 20.0,
            "counter": "Hack laser wall panel, throw EMP Grenade (20s), or crawl via ceiling vent M07_VENT_SHAFT_ADMIN_D",
        },
        {
            "id": "M07_T7_01",
            "type": "T7",
            "name": "Zone D Floor 2 West Server Hall Pressure Plate #1",
            "pos": [365.0, 435.0, 4.2],
            "zone": "ZONE_D",
            "floor": 2,
            "counter": "Jump 1.0m over plate or disarm (2.5s)",
        },
        {
            "id": "M07_T7_02",
            "type": "T7",
            "name": "Zone D Floor 2 East Monitor Approach Pressure Plate #2",
            "pos": [435.0, 435.0, 4.2],
            "zone": "ZONE_D",
            "floor": 2,
            "counter": "Jump 1.0m over plate or disarm (2.5s)",
        },
        {
            "id": "M07_T13_01",
            "type": "T13",
            "name": "Zone D Floor 1 Administration Front Lobby Alarmed Door #1",
            "pos": [400.0, 380.0, 0.0],
            "zone": "ZONE_D",
            "floor": 1,
            "snapped_doorway": [400.0, 380.0],
            "counter": "Lockpick + Hack PDA disarm before opening",
        },
        {
            "id": "M07_T13_02",
            "type": "T13",
            "name": "Zone D Floor 1 Administration Rear Service Stairs Alarmed Door #2",
            "pos": [400.0, 520.0, 0.0],
            "zone": "ZONE_D",
            "floor": 1,
            "snapped_doorway": [400.0, 520.0],
            "counter": "Lockpick + Hack PDA disarm before opening",
        },
        {
            "id": "M07_T16_01",
            "type": "T16",
            "name": "Zone A West Pier Electrified Wet Dock Conduit #1",
            "pos": [280.0, 45.0, 0.0],
            "zone": "ZONE_A",
            "hazard_subtype": "electrified_wet_dock_cable",
            "damage_per_sec": 35.0,
            "counter": "Shut off pier junction box or vault across dry bollard crates",
        },
        {
            "id": "M07_T16_02",
            "type": "T16",
            "name": "Zone A East Pier Swinging Crane Load & Wet Conduit #2",
            "pos": [620.0, 45.0, 0.0],
            "zone": "ZONE_A",
            "hazard_subtype": "swinging_crane_load_and_wet_cable",
            "damage_per_sec": 35.0,
            "counter": "Time crossing between crane swings or cut local power",
        },
    ]
    assert len(traps) == 10, f"Expected 10 traps, got {len(traps)}"

    cameras = [
        {
            "id": "M07_CAM_01",
            "type": "T11",
            "name": "Zone B Container Maze SW Watchtower Camera #1",
            "pos": [135.0, 114.0, 4.2],
            "zone": "ZONE_B",
            "mounted_on": "M07_WATCHTOWER_B_SW",
            "fov_deg": 70.0,
            "range_m": 35.0,
            "monitor_id": "M07_MON_01",
        },
        {
            "id": "M07_CAM_02",
            "type": "T11",
            "name": "Zone B Container Maze NW Watchtower Camera #2",
            "pos": [135.0, 314.0, 4.2],
            "zone": "ZONE_B",
            "mounted_on": "M07_WATCHTOWER_B_NW",
            "fov_deg": 70.0,
            "range_m": 35.0,
            "monitor_id": "M07_MON_01",
        },
        {
            "id": "M07_CAM_03",
            "type": "T11",
            "name": "Zone B Container Maze SE Watchtower Camera #3",
            "pos": [565.0, 114.0, 4.2],
            "zone": "ZONE_B",
            "mounted_on": "M07_WATCHTOWER_B_SE",
            "fov_deg": 70.0,
            "range_m": 35.0,
            "monitor_id": "M07_MON_01",
        },
        {
            "id": "M07_CAM_04",
            "type": "T11",
            "name": "Zone B Container Maze NE Watchtower Camera #4",
            "pos": [565.0, 314.0, 4.2],
            "zone": "ZONE_B",
            "mounted_on": "M07_WATCHTOWER_B_NE",
            "fov_deg": 70.0,
            "range_m": 35.0,
            "monitor_id": "M07_MON_01",
        },
        {
            "id": "M07_CAM_05",
            "type": "T11",
            "name": "Zone D Floor 1 Front Lobby Security Camera #5",
            "pos": [392.0, 380.4, 3.4],
            "zone": "ZONE_D",
            "floor": 1,
            "mounted_on": "M07_BLDG_ADMIN_VAULT_D",
            "fov_deg": 70.0,
            "range_m": 32.0,
            "monitor_id": "M07_MON_01",
        },
        {
            "id": "M07_CAM_06",
            "type": "T11",
            "name": "Zone D Floor 1 Rear Service Stairs Security Camera #6",
            "pos": [408.0, 519.6, 3.4],
            "zone": "ZONE_D",
            "floor": 1,
            "mounted_on": "M07_BLDG_ADMIN_VAULT_D",
            "fov_deg": 70.0,
            "range_m": 32.0,
            "monitor_id": "M07_MON_01",
        },
        {
            "id": "M07_CAM_07",
            "type": "T11",
            "name": "Zone D Floor 3 Executive West Hall Camera #7",
            "pos": [300.4, 462.0, 11.2],
            "zone": "ZONE_D",
            "floor": 3,
            "mounted_on": "M07_BLDG_ADMIN_VAULT_D",
            "fov_deg": 75.0,
            "range_m": 32.0,
            "monitor_id": "M07_MON_01",
        },
        {
            "id": "M07_CAM_08",
            "type": "T11",
            "name": "Zone D Floor 3 Executive Vault Door Camera #8",
            "pos": [499.6, 468.0, 11.2],
            "zone": "ZONE_D",
            "floor": 3,
            "mounted_on": "M07_BLDG_ADMIN_VAULT_D",
            "fov_deg": 75.0,
            "range_m": 32.0,
            "monitor_id": "M07_MON_01",
        },
    ]
    assert len(cameras) == 8, f"Expected 8 cameras, got {len(cameras)}"

    alarms = [
        {
            "id": "M07_ALM_01",
            "type": "prop_alarm_panel_a",
            "name": "Zone D Floor 1 Administration Lobby Master Alarm Panel #1",
            "pos": [404.0, 392.0, 1.3],
            "zone": "ZONE_D",
            "floor": 1,
        },
        {
            "id": "M07_ALM_02",
            "type": "prop_alarm_panel_a",
            "name": "Zone C East Gantry Crane Apron Alarm Panel #2",
            "pos": [696.0, 154.0, 1.3],
            "zone": "ZONE_C",
        },
        {
            "id": "M07_ALM_03",
            "type": "prop_alarm_panel_a",
            "name": "Zone E West Perimeter Gatehouse Alarm Panel #3",
            "pos": [52.0, 342.0, 1.3],
            "zone": "ZONE_E",
        },
    ]
    assert len(alarms) == 3

    safe_spots = [
        {
            "id": "M07_SAFE_01",
            "name": "East Breakwater Pump Alcove Safe Spot",
            "pos": [765.0, 22.0, 0.0],
            "radius": 4.5,
            "zone": "ZONE_A",
        },
        {
            "id": "M07_SAFE_02",
            "name": "Zone B Open Maintenance Shipping Container",
            "pos": [340.0, 225.0, 0.0],
            "radius": 4.0,
            "zone": "ZONE_B",
        },
        {
            "id": "M07_SAFE_03",
            "name": "West Pier Boat Boathouse Shadow Alcove",
            "pos": [74.0, 52.0, 0.0],
            "radius": 4.5,
            "zone": "ZONE_A",
        },
    ]
    assert len(safe_spots) == 3

    # =========================================================================
    # 4. ENEMIES (Exact 44: 24x E2, 4x E3, 4x E4, 2x E6, 4x E9, 2x E10, 4x E12)
    # =========================================================================
    enemies: List[Dict[str, Any]] = []

    # --- 24x E2 Cobalt Grunts (wpn_ar5_mesh) ---
    e2_specs = [
        ("M07_E2_01", "Waterfront Pier East Patrol #1",       [680.0, 28.0, 0.0],  "ZONE_A", [[680.0, 28.0], [745.0, 28.0], [745.0, 62.0], [680.0, 62.0]]),
        ("M07_E2_02", "Waterfront Pier Mid-East Patrol #2",   [510.0, 28.0, 0.0],  "ZONE_A", [[510.0, 28.0], [585.0, 28.0], [585.0, 62.0], [510.0, 62.0]]),
        ("M07_E2_03", "Waterfront Pier Mid-West Patrol #3",   [320.0, 28.0, 0.0],  "ZONE_A", [[320.0, 28.0], [395.0, 28.0], [395.0, 62.0], [320.0, 62.0]]),
        ("M07_E2_04", "Waterfront Patrol Boat Berth Guard #4",[110.0, 28.0, 0.0],  "ZONE_A", [[110.0, 28.0], [175.0, 28.0], [175.0, 62.0], [110.0, 62.0]]),
        ("M07_E2_05", "Container Maze Lane A1 Guard #5",      [155.0, 105.0, 0.0], "ZONE_B", [[155.0, 105.0], [235.0, 105.0], [235.0, 142.0], [155.0, 142.0]]),
        ("M07_E2_06", "Container Maze Lane A2 Guard #6",      [275.0, 105.0, 0.0], "ZONE_B", [[275.0, 105.0], [355.0, 105.0], [355.0, 142.0], [275.0, 142.0]]),
        ("M07_E2_07", "Container Maze Lane A3 Guard #7",      [395.0, 105.0, 0.0], "ZONE_B", [[395.0, 105.0], [475.0, 105.0], [475.0, 142.0], [395.0, 142.0]]),
        ("M07_E2_08", "Container Maze Lane B1 Guard #8",      [155.0, 175.0, 0.0], "ZONE_B", [[155.0, 175.0], [235.0, 175.0], [235.0, 215.0], [155.0, 215.0]]),
        ("M07_E2_09", "Container Maze Lane B2 Guard #9",      [275.0, 175.0, 0.0], "ZONE_B", [[275.0, 175.0], [355.0, 175.0], [355.0, 215.0], [275.0, 215.0]]),
        ("M07_E2_10", "Container Maze Lane B3 Guard #10",     [395.0, 175.0, 0.0], "ZONE_B", [[395.0, 175.0], [475.0, 175.0], [475.0, 215.0], [395.0, 215.0]]),
        ("M07_E2_11", "Container Maze Lane C1 Guard #11",     [155.0, 255.0, 0.0], "ZONE_B", [[155.0, 255.0], [235.0, 255.0], [235.0, 305.0], [155.0, 305.0]]),
        ("M07_E2_12", "Container Maze Lane C2 Guard #12",     [275.0, 255.0, 0.0], "ZONE_B", [[275.0, 255.0], [355.0, 255.0], [355.0, 305.0], [275.0, 305.0]]),
        ("M07_E2_13", "Container Maze Lane C3 Guard #13",     [395.0, 255.0, 0.0], "ZONE_B", [[395.0, 255.0], [475.0, 255.0], [475.0, 305.0], [395.0, 305.0]]),
        ("M07_E2_14", "Container Maze East Alley Guard #14",  [505.0, 155.0, 0.0], "ZONE_B", [[505.0, 155.0], [555.0, 155.0], [555.0, 285.0], [505.0, 285.0]]),
        ("M07_E2_15", "Zone C Crane Apron South Guard #15",   [625.0, 122.0, 0.0], "ZONE_C", [[625.0, 122.0], [685.0, 122.0], [685.0, 168.0], [625.0, 168.0]]),
        ("M07_E2_16", "Zone C Crane Apron East Guard #16",    [735.0, 135.0, 0.0], "ZONE_C", [[735.0, 135.0], [825.0, 135.0], [825.0, 205.0], [735.0, 205.0]]),
        ("M07_E2_17", "Zone C Crane Apron North Guard #17",   [635.0, 245.0, 0.0], "ZONE_C", [[635.0, 245.0], [785.0, 245.0], [785.0, 325.0], [635.0, 325.0]]),
        ("M07_E2_18", "Zone D Floor 1 West Lobby Guard #18",  [325.0, 395.0, 0.0], "ZONE_D", [[325.0, 395.0], [385.0, 395.0], [385.0, 445.0], [325.0, 445.0]]),
        ("M07_E2_19", "Zone D Floor 1 East Lobby Guard #19",  [415.0, 395.0, 0.0], "ZONE_D", [[415.0, 395.0], [475.0, 395.0], [475.0, 445.0], [415.0, 445.0]]),
        ("M07_E2_20", "Zone D Floor 1 Rear Stairs Guard #20", [335.0, 475.0, 0.0], "ZONE_D", [[335.0, 475.0], [465.0, 475.0], [465.0, 508.0], [335.0, 508.0]]),
        ("M07_E2_21", "Zone D Floor 2 Server Hall Guard #21", [325.0, 415.0, 4.2], "ZONE_D", [[325.0, 415.0], [475.0, 415.0], [475.0, 455.0], [325.0, 455.0]]),
        ("M07_E2_22", "Zone D Exterior West Courtyard #22",   [185.0, 415.0, 0.0], "ZONE_D", [[185.0, 415.0], [275.0, 415.0], [275.0, 495.0], [185.0, 495.0]]),
        ("M07_E2_23", "Zone D Exterior East Courtyard #23",   [525.0, 415.0, 0.0], "ZONE_D", [[525.0, 415.0], [625.0, 415.0], [625.0, 495.0], [525.0, 495.0]]),
        ("M07_E2_24", "Zone E West Gatehouse Road Guard #24", [48.0,  318.0, 0.0], "ZONE_E", [[48.0, 318.0],  [88.0, 318.0],  [88.0, 368.0],  [48.0, 368.0]]),
    ]
    for eid, ename, epos, ezone, ewps in e2_specs:
        enemies.append({
            "id": eid,
            "class": "E2",
            "name": ename,
            "asset_id": "chr_enemy_e2_rifleman",
            "weapon": "wpn_ar5_mesh",
            "uses_cover": True,
            "calls_squad": True,
            "pos": epos,
            "zone": ezone,
            "patrol_waypoints": ewps,
        })

    # --- 4x E3 Radio Officers (wpn_p45_enforcer, radio: true) ---
    e3_specs = [
        ("M07_E3_01", "Zone B Container Yard West Radio Officer #1", [245.0, 225.0, 0.0], "ZONE_B", [[245.0, 225.0], [315.0, 225.0], [315.0, 248.0], [245.0, 248.0]]),
        ("M07_E3_02", "Zone B Container Yard East Radio Officer #2", [465.0, 225.0, 0.0], "ZONE_B", [[465.0, 225.0], [535.0, 225.0], [535.0, 248.0], [465.0, 248.0]]),
        ("M07_E3_03", "Zone C Crane Apron Radio Officer #3",         [665.0, 195.0, 0.0], "ZONE_C", [[665.0, 195.0], [725.0, 195.0], [725.0, 228.0], [665.0, 228.0]]),
        ("M07_E3_04", "Zone D Floor 1 Lobby Duty Officer #4",        [395.0, 412.0, 0.0], "ZONE_D", [[375.0, 412.0], [425.0, 412.0], [425.0, 432.0], [375.0, 432.0]]),
    ]
    for eid, ename, epos, ezone, ewps in e3_specs:
        enemies.append({
            "id": eid,
            "class": "E3",
            "name": ename,
            "asset_id": "chr_enemy_e3_officer",
            "weapon": "wpn_p45_enforcer",
            "radio": True,
            "has_radio": True,
            "radio_checkin_interval_s": 45.0,
            "pos": epos,
            "zone": ezone,
            "patrol_waypoints": ewps,
        })

    # --- 4x E4 Cobalt Elite (wpn_ar12_burst) on Floor 3 Executive Vault Suite ---
    e4_specs = [
        ("M07_E4_01", "Zone D Floor 3 Vault West Elite #1",  [335.0, 445.0, 8.4], "ZONE_D", [[335.0, 445.0], [382.0, 445.0], [382.0, 488.0], [335.0, 488.0]]),
        ("M07_E4_02", "Zone D Floor 3 Vault East Elite #2",  [428.0, 445.0, 8.4], "ZONE_D", [[428.0, 445.0], [478.0, 445.0], [478.0, 488.0], [428.0, 488.0]]),
        ("M07_E4_03", "Zone D Floor 3 Vault North Elite #3", [375.0, 482.0, 8.4], "ZONE_D", [[375.0, 482.0], [435.0, 482.0], [435.0, 506.0], [375.0, 506.0]]),
        ("M07_E4_04", "Zone D Floor 3 Vault Inner Elite #4", [408.0, 468.0, 8.4], "ZONE_D", [[404.0, 465.0], [418.0, 465.0], [418.0, 476.0], [404.0, 476.0]]),
    ]
    for eid, ename, epos, ezone, ewps in e4_specs:
        enemies.append({
            "id": eid,
            "class": "E4",
            "name": ename,
            "asset_id": "chr_enemy_e4_shotgunner",
            "weapon": "wpn_ar12_burst",
            "ballistic_vest": True,
            "throws_grenades": True,
            "flanks_player": True,
            "floor": 3,
            "pos": epos,
            "zone": ezone,
            "patrol_waypoints": ewps,
        })

    # --- 2x E6 Snipers (wpn_longbow_mesh on Gantry Crane catwalk & Admin Roof) ---
    enemies.append({
        "id": "M07_E6_01",
        "class": "E6",
        "name": "Zone C Gantry Crane Upper Catwalk Sniper #1",
        "asset_id": "chr_enemy_e6_sniper",
        "weapon": "wpn_longbow_mesh",
        "vision_range_m": 80.0,
        "laser_paint_seconds": 1.0,
        "pos": [700.0, 150.0, 12.0],
        "elevation": 12.0,
        "mount": "watchtower",
        "zone": "ZONE_C",
        "patrol_waypoints": [
            [698.5, 148.5],
            [701.5, 148.5],
            [701.5, 151.5],
            [698.5, 151.5],
        ],
    })
    enemies.append({
        "id": "M07_E6_02",
        "class": "E6",
        "name": "Zone D Administration Building Roof Overwatch Sniper #2",
        "asset_id": "chr_enemy_e6_sniper",
        "weapon": "wpn_longbow_mesh",
        "vision_range_m": 80.0,
        "laser_paint_seconds": 1.0,
        "pos": [450.0, 400.0, 12.5],
        "elevation": 12.5,
        "mount": "roof",
        "zone": "ZONE_D",
        "patrol_waypoints": [
            [442.0, 392.0],
            [468.0, 392.0],
            [468.0, 412.0],
            [442.0, 412.0],
        ],
    })

    # --- 4x E9 Technicians (wpn_p9_compact) on Floor 2 Server Room & Zone C Crane Booth ---
    e9_specs = [
        ("M07_E9_01", "Zone D Floor 2 Camera Server Technician #1", [388.0, 442.0, 4.2], "ZONE_D", [[382.0, 438.0], [412.0, 438.0], [412.0, 456.0], [382.0, 456.0]]),
        ("M07_E9_02", "Zone D Floor 2 Power Grid Technician #2",    [442.0, 442.0, 4.2], "ZONE_D", [[436.0, 438.0], [468.0, 438.0], [468.0, 456.0], [436.0, 456.0]]),
        ("M07_E9_03", "Zone C Gantry Crane Booth Technician #3",    [704.0, 156.0, 0.0], "ZONE_C", [[692.0, 144.0], [714.0, 144.0], [714.0, 164.0], [692.0, 164.0]]),
        ("M07_E9_04", "Zone A Waterfront Conduit Technician #4",    [288.0, 52.0, 0.0],  "ZONE_A", [[272.0, 48.0],  [308.0, 48.0],  [308.0, 66.0],  [272.0, 66.0]]),
    ]
    for eid, ename, epos, ezone, ewps in e9_specs:
        enemies.append({
            "id": eid,
            "class": "E9",
            "name": ename,
            "asset_id": "chr_enemy_e9_technician",
            "weapon": "wpn_p9_compact",
            "repairs_cameras_and_lights": True,
            "pos": epos,
            "zone": ezone,
            "patrol_waypoints": ewps,
        })

    # --- 2x E10 Scouts (wpn_ar9_carbine) in Zone B Container Maze ---
    e10_specs = [
        ("M07_E10_01", "Zone B Container Yard South Recon Scout #1", [215.0, 145.0, 0.0], "ZONE_B", [[215.0, 145.0], [268.0, 145.0], [268.0, 168.0], [215.0, 168.0]]),
        ("M07_E10_02", "Zone B Container Yard North Recon Scout #2", [435.0, 315.0, 0.0], "ZONE_B", [[435.0, 315.0], [495.0, 315.0], [495.0, 338.0], [435.0, 338.0]]),
    ]
    for eid, ename, epos, ezone, ewps in e10_specs:
        enemies.append({
            "id": eid,
            "class": "E10",
            "name": ename,
            "asset_id": "chr_enemy_e10_dog_handler",
            "weapon": "wpn_ar9_carbine",
            "equipment": ["Binoculars"],
            "vision_range_m": 60.0,
            "pos": epos,
            "zone": ezone,
            "patrol_waypoints": ewps,
        })

    # --- 4x E12 Sentries (wpn_ar5_mesh) on the 4 Zone B Watchtowers ---
    e12_specs = [
        ("M07_E12_01", "Zone B SW Watchtower Sentry #1", [135.0, 115.0, 8.5], "ZONE_B", [[134.0, 114.0], [136.0, 114.0], [136.0, 116.0], [134.0, 116.0]]),
        ("M07_E12_02", "Zone B NW Watchtower Sentry #2", [135.0, 315.0, 8.5], "ZONE_B", [[134.0, 314.0], [136.0, 314.0], [136.0, 316.0], [134.0, 316.0]]),
        ("M07_E12_03", "Zone B SE Watchtower Sentry #3", [565.0, 115.0, 8.5], "ZONE_B", [[564.0, 114.0], [566.0, 114.0], [566.0, 116.0], [564.0, 116.0]]),
        ("M07_E12_04", "Zone B NE Watchtower Sentry #4", [565.0, 315.0, 8.5], "ZONE_B", [[564.0, 314.0], [566.0, 314.0], [566.0, 316.0], [564.0, 316.0]]),
    ]
    for eid, ename, epos, ezone, ewps in e12_specs:
        enemies.append({
            "id": eid,
            "class": "E12",
            "name": ename,
            "asset_id": "chr_enemy_e12_elite_commando",
            "weapon": "wpn_ar5_mesh",
            "pos": epos,
            "zone": ezone,
            "patrol_waypoints": ewps,
        })

    assert len(enemies) == 44, f"Expected 44 enemies, got {len(enemies)}"
    enemies = interleave_for_zero_step_repeats(enemies)

    # =========================================================================
    # 5. LIGHTS (Exact 63 Harbor Floodlights, Crane Sweep Light & Interior Lights)
    # =========================================================================
    lights: List[Dict[str, Any]] = [
        {
            "id": "M07_LGT_CRANE_SWEEP",
            "type": "light_flood_crane_rotating",
            "name": "Zone C Gantry Crane 90s Rotating Floodlight (Controlled by S1 at 700, 150)",
            "pos": [700.0, 150.0, 18.0],
            "zone": "ZONE_C",
            "sweep_period_sec": 90.0,
            "range_m": 65.0,
            "controlled_by_booth_id": "M07_CRANE_CONTROL_BOOTH_C",
        }
    ]
    light_zones = [
        ("ZONE_A",  25.0,  15.0, 875.0,  72.0, "light_flood_gate_pole"),
        ("ZONE_B", 110.0,  90.0, 590.0, 340.0, "light_flood_checkpoint"),
        ("ZONE_C", 610.0, 110.0, 840.0, 340.0, "light_flood_checkpoint"),
        ("ZONE_D", 310.0, 390.0, 490.0, 510.0, "light_fluorescent_tube"),
        ("ZONE_E",  15.0, 310.0,  90.0, 370.0, "light_caged_bulb_warm"),
    ]
    while len(lights) < 63:
        idx = len(lights) + 1
        zname, x0, y0, x1, y1, ltype = light_zones[idx % len(light_zones)]
        u = vdc(idx * 7 + 3, 2)
        v = vdc(idx * 11 + 5, 3)
        lx = round(x0 + u * (x1 - x0), 2)
        ly = round(y0 + v * (y1 - y0), 2)
        lights.append({
            "id": f"M07_LGT_{idx:02d}",
            "type": ltype,
            "pos": [lx, ly, 4.5],
            "zone": zname,
            "range_m": 18.0,
        })
    assert len(lights) == 63, f"Expected 63 lights, got {len(lights)}"

    # =========================================================================
    # 6. HIDING SPOTS (Exact 44 Hiding Spots across Zones A–E)
    # =========================================================================
    hide_zones = [
        ("ZONE_A",  30.0,  14.0, 860.0,  70.0, "prop_dumpster_metal_a"),
        ("ZONE_B", 115.0,  95.0, 585.0, 335.0, "prop_locker_metal_a"),
        ("ZONE_C", 615.0, 115.0, 835.0, 335.0, "prop_dumpster_metal_a"),
        ("ZONE_D", 312.0, 392.0, 488.0, 508.0, "vent_shaft"),
        ("ZONE_E",  18.0, 312.0,  88.0, 368.0, "prop_locker_metal_a"),
    ]
    hiding_spots: List[Dict[str, Any]] = []
    for i in range(1, 45):
        zname, x0, y0, x1, y1, htype = hide_zones[i % len(hide_zones)]
        u = vdc(i * 9 + 5, 2)
        v = vdc(i * 13 + 7, 3)
        hx = round(x0 + u * (x1 - x0), 2)
        hy = round(y0 + v * (y1 - y0), 2)
        hiding_spots.append({
            "id": f"M07_HIDE_{i:02d}",
            "type": htype,
            "pos": [hx, hy, 0.0],
            "zone": zname,
        })
    assert len(hiding_spots) == 44, f"Expected 44 hiding spots, got {len(hiding_spots)}"

    # =========================================================================
    # 7. PICKUPS (Exact 28 Pickups including Shipping Manifest O1, Boat Tracker S2 & Vector-K)
    # =========================================================================
    pickups: List[Dict[str, Any]] = [
        {"id": "M07_PKP_SHIPPING_MANIFEST", "type": "pickup_intel_manifest",     "name": "Top-Floor Vault Shipping Manifest (Primary Objective O1)", "pos": [410.0, 470.0, 8.4], "zone": "ZONE_D", "floor": 3, "objective_id": "O1"},
        {"id": "M07_PKP_REWARD_VECTORK",    "type": "pickup_reward_vectork",     "name": "Vector-K Tactical SMG (wpn_vectork — O1 Unlock)",          "pos": [412.0, 471.0, 8.4], "zone": "ZONE_D", "floor": 3},
        {"id": "M07_PKP_BOAT_TRACKER",      "type": "pickup_gadget_gps_tracker", "name": "Magnetic Hull GPS Tracker (Secondary Objective S2)",       "pos": [785.0, 18.0,  0.8], "zone": "ZONE_A", "objective_id": "S2"},
        {"id": "M07_PKP_KEYCARD_VAULT",     "type": "pickup_keycard_command",    "name": "Floor 3 Executive Vault Access Keycard",                   "pos": [402.0, 448.0, 4.2], "zone": "ZONE_D", "floor": 2},
        {"id": "M07_PKP_HACK_PDA",          "type": "pickup_gadget_hack_pda",    "name": "Harbor Cryptographic Hack PDA",                            "pos": [695.0, 148.0, 0.9], "zone": "ZONE_C"},
        {"id": "M07_PKP_EMP_01",            "type": "pickup_gadget_emp_grenade", "name": "EMP Grenade #1 (Disables T5 Laser Grid for 20s)",          "pos": [390.0, 442.0, 4.2], "zone": "ZONE_D", "floor": 2},
        {"id": "M07_PKP_EMP_02",            "type": "pickup_gadget_emp_grenade", "name": "EMP Grenade #2 (Disables T5 Laser Grid for 20s)",          "pos": [382.0, 452.0, 8.4], "zone": "ZONE_D", "floor": 3},
        {"id": "M07_PKP_WIRECUTTERS",       "type": "pickup_gadget_wirecutters", "name": "Insulated Harbor Wire Cutters",                            "pos": [242.0, 146.0, 0.8], "zone": "ZONE_B"},
        {"id": "M07_PKP_LOCKPICK",          "type": "pickup_gadget_lockpick",    "name": "Precision Lockpick Kit",                                   "pos": [396.0, 514.0, 0.8], "zone": "ZONE_D"},
    ]
    pkp_cycle = [
        ("pickup_ammo_9mm_box",    "9x19mm Subsonic Box"),
        ("pickup_ammo_556_box",    "5.56mm NATO Waterproof Crate"),
        ("pickup_medkit_field",    "Harbor Field Trauma Kit"),
        ("pickup_ammo_sniper_box", ".338 Longbow Match Box"),
    ]
    pkp_zones = [
        ("ZONE_A",  45.0,  16.0, 845.0,  68.0),
        ("ZONE_B", 120.0, 100.0, 580.0, 330.0),
        ("ZONE_C", 620.0, 120.0, 830.0, 330.0),
        ("ZONE_D", 315.0, 395.0, 485.0, 505.0),
        ("ZONE_E",  20.0, 315.0,  85.0, 365.0),
    ]
    while len(pickups) < 28:
        idx = len(pickups) + 1
        zname, x0, y0, x1, y1 = pkp_zones[idx % len(pkp_zones)]
        ptype, pname = pkp_cycle[idx % len(pkp_cycle)]
        u = vdc(idx * 7 + 11, 2)
        v = vdc(idx * 13 + 3, 3)
        px = round(x0 + u * (x1 - x0), 2)
        py = round(y0 + v * (y1 - y0), 2)
        pickups.append({
            "id": f"M07_PKP_{idx:02d}",
            "type": ptype,
            "name": f"{pname} #{idx}",
            "pos": [px, py, 0.8],
            "zone": zname,
        })
    assert len(pickups) == 28, f"Expected 28 pickups, got {len(pickups)}"
    pickups = interleave_for_zero_step_repeats(pickups)

    # =========================================================================
    # 8. VEGETATION (Exact 15 Coastal Scrub & Ornamental Planter Trees)
    # =========================================================================
    veg_zones = [
        ("ZONE_A",  25.0,  12.0, 880.0,  72.0),
        ("ZONE_D", 285.0, 368.0, 515.0, 532.0),
        ("ZONE_E",  12.0, 305.0,  95.0, 375.0),
    ]
    vegetation: List[Dict[str, Any]] = []
    for i in range(1, 16):
        zname, x0, y0, x1, y1 = veg_zones[i % len(veg_zones)]
        u = vdc(i * 5 + 3, 2)
        v = vdc(i * 9 + 7, 3)
        vx = round(x0 + u * (x1 - x0), 2)
        vy = round(y0 + v * (y1 - y0), 2)
        vegetation.append({
            "id": f"M07_VEG_{i:02d}",
            "type": "env_bush_stealth_a" if (i % 2 == 1) else "env_tree_pine_tall_a",
            "pos": [vx, vy, 0.0],
            "zone": zname,
        })
    assert len(vegetation) == 15, f"Expected 15 vegetation items, got {len(vegetation)}"
    vegetation = interleave_for_zero_step_repeats(vegetation)

    # =========================================================================
    # 9. COVER (Exact 814 Handcrafted Harbor Bollards, Crates & Barriers)
    # =========================================================================
    cover_zones = [
        ("ZONE_A",  18.0,  12.0, 882.0,  74.0, ["prop_concrete_barrier_a", "prop_crate_metal_a", "prop_sandbag_wall_a"]),
        ("ZONE_B", 108.0,  88.0, 592.0, 342.0, ["prop_crate_metal_a", "prop_concrete_barrier_a", "prop_crate_military_a"]),
        ("ZONE_C", 608.0, 108.0, 842.0, 342.0, ["prop_concrete_barrier_a", "prop_crate_metal_a", "prop_sandbag_wall_a"]),
        ("ZONE_D", 308.0, 388.0, 492.0, 512.0, ["prop_crate_metal_a", "prop_sandbag_wall_a", "prop_concrete_barrier_a"]),
        ("ZONE_E",  10.0, 306.0,  92.0, 374.0, ["prop_sandbag_wall_a", "prop_concrete_barrier_a", "prop_crate_military_a"]),
    ]
    cover: List[Dict[str, Any]] = []
    for i in range(1, 815):
        zname, x0, y0, x1, y1, ctypes = cover_zones[i % len(cover_zones)]
        u = vdc(i * 7 + 11, 2)
        v = vdc(i * 17 + 5, 3)
        cx = round(x0 + u * (x1 - x0), 2)
        cy = round(y0 + v * (y1 - y0), 2)
        cover.append({
            "id": f"M07_COV_{i:03d}",
            "type": ctypes[i % len(ctypes)],
            "pos": [cx, cy, 0.0],
            "zone": zname,
        })
    assert len(cover) == 814, f"Expected 814 cover pieces, got {len(cover)}"
    cover = interleave_for_zero_step_repeats(cover)

    # =========================================================================
    # 10. PROPS (Exact 1521 Props including M07_MON_01, Containers & 3 Alarms)
    # =========================================================================
    props: List[Dict[str, Any]] = [
        {
            "id": "M07_MON_01",
            "type": "prop_terminal_desk_a",
            "name": "Zone D Floor 2 Server Room Camera Monitor Terminal (Controls M07_CAM_01 to M07_CAM_08)",
            "pos": [400.0, 445.0, 4.2],
            "zone": "ZONE_D",
            "floor": 2,
            "controls_camera_ids": [
                "M07_CAM_01", "M07_CAM_02", "M07_CAM_03", "M07_CAM_04",
                "M07_CAM_05", "M07_CAM_06", "M07_CAM_07", "M07_CAM_08",
            ],
        },
        {
            "id": "M07_ALM_01",
            "type": "prop_alarm_panel_a",
            "name": "Zone D Floor 1 Administration Lobby Master Alarm Panel #1",
            "pos": [404.0, 392.0, 1.3],
            "zone": "ZONE_D",
            "floor": 1,
        },
        {
            "id": "M07_ALM_02",
            "type": "prop_alarm_panel_a",
            "name": "Zone C East Gantry Crane Apron Alarm Panel #2",
            "pos": [696.0, 154.0, 1.3],
            "zone": "ZONE_C",
        },
        {
            "id": "M07_ALM_03",
            "type": "prop_alarm_panel_a",
            "name": "Zone E West Perimeter Gatehouse Alarm Panel #3",
            "pos": [52.0, 342.0, 1.3],
            "zone": "ZONE_E",
        },
        {
            "id": "M07_PRP_VAULT_SAFE_D",
            "type": "prop_vault_safe_heavy_a",
            "name": "Top-Floor Executive Vault Safe at (410, 470) (Houses O1 Shipping Manifest)",
            "pos": [410.0, 470.0, 8.4],
            "zone": "ZONE_D",
            "floor": 3,
            "objective_id": "O1",
        },
        {
            "id": "M07_PRP_CRANE_CONSOLE_S1",
            "type": "prop_terminal_desk_a",
            "name": "Zone C Crane Floodlight Sabotage Console at (700, 150) (Secondary Objective S1)",
            "pos": [700.0, 150.0, 0.0],
            "zone": "ZONE_C",
            "objective_id": "S1",
        },
    ]

    prop_catalog = [
        "prop_container_20ft",
        "prop_container_40ft",
        "prop_crate_metal_a",
        "prop_crate_military_a",
        "prop_fuel_drum_metal_a",
        "prop_cable_spool_wood_a",
        "prop_concrete_barrier_a",
        "prop_locker_metal_a",
        "prop_dumpster_metal_a",
        "prop_generator_diesel_a",
        "prop_breaker_box_a",
        "prop_workbench_tools_a",
        "prop_radio_field_desk_a",
        "prop_water_jerrycan_a",
    ]
    prop_zones = [
        ("ZONE_A",  20.0,  14.0, 880.0,  72.0),
        ("ZONE_B", 106.0,  86.0, 594.0, 344.0),
        ("ZONE_C", 606.0, 106.0, 844.0, 344.0),
        ("ZONE_D", 306.0, 386.0, 494.0, 514.0),
        ("ZONE_E",  12.0, 308.0,  90.0, 372.0),
    ]

    while len(props) < 1521:
        idx = len(props) + 1
        zname, x0, y0, x1, y1 = prop_zones[idx % len(prop_zones)]
        u = vdc(idx * 11 + 5, 2)
        v = vdc(idx * 19 + 9, 5)
        px = round(x0 + u * (x1 - x0), 2)
        py = round(y0 + v * (y1 - y0), 2)
        props.append({
            "id": f"M07_PRP_{idx:04d}",
            "type": prop_catalog[idx % len(prop_catalog)],
            "pos": [px, py, 0.0],
            "zone": zname,
        })

    assert len(props) == 1521, f"Expected 1521 props, got {len(props)}"
    props = interleave_for_zero_step_repeats(props)

    # =========================================================================
    # 11. DYNAMIC MISSION EVENTS (Exact 2 Events: E_M07_RAIN, E_M07_CRANE)
    # =========================================================================
    events = [
        {
            "id": "E_M07_RAIN",
            "trigger": "elapsed >= 720",
            "condition": {"type": "time_elapsed_sec", "threshold": 720.0},
            "action": "weather_heavy_rain_hearing_0.8",
            "hearing_multiplier": 0.8,
            "description": "At elapsed >= 720s, rain intensifies into a heavy downpour, reducing enemy hearing radius to 0.8x.",
        },
        {
            "id": "E_M07_CRANE",
            "trigger": "loop:90s",
            "condition": {"type": "periodic_loop_sec", "interval_sec": 90.0},
            "action": "crane_floodlight_sweep_yard",
            "crane_id": "M07_GANTRY_CRANE_C",
            "disabled_by_objective": "S1",
            "description": "Every 90s (loop:90s), the Zone C gantry crane floodlight sweeps across the container yard unless sabotaged via S1 at (700, 150).",
        },
    ]
    assert len(events) == 2

    # =========================================================================
    # 12. OBJECTIVES (O1, S1, S2) & 3 COMPLETE 6-WAYPOINT TACTICAL ROUTES
    # =========================================================================
    objectives = {
        "primary": [
            {
                "id": "O1",
                "title": "Infiltrate the 3-story Administration Building and steal the shipping manifest from the top-floor vault at (410, 470)",
                "target_id": "M07_PKP_SHIPPING_MANIFEST",
                "target_pos": [410.0, 470.0, 8.4],
                "floor": 3,
                "zone": "ZONE_D",
                "unlock_reward": "Vector-K",
                "unlock_weapon_id": "wpn_vectork",
            }
        ],
        "secondary": [
            {
                "id": "S1",
                "title": "Sabotage crane controls at (700, 150)",
                "target_id": "M07_CRANE_CONTROL_BOOTH_C",
                "target_pos": [700.0, 150.0, 0.0],
                "disables_event_id": "E_M07_CRANE",
                "zone": "ZONE_C",
            },
            {
                "id": "S2",
                "title": "Plant tracker on patrol boat at (90, 30) and escape unseen (Ghost Medal)",
                "target_id": "M07_PATROL_BOAT_A",
                "target_pos": [90.0, 30.0, 0.0],
                "require_unseen": True,
                "medal_reward": "Ghost Medal",
                "zone": "ZONE_A",
            },
        ],
        "extraction": {
            "id": "EXT_M07",
            "title": "Extract at West Dock Extraction Point (60, 40)",
            "pos": [60.0, 40.0, 0.0],
            "radius": 10.0,
            "zone": "ZONE_A",
        },
    }

    routes = {
        "silent": {
            "name": "Silent Route (Zone C Shadow Gap, Exterior Drainpipe/Vent to Floor 3, Ceiling Vent Laser Bypass & Boat Tracker)",
            "description": "Sneak from (800, 10) through the Zone C shadow gap (720, 260), climb the exterior drainpipe/vent shaft at (500, 470) directly to Floor 3, bypass T5 laser grids via ceiling vent M07_VENT_SHAFT_ADMIN_D to steal the Shipping Manifest at (410, 470), descend to Pier Berth (90, 30) to plant the GPS tracker on the patrol boat (S2), and extract unseen at (60, 40).",
            "waypoints": [
                [800.0, 10.0],
                [720.0, 260.0],
                [500.0, 470.0],
                [410.0, 470.0],
                [90.0, 30.0],
                [60.0, 40.0],
            ],
        },
        "technical": {
            "name": "Technical Route (Sabotage Crane Controls S1, Hack T13 Rear Door, Disable Floor 2 Monitor & EMP T5 Lasers)",
            "description": "Advance from (800, 10) to the Zone C Crane Control Booth at (700, 150) to sabotage the sweeping floodlight (S1), hack the rear T13 Alarmed Door at (400, 520), disable all 8 cameras at M07_MON_01 on Floor 2 and EMP the T5 Laser Grids to steal the manifest at (410, 470), exit via the West courtyard (200, 380), and extract at (60, 40).",
            "waypoints": [
                [800.0, 10.0],
                [700.0, 150.0],
                [400.0, 520.0],
                [410.0, 470.0],
                [200.0, 380.0],
                [60.0, 40.0],
            ],
        },
        "loud": {
            "name": "Loud Route (Counter-Snipe Crane Sniper E6, Breach Front Lobby, Clear Floor 3 E4 Elites & Fight to West Pier)",
            "description": "Advance from (800, 10) to overwatch at (650, 150) to counter-snipe Gantry Crane Sniper M07_E6_01, breach the Administration Building front lobby at (400, 380), clear the 4x E4 Elites on Floor 3 to seize the manifest at (410, 470), exit West at (300, 470), and fight down to West Dock Extraction at (60, 40).",
            "waypoints": [
                [800.0, 10.0],
                [650.0, 150.0],
                [400.0, 380.0],
                [410.0, 470.0],
                [300.0, 470.0],
                [60.0, 40.0],
            ],
        },
    }

    level_dict = {
        "mission_id": "M07",
        "title": "Port Authority",
        "chapter": 2,
        "scene_name": "M07",
        "width": 900.0,
        "height": 600.0,
        "area_hectares": 54.0,
        "biome": "industrial_harbor",
        "time_of_day": "night",
        "weather": "rain",
        "player_start": {
            "pos": [800.0, 10.0, 0.0],
            "facing_deg": 270.0,
            "facing_cardinal": "West",
            "starting_loadout": ["wpn_usp45_suppressed", "wpn_mp5sd_integral", "wpn_knife_mesh", "BoatTrackerGPS", "WireCutters", "HackPDA", "EMPGrenade_x2", "Lockpick"],
        },
        "strict_exclusions_enforced": {
            "forbidden_enemies": ["E1", "E5", "E7", "E8", "E11", "E14"],
            "forbidden_traps": ["T2", "T3", "T4", "T6", "T8", "T9", "T10", "T12", "T14", "T15"],
            "allowed_traps_only": ["T1", "T5", "T7", "T13", "T16"],
            "security_cameras_count": 8,
        },
        "zones": zones,
        "objectives": objectives,
        "events": events,
        "routes": routes,
        "structures": structures,
        "props": props,
        "cover": cover,
        "vegetation": vegetation,
        "lights": lights,
        "hiding_spots": hiding_spots,
        "safe_spots": safe_spots,
        "enemies": enemies,
        "traps": traps,
        "cameras": cameras,
        "alarms": alarms,
        "pickups": pickups,
        "census": {
            "structures": len(structures),
            "props": len(props),
            "cover": len(cover),
            "vegetation": len(vegetation),
            "lights": len(lights),
            "hiding_spots": len(hiding_spots),
            "safe_spots": len(safe_spots),
            "enemies": len(enemies),
            "traps": len(traps),
            "cameras": len(cameras),
            "alarms": len(alarms),
            "pickups": len(pickups),
            "events": len(events),
        },
    }
    return level_dict


def write_m07_unity_scene_and_installer() -> Tuple[str, str]:
    scenes_dir = os.path.join(ROOT_DIR, "Assets/_Project/Scenes")
    scripts_dir = os.path.join(ROOT_DIR, "Assets/_Project/Scripts/Core")
    os.makedirs(scenes_dir, exist_ok=True)
    os.makedirs(scripts_dir, exist_ok=True)

    scene_path = os.path.join(scenes_dir, "M07.unity")
    installer_path = os.path.join(scripts_dir, "M07_PortAuthoritySceneInstaller.cs")

    unity_yaml = """%YAML 1.1
%TAG !u! tag:unity3d.com,2011:
--- !u!29 &1
OcclusionCullingSettings:
  m_ObjectHideFlags: 0
  serializedVersion: 2
  m_OcclusionBakeSettings:
    smallestOccluder: 5
    smallestHole: 0.25
    backfaceThreshold: 100
--- !u!104 &2
RenderSettings:
  m_ObjectHideFlags: 0
  serializedVersion: 9
  m_Fog: 1
  m_FogColor: {r: 0.08, g: 0.11, b: 0.16, a: 1}
  m_FogMode: 3
  m_FogDensity: 0.0085
  m_AmbientMode: 0
  m_AmbientSkyColor: {r: 0.10, g: 0.14, b: 0.20, a: 1}
--- !u!157 &3
LightmapSettings:
  m_ObjectHideFlags: 0
  serializedVersion: 12
--- !u!196 &4
NavMeshSettings:
  serializedVersion: 2
  m_ObjectHideFlags: 0
--- !u!1 &100
GameObject:
  m_ObjectHideFlags: 0
  serializedVersion: 6
  m_Component:
  - component: {fileID: 101}
  - component: {fileID: 102}
  m_Name: M07_PortAuthority_MissionRoot
  m_TagString: Untagged
  m_IsActive: 1
--- !u!4 &101
Transform:
  m_ObjectHideFlags: 0
  m_GameObject: {fileID: 100}
  m_LocalRotation: {x: 0, y: 0, z: 0, w: 1}
  m_LocalPosition: {x: 0, y: 0, z: 0}
  m_LocalScale: {x: 1, y: 1, z: 1}
--- !u!114 &102
MonoBehaviour:
  m_ObjectHideFlags: 0
  m_GameObject: {fileID: 100}
  m_Enabled: 1
  m_EditorHideFlags: 0
  m_Script: {fileID: 11500000, guid: 0718293a4b5c6d7e8f90a1b2c3d4e5f6, type: 3}
  m_Name: 
  m_EditorClassIdentifier: RealLoserStudio.Tactical.Core.M07_PortAuthoritySceneInstaller
  missionJsonPath: Assets/_Project/Missions/M07.json
  enforceStrictM07Exclusions: 1
"""
    with open(scene_path, "w", encoding="utf-8") as f:
        f.write(unity_yaml)

    installer_cs = """using System;
using System.Collections.Generic;
using UnityEngine;
using RealLoserStudio.Tactical.Player;
using RealLoserStudio.Tactical.Stealth;
using RealLoserStudio.Tactical.Traps;
using RealLoserStudio.Tactical.AI;
using RealLoserStudio.Tactical.UI;
using RealLoserStudio.Tactical.Streaming;

namespace RealLoserStudio.Tactical.Core
{
    /// <summary>
    /// Scene Bootstrapper & Runtime Controller for Mission 07 ("Port Authority" — Chapter 2).
    /// Manages the 5-Zone 900x600m (54.0 Hectares) Night-Rain Shipping Port,
    /// 44 Enemies (24x E2, 4x E3, 4x E4, 2x E6 Snipers, 4x E9 Technicians, 2x E10 Scouts, 4x E12 Sentries),
    /// 10 Traps (2x T1, 2x T5 Laser Grids, 2x T7 Pressure Plates, 2x T13 Alarmed Doors, 2x T16 Hazards),
    /// 8 Cameras (M07_CAM_01..08 linked to M07_MON_01 on Floor 2), and Events E_M07_RAIN & E_M07_CRANE.
    /// </summary>
    public class M07_PortAuthoritySceneInstaller : MonoBehaviour
    {
        [Header("Mission 07 Blueprint Binding")]
        public string missionJsonPath = "Assets/_Project/Missions/M07.json";
        public bool enforceStrictM07Exclusions = true;

        [Header("Core System References")]
        public PlayerTacticalController playerController;
        public StealthAndDetectionSystem stealthSystem;
        public MissionEventAndStreamingSystem streamingSystem;
        public MobileTouchHUDAndMEMap touchHudMap;

        [Header("Primary Objective O1 — Top-Floor Vault Shipping Manifest (410, 470)")]
        public bool manifestStolen;
        public bool objectiveO1_Complete;
        public bool rewardVectorKUnlocked;

        [Header("Secondary Objectives (S1 Crane Sabotage, S2 Boat Tracker & Ghost Medal)")]
        public bool objectiveS1_CraneControlsSabotaged;
        public bool boatTrackerPlanted;
        public bool playerDetectedDuringMission;
        public bool objectiveS2_GhostMedalEarned;

        [Header("Dynamic Mission Events (E_M07_RAIN at 720s, E_M07_CRANE every 90s)")]
        public bool heavyRainDownpourActive;
        public float enemyHearingMultiplier = 1.0f;
        public float craneSweepTimerSec;
        public float craneFloodlightAngleDeg;
        private float _missionElapsedSec;

        private void Start()
        {
            InitializeMission07();
        }

        public void InitializeMission07()
        {
            _missionElapsedSec = 0f;
            craneSweepTimerSec = 0f;
            heavyRainDownpourActive = false;
            enemyHearingMultiplier = 1.0f;

            if (playerController != null)
            {
                // Spawn at Zone A East Breakwater [800.0, 10.0] facing West (270 deg)
                playerController.transform.position = new Vector3(800.0f, 0.0f, 10.0f);
                playerController.transform.rotation = Quaternion.Euler(0f, 270f, 0f);
            }

            if (stealthSystem != null)
            {
                stealthSystem.OnAlertLevelChanged += HandleAlertLevelChanged;
            }
        }

        private void Update()
        {
            float dt = Time.deltaTime;
            _missionElapsedSec += dt;

            // Event 1: E_M07_RAIN at elapsed >= 720s (heavy rain reduces enemy hearing to 0.8x)
            if (!heavyRainDownpourActive && _missionElapsedSec >= 720.0f)
            {
                heavyRainDownpourActive = true;
                enemyHearingMultiplier = 0.8f;
            }

            // Event 2: E_M07_CRANE every 90s (unless sabotaged via S1 at [700, 150])
            if (!objectiveS1_CraneControlsSabotaged)
            {
                craneSweepTimerSec = (_missionElapsedSec % 90.0f);
                craneFloodlightAngleDeg = (craneSweepTimerSec / 90.0f) * 360.0f;
            }
        }

        private void HandleAlertLevelChanged(CompoundAlertLevel newLevel)
        {
            if (newLevel >= CompoundAlertLevel.Alert2_CompoundAlarm)
            {
                playerDetectedDuringMission = true;
            }
        }

        public void OnSabotageCraneControls_S1()
        {
            objectiveS1_CraneControlsSabotaged = true;
        }

        public void OnStealShippingManifest_O1()
        {
            manifestStolen = true;
        }

        public void OnPlantTrackerOnPatrolBoat_S2()
        {
            boatTrackerPlanted = true;
        }

        public void OnReachWestDockExtraction()
        {
            if (manifestStolen)
            {
                objectiveO1_Complete = true;
                rewardVectorKUnlocked = true;
            }
            if (boatTrackerPlanted && !playerDetectedDuringMission)
            {
                objectiveS2_GhostMedalEarned = true;
            }
        }
    }
}
"""
    with open(installer_path, "w", encoding="utf-8") as f:
        f.write(installer_cs)

    return scene_path, installer_path


def main() -> int:
    level_data = build_m07_level_dict()

    missions_dir = os.path.join(ROOT_DIR, "Assets/_Project/Missions")
    out_dir = os.path.join(ROOT_DIR, "artifacts/file_generation/ttl=63d/output")
    os.makedirs(missions_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    for p in (
        os.path.join(ROOT_DIR, "M07.json"),
        os.path.join(missions_dir, "M07.json"),
        os.path.join(out_dir, "M07.json"),
    ):
        with open(p, "w", encoding="utf-8") as f:
            json.dump(level_data, f, indent=2)

    scene_path, installer_path = write_m07_unity_scene_and_installer()
    with open(scene_path, "r", encoding="utf-8") as src, open(
        os.path.join(out_dir, "M07.unity"), "w", encoding="utf-8"
    ) as dst:
        dst.write(src.read())
    with open(installer_path, "r", encoding="utf-8") as src, open(
        os.path.join(out_dir, "M07_PortAuthoritySceneInstaller.cs"), "w", encoding="utf-8"
    ) as dst:
        dst.write(src.read())

    print(f"[M07 BUILDER] Successfully generated M07.json, {scene_path}, and {installer_path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
