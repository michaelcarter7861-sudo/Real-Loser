#!/usr/bin/env python3
from pathlib import Path
"""
Project Real Loser — Mission 06 ("Sand and Steel" — Chapter 2) Handcrafted Builder
Target Engine: Unity 2022.3.40f1 LTS (URP, Android ARM64 IL2CPP)

Builds ONLY Mission 06 (`M06.json`, `Assets/_Project/Scenes/M06.unity`, and
`Assets/_Project/Scripts/Core/M06_SandAndSteelSceneInstaller.cs`):
- Map Size & Biome: 1000m x 900m (90.0 Hectares), Desert Biome, Daylight (`day`), Clear (`clear`).
- Exact Object Census Targets:
  - `196` structures
  - `1618` props
  - `912` cover
  - `66` vegetation
  - `18` lights
  - `40` hiding spots
  - `3` safe spots
  - `40` enemies (`22x E2`, `3x E3`, `2x E4`, `2x E5`, `4x E9`, `2x E10`, `3x E12`, `2x E13`)
  - `10` traps (`2x T1`, `2x T4`, `2x T6`, `2x T12`, `2x T13`)
  - `6` cameras (`M06_CAM_01` to `M06_CAM_06` linked to `M06_MON_01` in Zone D R2)
  - `3` alarms (`M06_ALM_01` in Zone D Control Shed, `M06_ALM_02` in Zone C2 Central Depot, `M06_ALM_03` in Zone F Barracks)
  - `43` pickups (including 3x C4 charges for Manifolds 1–3 and `Burst-18` `wpn_burst18` reward)
  - `1` event (`E_M06_BLAST`)
- Strict Exclusions ("KYA NAHI HOGA"):
  - NO `E1`, `E6`, `E7`, `E8`, `E11`, `E14`.
  - NO `T5`, `T7`, `T9`, `T10`, `T14`.
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


def interleave_for_zero_step_repeats(items: List[Dict[str, Any]], width: float = 1000.0, height: float = 900.0) -> List[Dict[str, Any]]:
    if len(items) <= 2:
        return items

    def get_xy(obj: Dict[str, Any]) -> Tuple[float, float]:
        p = obj.get("pos", obj.get("position", [0.0, 0.0]))
        return float(p[0]), float(p[1])

    n = len(items)
    # Use coprime stride 13 against 9 zones
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
    wall_type: str = "env_wall_adobe_4m",
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
            jitter = 0.025 * math.sin(k * 2.17 + (1.3 if edge_name in ("N", "E") else 0.6)) / float(count)
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


def build_m06_level_dict() -> Dict[str, Any]:
    # =========================================================================
    # 1. ZONES (9 Handcrafted Tactical Sectors on 1000m x 900m Desert Facility)
    # =========================================================================
    zones = [
        {
            "id": "ZONE_A",
            "name": "South Desert Dunes & Insertion",
            "zone_type": "wilderness",
            "rect": [0.0, 0.0, 1000.0, 200.0],
            "bounds": [0.0, 0.0, 1000.0, 200.0],
            "description": "Player Start Position at (480, 10) behind low desert rock ridges and palm clusters (env_tree_palm_a); approaches to outer adobe wall guarded by Buried Mines M06_T4_01 (415, 175) & M06_T4_02 (545, 185) and Tripwire Alarms M06_T1_01 (350, 195) & M06_T1_02 (620, 195).",
        },
        {
            "id": "ZONE_B",
            "name": "Outer Industrial Yard & Adobe Perimeter",
            "zone_type": "industrial",
            "rect": [150.0, 200.0, 850.0, 400.0],
            "bounds": [150.0, 200.0, 850.0, 400.0],
            "description": "Enclosed by connected 4m adobe walls (env_wall_adobe_4m) and metal watchtowers (env_watchtower_metal_a), patrolled by E2 Cobalt Grunts and E10 Scouts, monitored by exterior cameras M06_CAM_01 and M06_CAM_02.",
        },
        {
            "id": "ZONE_C1",
            "name": "West Fuel Depot — Manifold #1",
            "zone_type": "industrial",
            "rect": [200.0, 430.0, 330.0, 560.0],
            "bounds": [200.0, 430.0, 330.0, 560.0],
            "description": "High-voltage Electric Fence M06_T12_01 enclosing large fuel tanks (prop_fuel_tank_large) and Manifold #1 at (265, 490), guarded by E9 Technician #1 and Camera M06_CAM_03.",
        },
        {
            "id": "ZONE_C2",
            "name": "Central Fuel Depot — Manifold #2",
            "zone_type": "industrial",
            "rect": [430.0, 500.0, 570.0, 640.0],
            "bounds": [430.0, 500.0, 570.0, 640.0],
            "description": "Protected by Electric Fence M06_T12_02, Motion Sensor M06_T6_01, Heavy Gunner M06_E5_01, E9 Technician #2, Camera M06_CAM_04, and Manifold #2 at (500, 570).",
        },
        {
            "id": "ZONE_C3",
            "name": "East Fuel Depot — Manifold #3",
            "zone_type": "industrial",
            "rect": [700.0, 450.0, 840.0, 590.0],
            "bounds": [700.0, 450.0, 840.0, 590.0],
            "description": "Protected by Motion Sensor M06_T6_02, Heavy Gunner M06_E5_02, E9 Technician #3, Camera M06_CAM_05, and Manifold #3 at (770, 520).",
        },
        {
            "id": "ZONE_D",
            "name": "Central Command & Camera Control Shed",
            "zone_type": "camp",
            "rect": [380.0, 330.0, 620.0, 470.0],
            "bounds": [380.0, 330.0, 620.0, 470.0],
            "description": "Contains Radar Dish Dome (env_radar_dish_dome), Officer quarters (with 2 sector E3 Officers for S2), and Security Control Shed (R1, R2, R3 interior rooms) secured by Alarmed Doors M06_T13_01 & M06_T13_02, Camera M06_CAM_06, Monitor Terminal M06_MON_01 (S1), and T12 generator breaker.",
        },
        {
            "id": "ZONE_E",
            "name": "North Reserve Motor Pool",
            "zone_type": "perimeter",
            "rect": [460.0, 700.0, 540.0, 780.0],
            "bounds": [460.0, 700.0, 540.0, 780.0],
            "description": "Northern motor pool staging area supporting cargo vehicles and E13 vehicle crews.",
        },
        {
            "id": "ZONE_F",
            "name": "East Barracks Camp",
            "zone_type": "camp",
            "rect": [800.0, 200.0, 950.0, 330.0],
            "bounds": [800.0, 200.0, 950.0, 330.0],
            "description": "Eastern adobe garrison barracks compound housing reserve E2 Cobalt squads and Alarm Panel M06_ALM_03.",
        },
        {
            "id": "ZONE_G",
            "name": "North Reinforcement Road & East Extraction Corridor",
            "zone_type": "perimeter",
            "rect": [480.0, 820.0, 520.0, 900.0],
            "bounds": [480.0, 820.0, 520.0, 900.0],
            "description": "North highway approach where reinforcement truck spawns at (500, 880) (E_M06_BLAST), connected to East Extraction Road at (980, 600) (radius 10.0m).",
        },
    ]

    # =========================================================================
    # 2. STRUCTURES (Exact 196 Structures: 172 Snapped Wall/Fence/Gate + 24 Buildings/Towers/Depots)
    # =========================================================================
    structures: List[Dict[str, Any]] = []

    # --- 24 Major Buildings, Manifolds, Radar Dome, Watchtowers & Vehicles ---
    # 1. Zone D Security Control Shed ([480, 380, 520, 416]) with R1, R2, R3
    structures.append({
        "id": "M06_BLDG_CONTROL_SHED_D",
        "type": "env_bldg_guardhouse_a",
        "pos": [500.0, 398.0, 0.0],
        "bounds": [480.0, 380.0, 520.0, 416.0],
        "height": 4.2,
        "doorways": [
            [480.0, 398.0],
            [480.0, 405.8],
            [520.0, 398.0],
            [499.0, 380.0],
            [500.0, 380.0],
            [500.0, 416.0],
        ],
        "rooms": [
            {"id": "R1", "name": "Control Shed West Entry Vestibule", "bounds": [480.0, 380.0, 493.0, 416.0]},
            {"id": "R2", "name": "Camera Control Terminal (M06_MON_01) & Breaker Room", "bounds": [493.0, 380.0, 507.0, 416.0]},
            {"id": "R3", "name": "East Comms & Keycard Locker Room", "bounds": [507.0, 380.0, 520.0, 416.0]},
        ],
        "zone": "ZONE_D",
        "description": "Security Control Shed in Zone D secured by Alarmed Doors M06_T13_01 (480, 398) and M06_T13_02 (520, 398), housing M06_MON_01 (S1) and T12 generator breaker in R2.",
    })
    # 2. Zone D Officer Quarters ([400, 350, 440, 380])
    structures.append({
        "id": "M06_BLDG_OFFICER_QUARTERS_D",
        "type": "env_bldg_barracks_a",
        "pos": [420.0, 365.0, 0.0],
        "bounds": [400.0, 350.0, 440.0, 380.0],
        "height": 4.5,
        "doorways": [[420.0, 350.0], [420.0, 380.0], [400.0, 365.0], [440.0, 365.0]],
        "zone": "ZONE_D",
        "description": "Officer Quarters in Zone D housing the 2 sector E3 Radio Officers (S2).",
    })
    # 3. Zone D Radar Dish Dome
    structures.append({
        "id": "M06_RADAR_DOME_D",
        "type": "env_radar_dish_dome",
        "pos": [565.0, 425.0, 0.0],
        "zone": "ZONE_D",
        "description": "High-power desert radar dish dome in Zone D.",
    })
    # 4. Zone C1 Fuel Manifold #1 at [265.0, 490.0]
    structures.append({
        "id": "M06_MANIFOLD_01_C1",
        "type": "env_fuel_manifold_assembly_a",
        "pos": [265.0, 490.0, 0.0],
        "c4_target": True,
        "objective_id": "O1",
        "zone": "ZONE_C1",
        "description": "Primary Objective O1 Fuel Depot Manifold #1 at (265, 490) in West Depot (Zone C1).",
    })
    # 5. Zone C2 Fuel Manifold #2 at [500.0, 570.0]
    structures.append({
        "id": "M06_MANIFOLD_02_C2",
        "type": "env_fuel_manifold_assembly_a",
        "pos": [500.0, 570.0, 0.0],
        "c4_target": True,
        "objective_id": "O1",
        "zone": "ZONE_C2",
        "description": "Primary Objective O1 Fuel Depot Manifold #2 at (500, 570) in Central Depot (Zone C2).",
    })
    # 6. Zone C3 Fuel Manifold #3 at [770.0, 520.0]
    structures.append({
        "id": "M06_MANIFOLD_03_C3",
        "type": "env_fuel_manifold_assembly_a",
        "pos": [770.0, 520.0, 0.0],
        "c4_target": True,
        "objective_id": "O1",
        "zone": "ZONE_C3",
        "description": "Primary Objective O1 Fuel Depot Manifold #3 at (770, 520) in East Depot (Zone C3).",
    })
    # 7-12. 6x Metal Watchtowers across Zones B, C1, C2, C3, E, F
    watchtower_specs = [
        ("M06_WATCHTOWER_B_SW", [185.0, 225.0, 0.0], "ZONE_B"),
        ("M06_WATCHTOWER_B_SE", [815.0, 225.0, 0.0], "ZONE_B"),
        ("M06_WATCHTOWER_C1_W", [212.0, 545.0, 0.0], "ZONE_C1"),
        ("M06_WATCHTOWER_C2_N", [500.0, 628.0, 0.0], "ZONE_C2"),
        ("M06_WATCHTOWER_C3_E", [828.0, 520.0, 0.0], "ZONE_C3"),
        ("M06_WATCHTOWER_E_N",  [500.0, 765.0, 0.0], "ZONE_E"),
    ]
    for wtid, wtpos, wtzone in watchtower_specs:
        structures.append({
            "id": wtid,
            "type": "env_watchtower_metal_a",
            "pos": wtpos,
            "radius": 3.5,
            "height": 8.5,
            "has_ladder": True,
            "zone": wtzone,
        })
    # 13. Zone F East Barracks Building ([850, 240, 910, 280])
    structures.append({
        "id": "M06_BLDG_BARRACKS_F",
        "type": "env_bldg_barracks_a",
        "pos": [880.0, 260.0, 0.0],
        "bounds": [850.0, 240.0, 910.0, 280.0],
        "height": 4.2,
        "doorways": [[880.0, 240.0], [880.0, 280.0], [850.0, 260.0], [910.0, 260.0]],
        "zone": "ZONE_F",
    })
    # 14-19. 6x Large Fuel Tanks (`prop_fuel_tank_large`) in Depots C1, C2, C3
    fuel_tank_specs = [
        ("M06_FUEL_TANK_C1_A", [240.0, 475.0, 0.0], "ZONE_C1"),
        ("M06_FUEL_TANK_C1_B", [290.0, 505.0, 0.0], "ZONE_C1"),
        ("M06_FUEL_TANK_C2_A", [475.0, 555.0, 0.0], "ZONE_C2"),
        ("M06_FUEL_TANK_C2_B", [525.0, 585.0, 0.0], "ZONE_C2"),
        ("M06_FUEL_TANK_C3_A", [745.0, 505.0, 0.0], "ZONE_C3"),
        ("M06_FUEL_TANK_C3_B", [795.0, 535.0, 0.0], "ZONE_C3"),
    ]
    for ftid, ftpos, ftzone in fuel_tank_specs:
        structures.append({
            "id": ftid,
            "type": "prop_fuel_tank_large",
            "pos": ftpos,
            "zone": ftzone,
        })
    # 20-22. Motor Pool Shed & 2 Cargo Trucks in Zone E / Zone G
    structures.append({
        "id": "M06_MOTORPOOL_CANOPY_E",
        "type": "env_supply_carport_a",
        "pos": [500.0, 735.0, 0.0],
        "zone": "ZONE_E",
    })
    structures.append({
        "id": "M06_VEH_TRUCK_E01",
        "type": "veh_truck_cargo_a",
        "pos": [485.0, 742.0, 0.0],
        "zone": "ZONE_E",
    })
    structures.append({
        "id": "M06_VEH_REINFORCEMENT_G",
        "type": "veh_truck_cargo_a",
        "pos": [500.0, 880.0, 0.0],
        "zone": "ZONE_G",
        "spawned_by_event": "E_M06_BLAST",
    })
    # 23. East Ridge Detonation Overwatch Shelter (`[885.0, 560.0]`)
    structures.append({
        "id": "M06_EAST_RIDGE_OVERWATCH",
        "type": "env_camo_net_canopy_a",
        "pos": [885.0, 560.0, 0.0],
        "zone": "ZONE_C3",
    })
    # 24. East Extraction Road Point at [980.0, 600.0] (radius 10.0m)
    structures.append({
        "id": "M06_EXTRACTION_POINT_G",
        "type": "env_extraction_zone_marker_a",
        "pos": [980.0, 600.0, 0.0],
        "extraction_radius": 10.0,
        "zone": "ZONE_G",
        "description": "East Extraction Road at (980, 600) (radius 10.0m).",
    })

    # --- 172 Closed Perimeter Wall/Fence/Gate Segments ---
    # 1. Outer Adobe Compound Wall ([150, 200, 850, 700]) -> 64 segments
    structures.extend(
        make_closed_perimeter_loop(
            prefix="M06_OUTER_ADOBE",
            x_min=150.0,
            y_min=200.0,
            x_max=850.0,
            y_max=700.0,
            n_south=18,
            n_east=14,
            n_north=18,
            n_west=14,
            wall_type="env_wall_adobe_4m",
            gates={
                ("S", 5):  ("M06_GATE_OUTER_SW", "env_gate_sliding_6m"),
                ("S", 12): ("M06_GATE_OUTER_SE", "env_gate_sliding_6m"),
                ("N", 9):  ("M06_GATE_OUTER_N",  "env_gate_sliding_6m"),
                ("E", 8):  ("M06_GATE_OUTER_E",  "env_gate_sliding_6m"),
            },
        )
    )
    # 2. Zone C1 West Fuel Depot Fence ([200, 430, 330, 560]) -> 24 segments
    structures.extend(
        make_closed_perimeter_loop(
            prefix="M06_DEPOT_C1_FENCE",
            x_min=200.0,
            y_min=430.0,
            x_max=330.0,
            y_max=560.0,
            n_south=6,
            n_east=6,
            n_north=6,
            n_west=6,
            wall_type="env_fence_chainlink_4m",
            gates={
                ("S", 3): ("M06_GATE_C1_SOUTH", "env_gate_sliding_6m"),
                ("E", 3): ("M06_GATE_C1_EAST",  "env_gate_sliding_6m"),
            },
        )
    )
    # 3. Zone C2 Central Fuel Depot Fence ([430, 500, 570, 640]) -> 24 segments
    structures.extend(
        make_closed_perimeter_loop(
            prefix="M06_DEPOT_C2_FENCE",
            x_min=430.0,
            y_min=500.0,
            x_max=570.0,
            y_max=640.0,
            n_south=6,
            n_east=6,
            n_north=6,
            n_west=6,
            wall_type="env_fence_chainlink_4m",
            gates={
                ("S", 3): ("M06_GATE_C2_SOUTH", "env_gate_sliding_6m"),
                ("W", 3): ("M06_GATE_C2_WEST",  "env_gate_sliding_6m"),
                ("E", 3): ("M06_GATE_C2_EAST",  "env_gate_sliding_6m"),
            },
        )
    )
    # 4. Zone C3 East Fuel Depot Fence ([700, 450, 840, 590]) -> 24 segments
    structures.extend(
        make_closed_perimeter_loop(
            prefix="M06_DEPOT_C3_FENCE",
            x_min=700.0,
            y_min=450.0,
            x_max=840.0,
            y_max=590.0,
            n_south=6,
            n_east=6,
            n_north=6,
            n_west=6,
            wall_type="env_fence_chainlink_4m",
            gates={
                ("W", 3): ("M06_GATE_C3_WEST", "env_gate_sliding_6m"),
                ("E", 3): ("M06_GATE_C3_EAST", "env_gate_sliding_6m"),
            },
        )
    )
    # 5. Zone D Central Command Adobe Wall ([380, 330, 620, 470]) -> 20 segments
    structures.extend(
        make_closed_perimeter_loop(
            prefix="M06_CMD_D_ADOBE",
            x_min=380.0,
            y_min=330.0,
            x_max=620.0,
            y_max=470.0,
            n_south=6,
            n_east=4,
            n_north=6,
            n_west=4,
            wall_type="env_wall_adobe_4m",
            gates={
                ("S", 3): ("M06_GATE_CMD_D_SOUTH", "env_gate_sliding_6m"),
                ("N", 3): ("M06_GATE_CMD_D_NORTH", "env_gate_sliding_6m"),
            },
        )
    )
    # 6. Zone F East Barracks Adobe Compound ([800, 200, 950, 330]) -> 16 segments
    structures.extend(
        make_closed_perimeter_loop(
            prefix="M06_BARRACKS_F_ADOBE",
            x_min=800.0,
            y_min=200.0,
            x_max=950.0,
            y_max=330.0,
            n_south=5,
            n_east=3,
            n_north=5,
            n_west=3,
            wall_type="env_wall_adobe_4m",
            gates={
                ("W", 1): ("M06_GATE_BARRACKS_F_W", "env_gate_sliding_6m"),
                ("N", 2): ("M06_GATE_BARRACKS_F_N", "env_gate_sliding_6m"),
            },
        )
    )

    assert len(structures) == 196, f"Expected 196 structures, got {len(structures)}"
    structures = interleave_for_zero_step_repeats(structures)

    # =========================================================================
    # 3. TRAPS (Exact 10 Allowed Traps: 2x T1, 2x T4, 2x T6, 2x T12, 2x T13) & 6 CAMERAS
    # =========================================================================
    traps = [
        {
            "id": "M06_T1_01",
            "type": "T1",
            "name": "South-West Adobe Breach Approach Tripwire Alarm #1",
            "pos": [350.0, 195.0, 0.2],
            "zone": "ZONE_A",
            "noise_radius_m": 40.0,
            "counter": "Wire Cutters (2.0s) or step over",
        },
        {
            "id": "M06_T1_02",
            "type": "T1",
            "name": "South-East Adobe Gate Approach Tripwire Alarm #2",
            "pos": [620.0, 195.0, 0.2],
            "zone": "ZONE_A",
            "noise_radius_m": 40.0,
            "counter": "Wire Cutters (2.0s) or step over",
        },
        {
            "id": "M06_T4_01",
            "type": "T4",
            "name": "South Desert Dune Approach Buried Mine #1",
            "pos": [415.0, 175.0, -0.05],
            "zone": "ZONE_A",
            "damage": 130.0,
            "counter": "Prone crawl disarm (< 1.2 m/s) or Binoculars spot",
        },
        {
            "id": "M06_T4_02",
            "type": "T4",
            "name": "South-East Dune Trail Buried Mine #2",
            "pos": [545.0, 185.0, -0.05],
            "zone": "ZONE_A",
            "damage": 130.0,
            "counter": "Prone crawl disarm (< 1.2 m/s) or Binoculars spot",
        },
        {
            "id": "M06_T12_01",
            "type": "T12",
            "name": "Zone C1 West Fuel Depot High-Voltage Electric Fence #1",
            "pos": [200.0, 495.0, 0.0],
            "zone": "ZONE_C1",
            "power_source_id": "M06_PRP_BREAKER_T12",
            "counter": "Cut power at Zone D Control Shed breaker M06_PRP_BREAKER_T12 or cut unpowered section",
        },
        {
            "id": "M06_T12_02",
            "type": "T12",
            "name": "Zone C2 Central Fuel Depot High-Voltage Electric Fence #2",
            "pos": [430.0, 570.0, 0.0],
            "zone": "ZONE_C2",
            "power_source_id": "M06_PRP_GEN_DIESEL_D",
            "counter": "Disable Zone D diesel generator M06_PRP_GEN_DIESEL_D or breaker M06_PRP_BREAKER_T12",
        },
        {
            "id": "M06_T6_01",
            "type": "T6",
            "name": "Zone C2 Central Depot Manifold Motion Sensor #1",
            "pos": [492.0, 558.0, 1.4],
            "zone": "ZONE_C2",
            "trigger_speed_threshold_mps": 1.2,
            "range_m": 12.0,
            "counter": "Prone crawl (< 1.2 m/s) or EMP Grenade",
        },
        {
            "id": "M06_T6_02",
            "type": "T6",
            "name": "Zone C3 East Depot Manifold Motion Sensor #2",
            "pos": [762.0, 512.0, 1.4],
            "zone": "ZONE_C3",
            "trigger_speed_threshold_mps": 1.2,
            "range_m": 12.0,
            "counter": "Prone crawl (< 1.2 m/s) or EMP Grenade",
        },
        {
            "id": "M06_T13_01",
            "type": "T13",
            "name": "Zone D Security Control Shed West Alarmed Door #1",
            "pos": [480.0, 398.0, 0.0],
            "zone": "ZONE_D",
            "snapped_doorway": [480.0, 398.0],
            "counter": "Lockpick + Hack PDA disarm before opening",
        },
        {
            "id": "M06_T13_02",
            "type": "T13",
            "name": "Zone D Security Control Shed East Alarmed Door #2",
            "pos": [520.0, 398.0, 0.0],
            "zone": "ZONE_D",
            "snapped_doorway": [520.0, 398.0],
            "counter": "Lockpick + Hack PDA disarm before opening",
        },
    ]
    assert len(traps) == 10, f"Expected 10 traps, got {len(traps)}"

    cameras = [
        {
            "id": "M06_CAM_01",
            "type": "T11",
            "name": "Zone B South-West Adobe Gate Camera #1",
            "pos": [185.0, 224.0, 4.2],
            "zone": "ZONE_B",
            "mounted_on": "M06_WATCHTOWER_B_SW",
            "fov_deg": 70.0,
            "range_m": 35.0,
            "monitor_id": "M06_MON_01",
        },
        {
            "id": "M06_CAM_02",
            "type": "T11",
            "name": "Zone B South-East Adobe Gate Camera #2",
            "pos": [815.0, 224.0, 4.2],
            "zone": "ZONE_B",
            "mounted_on": "M06_WATCHTOWER_B_SE",
            "fov_deg": 70.0,
            "range_m": 35.0,
            "monitor_id": "M06_MON_01",
        },
        {
            "id": "M06_CAM_03",
            "type": "T11",
            "name": "Zone C1 West Fuel Depot Manifold Camera #3",
            "pos": [212.0, 544.0, 4.2],
            "zone": "ZONE_C1",
            "mounted_on": "M06_WATCHTOWER_C1_W",
            "fov_deg": 75.0,
            "range_m": 36.0,
            "monitor_id": "M06_MON_01",
        },
        {
            "id": "M06_CAM_04",
            "type": "T11",
            "name": "Zone C2 Central Fuel Depot Manifold Camera #4",
            "pos": [500.0, 627.0, 4.2],
            "zone": "ZONE_C2",
            "mounted_on": "M06_WATCHTOWER_C2_N",
            "fov_deg": 75.0,
            "range_m": 36.0,
            "monitor_id": "M06_MON_01",
        },
        {
            "id": "M06_CAM_05",
            "type": "T11",
            "name": "Zone C3 East Fuel Depot Manifold Camera #5",
            "pos": [828.0, 519.0, 4.2],
            "zone": "ZONE_C3",
            "mounted_on": "M06_WATCHTOWER_C3_E",
            "fov_deg": 75.0,
            "range_m": 36.0,
            "monitor_id": "M06_MON_01",
        },
        {
            "id": "M06_CAM_06",
            "type": "T11",
            "name": "Zone D Security Control Shed Exterior Camera #6",
            "pos": [500.0, 380.2, 3.6],
            "zone": "ZONE_D",
            "mounted_on": "M06_BLDG_CONTROL_SHED_D",
            "fov_deg": 70.0,
            "range_m": 35.0,
            "monitor_id": "M06_MON_01",
        },
    ]
    assert len(cameras) == 6, f"Expected 6 cameras, got {len(cameras)}"

    alarms = [
        {
            "id": "M06_ALM_01",
            "type": "prop_alarm_panel_a",
            "name": "Zone D Control Shed Master Alarm Panel #1",
            "pos": [496.0, 395.0, 1.3],
            "zone": "ZONE_D",
            "room": "R2",
        },
        {
            "id": "M06_ALM_02",
            "type": "prop_alarm_panel_a",
            "name": "Zone C2 Central Fuel Depot Alarm Panel #2",
            "pos": [504.0, 566.0, 1.3],
            "zone": "ZONE_C2",
        },
        {
            "id": "M06_ALM_03",
            "type": "prop_alarm_panel_a",
            "name": "Zone F East Barracks Alarm Panel #3",
            "pos": [878.0, 258.0, 1.3],
            "zone": "ZONE_F",
        },
    ]
    assert len(alarms) == 3

    safe_spots = [
        {
            "id": "M06_SAFE_01",
            "name": "South Desert Palm Oasis Defilade",
            "pos": [465.0, 42.0, 0.0],
            "radius": 5.0,
            "zone": "ZONE_A",
        },
        {
            "id": "M06_SAFE_02",
            "name": "West Yard Dry Wadi Culvert Safe Spot",
            "pos": [172.0, 395.0, 0.0],
            "radius": 4.5,
            "zone": "ZONE_B",
        },
        {
            "id": "M06_SAFE_03",
            "name": "East Ridge Detonation Overwatch Safe Spot (>50m from all Manifolds)",
            "pos": [885.0, 560.0, 0.0],
            "radius": 5.0,
            "zone": "ZONE_C3",
        },
    ]
    assert len(safe_spots) == 3

    # =========================================================================
    # 4. ENEMIES (Exact 40: 22x E2, 3x E3, 2x E4, 2x E5, 4x E9, 2x E10, 3x E12, 2x E13)
    # =========================================================================
    enemies: List[Dict[str, Any]] = []

    # --- 22x E2 Cobalt Grunts (wpn_ar5_mesh) ---
    e2_specs = [
        ("M06_E2_01", "Outer Yard SW Gate Patrol #1",       [215.0, 235.0, 0.0], "ZONE_B",  [[215.0, 235.0], [275.0, 235.0], [275.0, 285.0], [215.0, 285.0]]),
        ("M06_E2_02", "Outer Yard South-Central Patrol #2", [345.0, 228.0, 0.0], "ZONE_B",  [[345.0, 228.0], [415.0, 228.0], [415.0, 278.0], [345.0, 278.0]]),
        ("M06_E2_03", "Outer Yard Central Road Patrol #3",  [485.0, 242.0, 0.0], "ZONE_B",  [[485.0, 242.0], [555.0, 242.0], [555.0, 292.0], [485.0, 292.0]]),
        ("M06_E2_04", "Outer Yard SE Gate Patrol #4",       [635.0, 232.0, 0.0], "ZONE_B",  [[635.0, 232.0], [705.0, 232.0], [705.0, 282.0], [635.0, 282.0]]),
        ("M06_E2_05", "Outer Yard East Flank Patrol #5",    [745.0, 265.0, 0.0], "ZONE_B",  [[745.0, 265.0], [790.0, 265.0], [790.0, 325.0], [745.0, 325.0]]),
        ("M06_E2_06", "Outer Yard West Flank Patrol #6",    [175.0, 315.0, 0.0], "ZONE_B",  [[175.0, 315.0], [235.0, 315.0], [235.0, 375.0], [175.0, 375.0]]),
        ("M06_E2_07", "Zone C1 West Depot South Guard #7",  [225.0, 445.0, 0.0], "ZONE_C1", [[225.0, 445.0], [305.0, 445.0], [305.0, 472.0], [225.0, 472.0]]),
        ("M06_E2_08", "Zone C1 West Depot North Guard #8",  [225.0, 518.0, 0.0], "ZONE_C1", [[225.0, 518.0], [305.0, 518.0], [305.0, 548.0], [225.0, 548.0]]),
        ("M06_E2_09", "Zone C1 Exterior East Corridor #9",  [342.0, 465.0, 0.0], "ZONE_C1", [[342.0, 465.0], [372.0, 465.0], [372.0, 535.0], [342.0, 535.0]]),
        ("M06_E2_10", "Zone C2 Central Depot West Guard #10",[442.0, 515.0, 0.0],"ZONE_C2", [[442.0, 515.0], [472.0, 515.0], [472.0, 615.0], [442.0, 615.0]]),
        ("M06_E2_11", "Zone C2 Central Depot East Guard #11",[532.0, 515.0, 0.0],"ZONE_C2", [[532.0, 515.0], [558.0, 515.0], [558.0, 615.0], [532.0, 615.0]]),
        ("M06_E2_12", "Zone C2 Exterior South Approach #12",[465.0, 482.0, 0.0], "ZONE_C2", [[465.0, 482.0], [535.0, 482.0], [535.0, 496.0], [465.0, 496.0]]),
        ("M06_E2_13", "Zone C3 East Depot South Guard #13", [715.0, 465.0, 0.0], "ZONE_C3", [[715.0, 465.0], [815.0, 465.0], [815.0, 492.0], [715.0, 492.0]]),
        ("M06_E2_14", "Zone C3 East Depot North Guard #14", [715.0, 548.0, 0.0], "ZONE_C3", [[715.0, 548.0], [815.0, 548.0], [815.0, 578.0], [715.0, 578.0]]),
        ("M06_E2_15", "Zone C3 Exterior West Lane #15",     [645.0, 485.0, 0.0], "ZONE_C3", [[645.0, 485.0], [688.0, 485.0], [688.0, 555.0], [645.0, 555.0]]),
        ("M06_E2_16", "Zone D Command Courtyard West #16",  [392.0, 395.0, 0.0], "ZONE_D",  [[392.0, 395.0], [462.0, 395.0], [462.0, 452.0], [392.0, 452.0]]),
        ("M06_E2_17", "Zone D Radar Dome Perimeter #17",    [535.0, 355.0, 0.0], "ZONE_D",  [[535.0, 355.0], [605.0, 355.0], [605.0, 455.0], [535.0, 455.0]]),
        ("M06_E2_18", "Zone E North Motor Pool Guard #18",  [468.0, 712.0, 0.0], "ZONE_E",  [[468.0, 712.0], [532.0, 712.0], [532.0, 768.0], [468.0, 768.0]]),
        ("M06_E2_19", "Zone F East Barracks Yard #19",      [812.0, 212.0, 0.0], "ZONE_F",  [[812.0, 212.0], [842.0, 212.0], [842.0, 315.0], [812.0, 315.0]]),
        ("M06_E2_20", "Zone F East Barracks North #20",     [855.0, 295.0, 0.0], "ZONE_F",  [[855.0, 295.0], [938.0, 295.0], [938.0, 322.0], [855.0, 322.0]]),
        ("M06_E2_21", "Zone F East Barracks South #21",     [855.0, 212.0, 0.0], "ZONE_F",  [[855.0, 212.0], [938.0, 212.0], [938.0, 232.0], [855.0, 232.0]]),
        ("M06_E2_22", "Zone G East Extraction Road #22",    [915.0, 585.0, 0.0], "ZONE_G",  [[915.0, 585.0], [955.0, 585.0], [955.0, 625.0], [915.0, 625.0]]),
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

    # --- 3x E3 Radio Officers (wpn_p45_enforcer, radio: true) ---
    # 2 in Zone D Officer Quarters sector for Secondary Objective S2, 1 in Zone F Barracks
    e3_specs = [
        ("M06_E3_01", "Zone D Sector Officer #1 (S2 Target)", [412.0, 342.0, 0.0], "ZONE_D", True,  [[412.0, 342.0], [448.0, 342.0], [448.0, 348.0], [412.0, 348.0]]),
        ("M06_E3_02", "Zone D Sector Officer #2 (S2 Target)", [448.0, 386.0, 0.0], "ZONE_D", True,  [[448.0, 386.0], [472.0, 386.0], [472.0, 422.0], [448.0, 422.0]]),
        ("M06_E3_03", "Zone F East Garrison Comms Officer #3",[918.0, 255.0, 0.0], "ZONE_F", False, [[918.0, 255.0], [942.0, 255.0], [942.0, 288.0], [918.0, 288.0]]),
    ]
    for eid, ename, epos, ezone, is_s2, ewps in e3_specs:
        enemies.append({
            "id": eid,
            "class": "E3",
            "name": ename,
            "asset_id": "chr_enemy_e3_officer",
            "weapon": "wpn_p45_enforcer",
            "radio": True,
            "has_radio": True,
            "radio_checkin_interval_s": 45.0,
            "s2_sector_officer": is_s2,
            "pos": epos,
            "zone": ezone,
            "patrol_waypoints": ewps,
        })

    # --- 2x E4 Cobalt Elite (wpn_ar12_burst) guarding Zone D Command Complex ---
    e4_specs = [
        ("M06_E4_01", "Zone D Command Shed West Elite Guard #1", [468.0, 368.0, 0.0], "ZONE_D", [[468.0, 368.0], [476.0, 368.0], [476.0, 424.0], [468.0, 424.0]]),
        ("M06_E4_02", "Zone D Command Shed East Elite Guard #2", [524.0, 368.0, 0.0], "ZONE_D", [[524.0, 368.0], [534.0, 368.0], [534.0, 424.0], [524.0, 424.0]]),
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
            "pos": epos,
            "zone": ezone,
            "patrol_waypoints": ewps,
        })

    # --- 2x E5 Heavy Gunners (200 HP, heavy armor, wpn_lmg60_hammer, suppression fire) in C2 & C3 ---
    e5_specs = [
        ("M06_E5_01", "Zone C2 Central Depot Heavy Gunner #1", [508.0, 582.0, 0.0], "ZONE_C2", [[488.0, 582.0], [518.0, 582.0], [518.0, 608.0], [488.0, 608.0]]),
        ("M06_E5_02", "Zone C3 East Depot Heavy Gunner #2",    [778.0, 532.0, 0.0], "ZONE_C3", [[758.0, 532.0], [792.0, 532.0], [792.0, 558.0], [758.0, 558.0]]),
    ]
    for eid, ename, epos, ezone, ewps in e5_specs:
        enemies.append({
            "id": eid,
            "class": "E5",
            "name": ename,
            "asset_id": "chr_enemy_e7_heavy_gunner",
            "hp": 200,
            "armor": "heavy_armor",
            "weapon": "wpn_lmg60_hammer",
            "suppression_fire": True,
            "pos": epos,
            "zone": ezone,
            "patrol_waypoints": ewps,
        })

    # --- 4x E9 Technicians (wpn_p9_compact — repairs disabled cameras/lights & disarms planted C4 in 10s!) ---
    e9_specs = [
        ("M06_E9_01", "Zone C1 West Depot Technician #1 (C4 Disarm 10s)",    [258.0, 484.0, 0.0], "ZONE_C1", "M06_MANIFOLD_01_C1", [[252.0, 480.0], [278.0, 480.0], [278.0, 502.0], [252.0, 502.0]]),
        ("M06_E9_02", "Zone C2 Central Depot Technician #2 (C4 Disarm 10s)", [494.0, 564.0, 0.0], "ZONE_C2", "M06_MANIFOLD_02_C2", [[486.0, 560.0], [514.0, 560.0], [514.0, 578.0], [486.0, 578.0]]),
        ("M06_E9_03", "Zone C3 East Depot Technician #3 (C4 Disarm 10s)",    [764.0, 514.0, 0.0], "ZONE_C3", "M06_MANIFOLD_03_C3", [[756.0, 510.0], [784.0, 510.0], [784.0, 528.0], [756.0, 528.0]]),
        ("M06_E9_04", "Zone D Radar & Generator Technician #4",              [552.0, 418.0, 0.0], "ZONE_D",  "M06_PRP_BREAKER_T12",[[545.0, 412.0], [578.0, 412.0], [578.0, 442.0], [545.0, 442.0]]),
    ]
    for eid, ename, epos, ezone, target_id, ewps in e9_specs:
        enemies.append({
            "id": eid,
            "class": "E9",
            "name": ename,
            "asset_id": "chr_enemy_e9_technician",
            "weapon": "wpn_p9_compact",
            "repairs_cameras_and_lights": True,
            "disarms_planted_c4": True,
            "c4_disarm_time_sec": 10.0,
            "guarded_manifold_id": target_id,
            "pos": epos,
            "zone": ezone,
            "patrol_waypoints": ewps,
        })

    # --- 2x E10 Scouts (wpn_ar9_carbine + Binoculars, 60m vision) in Zone B ---
    e10_specs = [
        ("M06_E10_01", "Zone B West Desert Perimeter Scout #1", [295.0, 345.0, 0.0], "ZONE_B", [[295.0, 345.0], [355.0, 345.0], [355.0, 385.0], [295.0, 385.0]]),
        ("M06_E10_02", "Zone B East Desert Perimeter Scout #2", [645.0, 345.0, 0.0], "ZONE_B", [[645.0, 345.0], [715.0, 345.0], [715.0, 385.0], [645.0, 385.0]]),
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

    # --- 3x E12 Sentries (wpn_ar5_mesh) on Watchtowers ---
    e12_specs = [
        ("M06_E12_01", "Zone B SW Watchtower Sentry #1", [185.0, 225.0, 8.5], "ZONE_B",  [[184.0, 224.0], [186.0, 224.0], [186.0, 226.0], [184.0, 226.0]]),
        ("M06_E12_02", "Zone B SE Watchtower Sentry #2", [815.0, 225.0, 8.5], "ZONE_B",  [[814.0, 224.0], [816.0, 224.0], [816.0, 226.0], [814.0, 226.0]]),
        ("M06_E12_03", "Zone C2 North Watchtower Sentry #3",[500.0, 628.0, 8.5],"ZONE_C2",[[499.0, 627.0], [501.0, 627.0], [501.0, 629.0], [499.0, 629.0]]),
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

    # --- 2x E13 Vehicle Crew (wpn_ar9_carbine) in Zone E & Zone G ---
    e13_specs = [
        ("M06_E13_01", "Zone E Motor Pool Cargo Truck Crew #1", [482.0, 745.0, 0.0], "ZONE_E", [[482.0, 745.0], [494.0, 745.0], [494.0, 756.0], [482.0, 756.0]]),
        ("M06_E13_02", "Zone G North Reinforcement Truck Crew #2",[496.0, 875.0, 0.0],"ZONE_G", [[496.0, 875.0], [508.0, 875.0], [508.0, 888.0], [496.0, 888.0]]),
    ]
    for eid, ename, epos, ezone, ewps in e13_specs:
        enemies.append({
            "id": eid,
            "class": "E13",
            "name": ename,
            "asset_id": "chr_enemy_e13_ghillie_spotter",
            "weapon": "wpn_ar9_carbine",
            "pos": epos,
            "zone": ezone,
            "patrol_waypoints": ewps,
        })

    assert len(enemies) == 40, f"Expected 40 enemies, got {len(enemies)}"
    enemies = interleave_for_zero_step_repeats(enemies)

    # =========================================================================
    # 5. LIGHTS (Exact 18 Lights across Zones B, C1, C2, C3, D, E, F, G)
    # =========================================================================
    lights = [
        {"id": "M06_LGT_01", "type": "light_flood_gate_pole",    "pos": [185.0, 225.0, 7.5], "zone": "ZONE_B",  "range_m": 22.0},
        {"id": "M06_LGT_02", "type": "light_flood_gate_pole",    "pos": [350.0, 202.0, 6.5], "zone": "ZONE_B",  "range_m": 20.0},
        {"id": "M06_LGT_03", "type": "light_flood_gate_pole",    "pos": [620.0, 202.0, 6.5], "zone": "ZONE_B",  "range_m": 20.0},
        {"id": "M06_LGT_04", "type": "light_flood_gate_pole",    "pos": [815.0, 225.0, 7.5], "zone": "ZONE_B",  "range_m": 22.0},
        {"id": "M06_LGT_05", "type": "light_caged_bulb_warm",    "pos": [265.0, 490.0, 4.2], "zone": "ZONE_C1", "range_m": 16.0},
        {"id": "M06_LGT_06", "type": "light_flood_checkpoint",   "pos": [212.0, 545.0, 7.0], "zone": "ZONE_C1", "range_m": 22.0},
        {"id": "M06_LGT_07", "type": "light_caged_bulb_warm",    "pos": [500.0, 570.0, 4.2], "zone": "ZONE_C2", "range_m": 16.0},
        {"id": "M06_LGT_08", "type": "light_flood_checkpoint",   "pos": [500.0, 628.0, 7.0], "zone": "ZONE_C2", "range_m": 22.0},
        {"id": "M06_LGT_09", "type": "light_caged_bulb_warm",    "pos": [770.0, 520.0, 4.2], "zone": "ZONE_C3", "range_m": 16.0},
        {"id": "M06_LGT_10", "type": "light_flood_checkpoint",   "pos": [828.0, 520.0, 7.0], "zone": "ZONE_C3", "range_m": 22.0},
        {"id": "M06_LGT_11", "type": "light_fluorescent_tube",   "pos": [486.0, 398.0, 3.6], "zone": "ZONE_D",  "room": "R1", "range_m": 12.0},
        {"id": "M06_LGT_12", "type": "light_fluorescent_tube",   "pos": [500.0, 398.0, 3.6], "zone": "ZONE_D",  "room": "R2", "range_m": 12.0},
        {"id": "M06_LGT_13", "type": "light_fluorescent_tube",   "pos": [514.0, 398.0, 3.6], "zone": "ZONE_D",  "room": "R3", "range_m": 12.0},
        {"id": "M06_LGT_14", "type": "light_command_table_lamp", "pos": [420.0, 365.0, 3.5], "zone": "ZONE_D",  "range_m": 14.0},
        {"id": "M06_LGT_15", "type": "light_caged_bulb_warm",    "pos": [565.0, 425.0, 5.0], "zone": "ZONE_D",  "range_m": 18.0},
        {"id": "M06_LGT_16", "type": "light_flood_gate_pole",    "pos": [500.0, 765.0, 7.5], "zone": "ZONE_E",  "range_m": 22.0},
        {"id": "M06_LGT_17", "type": "light_tent_lantern_a",     "pos": [880.0, 260.0, 3.6], "zone": "ZONE_F",  "range_m": 15.0},
        {"id": "M06_LGT_18", "type": "light_extraction_beacon",  "pos": [980.0, 600.0, 4.0], "zone": "ZONE_G",  "range_m": 20.0},
    ]
    assert len(lights) == 18, f"Expected 18 lights, got {len(lights)}"

    # =========================================================================
    # 6. HIDING SPOTS (Exact 40 Hiding Spots across Zones A–G)
    # =========================================================================
    hide_zone_templates = [
        ("ZONE_A",  25.0,  20.0, 960.0, 180.0, "env_bush_stealth_a"),
        ("ZONE_B", 165.0, 215.0, 835.0, 390.0, "prop_dumpster_metal_a"),
        ("ZONE_C1",210.0, 440.0, 320.0, 550.0, "prop_locker_metal_a"),
        ("ZONE_C2",440.0, 510.0, 560.0, 630.0, "prop_locker_metal_a"),
        ("ZONE_C3",710.0, 460.0, 830.0, 580.0, "prop_locker_metal_a"),
        ("ZONE_D", 390.0, 340.0, 610.0, 460.0, "closet_storage_a"),
        ("ZONE_E", 468.0, 708.0, 532.0, 772.0, "prop_dumpster_metal_a"),
        ("ZONE_F", 810.0, 210.0, 940.0, 320.0, "prop_locker_metal_a"),
    ]
    hiding_spots: List[Dict[str, Any]] = []
    for i in range(1, 41):
        zname, x0, y0, x1, y1, htype = hide_zone_templates[i % len(hide_zone_templates)]
        u = vdc(i * 7 + 3, 2)
        v = vdc(i * 11 + 5, 3)
        hx = round(x0 + u * (x1 - x0), 2)
        hy = round(y0 + v * (y1 - y0), 2)
        hiding_spots.append({
            "id": f"M06_HIDE_{i:02d}",
            "type": htype,
            "pos": [hx, hy, 0.0],
            "zone": zname,
        })
    assert len(hiding_spots) == 40, f"Expected 40 hiding spots, got {len(hiding_spots)}"

    # =========================================================================
    # 7. PICKUPS (Exact 43 Pickups including 3x C4 Charges & Burst-18 Reward)
    # =========================================================================
    pickups: List[Dict[str, Any]] = [
        {"id": "M06_PKP_C4_MANIFOLD_01", "type": "pickup_explosive_c4",       "name": "C4 Demolition Pack #1 (West Depot Manifold O1)",    "pos": [262.0, 488.0, 0.9], "zone": "ZONE_C1"},
        {"id": "M06_PKP_C4_MANIFOLD_02", "type": "pickup_explosive_c4",       "name": "C4 Demolition Pack #2 (Central Depot Manifold O1)", "pos": [498.0, 568.0, 0.9], "zone": "ZONE_C2"},
        {"id": "M06_PKP_C4_MANIFOLD_03", "type": "pickup_explosive_c4",       "name": "C4 Demolition Pack #3 (East Depot Manifold O1)",    "pos": [768.0, 518.0, 0.9], "zone": "ZONE_C3"},
        {"id": "M06_PKP_REWARD_BURST18", "type": "pickup_reward_burst18",     "name": "Burst-18 Machine Pistol (wpn_burst18 — O1 Unlock)", "pos": [512.0, 402.0, 1.0], "zone": "ZONE_D", "room": "R3"},
        {"id": "M06_PKP_KEYCARD_SHED_D", "type": "pickup_keycard_command",    "name": "Zone D Security Control Shed Master Keycard",       "pos": [418.0, 362.0, 1.0], "zone": "ZONE_D"},
        {"id": "M06_PKP_HACK_PDA_D",     "type": "pickup_gadget_hack_pda",    "name": "Cryptographic Hack PDA",                            "pos": [488.0, 392.0, 1.0], "zone": "ZONE_D", "room": "R1"},
        {"id": "M06_PKP_EMP_01",         "type": "pickup_gadget_emp_grenade", "name": "EMP Grenade #1 (Motion Sensor Counter)",            "pos": [502.0, 404.0, 1.0], "zone": "ZONE_D", "room": "R2"},
        {"id": "M06_PKP_EMP_02",         "type": "pickup_gadget_emp_grenade", "name": "EMP Grenade #2 (Motion Sensor Counter)",            "pos": [692.0, 488.0, 0.9], "zone": "ZONE_C3"},
        {"id": "M06_PKP_WIRECUTTERS_A",  "type": "pickup_gadget_wirecutters", "name": "Insulated Heavy Wire Cutters",                      "pos": [472.0, 28.0,  0.8], "zone": "ZONE_A"},
        {"id": "M06_PKP_LOCKPICK_B",     "type": "pickup_gadget_lockpick",    "name": "Desert Field Lockpick Set",                         "pos": [348.0, 218.0, 0.8], "zone": "ZONE_B"},
    ]
    pickup_types_cycle = [
        ("pickup_ammo_556_box",      "5.56mm NATO Desert Crate"),
        ("pickup_ammo_9mm_box",      "9x19mm Subsonic Box"),
        ("pickup_medkit_field",      "Desert Trauma Medkit"),
        ("pickup_gadget_binoculars", "Long-Range Desert Binoculars"),
        ("pickup_ammo_sniper_box",   "7.62mm Heavy Belt Box"),
    ]
    pkp_zones = [
        ("ZONE_A",   40.0,  25.0, 920.0, 170.0),
        ("ZONE_B",  175.0, 215.0, 825.0, 385.0),
        ("ZONE_C1", 210.0, 440.0, 320.0, 550.0),
        ("ZONE_C2", 440.0, 510.0, 560.0, 630.0),
        ("ZONE_C3", 710.0, 460.0, 830.0, 580.0),
        ("ZONE_D",  390.0, 340.0, 610.0, 460.0),
        ("ZONE_E",  468.0, 708.0, 532.0, 772.0),
        ("ZONE_F",  812.0, 212.0, 938.0, 318.0),
    ]
    while len(pickups) < 43:
        idx = len(pickups) + 1
        zname, x0, y0, x1, y1 = pkp_zones[idx % len(pkp_zones)]
        ptype, pname = pickup_types_cycle[idx % len(pickup_types_cycle)]
        u = vdc(idx * 9 + 5, 2)
        v = vdc(idx * 13 + 7, 3)
        px = round(x0 + u * (x1 - x0), 2)
        py = round(y0 + v * (y1 - y0), 2)
        pickups.append({
            "id": f"M06_PKP_{idx:02d}",
            "type": ptype,
            "name": f"{pname} #{idx}",
            "pos": [px, py, 0.8],
            "zone": zname,
        })
    assert len(pickups) == 43, f"Expected 43 pickups, got {len(pickups)}"
    pickups = interleave_for_zero_step_repeats(pickups)

    # =========================================================================
    # 8. VEGETATION (Exact 66 Desert Palm Clusters & Scrub Bushes across Zones A, B, F, G)
    # =========================================================================
    veg_zones = [
        ("ZONE_A",  18.0,  12.0, 980.0, 188.0),
        ("ZONE_B", 160.0, 208.0, 840.0, 392.0),
        ("ZONE_F", 808.0, 208.0, 942.0, 322.0),
        ("ZONE_G", 860.0, 520.0, 990.0, 680.0),
    ]
    vegetation: List[Dict[str, Any]] = []
    for i in range(1, 67):
        zname, x0, y0, x1, y1 = veg_zones[i % len(veg_zones)]
        u = vdc(i * 5 + 7, 2)
        v = vdc(i * 11 + 3, 3)
        vx = round(x0 + u * (x1 - x0), 2)
        vy = round(y0 + v * (y1 - y0), 2)
        vtype = "env_tree_palm_a" if (i % 2 == 1) else "env_bush_stealth_a"
        vegetation.append({
            "id": f"M06_VEG_{i:02d}",
            "type": vtype,
            "pos": [vx, vy, 0.0],
            "zone": zname,
        })
    assert len(vegetation) == 66, f"Expected 66 vegetation items, got {len(vegetation)}"
    vegetation = interleave_for_zero_step_repeats(vegetation)

    # =========================================================================
    # 9. COVER (Exact 912 Handcrafted Desert Rock Ridges, Sandbags & Barriers)
    # =========================================================================
    cover_zones = [
        ("ZONE_A",   15.0,  14.0, 985.0, 190.0, ["env_rock_boulder_a", "prop_sandbag_wall_a", "prop_concrete_barrier_a"]),
        ("ZONE_B",  158.0, 208.0, 842.0, 394.0, ["prop_sandbag_wall_a", "prop_concrete_barrier_a", "prop_crate_military_a"]),
        ("ZONE_C1", 204.0, 434.0, 326.0, 556.0, ["prop_concrete_barrier_a", "prop_crate_metal_a", "prop_sandbag_wall_a"]),
        ("ZONE_C2", 434.0, 504.0, 566.0, 636.0, ["prop_concrete_barrier_a", "prop_sandbag_wall_a", "prop_crate_military_a"]),
        ("ZONE_C3", 704.0, 454.0, 836.0, 586.0, ["prop_concrete_barrier_a", "prop_crate_metal_a", "prop_sandbag_wall_a"]),
        ("ZONE_D",  386.0, 336.0, 614.0, 464.0, ["prop_sandbag_wall_a", "prop_concrete_barrier_a", "prop_crate_military_a"]),
        ("ZONE_E",  464.0, 704.0, 536.0, 776.0, ["prop_concrete_barrier_a", "prop_sandbag_wall_a", "prop_crate_metal_a"]),
        ("ZONE_F",  806.0, 206.0, 944.0, 324.0, ["prop_sandbag_wall_a", "prop_crate_military_a", "prop_concrete_barrier_a"]),
        ("ZONE_G",  484.0, 824.0, 975.0, 892.0, ["env_rock_boulder_a", "prop_concrete_barrier_a", "prop_sandbag_wall_a"]),
    ]
    cover: List[Dict[str, Any]] = []
    for i in range(1, 913):
        zname, x0, y0, x1, y1, ctypes = cover_zones[i % len(cover_zones)]
        u = vdc(i * 7 + 13, 2)
        v = vdc(i * 17 + 9, 3)
        cx = round(x0 + u * (x1 - x0), 2)
        cy = round(y0 + v * (y1 - y0), 2)
        cover.append({
            "id": f"M06_COV_{i:03d}",
            "type": ctypes[i % len(ctypes)],
            "pos": [cx, cy, 0.0],
            "zone": zname,
        })
    assert len(cover) == 912, f"Expected 912 cover pieces, got {len(cover)}"
    cover = interleave_for_zero_step_repeats(cover)

    # =========================================================================
    # 10. PROPS (Exact 1618 Props including M06_MON_01, T12 Breaker/Generator & 3 Alarms)
    # =========================================================================
    props: List[Dict[str, Any]] = [
        {
            "id": "M06_MON_01",
            "type": "prop_terminal_desk_a",
            "name": "Zone D R2 Security Control Shed Camera Monitor Terminal (S1 — Loops 6 Cameras for 60s)",
            "pos": [500.0, 398.0, 0.0],
            "zone": "ZONE_D",
            "room": "R2",
            "controls_camera_ids": ["M06_CAM_01", "M06_CAM_02", "M06_CAM_03", "M06_CAM_04", "M06_CAM_05", "M06_CAM_06"],
            "camera_loop_duration_sec": 60.0,
            "objective_id": "S1",
        },
        {
            "id": "M06_PRP_BREAKER_T12",
            "type": "prop_breaker_box_a",
            "name": "Zone D R2 Master Electric Fence Breaker Box (Powers M06_T12_01 & M06_T12_02)",
            "pos": [504.0, 401.0, 1.2],
            "zone": "ZONE_D",
            "room": "R2",
        },
        {
            "id": "M06_PRP_GEN_DIESEL_D",
            "type": "prop_generator_diesel_a",
            "name": "Zone D Auxiliary Diesel Generator (Powers M06_T12_02)",
            "pos": [526.0, 402.0, 0.0],
            "zone": "ZONE_D",
        },
        {
            "id": "M06_ALM_01",
            "type": "prop_alarm_panel_a",
            "name": "Zone D Control Shed Master Alarm Panel #1",
            "pos": [496.0, 395.0, 1.3],
            "zone": "ZONE_D",
            "room": "R2",
        },
        {
            "id": "M06_ALM_02",
            "type": "prop_alarm_panel_a",
            "name": "Zone C2 Central Fuel Depot Alarm Panel #2",
            "pos": [504.0, 566.0, 1.3],
            "zone": "ZONE_C2",
        },
        {
            "id": "M06_ALM_03",
            "type": "prop_alarm_panel_a",
            "name": "Zone F East Barracks Alarm Panel #3",
            "pos": [878.0, 258.0, 1.3],
            "zone": "ZONE_F",
        },
    ]

    prop_catalog = [
        "prop_fuel_tank_large",
        "prop_fuel_drum_metal_a",
        "prop_ammo_crate_wood_a",
        "prop_crate_military_a",
        "prop_crate_metal_a",
        "prop_concrete_barrier_a",
        "prop_sandbag_wall_a",
        "prop_generator_diesel_a",
        "prop_breaker_box_a",
        "prop_cable_spool_wood_a",
        "prop_radio_field_desk_a",
        "prop_workbench_tools_a",
        "prop_water_jerrycan_a",
        "prop_locker_metal_a",
        "prop_dumpster_metal_a",
        "prop_weapon_rack_empty_a",
    ]
    prop_zones = [
        ("ZONE_A",   20.0,  16.0, 980.0, 188.0),
        ("ZONE_B",  160.0, 210.0, 840.0, 392.0),
        ("ZONE_C1", 206.0, 436.0, 324.0, 554.0),
        ("ZONE_C2", 436.0, 506.0, 564.0, 634.0),
        ("ZONE_C3", 706.0, 456.0, 834.0, 584.0),
        ("ZONE_D",  388.0, 338.0, 612.0, 462.0),
        ("ZONE_E",  466.0, 706.0, 534.0, 774.0),
        ("ZONE_F",  808.0, 208.0, 942.0, 322.0),
        ("ZONE_G",  484.0, 824.0, 976.0, 892.0),
    ]

    while len(props) < 1618:
        idx = len(props) + 1
        zname, x0, y0, x1, y1 = prop_zones[idx % len(prop_zones)]
        u = vdc(idx * 11 + 3, 2)
        v = vdc(idx * 19 + 7, 5)
        px = round(x0 + u * (x1 - x0), 2)
        py = round(y0 + v * (y1 - y0), 2)
        props.append({
            "id": f"M06_PRP_{idx:04d}",
            "type": prop_catalog[idx % len(prop_catalog)],
            "pos": [px, py, 0.0],
            "zone": zname,
        })

    assert len(props) == 1618, f"Expected 1618 props, got {len(props)}"
    props = interleave_for_zero_step_repeats(props)

    # =========================================================================
    # 11. DYNAMIC MISSION EVENT (Exact 1 Event: E_M06_BLAST)
    # =========================================================================
    events = [
        {
            "id": "E_M06_BLAST",
            "trigger": "depot_2_detonated_first and alert_level < 2",
            "condition": {
                "type": "FirstManifoldDetonatedUnderAlert2",
                "manifold_id": "M06_MANIFOLD_02_C2",
                "manifold_pos": [500.0, 570.0],
                "max_alert_exclusive": 2,
            },
            "action": "spawn:reinforcement_truck_500_880",
            "spawn_pos": [500.0, 880.0, 0.0],
            "spawn_vehicle": "veh_truck_cargo_a",
            "description": "If Depot 2 (500, 570) is detonated first while alert < 2, a reinforcement cargo truck spawns at (500, 880).",
        }
    ]
    assert len(events) == 1

    # =========================================================================
    # 12. OBJECTIVES (O1, S1, S2) & 3 COMPLETE 6-WAYPOINT TACTICAL ROUTES
    # =========================================================================
    objectives = {
        "primary": [
            {
                "id": "O1",
                "title": "Plant C4 on all 3 depot manifolds ((265,490), (500,570), (770,520)) & detonate from >50m away",
                "manifolds": [
                    {"id": "M06_MANIFOLD_01_C1", "pos": [265.0, 490.0, 0.0], "zone": "ZONE_C1"},
                    {"id": "M06_MANIFOLD_02_C2", "pos": [500.0, 570.0, 0.0], "zone": "ZONE_C2"},
                    {"id": "M06_MANIFOLD_03_C3", "pos": [770.0, 520.0, 0.0], "zone": "ZONE_C3"},
                ],
                "min_safe_detonation_distance_m": 50.0,
                "e9_technician_disarm_window_sec": 10.0,
                "unlock_reward": "Burst-18",
                "unlock_weapon_id": "wpn_burst18",
            }
        ],
        "secondary": [
            {
                "id": "S1",
                "title": "Hack control shed terminal in Zone D to loop all 6 cameras for 60s",
                "target_id": "M06_MON_01",
                "target_pos": [500.0, 398.0, 0.0],
                "loop_duration_sec": 60.0,
                "zone": "ZONE_D",
            },
            {
                "id": "S2",
                "title": "Eliminate both sector officers silently (Ghost Medal)",
                "target_enemies": ["M06_E3_01", "M06_E3_02"],
                "require_silent": True,
                "medal_reward": "Ghost Medal",
            },
        ],
        "extraction": {
            "id": "EXT_M06",
            "title": "Extract at East Extraction Road (980, 600)",
            "pos": [980.0, 600.0, 0.0],
            "radius": 10.0,
            "zone": "ZONE_G",
        },
    }

    routes = {
        "silent": {
            "name": "Silent Route (Prone Disarm T4 Mine, Unpowered Fence Cut, Silent E9 Elimination & >50m Ridge Detonation)",
            "description": "Crawl prone from (480, 10) to disarm Buried Mine M06_T4_01 at (415, 175), cut unpowered West fence section into Zone C1 to silently eliminate E9 Technician #1 and plant C4 on Manifold #1 (265, 490), eliminate E9 Technicians #2 & #3 while planting C4 on Manifold #2 (500, 570) and Manifold #3 (770, 520), detonate remotely from >50m away on the East Extraction Road, and extract at (980, 600).",
            "waypoints": [
                [480.0, 10.0],
                [415.0, 175.0],
                [265.0, 490.0],
                [500.0, 570.0],
                [770.0, 520.0],
                [980.0, 600.0],
            ],
        },
        "technical": {
            "name": "Technical Route (Disarm T13 Alarmed Door, Loop 6 Cameras 60s, Cut T12 Power & EMP T6 Sensors)",
            "description": "Advance from (480, 10) into Zone D Security Control Shed (500, 398) by picking/hacking T13 Alarmed Door, hack terminal M06_MON_01 to loop all 6 cameras for 60s (S1) and cut T12 Electric Fence power at M06_PRP_BREAKER_T12, plant C4 on Manifold #1 (265, 490), EMP Motion Sensors M06_T6_01 & M06_T6_02 to plant C4 on Manifold #2 (500, 570) and Manifold #3 (770, 520), and extract at (980, 600).",
            "waypoints": [
                [480.0, 10.0],
                [500.0, 398.0],
                [265.0, 490.0],
                [500.0, 570.0],
                [770.0, 520.0],
                [980.0, 600.0],
            ],
        },
        "loud": {
            "name": "Loud Route (Snipe Sector E3 Officers, Engage E5 Heavy Gunners & Blast All 3 Manifolds)",
            "description": "Advance from (480, 10) to overwatch outside Zone D Officer Quarters (390, 345) to eliminate both sector E3 Officers, assault West Depot Manifold #1 (265, 490), engage Heavy Gunners M06_E5_01 & M06_E5_02 from cover to plant and detonate C4 on Manifold #2 (500, 570) and Manifold #3 (770, 520), and exfiltrate to (980, 600).",
            "waypoints": [
                [480.0, 10.0],
                [390.0, 345.0],
                [265.0, 490.0],
                [500.0, 570.0],
                [770.0, 520.0],
                [980.0, 600.0],
            ],
        },
    }

    level_dict = {
        "mission_id": "M06",
        "title": "Sand and Steel",
        "chapter": 2,
        "scene_name": "M06",
        "width": 1000.0,
        "height": 900.0,
        "area_hectares": 90.0,
        "biome": "desert",
        "time_of_day": "day",
        "weather": "clear",
        "player_start": {
            "pos": [480.0, 10.0, 0.0],
            "facing_deg": 0.0,
            "facing_cardinal": "North",
            "starting_loadout": ["wpn_usp45_suppressed", "wpn_m4a1_sopmod", "wpn_knife_mesh", "C4Charge_x3", "WireCutters", "HackPDA", "EMPGrenade_x2", "Lockpick"],
        },
        "strict_exclusions_enforced": {
            "forbidden_enemies": ["E1", "E6", "E7", "E8", "E11", "E14"],
            "forbidden_traps": ["T2", "T3", "T5", "T7", "T8", "T9", "T10", "T14", "T15", "T16"],
            "allowed_traps_only": ["T1", "T4", "T6", "T12", "T13"],
            "security_cameras_count": 6,
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


def write_m06_unity_scene_and_installer() -> Tuple[str, str]:
    scenes_dir = os.path.join(ROOT_DIR, "Assets/_Project/Scenes")
    scripts_dir = os.path.join(ROOT_DIR, "Assets/_Project/Scripts/Core")
    os.makedirs(scenes_dir, exist_ok=True)
    os.makedirs(scripts_dir, exist_ok=True)

    scene_path = os.path.join(scenes_dir, "M06.unity")
    installer_path = os.path.join(scripts_dir, "M06_SandAndSteelSceneInstaller.cs")

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
  m_FogColor: {r: 0.88, g: 0.78, b: 0.62, a: 1}
  m_FogMode: 3
  m_FogDensity: 0.0022
  m_AmbientMode: 0
  m_AmbientSkyColor: {r: 0.85, g: 0.76, b: 0.60, a: 1}
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
  m_Name: M06_SandAndSteel_MissionRoot
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
  m_Script: {fileID: 11500000, guid: f60718293a4b5c6d7e8f90a1b2c3d4e5, type: 3}
  m_Name: 
  m_EditorClassIdentifier: RealLoserStudio.Tactical.Core.M06_SandAndSteelSceneInstaller
  missionJsonPath: Assets/_Project/Missions/M06.json
  enforceStrictM06Exclusions: 1
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
    /// Scene Bootstrapper & Runtime Controller for Mission 06 ("Sand and Steel" — Chapter 2).
    /// Manages the 9-Zone 1000x900m (90.0 Hectares) Desert Fuel & Munitions Facility,
    /// 40 Enemies (22x E2, 3x E3, 2x E4, 2x E5 Heavy Gunner, 4x E9 Technician with 10s C4 disarm,
    /// 2x E10, 3x E12, 2x E13), 10 Traps (2x T1, 2x T4, 2x T6, 2x T12, 2x T13), 6 Cameras,
    /// and Dynamic Event E_M06_BLAST.
    /// </summary>
    public class M06_SandAndSteelSceneInstaller : MonoBehaviour
    {
        [Header("Mission 06 Blueprint Binding")]
        public string missionJsonPath = "Assets/_Project/Missions/M06.json";
        public bool enforceStrictM06Exclusions = true;

        [Header("Core System References")]
        public PlayerTacticalController playerController;
        public StealthAndDetectionSystem stealthSystem;
        public MissionEventAndStreamingSystem streamingSystem;
        public MobileTouchHUDAndMEMap touchHudMap;

        [Header("Primary Objective O1 — 3 Fuel Depot Manifolds & >50m Detonation")]
        public Vector3 manifold1Pos = new Vector3(265.0f, 0.0f, 490.0f);
        public Vector3 manifold2Pos = new Vector3(500.0f, 0.0f, 570.0f);
        public Vector3 manifold3Pos = new Vector3(770.0f, 0.0f, 520.0f);
        public bool c4PlantedManifold1;
        public bool c4PlantedManifold2;
        public bool c4PlantedManifold3;
        public bool objectiveO1_Complete;
        public bool rewardBurst18Unlocked;

        [Header("E9 Technician 10s C4 Disarm Timers")]
        public bool e9Tech1Alive = true;
        public bool e9Tech2Alive = true;
        public bool e9Tech3Alive = true;
        public float c4DisarmTimerM1;
        public float c4DisarmTimerM2;
        public float c4DisarmTimerM3;

        [Header("Secondary Objectives (S1, S2) & Dynamic Event (E_M06_BLAST)")]
        public List<TrapAndHazardSystem> facilityCameras = new List<TrapAndHazardSystem>();
        public float cameraLoopRemainingSec;
        public bool objectiveS1_CamerasLooped60s;
        public bool officer1EliminatedSilently;
        public bool officer2EliminatedSilently;
        public bool objectiveS2_GhostMedalEarned;
        public bool eventBlastReinforcementSpawned;

        private void Start()
        {
            InitializeMission06();
        }

        public void InitializeMission06()
        {
            if (playerController != null)
            {
                // Spawn at Zone A South Desert Dunes [480.0, 10.0] facing North (0 deg)
                playerController.transform.position = new Vector3(480.0f, 0.0f, 10.0f);
                playerController.transform.rotation = Quaternion.Euler(0f, 0f, 0f);
            }
        }

        private void Update()
        {
            float dt = Time.deltaTime;

            // S1 Camera 60s Loop Countdown
            if (cameraLoopRemainingSec > 0f)
            {
                cameraLoopRemainingSec = Mathf.Max(0f, cameraLoopRemainingSec - dt);
                if (cameraLoopRemainingSec == 0f)
                {
                    SetAllCamerasArmed(true);
                }
            }

            // E9 Technician 10s C4 Disarm Mechanic if alive & alerted near manifold
            if (c4PlantedManifold1 && e9Tech1Alive)
            {
                c4DisarmTimerM1 += dt;
                if (c4DisarmTimerM1 >= 10.0f) { c4PlantedManifold1 = false; c4DisarmTimerM1 = 0f; }
            }
            if (c4PlantedManifold2 && e9Tech2Alive)
            {
                c4DisarmTimerM2 += dt;
                if (c4DisarmTimerM2 >= 10.0f) { c4PlantedManifold2 = false; c4DisarmTimerM2 = 0f; }
            }
            if (c4PlantedManifold3 && e9Tech3Alive)
            {
                c4DisarmTimerM3 += dt;
                if (c4DisarmTimerM3 >= 10.0f) { c4PlantedManifold3 = false; c4DisarmTimerM3 = 0f; }
            }
        }

        public void OnHackControlShedTerminal_M06_MON_01()
        {
            objectiveS1_CamerasLooped60s = true;
            cameraLoopRemainingSec = 60.0f;
            SetAllCamerasArmed(false);
        }

        private void SetAllCamerasArmed(bool armed)
        {
            for (int i = 0; i < facilityCameras.Count; i++)
            {
                if (facilityCameras[i] != null)
                {
                    facilityCameras[i].isArmed = armed;
                }
            }
        }

        public void OnPlantC4OnManifold(int manifoldIndex)
        {
            if (manifoldIndex == 1) { c4PlantedManifold1 = true; c4DisarmTimerM1 = 0f; }
            if (manifoldIndex == 2) { c4PlantedManifold2 = true; c4DisarmTimerM2 = 0f; }
            if (manifoldIndex == 3) { c4PlantedManifold3 = true; c4DisarmTimerM3 = 0f; }
        }

        public bool TryDetonateAllManifoldsFromSafeDistance(Vector3 playerWorldPos, int currentAlertLevel, bool depot2DetonatedFirst)
        {
            // E_M06_BLAST: If Depot 2 (500, 570) is detonated first while alert < 2, spawn reinforcement truck at (500, 880)
            if (depot2DetonatedFirst && currentAlertLevel < 2 && !eventBlastReinforcementSpawned)
            {
                eventBlastReinforcementSpawned = true;
            }

            if (!c4PlantedManifold1 || !c4PlantedManifold2 || !c4PlantedManifold3)
            {
                return false;
            }

            float d1 = Vector3.Distance(playerWorldPos, manifold1Pos);
            float d2 = Vector3.Distance(playerWorldPos, manifold2Pos);
            float d3 = Vector3.Distance(playerWorldPos, manifold3Pos);

            if (d1 > 50.0f && d2 > 50.0f && d3 > 50.0f)
            {
                objectiveO1_Complete = true;
                rewardBurst18Unlocked = true;
                return true;
            }
            return false;
        }

        public void OnSectorOfficerEliminatedSilently(int officerIndex)
        {
            if (officerIndex == 1) officer1EliminatedSilently = true;
            if (officerIndex == 2) officer2EliminatedSilently = true;
            if (officer1EliminatedSilently && officer2EliminatedSilently)
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
    level_data = build_m06_level_dict()

    missions_dir = os.path.join(ROOT_DIR, "Assets/_Project/Missions")
    out_dir = os.path.join(ROOT_DIR, "artifacts/file_generation/ttl=63d/output")
    os.makedirs(missions_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    for p in (
        os.path.join(ROOT_DIR, "M06.json"),
        os.path.join(missions_dir, "M06.json"),
        os.path.join(out_dir, "M06.json"),
    ):
        with open(p, "w", encoding="utf-8") as f:
            json.dump(level_data, f, indent=2)

    scene_path, installer_path = write_m06_unity_scene_and_installer()
    with open(scene_path, "r", encoding="utf-8") as src, open(
        os.path.join(out_dir, "M06.unity"), "w", encoding="utf-8"
    ) as dst:
        dst.write(src.read())
    with open(installer_path, "r", encoding="utf-8") as src, open(
        os.path.join(out_dir, "M06_SandAndSteelSceneInstaller.cs"), "w", encoding="utf-8"
    ) as dst:
        dst.write(src.read())

    print(f"[M06 BUILDER] Successfully generated M06.json, {scene_path}, and {installer_path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
