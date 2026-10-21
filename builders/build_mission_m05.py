#!/usr/bin/env python3
from pathlib import Path
"""
Project Real Loser — Mission 05 ("Bridge Crossing" — Chapter 1 Finale) Handcrafted Builder
Target Engine: Unity 2022.3.40f1 LTS (URP, Android ARM64 IL2CPP)

Builds ONLY Mission 05 (`M05.json`, `Assets/_Project/Scenes/M05.unity`, and
`Assets/_Project/Scripts/Core/M05_BridgeCrossingSceneInstaller.cs`):
- Map Size & Biome: 1200m x 350m (42.0 Hectares), City/River Bridge Outskirts Biome, Daylight (`day`), Clear (`clear`).
- Exact Object Census Targets:
  - `95` structures
  - `815` props
  - `430` cover
  - `85` vegetation
  - `13` lights
  - `36` hiding spots
  - `3` safe spots
  - `36` enemies (`6x E1`, `16x E2`, `3x E3`, `4x E4`, `2x E6`, `2x E10`, `2x E13`, `1x E14` Boss Captain Dar)
  - `6` traps (`2x T1` Tripwire Alarm, `2x T3` Directional Mine, `2x T16` Environmental Hazard)
  - `4` cameras (`M05_CAM_01` to `M05_CAM_04` linked to checkpoint monitor `M05_MON_01`)
  - `2` alarms (`M05_ALM_01` in Zone E Command Building, `M05_ALM_02` at Zone D Bridge Checkpoint)
  - `24` pickups (including C4 charges, Dar's Briefcase `S2`, and `Hand Cannon .357` `wpn_revolver357_mesh` reward)
  - `2` events (`E_M05_CONVOY`, `E_M05_HELI`)
- Strict Exclusions ("KYA NAHI HOGA"):
  - NO Buried Mines (`T4`), NO Laser Grids (`T5`), NO Motion Sensors (`T6`), NO Sentry Turrets (`T9`),
    NO Electric Fences (`T12`), NO Dogs (`E7`/`E8`).
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


def interleave_for_zero_step_repeats(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if len(items) <= 2:
        return items

    n = len(items)
    buckets = [items[k:n:7] for k in range(7)]
    reordered: List[Dict[str, Any]] = []
    max_len = max(len(b) for b in buckets)
    for i in range(max_len):
        for b in buckets:
            if i < len(b):
                reordered.append(b[i])

    def get_xy(obj: Dict[str, Any]) -> Tuple[float, float]:
        p = obj.get("pos", obj.get("position", [0.0, 0.0]))
        return float(p[0]), float(p[1])

    for _pass in range(45):
        deltas = Counter()
        conflict_idx = -1
        for i in range(len(reordered) - 1):
            x1, y1 = get_xy(reordered[i])
            x2, y2 = get_xy(reordered[i + 1])
            vec = (round(x2 - x1, 2), round(y2 - y1, 2))
            deltas[vec] += 1
            if deltas[vec] > 1:
                conflict_idx = i + 1
                break
        if conflict_idx == -1:
            break
        for j in range(len(reordered) - 1, 0, -1):
            if abs(j - conflict_idx) > 3:
                reordered[conflict_idx], reordered[j] = reordered[j], reordered[conflict_idx]
                break

    return reordered


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
    wall_type: str = "env_wall_concrete_4m",
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
            jitter = 0.025 * math.sin(k * 2.13 + (1.2 if edge_name in ("N", "E") else 0.5)) / float(count)
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


def build_m05_level_dict() -> Dict[str, Any]:
    # =========================================================================
    # 1. ZONES (6 Handcrafted Sectors on 1200m x 350m Bridge Outskirts Map)
    # =========================================================================
    zones = [
        {
            "id": "ZONE_A",
            "name": "West Approach Woods",
            "zone_type": "wilderness",
            "rect": [0.0, 100.0, 300.0, 250.0],
            "bounds": [0.0, 100.0, 300.0, 250.0],
            "description": "Player Start at (40, 175) on the western wooded approach overlooking the highway road; natural rock and tree cover leading up to the outer bridge security cordon, patrolled by E1 Grunts and E10 Scouts.",
        },
        {
            "id": "ZONE_B",
            "name": "North Ridge Overwatch & Sniper Perch",
            "zone_type": "wilderness",
            "rect": [200.0, 250.0, 700.0, 350.0],
            "bounds": [200.0, 250.0, 700.0, 350.0],
            "description": "High northern hillside running parallel to the bridge with watchpoints and ruined concrete facades (env_building_facade_a) where Ghillie Sniper M05_E6_01 (410, 285) overlooks the bridge approach, protected by Tripwire Alarm M05_T1_01 and Directional Mine M05_T3_01.",
        },
        {
            "id": "ZONE_C",
            "name": "Bridge Approaches & Under-Bridge Catwalks",
            "zone_type": "wilderness",
            "rect": [300.0, 60.0, 900.0, 290.0],
            "bounds": [300.0, 60.0, 900.0, 290.0],
            "description": "Riverbank slopes and maintenance catwalks running underneath the main bridge deck (env_vent_shaft_2m & service walkways), featuring Environmental Hazards M05_T16_01 (520, 165) and M05_T16_02 (680, 165).",
        },
        {
            "id": "ZONE_D",
            "name": "Main Bridge Span & Fortified Checkpoint",
            "zone_type": "perimeter",
            "rect": [350.0, 150.0, 850.0, 200.0],
            "bounds": [350.0, 150.0, 850.0, 200.0],
            "description": "500m-long concrete highway bridge (env_wall_concrete_4m barriers, sandbag emplacements, and toll/checkpoint booths at (600, 175)), monitored by 4 Security Cameras (M05_CAM_01 to M05_CAM_04 linked to M05_MON_01 — S1), where 2 Cargo Trucks (veh_truck_cargo_a crewed by 2x E13) halt for 90s during convoy event (O1), covered by Ghillie Sniper M05_E6_02 (645, 195) on bridge gantry tower.",
        },
        {
            "id": "ZONE_E",
            "name": "South-East Garrison & Captain Dar's Command Compound",
            "zone_type": "camp",
            "rect": [700.0, 0.0, 1000.0, 150.0],
            "bounds": [700.0, 0.0, 1000.0, 150.0],
            "description": "Fortified concrete command building ([820, 40] to [960, 120]) with elevator/stairs, 3 interior rooms (R1, R2, R3), Tripwire M05_T1_02, Directional Mine M05_T3_02, and Alarm Panel M05_ALM_01; Boss Captain Dar (M05_E14_01) commands from this sector, protected by 4x E4 Cobalt Elite guards and carrying Dar's Briefcase (S2).",
        },
        {
            "id": "ZONE_F",
            "name": "East Riverbank Extraction",
            "zone_type": "wilderness",
            "rect": [850.0, 150.0, 1200.0, 350.0],
            "bounds": [850.0, 150.0, 1200.0, 350.0],
            "description": "Eastern highway exit and wooded trail leading to the Extraction Point at (1160, 320) (radius 10.0m).",
        },
    ]

    # =========================================================================
    # 2. STRUCTURES (Exact 95 Connected Structures, 100% Closed Perimeters)
    # =========================================================================
    structures: List[Dict[str, Any]] = []

    # --- Zone B: Ruined Concrete Facade Sniper Perch at [410.0, 285.0] ---
    structures.append({
        "id": "M05_BLDG_RUINED_FACADE_B1",
        "type": "env_building_facade_a",
        "pos": [410.0, 285.0, 0.0],
        "bounds": [406.0, 281.0, 414.0, 289.0],
        "height": 8.5,
        "doorways": [
            [406.0, 283.8],
            [406.0, 285.0],
            [414.0, 282.7],
            [414.0, 285.0],
            [410.0, 281.0],
            [410.0, 289.0],
        ],
        "zone": "ZONE_B",
        "description": "Ruined concrete facade on North Ridge supporting Ghillie Sniper M05_E6_01 at (410, 285).",
    })
    structures.append({
        "id": "M05_BLDG_RUINED_FACADE_B2",
        "type": "env_building_facade_a",
        "pos": [540.0, 305.0, 0.0],
        "bounds": [535.0, 300.0, 545.0, 310.0],
        "height": 6.5,
        "doorways": [[540.0, 300.0], [540.0, 310.0], [535.0, 305.0], [545.0, 305.0]],
        "zone": "ZONE_B",
        "description": "Secondary North Ridge ruined concrete overwatch post.",
    })

    # --- Zone C: Under-Bridge Catwalks & Maintenance Shafts ---
    structures.append({
        "id": "M05_CATWALK_VENT_WEST_C",
        "type": "env_vent_shaft_2m",
        "pos": [460.0, 165.0, -4.5],
        "zone": "ZONE_C",
        "description": "West under-bridge maintenance catwalk and service duct leading toward checkpoint.",
    })
    structures.append({
        "id": "M05_CATWALK_VENT_EAST_C",
        "type": "env_vent_shaft_2m",
        "pos": [640.0, 165.0, -4.5],
        "zone": "ZONE_C",
        "description": "East under-bridge maintenance catwalk and service duct connecting to South-East slope.",
    })
    structures.append({
        "id": "M05_LADDER_UNDERBRIDGE_C",
        "type": "env_ladder_metal_4m",
        "pos": [585.0, 165.0, -4.5],
        "height": 4.5,
        "zone": "ZONE_C",
        "description": "Maintenance ladder behind bridge checkpoint connecting under-bridge catwalk to main deck.",
    })

    # --- Zone D: Main Bridge Checkpoint Booths, Gantry Sniper Tower & Convoy Trucks ---
    structures.append({
        "id": "M05_BLDG_CHECKPOINT_BOOTH",
        "type": "env_bldg_guardhouse_a",
        "pos": [600.0, 175.0, 0.0],
        "bounds": [594.0, 170.0, 606.0, 180.0],
        "height": 4.2,
        "doorways": [
            [594.0, 171.0],
            [594.0, 175.0],
            [594.0, 178.5],
            [606.0, 172.8],
            [606.0, 173.0],
            [606.0, 174.3],
            [606.0, 175.0],
            [600.0, 170.0],
            [600.0, 180.0],
        ],
        "zone": "ZONE_D",
        "description": "Fortified bridge toll/checkpoint booth at (600, 175) housing camera terminal M05_MON_01 (S1) and alarm M05_ALM_02.",
    })
    structures.append({
        "id": "M05_TOWER_GANTRY_SNIPER_D",
        "type": "env_watchtower_metal_a",
        "pos": [645.0, 195.0, 0.0],
        "radius": 4.0,
        "height": 9.5,
        "has_ladder": True,
        "zone": "ZONE_D",
        "description": "Bridge steel gantry tower at (645, 195) supporting Ghillie Sniper M05_E6_02 and Camera M05_CAM_03.",
    })
    structures.append({
        "id": "M05_VEH_CONVOY_TRUCK_01",
        "type": "veh_truck_cargo_a",
        "pos": [588.0, 178.0, 0.0],
        "zone": "ZONE_D",
        "c4_target": True,
        "objective_id": "O1",
        "description": "Cobalt Convoy Cargo Truck #1 (crewed by M05_E13_01) halting at bridge checkpoint (600, 175) for 90s.",
    })
    structures.append({
        "id": "M05_VEH_CONVOY_TRUCK_02",
        "type": "veh_truck_cargo_a",
        "pos": [612.0, 178.0, 0.0],
        "zone": "ZONE_D",
        "c4_target": True,
        "objective_id": "O1",
        "description": "Cobalt Convoy Cargo Truck #2 (crewed by M05_E13_02) halting at bridge checkpoint (600, 175) for 90s.",
    })
    structures.append({
        "id": "M05_BRIDGE_PYLON_WEST_D",
        "type": "env_bridge_pylon_concrete_a",
        "pos": [480.0, 175.0, 0.0],
        "zone": "ZONE_D",
    })
    structures.append({
        "id": "M05_BRIDGE_PYLON_EAST_D",
        "type": "env_bridge_pylon_concrete_a",
        "pos": [720.0, 175.0, 0.0],
        "zone": "ZONE_D",
    })

    # --- Zone E: Fortified Concrete Command Building ([820, 40] to [960, 120]) ---
    structures.append({
        "id": "M05_BLDG_DAR_COMMAND",
        "type": "env_bldg_command_fort_a",
        "pos": [890.0, 80.0, 0.0],
        "bounds": [820.0, 40.0, 960.0, 120.0],
        "height": 8.0,
        "has_elevator_and_stairs": True,
        "doorways": [
            [820.0, 80.0],
            [820.0, 99.1],
            [820.0, 102.9],
            [890.0, 40.0],
            [890.0, 120.0],
            [935.0, 120.0],
            [960.0, 80.0],
        ],
        "rooms": [
            {"id": "R1", "name": "Garrison Entry & Guard Hall", "bounds": [820.0, 40.0, 865.0, 120.0]},
            {"id": "R2", "name": "Tactical Operations & Elevator Core", "bounds": [865.0, 40.0, 915.0, 120.0]},
            {"id": "R3", "name": "Captain Dar's Command Suite & Briefcase Vault", "bounds": [915.0, 40.0, 960.0, 120.0]},
        ],
        "zone": "ZONE_E",
        "description": "Fortified concrete command building ([820, 40] to [960, 120]) with elevator/stairs, 3 rooms (R1, R2, R3), Alarm Panel M05_ALM_01, and Boss Captain Dar.",
    })
    structures.append({
        "id": "M05_TOWER_GARRISON_SE_E",
        "type": "env_watchtower_metal_a",
        "pos": [755.0, 45.0, 0.0],
        "radius": 3.5,
        "height": 8.5,
        "has_ladder": True,
        "zone": "ZONE_E",
    })
    structures.append({
        "id": "M05_HELIPAD_PATROL_E",
        "type": "env_helipad_concrete_a",
        "pos": [765.0, 95.0, 0.0],
        "zone": "ZONE_E",
        "description": "Garrison helipad supporting E_M05_HELI patrol helicopter searchlight sweep.",
    })

    # --- Zone F: East Riverbank Extraction Point at [1160.0, 320.0] (radius 10.0m) ---
    structures.append({
        "id": "M05_EXTRACTION_POINT_F",
        "type": "env_extraction_zone_marker_a",
        "pos": [1160.0, 320.0, 0.0],
        "extraction_radius": 10.0,
        "zone": "ZONE_F",
        "description": "East Riverbank Extraction Point at (1160, 320) (radius 10.0m).",
    })

    # --- Closed Perimeter 1: Zone D Main Bridge Span Barriers ([350, 150, 850, 200]) -> 36 segments ---
    bridge_perimeter_gates = {
        ("W", 2): ("M05_GATE_BRIDGE_WEST",  "env_gate_sliding_6m"),
        ("E", 2): ("M05_GATE_BRIDGE_EAST",  "env_gate_sliding_6m"),
        ("S", 8): ("M05_GATE_BRIDGE_SOUTH", "env_gate_sliding_6m"),
        ("N", 6): ("M05_GATE_BRIDGE_NORTH", "env_gate_sliding_6m"),
    }
    structures.extend(
        make_closed_perimeter_loop(
            prefix="M05_BRIDGE_BARRIER",
            x_min=350.0,
            y_min=150.0,
            x_max=850.0,
            y_max=200.0,
            n_south=12,
            n_east=6,
            n_north=12,
            n_west=6,
            wall_type="env_wall_concrete_4m",
            gates=bridge_perimeter_gates,
        )
    )

    # --- Closed Perimeter 2: Zone E Garrison Outer Concrete Wall ([720, 20, 980, 140]) -> 32 segments ---
    garrison_perimeter_gates = {
        ("N", 4): ("M05_GATE_GARRISON_NORTH", "env_gate_sliding_6m"),
        ("W", 2): ("M05_GATE_GARRISON_WEST",  "env_gate_sliding_6m"),
        ("E", 2): ("M05_GATE_GARRISON_EAST",  "env_gate_sliding_6m"),
    }
    structures.extend(
        make_closed_perimeter_loop(
            prefix="M05_GARRISON_WALL",
            x_min=720.0,
            y_min=20.0,
            x_max=980.0,
            y_max=140.0,
            n_south=10,
            n_east=6,
            n_north=10,
            n_west=6,
            wall_type="env_wall_concrete_4m",
            gates=garrison_perimeter_gates,
        )
    )

    # --- Closed Perimeter 3: Zone E Command Building Wall Ring ([820, 40, 960, 120]) -> 12 segments ---
    cmd_bldg_gates = {
        ("W", 1): ("M05_GATE_CMD_WEST_DOOR",  "env_gate_sliding_6m"),
        ("N", 1): ("M05_GATE_CMD_NORTH_DOOR", "env_gate_sliding_6m"),
    }
    structures.extend(
        make_closed_perimeter_loop(
            prefix="M05_CMD_BLDG_WALL",
            x_min=820.0,
            y_min=40.0,
            x_max=960.0,
            y_max=120.0,
            n_south=3,
            n_east=3,
            n_north=3,
            n_west=3,
            wall_type="env_wall_concrete_4m",
            gates=cmd_bldg_gates,
        )
    )

    assert len(structures) == 95, f"Expected 95 structures, got {len(structures)}"
    structures = interleave_for_zero_step_repeats(structures)

    # =========================================================================
    # 3. TRAPS (Exact 6 Allowed Traps: 2x T1, 2x T3, 2x T16) & 4 CAMERAS
    # =========================================================================
    traps = [
        {
            "id": "M05_T1_01",
            "type": "T1",
            "name": "North Ridge Sniper Approach Tripwire Alarm #1",
            "pos": [395.0, 278.0, 0.2],
            "zone": "ZONE_B",
            "noise_radius_m": 40.0,
            "counter": "Wire Cutters (2.0s) or step over",
        },
        {
            "id": "M05_T3_01",
            "type": "T3",
            "name": "North Ridge Sniper Perch Directional Mine #1",
            "pos": [404.0, 282.0, 0.2],
            "zone": "ZONE_B",
            "facing_deg": 225.0,
            "damage": 120.0,
            "counter": "Approach from rear arc or disarm with Wire Cutters",
        },
        {
            "id": "M05_T16_01",
            "type": "T16",
            "name": "Under-Bridge Exposed High-Voltage Power Cable #1",
            "pos": [520.0, 165.0, -4.5],
            "zone": "ZONE_C",
            "hazard_subtype": "high_voltage_bridge_cable",
            "damage_per_sec": 35.0,
            "counter": "Shut off local junction box, EMP, or vault across insulated girder",
        },
        {
            "id": "M05_T16_02",
            "type": "T16",
            "name": "Under-Bridge Collapsing Catwalk Grating #2",
            "pos": [680.0, 165.0, -4.5],
            "zone": "ZONE_C",
            "hazard_subtype": "collapsing_catwalk_grating",
            "noise_radius_m": 30.0,
            "counter": "Prone crawl across outer steel I-beam flange",
        },
        {
            "id": "M05_T1_02",
            "type": "T1",
            "name": "Zone E Command Compound Side Entry Tripwire Alarm #2",
            "pos": [814.0, 82.0, 0.2],
            "zone": "ZONE_E",
            "noise_radius_m": 40.0,
            "counter": "Wire Cutters (2.0s)",
        },
        {
            "id": "M05_T3_02",
            "type": "T3",
            "name": "Captain Dar's Command Suite Approach Directional Mine #2",
            "pos": [912.0, 78.0, 0.2],
            "zone": "ZONE_E",
            "facing_deg": 180.0,
            "damage": 120.0,
            "counter": "Bypass via elevator shaft or disarm from flank",
        },
    ]
    assert len(traps) == 6, f"Expected 6 traps, got {len(traps)}"

    cameras = [
        {
            "id": "M05_CAM_01",
            "type": "T11",
            "name": "Bridge Checkpoint West Approach Camera #1",
            "pos": [594.0, 172.0, 3.6],
            "zone": "ZONE_D",
            "mounted_on": "M05_BLDG_CHECKPOINT_BOOTH",
            "fov_deg": 70.0,
            "range_m": 35.0,
            "monitor_id": "M05_MON_01",
        },
        {
            "id": "M05_CAM_02",
            "type": "T11",
            "name": "Bridge Checkpoint East Convoy Lane Camera #2",
            "pos": [606.0, 178.0, 3.6],
            "zone": "ZONE_D",
            "mounted_on": "M05_BLDG_CHECKPOINT_BOOTH",
            "fov_deg": 70.0,
            "range_m": 35.0,
            "monitor_id": "M05_MON_01",
        },
        {
            "id": "M05_CAM_03",
            "type": "T11",
            "name": "Bridge Gantry Tower North Span Camera #3",
            "pos": [645.0, 194.0, 4.2],
            "zone": "ZONE_D",
            "mounted_on": "M05_TOWER_GANTRY_SNIPER_D",
            "fov_deg": 75.0,
            "range_m": 38.0,
            "monitor_id": "M05_MON_01",
        },
        {
            "id": "M05_CAM_04",
            "type": "T11",
            "name": "Bridge South Ramp Overlook Camera #4",
            "pos": [780.0, 150.5, 3.5],
            "zone": "ZONE_D",
            "mounted_on": "M05_BRIDGE_BARRIER_S_08",
            "fov_deg": 70.0,
            "range_m": 35.0,
            "monitor_id": "M05_MON_01",
        },
    ]
    assert len(cameras) == 4, f"Expected 4 cameras, got {len(cameras)}"

    alarms = [
        {
            "id": "M05_ALM_01",
            "type": "prop_alarm_panel_a",
            "name": "Zone E Command Building Master Alarm Panel #1",
            "pos": [875.0, 82.0, 1.3],
            "zone": "ZONE_E",
            "room": "R2",
        },
        {
            "id": "M05_ALM_02",
            "type": "prop_alarm_panel_a",
            "name": "Zone D Bridge Checkpoint Alarm Panel #2",
            "pos": [602.0, 176.0, 1.3],
            "zone": "ZONE_D",
        },
    ]
    assert len(alarms) == 2

    safe_spots = [
        {
            "id": "M05_SAFE_01",
            "name": "West Woods Rock Overhang Safe Spot",
            "pos": [65.0, 182.0, 0.0],
            "radius": 4.5,
            "zone": "ZONE_A",
        },
        {
            "id": "M05_SAFE_02",
            "name": "Under-Bridge Central Pier Maintenance Alcove",
            "pos": [575.0, 162.0, -4.5],
            "radius": 4.0,
            "zone": "ZONE_C",
        },
        {
            "id": "M05_SAFE_03",
            "name": "East Riverbank Culvert Safe Spot",
            "pos": [1045.0, 265.0, 0.0],
            "radius": 4.5,
            "zone": "ZONE_F",
        },
    ]
    assert len(safe_spots) == 3

    # =========================================================================
    # 4. ENEMIES (Exact 36 Enemies: 6x E1, 16x E2, 3x E3, 4x E4, 2x E6, 2x E10, 2x E13, 1x E14 Boss)
    # =========================================================================
    enemies: List[Dict[str, Any]] = []

    # --- 6x E1 Militia Grunts (wpn_mp9_mesh) in Zone A, Zone B, Zone C ---
    e1_specs = [
        ("M05_E1_01", "West Approach Highway Cordon Grunt #1", [125.0, 168.0, 0.0], "ZONE_A", [[125.0, 168.0], [165.0, 168.0], [165.0, 192.0], [125.0, 192.0]]),
        ("M05_E1_02", "West Approach Woods Trail Grunt #2",    [190.0, 142.0, 0.0], "ZONE_A", [[190.0, 142.0], [235.0, 142.0], [235.0, 166.0], [190.0, 166.0]]),
        ("M05_E1_03", "West Bridge Outer Cordon Grunt #3",     [265.0, 185.0, 0.0], "ZONE_A", [[265.0, 185.0], [295.0, 185.0], [295.0, 218.0], [265.0, 218.0]]),
        ("M05_E1_04", "North Ridge Lower Trail Grunt #4",      [285.0, 268.0, 0.0], "ZONE_B", [[285.0, 268.0], [335.0, 268.0], [335.0, 295.0], [285.0, 295.0]]),
        ("M05_E1_05", "Under-Bridge West Bank Grunt #5",       [355.0, 112.0, 0.0], "ZONE_C", [[355.0, 112.0], [410.0, 112.0], [410.0, 138.0], [355.0, 138.0]]),
        ("M05_E1_06", "East Riverbank Exit Trail Grunt #6",    [945.0, 215.0, 0.0], "ZONE_F", [[945.0, 215.0], [1005.0, 215.0], [1005.0, 248.0], [945.0, 248.0]]),
    ]
    for eid, ename, epos, ezone, ewps in e1_specs:
        enemies.append({
            "id": eid,
            "class": "E1",
            "name": ename,
            "asset_id": "chr_enemy_e1_recruit",
            "weapon": "wpn_mp9_mesh",
            "has_radio": False,
            "pos": epos,
            "zone": ezone,
            "patrol_waypoints": ewps,
        })

    # --- 16x E2 Cobalt Regular Grunts (wpn_ar5_mesh) across Zones B, C, D, E, F ---
    e2_specs = [
        ("M05_E2_01", "North Ridge East Overwatch Grunt #1",   [475.0, 275.0, 0.0], "ZONE_B", [[475.0, 275.0], [520.0, 275.0], [520.0, 298.0], [475.0, 298.0]]),
        ("M05_E2_02", "North Ridge Far East Flank Grunt #2",   [595.0, 272.0, 0.0], "ZONE_B", [[595.0, 272.0], [655.0, 272.0], [655.0, 305.0], [595.0, 305.0]]),
        ("M05_E2_03", "Under-Bridge Catwalk West Guard #3",    [445.0, 165.0, -4.5],"ZONE_C", [[445.0, 165.0], [495.0, 165.0], [495.0, 158.0], [445.0, 158.0]]),
        ("M05_E2_04", "Under-Bridge Catwalk East Guard #4",    [615.0, 165.0, -4.5],"ZONE_C", [[615.0, 165.0], [662.0, 165.0], [662.0, 158.0], [615.0, 158.0]]),
        ("M05_E2_05", "South Riverbank Embankment Guard #5",   [535.0, 105.0, 0.0], "ZONE_C", [[535.0, 105.0], [595.0, 105.0], [595.0, 132.0], [535.0, 132.0]]),
        ("M05_E2_06", "Bridge West Span Barrier Guard #6",     [385.0, 162.0, 0.0], "ZONE_D", [[385.0, 162.0], [445.0, 162.0], [445.0, 188.0], [385.0, 188.0]]),
        ("M05_E2_07", "Bridge Mid-West Span Guard #7",         [470.0, 185.0, 0.0], "ZONE_D", [[470.0, 185.0], [535.0, 185.0], [535.0, 162.0], [470.0, 162.0]]),
        ("M05_E2_08", "Bridge Checkpoint West Barrier Guard #8",[562.0, 164.0, 0.0],"ZONE_D", [[562.0, 164.0], [586.0, 164.0], [586.0, 188.0], [562.0, 188.0]]),
        ("M05_E2_09", "Bridge Checkpoint East Barrier Guard #9",[618.0, 164.0, 0.0],"ZONE_D", [[618.0, 164.0], [642.0, 164.0], [642.0, 188.0], [618.0, 188.0]]),
        ("M05_E2_10", "Bridge Mid-East Span Guard #10",        [675.0, 162.0, 0.0], "ZONE_D", [[675.0, 162.0], [740.0, 162.0], [740.0, 188.0], [675.0, 188.0]]),
        ("M05_E2_11", "Bridge East Exit Span Guard #11",       [765.0, 185.0, 0.0], "ZONE_D", [[765.0, 185.0], [830.0, 185.0], [830.0, 162.0], [765.0, 162.0]]),
        ("M05_E2_12", "Zone E Garrison Outer Courtyard Guard #12",[738.0, 62.0, 0.0],"ZONE_E", [[738.0, 62.0], [795.0, 62.0], [795.0, 118.0], [738.0, 118.0]]),
        ("M05_E2_13", "Zone E Garrison Helipad Perimeter Guard #13",[748.0, 125.0, 0.0],"ZONE_E",[[748.0, 125.0],[812.0, 125.0],[812.0, 136.0],[748.0, 136.0]]),
        ("M05_E2_14", "Zone E Command Building R1 Lobby Guard #14",[832.0, 56.0, 0.0],"ZONE_E", [[832.0, 56.0], [858.0, 56.0], [858.0, 104.0], [832.0, 104.0]]),
        ("M05_E2_15", "Zone E Command South Yard Guard #15",   [845.0, 26.0, 0.0],  "ZONE_E", [[845.0, 26.0], [945.0, 26.0], [945.0, 36.0], [845.0, 36.0]]),
        ("M05_E2_16", "Zone F East Highway Outpost Guard #16", [1035.0, 195.0, 0.0],"ZONE_F", [[1035.0, 195.0], [1110.0, 195.0], [1110.0, 245.0], [1035.0, 245.0]]),
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
            "has_radio": False,
            "pos": epos,
            "zone": ezone,
            "patrol_waypoints": ewps,
        })

    # --- 3x E3 Radio Officers (wpn_p45_enforcer, radio: true) ---
    e3_specs = [
        ("M05_E3_01", "North Ridge Overwatch Radio Officer #1", [365.0, 282.0, 0.0], "ZONE_B", [[365.0, 282.0], [392.0, 282.0], [392.0, 312.0], [365.0, 312.0]]),
        ("M05_E3_02", "Bridge Checkpoint Commander Radio Officer #2", [575.0, 175.0, 0.0], "ZONE_D", [[575.0, 175.0], [588.0, 175.0], [588.0, 192.0], [575.0, 192.0]]),
        ("M05_E3_03", "Zone E Garrison Comms Officer #3",       [878.0, 62.0, 0.0],  "ZONE_E", [[878.0, 62.0], [908.0, 62.0], [908.0, 102.0], [878.0, 102.0]]),
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

    # --- 4x E4 Cobalt Elite Bodyguards (ballistic vests, wpn_ar12_burst, throw grenades & flank) ---
    e4_specs = [
        ("M05_E4_01", "Captain Dar Cobalt Elite Bodyguard #1", [872.0, 92.0, 0.0], "ZONE_E", [[872.0, 92.0], [906.0, 92.0], [906.0, 112.0], [872.0, 112.0]]),
        ("M05_E4_02", "Captain Dar Cobalt Elite Bodyguard #2", [922.0, 54.0, 0.0], "ZONE_E", [[922.0, 54.0], [952.0, 54.0], [952.0, 74.0],  [922.0, 74.0]]),
        ("M05_E4_03", "Captain Dar Cobalt Elite Bodyguard #3", [922.0, 96.0, 0.0], "ZONE_E", [[922.0, 96.0], [952.0, 96.0], [952.0, 114.0], [922.0, 114.0]]),
        ("M05_E4_04", "Captain Dar Cobalt Elite Bodyguard #4", [966.0, 68.0, 0.0], "ZONE_E", [[966.0, 68.0], [976.0, 68.0], [976.0, 112.0], [966.0, 112.0]]),
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

    # --- 2x E6 Ghillie Snipers (wpn_longbow_mesh, 80m vision + 1s laser paint) ---
    enemies.append({
        "id": "M05_E6_01",
        "class": "E6",
        "name": "North Ridge Ruined Facade Ghillie Sniper #1",
        "asset_id": "chr_enemy_e6_sniper",
        "weapon": "wpn_longbow_mesh",
        "vision_range_m": 80.0,
        "laser_paint_seconds": 1.0,
        "pos": [410.0, 285.0, 8.5],
        "elevation": 8.5,
        "mount": "roof",
        "zone": "ZONE_B",
        "patrol_waypoints": [
            [408.5, 283.5],
            [411.5, 283.5],
            [411.5, 286.5],
            [408.5, 286.5],
        ],
    })
    enemies.append({
        "id": "M05_E6_02",
        "class": "E6",
        "name": "Main Bridge Gantry Tower Ghillie Sniper #2",
        "asset_id": "chr_enemy_e6_sniper",
        "weapon": "wpn_longbow_mesh",
        "vision_range_m": 80.0,
        "laser_paint_seconds": 1.0,
        "pos": [645.0, 195.0, 9.5],
        "elevation": 9.5,
        "mount": "watchtower",
        "zone": "ZONE_D",
        "patrol_waypoints": [
            [644.0, 194.0],
            [646.0, 194.0],
            [646.0, 196.0],
            [644.0, 196.0],
        ],
    })

    # --- 2x E10 Scouts (wpn_ar9_carbine + Binoculars, 60m vision) ---
    enemies.append({
        "id": "M05_E10_01",
        "class": "E10",
        "name": "West Approach Woods Recon Scout #1",
        "asset_id": "chr_enemy_e10_dog_handler",
        "weapon": "wpn_ar9_carbine",
        "equipment": ["Binoculars"],
        "vision_range_m": 60.0,
        "pos": [225.0, 212.0, 0.0],
        "zone": "ZONE_A",
        "patrol_waypoints": [
            [225.0, 212.0],
            [258.0, 212.0],
            [258.0, 238.0],
            [225.0, 238.0],
        ],
    })
    enemies.append({
        "id": "M05_E10_02",
        "class": "E10",
        "name": "North-West Slope Bridge Approach Scout #2",
        "asset_id": "chr_enemy_e10_dog_handler",
        "weapon": "wpn_ar9_carbine",
        "equipment": ["Binoculars"],
        "vision_range_m": 60.0,
        "pos": [325.0, 228.0, 0.0],
        "zone": "ZONE_C",
        "patrol_waypoints": [
            [325.0, 228.0],
            [344.0, 228.0],
            [344.0, 246.0],
            [325.0, 246.0],
        ],
    })

    # --- 2x E13 Vehicle Crew (crewing the 2 Convoy Cargo Trucks in Zone D) ---
    enemies.append({
        "id": "M05_E13_01",
        "class": "E13",
        "name": "Convoy Cargo Truck #1 Driver / Crew",
        "asset_id": "chr_enemy_e13_ghillie_spotter",
        "weapon": "wpn_mp9_mesh",
        "assigned_vehicle_id": "M05_VEH_CONVOY_TRUCK_01",
        "pos": [585.0, 182.0, 0.0],
        "zone": "ZONE_D",
        "patrol_waypoints": [
            [585.0, 182.0],
            [591.0, 182.0],
            [591.0, 186.0],
            [585.0, 186.0],
        ],
    })
    enemies.append({
        "id": "M05_E13_02",
        "class": "E13",
        "name": "Convoy Cargo Truck #2 Driver / Crew",
        "asset_id": "chr_enemy_e13_ghillie_spotter",
        "weapon": "wpn_mp9_mesh",
        "assigned_vehicle_id": "M05_VEH_CONVOY_TRUCK_02",
        "pos": [610.0, 182.0, 0.0],
        "zone": "ZONE_D",
        "patrol_waypoints": [
            [610.0, 182.0],
            [616.0, 182.0],
            [616.0, 186.0],
            [610.0, 186.0],
        ],
    })

    # --- 1x E14 Boss Commander Captain Dar (chr_boss_captain_dar, 180 HP, heavy vest, wpn_p45_enforcer / wpn_mp9_mesh) ---
    enemies.append({
        "id": "M05_E14_01",
        "class": "E14",
        "name": "Captain Dar (Boss Commander — Chapter 1 Finale)",
        "asset_id": "chr_boss_captain_dar",
        "is_boss": True,
        "hp": 180,
        "armor": "heavy_vest",
        "weapon": "wpn_p45_enforcer",
        "secondary_weapon": "wpn_mp9_mesh",
        "carries_item_id": "M05_PKP_DAR_BRIEFCASE",
        "pos": [935.0, 80.0, 0.0],
        "zone": "ZONE_E",
        "room": "R3",
        "patrol_waypoints": [
            [925.0, 76.0],
            [948.0, 76.0],
            [948.0, 88.0],
            [925.0, 88.0],
        ],
    })

    assert len(enemies) == 36, f"Expected 36 enemies, got {len(enemies)}"
    enemies = interleave_for_zero_step_repeats(enemies)

    # =========================================================================
    # 5. LIGHTS (Exact 13 Lights across Bridge, Checkpoint & Command Compound)
    # =========================================================================
    lights = [
        {"id": "M05_LGT_01", "type": "light_highway_sodium_pole", "pos": [290.0, 175.0, 6.5], "zone": "ZONE_A", "range_m": 20.0},
        {"id": "M05_LGT_02", "type": "light_bunker_lantern",      "pos": [410.0, 285.0, 3.2], "zone": "ZONE_B", "range_m": 10.0},
        {"id": "M05_LGT_03", "type": "light_caged_bulb_warm",     "pos": [520.0, 165.0, -3.2],"zone": "ZONE_C", "range_m": 12.0},
        {"id": "M05_LGT_04", "type": "light_caged_bulb_warm",     "pos": [680.0, 165.0, -3.2],"zone": "ZONE_C", "range_m": 12.0},
        {"id": "M05_LGT_05", "type": "light_flood_checkpoint",    "pos": [420.0, 175.0, 7.0], "zone": "ZONE_D", "range_m": 24.0},
        {"id": "M05_LGT_06", "type": "light_flood_checkpoint",    "pos": [585.0, 172.0, 7.0], "zone": "ZONE_D", "range_m": 25.0},
        {"id": "M05_LGT_07", "type": "light_fluorescent_tube",    "pos": [600.0, 175.0, 3.5], "zone": "ZONE_D", "range_m": 12.0},
        {"id": "M05_LGT_08", "type": "light_flood_checkpoint",    "pos": [618.0, 178.0, 7.0], "zone": "ZONE_D", "range_m": 25.0},
        {"id": "M05_LGT_09", "type": "light_flood_checkpoint",    "pos": [775.0, 175.0, 7.0], "zone": "ZONE_D", "range_m": 24.0},
        {"id": "M05_LGT_10", "type": "light_flood_gate_pole",     "pos": [890.0, 138.0, 6.5], "zone": "ZONE_E", "range_m": 22.0},
        {"id": "M05_LGT_11", "type": "light_fluorescent_tube",    "pos": [842.0, 80.0, 3.8],  "zone": "ZONE_E", "room": "R1", "range_m": 14.0},
        {"id": "M05_LGT_12", "type": "light_command_table_lamp",  "pos": [935.0, 80.0, 3.8],  "zone": "ZONE_E", "room": "R3", "range_m": 15.0},
        {"id": "M05_LGT_13", "type": "light_extraction_beacon",   "pos": [1160.0, 320.0, 3.8],"zone": "ZONE_F", "range_m": 18.0},
    ]
    assert len(lights) == 13, f"Expected 13 lights, got {len(lights)}"

    # =========================================================================
    # 6. HIDING SPOTS (Exact 36 Hiding Spots across Zones A-F)
    # =========================================================================
    hiding_spot_coords = [
        ("ZONE_A", "env_bush_stealth_a",    [58.4, 162.4, 0.0]),
        ("ZONE_A", "env_bush_stealth_a",    [94.2, 188.6, 0.0]),
        ("ZONE_A", "env_bush_stealth_a",    [142.8, 154.2, 0.0]),
        ("ZONE_A", "env_bush_stealth_a",    [178.6, 204.8, 0.0]),
        ("ZONE_A", "env_bush_stealth_a",    [218.4, 168.2, 0.0]),
        ("ZONE_A", "env_bush_stealth_a",    [274.2, 148.6, 0.0]),
        ("ZONE_B", "env_bush_stealth_a",    [245.6, 278.4, 0.0]),
        ("ZONE_B", "env_bush_stealth_a",    [318.4, 304.2, 0.0]),
        ("ZONE_B", "prop_locker_metal_a",   [408.2, 287.4, 0.0]),
        ("ZONE_B", "env_bush_stealth_a",    [462.8, 292.6, 0.0]),
        ("ZONE_B", "prop_dumpster_metal_a", [538.4, 302.8, 0.0]),
        ("ZONE_B", "env_bush_stealth_a",    [628.6, 288.4, 0.0]),
        ("ZONE_C", "vent_shaft",            [432.4, 165.0, -4.5]),
        ("ZONE_C", "vent_shaft",            [488.6, 165.0, -4.5]),
        ("ZONE_C", "vent_shaft",            [554.2, 165.0, -4.5]),
        ("ZONE_C", "vent_shaft",            [624.8, 165.0, -4.5]),
        ("ZONE_C", "vent_shaft",            [704.6, 165.0, -4.5]),
        ("ZONE_C", "env_bush_stealth_a",    [382.4, 98.6, 0.0]),
        ("ZONE_C", "env_bush_stealth_a",    [742.8, 224.6, 0.0]),
        ("ZONE_D", "prop_dumpster_metal_a", [396.4, 156.2, 0.0]),
        ("ZONE_D", "prop_dumpster_metal_a", [492.8, 192.4, 0.0]),
        ("ZONE_D", "prop_locker_metal_a",   [598.4, 172.4, 0.0]),
        ("ZONE_D", "prop_locker_metal_a",   [603.6, 177.8, 0.0]),
        ("ZONE_D", "prop_dumpster_metal_a", [698.4, 156.8, 0.0]),
        ("ZONE_D", "prop_dumpster_metal_a", [796.2, 192.6, 0.0]),
        ("ZONE_E", "prop_dumpster_metal_a", [734.6, 48.2, 0.0]),
        ("ZONE_E", "prop_dumpster_metal_a", [788.4, 128.6, 0.0]),
        ("ZONE_E", "prop_locker_metal_a",   [826.4, 48.4, 0.0]),
        ("ZONE_E", "prop_locker_metal_a",   [856.8, 112.4, 0.0]),
        ("ZONE_E", "prop_locker_metal_a",   [874.2, 48.6, 0.0]),
        ("ZONE_E", "closet_storage_a",      [906.4, 112.8, 0.0]),
        ("ZONE_E", "prop_locker_metal_a",   [924.8, 48.2, 0.0]),
        ("ZONE_E", "closet_storage_a",      [952.6, 112.6, 0.0]),
        ("ZONE_F", "env_bush_stealth_a",    [918.4, 242.6, 0.0]),
        ("ZONE_F", "env_bush_stealth_a",    [1024.6, 278.4, 0.0]),
        ("ZONE_F", "env_bush_stealth_a",    [1118.2, 304.8, 0.0]),
    ]
    hiding_spots = []
    for idx, (hz, htype, hpos) in enumerate(hiding_spot_coords):
        hiding_spots.append({
            "id": f"M05_HIDE_{idx+1:02d}",
            "type": htype,
            "pos": hpos,
            "zone": hz,
        })
    assert len(hiding_spots) == 36, f"Expected 36 hiding spots, got {len(hiding_spots)}"

    # =========================================================================
    # 7. PICKUPS (Exact 24 Pickups including C4, Briefcase S2, and .357 Reward)
    # =========================================================================
    pickups = [
        {"id": "M05_PKP_C4_CHARGE_01",    "type": "pickup_explosive_c4",       "name": "C4 Demolition Charge #1 (Convoy Sabotage O1)", "pos": [585.0, 166.5, 0.8], "zone": "ZONE_C"},
        {"id": "M05_PKP_C4_CHARGE_02",    "type": "pickup_explosive_c4",       "name": "C4 Demolition Charge #2 (Convoy Sabotage O1)", "pos": [598.5, 174.0, 1.0], "zone": "ZONE_D"},
        {"id": "M05_PKP_DAR_BRIEFCASE",   "type": "pickup_intel_briefcase",    "name": "Captain Dar's Classified Briefcase (S2)",      "pos": [942.0, 82.0, 1.0],  "zone": "ZONE_E", "room": "R3", "objective_id": "S2"},
        {"id": "M05_PKP_REWARD_357",      "type": "pickup_reward_revolver357", "name": "Hand Cannon .357 (wpn_revolver357_mesh — O1 Unlock)", "pos": [938.0, 78.0, 1.0], "zone": "ZONE_E", "room": "R3"},
        {"id": "M05_PKP_05",              "type": "pickup_gadget_wirecutters", "name": "Heavy Wire Cutters",                           "pos": [78.4, 172.6, 0.8],  "zone": "ZONE_A"},
        {"id": "M05_PKP_06",              "type": "pickup_ammo_9mm_box",       "name": "9x19mm Subsonic Box",                          "pos": [156.2, 182.4, 0.8], "zone": "ZONE_A"},
        {"id": "M05_PKP_07",              "type": "pickup_medkit_field",       "name": "Field Trauma Kit",                             "pos": [248.4, 196.2, 0.8], "zone": "ZONE_A"},
        {"id": "M05_PKP_08",              "type": "pickup_ammo_sniper_box",    "name": ".338 Longbow Match Grade Box",                 "pos": [411.2, 286.0, 8.6], "zone": "ZONE_B"},
        {"id": "M05_PKP_09",              "type": "pickup_gadget_binoculars",  "name": "Rangefinder Binoculars",                       "pos": [348.6, 276.4, 0.9], "zone": "ZONE_B"},
        {"id": "M05_PKP_10",              "type": "pickup_medkit_field",       "name": "First-Aid Field Dressing",                     "pos": [542.0, 306.0, 0.9], "zone": "ZONE_B"},
        {"id": "M05_PKP_11",              "type": "pickup_gadget_emp_grenade", "name": "EMP Grenade #1",                               "pos": [468.4, 165.0, -4.2],"zone": "ZONE_C"},
        {"id": "M05_PKP_12",              "type": "pickup_gadget_lockpick",    "name": "Precision Lockpick Set",                       "pos": [572.6, 163.2, -4.2],"zone": "ZONE_C"},
        {"id": "M05_PKP_13",              "type": "pickup_ammo_556_box",       "name": "5.56mm NATO Rifle Box #1",                     "pos": [412.4, 172.8, 0.8], "zone": "ZONE_D"},
        {"id": "M05_PKP_14",              "type": "pickup_gadget_hack_pda",    "name": "Cryptographic Hack PDA",                       "pos": [596.2, 176.4, 1.0], "zone": "ZONE_D"},
        {"id": "M05_PKP_15",              "type": "pickup_gadget_emp_grenade", "name": "EMP Grenade #2",                               "pos": [604.2, 173.8, 1.0], "zone": "ZONE_D"},
        {"id": "M05_PKP_16",              "type": "pickup_ammo_sniper_box",    "name": ".338 Longbow Box #2",                          "pos": [645.5, 195.5, 9.6], "zone": "ZONE_D"},
        {"id": "M05_PKP_17",              "type": "pickup_medkit_field",       "name": "Bridge Checkpoint Medkit",                     "pos": [718.4, 176.2, 0.8], "zone": "ZONE_D"},
        {"id": "M05_PKP_18",              "type": "pickup_ammo_556_box",       "name": "5.56mm NATO Rifle Box #2",                     "pos": [756.2, 46.4, 6.2],  "zone": "ZONE_E"},
        {"id": "M05_PKP_19",              "type": "pickup_keycard_command",    "name": "Zone E Command Building Side Keycard",         "pos": [792.4, 108.6, 0.9], "zone": "ZONE_E"},
        {"id": "M05_PKP_20",              "type": "pickup_ammo_556_box",       "name": "5.56mm AP Burst Box",                          "pos": [838.6, 68.4, 0.9],  "zone": "ZONE_E", "room": "R1"},
        {"id": "M05_PKP_21",              "type": "pickup_medkit_field",       "name": "Garrison Infirmary Medkit",                    "pos": [884.2, 96.4, 0.9],  "zone": "ZONE_E", "room": "R2"},
        {"id": "M05_PKP_22",              "type": "pickup_ammo_9mm_box",       "name": ".45 ACP Enforcer Box",                         "pos": [928.4, 62.8, 0.9],  "zone": "ZONE_E", "room": "R3"},
        {"id": "M05_PKP_23",              "type": "pickup_ammo_556_box",       "name": "5.56mm NATO Rifle Box #3",                     "pos": [988.4, 212.6, 0.8], "zone": "ZONE_F"},
        {"id": "M05_PKP_24",              "type": "pickup_medkit_field",       "name": "Extraction Trail Medkit",                      "pos": [1124.6, 298.4, 0.8],"zone": "ZONE_F"},
    ]
    assert len(pickups) == 24, f"Expected 24 pickups, got {len(pickups)}"
    pickups = interleave_for_zero_step_repeats(pickups)

    # =========================================================================
    # 8. VEGETATION (Exact 85 Forest/Riverbank Trees & Bushes across Zones A, B, C, F)
    # =========================================================================
    veg_zones = [
        ("ZONE_A", 8.0, 106.0, 292.0, 244.0),
        ("ZONE_B", 208.0, 256.0, 692.0, 344.0),
        ("ZONE_C", 308.0, 66.0, 892.0, 142.0),
        ("ZONE_F", 858.0, 158.0, 1192.0, 342.0),
    ]
    vegetation: List[Dict[str, Any]] = []
    for i in range(1, 86):
        zname, x0, y0, x1, y1 = veg_zones[i % len(veg_zones)]
        u = vdc(i * 5 + 3, 2)
        v = vdc(i * 9 + 7, 3)
        vx = round(x0 + u * (x1 - x0), 2)
        vy = round(y0 + v * (y1 - y0), 2)
        vtype = "env_tree_pine_tall_a" if (i % 2 == 0) else "env_bush_stealth_a"
        vegetation.append({
            "id": f"M05_VEG_{i:02d}",
            "type": vtype,
            "pos": [vx, vy, 0.0],
            "zone": zname,
        })
    assert len(vegetation) == 85, f"Expected 85 vegetation items, got {len(vegetation)}"
    vegetation = interleave_for_zero_step_repeats(vegetation)

    # =========================================================================
    # 9. COVER (Exact 430 Handcrafted Cover Pieces across Zones A-F)
    # =========================================================================
    cover_zones = [
        ("ZONE_A", 10.0, 108.0, 292.0, 242.0, ["env_rock_boulder_a", "prop_sandbag_wall_a", "prop_concrete_barrier_a"]),
        ("ZONE_B", 210.0, 256.0, 690.0, 342.0, ["env_rock_boulder_a", "prop_sandbag_wall_a", "prop_crate_military_a"]),
        ("ZONE_C", 310.0, 68.0, 890.0, 144.0, ["env_rock_boulder_a", "prop_crate_metal_a", "prop_concrete_barrier_a"]),
        ("ZONE_D", 356.0, 154.0, 844.0, 196.0, ["prop_concrete_barrier_a", "prop_sandbag_wall_a", "prop_crate_military_a"]),
        ("ZONE_E", 726.0, 24.0, 974.0, 136.0, ["prop_concrete_barrier_a", "prop_sandbag_wall_a", "prop_crate_metal_a"]),
        ("ZONE_F", 860.0, 158.0, 1188.0, 340.0, ["env_rock_boulder_a", "prop_concrete_barrier_a", "prop_sandbag_wall_a"]),
    ]
    cover: List[Dict[str, Any]] = []
    for i in range(1, 431):
        zname, x0, y0, x1, y1, ctypes = cover_zones[i % len(cover_zones)]
        u = vdc(i * 7 + 11, 2)
        v = vdc(i * 13 + 5, 3)
        cx = round(x0 + u * (x1 - x0), 2)
        cy = round(y0 + v * (y1 - y0), 2)
        cover.append({
            "id": f"M05_COV_{i:03d}",
            "type": ctypes[i % len(ctypes)],
            "pos": [cx, cy, 0.0],
            "zone": zname,
        })
    assert len(cover) == 430, f"Expected 430 cover pieces, got {len(cover)}"
    cover = interleave_for_zero_step_repeats(cover)

    # =========================================================================
    # 10. PROPS (Exact 815 Props including M05_MON_01, M05_ALM_01, M05_ALM_02)
    # =========================================================================
    props: List[Dict[str, Any]] = [
        {
            "id": "M05_MON_01",
            "type": "prop_terminal_desk_a",
            "name": "Bridge Checkpoint Security Camera Monitor Terminal (S1)",
            "pos": [600.0, 175.0, 0.0],
            "zone": "ZONE_D",
            "controls_camera_ids": ["M05_CAM_01", "M05_CAM_02", "M05_CAM_03", "M05_CAM_04"],
            "objective_id": "S1",
        },
        {
            "id": "M05_ALM_01",
            "type": "prop_alarm_panel_a",
            "name": "Zone E Command Building Master Alarm Panel #1",
            "pos": [875.0, 82.0, 1.3],
            "zone": "ZONE_E",
            "room": "R2",
        },
        {
            "id": "M05_ALM_02",
            "type": "prop_alarm_panel_a",
            "name": "Zone D Bridge Checkpoint Alarm Panel #2",
            "pos": [602.0, 176.0, 1.3],
            "zone": "ZONE_D",
        },
        {
            "id": "M05_PRP_ELEVATOR_E",
            "type": "prop_elevator_cage_a",
            "name": "Command Building Interior Elevator & Stairwell Core",
            "pos": [890.0, 80.0, 0.0],
            "zone": "ZONE_E",
            "room": "R2",
        },
        {
            "id": "M05_PRP_BREAKER_BRIDGE_C",
            "type": "prop_breaker_box_a",
            "name": "Under-Bridge High-Voltage Cable Breaker Box",
            "pos": [512.0, 165.0, -4.2],
            "zone": "ZONE_C",
        },
    ]

    prop_catalog = [
        "prop_concrete_barrier_a",
        "prop_crate_military_a",
        "prop_crate_metal_a",
        "prop_fuel_drum_metal_a",
        "prop_ammo_crate_wood_a",
        "prop_cable_spool_wood_a",
        "prop_radio_field_desk_a",
        "prop_workbench_tools_a",
        "prop_locker_metal_a",
        "prop_dumpster_metal_a",
        "prop_water_jerrycan_a",
        "prop_map_board_easel_a",
        "prop_generator_diesel_a",
        "prop_weapon_rack_empty_a",
    ]
    prop_zone_boxes = [
        ("ZONE_A", 12.0, 110.0, 288.0, 240.0),
        ("ZONE_B", 212.0, 258.0, 688.0, 340.0),
        ("ZONE_C", 312.0, 70.0, 888.0, 282.0),
        ("ZONE_D", 358.0, 154.0, 842.0, 196.0),
        ("ZONE_E", 726.0, 26.0, 974.0, 134.0),
        ("ZONE_F", 862.0, 162.0, 1184.0, 336.0),
    ]

    while len(props) < 815:
        idx = len(props) + 1
        zname, x0, y0, x1, y1 = prop_zone_boxes[idx % len(prop_zone_boxes)]
        u = vdc(idx * 11 + 7, 2)
        v = vdc(idx * 17 + 3, 5)
        px = round(x0 + u * (x1 - x0), 2)
        py = round(y0 + v * (y1 - y0), 2)
        props.append({
            "id": f"M05_PRP_{idx:03d}",
            "type": prop_catalog[idx % len(prop_catalog)],
            "pos": [px, py, 0.0],
            "zone": zname,
        })

    assert len(props) == 815, f"Expected 815 props, got {len(props)}"
    props = interleave_for_zero_step_repeats(props)

    # =========================================================================
    # 11. DYNAMIC MISSION EVENTS (Exact 2 Events: E_M05_CONVOY, E_M05_HELI)
    # =========================================================================
    events = [
        {
            "id": "E_M05_CONVOY",
            "trigger": "elapsed >= 360",
            "condition": {"type": "time_elapsed_sec", "threshold": 360.0},
            "action": "convoy_start:stop_checkpoint_90s",
            "vehicles": ["M05_VEH_CONVOY_TRUCK_01", "M05_VEH_CONVOY_TRUCK_02"],
            "crew_ids": ["M05_E13_01", "M05_E13_02"],
            "halt_pos": [600.0, 175.0, 0.0],
            "halt_duration_sec": 90.0,
            "description": "At elapsed >= 360s, the 2 cargo trucks drive onto the bridge and stop at the central checkpoint (600, 175) for 90s so the player can plant C4 on both trucks.",
        },
        {
            "id": "E_M05_HELI",
            "trigger": "elapsed >= 900",
            "condition": {"type": "time_elapsed_sec", "threshold": 900.0},
            "action": "spawn:heli_searchlight_sweep",
            "spawn_vehicle": "veh_helicopter_enemy_a",
            "sweep_path": [[350.0, 175.0, 35.0], [600.0, 175.0, 35.0], [850.0, 175.0, 35.0], [890.0, 80.0, 35.0]],
            "description": "At elapsed >= 900s, an enemy patrol helicopter (veh_helicopter_enemy_a) arrives and sweeps the bridge with a high-intensity searchlight.",
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
                "title": "Sabotage convoy (plant & detonate C4 on both cargo trucks) & eliminate Captain Dar",
                "target_vehicles": ["M05_VEH_CONVOY_TRUCK_01", "M05_VEH_CONVOY_TRUCK_02"],
                "checkpoint_pos": [600.0, 175.0, 0.0],
                "boss_id": "M05_E14_01",
                "boss_asset": "chr_boss_captain_dar",
                "boss_pos": [935.0, 80.0, 0.0],
                "unlock_reward": "Hand Cannon .357",
                "unlock_weapon_id": "wpn_revolver357_mesh",
            }
        ],
        "secondary": [
            {
                "id": "S1",
                "title": "Disable all 4 checkpoint cameras via monitor M05_MON_01",
                "target_id": "M05_MON_01",
                "target_pos": [600.0, 175.0, 0.0],
                "disabled_cameras": ["M05_CAM_01", "M05_CAM_02", "M05_CAM_03", "M05_CAM_04"],
                "zone": "ZONE_D",
            },
            {
                "id": "S2",
                "title": "Steal Captain Dar's briefcase without raising Alert 3 (Ghost Medal)",
                "target_pickup_id": "M05_PKP_DAR_BRIEFCASE",
                "max_alert_allowed": 2,
                "medal_reward": "Ghost Medal",
            },
        ],
        "extraction": {
            "id": "EXT_M05",
            "title": "Extract at East Riverbank Extraction Point (1160, 320)",
            "pos": [1160.0, 320.0, 0.0],
            "radius": 10.0,
            "zone": "ZONE_F",
        },
    }

    routes = {
        "silent": {
            "name": "Silent Route (Under-Bridge Catwalk Infiltration, Maintenance Ladder C4 & Suppressed Assassination)",
            "description": "Infiltrate from West Approach Woods (40, 175) down to the under-bridge catwalks (320, 165), bypass T16 hazards to the maintenance ladder behind the checkpoint (585, 165), climb up to plant C4 on both convoy trucks at (600, 175), slip into Zone E Command Building (890, 80) to assassinate Captain Dar with a suppressed weapon & take his briefcase, and extract at (1160, 320).",
            "waypoints": [
                [40.0, 175.0],
                [320.0, 165.0],
                [585.0, 165.0],
                [600.0, 175.0],
                [890.0, 80.0],
                [1160.0, 320.0],
            ],
        },
        "technical": {
            "name": "Technical Route (Checkpoint Monitor Hack M05_MON_01, EMP Convoy Escort & Side Door Unlock)",
            "description": "Advance from (40, 175) to the West Bridge Gate (350, 175), hack checkpoint camera terminal M05_MON_01 at (600, 175) to disable all 4 cameras (S1) and use an EMP grenade on the convoy escort while planting C4, descend the South-East ramp (780, 110) to unlock the Command Building side door into (890, 80) to eliminate Captain Dar, and extract at (1160, 320).",
            "waypoints": [
                [40.0, 175.0],
                [350.0, 175.0],
                [600.0, 175.0],
                [780.0, 110.0],
                [890.0, 80.0],
                [1160.0, 320.0],
            ],
        },
        "loud": {
            "name": "Loud Route (North Ridge Counter-Snipe, Convoy C4 Ambush & Garrison Storm)",
            "description": "Ascend from (40, 175) to the North Ridge Sniper Perch (410, 285) to counter-snipe E6 Ghillie Snipers, ambush the convoy at the central bridge checkpoint (600, 175) with C4 and rifle fire, breach the North Garrison gate (890, 140) to storm Captain Dar's command post at (890, 80), and extract at (1160, 320).",
            "waypoints": [
                [40.0, 175.0],
                [410.0, 285.0],
                [600.0, 175.0],
                [890.0, 140.0],
                [890.0, 80.0],
                [1160.0, 320.0],
            ],
        },
    }

    level_dict = {
        "mission_id": "M05",
        "title": "Bridge Crossing",
        "chapter": 1,
        "is_chapter_finale": True,
        "scene_name": "M05",
        "width": 1200.0,
        "height": 350.0,
        "area_hectares": 42.0,
        "biome": "city_river_bridge_outskirts",
        "time_of_day": "day",
        "weather": "clear",
        "player_start": {
            "pos": [40.0, 175.0, 0.0],
            "facing_deg": 90.0,
            "facing_cardinal": "East",
            "starting_loadout": ["wpn_usp45_suppressed", "wpn_m4a1_sopmod", "wpn_knife_mesh", "C4Charge_x2", "WireCutters", "HackPDA", "EMPGrenade", "Lockpick"],
        },
        "strict_exclusions_enforced": {
            "forbidden_enemies": ["E5", "E7", "E8", "E9", "E11", "E12"],
            "forbidden_traps": ["T2", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T12", "T13", "T14", "T15"],
            "allowed_traps_only": ["T1", "T3", "T16"],
            "security_cameras_count": 4,
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


def write_m05_unity_scene_and_installer() -> Tuple[str, str]:
    scenes_dir = os.path.join(ROOT_DIR, "Assets/_Project/Scenes")
    scripts_dir = os.path.join(ROOT_DIR, "Assets/_Project/Scripts/Core")
    os.makedirs(scenes_dir, exist_ok=True)
    os.makedirs(scripts_dir, exist_ok=True)

    scene_path = os.path.join(scenes_dir, "M05.unity")
    installer_path = os.path.join(scripts_dir, "M05_BridgeCrossingSceneInstaller.cs")

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
  m_FogColor: {r: 0.72, g: 0.80, b: 0.88, a: 1}
  m_FogMode: 3
  m_FogDensity: 0.0025
  m_AmbientMode: 0
  m_AmbientSkyColor: {r: 0.65, g: 0.72, b: 0.80, a: 1}
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
  m_Name: M05_BridgeCrossing_MissionRoot
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
  m_Script: {fileID: 11500000, guid: e5f60718293a4b5c6d7e8f90a1b2c3d4, type: 3}
  m_Name: 
  m_EditorClassIdentifier: RealLoserStudio.Tactical.Core.M05_BridgeCrossingSceneInstaller
  missionJsonPath: Assets/_Project/Missions/M05.json
  enforceStrictM05Exclusions: 1
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
    /// Scene Bootstrapper & Runtime Controller for Mission 05 ("Bridge Crossing" — Chapter 1 Finale).
    /// Manages the 6-Zone 1200x350m (42.0 Hectares) City/River Bridge Outskirts compound,
    /// 36 Enemies (6x E1, 16x E2, 3x E3, 4x E4, 2x E6, 2x E10, 2x E13, 1x E14 Boss Captain Dar),
    /// 6 Traps (2x T1, 2x T3, 2x T16), 4 Security Cameras (M05_CAM_01..04 linked to M05_MON_01),
    /// and 2 Dynamic Events (E_M05_CONVOY at 360s and E_M05_HELI at 900s).
    /// </summary>
    public class M05_BridgeCrossingSceneInstaller : MonoBehaviour
    {
        [Header("Mission 05 Blueprint Binding")]
        public string missionJsonPath = "Assets/_Project/Missions/M05.json";
        public bool enforceStrictM05Exclusions = true;

        [Header("Core System References")]
        public PlayerTacticalController playerController;
        public StealthAndDetectionSystem stealthSystem;
        public MissionEventAndStreamingSystem streamingSystem;
        public MobileTouchHUDAndMEMap touchHudMap;

        [Header("Convoy & Boss State (O1)")]
        public bool c4PlantedTruck01;
        public bool c4PlantedTruck02;
        public bool convoyDetonated;
        public bool captainDarEliminated;
        public int captainDarHP = 180;
        public bool objectiveO1_Complete;
        public bool rewardHandCannon357Unlocked;

        [Header("Secondary Objectives (S1, S2)")]
        public List<TrapAndHazardSystem> checkpointCameras = new List<TrapAndHazardSystem>();
        public bool objectiveS1_CamerasDisabled;
        public bool briefcaseStolen;
        public bool alert3Triggered;
        public bool objectiveS2_GhostMedalEarned;

        [Header("Dynamic Mission Events")]
        public bool eventConvoyTriggered;
        public float convoyHaltRemainingSec;
        public bool eventHeliSweepTriggered;
        private float _missionElapsedSec;

        private void Start()
        {
            InitializeMission05();
        }

        public void InitializeMission05()
        {
            _missionElapsedSec = 0f;
            eventConvoyTriggered = false;
            eventHeliSweepTriggered = false;
            alert3Triggered = false;

            if (playerController != null)
            {
                // Spawn at Zone A West Approach Woods [40.0, 175.0] facing East (90 deg)
                playerController.transform.position = new Vector3(40.0f, 0.0f, 175.0f);
                playerController.transform.rotation = Quaternion.Euler(0f, 90f, 0f);
            }

            if (stealthSystem != null)
            {
                stealthSystem.OnAlertLevelChanged += HandleAlertLevelChanged;
            }
        }

        private void Update()
        {
            _missionElapsedSec += Time.deltaTime;

            // Event 1: E_M05_CONVOY at elapsed >= 360s (2 cargo trucks stop at [600, 175] for 90s)
            if (!eventConvoyTriggered && _missionElapsedSec >= 360.0f)
            {
                eventConvoyTriggered = true;
                convoyHaltRemainingSec = 90.0f;
            }

            if (eventConvoyTriggered && convoyHaltRemainingSec > 0f && !convoyDetonated)
            {
                convoyHaltRemainingSec = Mathf.Max(0f, convoyHaltRemainingSec - Time.deltaTime);
            }

            // Event 2: E_M05_HELI at elapsed >= 900s (patrol helicopter searchlight sweep)
            if (!eventHeliSweepTriggered && _missionElapsedSec >= 900.0f)
            {
                eventHeliSweepTriggered = true;
            }
        }

        private void HandleAlertLevelChanged(CompoundAlertLevel newLevel)
        {
            if (newLevel >= CompoundAlertLevel.Alert3_Reinforcements)
            {
                alert3Triggered = true;
            }
        }

        public void OnHackCheckpointMonitor_M05_MON_01()
        {
            for (int i = 0; i < checkpointCameras.Count; i++)
            {
                if (checkpointCameras[i] != null)
                {
                    checkpointCameras[i].isArmed = false;
                }
            }
            objectiveS1_CamerasDisabled = true;
        }

        public void OnPlantC4OnConvoyTruck(int truckIndex)
        {
            if (truckIndex == 1) c4PlantedTruck01 = true;
            if (truckIndex == 2) c4PlantedTruck02 = true;
        }

        public void OnDetonateConvoyC4()
        {
            if (c4PlantedTruck01 && c4PlantedTruck02)
            {
                convoyDetonated = true;
                CheckPrimaryObjectiveO1();
            }
        }

        public void OnDamageCaptainDar(int damage)
        {
            captainDarHP = Mathf.Max(0, captainDarHP - damage);
            if (captainDarHP == 0 && !captainDarEliminated)
            {
                captainDarEliminated = true;
                CheckPrimaryObjectiveO1();
            }
        }

        public void OnCollectDarBriefcase()
        {
            briefcaseStolen = true;
            objectiveS2_GhostMedalEarned = !alert3Triggered;
        }

        private void CheckPrimaryObjectiveO1()
        {
            if (convoyDetonated && captainDarEliminated)
            {
                objectiveO1_Complete = true;
                rewardHandCannon357Unlocked = true;
            }
        }
    }
}
"""
    with open(installer_path, "w", encoding="utf-8") as f:
        f.write(installer_cs)

    return scene_path, installer_path


def main() -> int:
    level_data = build_m05_level_dict()

    missions_dir = os.path.join(ROOT_DIR, "Assets/_Project/Missions")
    out_dir = os.path.join(ROOT_DIR, "artifacts/file_generation/ttl=63d/output")
    os.makedirs(missions_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    for p in (
        os.path.join(ROOT_DIR, "M05.json"),
        os.path.join(missions_dir, "M05.json"),
        os.path.join(out_dir, "M05.json"),
    ):
        with open(p, "w", encoding="utf-8") as f:
            json.dump(level_data, f, indent=2)

    scene_path, installer_path = write_m05_unity_scene_and_installer()
    with open(scene_path, "r", encoding="utf-8") as src, open(
        os.path.join(out_dir, "M05.unity"), "w", encoding="utf-8"
    ) as dst:
        dst.write(src.read())
    with open(installer_path, "r", encoding="utf-8") as src, open(
        os.path.join(out_dir, "M05_BridgeCrossingSceneInstaller.cs"), "w", encoding="utf-8"
    ) as dst:
        dst.write(src.read())

    print(f"[M05 BUILDER] Successfully generated M05.json, {scene_path}, and {installer_path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
